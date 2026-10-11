# PACE MCP Server

A reference [Model Context Protocol](https://modelcontextprotocol.io/)
server that exposes PACE's validators as 25 MCP tools: the core
accessibility invariants, the wire primitives, and the
augmentation-profile extension. Uses stdio transport. Works with any MCP-compatible
client; see the VSCode section below for one concrete configuration.

## Install

**For end users (no clone needed):**

Requires Python 3.14+. Run directly with `uvx` in an ephemeral
environment:

```bash
uvx --from 'pace[mcp] @ git+https://github.com/ravikiran438/sauvidya-pace.git@v0.2.0' pace-mcp
```

Or install it as a persistent tool:

```bash
uv tool install 'pace[mcp] @ git+https://github.com/ravikiran438/sauvidya-pace.git@v0.2.0'
```

**For contributors (clone):**

From the repository root:

```bash
uv sync --extra mcp
uv run pace-mcp --doctor   # structural self-check
```

Each path installs the MCP Python SDK (2.x) alongside the PACE package
and registers the `pace-mcp` console script in the active Python
environment.

## Run

```bash
pace-mcp
```

Or without the script wrapper:

```bash
python -m pace.mcp_server
```

The server writes MCP protocol messages on stdout and reads requests
on stdin. It is not interactive from a shell; an MCP client starts it
as a subprocess.

## Tools exposed

**Core invariants**

| Tool | Invariant | Purpose |
|---|---|---|
| `validate_principal_capability_profile` | PCP | Structural check of a PrincipalCapabilityProfile at registration time. |
| `validate_im_precondition` | IM-1 | An InteractionModality references the current PCP before use. |
| `validate_channels` | IM-1 | Every channel, primary and fallback, reaches her and is supported by the agent; the chain never dead-ends. |
| `validate_language_match` | IM-2 | The modality's language is pinned by the PCP or meets the contract's fluency floor; the error names the next step. |
| `validate_contract_language` | IM-2 | An AdaptiveInteractionContract does not bind a language the PCP rules out. |
| `validate_ccc_gate` | CCC-1 | Principals with fluctuating, limited or guardian-required capacity have a passing ConsentCapacityCheck before consent. |
| `validate_ccc_privacy` | CCC-2 | No private ConsentCapacityCheck field is transmitted downstream. |
| `validate_relay_consent` | CCC-4 | Consent reached through a guardian relay carries a capacity check of the principal. |
| `validate_time_window` | AIC-1 | A moment is inside the principal's interaction windows, in her time zone (emergencies excepted). |
| `validate_option_count` | AIC-2 | The number of options presented stays within the contract's cap. |
| `validate_daily_limit` | AIC-1 | At most `max_interactions_per_day` contacts per principal, across all agents, by her local day; returns how many remain. |
| `validate_retry` | AIC-3 | No retry in the window of an unanswered attempt; escalate after repeated non-responses. |
| `enforce_violation` | AIC-4 | Applies the contract's violation policy; returns the actions and the guardian notification with both clocks. |
| `validate_modality_contract` | AIC-5 | An InteractionModality stays within its contract: language, timeout, speech rate, options, density, confirmation, recap. |

**Wire primitives**

| Tool | Purpose |
|---|---|
| `validate_accessibility_service_ref` | Validates the AgentCard `capabilities.extensions[]` entry for PACE. |
| `validate_active_challenge` | Validates ActiveChallenge evidence (keyed digests, timing, classification). |
| `validate_pace_consent_annotation` | Validates a PACEConsentAnnotation, including its capacity-check fields. |
| `validate_pace_violation_notice` | Validates a PACEViolationNotice and reports how a receiver handles it (V-1 to V-3). |
| `compute_ccc_trend` | Computes the capacity-check trend with the reference OLS-slope algorithm. |

**Augmentation-profile extension**

| Tool | Invariant | Purpose |
|---|---|---|
| `validate_reversibility` | AUG-1 | No agent action on an axis after the principal reverted it. |
| `validate_identity_preservation` | AUG-3 | Agent actions that alter voice or style cite identity consent. |
| `validate_skill_maintenance` | AUG-4 | No agent action on an axis declared `preserve` in the profile version in force. |
| `validate_emergency_boundary` | AUG-5 | No agent action between an emergency handoff and human acknowledgement. |
| `validate_step_up` | AUG-6 | No agent action on an axis the principal stepped up on in the same task. |
| `check_step_up_nudge` | AUG-6 | Reports whether a step-up is past its time limit and the principal is due a nudge. |

All tools take and return JSON. See `src/pace/mcp_server/tools.py`
for input schemas and output shapes.

## Wire into VSCode

Add this to `.vscode/mcp.json` at your workspace root (or configure
globally via your VSCode user settings, under the MCP section).

**Option A — `uvx` from git URL (no persistent install):**

```json
{
  "servers": {
    "pace": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "pace[mcp] @ git+https://github.com/ravikiran438/sauvidya-pace.git@v0.2.0",
        "pace-mcp"
      ]
    }
  }
}
```

**Option B — absolute path to a pre-installed binary:**

```json
{
  "servers": {
    "pace": {
      "type": "stdio",
      "command": "/absolute/path/to/your/.venv/bin/pace-mcp"
    }
  }
}
```

Reload the workspace. The tools appear in any MCP-aware VSCode
extension under the `pace` server name.

## Sample payloads

See [`EXAMPLES.md`](./EXAMPLES.md) for ready-to-paste JSON for the
core invariant tools, covering the happy path and the failure variant of
each.

## Doctor check

Run a structural self-check (tool registry intact, schemas
well-formed) without spawning the stdio loop:

```bash
uv run pace-mcp --doctor
```

Exit code is 0 when all tools register correctly, 1 otherwise.

## Testing

```bash
uv run pytest tests/mcp_server/
```

Handler-level tests hit `tools.py` directly; one stdio smoke test
launches the server as a subprocess and completes the MCP handshake,
confirming the end-to-end transport.
