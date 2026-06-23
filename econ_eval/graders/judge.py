"""Judge grader: rubric scoring and blind, order-swapped pairwise."""
from __future__ import annotations

import json
import re

from econ_eval.models import Grade, Task

_RUBRIC_PROMPT = """You are a strict, neutral grader. Score the ANSWER against each rubric point.
Return ONLY a JSON object mapping each point's index (as a string) to 0 or 1.

RUBRIC:
{rubric}

QUESTION:
{question}

ANSWER:
{answer}
"""

_PAIRWISE_PROMPT = """You are a strict, neutral judge. Two answers (A and B) respond to the same task.
Pick the better one. Return ONLY one token: A, B, or TIE.

TASK:
{question}

ANSWER A:
{a}

ANSWER B:
{b}
"""


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def rubric_score(judge, task: Task, text: str) -> Grade:
    points = task.grader["rubric"]
    rubric = "\n".join(f"{i}: {p}" for i, p in enumerate(points))
    prompt = _RUBRIC_PROMPT.format(rubric=rubric, question=task.prompt, answer=text)
    out = judge.run(prompt).text
    scores = _parse_json(out)
    hits = sum(1 for i in range(len(points)) if int(scores.get(str(i), 0)) == 1)
    frac = hits / len(points) if points else 0.0
    return Grade(frac, frac >= 0.5, f"{hits}/{len(points)} rubric points")


def _verdict(judge, question: str, a: str, b: str) -> float:
    out = judge.run(_PAIRWISE_PROMPT.format(question=question, a=a, b=b)).text.strip().upper()
    if out.startswith("A"):
        return 1.0
    if out.startswith("B"):
        return 0.0
    return 0.5


def pairwise(judge, task: Task, text_a: str, text_b: str) -> float:
    """Score for A vs B in [0,1], averaged over A/B-swapped runs to cancel position bias."""
    v1 = _verdict(judge, task.prompt, text_a, text_b)            # A in slot A
    v2 = _verdict(judge, task.prompt, text_b, text_a)            # A in slot B -> invert
    return (v1 + (1.0 - v2)) / 2.0
