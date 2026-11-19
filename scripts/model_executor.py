#!/usr/bin/env python3
"""A real executor for tier 3: prompt on stdin, JSON answer on stdout.

The gate does not know which provider you use, and this script keeps it that way.
Everything comes from the environment, so no key is ever written into the repo:

    MODEL_API_KEY    required
    MODEL_BASE_URL   default https://ollama.com/v1   (any OpenAI-compatible base)
    MODEL_NAME       default deepseek-v4.1-flash
    MODEL_SYSTEM     optional system prompt override

Usage:

    MODEL_API_KEY=... make run EXECUTOR_CMD='python3 scripts/model_executor.py'

Exit codes: 2 when the key is missing, 1 when the provider call fails. The gate
records those as `error` rows rather than silently passing a step.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

SYSTEM = (
    "You are one step inside a fixed workflow. Do only this step. "
    "Answer in at most 80 words, no preamble."
)


def main() -> int:
    key = os.environ.get("MODEL_API_KEY", "").strip()
    if not key:
        print("MODEL_API_KEY is not set", file=sys.stderr)
        return 2

    base = os.environ.get("MODEL_BASE_URL", "https://ollama.com/v1").rstrip("/")
    model = os.environ.get("MODEL_NAME", "deepseek-v4.1-flash")
    system = os.environ.get("MODEL_SYSTEM", SYSTEM)
    prompt = sys.stdin.read()

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0,
    }).encode()

    request = urllib.request.Request(
        f"{base}/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        print(f"provider HTTP {error.code}: {error.read()[:300]!r}", file=sys.stderr)
        return 1
    except Exception as error:                      # network, DNS, timeout
        print(f"provider call failed: {error}", file=sys.stderr)
        return 1

    usage = body.get("usage") or {}
    text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
    print(json.dumps({
        "text": text.strip(),
        "tokens_in": usage.get("prompt_tokens", len(prompt) // 4),
        "tokens_out": usage.get("completion_tokens", len(text) // 4),
        "tool": "none",
        "latency_ms": round((time.time() - started) * 1000, 1),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
