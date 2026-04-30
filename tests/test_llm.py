"""LLM provider abstraction."""

from __future__ import annotations

from artificial_mind.config import Settings
from artificial_mind.llm import LLM


def test_echo_provider_returns_structured_response() -> None:
    settings = Settings(llm_provider="echo")
    llm = LLM.from_settings(settings)
    out = llm.ask("Hello collective")
    assert "[echo]" in out
    assert "received: Hello collective" in out


def test_unknown_provider_raises() -> None:
    settings = Settings(llm_provider="missing-provider")
    try:
        LLM.from_settings(settings)
    except ValueError as exc:
        assert "Unknown LLM provider" in str(exc)
    else:  # pragma: no cover - explicit failure
        raise AssertionError("expected ValueError for unknown provider")


def test_register_custom_provider() -> None:
    LLM.register("custom-test", lambda prompt, _llm: f"got:{prompt}")
    settings = Settings(llm_provider="custom-test")
    llm = LLM.from_settings(settings)
    assert llm.ask("ping") == "got:ping"
