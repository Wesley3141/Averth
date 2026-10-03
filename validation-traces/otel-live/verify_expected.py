"""Verify imported ledgers against the attributes the generator set."""
import math, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from averth.importers import otel
from averth.importers.common import tracker_from_ledger

D = os.path.dirname(os.path.abspath(__file__))

def load(f):
    ledger = otel.load_otel(os.path.join(D, f))
    return ledger

fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)

# ---------------- trace A
la = load("trace-a-sequential-retry.json")
a = la["attempts"]
check(len(a) == 1, "trace-a: one attempt (single trace id)")
a = a[0]
check(a["success"] is False, "trace-a: ERROR tool span marks attempt failed")
check(a["retries"] == 1, "trace-a: one retry event, got %d" % a["retries"])
check(a["human_min"] == 3, "trace-a: 3 escalation minutes, got %s" % a["human_min"])
check(abs(a["business_value"] - 12.50) < 1e-9, "trace-a: business_value override 12.50, got %s" % a["business_value"])
check(a["tools"] is not None and abs(a["tools"] - (0.002+0.002+0.002+0.002)) < 1e-9,
      "trace-a: 4 tool calls at $0.002 = $0.008, got %s" % a["tools"])

pm = a["per_model"]
# sonnet spans: (2400,380) + (3100,640) + retry_plan via llm.token_count (2900,310)
exp_sonnet = (2400+3100+2900)/1e6*3.00 + (380+640+310)/1e6*15.00
check(abs(pm.get("anthropic:claude-sonnet-4-5", 0) - exp_sonnet) < 1e-9,
      "trace-a: sonnet cost %.6f, got %.6f" % (exp_sonnet, pm.get("anthropic:claude-sonnet-4-5", 0)))
exp_haiku = 1200/1e6*1.00 + 210/1e6*5.00
check(abs(pm.get("anthropic:claude-haiku-4-5", 0) - exp_haiku) < 1e-9,
      "trace-a: haiku cost %.6f, got %.6f" % (exp_haiku, pm.get("anthropic:claude-haiku-4-5", 0)))
# deepseek: negative input tokens clamped to 0 -> 150 out * fallback 3.00
exp_deep = 0/1e6*1.00 + 150/1e6*3.00
check(abs(pm.get("unknown:deepseek-v3.2", 0) - exp_deep) < 1e-9,
      "trace-a: deepseek cost clamped >=0: %.6f, got %.6f" % (exp_deep, pm.get("unknown:deepseek-v3.2", 0)))
check(all(v >= 0 for v in pm.values()), "trace-a: no negative model costs")

t = tracker_from_ledger(la).pnl()
check(t["unpriced_models"] == ["unknown:deepseek-v3.2"], "trace-a: unpriced_models flags deepseek, got %s" % t["unpriced_models"])
# total tokens: sonnet(2400+380+3100+640+2900+310) + haiku(1200+210) + deepseek(0+150); untracked span (no model) excluded
exp_tok = (2400+380+3100+640+2900+310) + (1200+210) + (0+150)
check(a["total_tokens"] == exp_tok, "trace-a: total_tokens %d, got %s" % (exp_tok, a["total_tokens"]))

# ---------------- trace B
lb = load("trace-b-parallel-fanout.json")
b = lb["attempts"]
check(len(b) == 1, "trace-b: one attempt across 4 parallel branches")
b = b[0]
check(b["success"] is False, "trace-b: double-failed branch marks attempt failed")
check(b["retries"] == 2, "trace-b: two retry events, got %d" % b["retries"])
bpm = b["per_model"]
# gemini via llm.token_count.prompt/completion: (2200,410) at 0.50/3.00
exp_gem = 2200/1e6*0.50 + 410/1e6*3.00
check(abs(bpm.get("google:gemini-3-flash", 0) - exp_gem) < 1e-9,
      "trace-b: gemini (openinference dialect) cost %.6f, got %.6f" % (exp_gem, bpm.get("google:gemini-3-flash", 0)))
# grok: (2600,520)+(900,120) at 3.00/15.00
exp_grok = (2600+900)/1e6*3.00 + (520+120)/1e6*15.00
check(abs(bpm.get("xai:grok-4", 0) - exp_grok) < 1e-9,
      "trace-b: grok cost %.6f, got %.6f" % (exp_grok, bpm.get("xai:grok-4", 0)))
# mini: branch0 (1800,260) priced + branch3 negative clamped to 0
exp_mini = 1800/1e6*0.30 + 260/1e6*1.20
check(abs(bpm.get("openai:gpt-5.6-mini", 0) - exp_mini) < 1e-9,
      "trace-b: mini cost %.6f (negatives clamped), got %.6f" % (exp_mini, bpm.get("openai:gpt-5.6-mini", 0)))
exp_merge = 4200/1e6*2.50 + 880/1e6*10.00
check(abs(bpm.get("openai:gpt-5.6", 0) - exp_merge) < 1e-9,
      "trace-b: merge gpt-5.6 cost %.6f, got %.6f" % (exp_merge, bpm.get("openai:gpt-5.6", 0)))
check(all(v >= 0 for v in bpm.values()), "trace-b: no negative model costs")
# tool latency: real HTTP durations recorded (delay/1 branch >= ~900ms total tool latency)
check(b.get("tool_latency_ms", 0) > 900, "trace-b: real tool latency captured (%.0f ms)" % b.get("tool_latency_ms", 0))

print()
print("FAILURES:", len(fails))
sys.exit(1 if fails else 0)
