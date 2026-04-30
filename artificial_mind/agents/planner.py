"""Planner agent — selects one concrete tool from the registry."""

from __future__ import annotations

from artificial_mind.agents.base import Agent


class Planner(Agent):
    name = "planner"
    kind = "plan"

    def build_prompt(self) -> str:
        catalog = self.ctx.tools.render_catalog()
        skill_catalog = self.ctx.skills.render_catalog()
        return (
            f"{self.base_context()}\n"
            "## Role\n"
            "You are the Planner. Choose exactly one action to perform this "
            "tick. Available tools are listed below. Skills are reusable "
            "playbooks; if one fits, prefer invoke_skill over reinventing.\n\n"
            f"## Tools\n{catalog}\n\n"
            f"## Skills\n{skill_catalog}\n\n"
            "## Output format (strict)\n"
            "Return three lines exactly:\n"
            "TOOL: <tool name from the catalog>\n"
            "ARGS: key1=value1; key2=value2\n"
            "WHY: <one sentence justification>\n"
        )
