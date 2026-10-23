"""Shared dollar rendering for reports and insights.

Agent runs routinely cost fractions of a cent. Rendering those as $0.00
makes real spend indistinguishable from missing usage data, which the
report treats as a loud warning. This helper keeps standard cent
precision for normal amounts and shows sub-cent values with enough
digits that a real cost never reads as zero.
"""


def dollars(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "$?"
    # Wave 5: a tiny NONZERO float (e.g. -1e-9 from a rounding residue)
    # formatted as "-$0" by the old code ("-" + dollars(tiny positive),
    # which itself renders "$0"). A nonzero residue below half a
    # micro-dollar renders as $0, so the sign must never survive on a
    # zero rendering. Exact zero keeps the standard "$0.00" rendering
    # (other tests and reports pin it).
    if v != 0 and abs(v) < 0.0000005:
        return "$0"
    if v < 0:
        return "-" + dollars(-v)
    if v == 0 or v >= 0.01:
        return "$" + "{:,.2f}".format(v)
    return "$" + "{:.6f}".format(v).rstrip("0").rstrip(".")
