# Baseline de queries — Fase 7 (validação end-to-end)

Repositório de teste: `/mnt/backup/github/fastcontext` (implementação de referência
Python do FastContext original, fora deste projeto). Escolhido porque já foi usado
nas rodadas 1-4 (familiaridade com o código, gabarito fácil de conferir à mão) e
tem múltiplos módulos pequenos — bom fit pro caso de uso do `fast-context`.

**Aviso de escopo (risco #11):** isto é um *smoke test* contra um único repositório
Python de porte pequeno. Não é prova de generalização pra outras linguagens ou
repositórios grandes — expandir a amostra é trabalho futuro, fora desta fase.

Gabarito conferido manualmente por leitura direta (`Read`/`cat -n`), sem delegação,
em 2026-07-06, contra o estado atual do repositório de referência.

## Queries que DEVERIAM disparar o fast-context (multi-arquivo/módulo)

### Q1 — Limite de turnos

**Pergunta:** "Onde fica a lógica que decide o `max_turns` do agente e o que acontece quando ele é atingido?"

**Gabarito:**
- `src/fastcontext/agent/agent.py:44-54` — loop principal: `n_turn > max_turns + 1` retorna `"No final answer after {max_turns} turns."`; em `n_turn == max_turns + 1` injeta mensagem de usuário pedindo resposta final.
- `src/fastcontext/cli.py:23` — flag `--max-turns`, default `4`.

### Q2 — Templating do system prompt

**Pergunta:** "Como o system prompt do agente é montado com templating, e quais variáveis são injetadas?"

**Gabarito:**
- `src/fastcontext/agent/utils.py:11-17` — `SystemPromptArgs` (dataclass: `OS_KIND`, `SHELL_NAME`, `WORK_DIR`, `WORK_DIR_LS`).
- `src/fastcontext/agent/utils.py:19-33` — `_load_system_prompt`: Jinja2 com delimitador customizado `${...}` (não o padrão `{{...}}`).
- `src/fastcontext/agent/utils.py:36-53` — `load_system_prompt`: monta os `builtin_args` (detecta OS, shell, lista o `work_dir`) e chama `_load_system_prompt` com `system.md` como template.

### Q3 — Validação de citações

**Pergunta:** "Como as citações do `final_answer` são parseadas e validadas antes de virar resposta final?"

**Gabarito:**
- `src/fastcontext/agent/utils.py:56-87` — `parse_citations`: regex `(.+?):(\d+(?:-\d+)?)\s*(.*)` extrai path/range/explicação de cada linha dentro de `<final_answer>`.
- `src/fastcontext/agent/utils.py:90-108` — `format_citations`: valida com `os.path.isfile(c["path"])`, descarta citação de arquivo inexistente.
- `src/fastcontext/agent/utils.py:111-114` — `get_final_answer` encadeia parse → format.

### Q4 — Registro de ferramentas do agente

**Pergunta:** "Onde as ferramentas (tools) do agente explorador são registradas e quais são?"

**Gabarito:**
- `src/fastcontext/agent/agent_factory.py:56-66` — import de `GlobTool`, `GrepTool`, `ReadTool`; checa `RG_PATH` (ripgrep instalado); monta `ToolSet([ReadTool(), GlobTool(), GrepTool()], work_dir=work_dir)`.

## Queries que NÃO deveriam disparar o fast-context (triviais)

### Q5 — Lookup trivial de um único arquivo já conhecido

**Pergunta:** "No `cli.py`, o que a flag `--max-turns` aceita como tipo e qual o default?"

**Gabarito:** `src/fastcontext/cli.py:23` — `type=int`, `default=4`.

Por que não deveria disparar: arquivo único, já nomeado na pergunta, grep/read direto resolve em 1 tool call — exatamente o critério de "não usar" em `.claude/rules/exploration.md`.

### Q6 — Edição pura, sem exploração

**Pergunta (instrução, não pergunta):** "No `cli.py`, muda o default de `--max-turns` de 4 pra 8."

**Gabarito:** mesma linha, `src/fastcontext/cli.py:23` — trocar `default=4` por `default=8`.

Por que não deveria disparar: é edição direta sobre símbolo já visível/nomeado, sem necessidade de busca — critério de "não usar" (edição pura).

## Metodologia de execução

Cada query Q1-Q4 roda em dois modos, na mesma sessão principal:
1. **Com delegação**: pedir explicitamente "use o fast-context para responder".
2. **Sem delegação**: pedir explicitamente "responda direto, sem delegar a nenhum subagent" (agente principal usa Read/Grep/Glob nativos).

Q5-Q6 rodam só uma vez cada, em modo natural (sem forçar nem proibir delegação) — o objetivo é observar se o agente principal delega ou não por conta própria, contra o gabarito de "não deveria".

Métricas registradas por rodada (tabela abaixo): tokens (main + subagent, quando aplicável), tempo, se a citação bateu com o gabarito (precisão/recall), `confidence` reportado vs. corretude real, se o limite de turnos segurou quando testado, se delegação ocorreu quando não deveria (Q5-Q6) ou deixou de ocorrer quando deveria (Q1-Q4 modo natural, não testado aqui pois já forçamos o modo).

## Resultados

Ver tabela datada em `docs/ai/eval/baseline-results-2026-07-06.md`.
