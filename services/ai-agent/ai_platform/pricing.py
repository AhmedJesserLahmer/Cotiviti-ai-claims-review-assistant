"""Token pricing used for per-analysis cost estimates (USD per 1M tokens).

Defaults are list prices at the time of writing and only drive *estimates* in the audit
trail and metrics; override them with ``AI_MODEL_PRICES`` without a code change, e.g.
``AI_MODEL_PRICES="llama-3.3-70b-versatile=0.59/0.79;my-model=1.0/2.0"``.
"""

from __future__ import annotations

DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def parse_prices(raw: str) -> dict[str, tuple[float, float]]:
    prices: dict[str, tuple[float, float]] = {}
    for entry in filter(None, (part.strip() for part in raw.split(";"))):
        try:
            model, rates = entry.split("=", 1)
            prompt_rate, completion_rate = (float(x) for x in rates.split("/", 1))
        except ValueError as exc:
            raise ValueError(f"invalid AI_MODEL_PRICES entry {entry!r}; expected model=in/out") from exc
        prices[model.strip()] = (prompt_rate, completion_rate)
    return prices


def estimate_cost(
    model: str, prompt_tokens: int, completion_tokens: int, prices: dict[str, tuple[float, float]]
) -> float:
    prompt_rate, completion_rate = prices.get(model, (0.0, 0.0))
    return (prompt_tokens * prompt_rate + completion_tokens * completion_rate) / 1_000_000
