# Decisão de arquitetura: subagent nativo do Claude Code (só Claude, sem infra externa)

Decisão: o projeto **não** vai portar/rodar o processo Python de referência (`Cirius1792/fastcontext`). Vai ser um ecossistema **100% nativo do Claude Code**: carregado e configurado inteiramente dentro do Claude (agents/skills/settings), usando só modelos Claude, sem CLI externa, sem Python/uv/ripgrep como dependência de runtime, sem endpoint OpenAI-compatible.

Isso muda o critério de avaliação das 6 estratégias em `context-economy-strategies.md`: a pergunta não é mais "qual é teoricamente mais eficaz", é **"qual funciona só com o que o Claude Code já oferece nativamente, sem infra fora do Claude"**.

## Comparativo das 6 estratégias sob esse critério

| # | Estratégia | Nativo no Claude Code? | Esforço de implementação | Economia esperada | Veredito |
|---|---|---|---|---|---|
| 4 | Isolamento de contexto por subagent | **Sim** — é o mecanismo do próprio `Agent`/`Task` tool | Baixo (1 arquivo `.claude/agents/*.md`) | Alta — é o que evita que busca/navegação entre no histórico do agente principal | **Fundação obrigatória** |
| 1 | Toggle de modelo (Haiku explorador / modelo da sessão resolvedor) | **Sim** — campo `model:` no frontmatter do agent | Baixo | Alta — Opus custa ~19x mais que Haiku em output | **Fundação obrigatória**, junto com #4 |
| 2 | Prompt caching | **Sim, automático** — Claude Code já cacheia CLAUDE.md/system prompt | Zero (só estruturar arquivos estáveis) | Média-alta, mas "de graça" | **Ativar por design**, não é trabalho extra |
| 6 | Cap de tamanho de saída das ferramentas | **Parcial** — Read/Grep nativos do Claude Code já truncam por padrão, mas sem controle explícito nosso | Baixo (reforçar via instrução no system prompt do subagent) | Média | **Reforçar**, não implementar do zero |
| 3 | Repo map estático (tree-sitter + PageRank) | **Não** — exige gerar/manter um índice fora do fluxo de conversa | Alto (script, atualização quando o repo muda) | Alta em repos grandes, mas custo de manutenção | Adiar para v2 |
| 5 | Retrieve-then-load com embeddings | **Não** — exige vector store/infra de embedding | Alto | Alta em repos muito grandes | Adiar / provavelmente desnecessário (grep+glob já faz o papel de "retrieve" no nosso caso) |

## Estratégia vencedora: #4 + #1 combinadas

O núcleo do projeto é um **subagent nativo** (`.claude/agents/fast-context.md`) que:
- roda em `model: haiku` por padrão (configurável para `sonnet` em repositórios grandes/complexos — ver estratégia #1);
- só tem acesso a `Read`, `Grep`, `Glob` (sem `Edit`, `Write`, `Bash`);
- sempre devolve um bloco compacto `<final_answer>` com `arquivo:linha_inicio-linha_fim`, nunca o histórico de navegação (estratégia #4).

As estratégias #3 e #5 ficam fora do escopo inicial porque exigem infraestrutura de indexação fora do Claude Code — contradiriam o objetivo de "tudo carregado e configurado dentro do Claude".

## Boas práticas para reforçar a estratégia escolhida

1. **Ativação explícita, não implícita.** O vídeo de referência já mostrou que ativação implícita de skill não é garantida. Regra no `CLAUDE.md`/`.claude/rules/`: sempre que uma tarefa exigir localizar código em mais de um arquivo ou seguir lógica entre módulos, invocar o subagent `fast-context` explicitamente antes de editar/responder — nunca depender do agente principal "decidir sozinho" usar Grep/Glob direto.

2. **Contrato de saída rígido.** O subagent nunca deve devolver raciocínio livre — só uma explicação opcional de até ~50 palavras seguida do bloco `<final_answer>`. Isso é o que garante que o "lixo" de navegação (tentativas de grep erradas, arquivos candidatos descartados) fique preso ao contexto do subagent e nunca volte pro agente principal.

3. **Tools restritas por design, não por convenção.** Definir `tools: Read, Grep, Glob` no frontmatter do agent (não confiar em instrução de prompt) — o subagent literalmente não deve ter acesso a `Edit`/`Write`/`Bash`, para que a separação exploração/resolução seja estrutural.

4. **Limite de turnos.** Mirror do `--max-turns` da implementação de referência: cap explícito no número de chamadas de ferramenta do subagent antes de forçar uma resposta final, evitando que um explorador em modelo barato entre em loop de busca gastando tokens sem convergir.

5. **Escalonamento em vez de modelo fixo.** Em vez de travar sempre em Haiku, permitir que o agente principal re-invoque o subagent num modelo mais forte (ex: Sonnet) quando o `<final_answer>` do Haiku vier vazio ou de baixa confiança — um "degrau" de escalonamento, não um único ponto de falha.

6. **Aproveitar prompt caching por estrutura, não por acidente.** Manter o system prompt do subagent e as regras de ativação em arquivos estáveis (que não mudam a cada sessão) para que o cache automático do Claude Code realmente pegue — evitar regenerar/reescrever esses arquivos com frequência.

7. **Reforçar os caps de saída no próprio system prompt do subagent.** Mesmo que Read/Grep nativos já truncem por padrão, instruir explicitamente o explorador a preferir `head_limit`/ranges pequenos e nunca despejar arquivo inteiro quando uma faixa de linhas resolve — reduz tokens mesmo dentro do próprio contexto isolado do subagent (não só o que volta pro agente principal).
