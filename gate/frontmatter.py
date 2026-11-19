"""Minimal YAML frontmatter reader for SKILL.md files.

Only the shape a SKILL.md actually uses: flat `key: value`, quoted strings,
and inline lists `[a, b]`. Anything else raises, loudly, instead of guessing.
"""

import re
from dataclasses import dataclass, field


class FrontmatterError(ValueError):
    pass


@dataclass
class SkillDoc:
    path: str
    meta: dict = field(default_factory=dict)
    body: str = ""
    lines: int = 0

    @property
    def name(self) -> str:
        return str(self.meta.get("name", ""))

    @property
    def description(self) -> str:
        return str(self.meta.get("description", ""))

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def tags(self) -> list:
        tags = self.meta.get("tags", [])
        return tags if isinstance(tags, list) else []


def _scalar(raw: str):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",") if part.strip()]
    return raw


def parse(text: str, path: str = "<text>") -> SkillDoc:
    if not text.startswith("---"):
        raise FrontmatterError(f"{path}: no frontmatter block")
    end = text.find("\n---", 3)
    if end == -1:
        raise FrontmatterError(f"{path}: frontmatter not closed")
    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise FrontmatterError(f"{path}: not a 'key: value' line: {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise FrontmatterError(f"{path}: bad key {key!r}")
        meta[key] = _scalar(value)
    return SkillDoc(path=path, meta=meta, body=body, lines=text.count("\n") + 1)
