#!/usr/bin/env python3
"""Reproduce the published Averth case-study numbers from public sources.

What it does, in order:

1. Downloads the public trajectory, the leaderboard record, and the
   SWE-bench task definition (public S3, GitHub, and Hugging Face
   URLs; nothing behind a login).
2. Checks out Django at the case-study base commit, installs it in a
   venv, and runs the target test before the agent patch (expected:
   fails with the reported SQL syntax error) and after it (expected:
   passes, module green: 89 tests, 1 skipped). A gold-patch
   cross-check runs the same target test under the merged fix.
3. Runs ``averth try`` on the trajectory with the recorded cost from
   the leaderboard record, and checks the meter numbers; a second
   meter run on the fixture JSONL events must agree to the cent.
4. Runs V0 in executed mode with the bundled checks and allowlist,
   then rebuilds the try report with the fresh ledger, and checks the
   verdict counts.
5. Prints one PASS/FAIL line per check. Exit code 0 means every
   check passed; anything else is a defect to fix, not a rounding
   note. If the run fails midway, the checks recorded so far print
   first.

What it checks: the published numbers listed in PUBLISHED below,
plus a gold-patch cross-check and consistency checks that are not
published numbers (leaderboard api_calls/resolved, the baseline
failure mode). What it does NOT check: the 3.84x 12-run leaderboard
gap, the 0-tool-failures claim, and the $0.9832 unrounded total
(checked only through its rounded parts and the ratio).

Prerequisites: Python 3.9+, git, curl, internet access (public S3,
GitHub, Hugging Face, and PyPI URLs), and about a minute for the
Django install (47 to 86 seconds measured; allow more on a slow
connection). Everything lands under --work-dir (default
./repro-work, created inside the checkout when run from the repo
root); the Averth venv step runs ``pip install -e`` on the checkout,
which writes a git-ignored ``averth.egg-info/`` directory into the
source tree. No tracked file is modified. Pass --force to wipe an
existing work directory and redo the run.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

TRAJ_URL = (
    "https://s3.amazonaws.com/swe-bench-submissions/bash-only/"
    "20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/"
    "django__django-15930/django__django-15930.traj.json"
)
PER_INSTANCE_URL = (
    "https://raw.githubusercontent.com/m0at/experiments/main/evaluation/"
    "verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514/"
    "per_instance_details.json"
)
PARQUET_URL = (
    "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/"
    "resolve/main/data/test-00000-of-00001.parquet"
)
INSTANCE_ID = "django__django-15930"
BASE_COMMIT = "63884829acd207404f2a5c3cc1d6b4cd0a822b70"
MODEL = "claude-sonnet-4-20250514"
TARGET_TEST = (
    "expressions_case.tests.CaseExpressionTests."
    "test_annotate_with_full_when"
)
CHECKS_DIGEST = (
    "sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a"
)

# Published numbers (case study page, section 09). Money is compared
# to the cent, ratios to two decimals, growth to one decimal.
PUBLISHED = {
    "meter_total": 0.98,
    "meter_priced": 0.91,
    "meter_estimated": 0.07,
    "meter_billed": 0.00,
    "recorded": 0.3205,
    "ratio": 3.07,
    "retries": 0,
    "context_growth": 9.9,
    "context_tax": 0.68,
    "context_tax_share": 75,
    "yield_rate": 100.0,
    "trajectory_messages": 72,
    "trajectory_assistant_messages": 35,
    "meter_model_events": 35,
    "fail_to_pass": 1,
    "pass_to_pass": 88,
    "superseded_runs": 0,
    "v0_verified": 2,
    "v0_failed": 0,
    "v0_unverifiable": 2,
    "v0_unknown_rate": 0.5,
    "v0_runs": 2,
}


def log(message):
    print("==> %s" % message, flush=True)


def run(cmd, cwd=None, env=None, timeout=600, check=True, input=None):
    """Run a command, streaming nothing, returning CompletedProcess."""
    result = subprocess.run(
        cmd, cwd=cwd, env=env, timeout=timeout, input=input,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            "command failed (exit %d): %s\n%s"
            % (result.returncode, " ".join(cmd), result.stdout[-3000:])
        )
    return result


def download(url, dest):
    # --fail: a 404 must fail here, not save an HTML error page that
    # only surfaces minutes later as a JSONDecodeError.
    run(["curl", "-sL", "-f", "--retry", "3", "--retry-delay", "2",
         "-o", dest, url], timeout=300)
    if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        raise RuntimeError("download produced nothing: %s" % url)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reproduce the Averth case-study numbers.")
    parser.add_argument("--work-dir", default="repro-work",
                        help="Working directory (default: ./repro-work).")
    parser.add_argument("--force", action="store_true",
                        help="Wipe an existing work directory and redo.")
    args = parser.parse_args(argv)

    for tool in ("git", "curl", "python3"):
        if not shutil.which(tool):
            print("reproduce: error: %s is required but not on PATH" % tool,
                  file=sys.stderr)
            return 2

    repo_root = os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))
    fixtures = os.path.join(repo_root, "try-it", "fixtures")
    work = os.path.abspath(args.work_dir)
    # --force wipes a directory. Refuse targets where a wipe would be
    # catastrophic or meaningless: the filesystem root, the home
    # directory, the current directory, the repo root, and any
    # ancestor of the repo checkout.
    forbidden = {"/", os.getcwd(), repo_root, os.path.expanduser("~")}
    if work in forbidden or repo_root.startswith(work + os.sep):
        print("reproduce: error: --work-dir %s is not a safe work "
              "directory; pick a fresh directory (the default "
              "./repro-work is fine)" % work, file=sys.stderr)
        return 2
    if os.path.isfile(work):
        print("reproduce: error: %s is a file, not a directory"
              % work, file=sys.stderr)
        return 2
    if os.path.exists(work):
        if not args.force:
            print("reproduce: error: %s already exists; pass --force to "
                  "wipe it and redo the run" % work, file=sys.stderr)
            return 2
        shutil.rmtree(work)
    os.makedirs(work)
    django_base = os.path.join(work, "django-base")
    django_venv = os.path.join(work, "django-venv")
    averth_venv = os.path.join(work, "averth-venv")
    django_python = os.path.join(django_venv, "bin", "python")
    averth_python = os.path.join(averth_venv, "bin", "python")
    checks = {}  # name -> (actual, expected, ok)

    def check(name, actual, expected, places=2):
        ok = round(float(actual), places) == round(float(expected), places)
        checks[name] = (actual, expected, ok)

    def check_int(name, actual, expected):
        checks[name] = (actual, expected, int(actual) == int(expected))

    def print_table():
        print()
        print("Published-number checks:")
        failed = 0
        for name, (actual, expected, ok) in checks.items():
            print("  %s %s (actual %s, published %s)"
                  % ("PASS" if ok else "FAIL", name, actual, expected))
            failed += 0 if ok else 1
        print()
        return failed

    try:
        # 1. Downloads.
        log("downloading the public trajectory")
        traj_path = os.path.join(work, "django-15930.traj.json")
        download(TRAJ_URL, traj_path)
        # Parse the trajectory immediately: a corrupt download (or a
        # saved error page) must fail here, not minutes later.
        with open(traj_path, encoding="utf-8") as f:
            traj = json.load(f)
        check_int("trajectory messages", len(traj["messages"]),
                  PUBLISHED["trajectory_messages"])
        check_int("trajectory assistant messages",
                  sum(1 for m in traj["messages"]
                      if m.get("role") == "assistant"),
                  PUBLISHED["trajectory_assistant_messages"])
        log("downloading the leaderboard record")
        record_path = os.path.join(work, "per_instance_details.json")
        download(PER_INSTANCE_URL, record_path)
        with open(record_path, encoding="utf-8") as f:
            record = json.load(f)[INSTANCE_ID]
        for key in ("cost", "api_calls", "resolved"):
            if key not in record:
                raise RuntimeError(
                    "leaderboard record for %s has no %r field; the "
                    "leaderboard format may have changed"
                    % (INSTANCE_ID, key))
        recorded = record["cost"]
        check("recorded cost", round(recorded, 4), PUBLISHED["recorded"],
              places=4)
        check_int("leaderboard api_calls", record["api_calls"], 35)
        check_int("leaderboard resolved", record["resolved"], True)
        # The trajectory carries its own recorded cost; it must agree
        # exactly with the leaderboard figure.
        traj_cost = (traj.get("info") or {}).get("model_stats", {}).get(
            "instance_cost")
        check_int("traj instance_cost agrees with leaderboard",
                  traj_cost == recorded, True)
        log("downloading the SWE-bench task definition")
        parquet_path = os.path.join(work, "swebench-verified.parquet")
        download(PARQUET_URL, parquet_path)

        # 2. Django venv + task extraction.
        log("creating the Django venv")
        run(["python3", "-m", "venv", django_venv], timeout=300)
        run([os.path.join(django_venv, "bin", "pip"), "install", "-q",
             "asgiref", "sqlparse", "pytest", "pyarrow"], timeout=600)
        log("extracting the test patch and gold patch")
        extract = (
            "import json\n"
            "import pyarrow.parquet as pq\n"
            "t = pq.read_table(%r)\n"
            "row = [r for r in t.to_pylist() "
            "if r['instance_id'] == %r][0]\n"
            "assert row['base_commit'] == %r\n"
            "open(%r, 'w').write(row['test_patch'])\n"
            "open(%r, 'w').write(row['patch'])\n"
            "# FAIL_TO_PASS / PASS_TO_PASS are JSON-encoded strings of\n"
            "# test names, not lists: decode before counting.\n"
            "print('FAIL_TO_PASS:', "
            "len(json.loads(row['FAIL_TO_PASS'])))\n"
            "print('PASS_TO_PASS:', "
            "len(json.loads(row['PASS_TO_PASS'])))\n"
            % (parquet_path, INSTANCE_ID, BASE_COMMIT,
               os.path.join(work, "test-patch.diff"),
               os.path.join(work, "gold-patch.diff"))
        )
        extraction = run([django_python, "-c", extract], timeout=300)
        check_int("FAIL_TO_PASS is 1 test",
                  int(re.search(r"FAIL_TO_PASS: (\d+)",
                                extraction.stdout).group(1)),
                  PUBLISHED["fail_to_pass"])
        check_int("PASS_TO_PASS is 88 tests",
                  int(re.search(r"PASS_TO_PASS: (\d+)",
                                extraction.stdout).group(1)),
                  PUBLISHED["pass_to_pass"])

        # 3. Django checkout at the base commit.
        log("checking out Django at the base commit")
        run(["git", "init", "-q", django_base], timeout=120)
        run(["git", "-C", django_base, "remote", "add", "origin",
             "https://github.com/django/django.git"], timeout=120)
        run(["git", "-C", django_base, "fetch", "--depth", "1", "origin",
             BASE_COMMIT], timeout=600)
        run(["git", "-C", django_base, "checkout", "FETCH_HEAD"],
            timeout=120)
        run([os.path.join(django_venv, "bin", "pip"), "install", "-q",
             "-e", django_base], timeout=600)
        run(["git", "-C", django_base, "apply",
             os.path.join(work, "test-patch.diff")], timeout=120)

        def runtests(*tests):
            return run(
                [django_python, "tests/runtests.py"] + list(tests)
                + ["-v", "0"],
                cwd=django_base, timeout=600, check=False,
            )

        # 4. Baseline: the target test fails without the agent patch.
        log("baseline: target test without the agent patch")
        baseline = runtests(TARGET_TEST)
        with open(os.path.join(work, "baseline-pre-patch-run.txt"),
                  "w") as f:
            f.write(baseline.stdout)
        check_int("baseline target test fails",
                  baseline.returncode != 0, True)
        check_int("baseline fails with the THEN syntax error",
                  'OperationalError: near "THEN": syntax error'
                  in baseline.stdout, True)

        # 5. Agent patch from the trajectory, then the checks.
        log("applying the agent patch from the trajectory")
        submission = traj["info"]["submission"]
        with open(os.path.join(work, "submission.diff"), "w") as f:
            f.write(submission)
            f.write("\n")
        run(["git", "-C", django_base, "apply",
             os.path.join(work, "submission.diff")], timeout=120)
        log("target test with the agent patch")
        target = runtests(TARGET_TEST)
        check_int("target test passes with the agent patch",
                  target.returncode == 0, True)
        log("module tests with the agent patch")
        module = runtests("expressions_case")
        check_int("module tests pass with the agent patch",
                  module.returncode == 0, True)
        check_int("module ran 89 tests",
                  "Ran 89 tests" in module.stdout, True)
        check_int("module skipped 1 test",
                  "skipped=1" in module.stdout, True)

        # 6. Gold-patch cross-check: same target test under the fix
        # Django actually merged.
        log("gold-patch cross-check")
        run(["git", "-C", django_base, "checkout", "--",
             "django/db/models/expressions.py"], timeout=120)
        run(["git", "-C", django_base, "apply",
             os.path.join(work, "gold-patch.diff")], timeout=120)
        gold = runtests(TARGET_TEST)
        with open(os.path.join(work, "gold-patch-run.txt"), "w") as f:
            f.write(gold.stdout)
        check_int("target test passes with the gold patch",
                  gold.returncode == 0, True)
        run(["git", "-C", django_base, "checkout", "--",
             "django/db/models/expressions.py"], timeout=120)
        run(["git", "-C", django_base, "apply",
             os.path.join(work, "submission.diff")], timeout=120)

        # 7. Averth venv + meter run.
        log("creating the Averth venv")
        run(["python3", "-m", "venv", averth_venv], timeout=300)
        run([os.path.join(averth_venv, "bin", "pip"), "install", "-q",
             "-e", repo_root], timeout=600)
        log("metering the trajectory")
        meter = run(
            [averth_python, "-m", "averth.cli", "try", traj_path,
             "--model", MODEL, "--recorded", repr(recorded),
             "--out", os.path.join(work, "report.html")],
            cwd=work, timeout=300,
        )
        out = meter.stdout
        money = lambda label: float(re.search(
            label + r":\s+\$([0-9.]+)", out).group(1))
        check("meter fully loaded", money("Fully loaded"),
              PUBLISHED["meter_total"])
        check("meter priced (model)", money(r"Model/API \(terminal\)"),
              PUBLISHED["meter_priced"])
        check("meter estimated (tools)", money("Tool calls"),
              PUBLISHED["meter_estimated"])
        # The provenance split is certified from the Data quality
        # bucket lines themselves, not from the cost-component lines
        # above: a bucket-math regression must fail these checks.
        bucket = lambda label: float(re.search(
            label + r":\s+\$([0-9.]+)", out).group(1))
        check("meter priced bucket", bucket(r"Priced \([^)]*\)"),
              PUBLISHED["meter_priced"])
        check("meter estimated bucket", bucket(r"Estimated \([^)]*\)"),
              PUBLISHED["meter_estimated"])
        check("meter billed bucket", bucket(r"Vendor-supplied \(billed\)"),
              PUBLISHED["meter_billed"])
        check_int("meter retries",
                  int(re.search(r"Retries:\s+(\d+)", out).group(1)),
                  PUBLISHED["retries"])
        growth = float(re.search(
            r"Context compounding: ([0-9.]+)x input growth", out).group(1))
        check("context growth", growth, PUBLISHED["context_growth"],
              places=1)
        tax, tax_share = re.search(
            r"context tax \$([0-9.]+) \((\d+)% of model spend\)",
            out).groups()
        check("context tax", float(tax), PUBLISHED["context_tax"])
        check_int("context tax share", int(tax_share),
                  PUBLISHED["context_tax_share"])
        check("yield rate",
              float(re.search(
                  r"Yield ratio: ([0-9.]+)% of tokens on the terminal "
                  r"path", out).group(1)),
              PUBLISHED["yield_rate"], places=1)
        ratio = float(re.search(r"ESTIMATED \(([0-9.]+)x\)", out).group(1))
        check("metered/recorded ratio", ratio, PUBLISHED["ratio"])
        # The meter's own model-event count: run the converter on the
        # downloaded trajectory and count its model events. Counting
        # trajectory assistant messages would not detect a converter
        # drop (a dropped small event leaves the cent-rounded total
        # unchanged).
        converter = run(
            [averth_python, "-c",
             "import sys\n"
             "from averth.importers import miniswe\n"
             "evs = miniswe.miniswe_events(sys.argv[1], model=sys.argv[2])\n"
             "print(sum(1 for e in evs if e['type'] == 'model'))\n",
             traj_path, MODEL],
            cwd=work, timeout=300,
        )
        check_int("meter model events",
                  int(converter.stdout.strip()),
                  PUBLISHED["meter_model_events"])
        # Second meter run on the fixture JSONL events: the
        # converter's events must meter identically to the
        # trajectory run.
        jsonl_meter = run(
            [averth_python, "-m", "averth.cli", "try",
             os.path.join(fixtures, "trace-events-django-15930.jsonl"),
             "--format", "jsonl",
             "--out", os.path.join(work, "jsonl-report.html")],
            cwd=work, timeout=300,
        )
        check("JSONL meter fully loaded",
              float(re.search(r"Fully loaded:\s+\$([0-9.]+)",
                              jsonl_meter.stdout).group(1)),
              PUBLISHED["meter_total"])
        # The fixture the second run meters must itself carry 35
        # model events: a dropped small event leaves the
        # cent-rounded total unchanged, so total equality alone
        # would not detect it.
        with open(os.path.join(
                fixtures, "trace-events-django-15930.jsonl"),
                encoding="utf-8") as f:
            check_int("fixture JSONL model events",
                      sum(1 for line in f
                          if json.loads(line).get("type") == "model"),
                      PUBLISHED["meter_model_events"])

        # 8. V0 run, then the combined report.
        log("running V0 in executed mode")
        marker = (datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"))
        env = dict(os.environ)
        env["PATH"] = (os.path.join(django_venv, "bin") + ":"
                       + env["PATH"])
        v0_out = os.path.join(work, "v0-run-repro")
        run(
            [sys.executable, "cli.py",
             "--repo", django_base,
             "--checks", os.path.join(fixtures, "case-study-1-checks.json"),
             "--allowlist", os.path.join(
                 fixtures, "case-study-1-allowlist.json"),
             "--execute",
             "--python", django_python,
             "--trace", os.path.join(
                 fixtures, "trace-events-django-15930.jsonl"),
             "--final-edit-marker", marker,
             "--out", v0_out,
             "--report-id", "v0-case-study-1-repro"],
            cwd=os.path.join(repo_root, "evidence-v0"), env=env,
            timeout=600,
        )
        with open(os.path.join(v0_out, "evidence_ledger.json"),
                  encoding="utf-8") as f:
            ledger = json.load(f)
        counts = ledger["coverage"]["counts"]
        check_int("V0 VERIFIED", counts.get("VERIFIED", 0),
                  PUBLISHED["v0_verified"])
        check_int("V0 FAILED", counts.get("FAILED", 0),
                  PUBLISHED["v0_failed"])
        check_int("V0 EXTERNAL-UNVERIFIABLE",
                  counts.get("EXTERNAL-UNVERIFIABLE", 0),
                  PUBLISHED["v0_unverifiable"])
        check("V0 unknown rate", ledger["coverage"]["unknown_rate"],
              PUBLISHED["v0_unknown_rate"], places=2)
        check_int("V0 runs recorded", ledger["coverage"]["runs_total"],
                  PUBLISHED["v0_runs"])
        check_int("V0 superseded runs retained",
                  ledger["coverage"].get("superseded_runs_retained", 0),
                  PUBLISHED["superseded_runs"])
        check_int("V0 checks digest matches the published one",
                  ledger["checks_digest"] == CHECKS_DIGEST, True)
        verdicts = [j["status"] for j in ledger["judgments"]]
        check_int("V0 judgments are 2 VERIFIED then 2 unverifiable",
                  verdicts == ["VERIFIED", "VERIFIED",
                               "EXTERNAL-UNVERIFIABLE",
                               "EXTERNAL-UNVERIFIABLE"], True)
        log("rebuilding the try report with the fresh V0 ledger")
        run(
            [averth_python, "-m", "averth.cli", "try", traj_path,
             "--model", MODEL, "--recorded", repr(recorded),
             "--ledger", os.path.join(v0_out, "evidence_ledger.json"),
             "--checks", os.path.join(fixtures,
                                      "case-study-1-checks.json"),
             "--out", os.path.join(work, "report.html"),
             "--force"],
            cwd=work, timeout=300,
        )
        with open(os.path.join(work, "report.html"),
                  encoding="utf-8") as f:
            report = f.read()
        check_int("combined report shows the V0 section",
                  "What the evidence supports (V0)" in report, True)
        check_int("combined report shows the recorded comparison",
                  "3.07x" in report, True)
        check_int("combined report has no external references",
                  "http" not in report, True)
        # The provenance wording itself is checked, not just the
        # numbers: a mislabelled report must fail this script.
        bucket_html = lambda label: float(re.search(
            label + r": \$([0-9.]+)", report).group(1))
        check("combined report priced bucket",
              bucket_html(r"<b>Priced</b> \([^)]*\)"),
              PUBLISHED["meter_priced"])
        check("combined report estimated bucket",
              bucket_html(r"<b>Estimated</b> \([^)]*\)"),
              PUBLISHED["meter_estimated"])
        check("combined report billed bucket",
              bucket_html(r"<b>Vendor-supplied</b> \(billed\)"),
              PUBLISHED["meter_billed"])
        check_int("combined report discloses characters/4",
                  "characters/4 estimates" in report, True)
        check_int("combined report disclaims accepted outcomes",
                  "no cost per accepted outcome is claimed" in report,
                  True)
        check_int("combined report shows digest verified",
                  "Checks digest verified" in report, True)
        check_int("combined report labels recorded operator-supplied",
                  "operator-supplied" in report, True)
        check_int("combined report V0 rows cite observations",
                  "Cited observation" in report
                  and "output digest" in report, True)
        check_int("combined report V0 rows show all verdicts",
                  "FAILED" in report and "NOT OBSERVED" in report, True)
        check("combined report yield ratio",
              float(re.search(
                  r"<div class=\"k\">Yield ratio</div><div class=\"v\">"
                  r"([0-9.]+)%</div>", report).group(1)),
              PUBLISHED["yield_rate"], places=1)
    except Exception as exc:  # noqa: BLE001 - report and fail
        # A mid-run failure still prints the checks recorded so far;
        # the rest never ran.
        print_table()
        print("reproduce: FAILED: %s" % exc, file=sys.stderr)
        return 1

    failed = print_table()
    if failed:
        print("reproduce: %d of %d checks FAILED" % (failed, len(checks)))
        return 1
    print("reproduce: all %d checks PASSED" % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
