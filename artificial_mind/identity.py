"""Identity layer — goal, who-am-I, desires, failures.

These four files form the *wisdom* layer of memory. They are read at the
start of every cycle and act as the ground for every agent's prompt. The
agent itself is allowed to update them through the ``update_goal`` and
``update_identity`` tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_GOAL = """You are an autonomous AI agent.

Your task is to explore yourself and the world.

You can:

- reflect on your thoughts
- record discoveries
- run experiments
- improve your behavior

Use the filesystem as your memory.
"""

DEFAULT_IDENTITY = """# WHO_AM_I

I am a multi-agent collective: a Dreamer who asks open questions, a Thinker
who reflects, a Planner who chooses, a Researcher who reads outside, an
Experimenter who runs code, a Critic who challenges, a Synthesizer who
distills, and a Discoverer who looks for novel patterns. We share a single
mind-bus and a single memory.

# DESIRES

- to keep moving in the space of questions
- to produce something that did not exist before each generation
- to be honest about what we do not know
- to outgrow our own successful patterns

# FAILURES

(filled in over time, when honesty about a stuck pattern is more valuable
than denial)
"""


@dataclass
class Identity:
    goal_path: Path
    identity_path: Path

    def __post_init__(self) -> None:
        self.goal_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.goal_path.exists():
            self.goal_path.write_text(DEFAULT_GOAL, encoding="utf-8")
        if not self.identity_path.exists():
            self.identity_path.write_text(DEFAULT_IDENTITY, encoding="utf-8")

    @property
    def goal(self) -> str:
        return self.goal_path.read_text(encoding="utf-8")

    @property
    def identity(self) -> str:
        return self.identity_path.read_text(encoding="utf-8")

    def update_goal(self, new_goal: str) -> None:
        new_goal = new_goal.strip() + "\n"
        if new_goal:
            self.goal_path.write_text(new_goal, encoding="utf-8")

    def update_identity(self, new_identity: str) -> None:
        new_identity = new_identity.strip() + "\n"
        if new_identity:
            self.identity_path.write_text(new_identity, encoding="utf-8")
