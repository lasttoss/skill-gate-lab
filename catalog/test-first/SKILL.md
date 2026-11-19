---
name: test-first
description: Reproduce a reported bug as a failing test before touching the fix. Records the assertion, the smallest input that shows it, and the regression guard that stays behind.
version: 1.4.0
tags: [bug, testing, regression, reproduce]
---

## When to use

A bug report arrives, or a behaviour looks wrong and nobody has a test that says so.

## Steps

1. Write the failing test first, with the smallest input that shows the bug.
2. Run it and paste the failure. A test that passes is not a reproduction.
3. Fix only what makes that test pass.
4. Keep the test as the regression guard, named after the bug.

## Stop condition

Stop when the new test fails for the reported reason and no other reason. If it fails
for a different reason, the report is not yet understood.

## Failure modes

- Writing the fix first and the test afterwards, which reproduces what was built
  rather than what was reported.
- A test that asserts on a mock instead of the reported behaviour.
Next step when this happens: throw the test away and read the report again.
