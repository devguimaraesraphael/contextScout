# Plano de implementação — fastContext (subagent nativo do Claude Code)

Consolida o discovery feito em `docs/ai/*.md` num plano executável, passo a passo. Escopo fechado: **100% nativo do Claude Code, só modelos Claude, sem processo/infra externa** (ver `architecture-decision-native-subagent.md`).

Docs de referência para cada fase:
- `context-economy-strategies.md` — as 6 estratégias de economia de contexto
- `reference-implementation-fastcontext.md` — discovery da implementação Python de referência
- `architecture-decision-native-subagent.md` — decisão e comparativo
- `ui-feedback-statuslines.md` — pesquisa de feedback visual

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
- [ ] Testar com 2-3 queries reais num repositório (ex: "onde fica a lógica de autenticação?") e conferir se o formato de saída bate com o esperado.

## Fase 2 — Ativação explícita e regras

**Objetivo:** garantir que o subagent seja realmente usado (o vídeo de referência mostrou que ativação implícita de skill não é confiável).

- [ ] Adicionar regra em `CLAUDE.md` (ou `.claude/rules/exploration.md`): sempre que uma tarefa exigir localizar código em mais de um arquivo ou seguir lógica entre módulos, invocar `fast-context` explicitamente antes de editar/responder.
- [ ] Documentar quando **não** usar (mirror do `SKILL.md` de referência): leitura de arquivo já conhecido, grep único em arquivo específico, tarefa de escrita pura sem exploração.

## Fase 3 — Escalonamento de modelo

**Objetivo:** reforçar a estratégia #1 sem travar num único modelo fixo.

- [ ] Definir uma segunda variante do agent (ex: `fast-context-deep` com `model: sonnet`, mesmo tools/system prompt) para repositórios grandes/complexos ou quando o Haiku retornar `<final_answer>` vazio/baixa confiança.
- [ ] Documentar no `CLAUDE.md`/regra a condição de escalonamento: se `fast-context` (Haiku) não encontrar nada relevante, o agente principal deve reinvocar via `fast-context-deep` antes de desistir ou fazer a busca manualmente.

## Fase 4 — Limite de turnos e caps de saída

**Objetivo:** estratégia #6 (cap de tamanho de saída) e prevenção de loop de busca gastando tokens à toa.

- [ ] No system prompt do subagent, instruir explicitamente: preferir `head_limit`/ranges pequenos nas ferramentas nativas de Grep/Read, nunca despejar arquivo inteiro quando uma faixa resolve.
- [ ] Definir um limite de turnos de exploração razoável na descrição/instruções do agent (mirror do `--max-turns` da referência) — se não convergir, forçar resposta final com o que foi encontrado até então.

## Fase 5 — Prompt caching por estrutura

**Objetivo:** estratégia #2, ativar o cache automático do Claude Code por design.

- [ ] Manter o system prompt do `fast-context` e as regras de ativação em arquivos estáveis, que não são reescritos a cada sessão.
- [ ] Evitar qualquer mecanismo que regenere esses arquivos dinamicamente por sessão (quebraria o cache hit).

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
- [ ] Rodar a mesma pergunta de exploração duas vezes: uma pedindo explicitamente para usar `fast-context`, outra sem (deixando o agente principal explorar direto com Read/Grep/Glob nativos).
- [ ] Comparar tokens gastos e tempo de resposta (via `/cost` e os resumos `Done (...)` de cada subagent call).
- [ ] Registrar o resultado como nota em `docs/ai/` (não precisa ser um doc novo — pode ser uma seção adicionada num dos existentes).

## Fora de escopo (adiado — ver `context-economy-strategies.md`)

- Estratégia #3 (repo map estático via tree-sitter) — exige índice mantido fora do fluxo de conversa.
- Estratégia #5 (retrieve-then-load com embeddings) — exige vector store; grep/glob já cobre o papel de "retrieve" aqui.
