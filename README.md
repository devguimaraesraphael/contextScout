# ContextScout

A Claude Code subagent that explores a code repository and returns only the
relevant excerpt (file + lines) to the main assistant — instead of letting
the main assistant (the more expensive model) burn context doing
grep/glob/file reads directly.
 

---

## For non-programmers

### In one sentence

A cheap, fast search intern who scouts the code before the expensive
assistant has to do it itself — and only hands back the exact page, already
highlighted.

### How to install

No program to download, no account to create. Just copy one folder.

1. Copy the whole **`.claude/`** folder from this project into the root
   folder of your project (wherever you already use Claude Code).
2. If your project already has its own `.claude/` folder, copy file by file
   instead of overwriting the whole folder (ask a programmer on your team to
   do this part — see the section below).
3. Close and reopen the Claude Code session in your project.

Done — the scout is now available.

### How to use it

You don't need to learn a special way of asking. Just ask your question
naturally, your own way. Two ways to trigger it:

- **Automatic**: the main assistant decides on its own whether it's worth
  calling the scout, based on the question.
- **Explicit** (more reliable): ask by naming it — *"use context-scout to
  find where X is"*.

Noticing whether a question is too broad and needs to be split into smaller
pieces is the main assistant's responsibility, not yours.

### Full visual guide

A guide with a flow diagram, question examples, and the honest list of what
you can trust vs. what needs care is available as an interactive artifact —
see the link at the top of this README, or ask Claude Code to "create an
artifact explaining ContextScout for non-programmers" to generate a new one.

---

## For programmers

### Architecture

Two native Claude Code agents, not two separate processes:

- **`context-scout`** (`model: haiku`) — the scout. Only has access to
  `Read`, `Grep`, `Glob`. Never edits, never executes. Runs in isolated
  context.
- **`context-scout-deep`** (`model: sonnet`) — same body/system prompt, used
  only as escalation when `context-scout` returns `confidence != "high"`
  (1-hop ceiling). **Body kept identical to `context-scout.md`, except the
  `model` field** — edit one, edit the other.

Activation orchestrated by `.claude/rules/exploration.md`: when to delegate,
when not to, self-check gate before delegating, defense in depth (verify a
citation before acting even with `confidence="high"`), escalation rule, and
the `subagentStatusLine` naming convention.

### File inventory

| File | Role |
|---|---|
| `.claude/agents/context-scout.md` | Scout definition (Haiku), structured output contract (`<final_answer>`), turn control. |
| `.claude/agents/context-scout-deep.md` | Escalation variant (Sonnet). |
| `.claude/rules/exploration.md` | Single source of truth for the activation/usage rule — the kill-switch is documented there. |
| `.claude/scripts/limit_turns_hook.py` | `PreToolUse` hook (scoped in `context-scout.md`'s frontmatter) that denies the 11th `Read\|Grep\|Glob` call per subagent invocation. Counting key: `agent_id` — don't use `session_id`/`transcript_path`, which leak across invocations in the same session. |
| `.claude/scripts/block_secrets_hook.py` | Global `PreToolUse` hook (`settings.json`), blocks reading/commands against `.env`, `.env.*`, `secrets/**`. |
| `.claude/scripts/validate_citations.py` | Deterministic script, **run by the main agent** (not the subagent) after receiving the `<final_answer>` — checks `os.path.isfile()` for each citation. Not called automatically by a hook; it's a manual/scripted check for when you want to validate a batch of answers. |
| `.claude/scripts/statusline.py` | Main agent's `statusLine` (cost, context, cache). |
| `.claude/scripts/subagent_statusline.py` | `subagentStatusLine` — one line per `running` subagent, with `label` + live tokens. |
| `.claude/settings.json` | Wires up the hooks above + `statusLine`/`subagentStatusLine` + secret `deny` rules. **Committed** — part of the feature, not a personal preference. |

### Installation

```bash
cp -r /mnt/backup/github/ContextScout/.claude /path/to/your/project/
```

If the destination project already has its own `.claude/settings.json`,
**don't overwrite it — merge manually** the `hooks`, `statusLine`,
`subagentStatusLine`, and `permissions.deny` blocks, since `settings.json` is
a single object per project.

Project subagents (`.claude/agents/*.md`) are only reloaded in a new session
— editing/copying mid-session has no effect until you restart.

### Guaranteed vs. non-guaranteed scope

See `CLAUDE.md` (section "Revised scope") for the summary, and the documents
below for the detail with evidence:

- `docs/ai/eval/baseline-results-2026-07-06.md` — end-to-end validation
  baseline.
- `docs/ai/risks-and-gaps.md` — 15 identified risks, with mitigation status
  (two remain unmitigated at the source: confidence calibration and turn
  blowout on broad questions — both contained via the usage rule in
  `exploration.md`, not fixed in the subagent itself).
- `docs/ai/go-no-go-analysis.md` — full decision history, including negative
  findings and how each was handled (or not).
- `docs/ai/claude-code-capabilities-verified.md` — confirmed platform facts
  (agent schema, the `maxTurns` bug, statusLine payload).

### Kill-switch

Deleting or renaming `.claude/agents/context-scout.md` disables the
mechanism without leaving a broken reference anywhere else — every reference
to the subagent is concentrated in `.claude/rules/exploration.md`.

### Repository rules

- No secrets/credentials in any committed file.
- `CLAUDE.local.md` and `.claude/settings.local.json` are personal — never
  commit them (see `.gitignore`).
