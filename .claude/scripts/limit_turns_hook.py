#!/usr/bin/env python3
"""Hook PreToolUse do fast-context: corte real de tool calls (Camada 2 do risco #4).

A auto-contagem de turnos no system prompt (Camada 1) e comportamental — o subagent
pode ignora-la e travar sem emitir <final_answer> (visto na pratica, ver
docs/ai/go-no-go-analysis.md, "Rodada 2", achado #2). Este hook conta de verdade as
chamadas de Read/Grep/Glob por invocacao do subagent e nega a partir do limite,
devolvendo uma instrucao pro modelo finalizar.

Chave de contagem: agent_id recebido no payload do hook. Confirmado empiricamente
(rodada 4, ver docs/ai/go-no-go-analysis.md) que transcript_path e session_id sao
o MESMO valor da sessao principal em toda chamada de subagent dentro da sessao —
usar qualquer um dos dois faz o contador vazar entre invocacoes distintas do
fast-context na mesma sessao, cortando cada vez mais cedo a cada chamada nova.
agent_id, por outro lado, e unico por invocacao (bate com o agentId devolvido
pela ferramenta Agent).

Uso: configurado no frontmatter `hooks.PreToolUse` do fast-context.md, matcher
"Read|Grep|Glob". Recebe o payload JSON do hook via stdin.
"""
import hashlib
import json
import os
import sys
import tempfile
import time

MAX_TOOL_CALLS = 10
COUNTER_DIR = os.path.join(tempfile.gettempdir(), "fast-context-turns")
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
                    f"Limite de {MAX_TOOL_CALLS} tool calls atingido (corte real, "
                    "nao comportamental). Emita <final_answer confidence=\"low\"> "
                    "agora com o que ja foi encontrado, sem mais tool calls."
                ),
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
