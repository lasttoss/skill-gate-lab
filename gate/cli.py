"""Command line: `python3 -m gate.cli <command>`.

Commands, and why each exists:
  tier1        structure only — must be green before anything else is worth running
  tier2        routing + wiring — free, deterministic, safe for CI
  gate         tier1 + tier2 + the routing floor (the ratchet that stops slow rot)
  smoke        gate + a tier-3 replay run + the report; no network, no key
  run          tier-3 against a real executor command
  baseline     write the current routing floor after a deliberate improvement
"""

import argparse
import json
import os
import sys

from . import report, tier1, tier2, tier3


def _root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _baseline_path(root: str) -> str:
    return os.path.join(root, "config", "routing-baseline.json")


def _read_baseline(root: str) -> dict:
    path = _baseline_path(root)
    if not os.path.isfile(path):
        return {"rank1_floor": 0.0}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _print_findings(title: str, findings: list) -> None:
    print(f"--- {title}: {len(findings)} finding(s)")
    for finding in findings:
        unit = finding.get("skill") or finding.get("workflow")
        step = f" [{finding['step']}]" if finding.get("step") else ""
        print(f"    {unit}{step}: {finding['code']} — {finding['detail']}")


def cmd_gate(args) -> int:
    root = _root()
    docs, _ = tier1.load_catalog(root)
    first = tier1.run(root)
    second = tier2.run(root, docs)
    _print_findings("tier 1 structural", first["findings"])
    _print_findings("tier 2 routing + wiring", second["findings"])

    baseline = _read_baseline(root)
    floor = float(baseline.get("rank1_floor", 0.0))
    print(f"--- routing rank-1: {second['rank1_rate']}%  (floor {floor}%)")
    ratchet_failed = second["rank1_rate"] < floor
    if ratchet_failed:
        print(f"    RATCHET: routing dropped below the committed floor {floor}%")

    checks = first["skills"] + second["cases"] + second["workflows"]
    failed = len(first["findings"]) + len(second["findings"]) + int(ratchet_failed)
    print(f"\n{checks} units checked — {failed} error(s)")
    print("PASSED" if failed == 0 else "FAILED")
    return 0 if failed == 0 else 1


def cmd_tier1(args) -> int:
    result = tier1.run(_root())
    _print_findings("tier 1 structural", result["findings"])
    print(f"\n{result['skills']} skills checked — {len(result['findings'])} error(s)")
    print("PASSED" if result["passed"] else "FAILED")
    return 0 if result["passed"] else 1


def cmd_tier2(args) -> int:
    root = _root()
    docs, _ = tier1.load_catalog(root)
    result = tier2.run(root, docs)
    _print_findings("tier 2 routing + wiring", result["findings"])
    print(f"--- routing rank-1: {result['rank1_rate']}%")
    print(f"\n{result['cases']} cases, {result['workflows']} workflows — "
          f"{len(result['findings'])} error(s)")
    print("PASSED" if result["passed"] else "FAILED")
    return 0 if result["passed"] else 1


def cmd_baseline(args) -> int:
    root = _root()
    docs, _ = tier1.load_catalog(root)
    result = tier2.run(root, docs)
    floors = [result["rank1_rate"]]
    if args.min is not None:
        floors.append(float(args.min))
    floor = min(floors)
    path = _baseline_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"rank1_floor": floor}, handle, indent=2)
        handle.write("\n")
    print(f"wrote routing floor {floor}% to {os.path.relpath(path, root)}")
    return 0


def _workflow(root: str, name: str) -> dict:
    path = os.path.join(root, "cases", "workflows", f"{name}.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def cmd_run(args) -> int:
    root = _root()
    flow = _workflow(root, args.workflow)
    prices = tier3.load_prices(root)
    if args.executor_cmd:
        executor = tier3.CommandExecutor(args.executor_cmd, args.timeout)
    else:
        executor = tier3.ReplayExecutor(prices)
    result = tier3.run(root, flow, executor, runs=args.runs)
    summary = result["summary"]
    print(f"run {result['run_id']}")
    print(f"  executor {executor.name} · {summary['rows']} rows · "
          f"{summary['runs_per_input']} runs/input")
    print(f"  pass {summary['pass_rate']}% · cost ${summary['cost_usd']:.6f} · "
          f"p50 {summary['p50_ms']} ms · p95 {summary['p95_ms']} ms · "
          f"stability {summary['stability_pct']}%")
    for step in summary["per_step"]:
        reasons = ", ".join(f"{k}×{v}" for k, v in sorted(step["reasons"].items())) or "—"
        print(f"    {step['step_id']:<12} {step['passed']:>2} pass {step['failed']:>2} fail  "
              f"{step['pass_rate']:>5}%  {reasons}")
    return 0


def cmd_report(args) -> int:
    """Rebuild the report from the newest recorded run, without spending anything.

    A run costs tokens; reading its rows does not. Keeping these two separate is why
    a paid run is worth running at all — you can re-render it a hundred times.
    """
    root = _root()
    runs_dir = os.path.join(root, tier3.RUNS_DIR)
    candidates = sorted(
        (os.path.join(runs_dir, name) for name in os.listdir(runs_dir)
         if os.path.isfile(os.path.join(runs_dir, name, "run.json"))),
        key=os.path.getmtime,
    ) if os.path.isdir(runs_dir) else []
    if not candidates:
        print("no recorded run under out/runs — run `make smoke` or `make run` first")
        return 1
    run_dir = candidates[-1]
    with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as handle:
        recorded = json.load(handle)
    with open(os.path.join(run_dir, "steps.jsonl"), encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    summary = dict(recorded["summary"])
    summary["failures"] = [row for row in rows if row["status"] != "passed"]

    docs, _ = tier1.load_catalog(root)
    document = report.to_json(tier1.run(root), tier2.run(root, docs), summary,
                              _read_baseline(root))
    json_path, html_path = report.write(root, document)
    print(f"--- report from {os.path.basename(run_dir)} "
          f"({recorded['executor']} · {summary['rows']} rows · pass {summary['pass_rate']}%)")
    print(f"    {os.path.relpath(html_path, root)} · {os.path.relpath(json_path, root)}")
    return 0


def cmd_smoke(args) -> int:
    code = cmd_gate(args)
    root = _root()
    docs, _ = tier1.load_catalog(root)
    first = tier1.run(root)
    second = tier2.run(root, docs)
    flow = _workflow(root, args.workflow)
    result = tier3.run(root, flow, tier3.ReplayExecutor(tier3.load_prices(root)),
                       runs=args.runs)
    summary = dict(result["summary"])
    summary["failures"] = [row for row in result["rows"] if row["status"] != "passed"]
    document = report.to_json(first, second, summary, _read_baseline(root))
    json_path, html_path = report.write(root, document)
    print(f"\n--- report: {os.path.relpath(html_path, root)} "
          f"({os.path.getsize(html_path)} bytes) · {os.path.relpath(json_path, root)}")
    print(f"    workflow {flow['name']}: pass {summary['pass_rate']}% · "
          f"cost ${summary['cost_usd']:.6f} · stability {summary['stability_pct']}%")
    return code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gate.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tier1").set_defaults(func=cmd_tier1)
    sub.add_parser("tier2").set_defaults(func=cmd_tier2)

    gate = sub.add_parser("gate")
    gate.set_defaults(func=cmd_gate, workflow="coding-flow", runs=2)

    baseline = sub.add_parser("baseline")
    baseline.add_argument("--min", type=float, default=None,
                          help="also cap the floor, e.g. 95 to refuse a lower floor")
    baseline.set_defaults(func=cmd_baseline)

    run = sub.add_parser("run")
    run.add_argument("--workflow", default="coding-flow")
    run.add_argument("--runs", type=int, default=2)
    run.add_argument("--executor-cmd", default="")
    run.add_argument("--timeout", type=float, default=120.0)
    run.set_defaults(func=cmd_run)

    report_cmd = sub.add_parser("report")
    report_cmd.set_defaults(func=cmd_report)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--workflow", default="coding-flow")
    smoke.add_argument("--runs", type=int, default=2)
    smoke.set_defaults(func=cmd_smoke)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
