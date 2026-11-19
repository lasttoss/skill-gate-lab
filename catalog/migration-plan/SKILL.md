---
name: migration-plan
description: Plan a schema or framework upgrade as a risk decision, not a technical one. Sizes the breaking change and the support deadline, names the rollback per phase, and states what will not be upgraded.
version: 0.9.1
tags: [migration, upgrade, breaking, rollback, schema]
---

## When to use

A dependency, database schema, or runtime must be upgraded and someone asks how long
it takes.

## Steps

1. Turn the fear into numbers: support deadline, count of affected call sites, and
   the three risks that would actually page someone.
2. Split the change into phases that each leave the system working: dual write, backfill,
   switch reads, remove the old path.
3. Name the rollback per phase, and the phase after which rollback stops being possible.
4. List what will not be upgraded. Wrapping and freezing is a valid decision.

## Stop condition

Stop when every phase has a rollback and the unsupported remainder is written down.

## Failure modes

- A plan that only lists the new version and the estimated time.
- Migrating and backfilling in one step, so the first failure has no way back.
Next step when this happens: split the phase and ship the dual write alone.
