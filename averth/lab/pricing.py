"""Token pricing. Prices are labeled estimates unless they come from a bill.

Stub-phase costs use this table so the plumbing is exercised end to end.
A measured experiment must replace these with the provider's billed rates
for the exact model used, or better, with invoice-reconciled spend.
"""
from __future__ import annotations

from typing import Dict

from .models import Usage

# USD per 1K tokens. Labeled estimates, October 2026.
PRICE_TABLE: Dict[str, Dict[str, float]] = {
    "sonnet-class": {"input": 0.003, "output": 0.015},
    "haiku-class": {"input": 0.0008, "output": 0.004},
    "stub": {"input": 0.0, "output": 0.0},
}


def cost_for(usage: Usage, model_class: str = "sonnet-class") -> float:
    rates = PRICE_TABLE[model_class]
    return (usage.input_tokens / 1000) * rates["input"] + (usage.output_tokens / 1000) * rates["output"]
