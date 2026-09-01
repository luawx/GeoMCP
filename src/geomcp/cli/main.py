"""Human CLI for GeoMCP."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Sequence
import yaml
from geomcp.api import das as das_api, filesystem as filesystem_api, jobs as jobs_api, system as system_api
from geomcp.models import ApiResult

def _add_window(p):
    p.add_argument("--channel-start", type=int, default=None)
    p.add_argument("--channel-stop", type=int, default=None)
    p.add_argument("--sample-start", type=int, default=0)
    p.add_argument("--sample-stop", type=int, default=None)

def _parser():
    parser = argparse.ArgumentParser(prog="geomcp", description="GeoMCP research service CLI")
    parser.add_argument("--config-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="group", required=True)

    system = sub.add_parser("system")
    ss = system.add_subparsers(dest="command", required=True)
    ss.add_parser("status")

    config = sub.add_parser("config")
    cs = config.add_subparsers(dest="command", required=True)
    cs.add_parser("show")
    cs.add_parser("validate")

    filesystem = sub.add_parser("filesystem")
    fs = filesystem.add_subparsers(dest="command", required=True)
    fsi = fs.add_parser("inspect")
    fsi.add_argument("path")

    job = sub.add_parser("job")
    js = job.add_subparsers(dest="command", required=True)
    jl = js.add_parser("list")
    jl.add_argument("--limit", type=int, default=100)
    jl.add_argument("--status", default=None)
    jh = js.add_parser("healthcheck")
    jh.add_argument("--executor", choices=("cpu", "gpu"), default="cpu")
    for name in ("status", "result", "logs", "cancel"):
        jp = js.add_parser(name)
        jp.add_argument("job_id")

    das = sub.add_parser("das")
    ds = das.add_subparsers(dest="command", required=True)
    di = ds.add_parser("inspect")
    di.add_argument("path")
    dr = ds.add_parser("read-window")
    dr.add_argument("path")
    _add_window(dr)
    db = ds.add_parser("bandpass")
    db.add_argument("path")
    db.add_argument("freqmin", type=float)
    db.add_argument("freqmax", type=float)
    db.add_argument("--output-path", default=None)
    _add_window(db)
    dm = ds.add_parser("rms")
    dm.add_argument("path")
    _add_window(dm)
    dp = ds.add_parser("plot")
    dp.add_argument("path")
    dp.add_argument("--output-path", default=None)
    dp.add_argument("--dpi", type=int, default=150)
    _add_window(dp)
    return parser

def _render(result: ApiResult, *, as_json: bool):
    payload = result.to_dict()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).rstrip())

def _window(args):
    return {
        "channel_start": args.channel_start,
        "channel_stop": args.channel_stop,
        "sample_start": args.sample_start,
        "sample_stop": args.sample_stop,
    }

def main(argv: Sequence[str] | None=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in raw
    raw = [x for x in raw if x != "--json"]
    args = _parser().parse_args(raw)
    cd = args.config_dir

    if args.group == "system":
        result = system_api.status(cd)
    elif args.group == "config" and args.command == "show":
        result = system_api.config_snapshot(cd)
    elif args.group == "config":
        result = system_api.validate(cd)
    elif args.group == "filesystem":
        result = filesystem_api.inspect(args.path, config_dir=cd)
    elif args.group == "job" and args.command == "list":
        result = jobs_api.list_jobs(limit=args.limit, status=args.status, config_dir=cd)
    elif args.group == "job" and args.command == "healthcheck":
        result = jobs_api.submit_healthcheck(executor=args.executor, config_dir=cd)
    elif args.group == "job" and args.command == "status":
        result = jobs_api.status(args.job_id, config_dir=cd)
    elif args.group == "job" and args.command == "result":
        result = jobs_api.result(args.job_id, config_dir=cd)
    elif args.group == "job" and args.command == "logs":
        result = jobs_api.logs(args.job_id, config_dir=cd)
    elif args.group == "job" and args.command == "cancel":
        result = jobs_api.cancel(args.job_id, config_dir=cd)
    elif args.group == "das" and args.command == "inspect":
        result = das_api.inspect(args.path, config_dir=cd)
    elif args.group == "das" and args.command == "read-window":
        result = das_api.read_window(args.path, config_dir=cd, **_window(args))
    elif args.group == "das" and args.command == "bandpass":
        result = das_api.bandpass(
            args.path,
            freqmin=args.freqmin,
            freqmax=args.freqmax,
            output_path=args.output_path,
            config_dir=cd,
            **_window(args),
        )
    elif args.group == "das" and args.command == "rms":
        result = das_api.rms(args.path, config_dir=cd, **_window(args))
    elif args.group == "das" and args.command == "plot":
        result = das_api.plot(
            args.path,
            output_path=args.output_path,
            dpi=args.dpi,
            config_dir=cd,
            **_window(args),
        )
    else:
        _parser().error("Unsupported command")
        return 2

    _render(result, as_json=as_json)
    return 0 if result.success else 2

if __name__ == "__main__":
    raise SystemExit(main())
