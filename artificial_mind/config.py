"""Runtime configuration loaded from environment variables.

The configuration is intentionally small and environment-driven so the agent
can be started without any local settings file. ``.env`` is loaded eagerly via
``python-dotenv`` if present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # pragma: no cover - import guard
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:  # pragma: no cover
    pass


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Container for runtime knobs.

    Use :meth:`Settings.from_env` to load values from the environment;
    construct directly in tests to override defaults deterministically.
    """

    root: Path = field(default_factory=lambda: Path.cwd())
    llm_provider: str = "gigachat"
    giga_credentials: str | None = None
    giga_model: str | None = None
    tick_delay: float = 0.0
    max_bus_history: int = 200
    generation_threshold: int = 50
    discovery_interval: int = 10
    max_cycles: int = 0  # 0 = run forever
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, root: Path | None = None) -> Settings:
        return cls(
            root=Path(root) if root is not None else Path.cwd(),
            llm_provider=os.getenv("AMA_LLM_PROVIDER", "gigachat").lower(),
            giga_credentials=os.getenv("GIGA_CREDENTIALS"),
            giga_model=os.getenv("GIGA_MODEL"),
            tick_delay=_env_float("AMA_TICK_DELAY", 0.0),
            max_bus_history=_env_int("AMA_MAX_BUS_HISTORY", 200),
            generation_threshold=_env_int("AMA_GENERATION_THRESHOLD", 50),
            discovery_interval=_env_int("AMA_DISCOVERY_INTERVAL", 10),
            max_cycles=_env_int("AMA_MAX_CYCLES", 0),
            log_level=os.getenv("AMA_LOG_LEVEL", "INFO").upper(),
        )

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def journal_dir(self) -> Path:
        return self.memory_dir / "journal"

    @property
    def generations_dir(self) -> Path:
        return self.memory_dir / "generations"

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def goal_path(self) -> Path:
        return self.config_dir / "goal.md"

    @property
    def identity_path(self) -> Path:
        return self.config_dir / "identity.md"

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def experiments_dir(self) -> Path:
        return self.root / "experiments"

    @property
    def stop_file(self) -> Path:
        return self.root / "STOP"
