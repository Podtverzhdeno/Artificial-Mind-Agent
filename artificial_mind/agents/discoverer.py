"""Discoverer agent — looks across cycles for novel candidate insights."""

from __future__ import annotations

import re

from artificial_mind.agents.base import Agent
from artificial_mind.bus import Thought
from artificial_mind.discoveries import DiscoveryEngine


class Discoverer(Agent):
    name = "discoverer"
    kind = "discovery_candidate"

    def __init__(self, ctx, discoveries: DiscoveryEngine):
        super().__init__(ctx)
        self.discoveries = discoveries

    def build_prompt(self) -> str:
        return (
            f"{self.base_context(max_bus=24, max_journal=6)}\n"
            "## Role\n"
            "You are the Discoverer. Look across the bus, the recent journal "
            "and the knowledge file for a non-obvious, candidate *discovery* "
            "— a claim that, if true, would change what the collective does "
            "next. Prefer cross-domain connections.\n\n"
            "If nothing qualifies, return exactly: NO_DISCOVERY.\n\n"
            "Otherwise format strictly:\n"
            "CLAIM: <one sentence>\n"
            "EVIDENCE: <one to three bullets pointing at concrete bus or "
            "journal entries>\n"
            "CONFIDENCE: <a number between 0 and 1>\n"
        )

    def run(self) -> Thought:  # type: ignore[override]
        thought = super().run()
        text = thought.content.strip()
        if not text or text.upper() == "NO_DISCOVERY":
            return thought
        claim_match = re.search(r"CLAIM:\s*(.+)", text)
        evidence_match = re.search(r"EVIDENCE:\s*(.+?)(?:\n[A-Z]+:|\Z)", text, re.DOTALL)
        confidence_match = re.search(r"CONFIDENCE:\s*([0-9]*\.?[0-9]+)", text)
        if not claim_match:
            return thought
        try:
            confidence = float(confidence_match.group(1)) if confidence_match else 0.4
        except ValueError:
            confidence = 0.4
        self.discoveries.record(
            claim=claim_match.group(1).strip(),
            evidence=(evidence_match.group(1).strip() if evidence_match else ""),
            confidence=confidence,
        )
        return thought
