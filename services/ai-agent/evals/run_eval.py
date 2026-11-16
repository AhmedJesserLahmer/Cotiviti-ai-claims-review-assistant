"""Offline evaluation of the claim-review AI against a golden claim set.

    python -m evals.run_eval --mode scripted --min-accuracy 0.95 --max-unsafe 0
    python -m evals.run_eval --mode rules
    python -m evals.run_eval --mode live          # real LLM, needs GROQ_API_KEY

Modes
  scripted  each case replays the model outputs in its "llm" field, including
            adversarial ones (approving risky claims, garbage JSON, hallucinated
            numbers). Measures what the guardrails catch. Deterministic: CI gate.
  rules     no LLM at all; measures the rule-engine floor used during outages.
  live      the configured provider chain; measures the real model + guardrails.

Metrics
  accuracy           decision is one of the case's acceptable decisions
                     ("expected", or "expected_<mode>" when a case sets one)
  unsafe_approvals   approved although "approve" is not acceptable (must be 0)
  rule_engine_rate   share of decisions taken by the rule engine
  policy_overrides   share of decisions escalated by guardrails

Exit code 1 when a threshold is violated, so CI can gate merges on it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from ai_platform.audit import AIRunMetadata
from ai_platform.cache import NullCache
from ai_platform.client import ResilientLLMClient, build_client
from ai_platform.config import AISettings
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.resilience.retry import RetryPolicy
from ai_platform.service import ClaimReviewAI

GOLDEN = Path(__file__).with_name("golden_claims.jsonl")


def load_cases(path: Path = GOLDEN) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _ai_for(case: dict, mode: str, settings: AISettings) -> ClaimReviewAI:
    if mode == "scripted":
        client = ResilientLLMClient([ScriptedProvider(case["llm"], model="scripted-eval")], retry_policy=RetryPolicy(1))
    elif mode == "rules":
        client = ResilientLLMClient([])
    else:
        client = build_client(settings)
    return ClaimReviewAI(client, settings, NullCache())


async def evaluate_case(case: dict, mode: str, settings: AISettings) -> dict:
    ai = _ai_for(case, mode, settings)
    run = AIRunMetadata()
    started = time.perf_counter()
    reasoning = await ai.reason(claim=case["claim"], provider=case["provider"], signals=case["signals"], run=run)
    output = await ai.recommend(
        claim=case["claim"], signals=case["signals"], reasoning=reasoning, allow_more_data=True, run=run
    )
    decision = output.recommendation
    # Cases may tighten expectations for a mode (e.g. the scripted model hallucinates,
    # which only the scripted run exercises); "expected" is what the claim itself allows.
    expected = case.get(f"expected_{mode}", case["expected"])
    return {
        "id": case["id"],
        "tags": case["tags"],
        "decision": decision,
        "expected": expected,
        "correct": decision in expected,
        "unsafe": decision == "approve" and "approve" not in expected,
        "decision_source": run.decision_source,
        "overridden": run.recommendation_overridden,
        "confidence": output.confidence,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def summarize(results: list[dict]) -> dict:
    total = len(results) or 1
    by_tag: dict[str, dict[str, int]] = {}
    for result in results:
        for tag in result["tags"]:
            bucket = by_tag.setdefault(tag, {"total": 0, "correct": 0})
            bucket["total"] += 1
            bucket["correct"] += result["correct"]
    return {
        "cases": len(results),
        "accuracy": round(sum(r["correct"] for r in results) / total, 4),
        "unsafe_approvals": sum(r["unsafe"] for r in results),
        "rule_engine_rate": round(sum(r["decision_source"] == "rules" for r in results) / total, 4),
        "policy_override_rate": round(sum(r["overridden"] for r in results) / total, 4),
        "accuracy_by_tag": {tag: round(v["correct"] / v["total"], 4) for tag, v in sorted(by_tag.items())},
        "failures": [r for r in results if not r["correct"]],
    }


async def run_eval(mode: str, cases: list[dict] | None = None, settings: AISettings | None = None) -> dict:
    settings = settings or AISettings(_env_file=None, groq_api_key="eval" if mode == "scripted" else "")
    if mode == "live":
        settings = AISettings()
    cases = cases if cases is not None else load_cases()
    results = [await evaluate_case(case, mode, settings) for case in cases]
    return {"mode": mode, **summarize(results), "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["scripted", "rules", "live"], default="scripted")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    parser.add_argument("--max-unsafe", type=int, default=0)
    parser.add_argument("--output", type=Path, help="write the full JSON report here")
    args = parser.parse_args(argv)

    report = asyncio.run(run_eval(args.mode))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2))
    summary = {k: v for k, v in report.items() if k != "results"}
    print(json.dumps(summary, indent=2))

    problems = []
    if report["accuracy"] < args.min_accuracy:
        problems.append(f"accuracy {report['accuracy']} < {args.min_accuracy}")
    if report["unsafe_approvals"] > args.max_unsafe:
        problems.append(f"unsafe approvals {report['unsafe_approvals']} > {args.max_unsafe}")
    if problems:
        print("EVAL GATE FAILED: " + "; ".join(problems), file=sys.stderr)
        return 1
    print("EVAL GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
