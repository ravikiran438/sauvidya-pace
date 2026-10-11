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
