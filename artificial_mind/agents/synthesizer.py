"""Synthesizer agent — distils episodes into durable knowledge."""

from __future__ import annotations

import re

from artificial_mind.agents.base import Agent
from artificial_mind.bus import Thought


class Synthesizer(Agent):
    name = "synthesizer"
    kind = "synthesis"

    def build_prompt(self) -> str:
        return (
            f"{self.base_context(max_bus=12, max_journal=4)}\n"
            "## Role\n"
            "You are the Synthesizer. Look across the recent bus and the "
            "recent journal entries. Extract at most one *durable* "
            "insight that is worth promoting to long-term knowledge — "
            "something the next generation should rediscover or build on.\n\n"
            "If nothing qualifies, return exactly: NOTHING_TO_DISTIL.\n\n"
            "Otherwise format strictly:\n"
            "HEADING: <a short title, less than 10 words>\n"
            "INSIGHT: <2-4 sentences>\n"
            "EVIDENCE: <bullet list of bus/journal entries the insight rests on>\n"
        )

    def run(self) -> Thought:  # type: ignore[override]
        thought = super().run()
        # Promote insights into the knowledge file when the synthesizer
        # produced something concrete.
        text = thought.content.strip()
        if text and text.upper() != "NOTHING_TO_DISTIL":
            heading_match = re.search(r"HEADING:\s*(.+)", text)
            insight_match = re.search(r"INSIGHT:\s*(.+?)(?:\n[A-Z]+:|\Z)", text, re.DOTALL)
            if heading_match and insight_match:
                self.ctx.memory.append_knowledge(
                    heading_match.group(1).strip(),
                    insight_match.group(1).strip(),
                )
        return thought
