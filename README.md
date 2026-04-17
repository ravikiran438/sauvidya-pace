# Sauvidya PACE

**Status:** Draft v0.1.0
**Paper:** Sauvidya: An Accessibility Protocol for Agent-to-Principal Interaction in Autonomous Agent Networks
**Extension URI:** `https://github.com/ravikiran438/sauvidya-pace/v1`
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

## Repository Layout

```
sauvidya-pace/
├── specification/
│   ├── Pace.tla            # TLA+ model (6 safety properties)
│   └── Pace.cfg            # TLC configuration
├── src/pace/
│   ├── types/              # Pydantic type library (4 primitives)
│   └── validators/         # Runtime invariant validators
├── tests/                  # pytest suite
└── adrs/                   # Architecture Decision Records
```

## Formal Safety Properties

| Property | Statement |
|---|---|
| PCP-Sovereignty | No remote agent may write or modify a PCP |
| IM-Precondition | No interaction without computing InteractionModality from PCP |
| CCC-Gate | No consent without capacity check for fluctuating/limited principals |
| AIC-Enforcement | Contract violations trigger automatic violation_policy |
| Privacy-Preservation | CCC results never transmitted to remote agents |
| Non-Diagnosis | No PACE primitive produces or stores a clinical assessment |

## Running Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest -v
```

32 tests covering type construction, bounds, and all six validator
invariants.

## Citation

```bibtex
@misc{kadaboina2026sauvidya,
  author       = {Kadaboina, Ravi Kiran},
  title        = {Sauvidya: An Accessibility Protocol for Agent-to-Principal
                  Interaction in Autonomous Agent Networks},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {},
  url          = {}
}
```

DOI will be added once the paper is published on Zenodo.

## License

Apache 2.0. See [LICENSE](./LICENSE).
