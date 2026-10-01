"""Probe: how does AverthCallbackHandler behave under a REAL LangGraph run?

Drives a tiny 2-node graph (node A calls a real HTTP tool, node B is a
passthrough) through the handler and prints what the tracker recorded.
Run with the venv python: .venv/bin/python probe_attempt_boundaries.py
"""
import sys, uuid

sys.path.insert(0, "/home/hatch/workspace/averth")

import requests
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from averth import Tracker
from averth.integrations import AverthCallbackHandler


class Events(AverthCallbackHandler):
    """Subclass that logs every callback event for inspection."""
    def __init__(self, tracker):
        super().__init__(tracker)
        self.log = []

    def on_chain_start(self, serialized, inputs, run_id=None, parent_run_id=None, **kw):
        name = (serialized or {}).get("name") if isinstance(serialized, dict) else None
        self.log.append(("chain_start", name, str(run_id)[:8], str(parent_run_id)[:8] if parent_run_id else None))
        super().on_chain_start(serialized, inputs, run_id=run_id, parent_run_id=parent_run_id, **kw)

    def on_chain_end(self, outputs, run_id=None, parent_run_id=None, **kw):
        self.log.append(("chain_end", str(run_id)[:8], str(parent_run_id)[:8] if parent_run_id else None))
        super().on_chain_end(outputs, run_id=run_id, parent_run_id=parent_run_id, **kw)

    def on_chain_error(self, error, run_id=None, parent_run_id=None, **kw):
        self.log.append(("chain_error", str(run_id)[:8], type(error).__name__))
        super().on_chain_error(error, run_id=run_id, parent_run_id=parent_run_id, **kw)

    def on_tool_start(self, serialized, input_str, run_id=None, parent_run_id=None, **kw):
        self.log.append(("tool_start", str(run_id)[:8], str(parent_run_id)[:8] if parent_run_id else None))
        super().on_tool_start(serialized, input_str, run_id=run_id, parent_run_id=parent_run_id, **kw)

    def on_tool_end(self, output, run_id=None, parent_run_id=None, **kw):
        self.log.append(("tool_end", str(run_id)[:8]))
        super().on_tool_end(output, run_id=run_id, parent_run_id=parent_run_id, **kw)


class S(TypedDict):
    case_id: str
    n: int


def node_a(state: S, config):
    r = requests.get("https://api.duckduckgo.com/?q=langgraph&format=json", timeout=15)
    r.raise_for_status()
    return {"n": state["n"] + 1}


def node_b(state: S, config):
    return {"n": state["n"] + 1}


g = StateGraph(S)
g.add_node("node_a", node_a)
g.add_node("node_b", node_b)
g.set_entry_point("node_a")
g.add_edge("node_a", "node_b")
g.add_edge("node_b", END)
app = g.compile()

tracker = Tracker("probe")
handler = Events(tracker)
app.invoke({"case_id": "PROBE-1", "n": 0}, config={"callbacks": [handler]})

print("=== callback event order ===")
for e in handler.log:
    print(e)
print()
p = tracker.pnl()
print("attempts:", p["attempts"], "successes:", p["successes"])
for a in tracker.attempts:
    print("  case:", a["case_id"], "events:", a["events"])
