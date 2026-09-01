import threading
import time
import pytest
from geomcp.exceptions import JobError
from geomcp.executors.dispatch import watch_dispatch
from geomcp.jobs import JobStore
from geomcp.worker.runtime import execute_job

def test_job_completed_and_mirrored(config_factory):
    config_dir, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="test", task_type="cpu.healthcheck", executor="cpu")
    assert execute_job(job.job_id, config_dir=config_dir, expected_executor="cpu") == 0
    done = store.get(job.job_id)
    assert done.status == "completed"
    assert done.output["ok"] is True
    assert done.progress == 1.0
    assert (runtime / "jobs" / f"{job.job_id}.json").exists()

def test_failed_unregistered_task(config_factory):
    config_dir, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="bad", task_type="not.registered", executor="cpu")
    assert execute_job(job.job_id, config_dir=config_dir, expected_executor="cpu") != 0
    assert store.get(job.job_id).status == "failed"

def test_cancelled_and_illegal_transition(config_factory):
    _, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="test", task_type="cpu.healthcheck", executor="cpu")
    cancelled = store.transition(job.job_id, "cancelled")
    assert cancelled.status == "cancelled"
    with pytest.raises(JobError):
        store.transition(job.job_id, "running")

def test_cpu_timeout_marks_failed(config_factory):
    config_dir, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="delay", task_type="cpu.delay", executor="cpu", parameters={"seconds": 2})
    assert execute_job(job.job_id, config_dir=config_dir, expected_executor="cpu") != 0
    failed = store.get(job.job_id)
    assert failed.status == "failed"
    assert "timeout" in (failed.error or "").lower()

def test_worker_rejects_unexpected_healthcheck_payload(config_factory):
    config_dir, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(
        tool="health",
        task_type="cpu.healthcheck",
        executor="cpu",
        input={"command": "unexpected text"},
    )
    assert execute_job(job.job_id, config_dir=config_dir, expected_executor="cpu") != 0
    failed = store.get(job.job_id)
    assert failed.status == "failed"
    assert "accepts no input" in (failed.error or "")

def test_terminal_transition_is_atomic_under_race(config_factory):
    _, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="race", task_type="cpu.healthcheck", executor="cpu")
    store.transition(job.job_id, "running")

    barrier = threading.Barrier(3)
    outcomes = []

    def finish(status):
        local = JobStore(runtime)
        barrier.wait()
        try:
            local.transition(job.job_id, status, output={"ok": True} if status == "completed" else None)
            outcomes.append(status)
        except JobError:
            outcomes.append("rejected")

    a = threading.Thread(target=finish, args=("completed",))
    b = threading.Thread(target=finish, args=("cancelled",))
    a.start()
    b.start()
    barrier.wait()
    a.join()
    b.join()

    assert outcomes.count("rejected") == 1
    assert store.get(job.job_id).status in {"completed", "cancelled"}

def test_dispatch_watchdog_fails_unclaimed_job(config_factory):
    _, _, runtime, _ = config_factory()
    store = JobStore(runtime)
    job = store.create(tool="dispatch", task_type="cpu.healthcheck", executor="cpu")

    class FailedProcess:
        pid = 123
        def poll(self):
            return 7

    watch_dispatch(store, job.job_id, FailedProcess(), timeout=0.5, label="test launcher")
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and store.get(job.job_id).status == "queued":
        time.sleep(0.05)

    failed = store.get(job.job_id)
    assert failed.status == "failed"
    assert "exit code 7" in (failed.error or "")
