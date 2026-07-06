# Regra de ativação — fast-context

Única fonte de referência ao subagent `fast-context` (kill-switch: apagar/renomear
`.claude/agents/fast-context.md` desativa o mecanismo sem deixar referência
quebrada em outro lugar).

## Quando usar

- Localização do código relevante é desconhecida.
- A lógica atravessa mais de 2 arquivos/módulos.
- Pergunta do tipo "como funciona X" sobre comportamento não visível no contexto atual.
- Análise de impacto ("o que quebra se eu mudar Y").

Exemplo: "onde fica a lógica de autenticação?" → localização desconhecida, delega.

## Quando NÃO usar

- O arquivo relevante já foi lido nesta sessão.
- É um grep único num arquivo já conhecido.
- É edição pura, sem exploração (símbolo exato já visível no contexto atual).
- A pergunta já foi respondida nesta conversa (citação anterior cobre o caso).

Exemplo: "muda o nome dessa variável na linha 42 que acabei de ler" → não delega, edita direto.

## Gate de auto-checagem obrigatório antes de delegar

Antes de invocar `fast-context`, pergunte-se explicitamente:
1. Eu já sei o arquivo:linha exato pra isso? Se sim, pula a delegação.
2. Eu já respondi isso nesta conversa? Se sim, reusa a citação anterior em vez de re-disparar.

## Defesa em profundidade (risco #2)

Antes de editar em cima de uma citação recebida do `fast-context`, sempre fazer
uma leitura rápida (Read) de pelo menos uma das citações pra confirmar que
o trecho existe e bate com o esperado — não confiar 100% no grounding do subagent.
