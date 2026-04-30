"""The agent society — every agent is a stateless callable bound to context.

All agents share the same construction signature so the orchestrator can
treat them uniformly. Each agent's :meth:`run` returns a single
:class:`~artificial_mind.bus.Thought`, which is also posted to the bus.

Available agents:

* :class:`~artificial_mind.agents.dreamer.Dreamer` — generates open-ended
  hypotheses and questions.
* :class:`~artificial_mind.agents.thinker.Thinker` — reflects on context and
  recent bus chatter.
* :class:`~artificial_mind.agents.planner.Planner` — chooses a tool plus
  arguments from the registry.
* :class:`~artificial_mind.agents.researcher.Researcher` — designs a research
  query (the planner is responsible for actually firing tools).
* :class:`~artificial_mind.agents.experimenter.Experimenter` — designs an
  experiment around a hypothesis.
* :class:`~artificial_mind.agents.critic.Critic` — challenges the most recent
  thoughts and the result of the executed action.
* :class:`~artificial_mind.agents.synthesizer.Synthesizer` — distils the
  cycle into a knowledge entry when worthwhile.
* :class:`~artificial_mind.agents.discoverer.Discoverer` — looks across the
  bus and journal for novel cross-cycle patterns.
"""

from artificial_mind.agents.base import Agent, AgentContext
from artificial_mind.agents.critic import Critic
from artificial_mind.agents.discoverer import Discoverer
from artificial_mind.agents.dreamer import Dreamer
from artificial_mind.agents.experimenter import Experimenter
from artificial_mind.agents.planner import Planner
from artificial_mind.agents.researcher import Researcher
from artificial_mind.agents.synthesizer import Synthesizer
from artificial_mind.agents.thinker import Thinker

__all__ = [
    "Agent",
    "AgentContext",
    "Critic",
    "Discoverer",
    "Dreamer",
    "Experimenter",
    "Planner",
    "Researcher",
    "Synthesizer",
    "Thinker",
]
