"""Built-in tools available to the agent collective.

Each tool returns a :class:`ToolResult` with a short ``summary`` (used by the
critic and the journal) and a richer ``data`` payload (used downstream by
synthesizers, discoverers, and skills).

Tools are intentionally small and orthogonal — every richer behaviour should
emerge from agents *composing* tools, not from a single mega-tool.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from artificial_mind.tools.registry import Tool, ToolContext, ToolRegistry, ToolResult


def _truncate(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --- Reflection / journal ------------------------------------------------


def _reflect(*, ctx: ToolContext, topic: str = "") -> ToolResult:
    topic = topic.strip() or "the current state of the collective"
    bus = ctx.bus.render(8)
    summary = f"Reflected on {topic!r}; pulled in {len(ctx.bus)} bus entries."
    return ToolResult(ok=True, summary=summary, data={"bus_digest": bus, "topic": topic})


def _write_journal(*, ctx: ToolContext, body: str) -> ToolResult:
    body = body.strip()
    if not body:
        return ToolResult(ok=False, summary="empty body")
    cycle = ctx.memory.cursor - 1 if ctx.memory.cursor > 1 else ctx.memory.cursor
    target = ctx.memory.journal_dir / f"note_{int(time.time())}.md"
    target.write_text(f"# Note (cycle {cycle})\n\n{body}\n", encoding="utf-8")
    return ToolResult(ok=True, summary=f"wrote {target.name}", data={"path": str(target)})


def _remember(*, ctx: ToolContext, heading: str, body: str) -> ToolResult:
    ctx.memory.append_knowledge(heading, body)
    return ToolResult(ok=True, summary=f"appended knowledge: {heading[:60]}")


def _search_memory(*, ctx: ToolContext, query: str, max_hits: int = 5) -> ToolResult:
    hits = ctx.memory.search_knowledge(query, max_hits=max_hits)
    summary = f"found {len(hits)} hit(s) for {query!r}"
    return ToolResult(ok=True, summary=summary, data={"hits": hits})


# --- Web ------------------------------------------------------------------


def _ddg_html_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Light-weight DuckDuckGo HTML scrape — works without an API key.

    Returns a list of ``{title, href, snippet}`` dicts. Resilient to small
    markup changes: we look for anchor tags with the well-known classes used
    by DuckDuckGo's ``html.duckduckgo.com`` endpoint.
    """

    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "ArtificialMindAgent/0.2"})
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8", errors="ignore")

    pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
        r'(?:.*?<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>)?',
        re.DOTALL,
    )
    results: list[dict[str, str]] = []
    for match in pattern.finditer(body):
        href, title_html, snippet_html = match.groups()
        title = html_lib.unescape(re.sub(r"<[^>]+>", "", title_html or "")).strip()
        snippet = html_lib.unescape(re.sub(r"<[^>]+>", "", snippet_html or "")).strip()
        href = html_lib.unescape(href)
        if href.startswith("//"):
            href = "https:" + href
        results.append({"title": title, "href": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _web_search(*, ctx: ToolContext, query: str, max_results: int = 5) -> ToolResult:  # noqa: ARG001
    try:
        results = _ddg_html_search(query, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            summary=f"web_search failed: {type(exc).__name__}: {exc}",
            data={"query": query},
        )
    summary = f"found {len(results)} result(s) for {query!r}"
    return ToolResult(ok=True, summary=summary, data={"query": query, "results": results})


def _web_fetch(*, ctx: ToolContext, url: str, max_chars: int = 4000) -> ToolResult:  # noqa: ARG001
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ArtificialMindAgent/0.2"})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, summary=f"web_fetch failed: {exc}", data={"url": url})
    text = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(re.sub(r"\s+", " ", text)).strip()
    text = _truncate(text, max_chars)
    return ToolResult(ok=True, summary=f"fetched {url} ({len(text)} chars)", data={"url": url, "text": text})


# --- Code execution ------------------------------------------------------


def _run_python(*, ctx: ToolContext, code: str, timeout: int = 10) -> ToolResult:
    code = code.strip()
    if not code:
        return ToolResult(ok=False, summary="empty code")
    target_dir: Path = ctx.settings.experiments_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    script = target_dir / f"run_{int(time.time())}.py"
    script.write_text(code, encoding="utf-8")
    try:
        completed = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ctx.settings.root),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, summary=f"timeout after {timeout}s", data={"script": str(script)})
    output = (completed.stdout or "") + (completed.stderr or "")
    output = _truncate(output, 4000)
    ok = completed.returncode == 0
    summary = f"python exited with code {completed.returncode}"
    return ToolResult(
        ok=ok,
        summary=summary,
        data={"script": str(script), "stdout": completed.stdout, "stderr": completed.stderr, "output": output},
    )


# --- Experiments --------------------------------------------------------


def _create_experiment(*, ctx: ToolContext, hypothesis: str, plan: str = "") -> ToolResult:
    hypothesis = hypothesis.strip()
    if not hypothesis:
        return ToolResult(ok=False, summary="empty hypothesis")
    target_dir: Path = ctx.settings.experiments_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    index = len(list(target_dir.glob("experiment_*.md"))) + 1
    path = target_dir / f"experiment_{index:03d}.md"
    body = (
        f"# Experiment {index}\n\n"
        f"## Hypothesis\n{hypothesis}\n\n"
        f"## Plan\n{plan or '(plan to be filled in)'}\n\n"
        "## Observations\n(not yet observed)\n\n"
        "## Conclusion\n(not yet concluded)\n"
    )
    path.write_text(body, encoding="utf-8")
    return ToolResult(ok=True, summary=f"created {path.name}", data={"path": str(path), "hypothesis": hypothesis})


# --- Skills ---------------------------------------------------------------


def _create_skill(*, ctx: ToolContext, name: str, description: str, instructions: str) -> ToolResult:
    return ctx.skills.create(name=name, description=description, instructions=instructions)


def _refine_skill(*, ctx: ToolContext, name: str, addendum: str) -> ToolResult:
    return ctx.skills.refine(name=name, addendum=addendum)


def _invoke_skill(*, ctx: ToolContext, name: str, situation: str = "") -> ToolResult:
    return ctx.skills.invoke(name=name, situation=situation)


# --- Self-modification ---------------------------------------------------


def _update_goal(*, ctx: ToolContext, new_goal: str) -> ToolResult:
    ctx.identity.update_goal(new_goal)
    return ToolResult(ok=True, summary="goal updated", data={"goal": ctx.identity.goal})


def _update_identity(*, ctx: ToolContext, new_identity: str) -> ToolResult:
    ctx.identity.update_identity(new_identity)
    return ToolResult(ok=True, summary="identity updated")


# --- Discoveries ---------------------------------------------------------


def _record_discovery(*, ctx: ToolContext, claim: str, evidence: str = "", confidence: float = 0.5) -> ToolResult:
    return ctx.discoveries.record(claim=claim, evidence=evidence, confidence=confidence)


# --- Bus introspection ---------------------------------------------------


def _read_bus(*, ctx: ToolContext, n: int = 12, kinds: str = "") -> ToolResult:
    kinds_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    digest = ctx.bus.render(n)
    return ToolResult(
        ok=True,
        summary=f"read {min(n, len(ctx.bus))} bus entries",
        data={"digest": digest, "kinds": kinds_list},
    )


# --- Stop / evolve --------------------------------------------------------


def _request_stop(*, ctx: ToolContext, reason: str = "") -> ToolResult:
    ctx.settings.stop_file.write_text(reason or "agent requested stop\n", encoding="utf-8")
    return ToolResult(ok=True, summary="STOP file written", data={"reason": reason})


def _evolve(*, ctx: ToolContext, legacy_letter: str = "") -> ToolResult:
    return ToolResult(
        ok=True,
        summary="evolution requested; orchestrator will rotate generation at end of cycle",
        data={"legacy": legacy_letter, "_evolve_request": True},
    )


# --- Metadata helper ------------------------------------------------------


def register_all(registry: ToolRegistry, ctx: ToolContext) -> None:
    """Register every built-in tool against ``registry``.

    The signature ``ctx`` is captured by closure so each tool sees the live
    context object even if attributes mutate.
    """

    def make(fn):
        def wrapper(**kwargs):
            return fn(ctx=ctx, **kwargs)

        return wrapper

    tools: list[Tool] = [
        Tool(
            name="reflect",
            description="Pause and read the recent mind-bus to set context.",
            fn=make(_reflect),
            schema={"topic": "str"},
            category="reflection",
        ),
        Tool(
            name="write_journal",
            description="Add a free-form note to the journal directory.",
            fn=make(_write_journal),
            schema={"body": "str"},
            category="reflection",
        ),
        Tool(
            name="remember",
            description="Append a distilled principle/observation to knowledge.md.",
            fn=make(_remember),
            schema={"heading": "str", "body": "str"},
            category="memory",
        ),
        Tool(
            name="search_memory",
            description="Search the semantic knowledge base.",
            fn=make(_search_memory),
            schema={"query": "str", "max_hits": "int"},
            category="memory",
        ),
        Tool(
            name="web_search",
            description="DuckDuckGo HTML search (no API key required).",
            fn=make(_web_search),
            schema={"query": "str", "max_results": "int"},
            category="research",
        ),
        Tool(
            name="web_fetch",
            description="Fetch a URL and return cleaned text.",
            fn=make(_web_fetch),
            schema={"url": "str", "max_chars": "int"},
            category="research",
        ),
        Tool(
            name="run_python",
            description="Execute a short Python snippet inside experiments/ with timeout.",
            fn=make(_run_python),
            schema={"code": "str", "timeout": "int"},
            category="experiment",
        ),
        Tool(
            name="create_experiment",
            description="Create a structured experiment markdown with hypothesis & plan.",
            fn=make(_create_experiment),
            schema={"hypothesis": "str", "plan": "str"},
            category="experiment",
        ),
        Tool(
            name="create_skill",
            description="Register a new reusable skill in the skills library.",
            fn=make(_create_skill),
            schema={"name": "str", "description": "str", "instructions": "str"},
            category="skill",
        ),
        Tool(
            name="refine_skill",
            description="Append refinement notes to an existing skill.",
            fn=make(_refine_skill),
            schema={"name": "str", "addendum": "str"},
            category="skill",
        ),
        Tool(
            name="invoke_skill",
            description="Read a skill's playbook and return it as guidance.",
            fn=make(_invoke_skill),
            schema={"name": "str", "situation": "str"},
            category="skill",
        ),
        Tool(
            name="update_goal",
            description="Rewrite the agent's main goal (config/goal.md).",
            fn=make(_update_goal),
            schema={"new_goal": "str"},
            category="self",
        ),
        Tool(
            name="update_identity",
            description="Rewrite the WHO_AM_I / DESIRES / FAILURES identity file.",
            fn=make(_update_identity),
            schema={"new_identity": "str"},
            category="self",
        ),
        Tool(
            name="record_discovery",
            description="Write a candidate discovery with evidence and confidence to discoveries.md.",
            fn=make(_record_discovery),
            schema={"claim": "str", "evidence": "str", "confidence": "float"},
            category="discovery",
        ),
        Tool(
            name="read_bus",
            description="Return the digest of recent thoughts on the mind-bus.",
            fn=make(_read_bus),
            schema={"n": "int", "kinds": "str"},
            category="reflection",
        ),
        Tool(
            name="request_stop",
            description="Write a STOP file so the orchestrator ends this generation.",
            fn=make(_request_stop),
            schema={"reason": "str"},
            category="self",
        ),
        Tool(
            name="evolve",
            description="Ask the orchestrator to rotate the generation at end of cycle.",
            fn=make(_evolve),
            schema={"legacy_letter": "str"},
            category="self",
        ),
    ]

    for tool in tools:
        registry.register(tool)


# --- Argument parsing helper --------------------------------------------


def parse_args_blob(blob: str) -> dict[str, str]:
    """Parse a planner-emitted ``key=value; key=value`` argument blob.

    The blob also accepts JSON via ``{...}`` for callers that want richer
    types. Whitespace and trailing punctuation are tolerated. Unknown keys
    are kept as strings; tools that need typed arguments coerce internally.
    """

    blob = blob.strip()
    if not blob:
        return {}
    if blob.startswith("{") and blob.endswith("}"):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    out: dict[str, str] = {}
    for chunk in re.split(r"[;\n]", blob):
        if "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        out[key.strip()] = value.strip().strip("\"'")
    return out
