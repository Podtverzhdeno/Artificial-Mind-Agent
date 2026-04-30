"""Command-line interface for Artificial Mind Agent.

The CLI is intentionally tiny — it wraps :class:`Orchestrator` so that all
the interesting behaviour lives in the package, not in argument parsing.

Usage
-----
::

    python -m artificial_mind run                # endless loop until STOP
    python -m artificial_mind tick               # one cycle (good for debug)
    python -m artificial_mind status             # snapshot of memory state
    python -m artificial_mind evolve [letter]    # force a generation rotation
    python -m artificial_mind discover           # run a discovery pass now
    python -m artificial_mind mcp                # start the MCP server
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from artificial_mind.config import Settings
from artificial_mind.orchestrator import Orchestrator


def _build_orchestrator(settings: Settings | None = None) -> Orchestrator:
    return Orchestrator(settings or Settings.from_env())


def cmd_run(args: argparse.Namespace) -> int:
    orch = _build_orchestrator()
    cycles = orch.run(max_cycles=args.cycles or None)
    print(f"completed {cycles} cycle(s); stopping")
    return 0


def cmd_tick(_args: argparse.Namespace) -> int:
    orch = _build_orchestrator()
    result = orch.tick()
    print(json.dumps(
        {
            "cycle": result.cycle,
            "tool": result.chosen_tool,
            "args": result.tool_args,
            "ok": result.tool_result.ok,
            "summary": result.tool_result.summary,
            "rotated_generation": result.rotated_generation,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    orch = _build_orchestrator()
    print(json.dumps(orch.status(), ensure_ascii=False, indent=2))
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    orch = _build_orchestrator()
    target = orch.generations.rotate(legacy_letter=args.letter or "")
    print(f"rotated generation to {target}")
    return 0


def cmd_discover(_args: argparse.Namespace) -> int:
    orch = _build_orchestrator()
    from artificial_mind.agents import Discoverer

    ctx = orch._agent_ctx(orch._current_cycle)  # noqa: SLF001
    discoverer = Discoverer(ctx, discoveries=orch.discoveries)
    thought = discoverer.run()
    print(thought.content)
    return 0


def cmd_mcp(_args: argparse.Namespace) -> int:
    try:
        from artificial_mind.mcp_server import serve_blocking
    except ModuleNotFoundError as err:
        print(f"MCP optional dependency missing: {err}", file=sys.stderr)
        return 2
    serve_blocking()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="artificial_mind",
        description="Run the self-evolving multi-agent collective.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Workspace root (defaults to current working directory).",
    )
    parser.add_argument("--log-level", default=None, help="Override log level (DEBUG/INFO/...)")

    sub = parser.add_subparsers(dest="cmd", required=False)

    run_p = sub.add_parser("run", help="run the loop until STOP")
    run_p.add_argument("--cycles", type=int, default=0, help="optional max cycles (0 = forever)")
    run_p.set_defaults(func=cmd_run)

    tick_p = sub.add_parser("tick", help="run one cycle")
    tick_p.set_defaults(func=cmd_tick)

    status_p = sub.add_parser("status", help="print snapshot of state")
    status_p.set_defaults(func=cmd_status)

    evolve_p = sub.add_parser("evolve", help="force a generation rotation")
    evolve_p.add_argument("letter", nargs="?", default="", help="optional legacy letter")
    evolve_p.set_defaults(func=cmd_evolve)

    discover_p = sub.add_parser("discover", help="run the discoverer agent once")
    discover_p.set_defaults(func=cmd_discover)

    mcp_p = sub.add_parser("mcp", help="start the MCP server")
    mcp_p.set_defaults(func=cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_level = (args.log_level or "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    if args.cmd is None:
        # Default to ``run`` so plain ``python main.py`` keeps working.
        args.cycles = 0
        return int(cmd_run(args) or 0)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
