# PACE MCP Server

A reference [Model Context Protocol](https://modelcontextprotocol.io/)
server that exposes PACE's six named accessibility-invariant validators
as MCP tools. Uses stdio transport. Works with any MCP-compatible
client; see the VSCode section below for one concrete configuration.

## Install

From the repository root:

```bash
pip install -e '.[mcp]'
```

This installs the MCP Python SDK alongside the PACE package and
registers the `pace-mcp` console script.

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

| Tool | PACE invariant | Purpose |
|---|---|---|
| `validate_im_precondition` | IM-1 | Every InteractionModality references a current PCP before use. |
| `validate_language_match` | IM-2 | Modality language is one the principal is fluent in. |
| `validate_ccc_gate` | CCC-1 | Principals with fluctuating or guardian-required capacity need a current ConsentCapacityCheck authorizing consent. |
| `validate_ccc_privacy` | CCC-2 | Only permitted fields of a CCC may be transmitted downstream. |
| `validate_time_window` | AIC-1 | Current time is inside the contract's allowed interaction windows (emergency overrides). |
| `validate_option_count` | AIC-2 | Number of options presented does not exceed the contract's cap. |

All tools take and return JSON. See `src/pace/mcp_server/tools.py`
for input schemas and output shapes.

## Wire into VSCode

Add this to `.vscode/mcp.json` at your workspace root (or configure
globally via your VSCode user settings, under the MCP section):

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

See [`EXAMPLES.md`](./EXAMPLES.md) for ready-to-paste JSON per tool,
covering the happy path and the failure variant for each invariant.

## Doctor check

Run a structural self-check (tool registry intact, schemas
well-formed) without spawning the stdio loop:

```bash
pace-mcp --doctor
```

Exit code is 0 when all tools register correctly, 1 otherwise.

## Testing

```bash
pytest tests/mcp_server/
```

Handler-level tests hit `tools.py` directly; one stdio smoke test
launches the server as a subprocess and completes the MCP handshake,
confirming the end-to-end transport.
