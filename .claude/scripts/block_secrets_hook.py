#!/usr/bin/env python3
"""PreToolUse hook: blocks reading/writing/executing against secrets (risk #13).

Protects the main agent and context-scout at the same time (same hook,
matcher "Read|Edit|Write|Bash" in settings.json). Checks tool_input.file_path
(Read/Edit/Write) and tool_input.command (Bash) against secret patterns and
exits with exit code 2 when it matches, which blocks the call and returns the
error message to the model.

Pattern source: docs/ai/claude-code-capabilities-verified.md, section
"Pattern for blocking secret reads".
"""
import json
import re
import sys

SECRET_PATTERNS = [
    re.compile(r"(^|[\s/])\.env(\.|$|[\s/])"),
    re.compile(r"(^|[\s/])secrets/"),
]


def matches_secret(text):
    if not text:
        return False
    return any(p.search(text) for p in SECRET_PATTERNS)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    candidates = [
        tool_input.get("file_path", ""),
        tool_input.get("command", ""),
    ]

    if any(matches_secret(c) for c in candidates):
        print(
            "Blocked: access to a secret file/pattern (.env, .env.*, secrets/**) "
            "is not allowed.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
