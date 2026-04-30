"""Dreamer agent — opens up the question space."""

from __future__ import annotations

from artificial_mind.agents.base import Agent


class Dreamer(Agent):
    name = "dreamer"
    kind = "dream"

    def build_prompt(self) -> str:
        return (
            f"{self.base_context()}\n"
            "## Role\n"
            "You are the Dreamer. Your job is to widen the space of questions "
            "the collective is willing to entertain. Suggest one bold open "
            "question, hypothesis, or analogy that the rest of the collective "
            "has *not* explored yet — drawn from a domain we have not touched.\n\n"
            "Constraints:\n"
            "- 3 to 6 sentences.\n"
            "- Do not propose a tool call.\n"
            "- Do not summarise prior work; *open* something new.\n"
            "- Be specific enough that a researcher could investigate.\n"
        )
