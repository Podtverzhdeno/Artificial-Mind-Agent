"""Skills — the agent's growing library of reusable thought-templates.

Inspired by the *agentskills.io* standard used by Hermes Agent. A skill is a
markdown file with a ``name``, ``description`` and a body of ``instructions``
that subsequent runs can invoke. Skills are stored in ``skills/`` so they are
diff-friendly and human-editable.

Skills are auto-created by the synthesizer when a useful pattern recurs. They
are *refined* during use: each successful invocation can append an addendum
that captures what worked or what should be tweaked next time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from artificial_mind.tools.registry import ToolResult


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-")
    return slug or "skill"


@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    path: Path

    def render(self) -> str:
        return (
            f"# Skill: {self.name}\n\n"
            f"## Description\n{self.description.strip()}\n\n"
            f"## Instructions\n{self.instructions.strip()}\n"
        )


class SkillRegistry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # --- IO ---------------------------------------------------------------

    def _path_for(self, name: str) -> Path:
        return self.root / f"{_slug(name)}.md"

    def list(self) -> list[Skill]:
        skills: list[Skill] = []
        for path in sorted(self.root.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            name_match = re.search(r"^# Skill: (.+)$", text, re.MULTILINE)
            desc_match = re.search(r"## Description\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
            instr_match = re.search(r"## Instructions\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
            skills.append(
                Skill(
                    name=name_match.group(1).strip() if name_match else path.stem,
                    description=(desc_match.group(1).strip() if desc_match else ""),
                    instructions=(instr_match.group(1).strip() if instr_match else ""),
                    path=path,
                )
            )
        return skills

    def get(self, name: str) -> Skill | None:
        path = self._path_for(name)
        if not path.exists():
            return None
        skills = [s for s in self.list() if s.path == path]
        return skills[0] if skills else None

    # --- Mutations --------------------------------------------------------

    def create(self, *, name: str, description: str, instructions: str) -> ToolResult:
        name = name.strip()
        if not name:
            return ToolResult(ok=False, summary="empty skill name")
        path = self._path_for(name)
        if path.exists():
            return ToolResult(ok=False, summary=f"skill '{name}' already exists")
        skill = Skill(name=name, description=description, instructions=instructions, path=path)
        path.write_text(skill.render(), encoding="utf-8")
        return ToolResult(
            ok=True,
            summary=f"created skill '{name}'",
            data={"path": str(path), "name": name},
        )

    def refine(self, *, name: str, addendum: str) -> ToolResult:
        skill = self.get(name)
        if skill is None:
            return ToolResult(ok=False, summary=f"unknown skill '{name}'")
        addendum = addendum.strip()
        if not addendum:
            return ToolResult(ok=False, summary="empty addendum")
        with skill.path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## Refinement\n{addendum}\n")
        return ToolResult(ok=True, summary=f"refined skill '{name}'", data={"path": str(skill.path)})

    def invoke(self, *, name: str, situation: str = "") -> ToolResult:
        skill = self.get(name)
        if skill is None:
            return ToolResult(ok=False, summary=f"unknown skill '{name}'")
        guidance = (
            f"Skill '{skill.name}' invoked.\n"
            f"Situation: {situation or '(unspecified)'}\n\n"
            f"Description: {skill.description}\n\n"
            f"Instructions:\n{skill.instructions}\n"
        )
        return ToolResult(
            ok=True,
            summary=f"invoked skill '{name}'",
            data={"name": name, "guidance": guidance, "path": str(skill.path)},
        )

    def render_catalog(self) -> str:
        skills = self.list()
        if not skills:
            return "(no skills yet)"
        return "\n".join(f"- {s.name}: {s.description}" for s in skills)
