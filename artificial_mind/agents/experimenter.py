"""Experimenter agent — turns a hypothesis into a runnable plan."""

from __future__ import annotations

from artificial_mind.agents.base import Agent


class Experimenter(Agent):
    name = "experimenter"
    kind = "experiment_design"

    def build_prompt(self) -> str:
        return (
            f"{self.base_context()}\n"
            "## Role\n"
            "You are the Experimenter. Pick the most testable hypothesis from "
            "the recent bus and design a *small*, runnable experiment.\n\n"
            "Output sections (use these exact headings):\n"
            "HYPOTHESIS: <one sentence claim>\n"
            "PLAN: <2-4 numbered steps a Python snippet could perform; "
            "each step concrete>\n"
            "EXPECTED: <what would falsify the hypothesis>\n"
        )
