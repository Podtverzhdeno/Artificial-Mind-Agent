"""Mind-bus persistence and filtering."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_mind.bus import MindBus, Thought


def test_post_persists_to_jsonl(tmp_path: Path) -> None:
    persist = tmp_path / "bus.jsonl"
    bus = MindBus(persist_path=persist, max_history=10)
    bus.post(agent="thinker", kind="reflection", content="hello world", cycle=1)

    raw_lines = persist.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 1
    payload = json.loads(raw_lines[0])
    assert payload["agent"] == "thinker"
    assert payload["content"] == "hello world"


def test_recent_filters_by_kind(tmp_path: Path) -> None:
    bus = MindBus(persist_path=tmp_path / "bus.jsonl", max_history=10)
    for cycle in range(5):
        bus.post(agent="dreamer", kind="dream", content=f"d{cycle}", cycle=cycle)
        bus.post(agent="critic", kind="critique", content=f"c{cycle}", cycle=cycle)

    dreams = bus.recent(n=3, kinds=["dream"])
    assert len(dreams) == 3
    assert all(t.kind == "dream" for t in dreams)


def test_load_existing_persistence(tmp_path: Path) -> None:
    persist = tmp_path / "bus.jsonl"
    persist.write_text(
        json.dumps(
            Thought(cycle=42, agent="planner", kind="plan", content="x").to_dict(),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    bus = MindBus(persist_path=persist, max_history=10)
    assert len(bus) == 1
    assert bus.all()[0].cycle == 42


def test_max_history_bounds_in_memory(tmp_path: Path) -> None:
    bus = MindBus(persist_path=tmp_path / "bus.jsonl", max_history=2)
    for i in range(5):
        bus.post(agent="x", kind="k", content=str(i), cycle=i)
    assert len(bus) == 2
    assert [t.content for t in bus.all()] == ["3", "4"]


def test_render_truncates_long_content(tmp_path: Path) -> None:
    bus = MindBus(persist_path=tmp_path / "bus.jsonl", max_history=10)
    long_content = "x" * 1000
    bus.post(agent="thinker", kind="reflection", content=long_content, cycle=1)
    rendered = bus.render(5)
    assert "..." in rendered
    assert len(rendered) < len(long_content)
