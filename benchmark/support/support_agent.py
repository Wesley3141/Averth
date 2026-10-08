"""Naive support agent, v1 (ARM A baseline — pinned, do not modify).

Pipeline (straightforward first attempt, no optimization):
  1. Haiku quick read: title + body -> draft resolution label.
  2. Tool: TF-IDF retrieval of 5 similar past tickets (resolutions appended).
  3. Sonnet final: full context -> resolution label + response draft.

All model calls go through the Averth Tracker with real token usage.
"""
import json
import os
import sys

import anthropic
import httpx2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from averth import Tracker

# trust_env=False: the sandbox's no_proxy IPv6 entries break httpx URL parsing
client = anthropic.Anthropic(http_client=httpx2.Client(trust_env=False))
TRACKER = Tracker("support-v1")

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-5"

LABELS = ["HOWTO", "CONFIG", "BUG_FIX", "DUPLICATE", "WONTFIX", "ESCALATED"]

_corpus = None
_vectorizer = None
_matrix = None


def build_corpus(tasks):
    global _corpus, _vectorizer, _matrix
    _corpus = tasks
    texts = [t["title"] + " " + t["body"] for t in tasks]
    _vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    _matrix = _vectorizer.fit_transform(texts)


def retrieve_similar(task, k=5):
    """Tool: find k similar past tickets. Logged as a tool call."""
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
    TRACKER.log_tool_call("similar_ticket_search")
    return out


def call_model(model, system, user, max_tokens=400):
    msg = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}])
    u = msg.usage
    TRACKER.log_model_call("anthropic", model, u.input_tokens, u.output_tokens)
    return msg.content[0].text, u.input_tokens, u.output_tokens


def _parse_label(text):
    for line in text.splitlines():
        if line.strip().upper().startswith("LABEL:"):
            cand = line.split(":", 1)[1].strip().upper()
            if cand in LABELS:
                return cand
    # fallback: first known label mentioned
    up = text.upper()
    for lab in LABELS:
        if lab in up:
            return lab
    return "HOWTO"


def resolve_ticket(task):
    """Run one ticket. Returns (prediction dict, attempt_id)."""
    attempt = TRACKER.start_attempt(case_id=task["id"])

    draft, _, _ = call_model(
        HAIKU,
        "You triage customer support tickets. Reply with one line: LABEL: <one of HOWTO, CONFIG, BUG_FIX, DUPLICATE, WONTFIX, ESCALATED>",
        f"Title: {task['title']}\n\nBody:\n{task['body'][:3000]}",
        max_tokens=60,
    )
    draft_label = _parse_label(draft)

    similar = retrieve_similar(task)
    context = "\n\n".join(
        f"--- past ticket {s['id']} (resolved as {s['resolution_label']}) ---\n"
        f"{s['title']}\n{s['body'][:800]}\nResolution: {s['resolution_summary']}"
        for s in similar
    )

    final, _, _ = call_model(
        SONNET,
        "You resolve customer support tickets. First line: LABEL: <one of HOWTO, CONFIG, BUG_FIX, DUPLICATE, WONTFIX, ESCALATED>. "
        "Then a blank line, then a short customer-facing response draft (max 150 words).",
        f"Ticket:\nTitle: {task['title']}\n\nBody:\n{task['body'][:4000]}\n\n"
        f"Draft label from quick read: {draft_label}\n\nSimilar past tickets:\n{context}",
        max_tokens=400,
    )
    lines = final.split("\n")
    label = _parse_label(final)
    draft_text = "\n".join(
        l for l in lines
        if not l.strip().upper().startswith("LABEL:")
    ).strip()

    # The ticket's real reopen flag flows into the ledger so analysis can
    # slice acceptance on reopened vs clean tickets (CRM grounding).
    TRACKER.end_attempt(success=True, reopened=bool(task.get("reopened")))
    return {"resolution_label": label, "response_draft": draft_text}, None
