"""Built-in tool behaviour with a sandboxed workspace."""

from __future__ import annotations

from pathlib import Path

from artificial_mind.bus import MindBus
from artificial_mind.config import Settings
from artificial_mind.discoveries import DiscoveryEngine
from artificial_mind.identity import Identity
from artificial_mind.memory import Memory
from artificial_mind.skills import SkillRegistry
from artificial_mind.tools import build_default_registry
from artificial_mind.tools.builtin import parse_args_blob
from artificial_mind.tools.registry import ToolContext
from artificial_mind.world import World


def _ctx(tmp_path: Path) -> ToolContext:
    settings = Settings(root=tmp_path, llm_provider="echo")
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    settings.memory_dir.mkdir(parents=True, exist_ok=True)
    settings.experiments_dir.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        settings=settings,
        world=World(tmp_path),
        memory=Memory(settings.journal_dir, settings.memory_dir / "knowledge.md"),
        identity=Identity(settings.goal_path, settings.identity_path),
        bus=MindBus(persist_path=settings.memory_dir / "mind_bus.jsonl"),
        skills=SkillRegistry(settings.skills_dir),
        discoveries=DiscoveryEngine(settings.memory_dir / "discoveries.md"),
    )


def test_default_registry_contains_core_tools(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    names = registry.names()
    for expected in (
        "reflect",
        "write_journal",
        "remember",
        "search_memory",
        "create_experiment",
        "create_skill",
        "record_discovery",
        "request_stop",
        "evolve",
    ):
        assert expected in names


def test_remember_then_search(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    out = registry.execute("remember", heading="bus shapes thought", body="Sharing thoughts changes their content.")
    assert out.ok

    hit = registry.execute("search_memory", query="bus")
    assert hit.ok
    assert hit.data["hits"]
    assert "bus shapes thought" in hit.data["hits"][0]


def test_create_experiment_writes_file(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    res = registry.execute(
        "create_experiment",
        hypothesis="Smaller skills get refined more often than large ones.",
        plan="1. Inspect skill sizes\n2. Count refinements\n3. Correlate",
    )
    assert res.ok
    target = Path(res.data["path"])
    assert target.exists()
    assert "Hypothesis" in target.read_text(encoding="utf-8")


def test_record_discovery_writes_to_file(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    res = registry.execute(
        "record_discovery",
        claim="Generations forget data faster than they forget process.",
        evidence="see anima generation 11 notes",
        confidence=0.7,
    )
    assert res.ok
    body = ctx.discoveries.read()
    assert "Generations forget data faster" in body
    assert "0.70" in body


def test_evolve_returns_request_flag(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    res = registry.execute("evolve", legacy_letter="be braver next generation")
    assert res.ok
    assert res.data["_evolve_request"] is True


def test_request_stop_creates_marker(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    res = registry.execute("request_stop", reason="we are done")
    assert res.ok
    assert ctx.settings.stop_file.exists()


def test_reflect_returns_bus_digest(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    ctx.bus.post(agent="dreamer", kind="dream", content="What if memory has color?", cycle=1)
    registry = build_default_registry(ctx)
    res = registry.execute("reflect", topic="memory and color")
    assert res.ok
    assert "What if memory has color?" in res.data["bus_digest"]


def test_unknown_tool_fails_gracefully(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    registry = build_default_registry(ctx)
    res = registry.execute("definitely_not_a_tool")
    assert not res.ok
    assert "unknown tool" in res.summary


def test_parse_args_blob_handles_kv_and_json() -> None:
    assert parse_args_blob("a=1; b=hello") == {"a": "1", "b": "hello"}
    assert parse_args_blob('{"a": 1, "b": "hello"}') == {"a": "1", "b": "hello"}
    assert parse_args_blob("") == {}
