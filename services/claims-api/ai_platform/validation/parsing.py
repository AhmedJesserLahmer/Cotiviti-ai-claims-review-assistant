"""Tolerant extraction of a JSON object from LLM text.

Models asked for "only JSON" still regularly return fenced blocks, a sentence before
the object, trailing commas or smart quotes. The previous implementation only stripped
backticks, so any of those made the analysis fall back to "flag_for_review" with no
explanation. This module recovers the common cases and fails loudly otherwise.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ai_platform.errors import OutputParseError

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_SMART_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def _first_balanced_object(text: str) -> str | None:
    """Return the first top-level {...} block, ignoring braces inside strings."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        start = text.find("{", start + 1)
    return None


def _repairs(candidate: str) -> list[str]:
    fixed = candidate.translate(_SMART_QUOTES)
    fixed = _TRAILING_COMMA_RE.sub(r"\1", fixed)
    variants = [fixed]
    # Python-dict style output ({'a': 'b'}) only when there are no double quotes at all,
    # so apostrophes inside normal JSON strings are never rewritten.
    if '"' not in fixed and "'" in fixed:
        variants.append(fixed.replace("'", '"'))
    for literal, json_literal in (("True", "true"), ("False", "false"), ("None", "null")):
        variants = [re.sub(rf"\b{literal}\b", json_literal, v) for v in variants]
    return variants


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse the JSON object contained in ``text`` or raise ``OutputParseError``."""
    if not isinstance(text, str) or not text.strip():
        raise OutputParseError("empty model output")

    candidates: list[str] = []
    stripped = text.strip()
    candidates.append(stripped)
    candidates.extend(match.strip() for match in _FENCE_RE.findall(stripped))
    balanced = _first_balanced_object(stripped.translate(_SMART_QUOTES))
    if balanced:
        candidates.append(balanced)

    for candidate in candidates:
        for variant in [candidate, *_repairs(candidate)]:
            try:
                parsed = json.loads(variant)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return parsed

    preview = stripped[:120].replace("\n", " ")
    raise OutputParseError(f"no JSON object found in model output: {preview!r}")
