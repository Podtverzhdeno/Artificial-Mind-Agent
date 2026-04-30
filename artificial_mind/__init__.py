"""Artificial Mind Agent — self-evolving multi-agent collective.

The package exposes a small public surface:

* :class:`artificial_mind.orchestrator.Orchestrator` runs the main loop.
* :class:`artificial_mind.bus.MindBus` is the shared thought stream.
* :class:`artificial_mind.memory.Memory` is the layered memory store.
* :class:`artificial_mind.tools.registry.ToolRegistry` registers callable tools.
* :class:`artificial_mind.llm.LLM` is the provider-agnostic LLM client.
"""

from artificial_mind.config import Settings
from artificial_mind.llm import LLM

__all__ = ["LLM", "Settings", "__version__"]

__version__ = "0.2.0"
