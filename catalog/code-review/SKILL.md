---
name: code-review
description: Review a diff before merge. Labels every finding by severity, separates unverified claims from confirmed defects, and treats agreement between reviewers as evidence of nothing.
version: 1.2.0
tags: [review, quality, diff, merge]
---

## When to use

A diff exists and someone is about to merge it. Also when a change arrives from a
model or a contractor and nobody can vouch for it.

## Steps

1. Read the diff against the contract it claims to satisfy, not against taste.
2. Classify each finding: blocker, critical, major, minor. A finding with no stated
   consequence is minor by definition.
3. Separate confirmed defects from unverified claims. Agreement is not proof.
4. Name the trigger, the consequence, and the location for every confirmed defect.
5. Give a verdict: merge, merge after fixes, or reject.

## Stop condition

Stop when every changed line is either explained or listed as a finding. If the diff
is larger than can be read in one pass, stop and ask for it split.

## Failure modes

- Reporting style opinions as defects.
- Marking a finding "nit" to avoid an argument, which silently downgrades a real bug.
- Treating three reviewers agreeing as verification.
Next step when this happens: re-read the caller of the changed function.
