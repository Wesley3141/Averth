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
    if v < 0:
        return "-" + dollars(-v)
    if v == 0 or v >= 0.01:
        return "$" + "{:,.2f}".format(v)
    return "$" + "{:.6f}".format(v).rstrip("0").rstrip(".")
