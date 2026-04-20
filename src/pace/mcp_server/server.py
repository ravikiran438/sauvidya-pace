# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main stdio MCP server for the PACE reference implementation.

MCP scaffolding portable across sibling protocol repos (acap, phala,
pratyahara-nerve). When copying this file, change only:

  - SERVER_NAME, SERVER_VERSION, SERVER_INSTRUCTIONS
  - the `from pace.mcp_server.tools import ...` line

The rest (build_server, _run, main, the two decorators, stdio plumbing)
is deliberately generic so each repo stays independently installable
without a shared package dependency.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from pace.mcp_server.tools import HANDLERS, TOOL_SCHEMAS, ToolInvocationError

SERVER_NAME = "pace"
SERVER_VERSION = "0.1.0"
SERVER_INSTRUCTIONS = (
    "PACE (Sauvidya, principal accessibility contract) reference "
    "server. Exposes six validators: interaction-modality "
    "precondition, language match, consent-capacity gate, "
    "consent-capacity privacy, contract time-window, and option-count "
    "overload. All tools take and return JSON. See the project README "
    "for schemas."
)


def build_server() -> Server:
    server = Server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=SERVER_INSTRUCTIONS,
    )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=schema["description"],
                inputSchema=schema["inputSchema"],
            )
            for name, schema in TOOL_SCHEMAS.items()
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        handler = HANDLERS.get(name)
        if handler is None:
            raise ValueError(f"unknown tool {name!r}")
        try:
            result = handler(arguments)
        except ToolInvocationError as exc:
            raise ValueError(str(exc)) from exc
        return [TextContent(type="text", text=result)]

    return server


async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def run_doctor() -> int:
    """Structural self-check. Prints status to stdout, returns exit code.

    Verifies every schema has a matching handler (and vice versa), and
    that every schema carries the required keys. Does NOT invoke any
    tool — use ``pytest tests/mcp_server/`` for end-to-end checks.
    """
    print(f"{SERVER_NAME} {SERVER_VERSION} - MCP server doctor")

    schema_names = set(TOOL_SCHEMAS.keys())
    handler_names = set(HANDLERS.keys())
    failed: list[str] = []

    only_schema = schema_names - handler_names
    only_handler = handler_names - schema_names
    if only_schema:
        failed.append(f"schemas without handlers: {sorted(only_schema)}")
    if only_handler:
        failed.append(f"handlers without schemas: {sorted(only_handler)}")

    for name in sorted(schema_names | handler_names):
        in_both = name in schema_names and name in handler_names
        schema_ok = in_both and all(
            k in TOOL_SCHEMAS[name] for k in ("description", "inputSchema")
        )
        input_is_object = (
            in_both
            and TOOL_SCHEMAS[name].get("inputSchema", {}).get("type") == "object"
        )
        ok = in_both and schema_ok and input_is_object
        mark = "ok" if ok else "FAIL"
        print(f"  [{mark}] {name}")
        if not ok:
            failed.append(f"{name}: registration incomplete")

    total = len(schema_names | handler_names)
    passing = total - sum(1 for n in failed if ":" in n)

    if failed:
        print(f"\n{passing}/{total} tools registered correctly.")
        print("Status: FAIL")
        for line in failed:
            print(f"  - {line}")
        return 1

    print(f"\n{total}/{total} tools registered correctly.")
    print("Status: OK")
    return 0


def main() -> None:
    """Entry point for ``python -m pace.mcp_server`` and the ``pace-mcp`` script.

    Pass ``--doctor`` to run a structural self-check and exit. Otherwise
    launches the stdio server loop.
    """
    if "--doctor" in sys.argv[1:]:
        raise SystemExit(run_doctor())
    asyncio.run(_run())


if __name__ == "__main__":
    main()
