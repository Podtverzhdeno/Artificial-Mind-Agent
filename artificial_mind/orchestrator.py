"""Main coordination loop for the agent collective.

A single ``tick`` is one full collective thought:

1. **Dreamer** opens a question.
2. **Thinker** reflects on goal + identity + bus + journal.
3. **Researcher** proposes an external query.
4. **Experimenter** designs a small experiment.
5. **Planner** picks one tool to fire (with arguments).
6. The orchestrator executes the chosen tool.
7. **Critic** challenges action and result.
8. **Synthesizer** distils any durable insight into knowledge.
9. Every ``discovery_interval`` ticks the **Discoverer** runs.
10. Every ``generation_threshold`` ticks (or on explicit request) the
    orchestrator rotates the generation, archives state and resets the
    journal.

The full transcript of a tick is saved to the journal as one cycle record.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from artificial_mind.agents import (
    Critic,
    Discoverer,
    Dreamer,
    Experimenter,
    Planner,
    Researcher,
    Synthesizer,
    Thinker,
)
from artificial_mind.agents.base import AgentContext
from artificial_mind.bus import MindBus
from artificial_mind.config import Settings
from artificial_mind.discoveries import DiscoveryEngine
from artificial_mind.evolution import GenerationManager
from artificial_mind.identity import Identity
from artificial_mind.llm import LLM
from artificial_mind.memory import CycleRecord, Memory
from artificial_mind.skills import SkillRegistry
from artificial_mind.tools import ToolRegistry, build_default_registry
from artificial_mind.tools.builtin import parse_args_blob
from artificial_mind.tools.registry import ToolContext, ToolResult
from artificial_mind.world import World

logger = logging.getLogger(__name__)


@dataclass
class TickResult:
    cycle: int
    chosen_tool: str
    tool_args: dict[str, str]
    tool_result: ToolResult
    thoughts: dict[str, str] = field(default_factory=dict)
    rotated_generation: bool = False


class Orchestrator:
    """Top-level controller. Use :meth:`tick` to advance one cycle."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: LLM | None = None,
        bus: MindBus | None = None,
        memory: Memory | None = None,
        identity: Identity | None = None,
        skills: SkillRegistry | None = None,
        discoveries: DiscoveryEngine | None = None,
        generations: GenerationManager | None = None,
        tools: ToolRegistry | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.world = World(self.settings.root)
        self.llm = llm or LLM.from_settings(self.settings)
        self.bus = bus or MindBus(
            persist_path=self.settings.memory_dir / "mind_bus.jsonl",
            max_history=self.settings.max_bus_history,
        )
        self.memory = memory or Memory(
            journal_dir=self.settings.journal_dir,
            knowledge_path=self.settings.memory_dir / "knowledge.md",
        )
        self.identity = identity or Identity(
            goal_path=self.settings.goal_path,
            identity_path=self.settings.identity_path,
        )
        self.skills = skills or SkillRegistry(self.settings.skills_dir)
        self.discoveries = discoveries or DiscoveryEngine(
            self.settings.memory_dir / "discoveries.md"
        )
        self.generations = generations or GenerationManager(
            root=self.settings.generations_dir,
            journal_dir=self.settings.journal_dir,
            knowledge_path=self.memory.knowledge_path,
            goal_path=self.settings.goal_path,
            identity_path=self.settings.identity_path,
        )

        tool_ctx = ToolContext(
            settings=self.settings,
            world=self.world,
            memory=self.memory,
            identity=self.identity,
            bus=self.bus,
            skills=self.skills,
            discoveries=self.discoveries,
        )
        self.tools = tools or build_default_registry(tool_ctx)

        self._current_cycle: int = self.memory.cursor

    # ------------------------------------------------------------------

    def _agent_ctx(self, cycle: int) -> AgentContext:
        return AgentContext(
            llm=self.llm,
            bus=self.bus,
            memory=self.memory,
            identity=self.identity,
            skills=self.skills,
            tools=self.tools,
            cycle=cycle,
        )

    @staticmethod
    def _parse_planner_output(content: str) -> tuple[str, dict[str, str], str]:
        tool_match = re.search(r"TOOL:\s*([\w_-]+)", content)
        args_match = re.search(r"ARGS:\s*(.+?)(?:\nWHY:|\Z)", content, re.DOTALL)
        why_match = re.search(r"WHY:\s*(.+)", content)
        tool_name = tool_match.group(1).strip() if tool_match else "reflect"
        args_blob = args_match.group(1).strip() if args_match else ""
        args = parse_args_blob(args_blob)
        why = why_match.group(1).strip() if why_match else ""
        return tool_name, args, why

    @staticmethod
    def _coerce_args(tool_schema: dict[str, str], args: dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in args.items():
            spec = tool_schema.get(key, "str")
            if spec == "int":
                try:
                    out[key] = int(value)
                except ValueError:
                    out[key] = 0
            elif spec == "float":
                try:
                    out[key] = float(value)
                except ValueError:
                    out[key] = 0.0
            else:
                out[key] = value
        return out

    # ------------------------------------------------------------------

    def tick(self) -> TickResult:
        cycle = self._current_cycle
        ctx = self._agent_ctx(cycle)
        thoughts: dict[str, str] = {}

        for agent_cls in (Dreamer, Thinker, Researcher, Experimenter):
            agent = agent_cls(ctx)
            thoughts[agent.name] = agent.run().content

        planner = Planner(ctx)
        plan_thought = planner.run()
        thoughts[planner.name] = plan_thought.content

        tool_name, args, why = self._parse_planner_output(plan_thought.content)
        tool = self.tools.get(tool_name)
        if tool is None:
            tool = self.tools.get("reflect")
            tool_name = tool.name if tool else "reflect"
            args = {"topic": "fallback because planner picked an unknown tool"}

        coerced = self._coerce_args(tool.schema if tool else {}, args)
        result = self.tools.execute(tool_name, **coerced) if tool else ToolResult(False, "no tools")

        rotated = bool(result.data.get("_evolve_request"))

        action_text = f"{tool_name}({coerced}) :: why={why}"
        result_text = result.render()
        if isinstance(result.data, dict) and result.data.get("output"):
            result_text += "\n---\n" + str(result.data.get("output"))[:1500]

        self.bus.post(agent="executor", kind="action_result", content=action_text + "\n" + result_text, cycle=cycle)

        critic = Critic(ctx, action=action_text, result=result_text)
        critique_thought = critic.run()
        thoughts[critic.name] = critique_thought.content

        synthesizer = Synthesizer(ctx)
        synthesis_thought = synthesizer.run()
        thoughts[synthesizer.name] = synthesis_thought.content

        if cycle and cycle % max(1, self.settings.discovery_interval) == 0:
            discoverer = Discoverer(ctx, discoveries=self.discoveries)
            discovery_thought = discoverer.run()
            thoughts[discoverer.name] = discovery_thought.content

        record = CycleRecord(
            cycle=cycle,
            thought=thoughts.get("thinker", ""),
            action=action_text,
            result=result_text,
            critique=thoughts.get("critic", ""),
            extras={
                "Dream": thoughts.get("dreamer", ""),
                "Research": thoughts.get("researcher", ""),
                "Experiment design": thoughts.get("experimenter", ""),
                "Synthesis": thoughts.get("synthesizer", ""),
                "Discovery candidate": thoughts.get("discoverer", ""),
                "Plan": thoughts.get("planner", ""),
            },
        )
        self.memory.store_cycle(record)

        # Optional generation rotation -------------------------------------
        if rotated or self._should_auto_rotate(cycle):
            legacy = result.data.get("legacy") if rotated else self._auto_legacy(cycle)
            self.generations.rotate(legacy_letter=str(legacy or ""))
            rotated = True
            self._current_cycle = self.memory.cursor
        else:
            self._current_cycle = cycle + 1

        return TickResult(
            cycle=cycle,
            chosen_tool=tool_name,
            tool_args=args,
            tool_result=result,
            thoughts=thoughts,
            rotated_generation=rotated,
        )

    # ------------------------------------------------------------------

    def _should_auto_rotate(self, cycle: int) -> bool:
        threshold = max(0, self.settings.generation_threshold)
        if not threshold:
            return False
        return cycle > 0 and cycle % threshold == 0

    def _auto_legacy(self, cycle: int) -> str:
        recent = self.bus.recent(20)
        digest = "\n".join(f"- [{t.agent}] {t.content[:160]}" for t in recent if t.content)
        return (
            f"Auto-rotation at cycle {cycle}.\n\n"
            "Carrying forward the last 20 thoughts as a hint to the next "
            "generation. The next generation should NOT treat them as truth — "
            "they are just the tone of voice we left behind.\n\n"
            f"{digest}\n"
        )

    # ------------------------------------------------------------------

    def run(self, max_cycles: int | None = None) -> int:
        """Run the loop until ``STOP`` file appears or ``max_cycles`` is hit."""

        cycles_done = 0
        target = max_cycles if max_cycles is not None else self.settings.max_cycles
        while True:
            if self.settings.stop_file.exists():
                logger.info("STOP file detected at %s — exiting loop", self.settings.stop_file)
                break
            self.tick()
            cycles_done += 1
            if target and cycles_done >= target:
                break
            if self.settings.tick_delay > 0:
                time.sleep(self.settings.tick_delay)
        return cycles_done

    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        return {
            "cycle": self._current_cycle,
            "generation_files": [p.name for p in self.generations.history()],
            "skills": [s.name for s in self.skills.list()],
            "knowledge_chars": len(self.memory.read_knowledge()),
            "bus_size": len(self.bus),
            "tools": self.tools.names(),
            "stop_file": str(self.settings.stop_file) if self.settings.stop_file.exists() else "",
        }
