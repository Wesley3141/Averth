"""Grader for the triage benchmark.

Primary task: bug vs feature_request classification (exact match).
Scored per run; aggregate accuracy + cost per accepted task computed by runner.
A run is 'accepted' if the classification is correct.
"""
import json


def grade(prediction, task):
    pred_cls = prediction.get("class", "")
    actual = task["class"]
    correct = (pred_cls == actual)
    return {
        "task_id": task["id"],
        "predicted": pred_cls,
        "actual": actual,
        "correct": correct,
    }


def summarize(grades):
    n = len(grades)
    acc = sum(1 for g in grades if g["correct"]) / n if n else 0.0
    return {"n": n, "accuracy": acc,
            "correct": sum(1 for g in grades if g["correct"])}
