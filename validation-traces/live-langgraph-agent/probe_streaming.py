"""Probe 2: does the handler receive token_usage for streamed and non-streamed
stub-model calls, and what model name/provider does it see?
"""
import sys
sys.path.insert(0, "/home/hatch/workspace/agentpnl")
sys.path.insert(0, "/home/hatch/workspace/agentpnl/validation-traces/live-langgraph-agent")

from langchain_core.messages import HumanMessage
from agentpnl import Tracker
from agentpnl.integrations import AgentPNLCallbackHandler
from stub_model import StubChatModel

seen = {}

class Spy(AgentPNLCallbackHandler):
    def on_llm_start(self, serialized, prompts, run_id=None, parent_run_id=None, **kw):
        seen["serialized"] = serialized
        super().on_llm_start(serialized, prompts, run_id=run_id, parent_run_id=parent_run_id, **kw)
    def on_llm_end(self, response, run_id=None, parent_run_id=None, **kw):
        seen["llm_output"] = getattr(response, "llm_output", None)
        super().on_llm_end(response, run_id=run_id, parent_run_id=parent_run_id, **kw)

tracker = Tracker("probe2")
h = Spy(tracker)

model = StubChatModel()
tracker.start_attempt(case_id="STREAM-TEST")
out = model.invoke([HumanMessage(content="PLAN_REQUEST what is langgraph")],
                   config={"callbacks": [h]})
print("non-streamed output head:", out.content[:60])
print("non-streamed llm_output:", seen.get("llm_output"))
print("serialized kwargs keys:", list((seen["serialized"].get("kwargs") or {}).keys())[:8])

smodel = StubChatModel(streaming=True)
seen.clear()
out2 = smodel.invoke([HumanMessage(content="summarize this context: hello world")],
                     config={"callbacks": [h]})
print("streamed output head:", out2.content[:60])
print("streamed llm_output:", seen.get("llm_output"))
tracker.end_attempt(success=True)

p = tracker.pnl()
print("attempts:", p["attempts"], "model cost:", p["cost_model"])
print("per_model:", p["per_model"])
print("unpriced_models:", p["unpriced_models"])
print("total_tokens:", tracker.attempts[0]["total_tokens"])
