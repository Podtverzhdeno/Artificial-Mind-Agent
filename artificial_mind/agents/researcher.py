"""Researcher agent — proposes external research queries."""

from __future__ import annotations

from artificial_mind.agents.base import Agent


class Researcher(Agent):
    name = "researcher"
    kind = "research_query"

    def build_prompt(self) -> str:
        return (
            f"{self.base_context()}\n"
            "## Role\n"
            "You are the Researcher. Propose one specific external query that "
            "would shift the collective's understanding the most given the "
            "current open question on the bus. Prefer queries that have a "
            "concrete answer reachable via the web (papers, docs, datasets) "
            "rather than vague topics.\n\n"
            "Format:\n"
            "QUERY: <a precise search query, < 20 words>\n"
            "WHY: <one sentence on what we expect to learn>\n"
        )
