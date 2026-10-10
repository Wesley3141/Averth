# Review pass 2 — demo.py + pyproject.toml + __init__.py files

Reviewer: hostile. Scope: `demo.py` (98 lines), `pyproject.toml` (25 lines),
`averth/__init__.py` (28), `averth/importers/__init__.py` (34),
`averth/integrations/__init__.py` (11). Tree state: working tree with
uncommitted Phase-1 fixes (HEAD d5a5524 + 11 modified files).

**Procedural caveat (read first): the tree moved during this review.**
`averth/pricing.py` was edited at 03:02:19 UTC (price table v1 → v2:
haiku 0.80/4.00 → 1.00/5.00 + versioning machinery) and `sample-output.txt`
regenerated at 03:03, both while this review was running. I verified the
demo's numbers against BOTH states (ledger exported under v1 at 03:01 and
under v2 at 03:03+). Headline figures are identical under both; only the
haiku model-mix line moved ($3.09 → $3.86, still "1% of model spend").
Anything below marked "verified" was checked against the current (v2) tree
unless noted.

Severity counts: **0 CRITICAL · 2 HIGH · 4 MEDIUM · 4 LOW**

---

## HIGH

### H1. demo.py docstring claims runaways "burn 60%+ of budget" — they burn 20%
`demo.py:8` (module docstring, layer 4):
`# 4. heavy tail — 2% of attempts go runaway and burn 60%+ of budget`

Hand-verified from the exported ledger (seed 42, deterministic, both v1/v2
price tables):
- Runaway attempts (event "hit max steps, abandoning"): **37 of 2000 = 1.85%**
  — the "2%" half of the claim is fine.
- Their share of **total spend: 20.1%** (v1) / 20.1% (v2). Not 60%+.
- Their share of **model-only spend: 81%** — the only reading under which
  "60%+" is true, but "budget" in this file unambiguously means the
  per-success budget / total spend (`budget_per_success=6.00`, "top 5%
  consumed 61% of budget" two lines below in the report output).

The report's own layer-4 line says "top 5% consumed 61% of budget" (verified:
top-100 cost share = 61.3%). The docstring author appears to have conflated
the top-5% figure (61%) with the runaway-2% figure (20%). Per rubric item 7
(docs-vs-code), a docstring claim contradicted 3x by the code's own output
is HIGH. Fix: rewrite as "2% of attempts go runaway; the top 5% of attempts
consume 61% of spend" (both verified true), or qualify "60%+ of *model*
spend".

### H2. The `averth` console script is declared but installed nowhere; the audit's "`averth simulate`" could not have run as a literal command
- `pyproject.toml:24-25`: `[project.scripts] averth = "averth.cli:main"` —
  the declaration is valid: wheel builds cleanly, `entry_points.txt`
  contains `averth = averth.cli:main`, `cli.main` exists, and
  `python -m averth.cli simulate` works.
- But: `which averth` → nothing; `pip show averth` → nothing (system python
  AND project `.venv`). The `.venv` instead contains a **stale pre-rename
  editable install**: `agentpnl-0.2.0.dist-info` +
  `__editable__.agentpnl-0.2.0.pth`, while `pyproject.toml` says
  `name = "averth"`. Pip metadata disagrees with the build file.
- `.venv/bin/agentpnl` exists with shebang
  `#!/home/hatch/workspace/agentpnl/.venv/bin/python3` — that path does not
  exist (`/home/hatch/workspace/agentpnl` is gone). Dead script from the
  pre-rename era.
- Consequence: in this environment there is no working `averth` on PATH, so
  the audit's reported "`averth simulate`" run must have been
  `python -m averth.cli` (or equivalent), not the console script. The
  installed-script path — the thing a real `pip install` user gets — has
  never been exercised here. I installed the built wheel into an isolated
  `--target` dir and ran `python -m averth.cli simulate` from it
  successfully, which validates the *code* but not the generated shim.
- Additionally, nothing in `tests/` covers the entry point at all
  (no test references console scripts, entry points, or `cli.main`).
- Fix: `pip install -e .` (or `pip install .`) in the dev venv to replace the
  stale `agentpnl` metadata, verify `averth --help` / `averth simulate` on
  PATH, and add a smoke test that resolves the `averth` entry point via
  `importlib.metadata`.

---

## MEDIUM

### M1. `/tmp/averth-ledger.json`: predictable path, silent overwrite, follows symlinks
`demo.py:87-88`: `P.export_ledger(t, "/tmp/averth-ledger.json")` →
`policy.export_ledger` does `open(path, "w")` with no `O_EXCL`, no existence
check, no explicit mode (umask-dependent; observed 0660 here, typically 0644
elsewhere). Verified behavior:
- A pre-existing `/tmp/averth-ledger.json` (I planted a sentinel) is
  **silently replaced**, no warning.
- A **symlink** at that path is followed: I pointed
  `/tmp/averth-ledger.json` at a scratch file and `export_ledger` overwrote
  the symlink *target* (CWE-59). On a shared machine another local user can
  pre-plant the symlink to redirect or destroy an arbitrary file the demo
  runner can write.
- Two concurrent `demo.py` runs clobber each other's ledger (no PID/user
  uniqueness), and the demo reads the file back immediately after writing,
  so a clobbered read silently simulates the wrong ledger.
- `/tmp` is also volatile in this runtime (my own `/tmp/demo-out.txt`
  vanished mid-review) — fine for a demo, but the fixed absolute path is
  not Windows-portable and ignores `TMPDIR`.
Impact is bounded (the ledger is sanitized metadata — verified by string
scan, see below), but the *write* side can destroy data. For a demo script
this is MEDIUM; fix with `tempfile.mkstemp`-style unique paths or at least
`O_EXCL`/0600.

### M2. Dead parameter `base_in` in `model_step` (AI-slop signature)
`demo.py:28-33`:
```python
def model_step(ctx, provider, model, base_in, base_out):
    ctx["in"] = min(int(ctx["in"] * random.uniform(1.25, 1.7)), 190000)
    t.log_model_call(provider, model, ctx["in"],
                     random.randint(int(base_out * 0.7), int(base_out * 1.3)))
```
`base_in` is never read in the body — the input-token count comes only from
compounding `ctx["in"]`. All 9 call sites pass `900` or `0` as a vestigial
argument, which misleads a reader into thinking the first call seeds 900
input tokens via the parameter (it doesn't — the seed comes from
`ctx = {"in": 900}` at `demo.py:41`). Remove the parameter.

### M3. "No prompts or customer data" is true for *this* demo but does not generalize
`demo.py:90` prints: `"Ledger exported: ..., no prompts or customer data."`
Verified true for the demo export — I scanned every string value in the
exported ledger; the only strings are `case_id`s, the two constant retry
reasons, and the price-vintage date. BUT `policy.export_ledger` copies the
per-attempt `"events"` list verbatim, and `Tracker.log_retry(reason, ...)`
accepts arbitrary caller strings. A customer copying this demo pattern with
real retry reasons (e.g. `"validation failed for invoice INV-1042: total
$1,203.55 mismatch"`) silently exports whatever they passed. The demo's
printed claim is scoped to its own export and holds; the *pattern it
teaches* ("reasons are safe to export") is not validated anywhere. MEDIUM
because the sentence reads as a guarantee of the pipeline, not just this
run. Suggest scrubbing/allowlisting reason strings or downgrading the claim.

### M4. No test coverage for the entry point or demo determinism
`tests/` contains no test that (a) resolves the `averth` console script,
(b) runs `cli.main(["simulate", ...])`, or (c) pins `demo.py`'s seeded
output. `sample-output.txt` is a byte-exact golden file (verified identical
to a fresh run on the current tree) but nothing asserts it — it only stays
fresh by manual regeneration (which did happen at 03:03, credit where due).
A one-test `subprocess [sys.executable, demo.py]` + stdout comparison, and
an `importlib.metadata` entry-point smoke test, would lock both.

---

## LOW

### L1. Redundant `sys.path.insert(0, ".")` — and it can shadow the real package
`demo.py:15`. When Python runs a script, the script's own directory is
already `sys.path[0]` — which is why `demo.py` works from *any* cwd
(verified: ran from `/tmp`, exit 0, correct output). The insert is a no-op
in the normal case, but it puts **cwd ahead of the script dir**, so running
`demo.py` from a directory containing a different `averth/` package would
import the wrong code. Harmless today, footgun tomorrow. Delete it or guard
it.

### L2. Mid-file import
`demo.py:85`: `from averth import policy as P` appears after 70 lines of
simulation and printing. Works fine; move to the top with the other imports.

### L3. `__all__` omits `policy` although docs use `from averth import policy`
`averth/__init__.py:28`: `__all__ = ["Tracker", "BudgetBreach", "pricing"]`.
README (`:69`) and `demo.py` use `from averth import policy as P`, which
works via submodule import — verified importable — but `from averth import
*` will not bring `policy` in. Either add `"policy"` to `__all__` or leave
as-is deliberately; currently inconsistent.

### L4. pyproject nits
No `keywords`/`classifiers` (discoverability); `version = "0.2.0"` appears
nowhere else in the repo docs to cross-check (no contradiction found
either). `averth.egg-info/` is stale build residue in the repo root but is
gitignored (`*.egg-info/`) — not tracked, not a finding beyond hygiene.

---

## Verified good (hostile checks that passed)

- **Every printed number is computed, none hardcoded.** Independently
  recomputed from the exported ledger under both price-table v1 and v2
  (seed 42, deterministic): model spend $312.09→$312.86, dashboard
  $0.1983→$0.1988 → **$0.20** ✓; fully loaded per success $0.8165→$0.8170 →
  **$0.82** ✓; ratio 4.11 → **4.1x** ✓; context growth mean 4.66 → **4.7x** ✓;
  context tax $262.06 = **84.0%** of model spend ✓; yield 6.4% → **6%** ✓;
  top-100 cost share 61.3% → **61%** ✓; p50 $0.02 / max $9.78 ✓ (p95 $5.68
  is the interpolated percentile per tracker's documented method; naive
  index gives $5.76 — not a bug); breaches **96** == hook count 96 ✓;
  policy replay **1020 stopped / 426 failed / $297.18 saved / $897.79
  collateral** ✓; business value $17,628.80 = 1574 × $11.20 ✓; net
  $16,343.65 ✓; retry reasons 594 + 37 = 631 retries ✓.
- **README claims match current output.** README:45 ("dashboard $0.20 vs
  fully-loaded $0.82") and README:83 ("$0.20 per success; $0.82 (4.1x);
  4.7x context compounding; 6% token yield ratio; top 5% consuming 61%")
  all verified against a fresh run.
- **Clean-checkout run works.** Stock `python3` (3.12, no venv), stdlib only,
  from repo root and from `/tmp`: exit 0 in ~1.2s. `demo.py` has no
  third-party imports.
- **Zero hard deps: TRUE.** Every import across `averth/` (tracker, report,
  policy, pricing, cli, insights, stress, importers/*, integrations/*) is
  stdlib (`argparse, datetime, html, json, math, os, random, sys, time`);
  `dependencies = []` is accurate; optionals correctly scoped to extras.
- **`from averth import Tracker, BudgetBreach, policy` — all importable.**
  `BudgetBreach` is an `Exception` subclass; the breach hook signature
  `(attempt, breach)` matches `tracker.py:370`
  (`self.on_breach(a, breach)`); hook-captured count (96) agrees with the
  report's `budget_breaches` (96) — the C1 "count every over-envelope
  attempt" fix is exercised by the demo.
- **Integrations are genuinely dependency-optional.** With neither
  `langchain_core` nor `openai` installed, `import averth.integrations`
  succeeds and `wrap_openai_client` works against a duck-typed fake client
  (docstring claim true). `averth.importers` imports cleanly; every name in
  `__all__` (`events_to_tracker`, `ledger_from_tracker`,
  `tracker_from_ledger`, `guess_provider`, `FALLBACK_PRICE`,
  `LEDGER_ATTEMPT_KEYS`, `otel`, `langsmith`, `jsonl`) resolves.
- **Packaging mechanics sound.** Wheel builds cleanly
  (`averth-0.2.0-py3-none-any.whl`); `entry_points.txt` correct; both
  subpackages included; 16 top-level `.py`, zero non-`.py` data files → no
  `package_data` needed; isolated wheel install imports and
  `python -m averth.cli simulate` runs. `requires-python >=3.9`: no 3.10+
  syntax found. LICENSE is MIT, matching `license = { text = "MIT" }`.
- **Ledger is metadata-only.** String scan of the exported ledger finds no
  prompt/completion/payload content (this run). `price_vintage` v2 stamp is
  present in the ledger (C2 working end to end).
- **No prompt-injection contact.** No web content was fetched for this
  review; no injected directives encountered.

## Recommended fixes (priority order)
1. H1: correct the "60%+ of budget" docstring (demo.py:8).
2. H2: reinstall the venv (`pip install -e .`), delete dead
   `.venv/bin/agentpnl`, verify `averth` on PATH, add entry-point smoke test.
3. M1: unique ledger path / `O_EXCL` / explicit 0600 in the demo (and consider
   in `export_ledger`).
4. M2: drop dead `base_in` param. L1/L2/L3: import hygiene.
5. M4: golden-file test for demo.py + entry-point test.
