# Artificial Mind Agent

> Self-evolving multi-agent collective inspired by [Rai220/anima](https://github.com/Rai220/anima)
> and [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

The agent is no longer a single linear loop. It is a **society** of specialised
roles sharing a single mind-bus, a layered memory, a growing skills library,
and a generation-based evolution mechanism. Each tick is one collective
thought; over time the collective accumulates durable knowledge, candidate
discoveries, and reusable skills.

> Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the design rationale and the
> mapping back to anima / hermes-agent.

---

## What changed since v0.1

| Old (v0.1) | New (v0.2) |
|---|---|
| 3 agents (think / plan / critique) in a strict line | 8 specialised agents (Dreamer, Thinker, Researcher, Experimenter, Planner, Critic, Synthesizer, Discoverer) |
| 4 hard-coded action strings | A live `ToolRegistry` with 17 built-in tools and runtime-extensible skills |
| Flat journal of cycle markdowns | DIKW memory: episodic journal → semantic `knowledge.md` → wisdom files (`goal.md`, `identity.md`) |
| No inter-agent communication | Persistent `MindBus` (`memory/mind_bus.jsonl`) — every agent reads peers' recent thoughts |
| No discovery surface | `Discoverer` agent that writes to `memory/discoveries.md` with confidence + evidence |
| No skill memory | `skills/*.md` — Hermes-style skills, auto-creatable, refinable, invokable |
| No evolution | anima-style **generations**: rotate state into `memory/generations/gen_NNN/` with a `LEGACY.md` letter |
| Direct `gigachat` import | Provider-agnostic `LLM` (default GigaChat, optional `echo` for offline/CI) |
| No CLI | `python -m artificial_mind {run|tick|status|evolve|discover|mcp}` |
| No tests, no CI | `pytest` suite + GitHub Actions on Python 3.10 / 3.11 / 3.12 |

---

## Quick start

```bash
git clone https://github.com/Podtverzhdeno/Artificial-Mind-Agent.git
cd Artificial-Mind-Agent

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Set GIGA_CREDENTIALS=...   to talk to GigaChat
# Or set AMA_LLM_PROVIDER=echo for an offline deterministic run

python -m artificial_mind tick     # run one collective thought
python -m artificial_mind status   # snapshot of memory state
python -m artificial_mind run      # run forever until STOP file appears
```

Plain `python main.py` still works and is equivalent to `python -m artificial_mind run`.

### Stopping the loop

Create an empty `STOP` file in the workspace, or have the agent itself call the
`request_stop` tool. The orchestrator checks for the file at the start of every
tick.

### Forcing evolution

```bash
python -m artificial_mind evolve "carry kindness forward"
```

This archives the current journal/knowledge/goal/identity into a fresh
`memory/generations/gen_NNN/` directory along with a `LEGACY.md` letter, then
clears the journal so the next generation starts on a clean episodic slate.

---

## Architecture at a glance

```
artificial_mind/
├── orchestrator.py       # one tick = one collective thought
├── llm.py                # provider-agnostic client (gigachat / echo / custom)
├── bus.py                # MindBus — persistent shared stream of thoughts
├── memory.py             # journal (episodic) + knowledge.md (semantic)
├── identity.py           # goal.md + identity.md (wisdom)
├── skills.py             # SkillRegistry — agentskills.io-style markdown
├── evolution.py          # generation rotation + legacy letters
├── discoveries.py        # candidate insights with confidence + evidence
├── world.py              # sandboxed filesystem operations
├── tools/                # built-in tools (17) — composable, schema-tagged
├── agents/               # the society
│   ├── dreamer.py        # opens new questions
│   ├── thinker.py        # honest reflection
│   ├── researcher.py     # external query design
│   ├── experimenter.py   # turns hypotheses into runnable plans
│   ├── planner.py        # picks one tool with arguments
│   ├── critic.py         # challenges action + result
│   ├── synthesizer.py    # promotes durable insights to knowledge
│   └── discoverer.py     # cross-cycle candidate discoveries
├── cli.py                # python -m artificial_mind ...
└── mcp_server.py         # optional MCP server for external clients
```

### Per-tick flow

```
Dreamer  ─┐
Thinker  ─┤
Researcher─┤  →  Planner  →  Tool  →  Critic  →  Synthesizer  →  [Discoverer*]
Experimenter ─┘                                                       │
                                                                       ▼
                                                               memory/discoveries.md
```

`*Discoverer` runs every `AMA_DISCOVERY_INTERVAL` cycles. Generations rotate
either on explicit `evolve` request or every `AMA_GENERATION_THRESHOLD` cycles
(set to `0` to disable auto-rotation).

---

## Tools the agent can use

| Tool | Category | What it does |
|---|---|---|
| `reflect`, `read_bus` | reflection | Pull the latest mind-bus digest into the cycle |
| `write_journal` | reflection | Free-form note appended to `memory/journal/` |
| `remember`, `search_memory` | memory | Append/search distilled knowledge |
| `web_search`, `web_fetch` | research | DuckDuckGo HTML search + URL fetch (no API keys) |
| `run_python` | experiment | Sandboxed `subprocess` Python with timeout |
| `create_experiment` | experiment | Structured experiment doc with hypothesis + plan |
| `create_skill`, `refine_skill`, `invoke_skill` | skill | Hermes-style skill library |
| `update_goal`, `update_identity` | self | The agent rewrites its own purpose / identity |
| `record_discovery` | discovery | Append claim + evidence + confidence to `discoveries.md` |
| `request_stop`, `evolve` | self | Graceful generation transition |

The catalog is dynamic — every registered skill becomes a callable named in the
planner prompt under `## Skills`.

---

## Configuration

All knobs are environment variables (loaded from `.env` if present):

| Variable | Default | Description |
|---|---|---|
| `AMA_LLM_PROVIDER` | `gigachat` | `gigachat`, `echo`, or any name registered via `LLM.register` |
| `GIGA_CREDENTIALS` | — | GigaChat token; required when provider is `gigachat` |
| `GIGA_MODEL` | (provider default) | Optional GigaChat model name |
| `AMA_TICK_DELAY` | `0` | Seconds between cycles |
| `AMA_MAX_BUS_HISTORY` | `200` | Recent thoughts retained in memory |
| `AMA_GENERATION_THRESHOLD` | `50` | Auto-rotate after N cycles (0 = never) |
| `AMA_DISCOVERY_INTERVAL` | `10` | Run discoverer every N cycles |
| `AMA_MAX_CYCLES` | `0` | Cap total cycles (0 = forever) |
| `AMA_LOG_LEVEL` | `INFO` | Standard logging level |

---

## Testing

```bash
pytest -q
ruff check .
```

Tests use the deterministic `echo` LLM provider, so they never touch the
network. CI runs the same suite on Python 3.10 / 3.11 / 3.12.

---

## Inspirations

* [Rai220/anima](https://github.com/Rai220/anima) — generation cycles, the
  "путь > цель" stance, the idea that what travels forward is *only* the file
  the previous generation chose to write.
* [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) — the
  closed learning loop: skills auto-created from experience, refined during use.
* [The 13-generation autonomous agent
  experiment](https://github.com/Rai220/anima#итоговый-отчёт) — the original
  motivation for an agent that can keep moving in the space of questions.

## Safety

The agent has filesystem access and can fire HTTP requests. Keep it in an
isolated environment (VM, container) without access to personal data. Treat
every "discovery" as a candidate, not a fact.

## License

MIT
