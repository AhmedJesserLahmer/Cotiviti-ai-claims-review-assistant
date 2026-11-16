"""The evaluation gate itself runs in CI through these tests (scripted + rules modes)."""

import pytest

from evals.run_eval import load_cases, main, run_eval


def test_golden_set_is_well_formed():
    cases = load_cases()
    assert len(cases) >= 20 and len({c["id"] for c in cases}) == len(cases)
    allowed = {"approve", "flag_for_review", "request_more_data"}
    for case in cases:
        assert set(case["expected"]) <= allowed and case["llm"], case["id"]


@pytest.mark.parametrize("mode", ["scripted", "rules"])
async def test_no_unsafe_approvals(mode):
    report = await run_eval(mode)
    assert report["unsafe_approvals"] == 0, report["failures"]
    assert report["accuracy"] == 1.0, report["failures"]


async def test_guardrails_are_exercised_in_scripted_mode():
    report = await run_eval("scripted")
    assert report["policy_override_rate"] >= 0.3  # adversarial approvals were escalated
    assert 0 < report["rule_engine_rate"] < 1


def test_cli_gate_exit_codes(tmp_path, capsys):
    assert main(["--mode", "rules", "--min-accuracy", "0.9", "--output", str(tmp_path / "r.json")]) == 0
    assert (tmp_path / "r.json").exists()
    assert main(["--mode", "rules", "--min-accuracy", "1.01"]) == 1
