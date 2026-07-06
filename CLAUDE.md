# ContextScout

A native reimplementation of the **FastContext** concept (originally
`microsoft/fastcontext`, now unavailable publicly): a subagent dedicated to
exploring a code repository and returning only the relevant excerpt (file +
line range) to the main agent, instead of letting the main agent burn context
doing grep/glob/file reads directly.

Context reference: `transcricao-video-fastcontext.md` (transcript of a video
explaining the original project) and
`docs/ai/reference-implementation-fastcontext.md` (discovery of a Python
reference implementation, cloned at `/mnt/backup/github/fastContextMicrosoft`,
outside this repo).

## Core idea

- Two separate agents: a **scout** (search) and a **resolver** (edits/decides).
- The scout only has 3 tools: file read (with line numbers), glob, and
  grep/regex. It never executes anything.
- The scout runs in isolated context and uses a cheaper model (Haiku) —
  whoever resolves the task uses the more expensive model.
- Scout output: a lean evidence block (file + lines), never the navigation
  history.
- Activation via `.claude/rules/exploration.md` — explicit (naming it in the
  prompt) is more reliable than implicit.

## Revised scope — only what's guaranteed by real evidence

After 7 phases + baseline validation + corrected negative findings, the value
proposition was **deliberately narrowed** to what the tests actually support.
See `docs/ai/risks-and-gaps.md` and `docs/ai/eval/baseline-results-2026-07-06.md`
for the detail behind each item below.

**Guaranteed (tested, reproduced):**
- **Dollar cost** reduction, not token-count reduction — Haiku costs a
  fraction of the main model per token. Token count vs. exploring directly is
  structurally unverifiable on this platform (the Agent tool doesn't expose
  comparable usage); we don't claim "fewer tokens", only "cheaper tokens" when
  delegation happens.
- Main-agent context hygiene: search history (wrong attempts, discarded
  naming conventions) stays isolated in the subagent and never enters the
  expensive model's context.
- Zero over-triggering on the trivial queries tested (baseline Q5/Q6) — the
  activation rule doesn't fire for an already-resolved lookup or pure editing.
- Structured output contract with verbatim citation, validated
  (`validate_citations.py`) against every real citation collected so far.
- Real tool-call cutoff via a `PreToolUse` hook (Layer 2) — doesn't rely only
  on prompt instructions.
- Secret blocking (`.env`, `secrets/**`) tested with synthetic positive and
  negative cases.
- Good answer quality **for pointed, closed questions** (locating a symbol,
  finding a function's definition, mapping 2-4 related files) — 3 of 4 cases
  in the baseline, including context beyond the expected answer.

**Not guaranteed — known risks, unmitigated at the source (use with these
restrictions):**
- **Confidence calibration fails silently**: a `confidence="high"` answer
  about the wrong repository/file has already happened. Mandatory defense:
  always read at least one citation before acting on it
  (`.claude/rules/exploration.md`) — don't trust self-reported `confidence`.
- **Broad, open-ended questions ("describe the whole flow, citing every
  file") blow past the turn limit without closing `<final_answer>`** —
  reproduced 3/3 times, not fixed by prompt tweaks. Don't delegate questions
  in that shape; break them into smaller pointed questions (see
  `exploration.md`).
- Robustness to path/case ambiguity **is not a reliable advantage** of
  `context-scout` over exploring directly — both sides make this mistake
  (revised finding from round 2 after a larger sample).

## Status

**Phases 0-7 implemented and validated in real use** (not just theory/unit
tests — the real subagent invoked repeatedly, including negative findings
fixed along the way). Main components:

- `.claude/agents/context-scout.md` (Haiku) and
  `.claude/agents/context-scout-deep.md` (Sonnet, escalation) — bodies kept
  in sync, only `model:` differs.
- `.claude/rules/exploration.md` — single activation rule, self-check gates,
  escalation (1-hop ceiling), defense in depth, statusLine naming convention.
- `.claude/scripts/limit_turns_hook.py` — real tool-call cutoff (keyed on
  `agent_id`, not `session_id`/`transcript_path` — those leak across
  invocations within the same session, a real bug found and fixed).
- `.claude/scripts/block_secrets_hook.py` + `deny` in `settings.json` —
  blocks `.env`/`secrets/**`.
- `.claude/scripts/statusline.py` / `subagent_statusline.py` — visual
  feedback (dev cost/tokens + live tokens for each running subagent).
- `docs/ai/eval/baseline-queries.md` + `baseline-results-2026-07-06.md` —
  end-to-end validation baseline with a manually-checked answer key.

**Most important finding of the process**: self-reported `confidence` from
the subagent doesn't catch its own mistake (in one baseline query, it
answered with `confidence="high"` about the wrong repository, due to a path
case mix-up) — the real defense is the "read at least one citation before
editing" rule in `exploration.md`, not the model's self-assessment.

Historical reference — context-economy strategy plan: see
`docs/ai/context-economy-strategies.md`.

Architecture decision (Claude only, no external infra, everything native to
Claude Code): see `docs/ai/architecture-decision-native-subagent.md`.

Step-by-step implementation plan, with checklist and findings per phase: see
`docs/ai/implementation-plan.md`. Visual feedback research
(statusLine/subagentStatusLine): see `docs/ai/ui-feedback-statuslines.md`.

Identified risks and gaps (15 total, with mitigation solution or status): see
`docs/ai/risks-and-gaps.md`. Confirmed platform facts (agent schema, the
`maxTurns` bug, statusLine payload, secret protection): see
`docs/ai/claude-code-capabilities-verified.md`. Full history of the go/no-go
decision, including negative findings (silent stall, counter leak, path
error) and how they were fixed: see `docs/ai/go-no-go-analysis.md`.

## Rules

- No secrets/credentials in any committed file.
- `CLAUDE.local.md` and `.claude/settings.local.json` are personal — never
  commit them (see `.gitignore`).
