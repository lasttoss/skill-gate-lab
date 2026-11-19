# skill-gate-lab

[![ci](https://github.com/lasttoss/skill-gate-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/lasttoss/skill-gate-lab/actions/workflows/ci.yml)

A three-tier gate for `SKILL.md` catalogs and the workflows built from them.
It answers one question with a number instead of an opinion:

> Which skill, at which step, of which workflow, is broken — and what did it cost?

## Result in three lines

- **Tier 1 + tier 2 run in 0.03 s, offline, with no API key**: 5 skills, 5 case files, one 3-step
  workflow, 11 units checked, routing rank-1 **100%** (107 checks' worth of structure behind it).
- **Tier 3 records one row per step**, not one score per workflow: 18 rows for 3 inputs × 2 runs ×
  3 steps, showing `reproduce` at **66.7%** while `review` and `notes` sit at 100% — the number that
  tells you where to look.
- The smoke run fails on purpose. One oversized input exceeds its token budget and produces
  `budget_exceeded` + `assert_failed`, so `make smoke` proves the gate catches something.

Measured on 2026-11-19, this machine, stdlib Python 3.12, 35 unit tests. Full numbers:
[`docs/RESULTS.md`](docs/RESULTS.md).

## The three tiers

Cost is the axis, because the reason an eval suite dies is that someone turns it off to save money.

| Tier | Question | Cost | When it runs | In this repo |
|---|---|---|---|---|
| 1. Structure | Does the skill say when to fire, what to do, **when to stop**, and what counts as broken? | free | every commit | `gate/tier1.py` |
| 2. Routing + wiring | Does the description carry the words users say? Do two descriptions collide? Are the steps connected? | free | every commit | `gate/tier2.py` |
| 3. Behaviour | What happens when the workflow actually runs, step by step, and what does it cost? | tokens | weekly, or before release | `gate/tier3.py` |

A skill without a **stop condition** and a **failure-mode** section is a prompt with a nice
filename: an agent will follow it straight past the point where it should have handed back to a
human. Tier 1 treats those two sections as required, not decorative.

## Quickstart (no API key, no network)

```bash
make test      # 35 unit tests
make gate      # tier 1 + tier 2 + the routing floor
make smoke     # gate + a tier-3 replay run + out/report.html
open out/report.html
```

Sample output of `make gate`:

```
--- tier 1 structural: 0 finding(s)
--- tier 2 routing + wiring: 0 finding(s)
--- routing rank-1: 100.0%  (floor 100.0%)

11 units checked — 0 error(s)
PASSED
```

## Why one row per step, and eight reason codes

A workflow at 82% can be three broken steps and five perfect ones. A single score tells you to
worry, not where to look. So tier 3 writes one row per `(run, input, step)` to
`out/runs/<run_id>/steps.jsonl`:

```
run_id · workflow · input_id · repeat · step_index · step_id · skill
status       passed | failed | skipped | error
reason_codes format_invalid · empty · hallucinated · wrong_tool
             assert_failed · timeout · budget_exceeded · skipped_no_input
tokens_in · tokens_out · cost_usd · latency_ms · trace
```

The reason set is **closed** (`gate/reasons.py`), and the module says why: a free-text reason cannot
be counted, and what cannot be counted cannot be ranked. Eight codes, no ninth, no prose.

`stability_pct` answers a question most harnesses skip: with the same input repeated, did every
repeat agree? A step that returns five different answers in five runs is unusable in production
even when its average looks fine.

## The trigger model

Free tiers run on every push because they cost nothing. The paid tier runs on a schedule or by
hand, never on a random commit.

```
.github/workflows/ci.yml     push/PR  -> make test, make gate, make smoke, then the container job
                             Monday   -> tier 3, real executor, key from a secret
deploy/compose/              gate (default) · smoke · run (behind the "paid" profile)
deploy/k8s/gate-cronjob      */15 * * * *   the free tiers
deploy/k8s/tier3-cronjob     Monday 02:00Z  tier 3, key from a Secret
```

The weekly job is not there to catch a changed skill. It is there to catch the **ground moving**:
providers update models and defaults without telling anyone, and a score that drops with no commit
is the most valuable finding this system produces.

```bash
make compose                              # runs the gate in the image that ships
make run EXECUTOR_CMD='your-model-cli'    # tier 3 against any CLI: prompt on stdin, answer on stdout
```

## Console

`console/` is a Vite + React viewer. It reads the same `out/report.json` the HTML report is built
from — it is a viewer, not a source of numbers, so the gate stays runnable on a machine with no
network and no `npm`.

```bash
make smoke && cp out/report.json console/public/report.json
cd console && npm install && npm run dev
```

## What this does not prove

- The bundled **replay executor is not a model.** It is deterministic on purpose: it proves the
  pipeline end to end — step log, reason codes, cost accounting, stability — and it measures the
  *harness*, not anybody's skill quality. `tier3.py` says so at the top.
- **Tier 2 is lexical.** Stemmed TF-IDF over descriptions cannot judge semantics. It catches two
  real bugs — a description missing the words users say, and an over-broad description that
  outranks the right skill — and it also produced two findings on this repo's own catalog while it
  was being written (`upgrade`/`upgraded` split into two tokens; a zero-score tie counting as a
  collision). Both were real, both were fixed, and neither would have been visible without it.
- **One workflow, one user.** Nothing here demonstrates adoption across teams. A catalog and a
  workflow that one person wrote is evidence of method, not of rollout.
- **Cost figures use `config/prices.json`**, not a provider invoice. Change the file to match yours.

## Layout

```
gate/        frontmatter · lexical · reasons · tier1 · tier2 · tier3 · report · cli
catalog/     5 SKILL.md files under test (the 4 required sections are enforced)
cases/       routing cases per skill + cases/workflows/coding-flow.json
fixtures/    step inputs — the bytes, not a description of them
config/      prices.json · routing-baseline.json (the routing floor)
deploy/      compose + k8s cronjobs, one per cost tier
scripts/     compose_smoke.sh
tests/       35 unit tests
docs/        RESULTS.md
```
