<div align="center">

# 🔎 ContextScout

**A cheap, isolated search subagent for Claude Code — so your expensive model never burns context on grep/glob/file exploration again.**

[![Built for Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-6366f1?style=flat-square)](https://claude.com/claude-code)
[![Scout model](https://img.shields.io/badge/scout-Haiku-B8701F?style=flat-square)]()
[![Escalation model](https://img.shields.io/badge/escalation-Sonnet-34459A?style=flat-square)]()
[![No infrastructure](https://img.shields.io/badge/infrastructure-none-2ea44f?style=flat-square)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen?style=flat-square)]()

[What it is](#what-it-is) · [Install](#install) · [For non-programmers](#for-non-programmers) · [For programmers](#for-programmers)

</div>

---

## What it is

`ContextScout` is a native reimplementation of the **FastContext** concept
(originally `microsoft/fastcontext`, now unavailable publicly): a subagent
dedicated to exploring a code repository and handing back only the relevant
excerpt — **file + exact line range** — instead of letting the main agent
(the more expensive model) spend its own context doing `grep`/`glob`/file
reads directly.

No servers, no external services, no dependencies to install — it's a set of
text files that Claude Code already knows how to interpret.

| | |
|---|---|
| **Search agent** | `context-scout` — runs on Haiku, has only `Read`/`Grep`/`Glob`, never edits or executes anything |
| **Escalation agent** | `context-scout-deep` — same body, Sonnet, used at most once when confidence is low |
| **Output contract** | Verbatim citation (`file:line`) + self-reported confidence, never a loose summary |
| **Defense in depth** | Real tool-call cutoff via hook, secret-file blocking, mandatory citation spot-check before acting |
| **Cost model** | Delegated search runs on a cheaper model — savings in **dollars**, not a token-count claim |

---

## Install

No program to download, no account to create — it's a single folder.

```bash
cp -r .claude /path/to/your/project/
```

Already have a `.claude/` folder in the target project? **Don't overwrite
it** — merge the `agents/`, `rules/`, `scripts/`, and `settings.json`
contents by hand (see [For programmers](#for-programmers)).

Restart the Claude Code session afterwards — subagents and rules are only
picked up on a new session.

---

## For non-programmers

### In one sentence

A cheap, fast search intern who scouts the code before the expensive
assistant has to do it itself — and only hands back the exact page, already
highlighted.

### How to install

No terminal commands needed — just three steps:

1. **Download this repository** — click the green **Code** button at the top
   of this page, then **Download ZIP**, and unzip it anywhere on your
   computer.
2. **Copy the `.claude` folder** from inside the unzipped folder into the
   root folder of your own project (the same place where your project's
   other files live).
3. **Open (or restart) Claude Code in your project** and start using it
   normally — ContextScout is now active in the background.

Already have a `.claude` folder in your project? Don't overwrite it — ask a
programmer on your team to merge the two (see
[For programmers](#for-programmers)).

### How to use it

You don't need to learn a special way of asking — just ask your question
naturally. Two ways it triggers:

- **Automatic** — the main assistant decides on its own whether the question
  is worth delegating.
- **Explicit** (more reliable) — ask by naming it: *"use context-scout to
  find where X is."*

Noticing whether a question is too broad and needs to be split into smaller
pieces is the main assistant's job, not yours.

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

Activation is orchestrated by `.claude/rules/exploration.md`: when to
delegate, when not to, the self-check gate before delegating, defense in
depth (verify a citation before acting even with `confidence="high"`), the
escalation rule, and the `subagentStatusLine` naming convention.

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

### Installation (detail)

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

Summarized in `CLAUDE.md` ("Revised scope"). The evidence behind each claim
(baseline results, the 15 identified risks with mitigation status, full
go/no-go decision history, confirmed platform facts) lives under `docs/ai/`
locally — that folder is intentionally **not versioned** (see
`.gitignore`), so it won't appear if you're browsing this repo on GitHub.

### Kill-switch

Deleting or renaming `.claude/agents/context-scout.md` disables the
mechanism without leaving a broken reference anywhere else — every reference
to the subagent is concentrated in `.claude/rules/exploration.md`.

### Repository rules

- No secrets/credentials in any committed file.
- `CLAUDE.local.md` and `.claude/settings.local.json` are personal — never
  commit them (see `.gitignore`).

---

<div align="center">

Suggested GitHub topics: `claude-code` `subagent` `ai-agents` `context-engineering` `llm-tooling`

</div>
