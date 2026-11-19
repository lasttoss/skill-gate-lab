---
name: release-notes
description: Write the changelog for a release from the merged changes, grouped by audience. States what shipped, what changed for the user, and what is deliberately not in this release.
version: 1.0.3
tags: [changelog, release, notes, audience]
---

## When to use

A release is being cut and someone has to tell users, support, or the client what is
actually inside it.

## Steps

1. Collect merged changes and drop anything that never reached the release branch.
2. Group by audience: end user, integrator, operator.
3. For each item, state the change in the words the audience uses.
4. List what was deliberately excluded, so the absence is a decision and not a rumour.

## Stop condition

Stop when every merged change is either described or listed as not release-note worthy.

## Failure modes

- A changelog made of commit subjects, which describe the code and not the change.
- Announcing a feature that shipped behind a flag that is still off.
Next step when this happens: check the flag state before publishing.
