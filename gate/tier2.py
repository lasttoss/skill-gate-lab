"""Tier 2: routing and workflow wiring. Free, deterministic, runs on every commit.

Two jobs:

1. Routing. Each case lists prompts that must rank their skill inside `top_k`, and
   prompts that must not rank it first. A description that misses the words users
   say fails the first; an over-broad description fails the second.
2. Wiring. A workflow is only worth measuring if its steps are connected. Four
   checks, in the order they break in practice: does each step's trigger activate
   *its* skill, are the steps ordered so every input exists when it is needed, do
   two steps write the same artifact, and does the producing step emit every field
   the consumer declares.
"""

import json
import os

from . import lexical

COLLISION_THRESHOLD = 0.55


def _load_cases(root: str) -> list:
    cases_dir = os.path.join(root, "cases")
    cases = []
    for name in sorted(os.listdir(cases_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(cases_dir, name), encoding="utf-8") as handle:
            cases.append(json.load(handle))
    return cases


def _load_workflows(root: str) -> list:
    flow_dir = os.path.join(root, "cases", "workflows")
    flows = []
    for name in sorted(os.listdir(flow_dir)):
        if name.endswith(".json"):
            with open(os.path.join(flow_dir, name), encoding="utf-8") as handle:
                flows.append(json.load(handle))
    return flows


def check_routing(docs: dict, cases: list) -> list:
    names = list(docs)
    index = lexical.Index([docs[n].description for n in names])
    findings = []
    for case in cases:
        skill = case["skill_name"]
        if skill not in docs:
            findings.append({"skill": skill, "code": "orphan_case",
                             "detail": "case file names a skill that is not in the catalog"})
            continue
        target = names.index(skill)
        for entry in case.get("trigger", {}).get("positive", []):
            top_k = entry.get("top_k", 3)
            ranking = index.rank(entry["prompt"])
            position = next(i for i, (doc_i, _) in enumerate(ranking) if doc_i == target)
            if position >= top_k:
                winner = names[ranking[0][0]]
                findings.append({
                    "skill": skill, "code": "positive_missed",
                    "detail": f"ranked {position + 1} (needs top {top_k}) for "
                              f"{entry['prompt']!r}; {winner!r} won",
                })
        for entry in case.get("trigger", {}).get("negative", []):
            ranking = index.rank(entry.get("prompt", ""))
            # A zero score everywhere is not a claim on the skill: it means the
            # prompt shares no vocabulary with any description. Counting the
            # index-0 tie as a collision would make the check fire on noise.
            if ranking and ranking[0][0] == target and ranking[0][1] > 0.0:
                findings.append({
                    "skill": skill, "code": "negative_collision",
                    "detail": f"ranked first for a prompt it must not claim: "
                              f"{entry.get('prompt', '')!r}",
                })
    return findings


def check_collisions(docs: dict) -> list:
    names = list(docs)
    index = lexical.Index([docs[n].description for n in names])
    findings = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            similarity = lexical.cosine(index.vectors[i], index.vectors[j])
            if similarity > COLLISION_THRESHOLD:
                findings.append({
                    "skill": names[i], "code": "description_collision",
                    "detail": f"cosine {similarity:.2f} with {names[j]!r} "
                              f"(threshold {COLLISION_THRESHOLD})",
                })
    return findings


def check_workflow(flow: dict, docs: dict) -> list:
    findings = []
    name = flow.get("name", "<unnamed>")
    names = list(docs)
    index = lexical.Index([docs[n].description for n in names])
    available = {}          # artifact -> set of fields written so far

    def fail(code, detail, step=None):
        findings.append({"workflow": name, "step": step, "code": code, "detail": detail})

    for position, step in enumerate(flow.get("steps", [])):
        step_id = step.get("id", f"step{position + 1}")
        skill = step.get("skill")

        if skill not in docs:
            fail("unknown_skill", f"step names skill {skill!r} which is not in the catalog", step_id)
            continue

        trigger = step.get("trigger", "")
        if trigger:
            ranking = index.rank(trigger)
            winner = names[ranking[0][0]]
            if winner != skill:
                fail("activation_miss", f"trigger activates {winner!r} instead of {skill!r}", step_id)

        for needed, fields in step.get("needs", {}).items():
            if needed not in available:
                fail("missing_dependency",
                     f"needs {needed!r} but no earlier step writes it", step_id)
                continue
            missing = sorted(set(fields) - available[needed])
            if missing:
                fail("contract_gap",
                     f"{needed!r} is missing fields {missing}", step_id)

        for written, fields in step.get("writes", {}).items():
            if written in available:
                fail("overlap", f"{written!r} is written by more than one step", step_id)
            available[written] = set(fields)

    return findings


def run(root: str, docs: dict) -> dict:
    cases = _load_cases(root)
    flows = _load_workflows(root)
    findings = check_routing(docs, cases)
    findings += check_collisions(docs)
    for flow in flows:
        findings += check_workflow(flow, docs)
    rank1 = rank1_rate(docs, cases)
    return {"tier": 2, "cases": len(cases), "workflows": len(flows),
            "rank1_rate": rank1, "findings": findings, "passed": not findings}


def rank1_rate(docs: dict, cases: list) -> float:
    names = list(docs)
    index = lexical.Index([docs[n].description for n in names])
    hits = total = 0
    for case in cases:
        skill = case["skill_name"]
        if skill not in docs:
            continue
        target = names.index(skill)
        for entry in case.get("trigger", {}).get("positive", []):
            total += 1
            ranking = index.rank(entry["prompt"])
            if ranking[0][0] == target:
                hits += 1
    return round(100.0 * hits / total, 1) if total else 0.0
