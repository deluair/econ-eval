from pathlib import Path

import pytest

from econ_eval.models import Task, VALID_TRACKS, VALID_GRADERS

TASK_DIR = Path(__file__).resolve().parent.parent / "tasks"
TASK_FILES = sorted(TASK_DIR.glob("*.yaml"))


def test_there_are_twelve_tasks():
    assert len(TASK_FILES) == 12


@pytest.mark.parametrize("path", TASK_FILES, ids=lambda p: p.stem)
def test_task_parses_and_is_well_formed(path):
    t = Task.from_yaml(path)
    assert t.track in VALID_TRACKS
    assert t.grader["type"] in VALID_GRADERS
    assert t.source.strip(), "every task needs a real source"
    if t.grader["type"] == "numeric":
        assert "reference" in t.grader
    if t.grader["type"] == "judge":
        assert t.grader.get("rubric"), "judge tasks need a rubric"
    if t.grader["type"] == "code_exec":
        assert t.grader.get("assertions"), "code tasks need assertions"


def test_three_tasks_per_track():
    counts = {}
    for p in TASK_FILES:
        t = Task.from_yaml(p)
        counts[t.track] = counts.get(t.track, 0) + 1
    assert counts == {"quantitative": 3, "reasoning": 3, "coding": 3, "writing": 3}


def test_one_bangla_writing_task():
    assert (TASK_DIR / "write-oped-bangla.yaml").exists()
