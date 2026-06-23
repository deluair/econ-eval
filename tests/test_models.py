import textwrap

import pytest

from econ_eval.models import Task, Grade, Completion


def write_task(tmp_path, body):
    p = tmp_path / "t.yaml"
    p.write_text(textwrap.dedent(body))
    return p


def test_task_from_yaml(tmp_path):
    p = write_task(tmp_path, """
        id: quant-demo
        track: quantitative
        prompt: |
          What is 2+2?
        grader:
          type: numeric
          reference: 4
          tolerance_pct: 0.5
        source: "trivial (2026-06-22)"
        samples: 3
    """)
    t = Task.from_yaml(p)
    assert t.id == "quant-demo"
    assert t.track == "quantitative"
    assert t.grader["reference"] == 4
    assert t.samples == 3
    assert "2+2" in t.prompt


def test_task_rejects_unknown_track(tmp_path):
    p = write_task(tmp_path, """
        id: bad
        track: astrology
        prompt: x
        grader: {type: numeric, reference: 1}
        source: "x"
    """)
    with pytest.raises(ValueError):
        Task.from_yaml(p)


def test_task_requires_source(tmp_path):
    p = write_task(tmp_path, """
        id: bad
        track: quantitative
        prompt: x
        grader: {type: numeric, reference: 1}
        source: ""
    """)
    with pytest.raises(ValueError):
        Task.from_yaml(p)


def test_grade_and_completion_fields():
    g = Grade(score=0.5, passed=False, detail="x")
    assert g.score == 0.5 and g.passed is False
    c = Completion(text="hi", tokens_in=1, tokens_out=2, latency_s=0.1, model="m")
    assert c.raw == {}
