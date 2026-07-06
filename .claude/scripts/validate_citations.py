#!/usr/bin/env python3
"""Valida citacoes arquivo:linha_inicio-linha_fim vindas de um <final_answer> do fast-context.

Mirror deterministico da validacao os.path.isfile() do projeto de referencia
(Cirius1792/fastcontext) -- so confere existencia do arquivo e se a faixa de
linha e valida, nao confere relevancia semantica.

Uso:
    echo "$FINAL_ANSWER_CITATIONS" | python3 .claude/scripts/validate_citations.py

Entrada: uma citacao por linha, formato "/caminho/arquivo.ext:10-15 texto opcional".
Saida: "OK <citacao>" por linha valida (stdout), "WARN <motivo>" por linha invalida (stderr).
Exit code 1 se alguma citacao for invalida, 0 se todas passarem (ou entrada vazia).
"""
import os
import re
import sys

PATTERN = re.compile(r"^(.+?):(\d+)(?:-(\d+))?\s*(.*)$")


def validate_line(line):
    match = PATTERN.match(line)
    if not match:
        return False, f"formato inesperado: {line}"

    path, start_s, end_s, _rest = match.groups()
    start = int(start_s)
    end = int(end_s) if end_s else start

    if not os.path.isfile(path):
        return False, f"arquivo nao existe: {path}"

    with open(path, encoding="utf-8", errors="replace") as f:
        total_lines = sum(1 for _ in f)

    if start < 1 or start > end or end > total_lines:
        return False, f"faixa de linha invalida ({start}-{end}, arquivo tem {total_lines} linhas): {path}"

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
