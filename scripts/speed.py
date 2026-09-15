"""Offline speed check: latency table over the local scores DB, optional median bars.

Run: uv run python scripts/speed.py [--models id,...] [--check id=sec,...]
Reads only results/scores.sqlite; makes no model calls. Exit 1 lists any
model whose median latency exceeds its --check bar.

Default models: deepseek-flash, muse-spark-1.3-contributor, gemini-3.8-flash-high.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

from econ_eval import config, stats

DEFAULT_MODELS = "deepseek-flash,muse-spark-1.3-contributor,gemini-3.8-flash-high"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="speed.py")
    p.add_argument("--models", default=DEFAULT_MODELS)
    p.add_argument("--check", default="",
                   help="comma-separated id=seconds median bars, e.g. deepseek-flash=15")
    args = p.parse_args(argv)
    con = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    medians: dict[str, float] = {}
    for model in args.models.split(","):
        rows = con.execute(
            "SELECT track, latency_s FROM scores WHERE model=? AND latency_s IS NOT NULL",
            (model,),
        ).fetchall()
        if not rows:
            print(f"{model}: no rows")
            continue
        s = stats.latency_summary([r[1] for r in rows])
        medians[model] = s["median"]
        by_track = sorted({t for t, _ in rows})
        print(f"{model} n={s['n']} mean={s['mean']:.1f}s median={s['median']:.1f}s "
              f"p95={s['p95']:.1f}s min={s['min']:.1f}s max={s['max']:.1f}s")
        for t in by_track:
            st = stats.latency_summary([l for tt, l in rows if tt == t])
            print(f"  {t}: n={st['n']} mean={st['mean']:.1f}s median={st['median']:.1f}s")
    con.close()
    bars = dict(kv.split("=") for kv in args.check.split(",") if "=" in kv)
    bad = stats.check_latency_bars(medians, {k: float(v) for k, v in bars.items()})
    if bad:
        print("OVER BAR: " + ", ".join(f"{m} median={medians[m]:.1f}s" for m in bad))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
