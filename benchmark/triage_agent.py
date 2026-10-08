"""Naive issue-triage agent, v1 (ARM A baseline — pinned, do not modify).

Pipeline (written as a straightforward first attempt, no optimization):
  1. Haiku quick read: title + body -> draft classification.
  2. Tool: TF-IDF retrieval of 5 similar past issues (full bodies appended).
  3. Sonnet final: full context -> classification + one-line summary.

All model calls go through the Averth Tracker with real token usage.
"""
import json, os, sys

import anthropic
import httpx2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from averth import Tracker

# trust_env=False: the sandbox's no_proxy IPv6 entries break httpx URL parsing
client = anthropic.Anthropic(http_client=httpx2.Client(trust_env=False))
TRACKER = Tracker("issue-triage-v1")

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-5"

_corpus = None
_vectorizer = None
_matrix = None

def build_corpus(tasks):
    global _corpus, _vectorizer, _matrix
    _corpus = tasks
    texts = [(t["title"] + " " + t["body"]) for t in tasks]
    _vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    _matrix = _vectorizer.fit_transform(texts)

def retrieve_similar(task, k=5):
    """Tool: find k similar past issues. Logged as a tool call."""
    q = _vectorizer.transform([task["title"] + " " + task["body"]])
    sims = cosine_similarity(q, _matrix)[0]
    idx = sims.argsort()[::-1]
    out = []
    for i in idx:
        if _corpus[i]["id"] == task["id"]:
            continue
        out.append(_corpus[i])
        if len(out) == k:
            break
    TRACKER.log_tool_call("similar_issue_search")
    return out

def call_model(model, system, user, max_tokens=300):
    msg = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}])
    u = msg.usage
    TRACKER.log_model_call("anthropic", model, u.input_tokens, u.output_tokens)
    return msg.content[0].text, u.input_tokens, u.output_tokens

DRAFT_SYSTEM = "You triage GitHub issues. Reply with exactly one word: BUG or FEATURE_REQUEST."
FINAL_SYSTEM = ("You triage GitHub issues. Reply in exactly this format:\n"
                "CLASS: BUG or FEATURE_REQUEST\n"
                "SUMMARY: one line, under 20 words")

def triage(task):
    TRACKER.start_attempt(case_id=task["id"])
    # Step 1: cheap draft read
    draft, _, _ = call_model(
        HAIKU, DRAFT_SYSTEM,
        f"Title: {task['title']}\nBody: {task['body'][:1500]}",
        max_tokens=20)
    # Step 2: retrieve similar issues (context growth happens here)
    similar = retrieve_similar(task, k=5)
    ctx = "\n\n".join(
        f"--- similar issue {s['id']} (labeled {s['class']}) ---\n"
        f"Title: {s['title']}\nBody: {s['body'][:1200]}"
        for s in similar)
    # Step 3: expensive final decision with full context
    out, _, _ = call_model(
        SONNET, FINAL_SYSTEM,
        f"Draft classification: {draft.strip()}\n\n"
        f"Issue to classify:\nTitle: {task['title']}\nBody: {task['body'][:1500]}\n\n"
        f"Similar past issues:\n{ctx}",
        max_tokens=120)
    klass = "bug" if "BUG" in out.split("\n")[0] else "feature_request"
    TRACKER.end_attempt(success=True)
    return {"class": klass, "raw": out, "draft": draft.strip()}

if __name__ == "__main__":
    with open("tasks.json") as f:
        data = json.load(f)
    build_corpus(data["dev"] + data["heldout"])
    t = data["dev"][0]
    print(json.dumps(triage(t), indent=2)[:600])
    print("tracker pnl:", json.dumps(TRACKER.pnl(), indent=2)[:400])
