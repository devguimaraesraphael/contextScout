#!/usr/bin/env python3
"""Validates file:start_line-end_line citations coming from a context-scout <final_answer>.

Deterministic mirror of the os.path.isfile() validation from the reference
project (Cirius1792/fastcontext) -- only checks file existence and whether the
line range is valid, does not check semantic relevance.

Usage:
    echo "$FINAL_ANSWER_CITATIONS" | python3 .claude/scripts/validate_citations.py

Input: one citation per line, format "/path/file.ext:10-15 optional text".
Output: "OK <citation>" per valid line (stdout), "WARN <reason>" per invalid line (stderr).
Exit code 1 if any citation is invalid, 0 if all pass (or empty input).
"""
import os
import re
import sys

PATTERN = re.compile(r"^(.+?):(\d+)(?:-(\d+))?\s*(.*)$")


def validate_line(line):
    match = PATTERN.match(line)
    if not match:
        return False, f"unexpected format: {line}"

    path, start_s, end_s, _rest = match.groups()
    start = int(start_s)
    end = int(end_s) if end_s else start

    if not os.path.isfile(path):
        return False, f"file does not exist: {path}"

    with open(path, encoding="utf-8", errors="replace") as f:
        total_lines = sum(1 for _ in f)

    if start < 1 or start > end or end > total_lines:
        return False, f"invalid line range ({start}-{end}, file has {total_lines} lines): {path}"

    return True, f"{path}:{start}-{end}"


def main():
    had_invalid = False
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        ok, message = validate_line(line)
        if ok:
            print(f"OK {message}")
        else:
            print(f"WARN {message}", file=sys.stderr)
            had_invalid = True
    sys.exit(1 if had_invalid else 0)


if __name__ == "__main__":
    main()
