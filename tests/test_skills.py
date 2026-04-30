"""Skills registry behaviour."""

from __future__ import annotations

from pathlib import Path

from artificial_mind.skills import SkillRegistry


def test_create_lists_and_invokes(tmp_path: Path) -> None:
    skills = SkillRegistry(tmp_path)
    create = skills.create(
        name="Distil cycle",
        description="Compress a cycle into one paragraph.",
        instructions="1. Read journal.\n2. Compress.\n3. Append to knowledge.",
    )
    assert create.ok

    listed = skills.list()
    assert len(listed) == 1
    assert listed[0].name == "Distil cycle"

    invoke = skills.invoke(name="Distil cycle", situation="cycle 5 just ended")
    assert invoke.ok
    assert "cycle 5 just ended" in invoke.data["guidance"]


def test_create_rejects_duplicates(tmp_path: Path) -> None:
    skills = SkillRegistry(tmp_path)
    skills.create(name="x", description="d", instructions="i")
    second = skills.create(name="x", description="d", instructions="i")
    assert not second.ok


def test_refine_appends(tmp_path: Path) -> None:
    skills = SkillRegistry(tmp_path)
    skills.create(name="x", description="d", instructions="i")
    skills.refine(name="x", addendum="now also do Y")
    skill = skills.get("x")
    assert skill is not None
    assert "now also do Y" in skill.path.read_text(encoding="utf-8")


def test_refine_unknown_skill_fails(tmp_path: Path) -> None:
    skills = SkillRegistry(tmp_path)
    result = skills.refine(name="ghost", addendum="a")
    assert not result.ok
