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

## Escalonamento de modelo (risco #3, #9, #10)

Se o `<final_answer>` do `fast-context` (Haiku) vier com `confidence` diferente de
`"high"`, **ou** com `files_found` que pareça baixo pro escopo da pergunta (não só
quando vier vazio — esse é o caso fácil, não o mais perigoso), escalone **uma única
vez** pra `fast-context-deep` (mesmo tools/system prompt, `model: sonnet`) com a
mesma pergunta original.

Teto de escalonamento: no máximo 1 salto. Se `fast-context-deep` também voltar com
`confidence != "high"`, pare — não escalone de novo, não repita. Devolva a resposta
pro fluxo principal com aviso explícito de baixa confiança pro usuário, em vez de
insistir num loop caro.

## Convenção de nomenclatura pro statusLine (Fase 6)

O payload do `subagentStatusLine` não expõe o tipo/model do subagent, só o `label`
(igual ao parâmetro `description` passado na chamada da ferramenta `Agent`). Por
isso, ao invocar `fast-context` ou `fast-context-deep`, prefixe a `description`
com o nome do agente (ex: `"fast-context: onde fica a lógica de auth?"`) — sem
isso, a linha de status mostra um texto genérico sem indicar qual modelo está rodando.
