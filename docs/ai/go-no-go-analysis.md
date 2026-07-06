# Go/no-go: vale a pena implementar o plano completo?

Análise crítica feita antes de investir nas Fases 2-7. Conclusão: **não construir o sistema completo especulativamente** — rodar um experimento mínimo primeiro (ver `implementation-plan.md`, Fase 0).

## Achado que muda a conta: o Claude Code já tem um agente `Explore` nativo

Este ambiente já oferece um subagent read-only pronto pra localizar código ("fast read-only search agent for locating code", com granularidade quick/medium/very thorough). Boa parte do "core" que estávamos planejando construir do zero — subagent isolado, read-only, focado em achar código — **já existe de graça**, sem os riscos documentados em `risks-and-gaps.md`. O diferencial real do nosso `fast-context` sobre o `Explore` nativo é estreito: forçar roteamento pra Haiku (controle de custo) + contrato de saída estruturado com `confidence` pra escalonamento calibrado.

## A vantagem de precisão do paper não é gratuita

O ganho de 60,3% de tokens / +5,5 de score reportado pelo paper do FastContext é atribuído ao **modelo treinado via RL** (`FastContext-1.0-4B-RL`), não à arquitetura de delegação isolada. O próprio paper diz que modelos pequenos genéricos (sem esse treino) recuperam arquivos/símbolos com menos precisão — e é exatamente essa configuração (modelo genérico, Haiku) que estamos usando. Expectativa realista: ganho de tokens sim (delegação + modelo mais barato), mas não necessariamente o ganho de precisão/score do paper.

## Tabela de riscos sem solução completa (recapitulada)

| # | Risco | Probabilidade | Impacto se ocorrer | Severidade residual |
|---|---|---|---|---|
| 1 | `maxTurns` não é enforced (bug confirmado, issue #41143) | Alta | Explorador roda além do razoável | Média |
| 2 | Confiança autorrelatada não calibrada | Alta | Escalonamento decide errado | Média-alta |
| 3 | Grounding não garante correção semântica | Média-alta | Edição com base em contexto tecnicamente verificado mas semanticamente errado — falha silenciosa | **Alta** |
| 4 | Teto de escalonamento/kill-switch dependem de obediência do modelo | Média | Ping-pong de escalonamento, dificuldade de desligar | Baixa-média |
| 5 | Duplicação entre `fast-context.md`/`fast-context-deep.md` | Média | Os dois agents divergem sem ninguém notar | Baixa-média |
| 6 | Amostra do harness pequena/um repo só | Certa | Baseline não generaliza | Média |
| 7 | Payload do `subagentStatusLine` não confirmado | Certa até abrir `/hooks` | Fase 6 trava (só cosmético) | Baixa |
| 8 | Re-disparo em follow-up não testado | Média | Delegação desnecessária | Baixa |

## O que o projeto Python original (Cirius1792/fastcontext) resolve — e o que não

| Risco nosso | Original resolve? | Por quê |
|---|---|---|
| #1 Limite de turnos | **Sim, de verdade** | `--max-turns` é corte real no loop Python, não instrução de prompt |
| #2/existência de citação | **Sim, parcialmente** | `os.path.isfile()` valida existência antes de devolver — mas só existência, não relevância |
| #3 Correção semântica | **Não** | Mesma lacuna que a nossa — validação de existência não checa se o trecho responde a pergunta |
| #4/#9 Confiança/escalonamento | **Não existe no original** | Roda um único modelo fixo por execução; nunca tentaram construir escalonamento |
| #10 Duplicação de agents | Não se aplica | É uma única base de código Python, não dois arquivos de agent |
| #13 Vazamento de segredos | **Não** | Só valida path dentro do `work_dir` (path traversal), nenhuma exclusão de `.env`/`secrets/**` |
| Precisão da busca | Sim, mas depende do modelo treinado (`FastContext-1.0-4B-RL`) servido via Ollama — infra local que este projeto decidiu não ter. O suporte a Claude no original é código morto (`llm_api.py` nunca commitado). |

**Conclusão**: portar o projeto Python não compraria a vantagem de precisão sem também assumir a infra rejeitada (servir modelo treinado localmente). As duas ideias dele que valem a pena roubar — validação de existência de citação e corte real de turnos — são portáveis pro nosso design nativo sem precisar do resto.

## Decisão: como roubar as ideias sem violar a arquitetura nativa

- **Validação de citação**: implementada como script determinístico (`validate_citations.py`), rodado pelo **agente principal** (que já tem Bash) depois de receber o `<final_answer>` do `fast-context` — não pelo `fast-context` em si, pra não dar acesso a Bash ao explorador e preservar a restrição estrutural de tools (`Read`/`Grep`/`Glob` só).
- **Corte de turnos**: mantido como auto-contagem comportamental (Camada 1) por agora. O contador via hook (Camada 2) fica pra depois, condicional ao resultado do experimento — se virasse um script, seria invocado pelo próprio hook `PreToolUse`, não pelo `fast-context`.

## Recomendação final

Rodar a **Fase 0 (experimento mínimo)** antes de qualquer coisa das Fases 2-7: `fast-context.md` enxuto (Fase 1 sem escalonamento) + `validate_citations.py`, comparado lado a lado com o agente `Explore` nativo e com o agente principal buscando direto. Só investir nas fases seguintes (escalonamento, hooks, statusline) se o experimento mostrar ganho real de tokens/qualidade sobre essas duas alternativas mais simples.

## Resultados da rodada 1 (via proxy — subagent nativo ainda não registrável na sessão)

**Limitação de setup descoberta**: subagents de projeto (`.claude/agents/*.md`) não são carregados dinamicamente durante uma sessão em andamento — o `fast-context` só aparece como `subagent_type` numa sessão nova do Claude Code, depois de reiniciar. Essa rodada usou um **proxy**: agente `general-purpose` com `model: haiku` e o mesmo system prompt do `fast-context.md` injetado como instrução. Isso aproxima o comportamento mas não testa o `maxTurns`/tool-allowlist reais.

Repositório de teste: o próprio clone do projeto Python original (`/mnt/backup/github/fastcontext`), só leitura.

| Query | Proxy fast-context (Haiku) | Explore nativo |
|---|---|---|
| 1. Carregamento do system prompt + templating | `confidence="high"`, 3 arquivos, citações corretas. 23.107 tokens, 8 tool calls, 41,5s | Resposta correta e mais rica (incluiu nuance sobre o `fast-context.md` não usar templating). **Sem stats de token/tempo expostos pelo tooling.** |
| 2. Validação de path do Grep | `confidence="high"`, 2 arquivos, citações corretas. 33.501 tokens, 14 tool calls, 45,3s | Resposta correta, mais detalhada (explicou o mecanismo de resolução de path passo a passo). Sem stats expostos. |
| 3. Trace do fluxo de tool call | `confidence="high"`, 5 arquivos, trace completo e correto. 38.871 tokens, **18 tool calls**, 86s | Resposta correta, trace igualmente completo com numeração de linha. Sem stats expostos. |

### Achados

1. **Qualidade: sem alucinação em nenhum dos dois lados.** Todas as citações do proxy Haiku foram conferidas contra o código real e batem (arquivo, linha, conteúdo). O contrato estruturado (`confidence`/`files_found`/grounding verbatim) funcionou como esperado — o Haiku seguiu o formato corretamente nas 3 vezes.
2. **Não foi possível comparar tokens de forma direta.** O `Explore` nativo não expõe `subagent_tokens`/`duration_ms` no formato que o `general-purpose` expõe — não dá pra afirmar "economizamos X tokens" com os dados desta rodada. Isso é uma limitação do experimento, não uma conclusão sobre custo.
3. **O proxy excedeu o orçamento de turnos pretendido.** A query mais complexa (trace de fluxo) usou 18 tool calls — mais que o dobro do `maxTurns: 8` real do `fast-context.md`. Como o proxy não tem esse campo configurado (é um `general-purpose` genérico), isso não testa se o limite real seguraria — mas é um sinal de alerta: essa classe de pergunta pode ser naturalmente mais cara do que o orçamento de 8 turnos permite, e merece atenção quando o subagent real for testado.
4. **`Explore` produziu respostas mais ricas/com mais nuance** nas 3 queries (cross-referenciou nossa própria documentação, explicou mais passo a passo) — provavelmente porque herda o modelo da sessão principal (mais forte que Haiku), não por ser estruturalmente melhor.

### Veredito desta rodada: inconclusivo, não é um go nem um no-go ainda

O sinal de qualidade é bom (zero alucinação, formato seguido corretamente), mas a pergunta central do projeto — "economiza tokens de verdade comparado ao `Explore` nativo?" — **não foi respondida** por limitação de instrumentação, e o teste não usou o subagent real (só um proxy). Próximo passo genuíno: reiniciar a sessão do Claude Code, invocar `fast-context` pelo nome de verdade, e usar `/cost` antes/depois de cada chamada como métrica de tokens (já que o usage por-subagent não é exposto de forma uniforme entre tipos de agent).
