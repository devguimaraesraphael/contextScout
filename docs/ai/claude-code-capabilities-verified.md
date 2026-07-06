# Capacidades do Claude Code — verificadas via documentação oficial

Fatos confirmados sobre a plataforma (não suposições), levantados para destravar premissas técnicas do `implementation-plan.md`. Cada item cita a fonte.

## Frontmatter de subagent (`.claude/agents/*.md`)

Campos suportados: `name`, `description`, `prompt`, `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills`, `initialPrompt`, `memory`, `effort`, `background`, `isolation`, `color`. Obrigatórios: `name` e `description`.

- **`model`**: aceita `sonnet`, `opus`, `haiku`, um ID completo (ex: `claude-opus-4-7`), ou `inherit` (padrão). Confirma que `model: haiku` no `fast-context.md` funciona como planejado.
- **`tools`**: allowlist — se especificado, o subagent só pode usar essas ferramentas. Se omitido, herda todas.
- **`disallowedTools`**: denylist subtraída do que o subagent teria por padrão. Se ambos definidos, `disallowedTools` é aplicado primeiro, depois `tools` é resolvido contra o que sobrou.
- **`hooks`**: pode ser definido **por-agent**, direto no frontmatter do subagent — não precisa ser um hook global em `settings.json`. Isso é relevante pro risco de "o hook consegue identificar qual agente disparou a tool call?" (ver `risks-and-gaps.md`, risco #4): a resposta é que **não precisa identificar**, porque o hook pode viver dentro da própria definição do `fast-context.md` e só disparar quando aquele agent específico rodar.
- **`maxTurns`**: limita quantos loops agentic (chamadas de ferramenta) o subagent pode rodar antes de parar. Recomendado como boa prática em todo agent (valor seguro sugerido: 50).
  - ⚠️ **Bug conhecido confirmado**: [issue #41143 no repo oficial `anthropics/claude-code`](https://github.com/anthropics/claude-code/issues/41143) documenta que `maxTurns` **não é enforced na prática** — um agent configurado com `maxTurns: 10` rodou 72+ turnos. Configurar o campo mesmo assim (é de graça e pode ser corrigido numa versão futura), mas **não tratar como garantia** — a auto-contagem comportamental no system prompt continua sendo o mecanismo primário de controle de turnos.

Fonte: [Create custom subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents), [GitHub issue #41143](https://github.com/anthropics/claude-code/issues/41143)

## Payload JSON do `statusLine`

Confirmado via documentação oficial — campos reais recebidos via stdin: `cwd`, `session_id`, `session_name`, `transcript_path`, `model` (`id`, `display_name`), `workspace` (`current_dir`, `project_dir`, `added_dirs`, `git_worktree`), `version`, `output_style`, `cost` (`total_cost_usd`, `total_duration_ms`, `total_api_duration_ms`, `total_lines_added`, `total_lines_removed`), `context_window` (`total_input_tokens`, `total_output_tokens`, `context_window_size`, `used_percentage`, `remaining_percentage`, `current_usage`), `exceeds_200k_tokens`, `rate_limits`, `cache_read_input_tokens`.

Isso já é suficiente pra escrever a linha do modelo **dev** no `statusLine` principal sem precisar do capturador de debug. O payload do `subagentStatusLine` (por-subagent) **ainda não foi confirmado** por essa pesquisa — continua pendente a captura via `/hooks`.

Fonte: [Customize your status line — Claude Code Docs](https://code.claude.com/docs/en/statusline)

## Grep/ripgrep já ignora diretórios ruidosos por padrão

O Grep do Claude Code é baseado em ripgrep, que **respeita `.gitignore`, `.ignore` e `.git/info/exclude` automaticamente**. `node_modules`, `dist`, `.venv` etc. já ficam de fora das buscas do `fast-context` sem nenhuma configuração extra, desde que estejam no `.gitignore` do projeto explorado. Resta só o caso de código vendorizado/gerado que foi commitado (não gitignored) — aí vale um glob de exclusão explícito no system prompt do subagent.

Fonte: [ripgrep — gitignore-aware search](https://github.com/BurntSushi/ripgrep), [Agentic Search — ivanleo.com](https://ivanleo.com/blog/agentic-search)

## Padrão para bloquear leitura de segredos (`.env`, `secrets/**`)

Solução conhecida e documentada por múltiplas fontes, aplicável tanto ao agente principal quanto ao `fast-context`:

- Hook `PreToolUse` casado com `Read|Edit|Write|Bash` que verifica `tool_input.file_path` (e `tool_input.command` pra Bash) contra padrões como `.env`, `.env.*`, `secrets/**`, e sai com **exit code 2** quando bate — isso bloqueia a chamada antes de executar e devolve a mensagem de erro pro modelo.
- Complementar com uma regra `deny` determinística em `settings.json`: `"deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]` — `deny` sempre vence sobre `allow`, em qualquer escopo.
- **Importante**: o Claude Code trata `.env` como arquivo legível normal por padrão — não há redação automática de segredo embutida. Sem essa configuração, tanto o agente principal quanto o `fast-context` podem ler e citar conteúdo de `.env` livremente.

Fonte: [Claude Code Hooks (2026) — Block Claude Reading .env](https://www.morphllm.com/claude-code-hooks), [Protecting Your .env File with Claude Code Hooks](https://jorgepit-14189.medium.com/protecting-your-env-file-with-claude-code-hooks-c0122019a575)

## Confiança autorrelatada em LLMs — pesquisa externa (não específica do Claude Code)

Not Claude-Code-specific, mas relevante pro risco #3/#8 em `risks-and-gaps.md`:

- Confiança verbalizada por um LLM tem viés estrutural de excesso de confiança e **"não pode ser interpretada como probabilidade sem um passo de recalibração posterior"** — mas é **útil como sinal de ranking** (ROC-AUC), que é exatamente o uso que fazemos aqui (decidir escalar ou não), não uma leitura de probabilidade exata.
- Mitigação mais barata aplicável sem infra extra (comparada a ensemble de múltiplos modelos ou RL de calibração): técnica tipo **UAR** (reflection-based) — quando o subagent for reportar `confidence` abaixo de `high`, instruir uma segunda passada de auto-crítica antes de finalizar ("você checou convenções de nome alternativas? Tem certeza que cobriu todos os casos?").

Fonte: [Confidence Calibration in LLMs — Emergent Mind](https://www.emergentmind.com/topics/confidence-calibration-in-llms), [Know When You're Wrong — arXiv 2603.06604](https://arxiv.org/pdf/2603.06604)
