# Install Averth V0 evidence verifier, branch checkout

Status: branch checkout install only. This tool is NOT
published to PyPI yet. Do not tell a customer it is on
PyPI, and do not install it from PyPI, because no such
release exists. The install below uses the branch checkout
itself, which is the only verified install path in wave 2.

## Requirements

- Python 3.9 or later. The tool itself is standard library
  only, so no tool dependency is installed.
- pytest, only if you want to run the unit tests, or to
  use cli.py --execute mode. The installed tool does not
  install pytest for you. Install it in the same
  environment with pip install pytest, or pass a python
  that already has pytest with cli.py --python.

## Install from a branch checkout, tested path

Wave 2 is uncommitted in the branch checkout, so the
clone path below is NOT yet a working install path: a
fresh clone does not contain the uncommitted wave 2
packaging files, and pip install ./evidence-v0 would
fail there. The clone path becomes valid only after
wave 2 is committed and pushed. The currently tested
path is a local checkout install, using a checkout
that already contains the wave 2 files:

```bash
python3 -m venv .venv-evidence
.venv-evidence/bin/python -m pip install /path/to/checkout/evidence-v0
.venv-evidence/bin/averth-evidence --help
```

For reference, the clone path, valid only after wave 2
is committed and pushed, is:

```bash
git clone https://github.com/Wesley3141/Averth.git
cd Averth
git checkout v0-evidence-verifier
python3 -m venv .venv-evidence
.venv-evidence/bin/python -m pip install ./evidence-v0
.venv-evidence/bin/averth-evidence --help
```

Expected: the help text for the V0 CLI prints, with
--repo, --checks, --out, --runs, --execute, --trace,
--final-edit-marker, --report-id, and --python options.
If averth-evidence is not found, the install did not
complete; do not proceed as if it had.

## Clean-install smoke run, fresh directory, no workspace copy

The smoke run below was tested in wave 2 from a fresh
directory, using only the installed tool, not the
workspace copy. It uses imported mode, so it needs no
pytest, and it creates its own tiny repo, checks, and
runs from scratch.

```bash
mkdir -p /tmp/averth-evidence-smoke/repo
cd /tmp/averth-evidence-smoke
cat > repo/test_smoke.py <<'EOF'
def test_smoke():
    assert 1 + 1 == 2
EOF
cat > checks.json <<'EOF'
{
  "task_intent": "smoke test",
  "task_intent_source": "smoke",
  "checks": [
    {
      "id": "S1",
      "text": "smoke test passes",
      "check_type": "recorded_run",
      "required_command": "python -m pytest -q test_smoke.py::test_smoke",
      "test_target": "test_smoke.py::test_smoke",
      "applicability": "applies"
    }
  ]
}
EOF
cat > runs.json <<'EOF'
{
  "final_edit_marker": "2026-11-04T00:00:00Z",
  "runs": [
    {
      "label": "smoke run",
      "command": "python -m pytest -q test_smoke.py::test_smoke",
      "working_directory": "/tmp/averth-evidence-smoke/repo",
      "start_timestamp": "2026-11-04T01:00:00Z",
      "end_timestamp": "2026-11-04T01:01:00Z",
      "exit_code": 0,
      "stdout": "1 passed",
      "stderr": ""
    }
  ]
}
EOF
averth-evidence --repo repo --checks checks.json --runs runs.json \
  --out out --report-id smoke
```

Expected: a ledger JSON and a Markdown report in out/,
with VERIFIED 1, unknown rate 0.0, 1 run, 0 superseded.
If the count differs, report the difference exactly;
do not edit the expected count to match a new run.

## What is not installed by this path

- The main Averth meter. That is a separate package,
  averth, version 0.3.0 on master, with its own install.
  Installing averth-evidence does not install the meter,
  and installing the meter does not install the verifier.
- Any demo package, fixture, or research folder. Those
  live outside evidence-v0/ and are not package data,
  except the examples/ files listed in pyproject.toml.
- Any live PR fetch verification. pr_live_fetch.py is
  installed with the tool, but its live path is labelled
  not live-verified in wave 2, and must not be cited as
  live-verified until a real fetch is run and recorded.

## Uninstall

```bash
.venv-evidence/bin/python -m pip uninstall averth-evidence
```

No other system change is made by the install. The tool
writes only to the --out directory the operator names.
