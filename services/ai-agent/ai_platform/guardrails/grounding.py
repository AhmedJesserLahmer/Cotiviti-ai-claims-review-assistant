"""Grounding check: numbers cited in LLM reasoning must exist in the source data.

A fluent explanation that quotes "$5,200 billed" when the claim says $1,200 is worse
than no explanation: a reviewer will trust it. Every dollar amount, percentage and
ratio in the reasoning is matched (with tolerance for rounding) against the values the
model was given. Unmatched numbers are reported; too many of them block an approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)\s?[x×]\b")

MONEY_FIELDS = ("billed_amount", "paid_amount", "predicted_paid_amount", "avg_claim_amount", "avg_billed")


@dataclass
class GroundingReport:
    checked: int = 0
    ungrounded: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"checked": self.checked, "ungrounded": self.ungrounded}


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _close(value: float, candidates: list[float], *, rel: float, abs_tol: float) -> bool:
    return any(abs(value - c) <= max(abs_tol, rel * abs(c)) for c in candidates)


def check_grounding(text: str, claim: dict[str, Any], signals: dict[str, Any], provider: dict | None = None) -> GroundingReport:
    sources = {**(provider or {}), **claim, **signals}
    money = [float(sources[k]) for k in MONEY_FIELDS if isinstance(sources.get(k), (int, float))]

    probabilities = [float(v) * 100 for v in (signals.get("risk_probabilities") or {}).values()]
    probabilities += [100 - p for p in probabilities]  # "5% high risk" vs "95% not high"
    if isinstance(signals.get("anomaly_recent_score"), (int, float)):
        probabilities.append(float(signals["anomaly_recent_score"]) * 100)

    ratios = []
    billed, predicted = claim.get("billed_amount"), signals.get("predicted_paid_amount")
    if isinstance(billed, (int, float)) and isinstance(predicted, (int, float)) and predicted > 0:
        ratios += [billed / predicted, predicted / billed]
    percentages = probabilities + [r * 100 for r in ratios] + [abs(r - 1) * 100 for r in ratios]

    report = GroundingReport()
    for match in _MONEY_RE.finditer(text):
        report.checked += 1
        value = _num(match.group(1))
        if not _close(value, money, rel=0.02, abs_tol=1.0):
            report.ungrounded.append(match.group(0).strip())
    for match in _PERCENT_RE.finditer(text):
        report.checked += 1
        if not _close(_num(match.group(1)), percentages, rel=0.0, abs_tol=1.5):
            report.ungrounded.append(match.group(0).strip())
    for match in _RATIO_RE.finditer(text):
        report.checked += 1
        if not _close(_num(match.group(1)), ratios, rel=0.05, abs_tol=0.1):
            report.ungrounded.append(match.group(0).strip())
    return report
