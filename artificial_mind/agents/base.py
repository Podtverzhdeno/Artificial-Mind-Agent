"""Base agent and shared context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from artificial_mind.bus import MindBus, Thought
from artificial_mind.identity import Identity
from artificial_mind.llm import LLM
from artificial_mind.memory import Memory

if TYPE_CHECKING:  # pragma: no cover
    from artificial_mind.skills import SkillRegistry
    from artificial_mind.tools.registry import ToolRegistry


@dataclass
class AgentContext:
    """Bag of dependencies handed to every agent on each tick."""

    llm: LLM
    bus: MindBus
    memory: Memory
    identity: Identity
    skills: SkillRegistry
    tools: ToolRegistry
    cycle: int


class Agent:
    """Base class — subclasses override :meth:`build_prompt` and :attr:`name`."""

    name: str = "agent"
    kind: str = "thought"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    # --- Prompt building --------------------------------------------------

    def base_context(self, *, max_journal: int = 2, max_bus: int = 8) -> str:
        bus_digest = self.ctx.bus.render(max_bus)
        recent_journal = self.ctx.memory.recent_digest(n=max_journal)
        knowledge = self.ctx.memory.read_knowledge()
        if len(knowledge) > 1500:
            knowledge = knowledge[-1500:]
        return (
            f"# Goal\n{self.ctx.identity.goal.strip()}\n\n"
            f"# Identity\n{self.ctx.identity.identity.strip()}\n\n"
            f"# Knowledge (truncated)\n{knowledge.strip()}\n\n"
            f"# Recent journal\n{recent_journal.strip()}\n\n"
            f"# Mind bus (recent)\n{bus_digest}\n"
        )

    def build_prompt(self) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- Execution --------------------------------------------------------

    def run(self) -> Thought:
        prompt = self.build_prompt().strip()
        response = self.ctx.llm.ask(prompt)
        return self.ctx.bus.post(
            agent=self.name,
            kind=self.kind,
            content=response,
            cycle=self.ctx.cycle,
        )
