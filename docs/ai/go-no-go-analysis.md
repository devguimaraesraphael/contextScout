# Go/no-go: vale a pena implementar o plano completo?

Análise crítica feita antes de investir nas Fases 2-7. Conclusão: **não construir o sistema completo especulativamente** — rodar um experimento mínimo primeiro (ver `implementation-plan.md`, Fase 0).

## Achado que muda a conta: o Claude Code já tem um agente `Explore` nativo

Este ambiente já oferece um subagent read-only pronto pra localizar código ("fast read-only search agent for locating code", com granularidade quick/medium/very thorough). Boa parte do "core" que estávamos planejando construir do zero — subagent isolado, read-only, focado em achar código — **já existe de graça**, sem os riscos documentados em `risks-and-gaps.md`. O diferencial real do nosso `fast-context` sobre o `Explore` nativo é estreito: forçar roteamento pra Haiku (controle de custo) + contrato de saída estruturado com `confidence` pra escalonamento calibrado.

## A vantagem de precisão do paper não é gratuita

O ganho de 60,3% de tokens / +5,5 de score reportado pelo paper do FastContext é atribuído ao **modelo treinado via RL** (`FastContext-1.0-4B-RL`), não à arquitetura de delegação isolada. O próprio paper diz que modelos pequenos genéricos (sem esse treino) recuperam arquivos/símbolos com menos precisão — e é exatamente essa configuração (modelo genérico, Haiku) que estamos usando. Expectativa realista: ganho de tokens sim (delegação + modelo mais barato), mas não necessariamente o ganho de precisão/score do paper.

## Tabela de riscos sem solução completa (recapitulada)

| # | Risco | Probabilidade | Impacto se ocorrer | Severidade residual |
|---|---|---|---|---|
| 1 | `maxTurns` não é enforced (bug confirmado, issue #41143) | Alta | Explorador roda além do razoável | Média |
| 2 | Confiança autorrelatada não calibrada | Alta | Escalonamento decide errado | Média-alta |
| 3 | Grounding não garante correção semântica | Média-alta | Edição com base em contexto tecnicamente verificado mas semanticamente errado — falha silenciosa | **Alta** |
| 4 | Teto de escalonamento/kill-switch dependem de obediência do modelo | Média | Ping-pong de escalonamento, dificuldade de desligar | Baixa-média |
| 5 | Duplicação entre `fast-context.md`/`fast-context-deep.md` | Média | Os dois agents divergem sem ninguém notar | Baixa-média |
| 6 | Amostra do harness pequena/um repo só | Certa | Baseline não generaliza | Média |
| 7 | Payload do `subagentStatusLine` não confirmado | Certa até abrir `/hooks` | Fase 6 trava (só cosmético) | Baixa |
| 8 | Re-disparo em follow-up não testado | Média | Delegação desnecessária | Baixa |

## O que o projeto Python original (Cirius1792/fastcontext) resolve — e o que não

| Risco nosso | Original resolve? | Por quê |
|---|---|---|
| #1 Limite de turnos | **Sim, de verdade** | `--max-turns` é corte real no loop Python, não instrução de prompt |
| #2/existência de citação | **Sim, parcialmente** | `os.path.isfile()` valida existência antes de devolver — mas só existência, não relevância |
| #3 Correção semântica | **Não** | Mesma lacuna que a nossa — validação de existência não checa se o trecho responde a pergunta |
| #4/#9 Confiança/escalonamento | **Não existe no original** | Roda um único modelo fixo por execução; nunca tentaram construir escalonamento |
| #10 Duplicação de agents | Não se aplica | É uma única base de código Python, não dois arquivos de agent |
| #13 Vazamento de segredos | **Não** | Só valida path dentro do `work_dir` (path traversal), nenhuma exclusão de `.env`/`secrets/**` |
| Precisão da busca | Sim, mas depende do modelo treinado (`FastContext-1.0-4B-RL`) servido via Ollama — infra local que este projeto decidiu não ter. O suporte a Claude no original é código morto (`llm_api.py` nunca commitado). |

**Conclusão**: portar o projeto Python não compraria a vantagem de precisão sem também assumir a infra rejeitada (servir modelo treinado localmente). As duas ideias dele que valem a pena roubar — validação de existência de citação e corte real de turnos — são portáveis pro nosso design nativo sem precisar do resto.

## Decisão: como roubar as ideias sem violar a arquitetura nativa

- **Validação de citação**: implementada como script determinístico (`validate_citations.py`), rodado pelo **agente principal** (que já tem Bash) depois de receber o `<final_answer>` do `fast-context` — não pelo `fast-context` em si, pra não dar acesso a Bash ao explorador e preservar a restrição estrutural de tools (`Read`/`Grep`/`Glob` só).
- **Corte de turnos**: mantido como auto-contagem comportamental (Camada 1) por agora. O contador via hook (Camada 2) fica pra depois, condicional ao resultado do experimento — se virasse um script, seria invocado pelo próprio hook `PreToolUse`, não pelo `fast-context`.

## Recomendação final

Rodar a **Fase 0 (experimento mínimo)** antes de qualquer coisa das Fases 2-7: `fast-context.md` enxuto (Fase 1 sem escalonamento) + `validate_citations.py`, comparado lado a lado com o agente `Explore` nativo e com o agente principal buscando direto. Só investir nas fases seguintes (escalonamento, hooks, statusline) se o experimento mostrar ganho real de tokens/qualidade sobre essas duas alternativas mais simples.
