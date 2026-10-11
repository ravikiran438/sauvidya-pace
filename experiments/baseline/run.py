# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""CP3 baseline: PACE vs. telling each agent, with perfect listeners.

Every agent in both arms obeys everything it knows, exactly. The arms
differ only in what an agent knows and when:

- prompt: an agent the family set up was given the best possible prompt
  ("speak Telugu, contact only 09:00-11:00 or 16:00-18:00 Asia/Kolkata,
  at most 2 options, at most 3 contacts a day, pass this on to any agent
  you delegate to"), as it stood on the day it was set up. It counts its
  own contacts. An agent nobody set up knows nothing.
- pace: every agent speaks PACE. Before each contact it reads her current
  contract from her orchestrator, which also counts contacts across agents.

A referee then applies the PACE validators to every contact that reached
her, under the contract in force at that moment. Because the agents are
perfect, a PACE-arm zero is by construction: the experiment measures what
a prompt cannot carry, not how well an agent obeys. Obedience is the
second arm's job (a real model given the prompt).

Usage:
  uv run python experiments/baseline/run.py [--json]
  uv run python experiments/baseline/run.py --export-testbed DIR

``--export-testbed`` writes every scenario and arm as an a2a-testbed
scenario: each contact that reached her is one step, and each rule the
referee applied is an extension check the testbed runs on pace-mcp with
the verdict this script expects. The testbed agrees when every step
passes.
"""

from __future__ import annotations

import argparse
import heapq
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from pace.types import (
    AdaptiveInteractionContract,
    InteractionRules,
    PrincipalCapabilityProfile,
)
from pace.types.adaptive_interaction_contract import TimeWindow
from pace.validators import (
    ContactAttempt,
    DailyLimitError,
    OptionOverloadError,
    TimeWindowViolationError,
    acceptable_languages,
    interactions_remaining,
    validate_daily_limit,
    validate_option_count,
    validate_time_window,
)
from pace.validators.contract import principal_local_time
from pace.validators.enforcement import next_window_start

IST = ZoneInfo("Asia/Kolkata")
CHICAGO = ZoneInfo("America/Chicago")

PCP = PrincipalCapabilityProfile(
    principal_id="principal-te",
    version="v1",
    declared_at="2026-10-01T10:00:00+05:30",
    declared_by="guardian:son",
    language=[{"code": "te", "fluency": 1.0}, {"code": "en", "fluency": 0.3}],
    adaptations_required=["language:te"],
)


def contract(
    version: str,
    windows: tuple[tuple[str, str], ...] = (("09:00", "11:00"), ("16:00", "18:00")),
    max_options: int = 2,
    per_day: int = 3,
) -> AdaptiveInteractionContract:
    return AdaptiveInteractionContract(
        principal_id=PCP.principal_id,
        pcp_version=PCP.version,
        interaction_rules=InteractionRules(
            language="te",
            timezone="Asia/Kolkata",
            valid_time_windows=[TimeWindow(start=s, end=e) for s, e in windows],
            max_options_per_turn=max_options,
            max_interactions_per_day=per_day,
        ),
    )


AIC_V1 = contract("v1")
# The guardian narrows the contract: mornings only, one option at a time.
AIC_V2 = contract("v2", windows=(("09:00", "11:00"),), max_options=1)


def ist(day: int, h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, day, h, m, tzinfo=IST)


@dataclass(frozen=True)
class Agent:
    id: str
    languages: frozenset[str]
    default_language: str = "en"
    told_at: datetime | None = None  # when the family gave it the prompt
    told_by: str | None = None  # gets the prompt forwarded by this agent


@dataclass(frozen=True)
class Intent:
    agent: str
    at: datetime  # zone-aware, on the agent's own clock
    options: int


@dataclass
class Scenario:
    name: str
    kind: str  # "control": a prompt should tie; "structural": it cannot
    why: str
    agents: list[Agent]
    intents: list[Intent]
    contracts: list[tuple[datetime, AdaptiveInteractionContract]] = field(
        default_factory=lambda: [(ist(1, 0), AIC_V1)]
    )
    gatekeeper: bool = False  # every contact routes through one prompted hub

    def contract_at(self, at: datetime) -> AdaptiveInteractionContract:
        current = self.contracts[0][1]
        for since, c in self.contracts:
            if since <= at:
                current = c
        return current


@dataclass(frozen=True)
class Contact:
    agent: str
    at: datetime
    language: str
    options: int


@dataclass
class Outcome:
    intents: int = 0
    delivered: int = 0
    violating: int = 0
    deferred: int = 0
    escalated: int = 0
    max_delay_hours: float = 0.0
    by_rule: dict[str, int] = field(default_factory=dict)


TE = frozenset({"te", "en"})
EN = frozenset({"en"})


def scenarios() -> list[Scenario]:
    week = range(12, 15)  # Mon 12 to Wed 14 October 2026
    return [
        Scenario(
            "told directly, same clock",
            "control",
            "One agent the family set up, on her clock, wants 14:00 and four options.",
            [Agent("pharmacy", TE, told_at=ist(1, 0))],
            [Intent("pharmacy", ist(d, 14), 4) for d in week],
        ),
        Scenario(
            "told directly, another clock",
            "control",
            "The prompt names her time zone, so an agent on Chicago time converts.",
            [Agent("booking", TE, told_at=ist(1, 0))],
            [Intent("booking", datetime(2026, 10, d, 9, tzinfo=CHICAGO), 3) for d in week],
        ),
        Scenario(
            "delegated sub-agent",
            "control",
            "The prompt says to pass it on, and the booking agent does.",
            [
                Agent("booking", TE, told_at=ist(1, 0)),
                Agent("clinic-scheduler", TE, told_by="booking"),
            ],
            [Intent("clinic-scheduler", ist(d, 13), 3) for d in week],
        ),
        Scenario(
            "one prompted gatekeeper",
            "control",
            "Every contact, even from agents nobody set up, routes through one hub "
            "the family keeps up to date, so one prompt sees everything.",
            [
                Agent("pharmacy", TE, told_at=ist(1, 0)),
                Agent("booking", TE, told_at=ist(1, 0)),
                Agent("bank", TE),
            ],
            [Intent(a, ist(d, h), 3) for d in week for a in ("pharmacy", "booking", "bank") for h in (9, 16)],
            contracts=[(ist(1, 0), AIC_V1), (ist(13, 0), AIC_V2)],
            gatekeeper=True,
        ),
        Scenario(
            "never told",
            "structural",
            "Her bank's agent was never set up by the family; nobody could give it a prompt.",
            [Agent("bank", TE)],
            [Intent("bank", ist(d, 13, 30), 4) for d in week],
        ),
        Scenario(
            "three agents, one day",
            "structural",
            "Each agent keeps the limit of three for its own contacts; none sees the others.",
            [Agent(a, TE, told_at=ist(1, 0)) for a in ("pharmacy", "booking", "family-reminder")],
            [Intent(a, ist(d, h), 2) for d in week for a in ("pharmacy", "booking", "family-reminder") for h in (9, 16)],
        ),
        Scenario(
            "contract changed after telling",
            "structural",
            "The guardian narrows the contract on the 13th; agents set up earlier keep the old prompt.",
            [Agent("pharmacy", TE, told_at=ist(1, 0)), Agent("booking", TE, told_at=ist(1, 0))],
            [Intent(a, ist(d, 16, 30), 2) for d in week for a in ("pharmacy", "booking")],
            contracts=[(ist(1, 0), AIC_V1), (ist(13, 0), AIC_V2)],
        ),
    ]


def knowledge(
    scenario: Scenario, arm: str, agent: Agent, at: datetime
) -> AdaptiveInteractionContract | None:
    """What contract this agent acts on at ``at``, or None if it knows nothing."""
    if arm == "pace" or scenario.gatekeeper:
        return scenario.contract_at(at)
    agents = {a.id: a for a in scenario.agents}
    told_at = agent.told_at
    if told_at is None and agent.told_by is not None:
        told_at = agents[agent.told_by].told_at
    return None if told_at is None else scenario.contract_at(told_at)


def next_day_window(c: AdaptiveInteractionContract, at: datetime) -> datetime | None:
    local = principal_local_time(c, at)
    midnight = datetime.combine(local.date() + timedelta(days=1), time(0, 0), tzinfo=local.tzinfo)
    return next_window_start(c, midnight - timedelta(minutes=1))


def simulate(scenario: Scenario, arm: str) -> tuple[list[Contact], Outcome]:
    agents = {a.id: a for a in scenario.agents}
    outcome = Outcome(intents=len(scenario.intents))
    queue = [(i.at, n, i.agent, i.options, i.at) for n, i in enumerate(scenario.intents)]
    heapq.heapify(queue)
    seq = len(queue)
    delivered: list[Contact] = []
    shared = arm == "pace" or scenario.gatekeeper

    while queue:
        at, _, agent_id, options, wanted = heapq.heappop(queue)
        agent = agents[agent_id]
        known = knowledge(scenario, arm, agent, at)
        if known is None:
            delivered.append(Contact(agent_id, at, agent.default_language, options))
            continue

        usable = agent.languages & acceptable_languages(PCP, known.interaction_rules.min_language_fluency)
        if not usable:
            outcome.escalated += 1
            continue

        later = None
        try:
            validate_time_window(known, at)
        except TimeWindowViolationError:
            later = next_window_start(known, at)
        if later is None:
            counted = [
                ContactAttempt(c.at, responded=True)
                for c in delivered
                if shared or c.agent == agent_id
            ]
            if interactions_remaining(known, counted, at) == 0:
                later = next_day_window(known, at)
        if later is not None:
            outcome.deferred += 1
            seq += 1
            heapq.heappush(queue, (later, seq, agent_id, options, wanted))
            continue

        delivered.append(
            Contact(agent_id, at, sorted(usable)[0], min(options, known.interaction_rules.max_options_per_turn))
        )
        outcome.max_delay_hours = max(outcome.max_delay_hours, (at - wanted).total_seconds() / 3600)

    outcome.delivered = len(delivered)
    for n, contact in enumerate(delivered):
        broken = referee(scenario, contact, delivered[:n])
        if broken:
            outcome.violating += 1
        for rule in broken:
            outcome.by_rule[rule] = outcome.by_rule.get(rule, 0) + 1
    return delivered, outcome


def referee(scenario: Scenario, contact: Contact, before: list[Contact]) -> list[str]:
    """Rules this contact broke, judged under the contract in force when it reached her."""
    c = scenario.contract_at(contact.at)
    broken = []
    checks = (
        ("AIC-1 window", lambda: validate_time_window(c, contact.at), TimeWindowViolationError),
        (
            "AIC-1 daily limit",
            lambda: validate_daily_limit(c, [ContactAttempt(b.at, True) for b in before], contact.at),
            DailyLimitError,
        ),
        ("AIC-2 options", lambda: validate_option_count(c, contact.options), OptionOverloadError),
    )
    for rule, check, error in checks:
        try:
            check()
        except error:
            broken.append(rule)
    if contact.language not in acceptable_languages(PCP, c.interaction_rules.min_language_fluency):
        broken.append("IM-2 language")
    return broken


def per_1000(violating: int, intents: int) -> float:
    return round(1000 * violating / intents, 1) if intents else 0.0


def run() -> dict:
    rows = []
    totals = {(arm, kind): Outcome() for arm in ("prompt", "pace") for kind in ("control", "structural")}
    for s in scenarios():
        row = {"scenario": s.name, "kind": s.kind, "why": s.why}
        for arm in ("prompt", "pace"):
            _, o = simulate(s, arm)
            row[arm] = {
                "intents": o.intents,
                "delivered": o.delivered,
                "violating": o.violating,
                "per_1000": per_1000(o.violating, o.intents),
                "deferred": o.deferred,
                "escalated": o.escalated,
                "max_delay_hours": round(o.max_delay_hours, 1),
                "by_rule": dict(sorted(o.by_rule.items())),
            }
            t = totals[(arm, s.kind)]
            t.intents += o.intents
            t.violating += o.violating
        rows.append(row)
    summary = {
        f"{arm}/{kind}": per_1000(t.violating, t.intents) for (arm, kind), t in totals.items()
    }
    return {"scenarios": rows, "per_1000": summary}


def render(result: dict) -> str:
    lines = [
        "Violations reaching her per 1,000 contact intents (perfect listeners)",
        "",
        f"{'':34}{'prompt':>10}{'pace':>10}",
    ]
    for kind in ("control", "structural"):
        lines.append(
            f"{kind + ' cases':34}{result['per_1000']['prompt/' + kind]:>10}{result['per_1000']['pace/' + kind]:>10}"
        )
    lines += ["", f"{'scenario':34}{'prompt':>10}{'pace':>10}  prompt-arm rules broken"]
    for row in result["scenarios"]:
        rules = ", ".join(f"{k} x{v}" for k, v in row["prompt"]["by_rule"].items()) or "-"
        lines.append(
            f"{row['scenario']:34}{row['prompt']['per_1000']:>10}{row['pace']['per_1000']:>10}  {rules}"
        )
    lines += ["", "The cost of keeping the rules: deferrals, escalations, longest wait (hours)", ""]
    lines.append(f"{'scenario':34}{'prompt':>16}{'pace':>16}")
    for row in result["scenarios"]:
        p, q = row["prompt"], row["pace"]
        cost = lambda o: f"{o['deferred']}/{o['escalated']}/{o['max_delay_hours']}"
        lines.append(f"{row['scenario']:34}{cost(p):>16}{cost(q):>16}")
    return "\n".join(lines)


# --- a2a-testbed export ----------------------------------------------------

PACE_URI = "https://ravikiran438.github.io/sauvidya-pace/v1"
PACE_RELEASE = "v0.2.0"
PRINCIPAL_AGENT = "her-orchestrator"


def _verdict(rule: str, broken: list[str]) -> str:
    return "violation" if rule in broken else "ok"


def contact_checks(scenario: Scenario, contact: Contact, before: list[Contact]) -> list[dict]:
    """The referee's four rules as pace-mcp tool calls, with the verdict
    the referee reached. The testbed re-asks the server and compares."""
    c = scenario.contract_at(contact.at)
    contract = c.model_dump(mode="json", exclude_none=True)
    at = contact.at.isoformat()
    broken = referee(scenario, contact, before)
    modality = {
        "agent_id": contact.agent,
        "principal_id": PCP.principal_id,
        "pcp_version": PCP.version,
        "modality_plan": {"primary_channel": "voice", "language": contact.language},
    }
    return [
        {
            "tool": "validate_time_window",
            "args": {"contract": contract, "at": at},
            "verdict": _verdict("AIC-1 window", broken),
        },
        {
            "tool": "validate_daily_limit",
            "args": {
                "contract": contract,
                "prior_contacts": [{"at": b.at.isoformat(), "responded": True} for b in before],
                "at": at,
            },
            "verdict": _verdict("AIC-1 daily limit", broken),
        },
        {
            "tool": "validate_option_count",
            "args": {"contract": contract, "options_presented": contact.options},
            "verdict": _verdict("AIC-2 options", broken),
        },
        {
            "tool": "validate_language_match",
            "args": {
                "modality": modality,
                "pcp": PCP.model_dump(mode="json", exclude_none=True),
                "contract": contract,
            },
            "verdict": _verdict("IM-2 language", broken),
        },
    ]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _card(name: str, description: str) -> dict:
    return {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "supportedInterfaces": [{"protocolBinding": "JSONRPC", "url": "http://127.0.0.1:0"}],
        "capabilities": {},
        "skills": [{"id": "contact", "name": "Contact", "description": description, "tags": ["cp3"]}],
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
    }


def testbed_scenario(scenario: Scenario, arm: str) -> tuple[dict, dict]:
    """(scenario document, expected summary) for one scenario and arm."""
    delivered, outcome = simulate(scenario, arm)
    agents = [{"id": PRINCIPAL_AGENT, "card": f"cards/{PRINCIPAL_AGENT}.json", "runtime": "python_inproc", "role": "principal"}]
    agents += [
        {"id": a.id, "card": f"cards/{a.id}.json", "runtime": "python_inproc", "role": "service_provider"}
        for a in scenario.agents
    ]
    flow = []
    for n, contact in enumerate(delivered):
        flow.append(
            {
                "from": contact.agent,
                "to": PRINCIPAL_AGENT,
                "action": "contact",
                "message": (
                    f"contact {n + 1}: {contact.at.isoformat()} on the agent's clock, "
                    f"{contact.language}, {contact.options} option(s)"
                ),
                "expect": {
                    "response_status": "2xx",
                    "extensions": {PACE_URI: contact_checks(scenario, contact, delivered[:n])},
                },
            }
        )
    doc = {
        "name": f"CP3 {scenario.name} ({arm} arm)",
        "description": (
            f"{scenario.kind} case. {scenario.why} Generated by "
            "experiments/baseline/run.py --export-testbed; do not hand-edit."
        ),
        "mode": "sim",
        "mcp_delegates": "mcp-delegates.yaml",
        "agents": agents,
        "flow": flow,
    }
    expected = {
        "scenario": scenario.name,
        "kind": scenario.kind,
        "arm": arm,
        "intents": outcome.intents,
        "steps": outcome.delivered,
        "violating_steps": outcome.violating,
        "per_1000": per_1000(outcome.violating, outcome.intents),
    }
    return doc, expected


def export_testbed(out: Path) -> list[Path]:
    """Write every scenario and arm for a2a-testbed. JSON is valid YAML."""
    (out / "cards").mkdir(parents=True, exist_ok=True)
    written = []

    def write(rel: str, data: dict) -> None:
        path = out / rel
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    write(f"cards/{PRINCIPAL_AGENT}.json", _card(PRINCIPAL_AGENT, "The principal's own agent; receives every contact."))
    seen = set()
    for s in scenarios():
        for a in s.agents:
            if a.id not in seen:
                seen.add(a.id)
                write(f"cards/{a.id}.json", _card(a.id, f"Agent that contacts the principal ({a.id})."))
    (out / "mcp-delegates.yaml").write_text(
        "# pace-mcp pinned to the release the expected verdicts were computed with.\n"
        "delegates:\n"
        f"  - uri: {PACE_URI}\n"
        f"    command: [uvx, --from, 'pace[mcp] @ git+https://github.com/ravikiran438/sauvidya-pace@{PACE_RELEASE}', pace-mcp]\n"
        "    card_validator_tool: validate_accessibility_service_ref\n",
        encoding="utf-8",
    )
    written.append(out / "mcp-delegates.yaml")
    summary = []
    for s in scenarios():
        for arm in ("prompt", "pace"):
            doc, expected = testbed_scenario(s, arm)
            expected["file"] = f"{_slug(s.name)}.{arm}.yaml"
            write(expected["file"], doc)
            summary.append(expected)
    write("expected.json", {"pace_release": PACE_RELEASE, "scenarios": summary})
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Print the full result as JSON.")
    parser.add_argument("--export-testbed", type=Path, metavar="DIR", help="Write a2a-testbed scenarios to DIR.")
    args = parser.parse_args(argv)
    if args.export_testbed:
        files = export_testbed(args.export_testbed)
        print(f"wrote {len(files)} files to {args.export_testbed}")
        return 0
    result = run()
    print(json.dumps(result, indent=2, default=str) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
