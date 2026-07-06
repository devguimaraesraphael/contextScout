#!/usr/bin/env python3
"""subagentStatusLine — one line per active subagent (discovery model).

Payload confirmed empirically (not officially documented): field "tasks", a
list of {id, type, status, description, label, startTime, tokenCount,
tokenSamples, cwd}. There is NO model/agent_type field here — only the
PreToolUse hook payload (limit_turns_hook.py) receives "agent_type". That's
why this project's convention is for the main agent to include the
subagent's name in the `description` of the Agent call (e.g. "context-scout: ..."
or "context-scout-deep: ..."), so it shows up legibly on this line.
"""
import json
import sys


def fmt_tokens(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tasks = [t for t in payload.get("tasks", []) if t.get("status") == "running"]
    if not tasks:
        return

    lines = []
    for t in tasks:
        label = t.get("label") or t.get("description") or t.get("id", "?")
        lines.append(f"🔎 {label}: {fmt_tokens(t.get('tokenCount', 0))} tokens")

    print(" | ".join(lines))


if __name__ == "__main__":
    main()
