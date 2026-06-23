"""Core data models for the benchmark."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_TRACKS = {"quantitative", "reasoning", "coding", "writing"}
VALID_GRADERS = {"numeric", "exact", "code_exec", "judge"}


@dataclass
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    latency_s: float
    model: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Grade:
    score: float          # in [0, 1]
    passed: bool
    detail: str = ""


@dataclass
class Task:
    id: str
    track: str
    prompt: str
    grader: dict[str, Any]
    source: str
    samples: int = 5

    def __post_init__(self) -> None:
        if self.track not in VALID_TRACKS:
            raise ValueError(f"{self.id}: unknown track {self.track!r}")
        gtype = self.grader.get("type")
        if gtype not in VALID_GRADERS:
            raise ValueError(f"{self.id}: unknown grader type {gtype!r}")
        if not self.source:
            raise ValueError(f"{self.id}: a source (provenance) is required")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Task":
        data = yaml.safe_load(Path(path).read_text())
        return cls(
            id=data["id"],
            track=data["track"],
            prompt=data["prompt"],
            grader=data["grader"],
            source=data["source"],
            samples=data.get("samples", 5),
        )


@dataclass
class Sample:
    task_id: str
    model: str
    idx: int
    completion: Completion
