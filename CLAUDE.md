# Executive Assistant

A file-based executive assistant / second-brain framework for Claude Code. Markdown notes, a small set of opinionated skills, hooks that nudge good habits, and a wikilink-driven knowledge graph that grows as you use it.

This file is the system prompt Claude Code sees on every session. Edit it to fit your life and your work.

## What this is

A folder of markdown that holds your context (orgs, priorities, goals), your projects, your decisions, and your daily rhythm. A set of skills under `.claude/skills/` that automate the rituals you actually do (morning planning, weekly rollups, drift detection between stated priorities and actual behavior). A few hooks that prevent the system from rotting (log nudges, secret scans, retrieval hints).

Obsidian-compatible so you can browse with a UI when you want, but the source of truth is plain markdown.

## File layout

```
context/         canonical, long-lived knowledge — entities and rhythm files
  orgs/          one folder or file per organization
  priorities.md  this week's dashboard
  goals.md       quarterly goals
projects/        active workstreams, one README per project
decisions/log.md append-only decision log with reasoning
.claude/
  rules/         your preferences, communication style, domain conventions
  skills/        the reusable workflows (see list below)
  hooks/         event-driven scripts (session start, post-write, stop)
  commands/      slash-command aliases for skills
templates/       reusable scaffolds
references/      external SOPs, examples, vendor docs
archives/        dormant content, never deleted
outputs/         generated artifacts (cheatsheets, drafts, reports)
daily/           one file per day (YYYY-MM-DD.md), written by /morning-coffee
weekly/          per-ISO-week rollups, written by /close-week
monthly/         per-calendar-month rollups, written by /close-month
log.md           append-only activity log
docs/superpowers/specs/ design docs for skills you build
docs/superpowers/plans/ implementation plans for skills you build
```

## Memory vs context

Memory is staging. `context/` is canonical. When they disagree, `context/` wins.

| | Auto-memory | `context/` files |
|---|---|---|
| Location | `~/.claude/projects/.../memory/` | repo `context/` |
| Versioned | No | Yes (git) |
| Trust | Point-in-time, can be stale | Canonical |
| Structure | Light frontmatter + prose | Full frontmatter + source citations |
| Write cadence | Automatic during conversations | Intentional, human-in-loop |
| Purpose | Working memory | Long-term reference |

When a memory entry proves stable and important, promote it to `context/` with the `/promote-memory` skill. When a file gets superseded, mark it with `/supersede`.

## Page format

Every content page starts with YAML frontmatter:

```yaml
---
title: Entity Name
type: organization | project | rule | rhythm-file | reference
last_updated: YYYY-MM-DD
sources: [list of sources]
---
```

Body uses Obsidian-compatible `[[wikilinks]]` (resolve by filename, not path). Cite factual claims with `[Source: filename]`. Flag contradictions with `> CONTRADICTION:`. Filenames are `kebab-case.md`. Dates are absolute (`2026-04-13`), never relative (`last week`).

## The skills

- **`/morning-coffee`** — daily kickoff. Reads your calendar(s), runs a two-pass planning dialog, writes tagged events, produces `daily/YYYY-MM-DD.md`.
- **`/close-week`** — weekly rollup at `weekly/YYYY-Www.md` from daily notes, log, decisions, and git.
- **`/close-month`** — monthly rollup at `monthly/YYYY-MM.md`.
- **`/show-priorities`** — regenerates the project dashboard in `priorities.md` from project frontmatter.
- **`/promote-memory`** — stable memory entries get promoted to `context/`.
- **`/supersede`** — mark a file as replaced by a newer canonical version; rewrites all wikilinks pointing at the old slug.
- **`/crystallize`** — distill the current session's primary thread into a structured wiki page.
- **`/graduate`** — promote `#idea` captures from daily notes to canonical pages.
- **`/drift`** — compare stated priorities against actual git + calendar behavior.
- **`/connect`** — bridge two concepts using the knowledge graph.
- **`/trace`** — show how your thinking on a topic has evolved over time.
- **`/graph`** — query the wikilink + frontmatter knowledge graph; per-page confidence buckets.
- **`/lint`** — scan for stale `last_updated`, broken wikilinks, orphan pages, missing frontmatter.
- **`/research`** — recent-web-source research pipeline (last 30 days).
- **`/discord-scrape`** — topic-filtered Discord chatter into a synthesis artifact.

Each skill lives at `.claude/skills/<name>.md`. The slash-command alias is at `.claude/commands/<name>.md`. Skills are flexible — read the source, fork what you need.

## Hooks

- `SessionStart` — `memory-reminder.sh` (nudge to promote memory), `session-start-marker.sh` (mark the session)
- `Stop` — `log-nudge.sh` (blocks the stop if you did repo-modifying work but didn't update `log.md`)
- `PostToolUse Write|Edit` — `secret-scan.sh` (catches API keys, JWTs, PEM blocks before they ship)
- `UserPromptSubmit` — `retrieval-hint.py` (greps the wiki for slug/name matches and injects paths into context)

## Logs

Two logs, distinct roles, never conflated:

- **`log.md`** — activity trail. High volume, automatic. Format: `## [YYYY-MM-DD] action | description`.
- **`decisions/log.md`** — decisions with reasoning. Low volume, curated. Format: `[YYYY-MM-DD] DECISION: ... REASONING: ... CONTEXT: ...`.

## Rules directory

`.claude/rules/*.md` holds your preferences. Three rule files ship with this framework as starting points:

- `communication-style.md` — tone, formatting preferences, draft-reply format
- `proactive-skill-recommendations.md` — when to surface `/crystallize`, `/supersede`, `/promote-memory` inline
- `daily-note-tags.md` — the frozen 5-tag vocabulary (`#idea`, `#decision`, `#blocker`, `#win`, `#followup`) for inline captures in daily notes

Add your own as preferences harden. Rules are binding for anything the user touches.

## Getting started

1. Clone this repo. Rename it to anything.
2. Open in Claude Code (the project root becomes `$CLAUDE_PROJECT_DIR`).
3. Read this file. Edit the file layout, skill list, and rules to match how you work.
4. Fill `context/orgs/`, `context/priorities.md`, `context/goals.md` with your own.
5. Run `/morning-coffee` to start the daily rhythm.

## Skill discipline

A new skill is worth formalizing when:
- You've asked Claude to do the same thing three times
- The workflow is stable
- Saving it as a skill is faster than re-describing it each session

Capture it as `.claude/skills/<name>.md`. Mirror the slash-command at `.claude/commands/<name>.md`. Write a design doc at `docs/superpowers/specs/YYYY-MM-DD-<name>-design.md` and an implementation plan at `docs/superpowers/plans/YYYY-MM-DD-<name>.md` (see the templates in `docs/superpowers/`).

## Maintenance rhythms

- **Every session**: read `priorities.md` and the relevant `projects/*/README.md` at start; log meaningful actions to `log.md`.
- **Weekly**: `/close-week` and sanity-check `priorities.md` matches reality.
- **Monthly**: `/close-month`.
- **Quarterly**: review `goals.md` at quarter boundaries.
- **Ongoing**: when memory hardens, `/promote-memory`. When a file is replaced, `/supersede`.

## Archives rule

Never delete. When content goes dormant, move it to `archives/` with a dated filename. Git is the ultimate backstop, but `archives/` keeps recent-enough content one directory away.
