"""End-to-end orchestrator behaviour with a scripted LLM."""

from __future__ import annotations

from pathlib import Path

from artificial_mind.bus import MindBus
from artificial_mind.config import Settings
from artificial_mind.discoveries import DiscoveryEngine
from artificial_mind.evolution import GenerationManager
from artificial_mind.identity import Identity
from artificial_mind.llm import LLM
from artificial_mind.memory import Memory
from artificial_mind.orchestrator import Orchestrator
from artificial_mind.skills import SkillRegistry


def _scripted_llm(settings: Settings, *responses: str) -> LLM:
    iterator = {"i": 0}
    seq = list(responses)

    def provider(_prompt: str, _llm: LLM) -> str:
        if not seq:
            return "[empty]"
        value = seq[iterator["i"] % len(seq)]
        iterator["i"] += 1
        return value

    return LLM(settings, provider=provider)


def _build(workspace: Path, *responses: str) -> Orchestrator:
    settings = Settings(
        root=workspace,
        llm_provider="echo",
        max_bus_history=50,
        generation_threshold=0,
        discovery_interval=10,
    )
    return Orchestrator(
        settings=settings,
        llm=_scripted_llm(settings, *responses),
        bus=MindBus(persist_path=settings.memory_dir / "mind_bus.jsonl"),
        memory=Memory(settings.journal_dir, settings.memory_dir / "knowledge.md"),
        identity=Identity(settings.goal_path, settings.identity_path),
        skills=SkillRegistry(settings.skills_dir),
        discoveries=DiscoveryEngine(settings.memory_dir / "discoveries.md"),
        generations=GenerationManager(
            root=settings.generations_dir,
            journal_dir=settings.journal_dir,
            knowledge_path=settings.memory_dir / "knowledge.md",
            goal_path=settings.goal_path,
            identity_path=settings.identity_path,
        ),
    )


# --- Fixed planner outputs for tests -----------------------------------

PLANNER_REFLECT = (
    "TOOL: reflect\nARGS: topic=test\nWHY: warm up the bus\n"
)
PLANNER_REMEMBER = (
    "TOOL: remember\n"
    "ARGS: heading=Bus shapes thought; body=Sharing thoughts changes their content.\n"
    "WHY: capture a durable insight\n"
)
PLANNER_RECORD_DISCOVERY = (
    "TOOL: record_discovery\n"
    "ARGS: claim=Generations forget data faster than process; "
    "evidence=cycle 1 reflections; confidence=0.6\n"
    "WHY: surface a candidate discovery\n"
)
PLANNER_EVOLVE = (
    "TOOL: evolve\nARGS: legacy_letter=be braver next generation\n"
    "WHY: time for a fresh start\n"
)
PLANNER_UNKNOWN = "TOOL: definitely_not_a_tool\nARGS: \nWHY: probe the fallback\n"
PLANNER_BAD_FORMAT = "I forgot the format entirely.\n"


def _responses(planner_output: str, **overrides: str) -> list[str]:
    """Order matches the orchestrator: dreamer, thinker, researcher,
    experimenter, planner, critic, synthesizer, [discoverer]."""

    base = {
        "dreamer": "What if memory is a place, not a record?",
        "thinker": "We have run too many self-referential cycles.\nNext: try something concrete.",
        "researcher": "QUERY: anima generation 11 inheritance findings\nWHY: see what others learned",
        "experimenter": (
            "HYPOTHESIS: small skills get refined more often than big ones.\n"
            "PLAN: 1. enumerate skills 2. count refinements 3. correlate sizes\n"
            "EXPECTED: no correlation falsifies it"
        ),
        "planner": planner_output,
        "critic": "VERDICT: useful\nREASON: the action moved knowledge forward.\nNEXT: keep testing.",
        "synthesizer": "NOTHING_TO_DISTIL",
        "discoverer": "NO_DISCOVERY",
    }
    base.update(overrides)
    return [
        base["dreamer"],
        base["thinker"],
        base["researcher"],
        base["experimenter"],
        base["planner"],
        base["critic"],
        base["synthesizer"],
        base["discoverer"],
    ]


def test_tick_executes_remember_tool(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_REMEMBER))
    result = orch.tick()

    assert result.cycle == 1
    assert result.chosen_tool == "remember"
    assert result.tool_result.ok
    knowledge = (workspace / "memory" / "knowledge.md").read_text(encoding="utf-8")
    assert "Bus shapes thought" in knowledge


def test_tick_records_discovery(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_RECORD_DISCOVERY))
    result = orch.tick()

    assert result.chosen_tool == "record_discovery"
    discoveries = (workspace / "memory" / "discoveries.md").read_text(encoding="utf-8")
    assert "Generations forget data faster than process" in discoveries


def test_unknown_tool_falls_back_to_reflect(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_UNKNOWN))
    result = orch.tick()
    assert result.chosen_tool == "reflect"
    assert result.tool_result.ok


def test_bad_planner_format_falls_back_to_reflect(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_BAD_FORMAT))
    result = orch.tick()
    # Default tool name when no "TOOL: ..." line is present is 'reflect'.
    assert result.chosen_tool == "reflect"


def test_evolve_request_rotates_generation(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_EVOLVE))
    result = orch.tick()
    assert result.rotated_generation
    rotated = list((workspace / "memory" / "generations").glob("gen_*"))
    assert rotated, "expected a generation snapshot"
    legacy = (rotated[0] / "LEGACY.md").read_text(encoding="utf-8")
    assert "be braver next generation" in legacy


def test_journal_record_contains_all_sections(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_REFLECT))
    orch.tick()
    journal_files = sorted((workspace / "memory" / "journal").glob("*.md"))
    assert journal_files
    text = journal_files[0].read_text(encoding="utf-8")
    for heading in (
        "## Thought",
        "## Action",
        "## Result",
        "## Critique",
        "## Dream",
        "## Synthesis",
        "## Plan",
    ):
        assert heading in text


def test_synthesizer_promotes_to_knowledge(workspace: Path) -> None:
    synthesis = (
        "HEADING: Bus shapes thought\n"
        "INSIGHT: Sharing thoughts on the bus changes their content.\n"
        "EVIDENCE:\n- bus c1\n- bus c2\n"
    )
    orch = _build(workspace, *_responses(PLANNER_REFLECT, synthesizer=synthesis))
    orch.tick()
    knowledge = (workspace / "memory" / "knowledge.md").read_text(encoding="utf-8")
    assert "Bus shapes thought" in knowledge


def test_status_reports_state(workspace: Path) -> None:
    orch = _build(workspace, *_responses(PLANNER_REMEMBER))
    orch.tick()
    status = orch.status()
    assert status["cycle"] == 2  # cursor advanced after first tick
    assert status["bus_size"] >= 1
    assert "remember" in status["tools"]


def test_run_respects_max_cycles(workspace: Path) -> None:
    responses = _responses(PLANNER_REFLECT) * 3
    orch = _build(workspace, *responses)
    cycles = orch.run(max_cycles=2)
    assert cycles == 2
    journals = list((workspace / "memory" / "journal").glob("*.md"))
    assert len(journals) == 2
