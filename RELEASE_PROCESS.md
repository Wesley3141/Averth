# Versions, branches, and pull requests

Use this record to make every change understandable to a customer, reviewer,
or future maintainer. Keep claims tied to the data that supports them.

## Branches

Create one branch per coherent change from the current default branch. Name it
`<type>/<short-purpose>` (for example, `fix/otel-outcome-labels` or
`docs/customer-pilot-inputs`). A release preparation branch can use
`release/v0.3.0`. Keep unrelated experiments out of the branch.

In the PR, state the starting commit, the intended change, and any generated
reports or fixtures that changed. Generated reports should be reproducible
from committed inputs and a documented command. Never commit customer data,
credentials, or unredacted ledgers.

## Pull requests

Fill in [the PR template](.github/pull_request_template.md). A reviewer
should be able to answer these questions without reading the entire diff:

1. **Why now?** Name the user-visible problem and the concrete trigger.
2. **What changed?** Give a before/after example, including changed API keys
   or report language. Explain any migration needed by an existing caller.
3. **What supports the result?** Distinguish measured tokens, billed costs,
   caller-provided outcomes, inferred trace status, and assumptions. Do not
   turn historical flagged spend into a projected saving.
4. **How was it checked?** List the exact test and validation commands, their
   results, and any fixture or real-trace comparison. State the limits of
   that evidence, especially when a snapshot came from the same event stream.
5. **What remains?** Name material limitations and the next customer input
   needed to close them. Link the relevant issue or follow-up when one exists.

Merge a PR after the relevant tests pass, generated artifacts match current
code, public docs match behavior, and a reviewer can trace important dollar
claims to their source. A change to cost or outcome semantics needs a test
that would fail under the previous behavior.

## Versions and release notes

The package version lives in `pyproject.toml`. While Averth is in the 0.x
series, increase the minor version for a breaking API or meaning change and
the patch version for a compatible correction. Increase the minor version
for a new capability that changes what customers can do. Keep the release
entry in [CHANGELOG.md](CHANGELOG.md) aligned with the package version.

Each entry should include:

- **Changed behavior:** what a customer sees and why it changed.
- **Compatibility:** renamed fields, removed aliases, and migration steps.
- **Evidence:** tests, trace checks, and invoice comparisons, with sample
  data clearly labeled as synthetic when applicable.
- **Known limits:** assumptions or missing data that affect interpretation.

Tag a version after its PR is merged and the installation, CLI, and release
notes have been checked from the merged commit. A clean code release is a
pilot-readiness milestone. A seed-funding claim needs separate commercial
evidence: real customer traces joined to accepted outcomes, cost reconciliation
against bills, repeat use, and willingness to pay. Record that evidence in
the fundraising materials without putting confidential customer data here.
