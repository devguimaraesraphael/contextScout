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

**Atualização (pesquisa externa, ver `claude-code-capabilities-verified.md`)**: pesquisa em calibração de LLM confirma que confiança verbalizada tem viés estrutural de excesso de confiança e não pode ser lida como probabilidade — mas é válida como **sinal de ranking** (que é o uso que fazemos: decidir escalar ou não, não estimar uma probabilidade exata). Mitigação barata sem precisar de ensemble/RL: quando o subagent for reportar `confidence` abaixo de `high`, forçar uma segunda passada de auto-crítica antes de finalizar (técnica tipo reflection/UAR). Isso reduz o problema, não o elimina — ver risco #8 abaixo.

## 4. Limite de turnos e caps de saída são só instrução, sem enforcement de código

Diferente do `--max-turns` da CLI Python (corte real no loop), no subagent nativo isso é só um pedido no system prompt — o modelo pode não obedecer, do mesmo jeito que a ativação implícita de skill "não é garantida". É o mesmo tipo de risco estrutural, aplicado agora ao limite de turnos.

**Correção**: aceitar essa limitação (não há campo de frontmatter pra isso hoje), mas ser explícito no system prompt sobre o custo de continuar buscando sem convergir, e revisar na Fase 7 se o comportamento observado bate com o esperado.

**Solução robusta** — duas camadas:
- **Camada 1 (sempre)**: auto-contagem no próprio raciocínio do subagent — "declare seu turno atual (Turno N/8); ao chegar no 8, você DEVE emitir `<final_answer>` mesmo que incompleto, com `confidence="low"`". Soft, mas combinado com o formato estruturado do risco #3 pelo menos produz um sinal honesto de "parei sem terminar" em vez de silenciosamente continuar.
- **Camada 2 (backstop real, a verificar antes de implementar)**: Claude Code tem hooks `PreToolUse` que **bloqueiam de verdade** uma tool call (`hookSpecificOutput.permissionDecision: "deny"`), diferente de pedir no system prompt. Um hook em `Read|Grep|Glob` poderia contar invocações num contador temporário e, passado o limite, negar com "limite de turnos atingido, finalize agora". Pré-requisito a confirmar: se o payload do hook identifica *qual agente* (main vs. subagent) disparou a chamada — senão o contador bloquearia também o agente principal usando essas mesmas ferramentas. Verificável com o mesmo método de captura de debug usado pro statusLine.
- Recomendação: implementar a Camada 1 já na Fase 1; só investir na Camada 2 se a Fase 7 mostrar que a auto-contagem não é confiável na prática.

**Atualização (pesquisa externa, ver `claude-code-capabilities-verified.md`)**: existe de fato um campo nativo `maxTurns` no frontmatter de subagent — mas a [issue #41143](https://github.com/anthropics/claude-code/issues/41143) no repositório oficial confirma que **não é enforced na prática** (agent com `maxTurns: 10` rodou 72+ turnos). Configurar o campo mesmo assim (grátis, pode ser corrigido numa versão futura), mas continuar tratando a auto-contagem comportamental (Camada 1) como o mecanismo real, não o `maxTurns`. Sobre a Camada 2: também descobri que `hooks` pode ser definido **por-agent** direto no frontmatter do `fast-context.md` — isso resolve o pré-requisito de identificação (não precisa mais inspecionar o payload pra saber "qual agente disparou", porque o hook já vive escopado dentro da definição do subagent).

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

## 7. Grounding por citação literal não garante correção semântica

Exigir um trecho verbatim (risco #2) prova que o subagent leu o arquivo de verdade — mas não prova que ele interpretou certo o que aquele trecho faz, ou que escolheu o trecho realmente relevante pra pergunta, não só um trecho tecnicamente correto que satisfaz o formato.

**Status: sem solução completa.** Mitigação parcial: exigir também uma frase curta conectando o trecho à pergunta ("este trecho resolve X porque Y") — não elimina o problema, mas força uma justificativa explícita que pode ser auditada pelo agente principal ou por revisão humana.

## 8. Confiança autorrelatada não tem calibração externa

Mesmo com o formato estruturado do risco #3, nada impede o subagent de sempre reportar `confidence="high"` — viés de excesso de confiança é um padrão documentado em LLMs (ver `claude-code-capabilities-verified.md`), não um bug específico deste projeto.

**Status: mitigado, não resolvido.** A técnica de reflection (forçar segunda passada de auto-crítica quando reportar não-`high`) reduz o problema. Resolução completa exigiria ensemble de múltiplos modelos ou RL de calibração — fora de escopo (custo/infra incompatível com "100% nativo, sem infra externa").

## 9. Sem teto para o escalonamento entre fast-context e fast-context-deep

Se `fast-context-deep` (Sonnet) também voltar com confiança baixa/média, o plano original não definia um limite — risco de ping-pong entre os dois agents gastando mais tokens do que se tivesse ido direto pro modelo forte.

**Status: mitigável por regra simples.** Limitar a 1 salto: Haiku → Sonnet uma vez. Se o Sonnet também não voltar com `confidence="high"`, parar e devolver pro agente principal com aviso explícito de baixa confiança, sem re-escalonar de novo.

## 10. Duplicação de system prompt entre dois arquivos de agent

`fast-context.md` e `fast-context-deep.md` compartilham o mesmo corpo de instruções, diferindo só no `model:`. Qualquer ajuste futuro no system prompt precisa ser replicado manualmente nos dois — risco real de divergência silenciosa.

**Status: mitigado por processo, não eliminado.** Não há mecanismo de import entre arquivos de agent no Claude Code. Mitigação: cabeçalho de aviso em ambos os arquivos ("manter corpo idêntico ao outro, exceto `model:`") e checagem de sincronia como item de checklist na Fase 7.

## 11. Amostra do harness de avaliação é pequena e de um repositório só

5-6 queries contra um único repositório não generaliza pra outros projetos, linguagens ou convenções de nome. O próprio gabarito manual é feito por nós olhando o repo uma vez — pode estar incompleto sem a gente perceber.

**Status: aceito como limitação, não resolvido.** Documentar o harness como "smoke test" de sanidade, não como prova de generalização. Expandir a amostra é trabalho futuro, fora do escopo da Fase 7 inicial.

## 12. Diretórios ruidosos no grep (`node_modules`, `dist`, `.venv`) — RESOLVIDO

**Status: resolvido por padrão, sem trabalho extra.** O Grep do Claude Code é baseado em ripgrep, que respeita `.gitignore` automaticamente (ver `claude-code-capabilities-verified.md`). Resta só instruir exclusão explícita de código vendorizado/gerado que tenha sido commitado (não gitignored).

## 13. Vazamento de segredos pro subagent (`.env`, credenciais) — RESOLVIDO (solução conhecida)

**Status: solução documentada e verificada, falta só implementar.** Hook `PreToolUse` em `Read|Edit|Write|Bash` que nega (`exit code 2`) quando o path bate com `.env`/`secrets/**`, complementado por uma regra `deny` determinística em `settings.json`. Ver `claude-code-capabilities-verified.md` para os detalhes e fontes. Deve ser aplicado em `settings.json` (protege agente principal e `fast-context` ao mesmo tempo).

## 14. Sem kill-switch documentado

Se a Fase 7 mostrar que o `fast-context` piora os resultados, não havia um jeito único e limpo de desligar tudo sem deixar referência quebrada espalhada (ex: regra no `CLAUDE.md` mencionando um agent que foi removido).

**Status: mitigável por organização de arquivos.** Concentrar toda referência ao `fast-context` numa única regra dedicada (`.claude/rules/exploration.md`), nunca espalhada direto no `CLAUDE.md`. Desligar vira "apagar/renomear 2 arquivos" (a regra + os agents), sem procurar referências soltas.

## 15. Re-disparo de delegação em perguntas de follow-up

Se o usuário pergunta algo que já foi respondido por uma citação anterior na mesma sessão, o gate de auto-checagem do risco #1 deveria pegar isso, mas nunca foi pensado especificamente pra esse cenário.

**Status: mitigável, ainda não testado.** Estender o gate de auto-checagem com "eu já respondi isso nesta conversa?", além de "eu já sei o arquivo:linha exato?". Incluir um caso de teste de follow-up no harness da Fase 7 (risco #6) pra validar na prática.
