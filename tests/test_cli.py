"""Smoke tests for the CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from artificial_mind.cli import main


@pytest.fixture(autouse=True)
def chdir_workspace(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("AMA_LLM_PROVIDER", "echo")


def test_cli_status(capsys: pytest.CaptureFixture) -> None:
    code = main(["status"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "cycle" in payload
    assert "tools" in payload


def test_cli_evolve_rotates(workspace: Path, capsys: pytest.CaptureFixture) -> None:
    # Ensure the workspace has at least one journal file so rotation has
    # something concrete to archive.
    (workspace / "memory" / "journal" / "0001.md").write_text("# Cycle 1\n", encoding="utf-8")
    code = main(["evolve", "carry kindness forward"])
    assert code == 0
    out = capsys.readouterr().out
    assert "rotated generation" in out
    assert any((workspace / "memory" / "generations").glob("gen_*"))


def test_cli_default_invocation_runs_once(workspace: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMA_MAX_CYCLES", "1")
    code = main([])
    assert code == 0
    captured = capsys.readouterr().out
    assert "completed 1 cycle" in captured
    assert os.listdir(workspace / "memory" / "journal")
