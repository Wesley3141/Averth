# Numbers review v3: re-verification of v2 finding N1 only

**Verdict: PASS** — the single defect from review-numbers-v2.md (N1) is fixed.
No other item was re-reviewed, per the task scope.

**Scope:** verify only the N1 fix in `case-study-1.md` against the new V0
ledger (`v0-run/evidence_ledger.json`, generated
2026-11-11T05:14:38.356674+00:00). No file was edited except this review
file. The case study and all evidence files were not edited.

---

## 1. Check (1): the text now says 0.168s, no longer 0.152s

**Fixed line** — `case-study-1.md:72-73`, verbatim:

> The output digests are over output that includes Django's run-time line
> (`Ran 89 tests in 0.168s`), so a reproducer's digests will usually differ
> for C2; compare exit codes (0), test counts (1 test OK; 89 tests OK,
> skipped=1), and verdicts, not digests.

**Counts in `case-study-1.md` (grep):**

- `0.168s`: 1 occurrence (line 73, the fixed line above).
- `0.152s`: 0 occurrences.

**Result: PASS.** The stale `Ran 89 tests in 0.152s` is gone from the case
study text.

Note on scope of "anywhere": `0.152s` still appears in other files in this
directory, as it should — in `review-numbers-v2.md` (which records the
defect), `review-numbers.md` / `review-reproduction.md` (first-run reviews),
`repro-test-fixed-steps.md` (which notes the old value), and
`review-reproduction-v2.md` (which lists it among observed rerun timings).
Those are historical records of the first V0 run, whose C2 timing genuinely
was `0.152s` (digest `sha256:498fa2e3…`). The check that matters for
publication is the case-study text itself, and it contains no `0.152s`.

---

## 2. Check (2): recomputed digest for the C2 run

**Source:** `v0-run/evidence_ledger.json`, `runs[1]` —
label "expressions_case module, PASS_TO_PASS tests with agent patch",
exit 0, trust tier 2.

Stored output, verbatim (Python `repr`):

- stdout: `'System check identified no issues (0 silenced).\n'`
- stderr: `'----------------------------------------------------------------------\nRan 89 tests in 0.168s\n\nOK (skipped=1)\n'`

**Recomputation** (done independently in this pass, `hashlib.sha256`
over `(stdout + stderr)` encoded UTF-8):

```
sha256(stdout+stderr) = sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b
```

**Cited digest** (ledger `runs[1].output_digest`, judgment C2
`output_digest`, and `case-study-1.md:65` C2 table row — all identical):

```
sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b
```

**Match: exact.**

**Hashed-output content check:**

- Combined `stdout + stderr` contains `Ran 89 tests in 0.168s`: **yes**.
- Combined `stdout + stderr` contains `0.152s`: **no**.

**Result: PASS.** The cited digest is a hash over output containing the
`0.168s` line the text now quotes, so the number and the digest agree.

---

## 3. Verdict

| Finding | Required fix | Status |
| --- | --- | --- |
| N1 — C2 run-time line stale (`0.152s` in text, `0.168s` in new ledger) | Change `case-study-1.md:73` to `0.168s` | **FIXED and re-verified.** Text reads `Ran 89 tests in 0.168s`; `0.152s` occurs 0 times in `case-study-1.md`; recomputed `sha256(stdout+stderr)` for the ledger C2 run equals the cited digest `sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b` exactly, and the hashed output contains the `0.168s` line. |

**Verdict: PASS.** The v2 FAIL's sole defect is corrected. Nothing else
was checked in this pass.
