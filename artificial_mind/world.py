"""Sandboxed filesystem operations for the agent.

The agent is allowed to read and write inside a designated *workspace* — a
subtree of the project root. Direct ``open(...)`` calls in tools and agents
should go through :class:`World` so that we can:

1. enforce path containment (no escaping with ``..`` or absolute paths);
2. produce predictable error messages;
3. log every modification to the mind bus or journal.

The class is intentionally tiny — it is not a security boundary against an
adversarial agent, only a convenience that prevents accidental writes outside
the workspace during normal operation.
"""

from __future__ import annotations

from pathlib import Path


class WorldError(RuntimeError):
    """Raised when a path operation escapes the workspace or violates rules."""


class World:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # --- Path helpers -----------------------------------------------------

    def resolve(self, path: str | Path) -> Path:
        candidate = (self.root / path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as err:
            raise WorldError(f"Path '{path}' escapes workspace at {self.root}") from err
        return candidate

    def relative(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.root))

    # --- File ops ---------------------------------------------------------

    def read(self, path: str | Path, default: str | None = None) -> str:
        target = self.resolve(path)
        if not target.exists():
            if default is None:
                raise FileNotFoundError(target)
            return default
        return target.read_text(encoding="utf-8")

    def write(self, path: str | Path, content: str) -> Path:
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def append(self, path: str | Path, content: str) -> Path:
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return target

    def list(self, path: str | Path = ".") -> list[str]:
        target = self.resolve(path)
        if not target.exists():
            return []
        if target.is_file():
            return [target.name]
        return sorted(item.name for item in target.iterdir())

    def exists(self, path: str | Path) -> bool:
        try:
            return self.resolve(path).exists()
        except WorldError:
            return False
