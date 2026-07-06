# Plano de implementação — fastContext (subagent nativo do Claude Code)

Consolida o discovery feito em `docs/ai/*.md` num plano executável, passo a passo. Escopo fechado: **100% nativo do Claude Code, só modelos Claude, sem processo/infra externa** (ver `architecture-decision-native-subagent.md`).

Docs de referência para cada fase:
- `context-economy-strategies.md` — as 6 estratégias de economia de contexto
- `reference-implementation-fastcontext.md` — discovery da implementação Python de referência
- `architecture-decision-native-subagent.md` — decisão e comparativo
- `ui-feedback-statuslines.md` — pesquisa de feedback visual
- `risks-and-gaps.md` — revisão crítica que motivou os ajustes marcados como "(ajustado)" abaixo

## Fase 1 — Subagent explorador ("discovery")

**Objetivo:** núcleo do projeto — estratégias #4 (isolamento de contexto) + #1 (toggle de modelo).

- [ ] Criar `.claude/agents/fast-context.md` com frontmatter:
  - `name: fast-context`
  - `description`: instrução pra ativação proativa ("use antes de explorar múltiplos arquivos ou seguir lógica entre módulos")
  - `model: haiku` (valor padrão)
  - `tools: Read, Grep, Glob` (sem Edit/Write/Bash — restrição estrutural, não por convenção)
- [ ] Escrever o system prompt do agent (corpo do arquivo, abaixo do frontmatter), adaptando o `system.md` da referência:
  - papel: especialista em exploração read-only
  - guidelines de busca (largo → estreito, múltiplas estratégias de nome, checar convenções diferentes)
  - nunca devolver o histórico de navegação, só o resultado final
- [ ] **(solução robusta — risco #3)** Contrato de saída estruturado, não texto livre:
  ```
  <final_answer confidence="high|medium|low" strategies_used="glob,grep,read" files_found="N">
  /caminho/arquivo.py:10-15
  > trecho verbatim das linhas citadas (ver próximo item)
  </final_answer>
  ```
  Definir no próprio system prompt os critérios de `confidence`: `high` = achou a definição exata do símbolo perguntado; `medium` = achou arquivos relacionados mas sem match exato ou via padrão amplo; `low` = poucos/nenhum match forte, baseado em suposição de convenção de nome.
- [ ] **(solução robusta — risco #2)** Grounding por citação literal: exigir um trecho verbatim do arquivo junto de cada `arquivo:linha` (não só o range) — força o subagent a ter lido aquele trecho de fato. Complementar: instruir "antes do `<final_answer>`, faça uma chamada de Read em cada citação pra confirmar que existe e bate com o esperado" (equivalente ao `os.path.isfile` da referência, via tool call real).
- [ ] **(solução robusta — risco #4, camada 1)** Auto-contagem de turnos no próprio raciocínio: "declare seu turno atual (Turno N/8); ao chegar no 8, você DEVE emitir `<final_answer>` mesmo que incompleto, com `confidence=\"low\"`".
- [ ] Testar com 2-3 queries reais num repositório (ex: "onde fica a lógica de autenticação?") e conferir se o formato estruturado, o grounding e a auto-contagem funcionam como esperado.

## Fase 2 — Ativação explícita e regras

**Objetivo:** garantir que o subagent seja realmente usado (o vídeo de referência mostrou que ativação implícita de skill não é confiável).

- [ ] **(solução robusta — risco #1)** Adicionar regra em `CLAUDE.md` (ou `.claude/rules/exploration.md`) com critério **simétrico**, com exemplos concretos dos dois lados (few-shot ancora melhor que regra abstrata):
  - **Usar**: localização desconhecida, lógica atravessando >2 arquivos/módulos, "como funciona X", análise de impacto ("o que quebra se eu mudar Y").
  - **Não usar**: arquivo já lido nesta sessão, grep único num arquivo já conhecido, edição pura sem exploração, símbolo exato já visível no contexto atual.
- [ ] **(solução robusta — risco #1)** Gate de auto-checagem obrigatório antes de delegar: instruir o agente principal a se perguntar explicitamente "eu já sei o arquivo:linha exato pra isso?" antes de invocar `fast-context` — se sim, pula a delegação.
- [ ] Defesa em profundidade pro risco #2: regra pra o agente principal sempre fazer uma leitura rápida de pelo menos uma citação recebida antes de editar em cima dela.

## Fase 3 — Escalonamento de modelo

**Objetivo:** reforçar a estratégia #1 sem travar num único modelo fixo.

- [ ] Definir uma segunda variante do agent (ex: `fast-context-deep` com `model: sonnet`, mesmo tools/system prompt) para repositórios grandes/complexos.
- [ ] **(solução robusta — risco #3)** Regra de escalonamento baseada no formato estruturado da Fase 1: escalona pra `fast-context-deep` quando `confidence != "high"` **ou** `files_found` parecer baixo pro escopo da pergunta — não só quando `<final_answer>` vier vazio, que é o caso mais fácil de detectar mas não o mais perigoso.
- [ ] Calibração ao longo do tempo: a Fase 7 registra `confidence` reportado vs. corretude real (contra o gabarito manual) — transforma "confiança" de vibe em sinal calibrado.

## Fase 4 — Limite de turnos e caps de saída

**Objetivo:** estratégia #6 (cap de tamanho de saída) e prevenção de loop de busca gastando tokens à toa.

- [ ] No system prompt do subagent, instruir explicitamente: preferir `head_limit`/ranges pequenos nas ferramentas nativas de Grep/Read, nunca despejar arquivo inteiro quando uma faixa resolve.
- [ ] Camada 1 (auto-contagem de turnos) já entra na Fase 1 — aqui só formalizar o número de turnos padrão (ex: 8) na descrição do agent.
- [ ] **(solução robusta — risco #4, camada 2, condicional)** Investigar via captura de debug (mesmo método usado pro statusLine) se o payload de um hook `PreToolUse` identifica *qual agente* (main vs. subagent) disparou a tool call. Se sim, implementar um hook `PreToolUse` em `Read|Grep|Glob` escopado ao `fast-context` que conta invocações e nega (`permissionDecision: "deny"`) passado o limite, como backstop real além da auto-contagem. **Só implementar essa camada se a Fase 7 mostrar que a Camada 1 (soft) não é confiável na prática** — não implementar preventivamente.

## Fase 5 — Prompt caching por estrutura

**Objetivo:** estratégia #2, ativar o cache automático do Claude Code por design.

- [ ] Manter o system prompt do `fast-context` e as regras de ativação em arquivos estáveis, que não são reescritos a cada sessão.
- [ ] Evitar qualquer mecanismo que regenere esses arquivos dinamicamente por sessão (quebraria o cache hit).
- [ ] **(solução robusta — risco #5)** Não afirmar o que não foi medido: tratar o ganho de cache no subagent explorador como hipótese até a Fase 7 medir de verdade (invocar `fast-context` duas vezes na mesma sessão, comparar custo de input reportado). Se não houver economia observável, corrigir esta fase pra "não atrapalha o cache do agente principal, mas não garante economia no subagent" em vez de "ativa cache por design".

## Fase 6 — Feedback visual (statusLine + subagentStatusLine)

**Objetivo:** visibilidade de qual agente está ativo e quantos tokens cada um gastou, sem custo de token adicional.

- [x] Pesquisar viabilidade (`ui-feedback-statuslines.md`) — confirmado: multi-linha suportado, posição só rodapé, `subagentStatusLine` é o campo certo para dados por-subagent.
- [ ] **Pendente**: reabrir `/hooks` (ou reiniciar) para forçar reload do `settings.local.json` de debug e capturar o payload JSON real recebido via stdin por `statusLine` e `subagentStatusLine`.
- [ ] Com o payload confirmado, escrever o script final:
  - `statusLine`: barra "FastCode Activate" + linha do modelo **dev** (nome, effort, tokens/custo do turno)
  - `subagentStatusLine`: linha do modelo **discovery** (nome, effort, tokens da chamada), visível no painel de agentes enquanto o `fast-context` roda
- [ ] Remover o capturador de debug de `settings.local.json` e substituir pelo script definitivo.
- [ ] Validar visualmente rodando uma query que dispare o `fast-context` e conferir se as duas linhas aparecem corretamente.

## Fase 7 — Validação end-to-end

**Objetivo:** confirmar o ganho de tokens/tempo prometido pela estratégia, mirror do teste que o vídeo de referência fez.

- [ ] Escolher um repositório de teste com múltiplos arquivos/módulos.
- [ ] **(solução robusta — risco #6)** Criar `docs/ai/eval/baseline-queries.md` com 5-6 queries fixas contra esse repositório, cada uma com **gabarito manual** (lista de arquivo:linha conferida à mão, uma vez, com calma). Misturar propositalmente:
  - queries que **deveriam** disparar o `fast-context` (multi-arquivo/módulo)
  - queries que **não deveriam** disparar (triviais) — valida o risco #1 (over-triggering) junto
- [ ] Rodar cada query duas vezes: uma pedindo explicitamente para usar `fast-context`, outra sem (deixando o agente principal explorar direto com Read/Grep/Glob nativos).
- [ ] Registrar por rodada, numa tabela datada no mesmo arquivo: tokens (main + subagent), tempo, precisão/recall contra o gabarito, `confidence` reportado vs. corretude real (risco #3), se o limite de turnos segurou (risco #4), se a 2ª chamada mostrou cache hit (risco #5), se queries triviais dispararam delegação indevida (risco #1).
- [ ] Essa tabela vira o baseline pra qualquer ajuste futuro no system prompt do subagent ser avaliado como melhora ou piora de forma objetiva.

## Fora de escopo (adiado — ver `context-economy-strategies.md`)

- Estratégia #3 (repo map estático via tree-sitter) — exige índice mantido fora do fluxo de conversa.
- Estratégia #5 (retrieve-then-load com embeddings) — exige vector store; grep/glob já cobre o papel de "retrieve" aqui.
