# Measured results

Run on 2026-11-19, this machine (AMD Ryzen 7 8845HS, 16 threads), stdlib Python 3.12.23,
no network, no API key. Reproduce with `make gate && make smoke`.

## Tier 1 + tier 2

| Measure | Value |
|---|---|
| Skills in catalog | 5 |
| Case files | 5 |
| Workflows | 1 (`coding-flow`, 3 steps) |
| Units checked | 11 |
| Findings | 0 |
| Routing rank-1 rate | 100.0% (floor 100.0%) |
| Wall clock, `make gate` | 0.03 s |

## Tier 3 — smoke run (replay executor, 3 inputs × 2 runs × 3 steps)

| Measure | Value |
|---|---|
| Rows | 18 |
| Passed / failed | 16 / 2 |
| Pass rate | 88.9% |
| Cost | $0.001524 (from `config/prices.json`, not an invoice) |
| p50 latency | 99 ms |
| p95 latency | 198 ms |
| Stability | 100.0% (every repeat agreed) |
| Wall clock, `make smoke` | 0.04 s |

Per step:

| Step | Skill | Passed | Failed | Pass rate | Reasons |
|---|---|---|---|---|---|
| `reproduce` | test-first | 4 | 2 | 66.7% | `budget_exceeded`×2, `assert_failed`×2 |
| `review` | code-review | 6 | 0 | 100.0% | — |
| `notes` | release-notes | 6 | 0 | 100.0% | — |

The two failures are one input (`bug-huge-log`, a 48-line log dump) repeated twice. It exceeds the
step's `token_budget` of 400, so the executor truncates, the `must_contain` assertion fails, and the
row carries both codes. That is deliberate: a smoke run that passes everything proves nothing.

## Tests

35 unit tests, 0.012 s: `make test`.

## Findings the gate produced on its own catalog

Both were real, both were fixed, and neither was visible by reading the files:

1. **`upgrade` and `upgraded` stemmed to different tokens** (`upgrade` → `upgrade`, `upgraded` →
   `upgrad`. The router split one concept in two, so `migration-plan` lost a prompt to
   `release-notes`. Fixed by making the stemmer symmetric.
2. **A zero-score tie counted as a routing collision.** Every description scored 0 against a
   prompt sharing no vocabulary, and index 0 won the tie-break, so `code-review` was reported as
   claiming a pager prompt. A zero score everywhere is not a claim on a skill. Fixed by requiring
   score > 0 before a negative can collide.

## What is not measured here

- Any model's quality. The replay executor is a deterministic stand-in.
- Any real cost. `config/prices.json` holds assumed prices.
- Adoption. One workflow, one author.
