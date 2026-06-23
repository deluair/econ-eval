import sqlite3
from pathlib import Path

from econ_eval.runner import SCHEMA
from econ_eval.report import build_report


def _seed(db):
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    rows = []
    # opus sweeps; glm loses every task -> should be significant
    for i, track in enumerate(["quantitative", "reasoning", "coding", "writing"] * 2):
        tid = f"t{i}"
        for idx in range(2):
            rows.append((tid, track, "claude-opus-4-8", idx, 1.0, 1, 100, 50, 0.1, "ok"))
            rows.append((tid, track, "glm-5.2", idx, 0.0, 0, 100, 50, 0.1, "no"))
    con.executemany("INSERT INTO scores VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()


def test_build_report(tmp_path):
    db = tmp_path / "scores.sqlite"
    _seed(db)
    md = tmp_path / "report.md"
    png = tmp_path / "plot.png"
    build_report(db, md, png)
    text = md.read_text()
    assert "## Overall" in text
    assert "## quantitative" in text
    assert "## Head-to-head" in text
    assert "sign-test p-value" in text
    assert "significant" in text
    assert png.exists() and png.stat().st_size > 0
