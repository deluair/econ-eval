from pathlib import Path

from econ_eval.models import Task, Completion
from econ_eval import runner


class CountingAdapter:
    def __init__(self, model, text):
        self.name = model
        self.model = model
        self.text = text
        self.calls = 0
    def run(self, prompt):
        self.calls += 1
        return Completion(self.text, 5, 5, 0.01, self.model)


def mk_task():
    return Task(id="q1", track="quantitative", prompt="2+2?",
                grader={"type": "numeric", "reference": 4, "tolerance_pct": 1},
                source="x", samples=3)


def test_runner_caches_and_resumes(tmp_path):
    t = mk_task()
    a = CountingAdapter("claude-opus-4-8", "ANSWER: 4")
    b = CountingAdapter("glm-5.2", "ANSWER: 4")
    models = {"opus": a, "glm": b}
    tr = tmp_path / "tr.jsonl"
    db = tmp_path / "scores.sqlite"

    made1 = runner.run([t], models, judge=None, n=3, transcripts_path=tr, db_path=db)
    assert made1 == 6 and a.calls == 3 and b.calls == 3

    # second run: everything cached -> zero new adapter calls
    made2 = runner.run([t], models, judge=None, n=3, transcripts_path=tr, db_path=db)
    assert made2 == 0 and a.calls == 3 and b.calls == 3


def test_dry_run_makes_no_calls(tmp_path):
    t = mk_task()
    a = CountingAdapter("claude-opus-4-8", "ANSWER: 4")
    made = runner.run([t], {"opus": a}, judge=None, n=2,
                      transcripts_path=tmp_path / "x.jsonl",
                      db_path=tmp_path / "x.sqlite", dry_run=True)
    assert made == 0 and a.calls == 0
