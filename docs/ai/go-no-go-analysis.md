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

## Resultados da rodada 2 (subagent real, sessão reiniciada)

Sessão nova confirmou o `fast-context` registrado e invocável por nome (`subagent_type: fast-context`, distinto de `general-purpose`). Mesmo repositório de teste (`/mnt/backup/github/fastcontext`), mesmas 3 queries da rodada 1, agora lado a lado com o `Explore` nativo real (não proxy).

| Query | fast-context real (Haiku) | Explore nativo (real) |
|---|---|---|
| 1. Templating do system prompt | `confidence="high"`, 4 arquivos, citações corretas. **14.122 tokens, 8 tool calls, 26,6s** | **Resolveu o repositório errado** (respondeu sobre `/mnt/backup/github/fastContext`, este projeto, em vez do `fastcontext` de referência — confundiu maiúscula/minúscula). Resposta longa mas sobre o repo incorreto. Sem stats de token expostos. |
| 2. Validação de path do grep | Parou em "Turno 1/8" sem emitir `<final_answer>` apesar de 9 tool calls — precisou de um follow-up manual (`SendMessage`) pedindo pra finalizar. Depois do nudge: `confidence="high"`, 5 arquivos, citações corretas. **14.711 + 15.497 = 30.208 tokens somando as duas chamadas**, 9 tool calls, ~30s total | Com o path desambiguado no prompt, resolveu o repositório certo. `confidence` não reportado (não é o contrato do fast-context), resposta correta e completa, trace equivalente. Sem stats de token expostos. |
| 3. Trace do fluxo de tool call | `confidence="high"`, 7 arquivos, trace completo com auto-crítica no Turno 7/8 antes de finalizar. **18.920 tokens, 11 tool calls, 50s** | Resposta correta, trace igualmente completo, incluiu diagrama de sequência ASCII. Sem stats de token expostos. |

### Achados da rodada 2

1. **Confirmado: nenhuma alucinação do lado do `fast-context` real.** As citações (arquivo:linha:trecho) conferem com o código de fato nas 3 queries — o contrato estruturado seguiu funcionando com o subagent real, não só no proxy.
2. **Achado novo, negativo: o `fast-context` real trava silenciosamente sob turno baixo.** Na query 2, o subagent parou após o Turno 1 sem emitir `<final_answer>`, mesmo tendo feito 9 tool calls — comportamento que o proxy da rodada 1 nunca exibiu. Precisou de intervenção manual (mensagem via `SendMessage` pedindo explicitamente para finalizar) pra completar. Isso quase dobrou o custo de tokens dessa query (30.208 vs. ~14-19k das outras) e é exatamente o tipo de falha que a "auto-contagem de turnos" (Camada 1, comportamental) deveria prevenir e não previne de forma confiável — reforça o risco #4 (`risks-and-gaps.md`) com evidência real, não só teórica.
3. **Achado novo, sobre o `Explore`: sensível à ambiguidade de path.** Na query 1, sem desambiguação explícita no prompt, o `Explore` nativo resolveu para o diretório errado (`fastContext` em vez de `fastcontext`) e respondeu com confiança sobre o repositório errado, sem sinalizar a ambiguidade. O `fast-context` não cometeu esse erro nas mesmas condições. É uma vantagem real de robustez do nosso subagent, mas amostra de 1 caso — não generalizar sem repetir.
4. **A pergunta central continua sem resposta por limitação de instrumentação.** O `Explore` nativo não expõe tokens/duração em nenhuma das 3 queries, mesmo com o subagent real (não é uma limitação do proxy, é estrutural da ferramenta) — não há como comparar diretamente "tokens gastos por `fast-context`" vs. "tokens gastos por `Explore`" nesta plataforma, hoje. Essa limitação parece permanente, não contornável rodando mais queries.

### Veredito da rodada 2: ainda não é go — pende de decisão sobre o achado #2

O sinal de qualidade continua bom, e a robustez a ambiguidade de path é um ponto a favor do `fast-context`. Mas a rodada revelou uma falha real (stall silencioso, achado #2) que o plano original só tratava como risco teórico (#4), e a pergunta central (economia de tokens vs. `Explore`) continua **estruturalmente não respondível** nesta plataforma — não é falta de mais dados, é a ferramenta não expor a métrica. Duas decisões pendentes antes de ir para as Fases 2-7:
- **Sobre o achado #2**: vale a pena investir na Camada 2 do risco #4 (hook `PreToolUse` que corta de verdade após N tool calls, ver Fase 4 do `implementation-plan.md`) antes de escalar, já que a auto-contagem comportamental falhou uma vez em 3 tentativas reais.
- **Sobre a instrumentação**: aceitar que "economia de tokens vs. Explore" nunca será uma métrica objetiva nesta plataforma, e redefinir o critério de sucesso do projeto para algo medível (ex: robustez a ambiguidade, contrato de saída estruturado pra escalonamento) em vez de tokens comparados ao `Explore`.

## Ações tomadas após a rodada 2

**Camada 2 implementada** (`.claude/scripts/limit_turns_hook.py` + `hooks.PreToolUse` no frontmatter de `fast-context.md`): corte real de tool calls, não mais só comportamental. Conta invocações de `Read|Grep|Glob` por invocação de subagent (chave = `transcript_path` do payload do hook, único por execução, não o `session_id` que é compartilhado com a sessão principal), e nega (`permissionDecision: "deny"`) a partir da 11ª chamada, instruindo o modelo a emitir `<final_answer confidence="low">` imediatamente. Testado isoladamente (unit test com payload sintético, 12 chamadas): chamadas 1-10 passam em silêncio, 11ª e 12ª negam com a mensagem esperada. **Ainda não testado em invocação real do subagent nesta sessão** — subagents de projeto não recarregam frontmatter dinamicamente (mesma limitação de setup da rodada 1); validar na próxima sessão nova.

**Critério de sucesso do projeto redefinido**: "economia de tokens vs. `Explore` nativo" sai como métrica de decisão (inviável — plataforma não expõe usage do `Explore`). Critérios que ficam, porque foram de fato observados e são medíveis:
1. Zero alucinação nas citações (`validate_citations.py` como gate objetivo) — confirmado nas rodadas 1 e 2.
2. Corte de turnos real (não comportamental) — implementado acima, falta validar em sessão nova.
3. Robustez a ambiguidade de path/contexto — vantagem observada 1x sobre o `Explore`, amostra pequena, repetir antes de generalizar.
4. Contrato de saída estruturado (`confidence`) útil pra escalonamento — funcionou nas 6 chamadas reais até agora (proxy + subagent real).

Com isso, a decisão go/no-go das Fases 2-7 passa a depender de validar o hook numa sessão nova e, se ele segurar de verdade, o "go" fica justificado pelos critérios 1-4 acima — não pela hipótese original de economia de tokens, que fica formalmente descartada como métrica deste projeto.

## Validação do hook em sessão nova (rodada 3)

Sessão nova, invocação real do `fast-context` (não proxy, não unit test) com uma pergunta deliberadamente ampla (7 sub-perguntas sobre `/mnt/backup/github/fastcontext`) para forçar a passagem dos 10 tool calls.

Resultado: o subagent fez **11 tool calls** e parou — o arquivo de contador (`/tmp/fast-context-turns/<hash>.count`) confirma `11`, batendo exatamente com `tool_uses: 11` no usage retornado. O hook negou a 11ª chamada de ferramenta e o modelo emitiu `<final_answer confidence="low">` imediatamente, citando explicitamente "Atingi o limite de 10 tool calls" e listando quais das 7 sub-perguntas ficaram sem resposta — **sem precisar de nudge manual via `SendMessage`**, diferente do stall observado na rodada 2. As 2 citações que conseguiu confirmar (agent.py, agent_factory.py, system.md) são verbatim corretas.

### Achados da rodada 3

1. **Camada 2 (hook `PreToolUse`) funciona de verdade em invocação real, não só em unit test sintético.** Corte determinístico no tool call 11, independente do modelo "lembrar" de contar turnos.
2. **Resolve o achado #2 da rodada 2 (stall silencioso).** Com o corte real, o subagent não trava mais sem emitir `<final_answer>` — o hook força a finalização mesmo que o modelo ignore a auto-contagem comportamental.
3. **Confirma que subagents de projeto recarregam frontmatter numa sessão nova** (a limitação de "não recarrega no meio da sessão atual" só se aplicava à sessão onde o arquivo foi editado — comportamento esperado, não um bug adicional).
4. Efeito colateral aceitável: a resposta final ficou parcial (2/7 sub-perguntas), mas isso é o comportamento pretendido — `confidence="low"` sinaliza corretamente pro agente principal que precisa relançar a busca ou aceitar a resposta parcial.

### Veredito final: GO para as Fases 2-7, com critérios de sucesso redefinidos

As duas decisões pendentes da rodada 2 estão resolvidas:
- **Camada 2 validada em uso real** — corte de turnos agora é confiável, não só comportamental.
- **Critério de sucesso do projeto formalmente redefinido** (não é mais "economia de tokens vs. `Explore`", que é estruturalmente não medível nesta plataforma): zero alucinação de citação, corte real de turnos, robustez a ambiguidade de path, contrato de saída estruturado — os 4 critérios do fim da rodada 2, todos observados e confirmados em uso real até aqui.

Próximo passo: seguir para a Fase 2 do `implementation-plan.md` (escalonamento) com esses critérios como gate de qualidade em vez de comparação de tokens.

## Bug real encontrado durante a Fase 3 (rodada 4): contador do hook vazava entre invocações

Ao testar o escalonamento pra `fast-context-deep` na mesma sessão da rodada 3, uma segunda invocação do `fast-context` foi cortada já na 2ª tool call real — muito antes do limite de 10. Investigação: o arquivo de contador (`/tmp/fast-context-turns/<hash>.count`) que tinha ficado em `11` ao fim da rodada 3 continuou incrementando para `13` na nova chamada, em vez de começar do zero.

Causa raiz: `transcript_path` e `session_id`, os dois campos usados como chave de contagem no `limit_turns_hook.py`, **são o mesmo valor da sessão principal em toda chamada de subagent dentro da mesma sessão** — não são únicos por invocação como a documentação original (rodada 2) assumia. Confirmado empiricamente adicionando um hook de debug temporário em `settings.json` (removido depois) que logou o payload completo do `PreToolUse`: `session_id` e `transcript_path` bateram exatamente com os da sessão principal em 3 tool calls consecutivas de uma mesma invocação do subagent. O campo correto, que é de fato único por invocação, é `agent_id` — confere com o `agentId` que a ferramenta `Agent` devolve no resultado.

**Impacto real do bug**: qualquer sessão com mais de uma invocação do `fast-context` (uso normal, não um caso extremo) acumula contagem entre chamadas — cada chamada nova herda o "resto" da anterior, cortando cada vez mais cedo até eventualmente negar a primeira tool call de uma invocação nova. Isso teria silenciosamente degradado a Camada 2 em qualquer sessão real de uso, ao contrário do que a validação da rodada 3 (uma única invocação por sessão) conseguiu detectar.

**Correção**: `limit_turns_hook.py` agora usa `agent_id` como chave primária (com fallback pra `transcript_path`/`session_id` só se `agent_id` não vier no payload, o que não deveria acontecer em invocação de subagent real). Validado com teste sintético: duas invocações (`agent_id` diferente) compartilhando o mesmo `session_id`/`transcript_path` mantêm contadores isolados — 10 chamadas silenciosas cada, independente da outra.

### Lição pro processo

A rodada 3 validou o hook com **uma única invocação por sessão**, o que mascarou esse bug — reforça que "validar em sessão nova" não é suficiente por si só; é preciso testar múltiplas invocações do mesmo subagent na mesma sessão antes de considerar um mecanismo de estado (contador, cache, etc.) robusto.
