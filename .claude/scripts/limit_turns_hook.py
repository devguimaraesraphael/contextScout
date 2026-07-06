#!/usr/bin/env python3
"""context-scout's PreToolUse hook: real tool-call cutoff (Layer 2 of risk #4).

Self-counting turns in the system prompt (Layer 1) is behavioral — the subagent
can ignore it and stall without emitting <final_answer> (seen in practice, see
docs/ai/go-no-go-analysis.md, "Round 2", finding #2). This hook actually counts
Read/Grep/Glob calls per subagent invocation and denies past the limit,
returning an instruction for the model to finish.

Counting key: agent_id received in the hook payload. Confirmed empirically
(round 4, see docs/ai/go-no-go-analysis.md) that transcript_path and session_id
are the SAME value as the main session on every subagent call within the
session — using either one leaks the counter across distinct context-scout
invocations in the same session, cutting off earlier and earlier with each new
call. agent_id, on the other hand, is unique per invocation (matches the
agentId returned by the Agent tool).

Usage: configured in the `hooks.PreToolUse` frontmatter of context-scout.md,
matcher "Read|Grep|Glob". Receives the hook's JSON payload via stdin.
"""
import hashlib
import json
import os
import sys
import tempfile
import time

MAX_TOOL_CALLS = 10
COUNTER_DIR = os.path.join(tempfile.gettempdir(), "context-scout-turns")
STALE_SECONDS = 3600


def cleanup_stale():
    if not os.path.isdir(COUNTER_DIR):
        return
    now = time.time()
    for name in os.listdir(COUNTER_DIR):
        path = os.path.join(COUNTER_DIR, name)
        try:
            if now - os.path.getmtime(path) > STALE_SECONDS:
                os.remove(path)
        except OSError:
            pass


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    key_source = payload.get("agent_id") or payload.get("transcript_path") or payload.get("session_id") or ""
    if not key_source:
        sys.exit(0)

    os.makedirs(COUNTER_DIR, exist_ok=True)
    cleanup_stale()

    key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    counter_path = os.path.join(COUNTER_DIR, f"{key}.count")

    count = 0
    if os.path.isfile(counter_path):
        try:
            count = int(open(counter_path, encoding="utf-8").read().strip() or "0")
        except ValueError:
            count = 0

    count += 1
    with open(counter_path, "w", encoding="utf-8") as f:
        f.write(str(count))

    if count > MAX_TOOL_CALLS:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Limit of {MAX_TOOL_CALLS} tool calls reached (real cutoff, "
                    "not behavioral). Emit <final_answer confidence=\"low\"> "
                    "now with whatever was already found, with no more tool calls."
                ),
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
