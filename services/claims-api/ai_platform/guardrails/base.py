"""Common result type for guardrail checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GuardrailAction = Literal["redacted", "sanitized", "blocked", "overridden", "warned"]


@dataclass(frozen=True)
class GuardrailFinding:
    guardrail: str
    action: GuardrailAction
    detail: str
