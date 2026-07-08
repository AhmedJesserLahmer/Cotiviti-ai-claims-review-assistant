"""LangGraph agent that chains reasoning over ML signals for a claim and
produces an agentic recommendation via Groq.

Graph:
  fetch_claim_context -> run_ml_signals -> reasoning_node -> recommendation_node
  recommendation_node --(request_more_data, loops < 1)--> fetch_claim_context
  recommendation_node --(otherwise)--> persist_result -> END
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from agent.state import AgentState
from core.config import settings
from db.mongo import db
from ml.inference import classify_claim, predict_payment

MAX_LOOPS = 1

_llm = None


def get_llm() -> ChatGroq:
    """Lazily construct the Groq client so the backend can boot without a key;
    it is only required when a claim is actually analyzed."""
    global _llm
    if _llm is None:
        if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your environment / .env to run AI analysis."
            )
        _llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.2)
    return _llm


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
    claim, signals, provider = state["claim"], state["signals"], state["provider"]

    prompt = (
        "You are a healthcare claims review analyst. Reason step-by-step (chain of "
        "thought) over the ML model outputs below for a single claim, considering "
        "treatment appropriateness, payment amount, provider behavior pattern, and "
        "billing anomaly history. Keep it to 4-6 short numbered steps of reasoning, "
        "plain text, no markdown headers.\n\n"
        f"Claim: {json.dumps(claim, default=str)}\n"
        f"Provider: {provider.get('name')} ({provider.get('specialty')}, {provider.get('region')})\n"
        f"ML Signals: {json.dumps(signals, default=str)}\n"
    )

    response = await get_llm().ainvoke([
        SystemMessage(content="You produce concise, numbered chain-of-thought reasoning for claims review."),
        HumanMessage(content=prompt),
    ])

    return {**state, "reasoning": response.content}


async def recommendation_node(state: AgentState) -> AgentState:
    loops = state.get("loops", 0)

    prompt = (
        "Based on the reasoning below, decide a final action for this healthcare claim. "
        "Respond with ONLY a JSON object with keys 'recommendation' (one of: "
        "'approve', 'flag_for_review', 'request_more_data') and 'summary' (one sentence "
        "explaining the decision).\n\n"
        f"Reasoning:\n{state['reasoning']}\n"
        f"ML Signals: {json.dumps(state['signals'], default=str)}\n"
    )
    if loops >= MAX_LOOPS:
        prompt += "\nNote: additional data has already been fetched once; you must not request more data again."

    response = await get_llm().ainvoke([
        SystemMessage(content="You are a decisive claims review agent. Reply with strict JSON only."),
        HumanMessage(content=prompt),
    ])

    try:
        text = response.content.strip().strip("`").removeprefix("json").strip()
        parsed = json.loads(text)
        recommendation = parsed.get("recommendation", "flag_for_review")
        summary = parsed.get("summary", "")
    except (json.JSONDecodeError, AttributeError):
        recommendation, summary = "flag_for_review", "Could not parse agent output; defaulting to manual review."

    if recommendation not in {"approve", "flag_for_review", "request_more_data"}:
        recommendation = "flag_for_review"
    if loops >= MAX_LOOPS and recommendation == "request_more_data":
        recommendation = "flag_for_review"

    return {
        **state,
        "recommendation": recommendation,
        "recommendation_summary": summary,
        "loops": loops + (1 if recommendation == "request_more_data" else 0),
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
    result = await graph.ainvoke({"claim_id": claim_id, "loops": 0})
    return {
        "claim_id": result["claim_id"],
        "signals": result["signals"],
        "reasoning": result["reasoning"],
        "recommendation": result["recommendation"],
        "recommendation_summary": result["recommendation_summary"],
        "loops": result.get("loops", 0),
    }
