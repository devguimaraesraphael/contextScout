#!/usr/bin/env python3
"""Hook PreToolUse: bloqueia leitura/escrita/execução sobre segredos (risco #13).

Protege o agente principal e o fast-context ao mesmo tempo (mesmo hook,
matcher "Read|Edit|Write|Bash" em settings.json). Verifica tool_input.file_path
(Read/Edit/Write) e tool_input.command (Bash) contra padroes de segredo e sai
com exit code 2 quando bate, o que bloqueia a chamada e devolve a mensagem
de erro pro modelo.

Fonte do padrao: docs/ai/claude-code-capabilities-verified.md, secao
"Padrao para bloquear leitura de segredos".
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
            "Bloqueado: acesso a arquivo/padrao de segredo (.env, .env.*, secrets/**) "
            "nao e permitido.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
