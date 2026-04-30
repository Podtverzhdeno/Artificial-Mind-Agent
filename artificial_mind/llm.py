"""Provider-agnostic LLM client.

The codebase has historically depended on ``gigachat`` directly. To make the
project testable, runnable in CI without API keys, and easy to extend with new
providers, every prompt now goes through :class:`LLM`. Selecting a provider is
done by setting :data:`Settings.llm_provider`:

* ``gigachat`` (default) — calls Sber's GigaChat API. Requires
  ``GIGA_CREDENTIALS``.
* ``echo`` — deterministic provider that echoes a structured stub of the
  prompt. Useful for offline development and tests.
* ``custom`` — any callable registered via :meth:`LLM.register`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from artificial_mind.config import Settings

logger = logging.getLogger(__name__)

ProviderFn = Callable[[str, "LLM"], str]


@dataclass
class _ProviderRegistry:
    providers: dict[str, ProviderFn]

    def register(self, name: str, fn: ProviderFn) -> None:
        self.providers[name.lower()] = fn

    def get(self, name: str) -> ProviderFn:
        try:
            return self.providers[name.lower()]
        except KeyError as err:
            raise ValueError(
                f"Unknown LLM provider '{name}'. Registered: {sorted(self.providers)}"
            ) from err


_REGISTRY = _ProviderRegistry(providers={})


class LLM:
    """A thin wrapper around a configured provider.

    Construct directly with explicit settings, or via :meth:`from_settings`.
    Use :meth:`ask` to send a prompt and get a string response. Behaviour for
    multi-turn dialogue is intentionally out of scope — this project keeps
    every cognitive step to a single prompt to make traces easy to inspect.
    """

    def __init__(self, settings: Settings, provider: ProviderFn | None = None):
        self.settings = settings
        self._provider: ProviderFn = provider or _REGISTRY.get(settings.llm_provider)

    @classmethod
    def from_settings(cls, settings: Settings) -> LLM:
        return cls(settings)

    @staticmethod
    def register(name: str, fn: ProviderFn) -> None:
        """Register an additional provider by name."""

        _REGISTRY.register(name, fn)

    def ask(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return ""
        try:
            return self._provider(prompt, self).strip()
        except Exception as exc:  # pragma: no cover - provider error
            logger.exception("LLM provider raised: %s", exc)
            return f"[llm-error: {exc}]"


# --- Built-in providers ---------------------------------------------------


def _echo_provider(prompt: str, _llm: LLM) -> str:
    """Deterministic provider used for tests and offline runs.

    The echo provider returns a short structured response so that downstream
    parsers (planners, criticisers, etc.) still have something useful to chew
    on. The format is documented in tests so it stays stable.
    """

    head = prompt.splitlines()[0][:120] if prompt else ""
    return (
        "[echo]\n"
        f"received: {head}\n"
        "thought: I will reflect on the inputs and choose the smallest useful next step.\n"
        "action: reflect\n"
    )


def _gigachat_provider(prompt: str, llm: LLM) -> str:  # pragma: no cover - I/O
    try:
        from gigachat import GigaChat  # type: ignore
    except ModuleNotFoundError as err:
        raise RuntimeError(
            "gigachat package is not installed. Install with `pip install gigachat`."
        ) from err

    if not llm.settings.giga_credentials:
        raise RuntimeError("GIGA_CREDENTIALS is not set; cannot use gigachat provider.")

    kwargs: dict[str, object] = {
        "credentials": llm.settings.giga_credentials,
        "verify_ssl_certs": False,
    }
    if llm.settings.giga_model:
        kwargs["model"] = llm.settings.giga_model

    client = GigaChat(**kwargs)
    response = client.chat({"messages": [{"role": "user", "content": prompt}]})
    return response.choices[0].message.content


_REGISTRY.register("echo", _echo_provider)
_REGISTRY.register("gigachat", _gigachat_provider)
