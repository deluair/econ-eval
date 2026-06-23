"""Adapter protocol: turn a prompt into a Completion."""
from __future__ import annotations

from typing import Protocol

from econ_eval.models import Completion


class Adapter(Protocol):
    name: str
    model: str

    def run(self, prompt: str) -> Completion: ...
