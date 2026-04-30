"""Layered memory store behaviour."""

from __future__ import annotations

from pathlib import Path

from artificial_mind.memory import CycleRecord, Memory


def _new_memory(tmp_path: Path) -> Memory:
    return Memory(tmp_path / "journal", tmp_path / "knowledge.md")


def test_cursor_starts_at_one(tmp_path: Path) -> None:
    memory = _new_memory(tmp_path)
    assert memory.cursor == 1


def test_store_and_recursor(tmp_path: Path) -> None:
    memory = _new_memory(tmp_path)
    record = CycleRecord(
        cycle=1, thought="t", action="reflect()", result="r", critique="c", extras={}
    )
    memory.store_cycle(record)
    assert memory.cursor == 2
    files = sorted((tmp_path / "journal").glob("*.md"))
    assert len(files) == 1
    assert "Cycle 1" in files[0].read_text(encoding="utf-8")


def test_extras_render(tmp_path: Path) -> None:
    memory = _new_memory(tmp_path)
    record = CycleRecord(
        cycle=2,
        thought="t",
        action="a",
        result="r",
        critique="c",
        extras={"Discovery candidate": "claim X", "Synthesis": "ok"},
    )
    path = memory.store_cycle(record)
    text = path.read_text(encoding="utf-8")
    assert "## Discovery candidate" in text
    assert "## Synthesis" in text


def test_search_knowledge(tmp_path: Path) -> None:
    memory = _new_memory(tmp_path)
    memory.append_knowledge("First", "alpha and beta")
    memory.append_knowledge("Second", "alpha alpha gamma")
    hits = memory.search_knowledge("alpha")
    assert len(hits) == 2
    # The section with two occurrences ranks first.
    assert "alpha alpha" in hits[0]
