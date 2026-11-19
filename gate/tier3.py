"""Tier 3: run the workflow and record one row per step. Costs money when a real
model is behind the executor; costs nothing with the bundled replay executor.

What this tier measures is the WORKFLOW, and it only becomes readable because of
two choices:

* One row per (run, input, step), never one score per workflow. A workflow at 82%
  can be three broken steps and five perfect ones; the score alone says nothing
  about where to look.
* A closed set of reason codes. Free-text reasons cannot be counted, and what
  cannot be counted cannot be ranked.

The bundled `replay` executor is a stand-in. It proves the pipeline end to end —
step log, reason codes, cost accounting, stability — and it measures the harness,
not any model. Plug a real one with `--executor-cmd`.
"""

import hashlib
import json
import os
import subprocess
import time

from . import reasons

RUNS_DIR = "out/runs"


class StepResult(dict):
    pass


def _now_ms() -> float:
    return round(time.time() * 1000.0, 1)


def _pct(values: list, fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round(fraction * (len(ordered) - 1))), len(ordered) - 1)
    return float(ordered[index])


def load_prices(root: str) -> dict:
    path = os.path.join(root, "config", "prices.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class ReplayExecutor:
    """Deterministic, offline, no network. Not a model: a repeatable stand-in.

    Token counts are derived from characters, latency from a hash, so two runs of
    the same input give the same numbers. A step whose input asks for more than its
    budget gets a truncated answer, which is how the smoke run produces one honest
    `budget_exceeded` failure instead of a clean sweep that proves nothing.
    """

    name = "replay"

    def __init__(self, prices: dict, model: str = "replay-1"):
        self.prices = prices
        self.model = model

    def call(self, prompt: str, meta: dict) -> dict:
        started = _now_ms()
        digest = hashlib.sha256((meta.get("step_id", "") + prompt).encode()).hexdigest()
        tokens_in = max(1, len(prompt) // 4)
        budget = meta.get("token_budget")
        truncated = bool(budget) and tokens_in > budget

        body = prompt if not truncated else prompt.split()[0]
        answer = f"[{meta.get('step_id', 'step')}] " + " ".join(body.split()[:40])
        tokens_out = max(1, len(answer) // 4)

        return {
            "text": answer if not truncated else answer + " …",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": round(int(digest[:4], 16) % 180 + 40, 1),
            "tool": meta.get("tool", "none"),
            "truncated": truncated,
            "wall_ms": round(_now_ms() - started, 1),
        }


class CommandExecutor:
    """Any CLI that takes a prompt on stdin and prints an answer on stdout.

    The contract is deliberately tiny so that swapping providers is not a rewrite:
    stdin = prompt, stdout = answer, optional JSON on stdout with
    {"text", "tokens_in", "tokens_out", "tool"}.
    """

    name = "cmd"

    def __init__(self, command: str, timeout_s: float = 120.0):
        self.command = command
        self.timeout_s = timeout_s

    def call(self, prompt: str, meta: dict) -> dict:
        started = _now_ms()
        try:
            completed = subprocess.run(
                self.command, shell=True, input=prompt, capture_output=True,
                text=True, timeout=self.timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {"text": "", "tokens_in": len(prompt) // 4, "tokens_out": 0,
                    "latency_ms": self.timeout_s * 1000, "timeout": True, "wall_ms": self.timeout_s * 1000}
        raw = completed.stdout.strip()
        payload = {"text": raw, "tokens_in": len(prompt) // 4,
                   "tokens_out": max(1, len(raw) // 4), "latency_ms": round(_now_ms() - started, 1),
                   "wall_ms": round(_now_ms() - started, 1)}
        if raw.startswith("{"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "text" in parsed:
                    payload.update({k: parsed[k] for k in
                                    ("text", "tokens_in", "tokens_out", "tool") if k in parsed})
            except json.JSONDecodeError:
                pass
        if completed.returncode != 0:
            payload["error"] = completed.stderr.strip()[:400]
        return payload


def _judge(step: dict, answer: dict, reason_out: list) -> str:
    """Return passed/failed/skipped/error. Appends reason codes as it goes."""
    if answer.get("timeout"):
        reason_out.append("timeout")
        return "failed"
    if answer.get("error"):
        reason_out.append("error")
        return "error"
    text = (answer.get("text") or "").strip()
    if not text:
        reason_out.append("empty")
        return "failed"

    expect = step.get("expect", {})
    schema = expect.get("schema", [])
    if schema and (text.startswith("{") is False or not all(f'"{f}"' in text for f in schema)):
        reason_out.append("format_invalid")

    for needle in expect.get("must_contain", []):
        if needle.lower() not in text.lower():
            reason_out.append("assert_failed")
            break

    # "at least one of" exists because a literal assertion on a word the answer does
    # not have to repeat punishes a correct answer. That mistake is recorded in
    # docs/RESULTS.md: the real-model run failed 9/9 notes steps on it.
    any_of = expect.get("must_contain_any", [])
    if any_of and not any(needle.lower() in text.lower() for needle in any_of):
        reason_out.append("assert_failed")

    minimum = expect.get("min_words")
    if minimum and len(text.split()) < minimum:
        reason_out.append("assert_failed")

    # Prose steps need a structural assertion. Asserting on a literal word punishes a
    # correct answer that does not repeat it — the mistake is recorded in docs/RESULTS.md.
    headings = sum(1 for line in text.splitlines()
                   if line.lstrip().startswith(("#", "**")) or line.lstrip().startswith("- "))
    wanted = expect.get("min_headings")
    if wanted and headings < wanted:
        reason_out.append("assert_failed")

    for needle in expect.get("must_not_contain", []):
        if needle.lower() in text.lower():
            reason_out.append("hallucinated")
            break

    budget = step.get("token_budget")
    if budget and answer.get("tokens_in", 0) + answer.get("tokens_out", 0) > budget:
        reason_out.append("budget_exceeded")

    if answer.get("truncated"):
        reason_out.append("budget_exceeded")

    return "passed" if not reason_out else "failed"


def _cost(prices: dict, model: str, tokens_in: int, tokens_out: int) -> float:
    price = prices.get(model) or prices.get("default") or {}
    return round(tokens_in / 1e6 * price.get("in_per_mtok", 0.0)
                 + tokens_out / 1e6 * price.get("out_per_mtok", 0.0), 6)


def _fixture_text(root: str, names: list) -> str:
    """Step inputs are the fixture bytes, not a description of them. Without this a
    token budget can never be exceeded and the run proves nothing about cost."""
    chunks = []
    for name in names:
        path = os.path.join(root, "fixtures", name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                chunks.append(f"--- {name} ---\n{handle.read()}")
    return "\n\n".join(chunks)


def run(root: str, flow: dict, executor, runs: int = 2, out_dir: str = None) -> dict:
    prices = load_prices(root)
    model = getattr(executor, "model", executor.name)
    stamped = time.strftime("%Y%m%dT%H%M%S")
    run_id = f"{flow['name']}-{stamped}-{executor.name}"
    run_dir = os.path.join(out_dir or os.path.join(root, RUNS_DIR), run_id)
    os.makedirs(run_dir, exist_ok=True)
    steps_path = os.path.join(run_dir, "steps.jsonl")

    rows = []
    with open(steps_path, "w", encoding="utf-8") as log:
        for entry in flow.get("inputs", []):
            for repeat in range(runs):
                attachment = _fixture_text(root, entry.get("files", []))
                for position, step in enumerate(flow.get("steps", [])):
                    prompt = f"{step.get('trigger', '')}\n\ninput: {entry.get('prompt', '')}"
                    if attachment:
                        prompt += "\n\n" + attachment
                    answer = executor.call(prompt, {**step, "input_id": entry.get("id")})
                    found_reasons = []
                    status = _judge(step, answer, found_reasons)
                    row = {
                        "run_id": run_id,
                        "workflow": flow["name"],
                        "input_id": entry.get("id"),
                        "repeat": repeat,
                        "step_index": position,
                        "step_id": step.get("id"),
                        "skill": step.get("skill"),
                        "status": status,
                        "reason_codes": sorted(set(found_reasons)),
                        "tokens_in": answer.get("tokens_in", 0),
                        "tokens_out": answer.get("tokens_out", 0),
                        "cost_usd": _cost(prices, model, answer.get("tokens_in", 0),
                                          answer.get("tokens_out", 0)),
                        "latency_ms": answer.get("latency_ms", 0),
                        "prompt_bytes": len(prompt.encode()),
                        "files": entry.get("files", []),
                        "trace": (answer.get("text") or "")[:400],
                    }
                    rows.append(row)
                    log.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = summarise(rows, runs, model)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as handle:
        json.dump({"run_id": run_id, "workflow": flow["name"], "executor": executor.name,
                   "model": model, "runs": runs, "summary": summary,
                   "rows": len(rows)}, handle, indent=2)
    return {"run_id": run_id, "run_dir": run_dir, "rows": rows, "summary": summary}


def summarise(rows: list, runs: int, model: str) -> dict:
    per_step = {}
    for row in rows:
        slot = per_step.setdefault(row["step_id"], {"step_id": row["step_id"],
                                                    "skill": row["skill"],
                                                    "passed": 0, "failed": 0,
                                                    "reasons": {}, "latency": []})
        slot["passed" if row["status"] == "passed" else "failed"] += 1
        for code in row["reason_codes"]:
            slot["reasons"][code] = slot["reasons"].get(code, 0) + 1
        slot["latency"].append(row["latency_ms"])

    for slot in per_step.values():
        total = slot["passed"] + slot["failed"]
        slot["pass_rate"] = round(100.0 * slot["passed"] / total, 1) if total else 0.0
        slot["p50_ms"] = _pct(slot["latency"], 0.50)
        slot["p95_ms"] = _pct(slot["latency"], 0.95)
        del slot["latency"]

    # Stability: for each (input, step), did every repeat agree?
    verdicts = {}
    for row in rows:
        key = (row["input_id"], row["step_id"])
        verdicts.setdefault(key, set()).add(row["status"])
    stable = sum(1 for seen in verdicts.values() if len(seen) == 1)

    total = len(rows)
    passed = sum(1 for row in rows if row["status"] == "passed")
    return {
        "rows": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(100.0 * passed / total, 1) if total else 0.0,
        "cost_usd": round(sum(row["cost_usd"] for row in rows), 6),
        "p50_ms": _pct([row["latency_ms"] for row in rows], 0.50),
        "p95_ms": _pct([row["latency_ms"] for row in rows], 0.95),
        "stability_pct": round(100.0 * stable / len(verdicts), 1) if verdicts else 0.0,
        "runs_per_input": runs,
        "model": model,
        "per_step": [per_step[k] for k in sorted(per_step, key=lambda s: str(s))],
    }
