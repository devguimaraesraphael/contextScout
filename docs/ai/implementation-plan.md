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
  - contrato de saída obrigatório: explicação opcional de até 50 palavras + bloco `<final_answer>` com `arquivo:linha_inicio-linha_fim`
  - nunca devolver o histórico de navegação, só o resultado final
- [ ] **(ajustado — risco #2)** Instruir o subagent a reconfirmar cada citação com uma leitura rápida antes de finalizar (evitar devolver caminho/linha não verificado — a implementação de referência valida isso em código com `os.path.isfile`, aqui só dá pra pedir via prompt, mas é melhor que nada).
- [ ] **(ajustado — risco #3)** Instruir o subagent a reportar confiança/completude junto com o `<final_answer>` (ex: "N arquivos encontrados via M estratégias de busca, confiança alta/média/baixa") — não só o bloco de citações puro.
- [ ] Testar com 2-3 queries reais num repositório (ex: "onde fica a lógica de autenticação?") e conferir se o formato de saída bate com o esperado.

## Fase 2 — Ativação explícita e regras

**Objetivo:** garantir que o subagent seja realmente usado (o vídeo de referência mostrou que ativação implícita de skill não é confiável).

- [ ] Adicionar regra em `CLAUDE.md` (ou `.claude/rules/exploration.md`): sempre que uma tarefa exigir localizar código em mais de um arquivo ou seguir lógica entre módulos, invocar `fast-context` explicitamente antes de editar/responder.
- [ ] **(ajustado — risco #1)** Documentar quando **não** usar, com o mesmo peso que a regra de quando usar (mirror do `SKILL.md` de referência): arquivo já lido nesta sessão, grep único num arquivo já conhecido, tarefa de escrita pura sem exploração. Isso não é opcional/nice-to-have — sem esse critério, a regra de "sempre invocar" aumenta o consumo de tokens em buscas triviais em vez de reduzir.

## Fase 3 — Escalonamento de modelo

**Objetivo:** reforçar a estratégia #1 sem travar num único modelo fixo.

- [ ] Definir uma segunda variante do agent (ex: `fast-context-deep` com `model: sonnet`, mesmo tools/system prompt) para repositórios grandes/complexos ou quando o Haiku retornar `<final_answer>` vazio/baixa confiança.
- [ ] **(ajustado — risco #3)** Documentar no `CLAUDE.md`/regra a condição de escalonamento cobrindo os dois casos: `<final_answer>` **vazio** OU confiança **baixa/média reportada pelo próprio subagent** (depende do ajuste da Fase 1 de reportar confiança) — não só o caso vazio, que é o mais fácil de detectar mas não o mais perigoso.

## Fase 4 — Limite de turnos e caps de saída

**Objetivo:** estratégia #6 (cap de tamanho de saída) e prevenção de loop de busca gastando tokens à toa.

- [ ] No system prompt do subagent, instruir explicitamente: preferir `head_limit`/ranges pequenos nas ferramentas nativas de Grep/Read, nunca despejar arquivo inteiro quando uma faixa resolve.
- [ ] Definir um limite de turnos de exploração razoável na descrição/instruções do agent (mirror do `--max-turns` da referência) — se não convergir, forçar resposta final com o que foi encontrado até então.
- [ ] **(ajustado — risco #4)** Documentar explicitamente que esse limite é uma instrução de prompt, não um corte de código — não existe campo de frontmatter que force isso hoje. Revisar na Fase 7 se o comportamento observado bate com o esperado (o subagent realmente para, ou continua buscando além do razoável?).

## Fase 5 — Prompt caching por estrutura

**Objetivo:** estratégia #2, ativar o cache automático do Claude Code por design.

- [ ] Manter o system prompt do `fast-context` e as regras de ativação em arquivos estáveis, que não são reescritos a cada sessão.
- [ ] Evitar qualquer mecanismo que regenere esses arquivos dinamicamente por sessão (quebraria o cache hit).
- [ ] **(ajustado — risco #5)** Tratar o ganho de cache no subagent explorador como suposição não confirmada, não como fato — validar de verdade na Fase 7 observando se chamadas repetidas ao `fast-context` mostram custo de input menor (cache hit) ou não.

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
- [ ] **(ajustado — risco #6)** Definir de 5 a 6 queries de teste **fixas** contra esse repositório antes de considerar a Fase 1 "pronta" — não uma pergunta solta e informal. Isso vira o baseline pra qualquer ajuste futuro no system prompt do subagent ser avaliado como melhora ou piora, não só "pareceu melhor".
- [ ] Rodar cada query duas vezes: uma pedindo explicitamente para usar `fast-context`, outra sem (deixando o agente principal explorar direto com Read/Grep/Glob nativos).
- [ ] Comparar tokens gastos, tempo de resposta (via `/cost` e os resumos `Done (...)`) e se o arquivo/linha certo foi de fato encontrado (não só se voltou uma resposta com aparência de completa — ver risco #3).
- [ ] Validar o comportamento de limite de turnos (risco #4) e de cache (risco #5) observados na prática.
- [ ] Registrar o resultado como nota em `docs/ai/` (não precisa ser um doc novo — pode ser uma seção adicionada num dos existentes).

## Fora de escopo (adiado — ver `context-economy-strategies.md`)

- Estratégia #3 (repo map estático via tree-sitter) — exige índice mantido fora do fluxo de conversa.
- Estratégia #5 (retrieve-then-load com embeddings) — exige vector store; grep/glob já cobre o papel de "retrieve" aqui.
