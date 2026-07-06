# fastContext

Reimplementação do conceito **FastContext** (originalmente `microsoft/fastcontext`, hoje indisponível publicamente): um subagent/skill dedicado a explorar um repositório de código e devolver só o trecho relevante (arquivo + intervalo de linhas) para o agente principal, em vez de deixar o agente principal gastar tokens fazendo grep/glob/leitura de arquivo diretamente.

Referência de contexto: `transcricao-video-fastcontext.md` (transcrição de vídeo explicando o projeto original) e `docs/ai/reference-implementation-fastcontext.md` (discovery de uma implementação de referência em Python, clonada em `/mnt/backup/github/fastcontext`, fora deste repo).

## Ideia central

- Dois agentes separados: um **explorador** (busca) e um **resolvedor** (edita/decide).
- O explorador só tem 3 ferramentas: leitura de arquivo (com número de linha), glob e grep/regex. Não executa nada.
- O explorador roda em contexto isolado e pode usar um modelo mais barato/local — quem resolve a tarefa usa o modelo mais caro.
- Saída do explorador: bloco enxuto de evidência (arquivo + linhas), nunca o histórico de navegação.
- Ativação no Claude Code via skill — pode ser implícita, via slash command, ou explícita citando o nome no prompt (a explícita é a mais confiável).

## Status

Fase 0 (experimento mínimo) implementada: `.claude/agents/fast-context.md` (subagent enxuto, model Haiku) e `.claude/scripts/validate_citations.py` (validação determinística de citações). Ainda **não validado em uso real** — falta rodar as queries de comparação contra o agente `Explore` nativo antes de decidir se vale investir nas Fases 2-7. Ver `docs/ai/go-no-go-analysis.md`.

Plano de estratégias de economia de contexto a implementar: ver `docs/ai/context-economy-strategies.md`.

Decisão de arquitetura (só Claude, sem infra externa, tudo nativo do Claude Code): ver `docs/ai/architecture-decision-native-subagent.md`.

Plano de implementação passo a passo (fases 1-7, com checklist): ver `docs/ai/implementation-plan.md`. Pesquisa de feedback visual (statusLine/subagentStatusLine): ver `docs/ai/ui-feedback-statuslines.md`.

Riscos e lacunas identificados (15 no total, com solução ou status de mitigação): ver `docs/ai/risks-and-gaps.md`. Fatos confirmados sobre a plataforma (schema de agent, bug do `maxTurns`, payload de statusLine, proteção de segredos): ver `docs/ai/claude-code-capabilities-verified.md`. Análise de custo/benefício e decisão de rodar um experimento mínimo antes do plano completo: ver `docs/ai/go-no-go-analysis.md`.

## Regras

- Sem segredos/credenciais em nenhum arquivo commitado.
- `CLAUDE.local.md` e `.claude/settings.local.json` são pessoais — nunca commitar (ver `.gitignore`).
