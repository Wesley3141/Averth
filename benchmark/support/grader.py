"""Grader for the support benchmark.

A resolution is ACCEPTED iff the predicted resolution_label exactly matches
the recorded accepted resolution. The response_draft is stored per run for
human audit (v2 adds a rubric judge; v1 scores the label only — stated).

Per-grade CRM fields (reopened, sla_breach, time_to_close_hours) flow
through so analysis can slice acceptance on tickets humans got wrong.
"""
import json

LABELS = ["HOWTO", "CONFIG", "BUG_FIX", "DUPLICATE", "WONTFIX", "ESCALATED"]


def grade(prediction, task):
    pred = (prediction.get("resolution_label") or "").upper()
    actual = task["resolution_label"]
    accepted = (pred == actual)
    return {
        "task_id": task["id"],
        "predicted": pred,
        "actual": actual,
        "accepted": accepted,
        # CRM-grounded context, not scored in v1
        "reopened": bool(task.get("reopened")),
        "sla_breach": bool(task.get("sla_breach")),
        "time_to_close_hours": task.get("time_to_close_hours"),
        "response_draft": prediction.get("response_draft", ""),
    }


def summarize(grades):
    n = len(grades)
    acc = sum(1 for g in grades if g["accepted"])
    reopened_n = sum(1 for g in grades if g["reopened"])
    reopened_acc = (sum(1 for g in grades if g["accepted"] and g["reopened"])
                    / reopened_n) if reopened_n else None
    return {
        "n": n,
        "acceptance_rate": acc / n if n else 0.0,
        "accepted": acc,
        # slice: do we match accepted resolutions on tickets that later
        # reopened (i.e. tickets humans themselves got wrong)?
        "reopened_n": reopened_n,
        "reopened_acceptance_rate": reopened_acc,
    }
