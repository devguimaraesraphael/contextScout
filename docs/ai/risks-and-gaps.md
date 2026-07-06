# Riscos e lacunas identificados antes da implementação

Revisão crítica do plano em `implementation-plan.md`, feita antes de codificar a Fase 1. Cada item aqui já foi incorporado como ajuste nas fases correspondentes do plano — este documento existe para não perder o "porquê" da mudança.

## 1. Ativação explícita "sempre" pode aumentar tokens, não diminuir

A Fase 2 original dizia "sempre invoque o fast-context antes de explorar múltiplos arquivos". Isso resolve o problema de ativação implícita não confiável, mas cria o problema oposto: toda chamada de subagent tem overhead fixo (system prompt do explorador, schema de 3 tools, ida-e-volta, resumo). Para buscas triviais — grep de uma classe conhecida, arquivo já identificado, 2-3 arquivos óbvios — delegar é **mais caro** que o agente principal buscar direto.

**Correção**: a Fase 2 precisa de um critério explícito de "quando NÃO usar" (mirror do `SKILL.md` da implementação de referência), não uma regra cega de "sempre".

**Solução robusta**:
- Critério simétrico com exemplos concretos (few-shot ancora melhor que regra abstrata): **usar** quando localização é desconhecida, lógica atravessa >2 arquivos/módulos, "como funciona X", análise de impacto; **não usar** quando arquivo já foi lido nesta sessão, grep único num arquivo já conhecido, edição pura sem exploração, símbolo exato já visível no contexto atual.
- Gate de auto-checagem obrigatório: instruir o agente principal a se perguntar explicitamente "eu já sei o arquivo:linha exato pra isso?" antes de invocar — se sim, pula a delegação. Vira passo de raciocínio obrigatório, não sugestão solta.
- Fechamento com medição real: o harness da Fase 7 (ver risco #6) inclui queries triviais de propósito — se o agente delegar nelas mesmo assim, isso aparece como regressão mensurável em vez de suspeita.

## 2. Sem validação das citações — risco de qualidade silenciosa

A implementação Python de referência valida cada `arquivo:linha` contra o filesystem (`os.path.isfile`) antes de devolver, descartando citações inválidas. Um subagent nativo em Haiku pode alucinar um caminho plausível e devolver com total confiança — o agente principal não tem como saber que aquilo não foi checado. É uma falha silenciosa: a resposta parece completa e precisa, mas pode estar errada.

**Correção**: adicionar um passo de verificação leve antes do subagent devolver o `<final_answer>` — idealmente instruído no próprio system prompt (reconfirmar cada citação com uma leitura rápida antes de finalizar).

**Solução robusta** — duas camadas independentes, porque "por favor confira" sozinho é frágil:
- **Grounding por citação literal**: o contrato de saída exige um trecho verbatim do arquivo junto de cada `arquivo:linha`, não só o range. Pra citar texto real, o subagent é forçado a ter lido aquele trecho de fato — estruturalmente mais difícil de alucinar do que só proibir por instrução.
- **Verificação ativa antes de finalizar**: instruir "antes do `<final_answer>`, faça uma chamada de Read em cada citação pra confirmar que existe e bate com o que você acha que é" — o mesmo papel do `os.path.isfile` da referência, via tool call real em vez de código.
- **Defesa em profundidade no agente principal**: regra na Fase 2 pra sempre fazer uma leitura rápida de pelo menos uma citação antes de editar em cima dela — barato, porque normalmente ele leria mesmo antes de editar.

## 3. Escalonamento só cobre resultado vazio, não resultado incompleto

A Fase 3 original escalona pra Sonnet só quando o Haiku volta com `<final_answer>` vazio. O caso mais perigoso é o oposto: o explorador acha *algo plausível mas incompleto* (2 de 4 arquivos relevantes) e devolve com aparência de resposta completa — não há sinal para o agente principal desconfiar.

**Correção**: instruir o subagent a reportar um nível de confiança/completude junto com o `<final_answer>` (ex: "explorei X estratégias de busca, encontrei N arquivos, confiança alta/média/baixa"), e o agente principal escalona também em confiança baixa, não só em resultado vazio.

**Solução robusta**:
- Formato estruturado, não prosa solta — troca o `<final_answer>` livre por atributos parseáveis:
  ```
  <final_answer confidence="high|medium|low" strategies_used="glob,grep,read" files_found="N">
  ...
  </final_answer>
  ```
- Critério de confiança definido no system prompt, não deixado a critério do modelo: `high` = achou definição exata do símbolo perguntado; `medium` = achou arquivos relacionados mas sem match exato, ou precisou usar padrão amplo; `low` = poucos/nenhum match forte, baseado em convenção de nome por suposição.
- Regra de escalonamento (Fase 3): escalona pra `fast-context-deep` quando `confidence != high` **ou** `files_found` parecer baixo pro escopo da pergunta — não só quando vier vazio.
- Calibração ao longo do tempo: o harness da Fase 7 registra confiança reportada vs. corretude real (contra o gabarito manual) — transforma "confiança" de vibe em sinal calibrado, e expõe se o subagent está super ou subconfiante.

## 4. Limite de turnos e caps de saída são só instrução, sem enforcement de código

Diferente do `--max-turns` da CLI Python (corte real no loop), no subagent nativo isso é só um pedido no system prompt — o modelo pode não obedecer, do mesmo jeito que a ativação implícita de skill "não é garantida". É o mesmo tipo de risco estrutural, aplicado agora ao limite de turnos.

**Correção**: aceitar essa limitação (não há campo de frontmatter pra isso hoje), mas ser explícito no system prompt sobre o custo de continuar buscando sem convergir, e revisar na Fase 7 se o comportamento observado bate com o esperado.

**Solução robusta** — duas camadas:
- **Camada 1 (sempre)**: auto-contagem no próprio raciocínio do subagent — "declare seu turno atual (Turno N/8); ao chegar no 8, você DEVE emitir `<final_answer>` mesmo que incompleto, com `confidence="low"`". Soft, mas combinado com o formato estruturado do risco #3 pelo menos produz um sinal honesto de "parei sem terminar" em vez de silenciosamente continuar.
- **Camada 2 (backstop real, a verificar antes de implementar)**: Claude Code tem hooks `PreToolUse` que **bloqueiam de verdade** uma tool call (`hookSpecificOutput.permissionDecision: "deny"`), diferente de pedir no system prompt. Um hook em `Read|Grep|Glob` poderia contar invocações num contador temporário e, passado o limite, negar com "limite de turnos atingido, finalize agora". Pré-requisito a confirmar: se o payload do hook identifica *qual agente* (main vs. subagent) disparou a chamada — senão o contador bloquearia também o agente principal usando essas mesmas ferramentas. Verificável com o mesmo método de captura de debug usado pro statusLine.
- Recomendação: implementar a Camada 1 já na Fase 1; só investir na Camada 2 se a Fase 7 mostrar que a auto-contagem não é confiável na prática.

## 5. Prompt caching pode não se aplicar do jeito assumido

A Fase 5 original assume que o cache automático do Claude Code beneficia o system prompt do subagent explorador entre chamadas. Isso não foi verificado — cada chamada ao subagent é um contexto novo e isolado, e não há confirmação de que o Claude Code reaproveita cache de definição de agent entre invocações dentro da mesma sessão.

**Correção**: tratar como suposição não confirmada, não como ganho garantido. Validar na prática durante a Fase 7 (observar se chamadas repetidas ao mesmo subagent mostram custo de input menor).

**Solução robusta**: não dá pra "resolver" tecnicamente — não há alavanca de configuração pra forçar cache no subagent. A solução é não afirmar o que não foi medido:
- Na Fase 7, invocar `fast-context` duas vezes na mesma sessão com queries diferentes e comparar o custo de input reportado (`/cost` ou o resumo `Done (...)`) — se a 2ª chamada não mostrar economia visível, é sinal de que não há cache hit real no subagent.
- Se não houver economia observável, a Fase 5 deixa de alegar "ativa cache por design" e vira só "não atrapalha o cache do agente principal, mas não garante economia no subagent" — corrigir a documentação pelo resultado medido, não pela suposição.

## 6. Falta um baseline mensurável para a Fase 7

"Comparar com/sem fast-context" sem um conjunto fixo de perguntas contra um repositório fixo não é repetível — ajustes futuros no system prompt do subagent não têm como ser avaliados como melhora ou piora sem esse baseline.

**Correção**: definir de 5 a 6 queries de teste fixas contra um repositório real antes de considerar a Fase 1 "pronta", e salvar os resultados (tokens, tempo, se achou o arquivo certo) como referência para comparações futuras.

**Solução robusta** — harness leve de verdade, não comparação informal:
- Novo arquivo `docs/ai/eval/baseline-queries.md`: 5-6 queries fixas contra um repositório de teste fixo, cada uma com **gabarito manual** (lista de arquivo:linha conferida à mão, com calma, uma vez).
- Mistura proposital: queries que **deveriam** disparar o fast-context (multi-arquivo) e queries que **não deveriam** (triviais) — valida o risco #1 (over-triggering) ao mesmo tempo que valida a qualidade da busca.
- Métricas por rodada: tokens (main + subagent), tempo, precisão/recall contra o gabarito, `confidence` reportado vs. corretude real (calibração do risco #3), se o limite de turnos segurou (risco #4), se a 2ª chamada mostrou cache hit (risco #5).
- Tabela de resultados datada no mesmo arquivo — cada rodada futura (depois de mexer no system prompt) vira uma linha nova comparável, não uma impressão solta.
