"""Live LangGraph validation agent for averth.

Runs a REAL LangGraph graph against REAL read-only public HTTP APIs and
meters it with AverthCallbackHandler (the 3-line integration).

Graph shape (exercises everything the meter must handle):
    plan (stub LLM, non-streamed)
      -> fan-out via Send: [search_ddg || github_lookup] (parallel tools)
      -> aggregate (fan-in)
      -> fetch_flaky (real HTTP; fails per-variant, retried via graph loop)
      -> report (stub LLM, STREAMED)

Variants:
    clean : flaky_fetch returns 200 on first try        -> success
    flaky : flaky_fetch 500s twice, then 200            -> success, 2 retries
    doomed: flaky_fetch 500s three times, then raise   -> FAILED attempt

LLM situation: no model API key and no provider SDK credentials exist in
this environment, so orchestration uses StubChatModel (stub_model.py), a
deterministic local stand-in. Token counts are REAL tiktoken measurements
of the actual prompt/completion strings; cost flows through averth's
documented estimate fallback and is flagged in unpriced_models.
Tool calls, latency, retries, parallelism, and failures are 100% real.

Usage:
    .venv/bin/python live_agent.py
Outputs (in this directory):
    ledger.json   - sanitized ledger via importers.common.ledger_from_tracker
    events.jsonl  - EVENT-schema reconstruction of every attempt (CLI input)
    pnl.json      - in-process tracker.pnl() (ground truth for validation)
    run_log.txt   - per-run wall-clock, variant, outcome
"""

import json
import os
import sys
import time
import traceback

sys.path.insert(0, "/home/hatch/workspace/averth")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from averth import Tracker
from averth.integrations import AverthCallbackHandler
from averth.importers import common as importer_common
from stub_model import StubChatModel

HERE = os.path.dirname(os.path.abspath(__file__))
HTTP_TIMEOUT = 20

# ---------------------------------------------------------------- tools ---
# Read-only public APIs. Every call below hits the real network.


@tool
def web_search(query: str) -> str:
    """Search the web via the DuckDuckGo instant-answer API (no key)."""
    r = requests.get("https://api.duckduckgo.com/",
                     params={"q": query, "format": "json"}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    parts = [data.get("AbstractText") or "", data.get("Answer") or ""]
    for t in (data.get("RelatedTopics") or [])[:3]:
        if isinstance(t, dict):
            parts.append(t.get("Text", ""))
    text = " ".join(p for p in parts if p).strip()
    return (text[:800] or "(no instant answer; empty result set)") + f" [q={query}]"


@tool
def github_lookup(query: str) -> str:
    """Look up public GitHub repositories matching a query (unauthenticated)."""
    r = requests.get("https://api.github.com/search/repositories",
                     params={"q": query, "per_page": 3, "sort": "stars"},
                     headers={"Accept": "application/vnd.github+json",
                              "User-Agent": "averth-validation"},
                     timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    items = r.json().get("items", [])
    lines = [f'{it["full_name"]} (stars={it["stargazers_count"]}): '
             f'{(it.get("description") or "")[:120]}' for it in items]
    return "\n".join(lines) + f"\n[q={query}]"


@tool
def flaky_fetch(url: str, fail_mode: str, attempt_no: int) -> str:
    """Fetch a URL that fails on purpose for some variants (httpbin).

    fail_mode 'flaky': HTTP 500 on attempt_no 0 and 1, 200 after.
    fail_mode 'doomed': HTTP 500 always. Anything else: 200.
    """
    if fail_mode == "flaky" and attempt_no < 2:
        code = 500
    elif fail_mode == "doomed":
        code = 500
    else:
        code = 200
    r = requests.get(f"https://httpbin.org/status/{code}", timeout=HTTP_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"flaky_fetch: upstream returned {r.status_code} "
                           f"(mode={fail_mode}, attempt={attempt_no})")
    return f"fetched {url} OK (mode={fail_mode}, attempt={attempt_no})"


# ---------------------------------------------------------------- graph ---

class S(TypedDict, total=False):
    case_id: str
    query: str
    variant: str
    plan: str
    search_result: str
    github_result: str
    flaky_result: str
    flaky_retries: int
    report: str


HANDLER = None  # set in main(); nodes close over it
PLAN_MODEL = StubChatModel()
REPORT_MODEL = StubChatModel(streaming=True)


def node_plan(state: S):
    msg = PLAN_MODEL.invoke(
        [HumanMessage(content="PLAN_REQUEST " + state["query"])],
        config={"callbacks": [HANDLER]})
    return {"plan": msg.content}


def fanout(state: S):
    return [Send("search_ddg", {"query": state["query"]}),
            Send("github_lookup", {"query": state["query"]})]


def node_search_ddg(state: S):
    out = web_search.invoke({"query": state["query"]},
                            config={"callbacks": [HANDLER]})
    return {"search_result": out}


def node_github_lookup(state: S):
    out = github_lookup.invoke({"query": state["query"]},
                               config={"callbacks": [HANDLER]})
    return {"github_result": out}


def node_aggregate(state: S):
    evidence = ("WEB:\n" + state.get("search_result", "") +
                "\nGITHUB:\n" + state.get("github_result", ""))
    return {"evidence": evidence}


def node_fetch_flaky(state: S):
    attempt_no = state.get("flaky_retries", 0)
    try:
        out = flaky_fetch.invoke(
            {"url": "https://httpbin.org/status/200",
             "fail_mode": state["variant"],
             "attempt_no": attempt_no},
            config={"callbacks": [HANDLER]})
    except Exception as exc:
        # Genuine failure: on_tool_error already fired -> retry logged.
        # Retry twice, then let the run fail for real.
        if attempt_no + 1 >= 3:
            raise RuntimeError(
                f"flaky_fetch exhausted retries ({exc})") from exc
        return {"flaky_result": f"ERROR: {exc}",
                "flaky_retries": attempt_no + 1}
    return {"flaky_result": out, "flaky_retries": attempt_no + 1}


def route_after_flaky(state: S):
    if state.get("flaky_result", "").startswith("ERROR"):
        return "fetch_flaky"  # retry loop
    return "report"


def node_report(state: S):
    ctx = state.get("evidence", "") + "\nFETCH: " + state.get("flaky_result", "")
    msg = REPORT_MODEL.invoke(
        [HumanMessage(content="Summarize for query '%s':\n%s"
                              % (state["query"], ctx[:1500]))],
        config={"callbacks": [HANDLER]})
    return {"report": msg.content}


def build_graph():
    g = StateGraph(S)
    g.add_node("plan", node_plan)
    g.add_node("search_ddg", node_search_ddg)
    g.add_node("github_lookup", node_github_lookup)
    g.add_node("aggregate", node_aggregate)
    g.add_node("fetch_flaky", node_fetch_flaky)
    g.add_node("report", node_report)
    g.set_entry_point("plan")
    g.add_conditional_edges("plan", fanout)
    g.add_edge("search_ddg", "aggregate")
    g.add_edge("github_lookup", "aggregate")
    g.add_edge("aggregate", "fetch_flaky")
    g.add_conditional_edges("fetch_flaky", route_after_flaky)
    g.add_edge("report", END)
    return g.compile()


# ---------------------------------------------------------------- runs ---

RUNS = [
    # (case_id, query, variant)
    ("RUN-01", "langgraph parallel tool calling", "clean"),
    ("RUN-02", "duckduckgo instant answer api", "clean"),
    ("RUN-03", "rust async runtimes comparison", "clean"),
    ("RUN-04", "sourdough starter hydration", "clean"),
    ("RUN-05", "webgpu browser support", "flaky"),
    ("RUN-06", "crdt collaboration algorithms", "flaky"),
    ("RUN-07", "ebpf observability tools", "clean"),
    ("RUN-08", "sqlite extensions list", "doomed"),
    ("RUN-09", "tiktoken byte pair encoding", "flaky"),
    ("RUN-10", "openapi code generators", "clean"),
    ("RUN-11", "vector database benchmarks", "flaky"),
    ("RUN-12", "htmx vs alpine js", "clean"),
    ("RUN-13", "postgres json indexing", "doomed"),
    ("RUN-14", "wasm garbage collection proposal", "clean"),
    ("RUN-15", "ollama local model serving", "flaky"),
    ("RUN-16", "nats jetstream persistence", "doomed"),
]


def events_from_attempts(tracker):
    """Rebuild EVENT-schema dicts from recorded attempts (for CLI input).

    Pairs each ("model", ...) event tuple with its step's real token counts.
    Order is preserved so retry-path flags survive the round trip.
    """
    lines = []
    for a in tracker.attempts:
        cid = a["case_id"]
        lines.append({"type": "start", "case_id": cid})
        steps = list(a["steps"])
        for ev in a["events"]:
            kind = ev[0]
            if kind in ("model", "model_estimate"):
                it, ot, _c, _rp = steps.pop(0)
                lines.append({"type": "model", "case_id": cid,
                              "provider": ev[1], "model": ev[2],
                              "input_tokens": it, "output_tokens": ot})
            elif kind == "tool":
                lines.append({"type": "tool", "case_id": cid,
                              "name": ev[1], "cost": ev[2]})
            elif kind == "retry":
                lines.append({"type": "retry", "case_id": cid,
                              "reason": ev[1]})
            elif kind == "escalation":
                lines.append({"type": "escalation", "case_id": cid,
                              "minutes": ev[2], "reason": ev[1]})
        lines.append({"type": "end", "case_id": cid,
                      "success": bool(a["success"]),
                      "business_value": 0.0,
                      "reopened": bool(a.get("reopened", False))})
        assert not steps, "unpaired model steps remain"
    return lines


def main():
    global HANDLER
    tracker = Tracker("live-langgraph-validation", budget_per_success=1.00)
    HANDLER = AverthCallbackHandler(tracker)
    app = build_graph()

    log_lines = []
    for case_id, query, variant in RUNS:
        t0 = time.time()
        outcome, err = "success", ""
        try:
            app.invoke({"case_id": case_id, "query": query, "variant": variant,
                        "flaky_retries": 0},
                       config={"callbacks": [HANDLER]})
        except Exception as exc:  # noqa: BLE001 - doomed runs fail for real
            outcome, err = "FAILED", f"{type(exc).__name__}: {exc}"
        dt = time.time() - t0
        line = f"{case_id} variant={variant} outcome={outcome} wall={dt:.2f}s {err}"
        print(line, flush=True)
        log_lines.append(line)

    with open(os.path.join(HERE, "run_log.txt"), "w") as f:
        f.write("live_langgraph_agent runs\n")
        f.write("\n".join(log_lines) + "\n")

    ledger = importer_common.ledger_from_tracker(tracker)
    with open(os.path.join(HERE, "ledger.json"), "w") as f:
        json.dump(ledger, f, indent=2)

    with open(os.path.join(HERE, "events.jsonl"), "w") as f:
        for ev in events_from_attempts(tracker):
            f.write(json.dumps(ev) + "\n")

    with open(os.path.join(HERE, "pnl.json"), "w") as f:
        json.dump(tracker.pnl(), f, indent=2)

    p = tracker.pnl()
    print(f"\nDONE: attempts={p['attempts']} successes={p['successes']} "
          f"retries={p['retries']} cost_total={p['cost_total']:.6f}")


if __name__ == "__main__":
    main()
