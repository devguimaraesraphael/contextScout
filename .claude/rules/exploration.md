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

**Falha sem `<final_answer>` nenhum (achado 2026-07-06)**: se a resposta do
`fast-context` terminar em texto de raciocínio solto, sem nenhum bloco
`<final_answer>` (ex: "Turno N/8: vou verificar mais uma coisa..." e nada depois),
trate isso como equivalente a `confidence="low"` pro efeito de escalonamento — **não**
como resposta vazia a ignorar. Causa raiz confirmada (3/3 reproduções com a mesma
pergunta ampla, mesmo após reforçar a instrução do subagent duas vezes): o modelo
anuncia uma próxima ação sem executá-la na mesma resposta, e o loop do subagent
termina ali por não haver tool call. Instrução no system prompt **não resolveu** —
tratar como limitação estrutural, não como algo corrigível só com redação melhor.

Ao escalonar por esse motivo, **reformule a pergunta original de forma mais estreita**
antes de reenviar pra `fast-context-deep` (ex: trocar "descreva passo a passo todo o
fluxo X, citando cada arquivo" por uma pergunta focada num único ponto do fluxo) — perguntas
amplas e abertas ("descreva com calma todo o fluxo", "citando cada arquivo relevante")
são o gatilho conhecido desse estouro; perguntas fechadas com escopo claro não
mostraram esse padrão nos testes.

Teto de escalonamento: no máximo 1 salto. Se `fast-context-deep` também voltar com
`confidence != "high"` (ou sem `<final_answer>` nenhum), pare — não escalone de novo,
não repita. Devolva a resposta pro fluxo principal com aviso explícito de baixa
confiança pro usuário, em vez de insistir num loop caro.

## Convenção de nomenclatura pro statusLine (Fase 6)

O payload do `subagentStatusLine` não expõe o tipo/model do subagent, só o `label`
(igual ao parâmetro `description` passado na chamada da ferramenta `Agent`). Por
isso, ao invocar `fast-context` ou `fast-context-deep`, prefixe a `description`
com o nome do agente (ex: `"fast-context: onde fica a lógica de auth?"`) — sem
isso, a linha de status mostra um texto genérico sem indicar qual modelo está rodando.
