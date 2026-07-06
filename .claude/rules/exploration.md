# Regra de ativação — fast-context

Única fonte de referência ao subagent `fast-context` (kill-switch: apagar/renomear
`.claude/agents/fast-context.md` desativa o mecanismo sem deixar referência
quebrada em outro lugar).

## Quando usar

Só perguntas **pontuais e fechadas** — escopo testado e com boa taxa de acerto:

- Localizar a definição de um símbolo/função/classe específico cujo arquivo é desconhecido.
- Achar onde uma lógica específica mora, quando ela atravessa 2-4 arquivos/módulos.
- Pergunta fechada tipo "como funciona X" sobre um comportamento específico e nomeável, não visível no contexto atual.
- Análise de impacto pontual ("o que quebra se eu mudar a assinatura de Y").

Exemplo: "onde fica a função que valida o token JWT?" → localização desconhecida, escopo fechado, delega.

## Quando NÃO usar

- O arquivo relevante já foi lido nesta sessão.
- É um grep único num arquivo já conhecido.
- É edição pura, sem exploração (símbolo exato já visível no contexto atual).
- A pergunta já foi respondida nesta conversa (citação anterior cobre o caso).
- **Pergunta ampla/aberta tipo "descreva todo o fluxo passo a passo", "explique tudo sobre X", "liste cada arquivo relacionado a Y"** — risco confirmado e reproduzido (3/3) de estouro de turno sem fechar `<final_answer>`, não corrigível só com instrução no prompt (ver `docs/ai/risks-and-gaps.md`, risco #4). Se precisar desse tipo de visão geral, quebre em 2-3 perguntas pontuais sequenciais e delegue cada uma separadamente, ou explore você mesmo.

Exemplo: "muda o nome dessa variável na linha 42 que acabei de ler" → não delega, edita direto.
Exemplo: "descreva com calma todo o fluxo de autenticação, citando cada arquivo relevante" → não delega assim; quebre em "onde começa o fluxo de autenticação" + "o que acontece depois de X validar o token", cada uma delegada separadamente.

## Gate de auto-checagem obrigatório antes de delegar

Antes de invocar `fast-context`, pergunte-se explicitamente:
1. Eu já sei o arquivo:linha exato pra isso? Se sim, pula a delegação.
2. Eu já respondi isso nesta conversa? Se sim, reusa a citação anterior em vez de re-disparar.

## Defesa em profundidade (risco #2 e #3 — obrigatória, sem exceção por confidence)

Antes de editar ou responder ao usuário em cima de uma citação recebida do
`fast-context`, sempre fazer uma leitura rápida (Read) de pelo menos uma das
citações pra confirmar que o trecho existe e bate com o esperado — **mesmo
quando `confidence="high"`**. Achado real (baseline Fase 7, Q3): o subagent
respondeu com `confidence="high"` sobre o repositório errado — confiança
autorrelatada não pega o próprio erro. Não pular essa checagem por causa de
confiança alta; é exatamente o caso em que ela falhou.

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
