---
name: incident-triage
description: Triage a production incident or alert into a severity, an owner, and a first action, then keep one timeline. Separates the mitigation from the diagnosis so the timeline stays honest.
version: 2.0.0
tags: [incident, outage, alert, pager, severity]
---

## When to use

A pager fires, an alert is noisy, or a customer reports an outage and nobody owns it yet.

## Steps

1. Assign a severity and an owner before any diagnosis starts.
2. Mitigate first: restore service, not correctness.
3. Keep one timeline: timestamp, action, who, result. Append only.
4. Write the diagnosis after the incident is mitigated, from the timeline.

## Stop condition

Stop triage when service is restored and an owner is named. The postmortem is a
separate unit of work.

## Failure modes

- Diagnosing while the outage continues, so the first useful fix arrives late.
- An incident channel where the timeline is reconstructed from memory afterwards.
Next step when this happens: name an owner who is not the person diagnosing.
