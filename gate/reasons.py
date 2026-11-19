"""The closed set of failure reasons.

A free-text reason cannot be counted, and a reason that cannot be counted cannot
be ranked. This is the whole point of the module: eight codes, no ninth, no prose.
"""

CODES = {
    "format_invalid": "output did not match the declared schema",
    "empty": "output was empty or whitespace",
    "hallucinated": "assertion caught content that is not in the input",
    "wrong_tool": "the step ran but not the tool the step declares",
    "assert_failed": "a declared expectation did not hold",
    "timeout": "the step exceeded its time budget",
    "budget_exceeded": "the step exceeded its token or money budget",
    "skipped_no_input": "a required input was missing before the step ran",
}

STATUSES = ("passed", "failed", "skipped", "error")


def check(code: str) -> str:
    if code not in CODES:
        raise ValueError(f"unknown reason code {code!r}; valid: {sorted(CODES)}")
    return code
