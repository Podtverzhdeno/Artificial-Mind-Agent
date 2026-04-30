"""Mind bus — the shared stream of thoughts between agents.

The bus is the central nervous system of the collective. Every specialised
agent (Dreamer, Thinker, Planner, Critic, Researcher, …) appends thoughts
here, and every agent reads recent thoughts from peers when forming its own
contribution. The bus is persisted to ``memory/mind_bus.jsonl`` so that the
collective wakes up with full context on the next process start.

Each :class:`Thought` is a structured dict with at minimum:

``cycle``
    The orchestrator tick that produced this thought.
``agent``
    The producing agent's name (e.g. ``"thinker"``).
``kind``
    Free-form tag (``"reflection"``, ``"plan"``, ``"discovery_candidate"``…).
``content``
    The textual content of the thought.

Thoughts are immutable once posted — the only way to "correct" a thought is
to post a new one referencing it via :data:`Thought.refs`.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Thought:
    cycle: int
    agent: str
    kind: str
    content: str
    timestamp: float = field(default_factory=time.time)
    refs: list[str] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"c{self.cycle:06d}-{self.agent}-{self.kind}"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Thought:
        return cls(
            cycle=int(data.get("cycle", 0)),
            agent=str(data.get("agent", "")),
            kind=str(data.get("kind", "")),
            content=str(data.get("content", "")),
            timestamp=float(data.get("timestamp", time.time())),
            refs=list(data.get("refs", []) or []),
            meta=dict(data.get("meta", {}) or {}),
        )


class MindBus:
    """In-memory bus with optional persistence to JSONL.

    ``max_history`` caps how many thoughts are retained in the in-memory
    deque used for fast lookups; the JSONL file keeps the full history.
    """

    def __init__(self, persist_path: Path | None = None, max_history: int = 200):
        self.persist_path = Path(persist_path) if persist_path else None
        self.max_history = max(1, max_history)
        self._buffer: deque[Thought] = deque(maxlen=self.max_history)
        if self.persist_path is not None:
            self._load()

    # --- Loading / persistence -------------------------------------------

    def _load(self) -> None:
        path = self.persist_path
        if path is None or not path.exists():
            return
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                self._buffer.append(Thought.from_dict(json.loads(raw)))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    def _persist(self, thought: Thought) -> None:
        if self.persist_path is None:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self.persist_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(thought.to_dict(), ensure_ascii=False) + "\n")

    # --- Public API -------------------------------------------------------

    def post(
        self,
        agent: str,
        kind: str,
        content: str,
        cycle: int,
        refs: list[str] | None = None,
        meta: dict[str, object] | None = None,
    ) -> Thought:
        thought = Thought(
            cycle=cycle,
            agent=agent,
            kind=kind,
            content=content,
            refs=list(refs or []),
            meta=dict(meta or {}),
        )
        self._buffer.append(thought)
        self._persist(thought)
        return thought

    def recent(self, n: int = 20, kinds: list[str] | None = None) -> list[Thought]:
        items = list(self._buffer)
        if kinds:
            allowed = {k.lower() for k in kinds}
            items = [t for t in items if t.kind.lower() in allowed]
        return items[-n:]

    def by_agent(self, agent: str, n: int = 20) -> list[Thought]:
        items = [t for t in self._buffer if t.agent == agent]
        return items[-n:]

    def by_cycle(self, cycle: int) -> list[Thought]:
        return [t for t in self._buffer if t.cycle == cycle]

    def all(self) -> list[Thought]:
        return list(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)

    def render(self, n: int = 12) -> str:
        """Return a human-readable digest of the last ``n`` thoughts."""

        thoughts = self.recent(n)
        if not thoughts:
            return "(empty mind-bus)"
        lines = []
        for t in thoughts:
            content = t.content.strip().replace("\n", " ")
            if len(content) > 240:
                content = content[:237] + "..."
            lines.append(f"[c{t.cycle}|{t.agent}|{t.kind}] {content}")
        return "\n".join(lines)
