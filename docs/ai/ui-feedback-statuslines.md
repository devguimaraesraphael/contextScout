# Feedback visual: statusLine e subagentStatusLine

Pesquisa sobre como mostrar, dentro do próprio Claude Code, qual agente está ativo (explorador "discovery" vs. agente principal "dev") e quantos tokens cada um consumiu — sem infra externa, sem custo extra de tokens.

## O que já é nativo, sem configurar nada

- Toda chamada de subagent (Task/Agent) mostra o nome/descrição do agente no cabeçalho do bloco na conversa, e ao terminar imprime um resumo `Done (N tool uses · Xk tokens · Ys)`.
- `/cost` a qualquer momento mostra o total acumulado de tokens/custo da sessão, quebrado por modelo.

## statusLine vs. subagentStatusLine

Existem **dois campos de configuração distintos** em `settings.json`, com propósitos diferentes:

| Campo | Onde aparece | Escopo dos dados | Uso pretendido aqui |
|---|---|---|---|
| `statusLine` | Rodapé da tela, sempre visível, acima da caixa de input | Sessão/turno como um todo (modelo atual, custo total) | Barra "FastCode Activate" + linha do modelo **dev** (agente principal) |
| `subagentStatusLine` | Painel de agentes, só enquanto um subagent está rodando | Contexto da linha (row) daquele subagent específico | Linha do modelo **discovery** (explorador Haiku), tokens daquela chamada |

Ambos são só `{"type": "command", "command": "..."}` — um comando local que roda no seu shell e recebe um JSON via stdin. **Não chamam a API**, então não têm custo de token algum — são gratuitos por definição.

## Confirmado pelo schema oficial de settings

- `statusLine.command`: string, roda como comando local.
- `statusLine.refreshInterval`: permite re-rodar o comando a cada N segundos, além dos updates orientados a evento.
- `statusLine.padding`: espaçamento.
- Multi-linha é suportado (o comando pode imprimir `\n` e a barra renderiza várias linhas).
- **Posição é sempre rodapé** — não existe opção de renderizar no topo da tela.
- `subagentStatusLine.command`: mesma estrutura, mas "recebe contexto da linha (row) como JSON no stdin" — dado por-subagent, não por-sessão.

## Em aberto — payload exato via stdin

Ainda não confirmei os nomes exatos dos campos JSON que cada comando recebe (ex: se vem `total_tokens` explícito, ou só `total_cost_usd`, ou informação de `effort`). O schema de `settings.json` documenta a *configuração*, não o *payload em runtime*.

Método de verificação em andamento: configurado um capturador de debug temporário em `.claude/settings.local.json` (arquivo pessoal, gitignored) que grava o stdin recebido em arquivos de scratchpad:

```json
{
  "statusLine": { "type": "command", "command": "tee <scratchpad>/statusline_payload.json > /dev/null; echo '...'" },
  "subagentStatusLine": { "type": "command", "command": "tee -a <scratchpad>/subagent_statusline_payload.jsonl > /dev/null; echo '...'" }
}
```

A config só é lida pelo watcher em arquivos que já existiam no início da sessão — como este `settings.local.json` foi criado no meio da sessão, é necessário reabrir o menu `/hooks` (ou reiniciar) para forçar o reload antes da captura funcionar. **Isso é o próximo passo pendente antes de escrever o script final** — ver `docs/ai/implementation-plan.md`, fase 5.

## Desenho proposto (pendente de confirmação do payload real)

- `statusLine`: `"FastCode Activate\n[dev] <modelo> · effort:<n> · <tokens/custo do turno>"`
- `subagentStatusLine`: `"[discovery] <modelo> · effort:<n> · <tokens da chamada>"`

Os nomes de campo exatos usados no `jq`/parsing do script serão ajustados assim que o payload real for capturado.
