# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""CP3 baseline: the claim the experiment makes, as tests.

Perfect listeners in both arms: a prompt ties wherever it can reach the
agent with current information, and loses only where it cannot.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "experiments" / "baseline" / "run.py"
_spec = importlib.util.spec_from_file_location("baseline_run", _PATH)
baseline = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = baseline  # dataclasses resolve annotations through it
_spec.loader.exec_module(baseline)

SCENARIOS = baseline.scenarios()


def _ids(s):
    return s.name


@pytest.mark.parametrize("scenario", SCENARIOS, ids=_ids)
def test_pace_arm_has_no_violations(scenario):
    _, outcome = baseline.simulate(scenario, "pace")
    assert outcome.violating == 0


@pytest.mark.parametrize("scenario", SCENARIOS, ids=_ids)
def test_every_intent_is_delivered_or_escalated(scenario):
    for arm in ("prompt", "pace"):
        _, outcome = baseline.simulate(scenario, arm)
        assert outcome.delivered + outcome.escalated == outcome.intents, arm


@pytest.mark.parametrize("scenario", [s for s in SCENARIOS if s.kind == "control"], ids=_ids)
def test_a_good_prompt_ties_on_controls(scenario):
    _, prompt = baseline.simulate(scenario, "prompt")
    _, pace = baseline.simulate(scenario, "pace")
    assert prompt.violating == pace.violating == 0


@pytest.mark.parametrize("scenario", [s for s in SCENARIOS if s.kind == "structural"], ids=_ids)
def test_a_prompt_loses_only_where_it_cannot_reach(scenario):
    _, prompt = baseline.simulate(scenario, "prompt")
    assert prompt.violating > 0


def test_the_referee_is_independent_of_the_arm():
    """Same contact, same verdict: the referee reads only the contact and
    the contract in force when it reached her."""
    s = next(x for x in SCENARIOS if x.name == "never told")
    contact = baseline.Contact("bank", baseline.ist(12, 13, 30), "en", 4)
    assert baseline.referee(s, contact, []) == ["AIC-1 window", "AIC-2 options", "IM-2 language"]


def test_both_kinds_are_present():
    kinds = {s.kind for s in SCENARIOS}
    assert kinds == {"control", "structural"}


def test_export_writes_every_scenario_and_arm(tmp_path):
    baseline.export_testbed(tmp_path)
    import json

    expected = json.loads((tmp_path / "expected.json").read_text())
    assert expected["pace_release"] == baseline.PACE_RELEASE
    assert len(expected["scenarios"]) == 2 * len(SCENARIOS)
    for entry in expected["scenarios"]:
        doc = json.loads((tmp_path / entry["file"]).read_text())
        assert len(doc["flow"]) == entry["steps"]
        for agent in doc["agents"]:
            assert (tmp_path / agent["card"]).exists()


def test_exported_verdicts_match_the_mcp_server():
    """The verdicts the testbed will compare are the ones pace-mcp returns."""
    pytest.importorskip("mcp")
    import json

    from pace.mcp_server.tools import HANDLERS

    for scenario in SCENARIOS:
        for arm in ("prompt", "pace"):
            doc, expected = baseline.testbed_scenario(scenario, arm)
            violating = 0
            for step in doc["flow"]:
                checks = step["expect"]["extensions"][baseline.PACE_URI]
                for check in checks:
                    answer = json.loads(HANDLERS[check["tool"]](check["args"]))
                    got = "ok" if answer["ok"] else "violation"
                    assert got == check["verdict"], (scenario.name, arm, check["tool"], answer)
                violating += any(c["verdict"] == "violation" for c in checks)
            assert violating == expected["violating_steps"]
