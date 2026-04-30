"""Tool layer — concrete actions the planner can choose from.

The :class:`~artificial_mind.tools.registry.ToolRegistry` is populated with a
set of built-in tools when :func:`build_default_registry` is called. Custom
tools (and runtime-generated skills) can be registered with
:meth:`ToolRegistry.register`.
"""

from artificial_mind.tools.registry import Tool, ToolRegistry, ToolResult, build_default_registry

__all__ = ["Tool", "ToolRegistry", "ToolResult", "build_default_registry"]
