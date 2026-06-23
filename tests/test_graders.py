from types import SimpleNamespace

from econ_eval.models import Task, Completion
from econ_eval.graders import numeric, exact, code_exec, judge


def mk(grader, track="quantitative", prompt="q"):
    return Task(id="t", track=track, prompt=prompt, grader=grader, source="x")


def test_numeric_extract_prefers_answer_line():
    assert numeric.extract_number("blah 99\nANSWER: 8,412,034") == 8412034.0


def test_numeric_tolerance_pass_and_fail():
    t = mk({"type": "numeric", "reference": 1000, "tolerance_pct": 0.5})
    assert numeric.grade(t, "ANSWER: 1003").passed is True      # 0.3% within 0.5%
    assert numeric.grade(t, "ANSWER: 1010").passed is False     # 1.0% outside


def test_numeric_no_number():
    t = mk({"type": "numeric", "reference": 5})
    assert numeric.grade(t, "no digits here").passed is False


def test_exact_normalized():
    t = mk({"type": "exact", "reference": "Ready-Made Garments"})
    assert exact.grade(t, "It is ready-made   garments, yes").passed is True
    assert exact.grade(t, "jute").passed is False


def test_code_exec_pass_and_fail(tmp_path):
    t = mk({"type": "code_exec", "assertions": "assert add(2,3) == 5"}, track="coding")
    good = "```python\ndef add(a,b):\n    return a+b\n```"
    bad = "```python\ndef add(a,b):\n    return a-b\n```"
    assert code_exec.grade(t, good).passed is True
    assert code_exec.grade(t, bad).passed is False


class FakeJudge:
    def __init__(self, text):
        self._text = text
    def run(self, prompt):
        return Completion(text=self._text, tokens_in=0, tokens_out=0, latency_s=0, model="fake")


def test_rubric_score():
    t = mk({"type": "judge", "rubric": ["cites a source", "states a number", "no slop"]},
           track="reasoning")
    g = judge.rubric_score(FakeJudge('{"0":1,"1":1,"2":0}'), t, "answer")
    assert abs(g.score - 2/3) < 1e-9
    assert g.passed is True


def test_pairwise_order_swap_cancels_bias():
    t = mk({"type": "judge", "rubric": []}, track="writing")
    # A judge that always says "the first slot wins" -> A in slot A = win,
    # A in slot B = loss; order-swap average must be 0.5 (no real preference).
    first_slot = FakeJudge("A")
    score = judge.pairwise(first_slot, t, "text_a", "text_b")
    assert abs(score - 0.5) < 1e-9
    # A judge that genuinely prefers text_a regardless of slot.
    class PrefersA:
        def run(self, prompt):
            verdict = "A" if "text_a" in prompt.split("ANSWER B:")[0] else "B"
            return Completion(verdict, 0, 0, 0, "fake")
    assert judge.pairwise(PrefersA(), t, "text_a", "text_b") == 1.0
