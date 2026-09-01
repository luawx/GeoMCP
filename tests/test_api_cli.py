from geomcp.api import jobs
from geomcp.cli.main import main

def test_job_api_and_cli(config_factory, capsys):
    config_dir, _, _, _=config_factory()
    assert jobs.list_jobs(config_dir=config_dir).success
    code=main(["--config-dir",str(config_dir),"job","list","--json"])
    assert code==0 and '"success": true' in capsys.readouterr().out
