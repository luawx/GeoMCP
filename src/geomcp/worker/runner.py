from __future__ import annotations
import argparse
from .runtime import cancel_local_job, execute_job

def main(argv=None):
    p=argparse.ArgumentParser(prog="python -m geomcp.worker.runner"); p.add_argument("job_id"); p.add_argument("--config-dir", default=None); p.add_argument("--cancel", action="store_true"); a=p.parse_args(argv)
    if a.cancel: cancel_local_job(a.job_id, config_dir=a.config_dir); return 0
    return execute_job(a.job_id, config_dir=a.config_dir, expected_executor="gpu")
if __name__ == "__main__": raise SystemExit(main())
