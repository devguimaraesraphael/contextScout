# Activation rule — context-scout

Single source of reference for the `context-scout` subagent (kill-switch: delete/rename
`.claude/agents/context-scout.md` disables the mechanism without leaving a broken
reference anywhere else).

## When to use

Only **pointed and closed** questions — tested scope with a good hit rate:

- Locate the definition of a specific symbol/function/class whose file is unknown.
- Find where a specific piece of logic lives, when it spans 2-4 files/modules.
- A closed "how does X work" question about a specific, nameable behavior not visible in the current context.
- Pointed impact analysis ("what breaks if I change Y's signature").

Example: "where's the function that validates the JWT token?" → unknown location, closed scope, delegate.

## When NOT to use

- The relevant file was already read this session.
- It's a single grep in an already-known file.
- It's pure editing, with no exploration needed (exact symbol already visible in the current context).
- The question was already answered in this conversation (a prior citation covers the case).
- **A broad/open-ended question like "describe the whole flow step by step", "explain everything about X", "list every file related to Y"** — confirmed and reproduced risk (3/3) of a turn blowing past its limit without closing `<final_answer>`, not fixable with prompt instructions alone (see `docs/ai/risks-and-gaps.md`, risk #4). If you need that kind of overview, break it into 2-3 sequential pointed questions and delegate each one separately, or explore it yourself.

Example: "rename that variable on the line I just read" → don't delegate, edit directly.
Example: "describe the whole authentication flow carefully, citing every relevant file" → don't delegate as-is; break it into "where does the authentication flow start" + "what happens after X validates the token", each delegated separately.

## Mandatory self-check gate before delegating

Before invoking `context-scout`, ask yourself explicitly:
1. Do I already know the exact file:line for this? If yes, skip delegation.
2. Did I already answer this in this conversation? If yes, reuse the prior citation instead of re-triggering.

## Defense in depth (risk #2 and #3 — mandatory, no exception for confidence)

Before editing or answering the user based on a citation received from
`context-scout`, always do a quick read (Read) of at least one of the citations
to confirm the excerpt exists and matches what's expected — **even when
`confidence="high"`**. Real finding (Phase 7 baseline, Q3): the subagent
answered with `confidence="high"` about the wrong repository — self-reported
confidence doesn't catch its own mistake. Don't skip this check because of high
confidence; that's exactly the case where it failed.

## Model escalation (risk #3, #9, #10)

If `context-scout`'s (Haiku) `<final_answer>` comes back with `confidence` other
than `"high"`, **or** with `files_found` that seems low for the question's scope
(not just when it comes back empty — that's the easy case, not the most
dangerous one), escalate **exactly once** to `context-scout-deep` (same
tools/system prompt, `model: sonnet`) with the original question.

**Failure with no `<final_answer>` at all (found 2026-07-06)**: if `context-scout`'s
response ends in loose reasoning text, with no `<final_answer>` block at all
(e.g. "Turn N/8: I'll check one more thing..." and nothing after), treat this
as equivalent to `confidence="low"` for escalation purposes — **not** as an
empty response to ignore. Confirmed root cause (3/3 reproductions with the same
broad question, even after reinforcing the subagent's instructions twice): the
model announces a next action without executing it in the same response, and
the subagent's loop ends there because there's no tool call. The system prompt
instruction **did not fix it** — treat this as a structural limitation, not
something fixable with better wording alone.

When escalating for this reason, **rephrase the original question more
narrowly** before resending it to `context-scout-deep` (e.g. swap "describe the
whole flow X step by step, citing every file" for a question focused on a
single point in the flow) — broad, open-ended questions ("describe the whole
flow carefully", "citing every relevant file") are the known trigger for this
blowout; closed questions with clear scope haven't shown this pattern in
testing.

Escalation ceiling: at most 1 hop. If `context-scout-deep` also comes back with
`confidence != "high"` (or no `<final_answer>` at all), stop — don't escalate
again, don't repeat. Return the response to the main flow with an explicit
low-confidence warning for the user, instead of insisting on an expensive loop.

## statusLine naming convention (Phase 6)

The `subagentStatusLine` payload doesn't expose the subagent's type/model, only
the `label` (same as the `description` parameter passed to the `Agent` tool
call). So, when invoking `context-scout` or `context-scout-deep`, prefix the
`description` with the agent's name (e.g. `"context-scout: where's the auth
logic?"`) — without this, the status line shows generic text with no
indication of which model is running.
