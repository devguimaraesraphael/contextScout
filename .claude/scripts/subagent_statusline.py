#!/usr/bin/env python3
"""subagentStatusLine — linha por subagent ativo (modelo discovery).

Payload confirmado empiricamente (nao documentado oficialmente): campo
"tasks", lista de {id, type, status, description, label, startTime,
tokenCount, tokenSamples, cwd}. NAO ha campo de model/agent_type aqui —
so o PreToolUse hook payload (limit_turns_hook.py) recebe "agent_type".
Por isso a convencao deste projeto e' o agente principal incluir o nome
do subagent na `description` da chamada Agent (ex: "fast-context: ..."
ou "fast-context-deep: ..."), pra aparecer legivel nesta linha.
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
