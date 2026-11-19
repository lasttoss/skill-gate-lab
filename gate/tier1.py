"""Tier 1: structural checks. Free, deterministic, runs on every commit.

The four required sections are not cosmetic. A skill that does not say *when to
stop* and *what counts as broken* is a prompt with a nice filename: an agent will
follow it past the point where it should have handed back to a human.
"""

import os
import re

from . import frontmatter

REQUIRED_SECTIONS = (
    ("when to use", "when the skill should fire"),
    ("steps", "the ordered procedure"),
    ("stop condition", "when the agent must hand back to a human"),
    ("failure modes", "what counts as broken, and what to do next"),
)

MAX_LINES = 200
MIN_DESCRIPTION = 40
MAX_DESCRIPTION = 400
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _headings(body: str) -> list:
    return [line.lstrip("#").strip().lower()
            for line in body.splitlines() if line.startswith("#")]


def check_skill(doc: frontmatter.SkillDoc, dirname: str) -> list:
    findings = []

    def fail(code: str, detail: str):
        findings.append({"skill": dirname, "code": code, "detail": detail})

    if not doc.name:
        fail("missing_name", "frontmatter has no `name`")
    elif doc.name != dirname:
        fail("name_mismatch", f"name {doc.name!r} != directory {dirname!r}")

    if not doc.description:
        fail("missing_description", "frontmatter has no `description`")
    elif not MIN_DESCRIPTION <= len(doc.description) <= MAX_DESCRIPTION:
        fail("description_length",
             f"{len(doc.description)} chars, expected {MIN_DESCRIPTION}-{MAX_DESCRIPTION}")

    if not SEMVER.fullmatch(doc.version):
        fail("bad_version", f"version {doc.version!r} is not major.minor.patch")

    if not doc.tags:
        fail("missing_tags", "frontmatter has no non-empty `tags` list")

    headings = _headings(doc.body)
    for section, why in REQUIRED_SECTIONS:
        if not any(section in h for h in headings):
            fail("missing_section", f"no '## {section.title()}' heading ({why})")

    if doc.lines > MAX_LINES:
        fail("line_budget", f"{doc.lines} lines, budget {MAX_LINES}")

    return findings


def load_catalog(root: str) -> tuple:
    """Return (docs by skill name, findings)."""
    catalog_dir = os.path.join(root, "catalog")
    docs, findings = {}, []
    for dirname in sorted(os.listdir(catalog_dir)):
        path = os.path.join(catalog_dir, dirname, "SKILL.md")
        if not os.path.isfile(path):
            findings.append({"skill": dirname, "code": "missing_skill_md",
                             "detail": "catalog entry has no SKILL.md"})
            continue
        with open(path, encoding="utf-8") as handle:
            doc = frontmatter.parse(handle.read(), path)
        docs[dirname] = doc
        findings.extend(check_skill(doc, dirname))
    return docs, findings


def run(root: str) -> dict:
    docs, findings = load_catalog(root)
    return {"tier": 1, "skills": len(docs), "findings": findings,
            "passed": not findings}
