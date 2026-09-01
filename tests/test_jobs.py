import pytest
from geomcp.exceptions import JobError
from geomcp.jobs import JobStore
from geomcp.worker.runtime import execute_job

def test_job_completed_and_mirrored(config_factory):
    config_dir, _, runtime, _ = config_factory(); store=JobStore(runtime)
    job=store.create(tool="test",task_type="cpu.healthcheck",executor="cpu")
    assert execute_job(job.job_id,config_dir=config_dir,expected_executor="cpu")==0
    done=store.get(job.job_id)
    assert done.status=="completed" and done.output["ok"] is True and done.progress==1.0
    assert (runtime/"jobs"/f"{job.job_id}.json").exists()

def test_failed_unregistered_task(config_factory):
    config_dir, _, runtime, _ = config_factory(); store=JobStore(runtime)
    job=store.create(tool="bad",task_type="not.registered",executor="cpu")
    assert execute_job(job.job_id,config_dir=config_dir,expected_executor="cpu")!=0
    assert store.get(job.job_id).status=="failed"

def test_cancelled_and_illegal_transition(config_factory):
    _, _, runtime, _=config_factory(); store=JobStore(runtime)
    job=store.create(tool="test",task_type="cpu.healthcheck",executor="cpu")
    cancelled=store.transition(job.job_id,"cancelled")
    assert cancelled.status=="cancelled"
    with pytest.raises(JobError): store.transition(job.job_id,"running")

def test_cpu_timeout_marks_failed(config_factory):
    config_dir, _, runtime, _=config_factory(); store=JobStore(runtime)
    job=store.create(tool="delay",task_type="cpu.delay",executor="cpu",parameters={"seconds":2})
    assert execute_job(job.job_id,config_dir=config_dir,expected_executor="cpu")!=0
    failed=store.get(job.job_id)
    assert failed.status=="failed" and "timeout" in (failed.error or "").lower()

def test_worker_rejects_unexpected_healthcheck_payload(config_factory):
    config_dir, _, runtime, _=config_factory(); store=JobStore(runtime)
    job=store.create(tool="health",task_type="cpu.healthcheck",executor="cpu",input={"command":"unexpected text"})
    assert execute_job(job.job_id,config_dir=config_dir,expected_executor="cpu")!=0
    failed=store.get(job.job_id)
    assert failed.status=="failed" and "accepts no input" in (failed.error or "")
