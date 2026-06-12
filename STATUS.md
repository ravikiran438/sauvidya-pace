# PACE — repository status

Internal snapshot. The canonical references are this repo's README and the
published paper (Zenodo DOI 10.5281/zenodo.19633138).

## Last touched

May 1, 2026 — added `AccessibilityServiceRef` AgentCard descriptor + 4 sibling
primitives (`PACEConsentAnnotation`, `ActiveChallenge`, `CCCTrend` +
`derive_ccc_trend`, `PACEViolationNotice`), tightened TLA+ V-3 to require exact
AIC version match, added a cross-field model validator on
`PACEConsentAnnotation`, wired 5 new MCP validators.

## What works (verified)

- 129 tests passing (incl. the AG-UI binding suite).
- **AG-UI binding** at `pace.ag_ui` (`src/pace/ag_ui/binding.py`): carries the
  PACE data plane over the agent↔human transport — capability envelope as a
  `STATE_SNAPSHOT`, an active CCC as an `input_required` interrupt, and a typed
  resume back to `ActiveChallenge`. Dependency-free; 9 tests in
  `tests/test_ag_ui_binding.py`. Follows the cross-cutting *Governance over
  AG-UI* spec (<https://ravikiran438.github.io/agent-protocol-stack/ag-ui/>).
- TLA+ model `specification/Pace.tla` checks clean under TLC at the current
  widened model (2 principals, 2 orchestrators, 3 AIC versions). Invariants:
  `ViolationBlockEnforcement` (V-1), `ViolationScopeRespected` (V-3),
  `AnnotationIntegrity`. V-2 is structural (one-hop broadcast enforced by the
  `ApplyViolationNotice` action's lack of mutation on `violationNotices`).
- MCP server at `pace.mcp_server` exposes 16 validator tools including the 5 new
  ones (`validate_accessibility_service_ref`, `validate_active_challenge`,
  `validate_pace_consent_annotation`, `validate_pace_violation_notice`,
  `compute_ccc_trend`).
- ExtensionManifest published at `v1/manifest.json`, auto-generated from
  `pace.types.AccessibilityServiceRef`.
- Augmentation-profile sub-extension has a URI constant + manifest at
  `extensions/augmentation-profile/v1/manifest.json`.

## What's pending

- The current paper is a breaking change for the previously-published embedded
  `ConsentRecord.pace` pattern (now replaced by the `PACEConsentAnnotation`
  sibling); the migration recipe is in §4.1 of the paper.

## Verify

1. `python -m pytest -q` — expect 129/129.
2. Run TLC: `cd specification && java -Xmx4g -cp "$TLA2TOOLS" tlc2.TLC
   -workers auto -deadlock Pace` — expect "no error".
3. Re-read `src/pace/types/accessibility_service_ref.py` and the four sibling
   primitive files for current wire format.

## Files to look at first

- `src/pace/types/accessibility_service_ref.py` — AgentCard descriptor.
- `src/pace/types/pace_consent_annotation.py` — sibling to the ACAP
  ConsentRecord; the cross-field validator there enforces CCC coherence.
- `src/pace/types/active_challenge.py` — tamper-evident active CCC evidence
  (challenge_hash + response_hash + timing + classification).
- `src/pace/types/violation_notice.py` — cross-orchestrator block broadcast;
  `compute_evidence_hash` is the canonical helper.
- `src/pace/types/ccc_trend.py` — `CCCTrend` enum (canonical) +
  `derive_ccc_trend` (reference impl, non-normative).
- `specification/Pace.tla` — V-1, V-3, AnnotationIntegrity verified.

## Known gaps / future work

- V-3 requires exact AIC version match. TLC re-verifies clean at the widened
  model. If expanded model checking flags issues, treat as a new finding.
- `ActiveChallenge` stores SHA-256 digests of challenge/response text — strong
  tamper-evidence, weak privacy if anyone holds the original transcript. The
  paper's privacy section documents this.
- `derive_ccc_trend` ships an OLS-slope reference; deployments are free to swap
  for EWMA/Mann-Kendall/etc. as long as outputs map onto the canonical
  four-value enum.
