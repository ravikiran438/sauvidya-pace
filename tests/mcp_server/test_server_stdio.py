# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""End-to-end stdio smoke test for the PACE MCP server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _spawn_env() -> dict[str, str]:
    """Inject repo's src/ into the subprocess PYTHONPATH so the spawned
    process can import the package without requiring an editable install.
    """
    repo_root = Path(__file__).resolve().parents[2]
    src = str(repo_root / "src")
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else src
    return env


@pytest.mark.asyncio
async def test_server_lists_tools_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pace.mcp_server"],
        env=_spawn_env(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    names = {t.name for t in tools.tools}
    expected = {
        "validate_principal_capability_profile",
        "validate_im_precondition",
        "validate_language_match",
        "validate_ccc_gate",
        "validate_ccc_privacy",
        "validate_time_window",
        "validate_option_count",
        # augmentation_profile extension
        "validate_reversibility",
        "validate_identity_preservation",
        "validate_skill_maintenance",
        "validate_emergency_boundary",
    }
    assert names == expected


@pytest.mark.asyncio
async def test_server_call_language_match_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pace.mcp_server"],
        env=_spawn_env(),
    )

    modality = {
        "agent_id": "a1",
        "principal_id": "p1",
        "pcp_version": "v1",
        "modality_plan": {
            "primary_channel": "voice",
            "language": "en",
            "max_options": 2,
            "timeout_seconds": 300,
        },
    }
    pcp = {
        "principal_id": "p1",
        "version": "v1",
        "declared_at": "2026-04-17T10:00:00Z",
        "declared_by": "guardian:g1",
        "language": [{"code": "te", "fluency": 1.0}],
        "decision_capacity": "fluctuating",
    }

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "validate_language_match",
                {"modality": modality, "pcp": pcp},
            )

    assert result.content
    body = json.loads(result.content[0].text)
    assert body["ok"] is False
    assert "IM-2" in body["error"]
