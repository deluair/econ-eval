from pathlib import Path

import pytest

from econ_eval.models import Task, VALID_TRACKS, VALID_GRADERS

TASK_DIR = Path(__file__).resolve().parent.parent / "tasks"
TASK_FILES = sorted(TASK_DIR.glob("*.yaml"))


def test_there_are_fifty_four_tasks():
    # 20 original (2026-06-22) plus 30 "daily work" tasks (2026-09-15)
    # plus 4 agent-track pilot tasks (2026-09-15)
    assert len(TASK_FILES) == 54


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
    if t.grader["type"] == "artifact":
        mode = t.grader.get("mode", "numeric-on-file")
        assert mode in ("numeric-on-file", "assertions-on-file")
        if mode == "numeric-on-file":
            assert "file" in t.grader and "reference" in t.grader
        else:
            assert t.grader.get("assertions"), "assertions-on-file needs assertions"
    if t.files is not None:
        assert (TASK_DIR / "files" / t.id / t.files).is_dir(), \
            f"{t.id}: files dir tasks/files/{t.id}/{t.files}/ missing"


def test_tasks_per_track():
    counts = {}
    for p in TASK_FILES:
        t = Task.from_yaml(p)
        counts[t.track] = counts.get(t.track, 0) + 1
    assert counts == {"quantitative": 11, "reasoning": 10, "coding": 10, "writing": 10,
                      "finance": 5, "review": 4, "agent": 4}


def test_one_bangla_writing_task():
    assert (TASK_DIR / "write-oped-bangla.yaml").exists()
