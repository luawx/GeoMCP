from __future__ import annotations
import multiprocessing as mp, os, signal, time, subprocess
from queue import Empty
from pathlib import Path
from typing import Any
from geomcp.config import load_config, runtime_dir
from geomcp.exceptions import JobError, WorkerError
from geomcp.jobs import JobStore
from .registry import build_task_registry

def _child(task_name: str, input_data: dict[str, Any], parameters: dict[str, Any], queue, memory_soft_limit_mb: int | None):
    try:
        if os.name != "nt":
            os.setsid()
        if memory_soft_limit_mb:
            try:
                import resource
                limit=int(memory_soft_limit_mb)*1024*1024
                resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
            except (ImportError, ValueError, OSError):
                pass
        task=build_task_registry().get(task_name); queue.put((True,task.handler(input_data,parameters),None))
    except BaseException as exc: queue.put((False,None,f"{type(exc).__name__}: {exc}"))

def _claim(store: JobStore, job_id: str, *, executor: str, max_workers: int) -> bool:
    while True:
        current=store.get(job_id)
        if current.status=="cancelled": return False
        if current.status!="queued": raise JobError(f"Cannot start job in state: {current.status}")
        if store.claim_running(job_id,executor=executor,max_running=max_workers): return True
        time.sleep(0.2)

def execute_job(job_id: str, *, config_dir: str | Path | None=None, expected_executor: str) -> int:
    config=load_config(config_dir); store=JobStore(runtime_dir(config)); job=store.get(job_id)
    if job.executor!=expected_executor:
        store.transition(job_id,"failed",error=f"Executor mismatch: expected {expected_executor}, got {job.executor}"); return 2
    try: task=build_task_registry().get(job.task_type)
    except WorkerError as exc: store.transition(job_id,"failed",error=str(exc)); return 2
    if task.executor!=expected_executor:
        store.transition(job_id,"failed",error=f"Task {task.name} is not registered for {expected_executor}"); return 2
    try:
        task.validate(job.input, job.parameters)
    except WorkerError as exc:
        store.transition(job_id,"failed",error=str(exc)); return 2
    executor_cfg=config.get("executors",{}).get(expected_executor,{}) or {}
    profile = {}
    picking_output = None
    task_input = dict(job.input)
    if task.name.startswith('picking.'):
        # The executing worker binds its own configuration; stored input cannot redirect it.
        task_input['config_dir'] = config['_meta']['config_dir']
        try:
            from geomcp.services.picking import PickingService
            service = PickingService(config_dir=config['_meta']['config_dir'])
            if task.name != 'picking.import.cpu':
                workspace = task_input.get('workspace')
                ref = task_input['prepared_ref']
                if workspace:
                    ref = service._ref(Path(ref), workspace)
                prepared = service._prepared(ref, workspace)
                profile = prepared['execution_profile']
                picking_output = Path(prepared['output_dir'])
                expected = f"picking.{prepared['backend_id']}.{profile.get('executor', 'cpu')}"
                if expected != task.name:
                    raise WorkerError('Picking task mismatch')
            else:
                profile = config.get('picking', {}).get('execution_profiles', {}).get('import-cpu', {})
                picking_output = service.policy.validate_write(task_input['output_dir'])
            if not profile or not profile.get('enabled'):
                raise WorkerError('Picking execution profile is disabled')
            if not isinstance(profile.get('concurrency'), int) or isinstance(profile.get('concurrency'), bool) or profile['concurrency'] < 1:
                raise WorkerError('Picking profile requires positive concurrency')
            if isinstance(profile.get('timeout'), bool) or not isinstance(profile.get('timeout'), (int, float)) or not 0 < profile['timeout'] <= 86400:
                raise WorkerError('Picking profile requires bounded timeout')
        except Exception as exc:
            store.transition(job_id, 'failed', error=str(exc))
            return 2
        task_input['_job_id'] = job_id
    max_workers=max(1,int(executor_cfg.get("max_workers",1)))
    if profile:
        max_workers = min(max_workers, profile['concurrency'])
    if not _claim(store,job_id,executor=expected_executor,max_workers=max_workers): return 0
    store.set_executor_meta(job_id,worker_pid=os.getpid())
    configured_timeout=float(executor_cfg.get("timeout",task.timeout) or task.timeout)
    timeout=min(float(task.timeout),configured_timeout) if configured_timeout>0 else float(task.timeout)
    if profile:
        timeout = min(timeout, float(profile["timeout"]))
    memory_limit=executor_cfg.get("memory_soft_limit_mb")
    queue=mp.Queue(); process=mp.Process(target=_child,args=(task.name,task_input,job.parameters,queue,memory_limit),daemon=False)
    process.start(); store.set_executor_meta(job_id,task_pid=process.pid,timeout=timeout,memory_soft_limit_mb=memory_limit)
    process.join(timeout)
    if process.is_alive():
        _terminate_tree(process.pid); process.join(5)
        _invalidate_manifest(picking_output, config)
        if store.get(job_id).status!="cancelled": store.transition(job_id,"failed",error=f"Task timeout after {timeout:.1f}s")
        return 2
    if store.get(job_id).status=="cancelled":
        _invalidate_manifest(picking_output, config)
        return 0
    try: success,output,error=queue.get(timeout=1)
    except Empty: success,output,error=False,None,f"Worker exited with code {process.exitcode} without a result"
    if success:
        try:
            store.transition(job_id, 'completed', output=output, progress=1.0)
        except JobError:
            _invalidate_manifest(picking_output, config)
            if store.get(job_id).status == 'cancelled':
                return 0
            raise
        return 0
    _invalidate_manifest(picking_output, config)
    store.transition(job_id,"failed",error=error or "Task failed"); return 2

def cancel_local_job(job_id: str, *, config_dir: str | Path | None=None) -> bool:
    config=load_config(config_dir); store=JobStore(runtime_dir(config)); job=store.get(job_id)
    # Persist cancellation before terminating: the supervising worker must never
    # promote a completed queue result after cancellation wins the race.
    if job.status in {'completed', 'failed', 'cancelled'}:
        return True
    store.transition(job_id, 'cancelled')
    pid=job.executor_meta.get("task_pid") or job.executor_meta.get("worker_pid")
    if pid:
        try: _terminate_tree(int(pid))
        except ProcessLookupError: pass
        except OSError as exc: raise JobError(f"Unable to terminate worker process {pid}: {exc}") from exc
    current=store.get(job_id)
    if current.status in {"queued","running"}: store.transition(job_id,"cancelled")
    if job.task_type.startswith('picking.'):
        from geomcp.services.picking import PickingService
        service = PickingService(config_dir=config['_meta']['config_dir'])
        if job.task_type == 'picking.import.cpu':
            output = service.policy.validate_write(job.input['output_dir'])
        else:
            ref = job.input['prepared_ref']
            workspace = job.input.get('workspace')
            if workspace:
                ref = service._ref(Path(ref), workspace)
            snapshot = service._read(ref, workspace)
            output = service.policy.validate_write(snapshot.parent)
        _invalidate_manifest(output, config)
    return True


def _invalidate_manifest(output, config):
    if output is None:
        return
    from geomcp.services.permissions import PathPolicy
    path = PathPolicy.from_config(config).validate_write(Path(output) / 'manifest.json')
    path.unlink(missing_ok=True)


def _terminate_tree(pid):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(int(pid)), '/T', '/F'], capture_output=True, check=False)
    else:
        try:
            os.killpg(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
