from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    claim_id: str
    claim: dict[str, Any]
    patient: dict[str, Any]
    provider: dict[str, Any]
    timeseries_window: list[dict[str, Any]]
    signals: dict[str, Any]
    reasoning: str
    recommendation: str
    recommendation_summary: str
    loops: int
