# Sauvidya PACE

[![CI status](https://github.com/ravikiran438/sauvidya-pace/actions/workflows/ci.yml/badge.svg)](https://github.com/ravikiran438/sauvidya-pace/actions/workflows/ci.yml)

**Status:** Draft 0.1.0 (unreleased changes in [CHANGELOG](CHANGELOG.md))
**Paper:** [Sauvidya: An Accessibility Protocol for Agent-to-Principal Interaction in Autonomous Agent Networks](https://doi.org/10.5281/zenodo.19633138)
**Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/v1`
**License:** Apache 2.0

Sauvidya (Sanskrit, read as *with proper knowledge* or *with proper
accessibility*) defines the **PACE** specification: **P**rincipal
**A**ccessibility & **C**apacity **E**nvelope.

Agent protocols define how agents authenticate, delegate, consent and
report outcomes. They assume a principal who can see, hear, read, decide
in real time and stay equally sharp all day. For the estimated 1.3
billion people living with a disability, and for every adult whose
capabilities change with age, that assumption shuts them out.

PACE is the protocol layer between an agent and the person it serves. It
governs what an agent may say, when, in which language, with how many
choices, and whether the person can meaningfully consent at that moment.
WCAG governs how content is rendered; PACE governs how the agent behaves.

![Flowchart of PACE. A guardian declares an on-device PrincipalCapabilityProfile with eight capability dimensions. An agent reads it and computes an InteractionModality, an adapted communication plan. Before any consent, a ConsentCapacityCheck asks whether the principal's capacity signal meets the threshold. On proceed or simplify, a ConsentRecord is created with an on-device PACEConsentAnnotation, governed by the AdaptiveInteractionContract (time windows, option limits, violation policy). On defer, the agent waits for the next valid time window. On escalate, the guardian is notified. Outcomes feed an accessibility trace, kept alongside Phala's WelfareTrace, and a declining trajectory alerts the guardian.](figures/pace_architecture.png)

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+ (uv installs
the interpreter pinned in `.python-version`).

```bash
git clone https://github.com/ravikiran438/sauvidya-pace.git
cd sauvidya-pace
uv sync --all-extras
```

The paper's worked example: a principal who thinks in Telugu, with
English at 0.3 fluency. An agent that tries to call her in English is
stopped, and told what to do instead.

```python
from pace.types import InteractionModality, PrincipalCapabilityProfile
from pace.validators import validate_language_match

pcp = PrincipalCapabilityProfile(
    principal_id="p-lakshmi",
    version="v1",
    declared_at="2026-10-01T10:00:00+05:30",
    declared_by="guardian:g-ravi",
    language=[{"code": "te", "fluency": 1.0}, {"code": "en", "fluency": 0.3}],
    decision_capacity="fluctuating",
)

english_call = InteractionModality(
    agent_id="service-routing-agent",
    principal_id="p-lakshmi",
    pcp_version="v1",
    modality_plan={"primary_channel": "voice", "language": "en",
                   "max_options": 2, "timeout_seconds": 300},
)

try:
    validate_language_match(english_call, pcp)
except ValueError as err:
    print(err)
```

```text
IM-2 violated: modality language 'en' is not acceptable for 'p-lakshmi' because
fluency in 'en' is 0.30, below the floor of 0.70. Route to a sub-agent that speaks
one of ['te'], otherwise escalate to the guardian. Do not fall back to 'en'.
```

## The four primitives

| Primitive | What it does |
|---|---|
| `PrincipalCapabilityProfile` | On-device declaration of the principal's capabilities across eight dimensions: vision, hearing, motor, cognition, language, literacy, tech fluency, decision capacity. Versions are append-only. |
| `InteractionModality` | The agent's communication plan, computed from the profile before any contact: channel, language, speech rate, information density, option count, timeout. |
| `ConsentCapacityCheck` | Before consent, checks whether the principal can meaningfully consent *now*, and recommends proceed, simplify, defer or escalate. Results never leave the device. |
| `AdaptiveInteractionContract` | Binding rules for every agent serving the principal: time windows in her own time zone, option limits, language floor, retry policy, and what happens on a violation. |

## Wire primitives

| Primitive | What it does |
|---|---|
| `AccessibilityServiceRef` | The AgentCard entry under `capabilities.extensions[]`: endpoints, supported modalities, supported languages. |
| `PACEConsentAnnotation` | On-device record of the accessibility context of one consent, referencing the consent record by ID. Records a guardian relay in `relayed_by`. |
| `ActiveChallenge` | Tamper-evident evidence of an active capacity check: HMAC-SHA256 digests under an on-device audit key, bound to the challenge. |
| `CCCTrend` | Whether capacity checks are trending stable, improving or declining. |
| `PACEViolationNotice` | Signed, one-hop broadcast that blocks an agent across orchestrators after a contract violation. |
| `GuardianNotification` | What the guardian receives on a violation: the agent, the rule, a plain-language summary, both clocks, the actions taken and when agents may next contact her. No capacity data. |

## Language and relay rules

- **IM-2.** If the profile pins a language (`language:te` in
  `adaptations_required`), only that language is acceptable. Otherwise the
  language must be listed at or above the contract's
  `min_language_fluency` (default 0.7, set by the guardian). An agent that
  can't comply routes to a sub-agent that can, or escalates. It never
  falls back to another language.
- **Contract check.** A contract may not bind every agent to a language
  the profile rules out (`validate_contract_language`).
- **CCC-4, relay carries the question, not the consent.** When a guardian
  relays a question, the consent still has to be the principal's: a
  capacity check of her is required, and the relaying guardian can't also
  vouch for her capacity. The exception is a principal whose
  `decision_capacity` is `guardian_required`.

## Augmentation-profile extension

[`extensions/augmentation_profile/`](extensions/augmentation_profile/)
lets a principal declare which capacities an agent may compensate for,
amplify, or must leave to them, with six invariants (AUG-1 to AUG-6).
AUG-6 is a task-scoped step-up: "let me do this one myself" takes an axis
back for one task, and help returns when the task ends. If the time
limit passes, the agent nudges; it never resumes on its own.

## Relationship to other protocols

PACE extends A2A and MCP through the standard `capabilities.extensions`
mechanism; no core spec change is needed. It composes with two other
protocols in the [agent protocol stack](https://ravikiran438.github.io/agent-protocol-stack/):

- **Anumati** (consent): consent becomes capability-conditional
- **Phala** (welfare feedback): satisfaction measurement becomes
  capability-aware

## AG-UI binding

PACE governs whether the principal can perceive, comprehend and respond,
so [AG-UI](https://github.com/ag-ui-protocol/ag-ui), the agent↔human
transport, is its natural carrier alongside A2A and MCP. The `pace.ag_ui`
module ([`src/pace/ag_ui/binding.py`](src/pace/ag_ui/binding.py)) carries
the PACE data plane over AG-UI:

- `envelope_state_snapshot(ref)` publishes the `AccessibilityServiceRef`
  as an AG-UI `STATE_SNAPSHOT`, keyed by the PACE extension URI.
- `active_challenge_interrupt(...)` presents an `ActiveChallenge` as an
  AG-UI interrupt (`reason: "input_required"`), binding the challenge text
  by a keyed digest and enforcing the response window via `expiresAt`.
- `resolve_active_challenge(...)` turns the principal's resume back into a
  typed `ActiveChallenge`, and rejects one whose challenge text no longer
  matches its digest. A refusal is encoded in the payload, never as a bare
  AG-UI cancel.

The binding is dependency-free (plain JSON-serializable event dicts) and
follows the [Governance over AG-UI](https://ravikiran438.github.io/agent-protocol-stack/ag-ui/)
convention. See [`tests/test_ag_ui_binding.py`](tests/test_ag_ui_binding.py)
for worked examples.

## MCP server

`pace-mcp` exposes the validators as MCP tools over stdio: core
invariants, wire primitives and the augmentation extension. See the
[MCP server README](src/pace/mcp_server/README.md).

## Formal safety properties

| Property | Statement | How it is checked |
|---|---|---|
| PCP-Sovereignty | No remote agent may write or modify a PCP | API shape: the reference implementation has no remote write path. Not model-checked. |
| IM-Precondition | No interaction without computing InteractionModality from PCP | TLC invariant `IMPrecondition`; validators `validate_im_precondition`, `validate_language_match` |
| CCC-Gate | No consent without capacity check for fluctuating/limited principals | TLC invariant `CCCGate`; validators `validate_ccc_gate`, `validate_relay_consent` |
| AIC-Enforcement | Contract violations trigger automatic violation_policy | `enforce_violation` applies the policy; TLC invariant `AICOptionBound` (AIC-2); AIC-1 enforced by the `CreateConsent` action guard; validators `validate_time_window`, `validate_option_count`, `validate_contract_language`, `validate_modality_contract` (AIC-5) |
| Privacy-Preservation | CCC results never transmitted to remote agents | Validator `validate_ccc_privacy`; `ActiveChallenge` digests are keyed. Not model-checked. |
| Non-Diagnosis | No PACE primitive produces or stores a clinical assessment | By construction: no primitive has a diagnostic field. Not model-checked. |

The core model also checks cross-orchestrator violation handling:
`ViolationBlockEnforcement` (V-1) and `AnnotationIntegrity` are TLC
invariants; V-2 (one-hop) and V-3 (scope) are enforced by the
`ApplyViolationNotice` action structure.

### Model checking

Needs Java 11+. One script runs every check, locally and in CI; it
downloads the pinned `tla2tools.jar` and verifies its checksum:

```bash
scripts/check-models.sh            # everything (about 3 minutes)
scripts/check-models.sh core augmentation witnesses mutants   # under a minute
```

Besides the configs below, it runs **reachability witnesses** (scenarios
that must be reachable, so the invariants don't pass vacuously) and
**mutants** (copies of the model with a guard removed, which TLC must
catch). To run a single config by hand:

```bash
cd specification
java -cp tla2tools.jar tlc2.TLC -workers auto -deadlock -config Pace.cfg Pace
java -cp tla2tools.jar tlc2.TLC -workers auto -deadlock -config Pace-CrossOrchestrator.cfg Pace

cd ../extensions/augmentation_profile
java -cp tla2tools.jar tlc2.TLC -workers auto -config AugmentationProfile.cfg AugmentationProfile
java -cp tla2tools.jar tlc2.TLC -workers auto -config AugmentationProfile-Liveness.cfg AugmentationProfile
```

| Config | Checks | Distinct states | Result |
|---|---|---|---|
| `Pace.cfg` | core invariants, one orchestrator | 40,760 | no errors |
| `Pace-CrossOrchestrator.cfg` | core invariants, two orchestrators | 8,249,080 | no errors |
| `AugmentationProfile.cfg` | AUG-1 to AUG-6 safety | 4,048,527 | no errors |
| `AugmentationProfile-Liveness.cfg` | AUG-6 nudge liveness | 6,606 | no errors |

`-deadlock` disables deadlock checking for the core model, which reaches
terminal states by design (for example, once consent is recorded).

## Tests

```bash
uv run pytest
```

The suite covers type bounds, every validator invariant, the AG-UI
binding, the MCP server over stdio, and a drift check that fails if the
committed manifests stop matching the code.

## Extension manifest

A JSON-Schema manifest describes the AgentCard payload a PACE-aware agent
declares under `capabilities.extensions[]`, the runtime messages it
exchanges, and the invariants it upholds:

- Machine-readable: [`v1/manifest.json`](v1/manifest.json)
- Human-readable: [`v1/SPEC.md`](v1/SPEC.md)
- Augmentation profile: [`extensions/augmentation-profile/v1/`](extensions/augmentation-profile/v1/)

Both manifests and their `SPEC.md` files are generated from the code with
`uv run python -m pace.manifest --write`. A2A 1.0 does not yet prescribe
a schema-discovery convention for extensions, so the manifest is a
reference implementation: a generic validator can fetch it and check any
declared payload without PACE-specific code.

## Repository layout

```
sauvidya-pace/
├── specification/            TLA+ model of the core protocol and its TLC configs
├── extensions/
│   ├── augmentation_profile/ augmentation extension: README, TLA+ model, TLC configs
│   └── augmentation-profile/ published manifest and SPEC.md for its extension URI
├── v1/                       published manifest and SPEC.md for the core extension URI
├── src/pace/
│   ├── types/                Pydantic models for the primitives
│   ├── validators/           runtime invariant validators
│   ├── extensions/           augmentation-profile types and validators
│   ├── ag_ui/                AG-UI binding
│   ├── mcp_server/           pace-mcp reference MCP server
│   └── manifest.py           manifest and SPEC.md generator
├── tests/                    pytest suite
├── figures/                  Mermaid sources and rendered figures
├── adrs/                     architecture decision records
└── CHANGELOG.md
```

## Contributing

Feedback from people who live with a disability, caregivers and
accessibility practitioners is the most valuable input this project
gets, and it needs no code: the
[feedback form](https://github.com/ravikiran438/sauvidya-pace/issues/new?template=capability-feedback.yml)
takes a few minutes. Developers, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Project records

- [CHECKPOINTS.md](CHECKPOINTS.md): what is done, with the numbers, and
  the gate for what comes next
- [docs/decisions.md](docs/decisions.md): every rule and the fact behind
  it, including the ones reversed
- [docs/perturbations.md](docs/perturbations.md): "say X happens" questions
  asked of the code, and what they found
- [docs/consumer.md](docs/consumer.md): the five-minute story for each
  person PACE serves

## Citation

```bibtex
@misc{kadaboina2026sauvidya,
  author       = {Kadaboina, Ravi Kiran},
  title        = {Sauvidya: An Accessibility Protocol for Agent-to-Principal
                  Interaction in Autonomous Agent Networks},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.19633138},
  url          = {https://doi.org/10.5281/zenodo.19633138}
}
```

## License

Apache 2.0. See [LICENSE](./LICENSE).
