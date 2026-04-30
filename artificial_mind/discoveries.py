"""Discovery engine — surface candidate insights for human review.

Discoveries are *not* automatically promoted to truth. The engine writes to
``memory/discoveries.md`` with a confidence score, evidence trail, and the
cycle in which the candidate was minted. The expectation is that a human (or
a future, more capable critic) will review them periodically.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from artificial_mind.tools.registry import ToolResult


@dataclass
class DiscoveryEngine:
    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                "# Discoveries\n\nCandidate insights; each entry is unverified.\n",
                encoding="utf-8",
            )

    def record(self, *, claim: str, evidence: str = "", confidence: float = 0.5) -> ToolResult:
        claim = claim.strip()
        if not claim:
            return ToolResult(ok=False, summary="empty claim")
        confidence = max(0.0, min(1.0, float(confidence)))
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        block = (
            f"\n## {claim}\n\n"
            f"- timestamp: {ts}\n"
            f"- confidence: {confidence:.2f}\n"
            f"- evidence: {evidence.strip() or '(none recorded)'}\n"
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(block)
        return ToolResult(
            ok=True,
            summary=f"recorded discovery (confidence={confidence:.2f})",
            data={"claim": claim, "confidence": confidence, "path": str(self.path)},
        )

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")
