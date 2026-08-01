"""CLI: python -m econ_eval {eval,report,probe}"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from econ_eval import config
from econ_eval.models import Task


def _load_tasks() -> list[Task]:
    return [Task.from_yaml(p) for p in sorted(config.TASKS_DIR.glob("*.yaml"))]


def cmd_eval(args):
    from econ_eval.runner import run

    tasks = _load_tasks()
    if not tasks:
        print("no tasks in tasks/ - add some first", file=sys.stderr)
        return 1
    only = set(args.models.split(",")) if args.models else None
    models = config.build_models(only)
    judge = config.build_judge() if any(t.grader["type"] == "judge" for t in tasks) else None
    suffix = f"-{'-'.join(sorted(only))}" if only else ""
    ts = config.RESULTS_DIR / f"transcripts-{args.date}{suffix}.jsonl"
    run(tasks, models, judge, n=args.n, transcripts_path=ts, db_path=config.DB_PATH,
        dry_run=args.dry_run, only_task=args.task)
    return 0


def cmd_report(args):
    from econ_eval.report import build_report

    tracks = args.tracks.split(",") if args.tracks else None
    suffix = f"-{'-'.join(tracks)}" if tracks else ""
    md = config.RESULTS_DIR / f"report-{args.date}{suffix}.md"
    png = config.RESULTS_DIR / f"plot-{args.date}{suffix}.png"
    build_report(config.DB_PATH, md, png, tracks)
    print(f"wrote {md} and {png}")
    return 0


def cmd_probe(args):
    """Confirm both contestants and the judge are reachable with a trivial prompt."""
    models = config.build_models()
    judge = config.build_judge()
    for name, a in {**models, "judge": judge}.items():
        try:
            c = a.run("Reply with the single word: ok")
            print(f"{name} ({a.model}): OK -> {c.text.strip()[:40]!r}")
        except Exception as e:  # surface endpoint rejection (e.g. glm-5.2 not exposed)
            print(f"{name} ({a.model}): FAIL -> {type(e).__name__}: {e}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="econ_eval")
    p.add_argument("--date", default="run")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("eval")
    pe.add_argument("-n", type=int, default=config.DEFAULT_SAMPLES)
    pe.add_argument("--task", default=None)
    pe.add_argument("--models", default=None,
                    help="comma-separated adapter names (e.g. grok,luna); default all")
    pe.add_argument("--dry-run", action="store_true")
    pe.set_defaults(func=cmd_eval)

    pr = sub.add_parser("report")
    pr.add_argument("--tracks", default=None,
                    help="comma-separated tracks (e.g. quantitative,coding); default all")
    pr.set_defaults(func=cmd_report)

    pp = sub.add_parser("probe")
    pp.set_defaults(func=cmd_probe)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
