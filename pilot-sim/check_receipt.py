"""Numeric receipt assertions for the prospect simulation.

Runs `averth trace` exactly as a prospect would and checks the NUMBERS,
not just that sections exist. A receipt of all zeros must FAIL.
Exit 0 = all assertions held. Exit 1 = print what broke.
"""
import re
import subprocess
import sys

CLI = sys.argv[1]          # path to averth binary in the test venv
FMT = sys.argv[2]          # langfuse | langsmith | otel
TRACE = sys.argv[3]
EXPECTED_UNKNOWN = int(sys.argv[4])  # unknown calls in this fixture

fails = []


def check(name, cond, detail=""):
    if not cond:
        fails.append(f"{name}: {detail}")


def money(s):
    return float(s.replace("$", "").replace(",", ""))


r = subprocess.run([CLI, "trace", TRACE, "--format", FMT,
                    "--agent", "acme-support"],
                   capture_output=True, text=True)
check("exit code 0", r.returncode == 0, r.stderr[:300])
out = r.stdout


def grab(pat):
    m = re.search(pat, out, re.M)
    return m.group(1) if m else None


attempts = grab(r"^Attempts:\s+(\d+)")
check("attempts parsed", attempts is not None)
if attempts:
    check("attempts == 25", int(attempts) == 25, f"got {attempts}")

total = grab(r"^Total cost:\s+\$([\d.,]+)")
check("total cost parsed", total is not None)
total = money(total) if total else 0.0
check("total cost > 0", total > 0, f"got ${total}")

measured = grab(r"Measured \(tokens x vendor prices\):\s+\$([\d.,]+)")
billed = grab(r"Vendor-supplied \(billed\):\s+\$([\d.,]+)")
estimated = grab(r"Estimated \(fallback prices\):\s+\$([\d.,]+)")
check("all three buckets parsed",
      measured and billed and estimated,
      "missing bucket lines")
if measured and billed and estimated:
    s = money(measured) + money(billed) + money(estimated)
    check("buckets sum to total", abs(s - total) < 0.02,
          f"buckets=${s:.4f} total=${total:.4f}")
    check("measured > 0", money(measured) > 0)
    if FMT == "langfuse":
        check("billed > 0 (langfuse fixture has vendor costs)",
              money(billed) > 0, f"billed=${billed}")

unk = grab(r"Unknown:\s+(\d+) calls with no usage data")
if EXPECTED_UNKNOWN:
    check("unknown calls flagged", unk is not None)
    if unk:
        check(f"unknown == {EXPECTED_UNKNOWN}", int(unk) == EXPECTED_UNKNOWN,
              f"got {unk}")
else:
    check("no unknown section when none exist", unk is None or int(unk) == 0)

retries = grab(r"^Retries:\s+(\d+)")
check("retries parsed", retries is not None)
if retries:
    check("retries >= 1 (fixture has retry markers)", int(retries) >= 1,
          f"got {retries}")

failed_spend = grab(r"Failed runs:\s+\$([\d.,]+)")
check("failed-runs line parsed", failed_spend is not None)
if failed_spend:
    check("failed spend > 0 (fixture has 4 failed tickets)",
          money(failed_spend) > 0, f"got ${failed_spend}")

if fails:
    print(f"FAIL [{FMT}]:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print(f"PASS [{FMT}]: attempts={attempts} total=${total:.2f} "
      f"retries={retries} unknown={unk or 0}")
