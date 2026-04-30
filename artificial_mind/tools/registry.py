"""Tool registry shared by the planner, the executor and the skill system."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Structured result of a tool invocation."""

    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        return self.summary if self.ok else f"[error] {self.summary}"


ToolFn = Callable[..., ToolResult]


@dataclass
class Tool:
    name: str
    description: str
    fn: ToolFn
    schema: dict[str, str] = field(default_factory=dict)
    category: str = "general"

    def __call__(self, **kwargs: Any) -> ToolResult:
        try:
            result = self.fn(**kwargs)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"{self.name} raised {type(exc).__name__}: {exc}")
        if isinstance(result, ToolResult):
            return result
        return ToolResult(ok=True, summary=str(result))


class ToolRegistry:
    """Mutable registry of named tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def deregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[Tool]:
        return [self._tools[name] for name in self.names()]

    def render_catalog(self) -> str:
        lines = []
        for tool in self.all():
            schema = ", ".join(f"{k}: {v}" for k, v in tool.schema.items()) or "(no args)"
            lines.append(f"- {tool.name} [{tool.category}]: {tool.description} :: {schema}")
        return "\n".join(lines) if lines else "(no tools registered)"

    # ------------------------------------------------------------------

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, summary=f"unknown tool: {name}")
        return tool(**kwargs)


def build_default_registry(context: ToolContext) -> ToolRegistry:
    """Populate a fresh registry with the project's built-in tools."""

    from artificial_mind.tools import builtin  # local import to avoid cycle

    registry = ToolRegistry()
    builtin.register_all(registry, context)
    return registry


@dataclass
class ToolContext:
    """Bag of dependencies built-in tools may need."""

    settings: Any
    world: Any
    memory: Any
    identity: Any
    bus: Any
    skills: Any
    discoveries: Any
