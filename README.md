# Sauvidya PACE

**Status:** Draft v0.1.0
**Paper:** [Sauvidya: An Accessibility Protocol for Agent-to-Principal Interaction in Autonomous Agent Networks](https://doi.org/10.5281/zenodo.19633138)
**Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/v1`
**License:** Apache 2.0

Sauvidya (Sanskrit for *with proper knowledge*) defines the **PACE**
specification: **P**rincipal **A**ccessibility & **C**apacity
**E**nvelope.

PACE addresses the accessibility gap in the agent protocol stack: the
absence of any protocol-level mechanism for an agent to discover,
respect, and adapt to the principal's interaction capabilities. For the
estimated 1.3 billion people worldwide living with some form of
disability, and for every adult whose capabilities are declining with
age, current agent protocols are structurally exclusionary.

## The Four Primitives

| Primitive | What it does |
|---|---|
| `PrincipalCapabilityProfile` | On-device declaration of the principal's interaction capabilities across eight dimensions |
| `InteractionModality` | Agent's adapted communication plan computed from the PCP |
| `ConsentCapacityCheck` | Per-interaction verification that the principal can meaningfully consent right now |
| `AdaptiveInteractionContract` | Binding rules governing how all agents interact with this principal |

## Relationship to Other Protocols

PACE is an extension to A2A and MCP using the standard
`capabilities.extensions` mechanism. It also extends two existing
protocol layers:

- **Anumati** (consent) gains accessibility as a consent precondition
- **Phala** (welfare feedback) gains capability-aware satisfaction measurement

## AG-UI Binding

PACE governs whether the principal can perceive, comprehend, and respond, so
[AG-UI](https://github.com/ag-ui-protocol/ag-ui) — the agent↔human transport —
is its natural carrier alongside A2A and MCP. The `pace.ag_ui` module
([`src/pace/ag_ui/binding.py`](src/pace/ag_ui/binding.py)) carries the PACE data
plane over AG-UI:

- `envelope_state_snapshot(ref)` — publishes the `AccessibilityServiceRef`
  capability envelope as an AG-UI `STATE_SNAPSHOT`, keyed by the PACE extension URI.
- `active_challenge_interrupt(...)` — presents a ConsentCapacityCheck
  (`ActiveChallenge`) as an AG-UI **interrupt** (`reason: "input_required"`),
  binding the challenge text by hash and enforcing the response window via
  `expiresAt`.
- `resolve_active_challenge(...)` — turns the principal's resume payload back
  into a typed, validated `ActiveChallenge`; a refusal is encoded in the payload,
  never as a bare AG-UI cancel.

The binding is dependency-free (plain JSON-serializable AG-UI event dicts) and
follows the cross-cutting *Governance over AG-UI* convention documented at
<https://ravikiran438.github.io/agent-protocol-stack/ag-ui/>. See
[`tests/test_ag_ui_binding.py`](tests/test_ag_ui_binding.py) for worked examples.

## Repository Layout

```
sauvidya-pace/
├── specification/
│   ├── Pace.tla                     # TLA+ model (5 TLC-checked invariants)
│   ├── Pace.cfg                     # small model, under a second
│   └── Pace-CrossOrchestrator.cfg   # two orchestrators, about 2 minutes
├── src/pace/
│   ├── types/              # Pydantic type library (4 primitives)
│   ├── ag_ui/              # AG-UI (agent↔human) binding
│   └── validators/         # Runtime invariant validators
├── tests/                  # pytest suite
└── adrs/                   # Architecture Decision Records
```

## Formal Safety Properties

| Property | Statement | How it is checked |
|---|---|---|
| PCP-Sovereignty | No remote agent may write or modify a PCP | API shape: the reference implementation has no remote write path. Not model-checked. |
| IM-Precondition | No interaction without computing InteractionModality from PCP | TLC invariant `IMPrecondition`; validators `validate_im_precondition`, `validate_language_match` |
| CCC-Gate | No consent without capacity check for fluctuating/limited principals | TLC invariant `CCCGate`; validator `validate_ccc_gate` |
| AIC-Enforcement | Contract violations trigger automatic violation_policy | TLC invariant `AICOptionBound` (AIC-2); AIC-1 enforced by the `CreateConsent` action guard; validators `validate_time_window`, `validate_option_count` |
| Privacy-Preservation | CCC results never transmitted to remote agents | Validator `validate_ccc_privacy`. Not model-checked. |
| Non-Diagnosis | No PACE primitive produces or stores a clinical assessment | By construction: no primitive has a diagnostic field. Not model-checked. |

The model also checks cross-orchestrator violation handling:
`ViolationBlockEnforcement` (V-1) and `AnnotationIntegrity` are TLC
invariants; V-2 (one-hop) and V-3 (scope) are enforced by the
`ApplyViolationNotice` action structure.

### Model checking

Uses the TLA+ tools jar (`tla2tools.jar`) from
<https://github.com/tlaplus/tlaplus/releases> and Java 11+.

```bash
cd specification
java -cp tla2tools.jar tlc2.TLC -workers auto -deadlock -config Pace.cfg Pace
java -cp tla2tools.jar tlc2.TLC -workers auto -deadlock -config Pace-CrossOrchestrator.cfg Pace
```

| Config | Distinct states | Result |
|---|---|---|
| `Pace.cfg` | 40,760 | no errors |
| `Pace-CrossOrchestrator.cfg` | 8,249,080 | no errors |

`-deadlock` disables deadlock checking; the model reaches terminal
states by design (for example, once consent is recorded).

## Running Tests

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+ (uv installs
the interpreter pinned in `.python-version` automatically).

```bash
uv sync --all-extras   # creates .venv with dev tools and the MCP extra
uv run pytest -v
```

32 tests covering type construction, bounds, and all six validator
invariants.

## Extension Manifest

This repository publishes a JSON-Schema manifest describing the
AgentCard payload a PACE-aware agent declares under
`capabilities.extensions[]`:

- Machine-readable: [`v1/manifest.json`](v1/manifest.json)
- Human-readable: [`v1/SPEC.md`](v1/SPEC.md)
- Extension URI: `https://ravikiran438.github.io/sauvidya-pace/v1`

The PACE AgentCard descriptor is `AccessibilityServiceRef` (see
[`src/pace/types/accessibility_service_ref.py`](src/pace/types/accessibility_service_ref.py));
the manifest and `SPEC.md` are generated from it with
`uv run python -m pace.manifest --write`, and a test fails if the
committed files drift. The augmentation-profile
sub-extension follows the same layout at
[`extensions/augmentation-profile/v1/manifest.json`](extensions/augmentation-profile/v1/manifest.json) /
[`SPEC.md`](extensions/augmentation-profile/v1/SPEC.md).

The manifest is exploratory: A2A 1.0 does not yet prescribe a schema-
discovery convention for extensions. This repository ships the
manifest as a reference implementation; a generic validator can fetch
the JSON and validate any declared payload without protocol-specific
code.

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
