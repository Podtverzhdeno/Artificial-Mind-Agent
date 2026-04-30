"""Optional MCP server exposing the agent collective as a tool.

Mirrors the integration pattern used by the sister project ``gigaspeech``:
external LLM clients (Claude Desktop, Cursor, etc.) can call into this
collective through a single ``tick`` tool. The server is best-effort — if
the ``mcp`` extra is not installed, importing this module raises a clean
``ModuleNotFoundError`` that the CLI surfaces as an error message.
"""

from __future__ import annotations

import json

try:  # pragma: no cover - optional dep
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as err:  # pragma: no cover
    raise ModuleNotFoundError(
        "Install the optional MCP extra: pip install '.[mcp]'"
    ) from err

from artificial_mind.config import Settings
from artificial_mind.orchestrator import Orchestrator

mcp = FastMCP("artificial-mind-agent")
_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(Settings.from_env())
    return _orchestrator


@mcp.tool()
def tick() -> str:
    """Advance the collective by one cycle and return a JSON summary."""

    orch = _get_orchestrator()
    result = orch.tick()
    return json.dumps(
        {
            "cycle": result.cycle,
            "tool": result.chosen_tool,
            "args": result.tool_args,
            "ok": result.tool_result.ok,
            "summary": result.tool_result.summary,
            "rotated_generation": result.rotated_generation,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def status() -> str:
    """Return a JSON snapshot of the collective's state."""

    orch = _get_orchestrator()
    return json.dumps(orch.status(), ensure_ascii=False)


@mcp.tool()
def evolve(letter: str = "") -> str:
    """Force a generation rotation, optionally with a legacy letter."""

    orch = _get_orchestrator()
    target = orch.generations.rotate(legacy_letter=letter or "")
    return json.dumps({"rotated_to": str(target)}, ensure_ascii=False)


def serve_blocking() -> None:  # pragma: no cover - I/O wrapper
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    serve_blocking()
