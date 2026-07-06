# Plano de implementação — fastContext (subagent nativo do Claude Code)

Consolida o discovery feito em `docs/ai/*.md` num plano executável, passo a passo. Escopo fechado: **100% nativo do Claude Code, só modelos Claude, sem processo/infra externa** (ver `architecture-decision-native-subagent.md`).

Docs de referência para cada fase:
- `context-economy-strategies.md` — as 6 estratégias de economia de contexto
- `reference-implementation-fastcontext.md` — discovery da implementação Python de referência
- `architecture-decision-native-subagent.md` — decisão e comparativo
- `ui-feedback-statuslines.md` — pesquisa de feedback visual
- `risks-and-gaps.md` — revisão crítica que motivou os ajustes marcados como "(ajustado)" abaixo (agora com 15 riscos, incluindo os novos #7-#15)
- `claude-code-capabilities-verified.md` — fatos confirmados via documentação oficial (schema de frontmatter, bug do `maxTurns`, payload de statusLine, comportamento do Grep, padrão de proteção de segredos)
- `go-no-go-analysis.md` — análise crítica de custo/benefício, comparação com o projeto Python original, e a decisão de rodar a Fase 0 antes de comprometer com as Fases 2-7

## Fase 0 — Experimento mínimo (gate antes de investir nas Fases 2-7) ✅ implementado e validado — GO

**Objetivo:** testar a hipótese central (delegação pra Haiku economiza tokens sem perder qualidade) com o menor investimento possível, **antes** de construir escalonamento, hooks e statusline. Ver `go-no-go-analysis.md` para o raciocínio completo.

- [x] Criar `.claude/agents/fast-context.md` **enxuto**: só o núcleo da Fase 1 (contrato estruturado, grounding verbatim, auto-contagem de turnos, reflection em confiança baixa, instrução de não citar segredos) — sem `fast-context-deep`, sem hooks, sem statusline.
- [x] Criar `.claude/scripts/validate_citations.py` — versão determinística da validação `os.path.isfile()` do projeto Python de referência (risco #2/#3), rodada pelo **agente principal** depois de receber o `<final_answer>` do `fast-context` (não pelo próprio subagent, pra preservar a restrição de tools só-leitura). Testado manualmente: rejeita arquivo inexistente e faixa de linha inválida, aceita citação real.
- [x] Rodar 3 queries reais lado a lado: `fast-context` (Haiku, subagent real, não proxy) vs. agente `Explore` nativo do Claude Code — comparar tokens, tempo, e se a resposta estava certa. Resultado: ver "Resultados da rodada 2" em `go-no-go-analysis.md`. Achados principais: (1) zero alucinação do lado do `fast-context`; (2) `fast-context` travou silenciosamente numa query (Turno 1/8, sem `<final_answer>`, precisou de nudge manual) — falha real do risco #4, não só teórica; (3) `Explore` sem desambiguação de path resolveu o repositório errado numa query; (4) comparação de tokens vs. `Explore` continua estruturalmente impossível — a ferramenta não expõe usage por-subagent.
- [x] Rodar o `validate_citations.py` no resultado de cada chamada ao `fast-context` durante o teste — todas as 22 citações das 3 queries reais passaram (exit code 0, nenhum arquivo/faixa de linha inválido).
- [x] **Decisão go/no-go: GO.** Camada 2 (hook `PreToolUse`) validada em invocação real numa sessão nova (rodada 3, ver `go-no-go-analysis.md`): query ampla forçou 11 tool calls, o hook negou a 11ª e o subagent emitiu `<final_answer confidence="low">` sozinho, sem nudge manual — resolve o stall silencioso da rodada 2. Critério de sucesso do projeto formalmente redefinido (tokens vs. `Explore` sai, por ser estruturalmente não medível nesta plataforma): zero alucinação de citação, corte real de turnos, robustez a ambiguidade de path, contrato de saída estruturado — os 4 confirmados em uso real. Próximo passo: Fase 2 (escalonamento).

## Fase 1 — Subagent explorador ("discovery") ✅ conteúdo incorporado na Fase 0 enxuta e confirmado presente em `fast-context.md`

**Objetivo:** núcleo do projeto — estratégias #4 (isolamento de contexto) + #1 (toggle de modelo).

- [x] Criar `.claude/agents/fast-context.md` com frontmatter (schema confirmado em `claude-code-capabilities-verified.md`):
  - `name: fast-context`
  - `description`: instrução pra ativação proativa ("use antes de explorar múltiplos arquivos ou seguir lógica entre módulos")
  - `model: haiku` (valor padrão — confirmado que aceita alias direto, não precisa de ID completo)
  - `tools: Read, Grep, Glob` (sem Edit/Write/Bash — restrição estrutural, não por convenção)
  - `maxTurns: 8` (configurar mesmo sabendo que há bug conhecido de não-enforcement — [issue #41143](https://github.com/anthropics/claude-code/issues/41143) — é grátis e pode ser corrigido numa versão futura; não é o mecanismo principal, ver item de auto-contagem abaixo)
- [x] Escrever o system prompt do agent (corpo do arquivo, abaixo do frontmatter), adaptando o `system.md` da referência:
  - papel: especialista em exploração read-only
  - guidelines de busca (largo → estreito, múltiplas estratégias de nome, checar convenções diferentes)
  - nunca devolver o histórico de navegação, só o resultado final
- [x] **(solução robusta — risco #3)** Contrato de saída estruturado, não texto livre:
  ```
  <final_answer confidence="high|medium|low" strategies_used="glob,grep,read" files_found="N">
  /caminho/arquivo.py:10-15
  > trecho verbatim das linhas citadas (ver próximo item)
  </final_answer>
  ```
  Definir no próprio system prompt os critérios de `confidence`: `high` = achou a definição exata do símbolo perguntado; `medium` = achou arquivos relacionados mas sem match exato ou via padrão amplo; `low` = poucos/nenhum match forte, baseado em suposição de convenção de nome.
- [x] **(solução robusta — risco #2)** Grounding por citação literal: exigir um trecho verbatim do arquivo junto de cada `arquivo:linha` (não só o range) — força o subagent a ter lido aquele trecho de fato. Complementar: instruir "antes do `<final_answer>`, faça uma chamada de Read em cada citação pra confirmar que existe e bate com o esperado" (equivalente ao `os.path.isfile` da referência, via tool call real).
- [x] **(solução robusta — risco #4, camada 1)** Auto-contagem de turnos no próprio raciocínio: "declare seu turno atual (Turno N/8); ao chegar no 8, você DEVE emitir `<final_answer>` mesmo que incompleto, com `confidence=\"low\"`".
- [x] **(solução robusta — risco #8)** Instruir reflection antes de finalizar quando `confidence` for `medium`/`low`: uma segunda passada de auto-crítica ("você checou convenções de nome alternativas? Tem certeza que cobriu todos os casos?") antes de emitir o `<final_answer>` — reduz mas não elimina o viés de excesso de confiança documentado em LLMs.
- [x] **(solução robusta — risco #7)** Exigir uma frase curta conectando cada trecho citado à pergunta original ("este trecho resolve X porque Y") — não garante correção semântica, mas força justificativa auditável em vez de citação sem contexto.
- [x] **(resolvido — risco #12)** Não precisa de configuração extra: o Grep já respeita `.gitignore` por padrão. Só adicionar no system prompt uma exclusão explícita pra código vendorizado/gerado que tenha sido commitado (não gitignored), se souber de algum caso assim no repo de teste.
- [x] Testado com 2-3 queries reais num repositório (ex: "onde fica a lógica de autenticação?") e conferido se o formato estruturado, o grounding e a auto-contagem funcionam como esperado — coberto nas rodadas 1-4 (`go-no-go-analysis.md`) e no baseline da Fase 7.

## Fase 2 — Ativação explícita e regras ✅ implementada

**Objetivo:** garantir que o subagent seja realmente usado (o vídeo de referência mostrou que ativação implícita de skill não é confiável).

- [x] **(solução robusta — risco #1)** Regra criada em `.claude/rules/exploration.md` com critério **simétrico** e exemplos concretos dos dois lados (usar: localização desconhecida, >2 arquivos, "como funciona X", análise de impacto; não usar: arquivo já lido, grep único num arquivo conhecido, edição pura, símbolo já visível).
- [x] **(solução robusta — risco #1)** Gate de auto-checagem em `.claude/rules/exploration.md`: "eu já sei o arquivo:linha exato pra isso?" antes de delegar.
- [x] **(solução robusta — risco #15)** Gate estendido com "eu já respondi isso nesta conversa?" no mesmo arquivo.
- [x] Defesa em profundidade pro risco #2: regra de leitura rápida de pelo menos uma citação antes de editar em cima dela, em `.claude/rules/exploration.md`.
- [x] **(resolvido — risco #13)** `.claude/scripts/block_secrets_hook.py` + `hooks.PreToolUse` (`Read|Edit|Write|Bash`) em `settings.json`, mais `deny` determinístico (`Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`). Testado com 7 casos sintéticos (arquivo/comando, positivo/negativo, incluindo falso-positivo `environment.md`/`enviar.envelope`) — todos corretos. Bug real encontrado e corrigido durante o teste: regex original só batia `.env`/`secrets/` no início da string ou após `/`, não após espaço — comandos Bash como `cat .env` (espaço antes do path) passavam batido. Corrigido pra `(^|[\s/])`.
- [x] **(solução robusta — risco #14)** Toda referência ao `fast-context` concentrada em `.claude/rules/exploration.md`, incluindo a nota de kill-switch (apagar/renomear `.claude/agents/fast-context.md`).

## Fase 3 — Escalonamento de modelo ✅ implementada (achou e corrigiu bug real no hook — ver rodada 4)

**Objetivo:** reforçar a estratégia #1 sem travar num único modelo fixo.

- [x] Criada `.claude/agents/fast-context-deep.md` (`model: sonnet`, mesmo tools/system prompt de `fast-context.md`). **(risco #10)** Cabeçalho de aviso YAML adicionado nos dois arquivos: "manter corpo idêntico ao outro, exceto `model:`".
- [x] **(solução robusta — risco #3)** Regra de escalonamento em `.claude/rules/exploration.md`: escalona pra `fast-context-deep` quando `confidence != "high"` **ou** `files_found` parecer baixo pro escopo da pergunta.
- [x] **(solução robusta — risco #9)** Teto de escalonamento (máximo 1 salto) documentado na mesma regra.
- [ ] Calibração ao longo do tempo: fica pra Fase 7 (precisa de gabarito manual acumulado, não faz sentido antecipar com N=poucas queries).
- [x] **Bug real encontrado e corrigido durante o teste de escalonamento** (rodada 4, ver `go-no-go-analysis.md`): o contador do `limit_turns_hook.py` usava `transcript_path`/`session_id` como chave, mas esses campos são **os mesmos em toda invocação de subagent dentro da sessão** (confirmado via hook de debug temporário) — contagem vazava entre chamadas separadas do `fast-context`, cortando cada vez mais cedo a cada nova invocação na mesma sessão. Corrigido pra usar `agent_id` (único por invocação, confirmado que bate com o `agentId` da ferramenta `Agent`). Validado com teste sintético: duas invocações com `agent_id` diferentes mas mesmo `session_id`/`transcript_path` mantêm contadores isolados.

## Fase 4 — Limite de turnos e caps de saída ✅ implementada

**Objetivo:** estratégia #6 (cap de tamanho de saída) e prevenção de loop de busca gastando tokens à toa.

- [x] No system prompt do subagent, instruído explicitamente: preferir `head_limit`/ranges pequenos nas ferramentas nativas de Grep/Read, nunca despejar arquivo inteiro quando uma faixa resolve (`.claude/agents/fast-context.md:24`).
- [x] Camada 1 (auto-contagem de turnos) já entra na Fase 1, junto com `maxTurns: 8` no frontmatter (mesmo sabendo do bug de não-enforcement).
- [x] **(solução robusta — risco #4, camada 2)** Implementado antes do previsto: a Fase 0/rodada 2 já mostrou a Camada 1 (soft) falhar 1 em 3 vezes reais (stall silencioso sem `<final_answer>`), então a condição original ("só implementar se a Fase 7 mostrar falha") foi satisfeita antecipadamente. `.claude/scripts/limit_turns_hook.py` conta invocações de `Read|Grep|Glob` por invocação de subagent (chave = `transcript_path`, único por execução) e nega via `permissionDecision: "deny"` a partir da 11ª chamada. Configurado em `hooks.PreToolUse` no frontmatter do `fast-context.md`. **Validado em sessão nova com invocação real** (rodada 3, ver `go-no-go-analysis.md`): 11 tool calls, corte confirmado, `<final_answer confidence="low">` emitido sem nudge manual.

## Fase 5 — Prompt caching por estrutura ✅ concluída (conclusão negativa — cache no subagent não é medível/observável)

**Objetivo original:** estratégia #2, ativar o cache automático do Claude Code por design.

- [x] Confirmado: `fast-context.md`, `fast-context-deep.md` e `.claude/rules/exploration.md` são editados só manualmente (`git log` mostra só commits diretos, nenhum script escreve neles) — arquivos estáveis, não regenerados por sessão.
- [x] Confirmado que nada nesse projeto regenera esses arquivos dinamicamente — condição estrutural pro cache hit do lado do Claude Code está satisfeita, na medida do que dá pra garantir sem acesso à implementação interna do cache.
- [x] **(risco #5) Medido, não afirmado — resultado negativo/inconclusivo.** Invocado `fast-context` duas vezes na mesma sessão com prompt e pergunta idênticos: chamada 1 = 9.988 tokens/4 tool calls; chamada 2 = 11.052 tokens/3 tool calls. **A 2ª chamada não ficou mais barata** mesmo com uma tool call a menos — nenhum sinal de economia de cache. Causa provável: o `Agent` tool só expõe `subagent_tokens` como total combinado (não separa `cache_read_input_tokens` de input fresco), a mesma limitação de instrumentação já registrada nas rodadas 1-2 (`go-no-go-analysis.md`). **Conclusão ajustada conforme a contingência prevista nesta fase**: não dá pra afirmar "ativa cache por design" — o que se pode afirmar é que a estrutura de arquivos estáveis não *atrapalha* um cache hipotético do lado da plataforma, mas nenhuma economia foi observável com a instrumentação disponível.

## Fase 6 — Feedback visual (statusLine + subagentStatusLine) ✅ implementada, pendente confirmação visual do usuário

**Objetivo:** visibilidade de qual agente está ativo e quantos tokens cada um gastou, sem custo de token adicional.

- [x] Pesquisar viabilidade (`ui-feedback-statuslines.md`) — confirmado: multi-linha suportado, posição só rodapé, `subagentStatusLine` é o campo certo para dados por-subagent.
- [x] **Payload do `statusLine` principal confirmado**, incluindo detalhes que a doc oficial sozinha não deixava claro: `effort.level` existe como campo próprio (não só dentro de `model`), e `cache_read_input_tokens` fica aninhado em `context_window.current_usage`, não no nível raiz de `context_window`.
- [x] **Payload do `subagentStatusLine` confirmado** via captura real do debug capturer que já estava em `settings.local.json` (dados de sessões anteriores, inclusive desta): campo `tasks` (lista), cada item com `id` (bate com o `agent_id` do payload do `PreToolUse`), `type`, `status` (`running`/`completed`), `description`/`label`, `startTime`, `tokenCount`, `tokenSamples`, `cwd`. **Não há campo de model/agent_type nesse payload** — só o hook `PreToolUse` recebe isso.
- [x] Scripts finais escritos: `.claude/scripts/statusline.py` (barra "FastCode Activate" + modelo dev, effort, custo, uso de contexto, cache read) e `.claude/scripts/subagent_statusline.py` (uma linha por subagent `running`, com `label` + tokens ao vivo). Testados contra payloads reais capturados nesta sessão — output correto, incluindo fix de formatação (`1000.0k` → `1.0M` pra `context_window_size`).
- [x] Como o payload do subagent não expõe o model, adotada convenção documentada em `.claude/rules/exploration.md`: prefixar a `description` da chamada `Agent` com o nome do agente (`"fast-context: ..."`) pra aparecer legível na linha de status.
- [x] Capturador de debug removido de `settings.local.json` (voltou a `{}`); scripts definitivos configurados em `settings.json` (**projeto, committed** — decisão do usuário: é parte da feature, não preferência pessoal).
- [ ] **Validação visual pendente**: rodei uma query real disparando o `fast-context` com a convenção de nomenclatura; preciso que o usuário confirme visualmente se as duas linhas aparecem corretamente na UI (não tenho como observar a renderização do statusLine daqui).

## Fase 7 — Validação end-to-end

**Objetivo:** confirmar o ganho de tokens/tempo prometido pela estratégia, mirror do teste que o vídeo de referência fez.

- [x] Repositório de teste: `/mnt/backup/github/fastcontext` (já usado nas rodadas 1-4, gabarito fácil de conferir à mão).
- [x] **(solução robusta — risco #6)** Criado `docs/ai/eval/baseline-queries.md`: 4 queries que deveriam disparar (Q1-Q4, multi-arquivo) + 2 triviais que não deveriam (Q5-Q6), cada uma com gabarito conferido manualmente por leitura direta.
- [x] Rodado Q1-Q4 em modo "com delegação" (fast-context real) e "sem delegação" (agente principal direto); Q5-Q6 em modo natural. Resultados em `docs/ai/eval/baseline-results-2026-07-06.md`.
- [x] Tabela de resultados registrada com tokens/tool_uses/duração/acerto contra gabarito por query.
- [x] **(risco #10)** Confirmado: `fast-context.md` e `fast-context-deep.md` seguem com corpo idêntico, só `name`/`description`/`model` diferentes.
- [x] **(risco #11)** Aviso de escopo explícito no `baseline-queries.md`: smoke test contra 1 repositório Python pequeno, não é prova de generalização.
- [x] Baseline registrado — pode servir de referência pra avaliar futuras mudanças no system prompt do subagent.

**Achados da Fase 7** (detalhe completo em `baseline-results-2026-07-06.md`):
1. **3 de 4 queries "deveria disparar" tiveram citação verbatim correta e completa**, às vezes indo além do gabarito com contexto relevante adicional (Q2, Q4) — mantém o sinal de qualidade das rodadas anteriores.
2. **Zero over-triggering** (risco #1): as 2 queries triviais (Q5-Q6) não dispararam delegação indevida — o agente principal reconheceu corretamente os dois casos de "não usar".
3. **Achado negativo importante, revisa uma conclusão da rodada 2**: Q3 falhou — o `fast-context` respondeu sobre o repositório errado (`fastContext`, este projeto, em vez de `fastcontext`, o repo de referência) por confusão de case no path, **com `confidence="high"`**. Isso mostra que o erro de ambiguidade de path (rodada 2, achado #3, atribuído só ao `Explore` nativo) **também ocorre no `fast-context`** — a vantagem de robustez relatada antes não se sustenta numa amostra maior. Critério de sucesso #3 da Fase 0 (`go-no-go-analysis.md`) fica revisado: não é uma vantagem confiável do `fast-context`.
4. **Risco #3/#8 (calibração de confidence) confirmado como não mitigado**: a falha do item 3 veio com `confidence="high"`, não `medium`/`low` — a auto-crítica instruída só dispara nos dois últimos casos, então não pegou esse erro. A defesa em profundidade (ler ao menos uma citação antes de editar, já em `exploration.md`) continua sendo a mitigação real, não a auto-avaliação do subagent.
5. **Comparação "com/sem delegação" ficou metodologicamente inconclusiva**: o agente principal já tinha lido os arquivos relevantes nesta sessão (pra montar o gabarito), então "sem delegação" não partiu do zero — registrado como limitação do baseline, não como resultado.

## Fora de escopo (adiado — ver `context-economy-strategies.md`)

- Estratégia #3 (repo map estático via tree-sitter) — exige índice mantido fora do fluxo de conversa.
- Estratégia #5 (retrieve-then-load com embeddings) — exige vector store; grep/glob já cobre o papel de "retrieve" aqui.
