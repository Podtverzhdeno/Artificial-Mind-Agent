"""Shared pytest fixtures.

Every test gets its own temp workspace and a deterministic LLM provider so
no real network calls are made.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from artificial_mind.config import Settings
from artificial_mind.llm import LLM


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "journal").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "skills").mkdir()
    return tmp_path


@pytest.fixture
def settings(workspace: Path) -> Settings:
    return Settings(
        root=workspace,
        llm_provider="echo",
        max_bus_history=50,
        generation_threshold=0,  # disable auto-rotation for unit tests
        discovery_interval=2,
        max_cycles=0,
    )


def _scripted(*responses: str) -> Callable[..., LLM]:
    def factory(settings: Settings) -> LLM:
        seq = list(responses)
        index = {"i": 0}

        def provider(prompt: str, _llm: LLM) -> str:
            if not seq:
                return f"[scripted-empty]\nprompt-len={len(prompt)}"
            value = seq[index["i"] % len(seq)]
            index["i"] += 1
            return value

        return LLM(settings, provider=provider)

    return factory


@pytest.fixture
def scripted_llm():
    """Build an LLM that returns the next response from a fixed list."""

    return _scripted
