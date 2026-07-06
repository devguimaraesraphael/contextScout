# fastContext

Um subagente do Claude Code que explora um repositório de código e devolve só o
trecho relevante (arquivo + linhas) para o assistente principal — em vez de deixar
o assistente principal (o modelo mais caro) gastar contexto fazendo grep/glob/leitura
de arquivo diretamente.

Reimplementação nativa (sem infraestrutura externa, só arquivos que o Claude Code
já sabe interpretar) do conceito **FastContext** (`microsoft/fastcontext`, hoje
indisponível publicamente).

---

## Para não programadores

### Em uma frase

Um estagiário de busca, barato e rápido, que vasculha o código antes do assistente
caro precisar fazer isso ele mesmo — e só entrega a página exata, já grifada.

### Como instalar

Não tem programa pra baixar nem conta pra criar. É só copiar uma pasta.

1. Copie a pasta inteira **`.claude/`** deste projeto para dentro da pasta raiz do
   seu projeto (o lugar onde você já usa o Claude Code).
2. Se o seu projeto já tiver uma pasta `.claude/` própria, copie por dentro — arquivo
   por arquivo — em vez de sobrescrever a pasta toda (peça pra um programador da
   equipe fazer essa parte, ver seção abaixo).
3. Feche e abra de novo a sessão do Claude Code no projeto.

Pronto — o explorador já está disponível.

### Como usar

Você não precisa aprender um jeito especial de perguntar. Faça a pergunta
normalmente, do seu jeito. Duas formas de acionar:

- **Automática**: o assistente principal decide sozinho se vale a pena chamar o
  explorador, com base na pergunta.
- **Explícita** (mais confiável): peça citando o nome — *"usa o fast-context pra
  achar onde fica X"*.

A responsabilidade de perceber se a pergunta é ampla demais e precisa ser quebrada
em pedaços menores é do assistente principal, não sua.

### Guia visual completo

Um guia com organograma do fluxo, exemplos de perguntas, e a lista honesta do que
dá pra confiar e o que exige cuidado está disponível como artefato interativo —
peça para quem te repassou este projeto o link, ou gere um novo pedindo ao Claude
Code "cria um artefato explicando o fastContext para quem não programa".

---

## Para programadores

### Arquitetura

Dois agentes nativos do Claude Code, não dois processos separados:

- **`fast-context`** (`model: haiku`) — explorador. Só tem acesso a `Read`, `Grep`,
  `Glob`. Nunca edita, nunca executa. Roda em contexto isolado.
- **`fast-context-deep`** (`model: sonnet`) — mesmo corpo/system prompt, usado só
  como escalonamento quando `fast-context` retorna `confidence != "high"` (teto de
  1 salto). **Corpo mantido idêntico ao de `fast-context.md`, exceto o campo
  `model`** — ao editar um, edite o outro.

Ativação orquestrada por `.claude/rules/exploration.md`: quando delegar, quando
não delegar, gate de auto-checagem antes de delegar, defesa em profundidade
(conferir citação antes de agir mesmo com `confidence="high"`), regra de
escalonamento, e a convenção de nomenclatura pro `subagentStatusLine`.

### Inventário de arquivos

| Arquivo | Papel |
|---|---|
| `.claude/agents/fast-context.md` | Definição do explorador (Haiku), contrato de saída estruturado (`<final_answer>`), controle de turnos. |
| `.claude/agents/fast-context-deep.md` | Variante de escalonamento (Sonnet). |
| `.claude/rules/exploration.md` | Única fonte de regra de ativação/uso — kill-switch documentado ali. |
| `.claude/scripts/limit_turns_hook.py` | Hook `PreToolUse` (escopado no frontmatter do `fast-context.md`) que nega a 11ª chamada de `Read\|Grep\|Glob` por invocação de subagente. Chave de contagem: `agent_id` — não usar `session_id`/`transcript_path`, que vazam entre invocações na mesma sessão. |
| `.claude/scripts/block_secrets_hook.py` | Hook `PreToolUse` global (`settings.json`), bloqueia leitura/comando sobre `.env`, `.env.*`, `secrets/**`. |
| `.claude/scripts/validate_citations.py` | Script determinístico, **rodado pelo agente principal** (não pelo subagente) depois de receber o `<final_answer>` — confere `os.path.isfile()` de cada citação. Não é chamado automaticamente por hook; é uma checagem manual/scriptada quando quiser validar um lote de respostas. |
| `.claude/scripts/statusline.py` | `statusLine` do agente principal (custo, contexto, cache). |
| `.claude/scripts/subagent_statusline.py` | `subagentStatusLine` — uma linha por subagente `running`, com `label` + tokens ao vivo. |
| `.claude/settings.json` | Wiring dos hooks acima + `statusLine`/`subagentStatusLine` + `deny` de segredos. **Committed** — parte da feature, não preferência pessoal. |

### Instalação

```bash
cp -r /mnt/backup/github/fastContext/.claude /caminho/do/seu/projeto/
```

Se o projeto de destino já tiver `.claude/settings.json` próprio, **não sobrescreva
— faça merge manual** dos blocos `hooks`, `statusLine`, `subagentStatusLine` e
`permissions.deny`, já que `settings.json` é um objeto único por projeto.

Subagentes de projeto (`.claude/agents/*.md`) só são recarregados numa sessão nova
— editar/copiar no meio de uma sessão em andamento não tem efeito até reiniciar.

### Escopo garantido vs. não garantido

Ver `CLAUDE.md` (seção "Escopo revisado") para o resumo, e os documentos abaixo
para o detalhe com evidência:

- `docs/ai/eval/baseline-results-2026-07-06.md` — baseline de validação end-to-end.
- `docs/ai/risks-and-gaps.md` — 15 riscos identificados, com status de mitigação
  (dois seguem sem mitigação na origem: calibração de confiança e estouro de turno
  em perguntas amplas — ambos contidos via regra de uso em `exploration.md`, não
  corrigidos no subagente em si).
- `docs/ai/go-no-go-analysis.md` — histórico completo da decisão, incluindo achados
  negativos e como cada um foi tratado (ou não).
- `docs/ai/claude-code-capabilities-verified.md` — fatos confirmados sobre a
  plataforma (schema de agent, bug do `maxTurns`, payload de statusLine).

### Kill-switch

Apagar ou renomear `.claude/agents/fast-context.md` desativa o mecanismo sem deixar
referência quebrada em outro lugar — toda referência ao subagente está concentrada
em `.claude/rules/exploration.md`.

### Regras do repositório

- Sem segredos/credenciais em nenhum arquivo committed.
- `CLAUDE.local.md` e `.claude/settings.local.json` são pessoais — nunca commitar
  (ver `.gitignore`).
