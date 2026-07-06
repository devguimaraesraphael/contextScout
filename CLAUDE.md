# fastContext

Reimplementação do conceito **FastContext** (originalmente `microsoft/fastcontext`, hoje indisponível publicamente): um subagent dedicado a explorar um repositório de código e devolver só o trecho relevante (arquivo + intervalo de linhas) para o agente principal, em vez de deixar o agente principal gastar contexto fazendo grep/glob/leitura de arquivo diretamente.

Referência de contexto: `transcricao-video-fastcontext.md` (transcrição de vídeo explicando o projeto original) e `docs/ai/reference-implementation-fastcontext.md` (discovery de uma implementação de referência em Python, clonada em `/mnt/backup/github/fastContextMicrosoft`, fora deste repo).

## Ideia central

- Dois agentes separados: um **explorador** (busca) e um **resolvedor** (edita/decide).
- O explorador só tem 3 ferramentas: leitura de arquivo (com número de linha), glob e grep/regex. Não executa nada.
- O explorador roda em contexto isolado e usa um modelo mais barato (Haiku) — quem resolve a tarefa usa o modelo mais caro.
- Saída do explorador: bloco enxuto de evidência (arquivo + linhas), nunca o histórico de navegação.
- Ativação via `.claude/rules/exploration.md` — explícita (citar o nome no prompt) é mais confiável que implícita.

## Escopo revisado — só o que está garantido por evidência real

Depois de 7 fases + validação de baseline + achados negativos corrigidos, a proposta de valor foi **reduzida deliberadamente** ao que os testes realmente sustentam. Ver `docs/ai/risks-and-gaps.md` e `docs/ai/eval/baseline-results-2026-07-06.md` para o detalhe de cada item abaixo.

**Garantido (testado, reproduzido):**
- Redução de **custo em dólar**, não de contagem de tokens — Haiku custa uma fração do modelo principal por token. Contagem de tokens vs. explorar direto é estruturalmente inverificável nesta plataforma (Agent tool não expõe usage comparável); não afirmamos "menos tokens", só "tokens mais baratos" quando a delegação acontece.
- Higiene de contexto do agente principal: histórico de busca (tentativas erradas, convenções de nome descartadas) fica isolado no subagent e nunca entra no contexto do modelo caro.
- Zero over-triggering nas queries triviais testadas (baseline Q5/Q6) — a regra de ativação não dispara para lookup já resolvido ou edição pura.
- Contrato de saída estruturado com citação verbatim, validado (`validate_citations.py`) contra todas as citações reais coletadas até agora.
- Corte real de tool calls via hook `PreToolUse` (Camada 2) — não depende só de instrução no prompt.
- Bloqueio de segredos (`.env`, `secrets/**`) testado com casos sintéticos positivos e negativos.
- Boa qualidade de resposta **para perguntas pontuais e fechadas** (localizar um símbolo, achar a definição de uma função, mapear 2-4 arquivos relacionados) — 3 de 4 casos do baseline, incluindo contexto além do gabarito.

**Não garantido — riscos conhecidos, sem mitigação na origem (usar com essas restrições):**
- **Calibração de confiança falha silenciosamente**: já ocorreu resposta `confidence="high"` sobre o repositório/arquivo errado. Defesa obrigatória: sempre ler ao menos uma citação antes de agir em cima dela (`.claude/rules/exploration.md`) — não confiar no `confidence` autorrelatado.
- **Perguntas amplas e abertas ("descreva todo o fluxo, citando cada arquivo") estouram o turno sem fechar `<final_answer>`** — reproduzido 3/3 vezes, não corrigido por ajuste de prompt. Não delegar perguntas desse formato; quebrar em perguntas pontuais menores (ver `exploration.md`).
- Robustez a ambiguidade de path/case **não é uma vantagem confiável** do `fast-context` sobre explorar direto — ambos os lados cometem esse erro (revisão do achado da rodada 2 após amostra maior).

## Status

**Fases 0-7 implementadas e validadas em uso real** (não só teoria/unit test — subagent real invocado repetidas vezes, incluindo achados negativos corrigidos no processo). Componentes principais:

- `.claude/agents/fast-context.md` (Haiku) e `.claude/agents/fast-context-deep.md` (Sonnet, escalonamento) — corpo sincronizado, só `model:` difere.
- `.claude/rules/exploration.md` — regra única de ativação, gates de auto-checagem, escalonamento (teto de 1 salto), defesa em profundidade, convenção de nomenclatura pro statusLine.
- `.claude/scripts/limit_turns_hook.py` — corte real de tool calls (chave `agent_id`, não `session_id`/`transcript_path` — esses vazam entre invocações na mesma sessão, bug real encontrado e corrigido).
- `.claude/scripts/block_secrets_hook.py` + `deny` em `settings.json` — bloqueio de `.env`/`secrets/**`.
- `.claude/scripts/statusline.py` / `subagent_statusline.py` — feedback visual (custo/tokens do dev + tokens ao vivo de cada subagent rodando).
- `docs/ai/eval/baseline-queries.md` + `baseline-results-2026-07-06.md` — baseline de validação end-to-end com gabarito manual.

**Achado mais importante do processo**: `confidence` autorrelatado pelo subagent não pega o próprio erro (numa query do baseline, respondeu com `confidence="high"` sobre o repositório errado, por confusão de case no path) — a defesa real é a regra de "ler ao menos uma citação antes de editar" em `exploration.md`, não a auto-avaliação do modelo.

Plano de estratégias de economia de contexto (referência histórica): ver `docs/ai/context-economy-strategies.md`.

Decisão de arquitetura (só Claude, sem infra externa, tudo nativo do Claude Code): ver `docs/ai/architecture-decision-native-subagent.md`.

Plano de implementação passo a passo, com checklist e achados de cada fase: ver `docs/ai/implementation-plan.md`. Pesquisa de feedback visual (statusLine/subagentStatusLine): ver `docs/ai/ui-feedback-statuslines.md`.

Riscos e lacunas identificados (15 no total, com solução ou status de mitigação): ver `docs/ai/risks-and-gaps.md`. Fatos confirmados sobre a plataforma (schema de agent, bug do `maxTurns`, payload de statusLine, proteção de segredos): ver `docs/ai/claude-code-capabilities-verified.md`. Histórico completo da decisão go/no-go, incluindo achados negativos (stall silencioso, vazamento de contador, erro de path) e como foram corrigidos: ver `docs/ai/go-no-go-analysis.md`.

## Regras

- Sem segredos/credenciais em nenhum arquivo commitado.
- `CLAUDE.local.md` e `.claude/settings.local.json` são pessoais — nunca commitar (ver `.gitignore`).
