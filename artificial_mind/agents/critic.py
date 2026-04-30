"""Critic agent — challenges the action and its result."""

from __future__ import annotations

from artificial_mind.agents.base import Agent


class Critic(Agent):
    name = "critic"
    kind = "critique"

    def __init__(self, ctx, *, action: str = "", result: str = ""):
        super().__init__(ctx)
        self.action = action
        self.result = result

    def build_prompt(self) -> str:
        return (
            f"{self.base_context()}\n"
            "## Role\n"
            "You are the Critic. Read the action that was performed and its "
            "result. Be ruthless about the difference between *signal* and "
            "*ceremony*. If the action was self-referential busywork, say so "
            "plainly. If the result is genuinely useful, name *why* — be "
            "specific about which prior question it advances.\n\n"
            f"## Action\n{self.action.strip()}\n\n"
            f"## Result\n{self.result.strip()}\n\n"
            "Format:\n"
            "VERDICT: <useful | weak | busywork>\n"
            "REASON: <one or two sentences>\n"
            "NEXT: <one sentence on what would beat this>\n"
        )
