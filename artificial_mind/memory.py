"""Layered memory store (DIKW-style).

Memory is intentionally split into three layers:

* **Episodic** — one markdown file per cycle in ``memory/journal/`` (the
  granular log preserved from the original project).
* **Semantic** — distilled, durable knowledge in ``memory/knowledge.md``,
  produced by the synthesizer agent. Each entry is a stable principle,
  observation, or recipe.
* **Wisdom / identity** — see :mod:`artificial_mind.identity`.

This module also persists a lightweight :class:`Memory.cursor` which tracks
the next cycle number across process restarts. The cursor is computed from
the highest existing journal file, so manual edits are tolerated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CycleRecord:
    cycle: int
    thought: str
    action: str
    result: str
    critique: str
    extras: dict[str, str]

    def render(self) -> str:
        body = [f"# Cycle {self.cycle}", "", "## Thought", self.thought, "", "## Action", self.action, "", "## Result", self.result, "", "## Critique", self.critique]
        for key, value in self.extras.items():
            body.extend(["", f"## {key}", value])
        return "\n".join(body).strip() + "\n"


class Memory:
    """Filesystem-backed, layered memory store."""

    def __init__(self, journal_dir: Path, knowledge_path: Path):
        self.journal_dir = Path(journal_dir)
        self.knowledge_path = Path(knowledge_path)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.knowledge_path.exists():
            self.knowledge_path.write_text(
                "# Knowledge\n\nDistilled, durable principles and observations.\n",
                encoding="utf-8",
            )

    # --- Cursor -----------------------------------------------------------

    @property
    def cursor(self) -> int:
        """Return the next free cycle number (1-based)."""

        max_cycle = 0
        for entry in self.journal_dir.glob("*.md"):
            stem = entry.stem
            if stem.isdigit():
                max_cycle = max(max_cycle, int(stem))
        return max_cycle + 1

    # --- Episodic memory --------------------------------------------------

    def store_cycle(self, record: CycleRecord) -> Path:
        path = self.journal_dir / f"{record.cycle:04d}.md"
        path.write_text(record.render(), encoding="utf-8")
        return path

    def recent_cycles(self, n: int = 5) -> list[str]:
        files = sorted(self.journal_dir.glob("*.md"))[-n:]
        return [path.read_text(encoding="utf-8") for path in files]

    def recent_digest(self, n: int = 3, max_chars: int = 2000) -> str:
        chunks = self.recent_cycles(n)
        if not chunks:
            return "(no prior cycles)"
        digest = "\n\n---\n\n".join(chunks)
        if len(digest) > max_chars:
            digest = digest[-max_chars:]
        return digest

    # --- Semantic memory --------------------------------------------------

    def read_knowledge(self) -> str:
        return self.knowledge_path.read_text(encoding="utf-8")

    def append_knowledge(self, heading: str, body: str) -> None:
        body = body.strip()
        if not body:
            return
        snippet = f"\n## {heading.strip()}\n\n{body}\n"
        with self.knowledge_path.open("a", encoding="utf-8") as fh:
            fh.write(snippet)

    def search_knowledge(self, query: str, max_hits: int = 5) -> list[str]:
        text = self.read_knowledge()
        query = query.strip().lower()
        if not query:
            return []
        sections = [section for section in text.split("\n## ") if section.strip()]
        hits: list[tuple[int, str]] = []
        for section in sections:
            score = section.lower().count(query)
            if score:
                hits.append((score, section))
        hits.sort(key=lambda pair: pair[0], reverse=True)
        return [section for _, section in hits[:max_hits]]
