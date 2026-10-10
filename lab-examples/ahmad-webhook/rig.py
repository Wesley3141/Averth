"""Test rig: import a webhook module with heavy deps stubbed.

Stubs: anthropic (records model calls, controllable), incident_store (in-mem),
run_kubectl (canned), send_telegram (records, async hold gate for in-flight
control). The route handler code under test is the REAL module code.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types


class FakeUsage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class FakeResponse:
    def __init__(self, text, i, o):
        self.content = [types.SimpleNamespace(text=text)]
        self.usage = FakeUsage(i, o)


class FakeMessages:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, *, model, max_tokens, system, messages):
        prompt = messages[0]["content"]
        self.calls.append({
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "prompt_chars": len(prompt),
        })
        return FakeResponse("Stubbed diagnosis.", len(prompt) // 4, 120)


class FakeAnthropic:
    def __init__(self, api_key=None):
        self.messages = FakeMessages()


class FakeStore:
    def __init__(self):
        self.saved: list[dict] = []

    def find_similar(self, **kwargs):
        return []

    def save_incident(self, **kwargs):
        self.saved.append(kwargs)

    def get_stats(self):
        return {"total_incidents": len(self.saved)}


class TelegramLog:
    def __init__(self):
        self.messages: list[str] = []

    async def send(self, message: str):
        self.messages.append(message)


def load_webhook(module_name: str, path: str):
    """Import the webhook file with stubbed deps. Returns (module, fakes)."""
    fake_anthropic_mod = types.ModuleType("anthropic")
    fake_anthropic_mod.Anthropic = FakeAnthropic
    sys.modules["anthropic"] = fake_anthropic_mod

    fake_store_mod = types.ModuleType("incident_store")
    store = FakeStore()
    fake_store_mod.store = store
    sys.modules["incident_store"] = fake_store_mod

    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)

    telegram = TelegramLog()

    async def fake_send_telegram(message: str):
        await telegram.send(message)

    mod.send_telegram = fake_send_telegram
    # Realistic-sized canned outputs so prompt-size cost estimates are honest.
    # ~800 chars pod status + ~2500 chars logs + ~1200 chars events.
    def fake_kubectl(command: str) -> str:
        if command.startswith("logs"):
            lines = [f"2026-10-10T12:00:{i:02d}Z app: worker iteration {i}, heap=128Mi, req_id=abc{i:04d}" for i in range(20)]
            return "\n".join(lines)
        if "events" in command:
            lines = [f"12m{i:02d}s Normal Started pod/api-1_{i} Started container app, image busybox:1.36" for i in range(10)]
            return "\n".join(lines)
        return ("NAME    READY   STATUS    RESTARTS   AGE   IP            NODE\n"
                "api-1   0/1     CrashLoopBackOff   7   42m   10.244.1.23   worker-2")
    mod.run_kubectl = fake_kubectl

    fakes = {
        "anthropic_client": mod.client,  # FakeAnthropic instance
        "store": store,
        "telegram": telegram,
    }
    return mod, fakes
