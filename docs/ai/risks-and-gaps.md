# Riscos e lacunas identificados antes da implementação

Revisão crítica do plano em `implementation-plan.md`, feita antes de codificar a Fase 1. Cada item aqui já foi incorporado como ajuste nas fases correspondentes do plano — este documento existe para não perder o "porquê" da mudança.

## 1. Ativação explícita "sempre" pode aumentar tokens, não diminuir

A Fase 2 original dizia "sempre invoque o fast-context antes de explorar múltiplos arquivos". Isso resolve o problema de ativação implícita não confiável, mas cria o problema oposto: toda chamada de subagent tem overhead fixo (system prompt do explorador, schema de 3 tools, ida-e-volta, resumo). Para buscas triviais — grep de uma classe conhecida, arquivo já identificado, 2-3 arquivos óbvios — delegar é **mais caro** que o agente principal buscar direto.

**Correção**: a Fase 2 precisa de um critério explícito de "quando NÃO usar" (mirror do `SKILL.md` da implementação de referência), não uma regra cega de "sempre".

## 2. Sem validação das citações — risco de qualidade silenciosa

A implementação Python de referência valida cada `arquivo:linha` contra o filesystem (`os.path.isfile`) antes de devolver, descartando citações inválidas. Um subagent nativo em Haiku pode alucinar um caminho plausível e devolver com total confiança — o agente principal não tem como saber que aquilo não foi checado. É uma falha silenciosa: a resposta parece completa e precisa, mas pode estar errada.

**Correção**: adicionar um passo de verificação leve antes do subagent devolver o `<final_answer>` — idealmente instruído no próprio system prompt (reconfirmar cada citação com uma leitura rápida antes de finalizar).

## 3. Escalonamento só cobre resultado vazio, não resultado incompleto

A Fase 3 original escalona pra Sonnet só quando o Haiku volta com `<final_answer>` vazio. O caso mais perigoso é o oposto: o explorador acha *algo plausível mas incompleto* (2 de 4 arquivos relevantes) e devolve com aparência de resposta completa — não há sinal para o agente principal desconfiar.

**Correção**: instruir o subagent a reportar um nível de confiança/completude junto com o `<final_answer>` (ex: "explorei X estratégias de busca, encontrei N arquivos, confiança alta/média/baixa"), e o agente principal escalona também em confiança baixa, não só em resultado vazio.

## 4. Limite de turnos e caps de saída são só instrução, sem enforcement de código

Diferente do `--max-turns` da CLI Python (corte real no loop), no subagent nativo isso é só um pedido no system prompt — o modelo pode não obedecer, do mesmo jeito que a ativação implícita de skill "não é garantida". É o mesmo tipo de risco estrutural, aplicado agora ao limite de turnos.

**Correção**: aceitar essa limitação (não há campo de frontmatter pra isso hoje), mas ser explícito no system prompt sobre o custo de continuar buscando sem convergir, e revisar na Fase 7 se o comportamento observado bate com o esperado.

## 5. Prompt caching pode não se aplicar do jeito assumido

A Fase 5 original assume que o cache automático do Claude Code beneficia o system prompt do subagent explorador entre chamadas. Isso não foi verificado — cada chamada ao subagent é um contexto novo e isolado, e não há confirmação de que o Claude Code reaproveita cache de definição de agent entre invocações dentro da mesma sessão.

**Correção**: tratar como suposição não confirmada, não como ganho garantido. Validar na prática durante a Fase 7 (observar se chamadas repetidas ao mesmo subagent mostram custo de input menor).

## 6. Falta um baseline mensurável para a Fase 7

"Comparar com/sem fast-context" sem um conjunto fixo de perguntas contra um repositório fixo não é repetível — ajustes futuros no system prompt do subagent não têm como ser avaliados como melhora ou piora sem esse baseline.

**Correção**: definir de 5 a 6 queries de teste fixas contra um repositório real antes de considerar a Fase 1 "pronta", e salvar os resultados (tokens, tempo, se achou o arquivo certo) como referência para comparações futuras.
