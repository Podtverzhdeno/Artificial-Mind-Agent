"""Generation rotation behaviour."""

from __future__ import annotations

from pathlib import Path

from artificial_mind.evolution import GenerationManager


def _seed(tmp_path: Path) -> GenerationManager:
    journal = tmp_path / "journal"
    journal.mkdir(parents=True)
    (journal / "0001.md").write_text("# Cycle 1\n", encoding="utf-8")
    (journal / "0002.md").write_text("# Cycle 2\n", encoding="utf-8")

    knowledge = tmp_path / "knowledge.md"
    knowledge.write_text("# K\nentry\n", encoding="utf-8")
    goal = tmp_path / "goal.md"
    goal.write_text("explore", encoding="utf-8")
    identity = tmp_path / "identity.md"
    identity.write_text("collective", encoding="utf-8")
    return GenerationManager(
        root=tmp_path / "generations",
        journal_dir=journal,
        knowledge_path=knowledge,
        goal_path=goal,
        identity_path=identity,
    )


def test_rotate_archives_state_and_clears_journal(tmp_path: Path) -> None:
    gm = _seed(tmp_path)
    target = gm.rotate(legacy_letter="be brave")
    assert target.exists()
    archived = sorted((target / "journal").glob("*.md"))
    assert [p.name for p in archived] == ["0001.md", "0002.md"]
    assert (target / "knowledge.md").exists()
    assert (target / "goal.md").exists()
    assert (target / "identity.md").exists()
    assert "be brave" in (target / "LEGACY.md").read_text(encoding="utf-8")

    # Working journal has been cleared after rotation.
    assert list((tmp_path / "journal").glob("*.md")) == []


def test_next_index_progression(tmp_path: Path) -> None:
    gm = _seed(tmp_path)
    first = gm.rotate("a")
    assert first.name == "gen_001"

    # Re-seed journal so next rotation has something to archive.
    (tmp_path / "journal" / "0003.md").write_text("# Cycle 3\n", encoding="utf-8")
    second = gm.rotate("b")
    assert second.name == "gen_002"

    history = gm.history()
    assert [p.name for p in history] == ["gen_001", "gen_002"]
