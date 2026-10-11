# PACE MCP Server — Sample Payloads

Ready-to-paste JSON for the core invariant tools of `pace-mcp`. Drop any
block at an MCP client with an invocation like:

> Call `validate_time_window` with this input: `<paste>`

Each of these tools maps 1:1 to a named PACE invariant. Happy-path payloads
return `"ok": true`; failure variants trip the invariant.

---

## validate_im_precondition (IM-1)

**What it checks:** every InteractionModality references the
principal's current PCP before use.

```json
{
  "modality": {
    "agent_id": "a1",
    "principal_id": "p1",
    "pcp_version": "v1",
    "modality_plan": {
      "primary_channel": "voice",
      "language": "te",
      "max_options": 2,
      "timeout_seconds": 300
    }
  },
  "pcp": {
    "principal_id": "p1",
    "version": "v1",
    "declared_at": "2026-04-17T10:00:00Z",
    "declared_by": "guardian:g1",
    "language": [{"code": "te", "fluency": 1.0}],
    "decision_capacity": "fluctuating"
  }
}
```

**Failure variants:**
- Pass `"modality": null` (no modality attached).
- Set `"pcp_version": "v0"` on the modality — mismatch with PCP v1.

---

## validate_language_match (IM-2)

**What it checks:** modality language is one the principal is fluent
in (per the PCP).

```json
{
  "modality": {
    "agent_id": "a1",
    "principal_id": "p1",
    "pcp_version": "v1",
    "modality_plan": {
      "primary_channel": "voice",
      "language": "te",
      "max_options": 2,
      "timeout_seconds": 300
    }
  },
  "pcp": {
    "principal_id": "p1",
    "version": "v1",
    "declared_at": "2026-04-17T10:00:00Z",
    "declared_by": "guardian:g1",
    "language": [{"code": "te", "fluency": 1.0}],
    "decision_capacity": "fluctuating"
  }
}
```

**Failure variant:** set modality `"language": "en"` while the PCP
declares only `te` fluency.

---

## validate_ccc_gate (CCC-1)

**What it checks:** principals with fluctuating or guardian-required
capacity need a current ConsentCapacityCheck authorizing consent.

```json
{
  "pcp": {
    "principal_id": "p1",
    "version": "v1",
    "declared_at": "2026-04-17T10:00:00Z",
    "declared_by": "guardian:g1",
    "language": [{"code": "te", "fluency": 1.0}],
    "decision_capacity": "fluctuating"
  },
  "ccc": {
    "principal_id": "p1",
    "timestamp": "2026-04-17T10:15:00Z",
    "capacity_signal": 0.82,
    "confidence": 0.75,
    "assessment_method": "passive",
    "pcp_version": "v1",
    "recommendation": "proceed"
  }
}
```

**Failure variants:**
- Pass `"ccc": null` with `"decision_capacity": "fluctuating"` — gate
  requires a CCC.
- Set `"recommendation": "defer"` — the gate blocks consent.

---

## validate_ccc_privacy (CCC-2)

**What it checks:** only permitted fields of a CCC may be transmitted
downstream (prevents leaking the capacity signal or assessment method
outside the trust boundary).

```json
{
  "ccc": {
    "principal_id": "p1",
    "timestamp": "2026-04-17T10:15:00Z",
    "capacity_signal": 0.82,
    "confidence": 0.75,
    "assessment_method": "passive",
    "pcp_version": "v1",
    "recommendation": "proceed"
  },
  "transmitted_fields": ["interaction_status", "agent_id"]
}
```

**Failure variant:** include `"capacity_signal"` or
`"assessment_method"` in `transmitted_fields` — trips CCC-2.

---

## validate_time_window (AIC-1)

**What it checks:** a moment falls inside the principal's
interaction windows, in her time zone, whatever clock the agent runs
on. The timestamp must carry a UTC offset. Emergency invocations
bypass the window.

```json
{
  "contract": {
    "principal_id": "p1",
    "pcp_version": "v1",
    "interaction_rules": {
      "language": "te",
      "timezone": "Asia/Kolkata",
      "valid_time_windows": [
        {"start": "09:00", "end": "11:00"},
        {"start": "14:00", "end": "16:00"}
      ],
      "sundown_block": {"start": "17:00", "end": "08:00"}
    }
  },
  "at": "2026-10-10T10:00:00+05:30"
}
```

**Failure variant:** set `"at": "2026-10-10T08:30:00-05:00"`, a
morning call from an agent in Texas. That is 19:00 in Hyderabad,
inside the sundown block. Add `"is_emergency": true` to override.

---

## validate_option_count (AIC-2)

**What it checks:** number of options presented does not exceed the
contract's `max_options_per_turn` (default 2).

```json
{
  "contract": {
    "principal_id": "p1",
    "pcp_version": "v1",
    "interaction_rules": {
      "language": "te",
      "timezone": "Asia/Kolkata",
      "valid_time_windows": [{"start": "09:00", "end": "11:00"}]
    }
  },
  "options_presented": 2
}
```

**Failure variant:** set `"options_presented": 5` — exceeds the
default cap of 2, trips AIC-2.
