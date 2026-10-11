# Checkpoints

Each checkpoint: a claim, test-shaped exits, its perturbation round, and
the gate for the next one. Status marks: ✅, ✅ (fixture), pending.

## CP1 — The reference surface says only what it can show ✅

**Claim.** Every statement in the README, the manifests and the module
headers is backed by a test, a model check, or is labeled as unchecked.
The paper's worked example behaves as the paper says: an English call to
a Telugu-pinned principal is rejected, with the next step named.

- **Sample:** the README quick start (output checked against the README).
- **Unit:** `uv run pytest` — 192 tests on Python 3.14.
- **e2e:** `pace-mcp` over stdio (20 tools, `--doctor` OK); a PACE
  AgentCard validated by `a2a-testbed validate` and `card` against the
  published manifest ✅ (fixture: hand-written card).
- **Models:** `scripts/check-models.sh`

  | Config | Distinct states |
  |---|---|
  | `Pace.cfg` | 40,760 |
  | `Pace-CrossOrchestrator.cfg` | 8,249,080 |
  | `AugmentationProfile.cfg` | 4,048,527 |
  | `AugmentationProfile-Liveness.cfg` | 6,606 |

  4 reachability witnesses violated as expected; 2 of 2 mutants caught.
- **Perturbation round 1:** 18 questions — 8 bug · 4 gap · 2 ok · 4 open.
  See [docs/perturbations.md](docs/perturbations.md).

**Gate for CP2:** how many contract fields have no reader? Measured by
`uv run python scripts/contract-readers.py`: **13 of 20** at CP1 (first
reported as 12 of 18, a hand-count error). CP2 is justified until that is
0, or each remaining field is documented as an instruction to the agent
with a test that a modality honors it.

## CP2 — The contract is honored end to end ✅ (fixture)

**Claim.** An agent's plan cannot quietly violate the contract it was
computed under; time windows and the daily limit mean the principal's
local time; every contract field has a reader and every field the paper
names exists or was removed on purpose; a violation reaches the guardian
with enough to act on.

- **Sample:** `test_guardian_story_from_consumer_md` produces the guardian
  story's notification (18:40 IST / 08:10 CDT, next contact 09:00 IST).
- **Unit:** `uv run pytest` — 256 tests.
- **e2e:** `pace-mcp` over stdio, 25 tools; a2a-testbed validates the
  card against the published manifest and rejects the old channel
  vocabulary.
- **Contract readers:** `uv run python scripts/contract-readers.py` —
  0 of 20 fields unread (13 at CP1), 0 paper fields missing (4 before
  AIC-3), 2 removed on purpose. Runs in CI.
- **What was built:** time zones (AIC-1), daily limit per principal
  (AIC-1), non-response policy (AIC-3), enforcement and the guardian
  notification (AIC-4), plan vs. contract (AIC-5), channels and fallback
  (IM-1). Cut: `guardian_cc`, `escalation_on_confusion`.
- **Perturbation round 2:** 18 questions — 6 bug · 4 gap · 8 ok · 0 open.
  Round 1's last three opens (16–18) closed here.
- **Fixture, not real surface:** no agent network or guardian app runs
  these stories yet; that is CP5.

**Gate for CP3:** does PACE beat prompt-level accommodation on cases a
prompt cannot see? Measured, not argued, before more protocol is added.

## CP3 — Baseline: PACE vs. telling the agent (in progress)

**Claim, narrowed by the measurement.** A good prompt ties PACE wherever
it can reach the agent with current information: one agent on her clock,
an agent on another clock (the prompt names her time zone), a sub-agent
(the prompt is passed on), every contact routed through one hub the
family keeps current. PACE stops violations a prompt lets through in
three cases: an agent nobody set up, several agents sharing one daily
limit, and a contract changed after the agents were told.

- **Arm 1, perfect listeners ✅:**
  [`experiments/baseline/`](experiments/baseline/). Every agent in both
  arms obeys everything it knows, so the PACE zero is by construction;
  the arm measures what a prompt cannot carry, not obedience. Runs in CI;
  `tests/test_baseline.py` holds the claim: controls tie, structural cases
  differ, the PACE arm has no violations, every intent is delivered or
  escalated.
- **The number:** violations reaching her per 1,000 contact intents, per
  scenario and per kind (control / structural). The overall figure
  depends on the scenario mix. Commit the script, not the number.
- **Cost, reported beside it:** deferrals, escalations and the longest
  wait. Six asks a day against a limit of three leave the last request
  waiting 65 hours. Which request goes first is not PACE's call
  (perturbation #39); the experiment queues first come, first served.
- **Arm 2, a real model given the prompt:** pending. Measures obedience.
- **a2a-testbed:** pending. The same scenarios as agents over A2A, which
  also checks the testbed against a known answer.
- **Perturbation round 3:** see [docs/perturbations.md](docs/perturbations.md).

**Gate for CP4:** the baseline holds on the structural cases in both
arms, and the a2a-testbed run agrees with the script.

## CP4 — Cost (pending)

**Claim.** The cost of PACE per interaction is published and moves when
the code does.

- `scripts/measure-cost.py`, computed from the real types: bytes per
  AgentCard entry, annotation and violation notice; validation latency per
  interaction; extra round trips (PCP delivery, AIC fetch).

## CP5 — The principal's story runs (pending)

**Claim.** The principal story in [docs/consumer.md](docs/consumer.md)
runs on an agent network, recorded as the demo: routed to a Telugu
sub-agent, two options, a capacity check, a blocked sundown call, a
guardian notification.

## Roadmap

- Tag v0.2.0 and pin docs to it.
- Paper: §3.2 (IM-2, fallback ladder, CCC-4), §4.4 (keyed digests), §7
  (what TLC checks), figures 1 and 2 (annotation design).
- Alt text for figures on the protocol-stack site.
- EmergencyRoute: declared, consented, tiered, local to the principal.
  Takes the urgency decision as input; deciding urgency is out of scope.
- a2a-testbed: `version` command, `compat` top-level `url`, reference
  agent error codes.
- PACT: propose a capacity check before its consent page.

## Parked

- **Fallback routing helper** (pick a sub-agent, else relay, else
  defer): parked until CP5 needs it; the validators already name the
  next step.
- **Suggesting a permanent step-up** after repeated step-ups on one axis:
  parked until real step-up data exists.
- **Per-channel fluency** (speaking vs. reading): parked; one score per
  language until feedback says otherwise.
- **Larger TLA+ models** (three agents, two principals): not tractable
  for CI (three agents passed 17M states in 2.5 minutes); principals
  share no state in the augmentation model.
