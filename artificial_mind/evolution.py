"""Generation rotation — anima-style.

A *generation* is a snapshot of the agent's state at a moment when it decides
(or the orchestrator decides for it) to start over. The previous state is
archived under ``memory/generations/gen_NNN/`` and a new working state is
seeded from the configured defaults plus a hand-written ``LEGACY.md`` letter.

The rotation is intentionally lossy: the only thing that travels forward is
``LEGACY.md``. Everything else must be reconstructed if the next generation
needs it. This forces honest re-discovery and keeps the agent from drifting
into busywork that re-uses cached, no-longer-valid context.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GenerationManager:
    root: Path
    journal_dir: Path
    knowledge_path: Path
    goal_path: Path
    identity_path: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    # --- Numbering --------------------------------------------------------

    def next_index(self) -> int:
        max_idx = 0
        for entry in self.root.glob("gen_*"):
            stem = entry.name.removeprefix("gen_")
            if stem.isdigit():
                max_idx = max(max_idx, int(stem))
        return max_idx + 1

    def latest(self) -> Path | None:
        candidates = sorted(self.root.glob("gen_*"), key=lambda p: p.name)
        return candidates[-1] if candidates else None

    # --- Rotation ---------------------------------------------------------

    def rotate(self, legacy_letter: str = "") -> Path:
        index = self.next_index()
        target = self.root / f"gen_{index:03d}"
        target.mkdir(parents=True, exist_ok=False)

        # Archive prior state (without removing it from the working tree —
        # the agent decides what to keep). We archive a *copy*, so the
        # working tree stays usable across rotations; only the legacy letter
        # is the canonical handoff.
        (target / "journal").mkdir(parents=True, exist_ok=True)
        for entry in sorted(self.journal_dir.glob("*.md")):
            shutil.copy2(entry, target / "journal" / entry.name)

        if self.knowledge_path.exists():
            shutil.copy2(self.knowledge_path, target / "knowledge.md")
        if self.goal_path.exists():
            shutil.copy2(self.goal_path, target / "goal.md")
        if self.identity_path.exists():
            shutil.copy2(self.identity_path, target / "identity.md")

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        legacy_body = legacy_letter.strip() or (
            "(no explicit legacy letter — the next generation must rediscover.)"
        )
        (target / "LEGACY.md").write_text(
            f"# Legacy from gen_{index:03d}\n\n"
            f"- archived_at: {ts}\n\n"
            f"## Letter to next generation\n\n{legacy_body}\n",
            encoding="utf-8",
        )

        # Truncate journal so the next generation starts fresh on episodic
        # memory but keeps the (durable) knowledge.md unless the agent itself
        # decided to clear it.
        for entry in self.journal_dir.glob("*.md"):
            entry.unlink()

        return target

    # --- Inspection -------------------------------------------------------

    def history(self) -> list[Path]:
        return sorted(self.root.glob("gen_*"), key=lambda p: p.name)
