# Estratégias de economia de contexto/tokens

Levantamento de estratégias usadas por agentes de código (FastContext, Aider, Claude Code) para reduzir o consumo de tokens de contexto. Nenhuma foi implementada ainda neste projeto — este documento é o plano de referência para quando a implementação começar.

Pesquisa feita em 2026-07, fontes no final de cada seção.

## 1. Subagent explorador com modelo mais barato (toggle de modelo)

**Status: não implementado.**

Em vez de um modelo local treinado (como o `microsoft/FastContext-1.0-4B-RL`), usar um subagent nativo do Claude Code com `model: haiku` para explorar o repositório (Read/Glob/Grep), enquanto o modelo escolhido pelo usuário na sessão (Opus/Sonnet) fica responsável por resolver a tarefa.

- Configurável: permitir subir o explorador para Sonnet em repositórios muito grandes/complexos, em vez de fixar sempre em Haiku.
- Sem infra local (sem Ollama, sem GPU dedicada).
- Trade-off: Haiku genérico não tem o fine-tuning específico do modelo da Microsoft, então a precisão da busca pode ser levemente menor — compensado pela simplicidade.

Fonte: [FastContext-1.0-4B-RL — Hugging Face](https://huggingface.co/microsoft/FastContext-1.0-4B-RL), [Claude Code Docs — Subagents](https://code.claude.com/docs/en/sub-agents), [Best AI Model for Coding Agents in 2026 — Augment Code](https://www.augmentcode.com/guides/ai-model-routing-guide)

## 2. Prompt caching

**Status: não implementado (parcialmente automático no Claude Code, mas não estruturado no projeto).**

O Claude Code já cacheia automaticamente CLAUDE.md e o system prompt entre mensagens (desconto de até 90% no custo de input em cache hit). Para aproveitar isso de propósito no projeto:

- Manter conteúdo estável (CLAUDE.md, docs de arquitetura, regras) em posição cacheável no prompt — evitar reescrever esses arquivos com frequência dentro de uma mesma sessão.
- Evitar cachear resultados de ferramentas com saída muito variável (ex: grep com resultado diferente a cada chamada) — não há benefício e pode adicionar overhead.

Fonte: [Prompt Caching — Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Don't Break the Cache — arXiv 2601.06007](https://arxiv.org/html/2601.06007v2)

## 3. Repo map estático (estilo Aider)

**Status: não implementado.**

Índice estático do repositório via tree-sitter, com ranking tipo PageRank sobre símbolos/identificadores. Identificadores já citados na conversa recebem peso maior (~10x) e arquivos abertos no contexto atual recebem peso ainda maior (~50x). Reduz a necessidade de grep amplo porque o agente já sabe de antemão onde os símbolos relevantes provavelmente estão.

Fonte: [Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures — arXiv 2604.03515](https://arxiv.org/pdf/2604.03515)

## 4. Isolamento de contexto por subagent

**Status: não implementado — é o mecanismo central do design do FastContext (ver `CLAUDE.md`).**

Cada subagent roda em janela de contexto própria. Buscas, candidatos descartados e navegação intermediária ficam presos ao contexto do explorador e nunca entram no histórico do agente principal — só o resultado final (arquivo + intervalo de linhas) é devolvido.

Fonte: transcrição em `transcricao-video-fastcontext.md`, [FastContext — DeepWiki](https://deepwiki.com/microsoft/fastcontext)

## 5. Retrieve-then-load híbrido

**Status: não implementado.**

Combinar uma etapa de recuperação (grep/regex ou embeddings) para localizar a fatia relevante do repositório, e só então carregar essa fatia na janela de contexto grande para o raciocínio do agente principal. Evita dois extremos ruins: indexar tudo via embeddings (caro de manter atualizado) ou carregar o repositório inteiro na janela (estoura contexto rápido).

Fonte: [Context engineering: LLM evolution for agentic AI — Elastic Search Labs](https://www.elastic.co/search-labs/blog/context-engineering-llm-evolution-agentic-ai)

## Poda de transcript (bônus, não contada nas 5 principais)

Descartar do histórico do agente principal chamadas de ferramenta antigas que não são mais referenciadas, evitando que o contexto cresça sem necessidade ao longo de uma sessão longa.

## Cap de tamanho de saída das ferramentas (encontrado na implementação de referência)

**Status: não implementado.**

A implementação de referência (`Cirius1792/fastcontext`, ver `docs/ai/reference-implementation-fastcontext.md`) limita agressivamente o tamanho da resposta de cada tool call, independente de quantos tokens o modelo "pediria":

- `Read`: máximo 2000 linhas e 2000 caracteres por linha.
- `Grep`: máximo 100 linhas de resultado.
- `Glob`: máximo 100 arquivos.

Isso evita que uma única chamada de ferramenta explosiva (grep genérico demais, arquivo enorme) estoure sozinha o orçamento de contexto do turno, independente de qualquer outra estratégia de delegação.

Fonte: `docs/ai/reference-implementation-fastcontext.md` (código-fonte lido em `src/fastcontext/agent/tool/{read,grep,glob}.py`)
