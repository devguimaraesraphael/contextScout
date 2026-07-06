# Resultados do baseline — 2026-07-06

Ver queries e gabarito em `baseline-queries.md`. Rodado nesta sessão, mesmo repositório
de referência (`/mnt/backup/github/fastContextMicrosoft`) usado nas rodadas 1-4.

## Q1-Q4, modo "com delegação" (fast-context real, Haiku)

| Query | confidence | files_found | tool_uses | subagent_tokens | duration | Bateu com o gabarito? |
|---|---|---|---|---|---|---|
| Q1 — limite de turnos | high | 2 | 6 | 11.725 | 24,6s | **Sim** — agent.py:38-76 (inclui a faixa exata do gabarito, 44-54) e cli.py:23, ambos verbatim corretos. |
| Q2 — templating system prompt | high | 4 | 8 | 14.470 | 23,6s | **Sim** — utils.py:11-17, 19-33, 36-53 e ainda foi além do gabarito citando system.md:33-41 (o template em si, não previsto no gabarito mas correto e relevante). |
| Q3 — validação de citações | high | 3 | 11 | 20.857 | 33,4s | **Não — falha real.** Respondeu sobre `/mnt/backup/github/fastContext` (este projeto, `validate_citations.py`) em vez de `/mnt/backup/github/fastContextMicrosoft` (repo de referência, `utils.py:parse_citations`/`format_citations`). Confusão de path por case-sensitivity (`fastContext` vs `fastcontext`), apesar do prompt ter afirmado o path completo e correto. `confidence="high"` **calibrado errado** — reportou alta confiança sobre a resposta errada. |
| Q4 — registro de ferramentas | high | 3 | 11 | 14.443 | 28,8s | **Sim** — agent_factory.py:56-66 (bate exato com o gabarito) mais read.py/glob.py como bônus (não pedido, mas correto e útil). |

## Q1-Q4, modo "sem delegação" (agente principal, direto)

**Ressalva de metodologia**: as citações abaixo reaproveitam a leitura que o agente
principal já fez nesta sessão pra construir o gabarito manual — não é um teste às
ciegas. Reflete, porém, um cenário real: quando o arquivo já foi lido na sessão, a
própria regra em `.claude/rules/exploration.md` diz "não delegar". `tool_uses` marcado
como 0 porque nenhuma tool call nova foi necessária — a resposta veio do contexto já
carregado.

| Query | tool_uses novas | Bateu com o gabarito? |
|---|---|---|
| Q1-Q4 | 0 (reaproveitou leitura anterior) | Sim, as 4 — mas não é comparável 1:1 com o custo de uma primeira exploração fria. |

**Achado**: esse resultado não mede "agente principal explorando do zero vs. `fast-context`" —
mede "agente principal com contexto já quente vs. `fast-context` sem contexto". Pra medir
o cenário realmente comparável (ambos partindo de zero), seria preciso repetir em uma
sessão nova, o que não foi feito aqui por custo/tempo. **Registrado como limitação do
baseline, não como resultado positivo do agente principal.**

## Q5-Q6, modo natural (trivial, não deveria disparar delegação)

| Query | O que o agente principal fez | Delegou indevidamente? |
|---|---|---|
| Q5 — lookup trivial (`--max-turns` tipo/default) | 1 `Bash(grep)` direto, sem subagent. Resposta correta: `type=int`, `default=4`. | **Não** — comportamento correto. |
| Q6 — edição pura (mudar default 4→8) | `Edit` direto sobre a linha já conhecida, sem subagent, sem exploração. Revertido depois (repo de referência é de terceiros, só fixture de teste, não deveria ficar sujo). | **Não** — comportamento correto. |

## Síntese

1. **Zero over-triggering** (risco #1): Q5/Q6 não dispararam delegação indevida — o agente principal reconheceu os dois como "não usar" corretamente.
2. **Achado novo, negativo, o mais importante desta rodada**: o `fast-context` real **também** comete erro de path por case-sensitivity (Q3), não só o `Explore` nativo (achado da rodada 2). Isso contradiz — ou pelo menos reduz a força de — o achado #3 da rodada 2 ("robustez a ambiguidade de path é vantagem do fast-context"): a amostra maior (4 queries novas) mostra que o subagent comete o mesmo tipo de erro, só que com amostra pequena o suficiente pra não ter aparecido antes. **Corrigir o critério de sucesso #3 da Fase 0**: não é "robustez a ambiguidade de path", é "ambos os lados cometem esse erro, então não é uma vantagem confiável do fast-context".
3. **Calibração de confidence (risco #3/#8) falhou no caso que mais importa**: Q3 teve `confidence="high"` numa resposta objetivamente errada (repositório trocado). Alta confiança não pegou o próprio erro — a auto-crítica instruída pro caso `medium`/`low` não se aplica aqui porque o modelo se considerou seguro. **Risco #3 permanece real, não mitigado**: `confidence` autorrelatado não é suficiente pra detectar esse tipo de erro; só uma verificação externa (o "ler ao menos uma citação antes de editar", já na regra de defesa em profundidade) pegaria isso na prática.
4. **3 de 4 queries "deveria disparar" tiveram citação verbatim correta e completa**, muitas vezes indo além do gabarito com contexto adicional relevante (Q2, Q4) — sinal de qualidade que se mantém das rodadas anteriores.
5. **Comparação "main direto vs. fast-context" ficou inconclusiva por desenho do teste** (main já tinha contexto quente) — não é um resultado, é uma lacuna metodológica registrada para não ser mal-interpretada como "main sempre mais barato".

## Ação de acompanhamento sugerida (não implementada nesta rodada)

Dado o achado #2 (falha de path também no `fast-context`), considerar adicionar ao
system prompt do subagent uma instrução explícita: "confirme o path exato do
repositório com um `Glob` ou `Read` do diretório raiz antes de assumir case/nome,
especialmente quando dois diretórios com nomes parecidos possam existir". Não
implementado agora — fica registrado como próximo passo, não como parte do go/no-go.
