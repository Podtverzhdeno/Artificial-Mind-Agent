# Architecture

This document is the design rationale for v0.2 of Artificial Mind Agent. It
maps the project's components back to the two reference designs we drew from:
[Rai220/anima](https://github.com/Rai220/anima) and
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

## Goals

The user goal is *"agents that constantly evolve, learn something new, and
share thoughts; eventually the architecture should be capable of producing
discoveries"*. Translated to four concrete properties:

1. **Continual learning.** State must accumulate across runs in a way that
   future runs can build on rather than just replay.
2. **Shared cognition.** A useful thought of one agent should change what
   subsequent agents do — without going through a single planner bottleneck.
3. **Evolution.** The agent should be able to change *itself* — its goal, its
   identity, its toolset — when honesty demands it. And it must be able to
   start over without losing the durable lessons.
4. **Candidate discoveries.** The system must produce surface artefacts a human
   reviewer can actually inspect, with provenance and a confidence signal.

## Layered memory (DIKW)

Borrowed from anima's generation-1 file structure (the "DIKW pyramid" hint in
[`AGENTS.md`](https://github.com/Rai220/anima/blob/master/generation_1/AGENTS.md)),
re-implemented as actual Python data structures.

| Layer | Storage | Owner | Why |
|---|---|---|---|
| Data — **episodic** | `memory/journal/NNNN.md` | `Memory.store_cycle` | one record per tick, fully reconstructible from text |
| Information — **mind bus** | `memory/mind_bus.jsonl` | `MindBus` | structured per-thought events with `kind`, `cycle`, `agent` |
| Knowledge — **semantic** | `memory/knowledge.md` | `Memory.append_knowledge` (driven by `Synthesizer`) | distilled, durable principles |
| Wisdom — **identity** | `config/goal.md`, `config/identity.md` | `Identity` | re-read every cycle; the agent may rewrite them |
| Discoveries — **candidate** | `memory/discoveries.md` | `DiscoveryEngine` | high-confidence artefacts surfaced for human review |

A key invariant: every layer is plain text the agent can edit through tools,
so future generations can re-discover their own past without breaking on a
schema change.

## Mind-bus — the shared cognition substrate

`MindBus` is intentionally simple: an append-only `jsonl` log of `Thought`
records. Every agent posts one thought per tick (sometimes more); every agent
reads the recent N thoughts before forming its own. This is the difference
between "a pipeline of agents" and "a society": the planner doesn't direct the
critic; the critic reads the bus and pushes back.

Key design choices:

* **Persistence by default.** The collective wakes up across process restarts
  with full context.
* **Bounded in-memory deque.** Big production runs would otherwise OOM after
  thousands of cycles. The full history stays on disk.
* **No deletes.** The only way to "correct" a thought is to post a new one
  with `refs` pointing at the old one. This keeps the trace honest.

## Skills — the closed learning loop (hermes-style)

`SkillRegistry` is the project's homage to
[hermes-agent's skill system](https://github.com/NousResearch/hermes-agent#a-closed-learning-loop):
skills are markdown files (compatible with the [agentskills.io](https://agentskills.io)
shape) that any cycle can register, refine and invoke. Three differences from
the v0.1 hard-coded action list:

1. **Open-ended.** Any cycle can add a new skill via `create_skill`.
2. **Self-improving.** `refine_skill` appends an addendum so future invocations
   benefit from each use.
3. **First-class in the planner prompt.** The planner sees skills alongside
   built-in tools and can pick `invoke_skill` as just another action.

## Generations — anima-style evolution

`GenerationManager.rotate(legacy_letter)` is the project's homage to
[anima's generation directories](https://github.com/Rai220/anima#что-это).
The semantics:

* The next generation inherits **only** what was written into `LEGACY.md` —
  not the journal, not the knowledge file, not the bus.
* Everything else is archived under `memory/generations/gen_NNN/`.
* The journal is cleared (the next generation starts on a clean episodic
  slate).
* `knowledge.md`, `goal.md` and `identity.md` are *kept* in the working tree
  but archived alongside; the agent decides explicitly whether to clear them.

This is intentionally lossy. From anima:

> "Design for forgetting, not remembering. Factual knowledge decays with a
> half-life of ~2 generations. Process knowledge ('how to think') survives
> because each generation rediscovers it independently."

The `LEGACY.md` letter is therefore the only honest handoff: a question to the
next generation, not an answer.

## The agent society

Each agent is a stateless callable; the orchestrator constructs them per tick
with a shared :class:`AgentContext` so they can read the bus, the memory and
the identity.

| Agent | Responsibility | Output kind on the bus |
|---|---|---|
| `Dreamer` | Opens an unexplored question or analogy | `dream` |
| `Thinker` | Honest reflection on current state | `reflection` |
| `Researcher` | Designs a precise external query | `research_query` |
| `Experimenter` | Turns a hypothesis into a runnable plan | `experiment_design` |
| `Planner` | Chooses ONE tool with arguments | `plan` |
| executor (orchestrator) | Fires the tool | `action_result` |
| `Critic` | Verdict: useful / weak / busywork | `critique` |
| `Synthesizer` | Promotes a durable insight (or `NOTHING_TO_DISTIL`) | `synthesis` |
| `Discoverer` (every N) | Surfaces a candidate discovery (or `NO_DISCOVERY`) | `discovery_candidate` |

The 8-role split is deliberate: it forces honesty (the Critic must read the
result; the Synthesizer must say `NOTHING_TO_DISTIL` when there's nothing to
distil; the Discoverer must say `NO_DISCOVERY` when nothing crosses cycles).
This is the structural equivalent of anima's principle:

> "Действуй, а не планируй действовать. Рефлексия ценна, но не должна
> превышать создание."

## Tools — replacing placeholder strings

The original `executor.py` returned strings like `"Agent reflected internally."`.
The new `ToolRegistry` exposes 17 *actually-doing-something* tools:

* `web_search` / `web_fetch` — DuckDuckGo HTML scrape (no API key) and URL
  fetcher with HTML stripping.
* `run_python` — `subprocess` invocation of the snippet inside `experiments/`
  with a timeout. Gives the experimenter a closed feedback loop.
* `create_experiment` — produces a structured markdown with hypothesis, plan,
  observations and conclusion sections.
* `create_skill`, `refine_skill`, `invoke_skill` — the hermes-style loop.
* `update_goal`, `update_identity` — the agent edits its own wisdom layer.
* `evolve`, `request_stop` — the agent participates in its own life-cycle.

Each tool returns a structured `ToolResult` (`ok`, `summary`, `data`) so the
critic gets a clean signal and the synthesizer can read structured payloads.

## LLM abstraction

The original code was hard-wired to GigaChat, which made testing and
non-network operation hard. `LLM` is now a tiny wrapper around a registry of
named providers:

* `gigachat` (default) — production.
* `echo` — deterministic stub used in tests and offline/CI runs.
* `custom` — `LLM.register("name", fn)` lets a user plug in OpenAI, OpenRouter,
  a local model, or anything that maps `prompt -> str`.

This keeps every cognitive step a single prompt — making traces easy to
inspect — while allowing the user to swap models without code changes.

## CLI and MCP

`cli.py` exposes the orchestrator through `python -m artificial_mind`. The
optional `mcp_server.py` (gated behind the `mcp` extra) wraps the same API so
any MCP-aware client can drive the collective tick-by-tick — directly inspired
by the sister project [`gigaspeech`](https://github.com/Podtverzhdeno/gigaspeech).

## What is *not* in v0.2 (intentional next steps)

* **Parallel sub-agents.** Hermes-agent supports spawning isolated sub-agents
  for parallel workstreams. We deliberately stayed with a single-process
  orchestrator for v0.2; adding `concurrent.futures`-backed sub-agents is a
  natural next iteration.
* **Vector memory.** `search_memory` is a substring counter. Plug in
  `chromadb` (already used in the sister project `gigaspeech`) when context
  windows start to matter.
* **Cron / schedules.** Hermes has built-in cron. We rely on whatever process
  manager runs the loop today.
* **Multi-modal channels.** Telegram / Discord gateways are out of scope; the
  MCP server already covers the most useful external surface.

## Reading order for new contributors

1. `artificial_mind/orchestrator.py` — the tick.
2. `artificial_mind/agents/*.py` — what each role does.
3. `artificial_mind/tools/builtin.py` — the action surface.
4. `artificial_mind/memory.py` + `artificial_mind/bus.py` — the substrate.
5. `tests/test_orchestrator.py` — end-to-end worked examples.
