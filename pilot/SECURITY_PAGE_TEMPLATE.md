# Averth Security & Data Practices (Template)

> DRAFT — publish a version of this before any customer outreach. Have
> counsel review the DPA before signing with a customer.

## What data Averth receives

**Default (recommended): none of your workflow data leaves your systems.**
Averth's harness runs inside your environment. Only aggregated results that
you explicitly approve are shared with us.

**Opt-in trace sharing:** if you choose to share redacted traces for deeper
analysis, redaction happens on your side with our open redactor. You review
the redaction report (what was stripped, counts by category) before anything
is transmitted.

## What we never do

- Train models on your data. Ever.
- Store prompts, traces, or workflow contents beyond the engagement.
- Share your data with third parties except the subprocessors below, and
  then only as required to perform the engagement.

## Retention and deletion

- Engagement data: deleted 30 days after engagement end, automatically.
- Aggregated experiment metadata (see below): retained per the pilot
  agreement, or deleted on written request.
- You may request deletion at any time: [contact].

## Anonymized experiment metadata

With your agreement (opt-out available), we retain anonymized metadata:
workflow pattern category, intervention type, measured effect size. This
contains no prompts, no traces, no business data, and cannot be traced back
to your workflows.

## Subprocessors

| Subprocessor | Purpose | Data |
|---|---|---|
| [Model provider, e.g. Anthropic] | Running experiments you approve | Prompts for the approved runs only |
| [Cloud/hosting] | [purpose] | [data] |

We will notify you before adding a subprocessor.

## Infrastructure

- Region: [region]
- Encryption: TLS 1.2+ in transit, AES-256 at rest.
- Access: least-privilege; engagement staff only.

## Compliance roadmap

- SOC 2 Type I: [in progress / planned Q_]
- DPA: available on request — standard template covers GDPR/CCPA processing
  terms.

## Contact

Security questions: [security contact]
