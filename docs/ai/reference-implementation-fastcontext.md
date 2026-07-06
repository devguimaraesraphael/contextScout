# Discovery: implementação de referência (Cirius1792/fastcontext)

Repositório: https://github.com/Cirius1792/fastcontext (mirror/fork do `microsoft/fastcontext` original, que está indisponível publicamente). Clonado como projeto irmão em `/mnt/backup/github/fastcontext` (fora deste repo — não é submódulo nem foi vendorizado).

Licença: MIT, copyright Microsoft Corporation. Se qualquer código daqui for reaproveitado/adaptado, manter o aviso de copyright.

## Stack

- Python 3.12+, gerenciado com `uv`.
- Dependências principais: `openai` (cliente usado mesmo para endpoints não-OpenAI, via base_url compatível), `pydantic`, `jinja2` (template do system prompt), `aiofiles`.
- CLI via `argparse`, entrypoint `fastcontext = "fastcontext.cli:main"`.
- Ferramenta `Grep` depende de `ripgrep` (`rg`) instalado no sistema — falha explicitamente se não encontrar.

## Arquitetura

```
cli.py
  → agent_factory.make_fastcontext_agent(trajectory_file, work_dir)
      → carrega system.md (template Jinja com OS/shell/work_dir/listagem de diretório)
      → cria LLM (wrapper OpenAI-compatible: FC_MODEL, FC_BASE_URL, FC_API_KEY, FC_MAX_TOKENS, FC_TEMPERATURE)
      → cria ToolSet([ReadTool, GlobTool, GrepTool])
  → Agent.run(prompt, max_turns, verbose, citation)
      → loop: LLM.acall(messages, tools) → se tool_calls, executa e acrescenta resultado; senão retorna conteúdo final
      → se --citation, extrai só o bloco <final_answer> via regex (utils.parse_citations/format_citations)
```

- **Context** (`context.py`): histórico de mensagens em memória + append em JSONL de trajetória (`.fastcontext/trajectory_*.jsonl`). Descarta `usage`/`reasoning_content` do histórico antes de reenviar ao LLM (evita inflar tokens com metadado).
- **Tools** (`tool/read.py`, `glob.py`, `grep.py`): todas restringem o `path`/`directory` a estar dentro do `work_dir` (checagem `is_relative_to`) — sandboxing básico contra path traversal.
- **Guard-rails de tamanho de saída** (relevante para economia de contexto — não estava nas 5 estratégias documentadas antes, vale registrar como complementar):
  - `Read`: cap de 2000 linhas e 2000 caracteres por linha.
  - `Grep`: cap de 100 linhas de resultado (ou `head_limit` do chamador, se menor).
  - `Glob`: cap de 100 arquivos.
- **Modelo configurável via env vars** (`FC_MODEL`, `FC_BASE_URL`, `FC_API_KEY`, `FC_MAX_TOKENS`, `FC_TEMPERATURE`, `FC_REASONING_EFFORT`) — qualquer endpoint OpenAI-compatible, incluindo Ollama local (README mostra `FastContext-1.0-4B-RL` rodando via Ollama).

## Gap encontrado: suporte a Claude é código morto

Em `src/fastcontext/agent/llm.py:93-97`:

```python
if "claude" in self.model:
    # Use the custom API call for claude models
    from fastcontext.agent.llm_api import call_completion
    response = call_completion(model=self.model, messages=messages, tools=tools)
```

O módulo `fastcontext.agent.llm_api` **nunca foi commitado** neste repositório (confirmado via `git log --all -- src/fastcontext/agent/llm_api.py`, sem resultado). Ou seja: passar um `FC_MODEL` contendo `"claude"` quebra em `ImportError` — não há, de fato, integração nativa com Claude/Anthropic pronta em nenhum fork conhecido do FastContext. Isso confirma que a estratégia #1 do nosso plano (`docs/ai/context-economy-strategies.md`) — explorador rodando em Haiku/modelo Claude mais barato, resolvedor no modelo escolhido pela sessão — é trabalho real a fazer, não algo que já existe e só falta configurar.

## Duas formas de integração com um coding agent

1. **Skill que invoca a CLI via shell** (`skills/fastcontext/SKILL.md`): frontmatter `allowed-tools: Bash(fastcontext *)`, instrui quando usar/não usar, e o agente principal chama `fastcontext -q "<pergunta>" --citation` como subprocesso.
2. **Uso programático em Python**: `make_fastcontext_agent(...).run(prompt=..., max_turns=6, citation=True)` — para quem já está integrando via código, não via shell.

O `system.md` (system prompt do explorador) é o texto que define seu comportamento — a mesma noção explicada antes: instrui o modelo a ser um "codebase exploration specialist", só ferramentas read-only, terminar sempre com um bloco `<final_answer>` com `arquivo:linha_inicio-linha_fim`.

## Implicação para o nosso projeto

Este repositório de referência é um **processo Python externo** que fala com qualquer LLM via API OpenAI-compatible — não é nativo do Claude Code. Para o nosso caso ("só usar Claude, sem infra local"), há duas rotas possíveis, com trade-offs diferentes:

- **(A) Portar/adaptar este projeto Python**: implementar de fato o `llm_api.py` faltante para chamar a API da Anthropic, manter a CLI e a skill via `Bash(fastcontext *)`. Vantagem: reaproveita toda a lógica de agent loop, guard-rails de tamanho de saída e parsing de citação já testada. Desvantagem: mantém uma dependência de processo Python externo rodando fora do Claude Code.
- **(B) Subagent nativo do Claude Code**: reimplementar o mesmo contrato (system prompt read-only, `<final_answer>` com file:line, tools Read/Glob/Grep) como um agent definido em `.claude/agents/fast-context.md`, usando as ferramentas Read/Glob/Grep que o próprio Claude Code já expõe nativamente, com `model: haiku` configurável. Vantagem: zero processo externo, zero dependência de `ripgrep`/Python/uv, mais simples de manter. Desvantagem: não reaproveita o código Python existente (mas o *system prompt* e o *contrato de saída* podem ser copiados quase 1:1).

Essa decisão de arquitetura ainda não foi tomada — ver conversa/próximos passos.
