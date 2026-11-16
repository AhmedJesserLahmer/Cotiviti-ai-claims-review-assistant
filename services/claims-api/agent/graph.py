"""LangGraph agent that chains reasoning over ML signals for a claim and
produces an agentic recommendation.

Graph:
  fetch_claim_context -> run_ml_signals -> reasoning_node -> recommendation_node
  recommendation_node --(request_more_data, loops < 1)--> fetch_claim_context
  recommendation_node --(otherwise)--> persist_result -> END

All LLM work goes through ai_platform.ClaimReviewAI, which adds retries, timeouts,
circuit breakers, model fallback, guardrails, schema validation and a deterministic
fallback. The graph itself stays a pure orchestration of data, ML and AI steps.
"""

from langgraph.graph import END, StateGraph

from agent.state import AgentState
from ai_platform.audit import AIRunMetadata
from ai_platform.service import get_claim_review_ai
from db.mongo import db
from ml.inference import classify_claim, predict_payment

MAX_LOOPS = 1


async def fetch_claim_context(state: AgentState) -> AgentState:
    loops = state.get("loops", 0)
    window_days = 30 if loops == 0 else 90

    claim = await db["claims"].find_one({"claim_id": state["claim_id"]}, {"_id": 0})
    patient = await db["patients"].find_one({"patient_id": claim["patient_id"]}, {"_id": 0})
    provider = await db["providers"].find_one({"provider_id": claim["provider_id"]}, {"_id": 0})

    cursor = (
        db["provider_timeseries"]
        .find({"provider_id": provider["provider_id"]}, {"_id": 0})
        .sort("date", -1)
        .limit(window_days)
    )
    timeseries_window = await cursor.to_list(length=window_days)
    timeseries_window.reverse()

    return {
        **state,
        "claim": claim,
        "patient": patient,
        "provider": provider,
        "timeseries_window": timeseries_window,
    }


async def run_ml_signals(state: AgentState) -> AgentState:
    claim = state["claim"]
    patient = state["patient"]
    provider = state["provider"]
    timeseries_window = state["timeseries_window"]

    risk_label, risk_probabilities = classify_claim(claim, patient)
    predicted_paid = predict_payment(claim, provider.get("avg_claim_amount", claim["billed_amount"]))

    anomaly_days = [row for row in timeseries_window if row.get("is_anomaly")]
    most_recent = timeseries_window[-1] if timeseries_window else {}

    signals = {
        "predicted_risk_label": risk_label,
        "risk_probabilities": risk_probabilities,
        "predicted_paid_amount": predicted_paid,
        "provider_cluster_id": int(provider.get("cluster_id", -1)),
        "provider_cluster_label": provider.get("cluster_label", "Unknown"),
        "anomaly_flagged_days": len(anomaly_days),
        "anomaly_recent_score": round(float(most_recent.get("anomaly_score", 0.0)), 3),
        "is_recent_anomaly": bool(most_recent.get("is_anomaly", False)),
    }

    return {**state, "signals": signals}


async def reasoning_node(state: AgentState) -> AgentState:
    run = state.get("ai_run") or AIRunMetadata()
    reasoning = await get_claim_review_ai().reason(
        claim=state["claim"],
        provider=state["provider"],
        signals=state["signals"],
        run=run,
    )
    return {**state, "reasoning": reasoning, "ai_run": run}


async def recommendation_node(state: AgentState) -> AgentState:
    loops = state.get("loops", 0)
    run = state["ai_run"]
    decision = await get_claim_review_ai().recommend(
        claim=state["claim"],
        signals=state["signals"],
        reasoning=state["reasoning"],
        allow_more_data=loops < MAX_LOOPS,
        run=run,
    )
    return {
        **state,
        "recommendation": decision.recommendation,
        "recommendation_summary": decision.summary,
        "loops": loops + (1 if decision.recommendation == "request_more_data" else 0),
        "ai_run": run,
    }


async def persist_result(state: AgentState) -> AgentState:
    doc = {
        "claim_id": state["claim_id"],
        "signals": state["signals"],
        "reasoning": state["reasoning"],
        "recommendation": state["recommendation"],
        "recommendation_summary": state["recommendation_summary"],
        "loops": state.get("loops", 0),
    }
    await db["claim_analyses"].update_one(
        {"claim_id": state["claim_id"]}, {"$set": doc}, upsert=True
    )
    return state


def _route_after_recommendation(state: AgentState) -> str:
    if state["recommendation"] == "request_more_data" and state.get("loops", 0) <= MAX_LOOPS:
        return "fetch_claim_context"
    return "persist_result"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("fetch_claim_context", fetch_claim_context)
    graph.add_node("run_ml_signals", run_ml_signals)
    graph.add_node("reasoning_node", reasoning_node)
    graph.add_node("recommendation_node", recommendation_node)
    graph.add_node("persist_result", persist_result)

    graph.set_entry_point("fetch_claim_context")
    graph.add_edge("fetch_claim_context", "run_ml_signals")
    graph.add_edge("run_ml_signals", "reasoning_node")
    graph.add_edge("reasoning_node", "recommendation_node")
    graph.add_conditional_edges(
        "recommendation_node",
        _route_after_recommendation,
        {"fetch_claim_context": "fetch_claim_context", "persist_result": "persist_result"},
    )
    graph.add_edge("persist_result", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


async def analyze_claim(claim_id: str) -> dict:
    graph = get_graph()
    result = await graph.ainvoke({"claim_id": claim_id, "loops": 0, "ai_run": AIRunMetadata()})
    result["ai_run"].finish()
    return {
        "claim_id": result["claim_id"],
        "signals": result["signals"],
        "reasoning": result["reasoning"],
        "recommendation": result["recommendation"],
        "recommendation_summary": result["recommendation_summary"],
        "loops": result.get("loops", 0),
        "ai_metadata": result["ai_run"].model_dump(),
    }
