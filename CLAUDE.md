# fastContext

Reimplementação do conceito **FastContext** (originalmente `microsoft/fastcontext`, hoje indisponível publicamente): um subagent/skill dedicado a explorar um repositório de código e devolver só o trecho relevante (arquivo + intervalo de linhas) para o agente principal, em vez de deixar o agente principal gastar tokens fazendo grep/glob/leitura de arquivo diretamente.

Referência de contexto: `transcricao-video-fastcontext.md` (transcrição de vídeo explicando o projeto original) e `docs/ai/reference-implementation-fastcontext.md` (discovery de uma implementação de referência em Python, clonada em `/mnt/backup/github/fastcontext`, fora deste repo).

## Ideia central

- Dois agentes separados: um **explorador** (busca) e um **resolvedor** (edita/decide).
- O explorador só tem 3 ferramentas: leitura de arquivo (com número de linha), glob e grep/regex. Não executa nada.
- O explorador roda em contexto isolado e pode usar um modelo mais barato/local — quem resolve a tarefa usa o modelo mais caro.
- Saída do explorador: bloco enxuto de evidência (arquivo + linhas), nunca o histórico de navegação.
- Ativação no Claude Code via skill — pode ser implícita, via slash command, ou explícita citando o nome no prompt (a explícita é a mais confiável).

## Status

Projeto ainda não implementado — este é o setup inicial do repositório. Stack, comandos e estrutura de pastas serão definidos quando a implementação começar.

Plano de estratégias de economia de contexto a implementar: ver `docs/ai/context-economy-strategies.md`.

Decisão de arquitetura (só Claude, sem infra externa, tudo nativo do Claude Code): ver `docs/ai/architecture-decision-native-subagent.md`.

## Regras

- Sem segredos/credenciais em nenhum arquivo commitado.
- `CLAUDE.local.md` e `.claude/settings.local.json` são pessoais — nunca commitar (ver `.gitignore`).
