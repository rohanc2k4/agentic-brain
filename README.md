# Agentic Brain

A file-based second brain for [Claude Code](https://claude.com/claude-code).

Markdown notes, opinionated skills, hooks that nudge good habits, and a wikilink-driven knowledge graph that grows as you use it. Obsidian-compatible so you can browse with a UI when you want, but the source of truth is plain markdown on your filesystem.

Everything in this repo is here on purpose. Read on.

---

## How it became an Agentic Brain

This started as a study wiki for finals.

In April 2026 I was a CS senior at the University of Maryland, halfway through a Software Infrastructure internship, building a side project on the side, and taking three classes. The standard answer to that load is "pick one, let the others coast." I didn't want to pick one. So I started keeping all of it in a single markdown vault and pointing Claude Code at the vault.

The first version was small. A folder of pages for parallel computing exam prep. Each page had frontmatter (title, type, sources, last_updated), wikilinks to other pages, and citations to where the facts came from. The bet was that if I treated my own notes the way Wikipedia treats articles, with strict provenance and cross-references, an LLM could actually be useful on top of them instead of hallucinating around them.

Andrej Karpathy tweeted around that time about using Obsidian and Claude Code together as an LLM-native wiki stack of `.md` files. That confirmed the direction.

Within a week the wiki had grown beyond exam prep. It now held the projects I was leading, the study material I kept ingesting for new classes, and the open-source projects I was building on the side, including [Sanji](https://sanji.dev), a localhost replacement for NotebookLM. I added a `priorities.md` to track what was active, a `decisions/log.md` to capture choices with reasoning, and a `daily/` folder for daily notes. The wiki was now a second brain.

Within a month it was running my life. I added a `morning-coffee` skill that read my Google Calendar, ran a two-pass planning dialog with me, and packed the day. I added `close-week` and `close-month` skills that rolled up tagged inline captures from daily notes into weekly and monthly summaries. I added a `drift` skill that compared what I said I was working on in `priorities.md` against what my git history and calendar actually showed me doing. The system stopped being something I used. It was a rhythm I lived inside.

The skills kept compounding. `crystallize` distilled a session's primary thread into a wiki page. `supersede` marked old pages as replaced by newer canonical ones and rewrote every wikilink that pointed at the old slug. `promote-memory` graduated stable observations from Claude's auto-memory into versioned, citable context files. `graph` queried the knowledge graph for inbound and outbound edges and reported per-page confidence based on source count, recency, and contradictions.

This repo is the framework that resulted, scrubbed of my personal data and shipped for anyone to fork. It's opinionated. Most of those opinions came out of getting something wrong the first time and only fixing it on the third or fourth pass.

---

## What's in here

```
.claude/skills/       15 workflows you can /invoke as slash commands
.claude/commands/     slash-command aliases mirroring the skills
.claude/hooks/        session-start, post-write, stop, and prompt hooks
.claude/rules/        three preference files you should edit
.claude/settings.json hook wiring
templates/            scaffolds (session summaries, etc.)
docs/superpowers/     spec and plan templates for designing new skills
references/sops/      external setup notes (vendor docs, integrations)
CLAUDE.md             the system prompt Claude Code sees each session
README.md             this file
```

What's NOT in here, because it's yours to create:

```
context/              your canonical knowledge: orgs, priorities, goals
projects/             one folder per active workstream
decisions/log.md      decisions with reasoning (curated)
daily/                one daily note per day
weekly/               weekly rollups produced by /close-week
monthly/              monthly rollups produced by /close-month
archives/             dormant content; never deleted
outputs/              generated artifacts (cheatsheets, drafts, reports)
log.md                activity trail (auto-written by hooks + skills)
```

These directories are in `.gitignore` by default so your personal content stays out of forks. Create them when you start using the framework.

---

## Philosophy

A few non-negotiables that the rest of the system is built on.

### 1. Memory is staging. `context/` is canonical.

Claude Code writes to an automatic memory directory during conversations. That memory is point-in-time, can be wrong, isn't versioned, and isn't trusted. It's a working capture.

`context/` is the opposite. Files there are curated, versioned in git, written with full frontmatter and source citations, and trusted on the next read. When memory and `context/` disagree, `context/` wins.

When a memory entry proves stable and important over multiple conversations, you run `/promote-memory`. It scans the memory dir for unsuperseded entries, proposes a `context/` destination based on topic, drafts the new file, shows a diff, and on approval chains into `/supersede` to mark the memory entry as replaced. The memory entry stays in place with a banner pointing at the new canonical file. Nothing disappears.

### 2. Nothing gets deleted. Things get superseded.

Six months from now you will want to know why you made a decision, what an old project was called before the rename, or what the wiki said about something before you updated it. Git history is the ultimate backstop, but going through git log to recover a deleted file is friction.

So this framework's rule: when content goes dormant, move it to `archives/` with a dated filename. When a file is replaced by a newer canonical version, run `/supersede <old> <new>`. The skill moves the old file to `archives/`, edits frontmatter on both ends (`superseded_by:` / `superseded_on:` on the old file, `supersedes:` on the new), prepends a deprecation banner to the old file's body, and rewrites every `[[wikilink]]` in the live tree that pointed at the old slug. Backward references stay intact. Forward references move forward.

The result is that the knowledge graph never has dangling links and you can always trace back to what something used to be.

### 3. Two logs, distinct roles, never conflated.

- **`log.md`** is the activity trail. High volume. Auto-written. Format: `## [YYYY-MM-DD] action | description`. Actions are limited to `ingest`, `query`, `lint`, `update`. A stop hook (`log-nudge.sh`) blocks Claude's stop event if the session did repo-modifying work but `log.md` wasn't touched. The nudge prompts you for the entry; once written, it clears.

- **`decisions/log.md`** is the curated decision register. Low volume. Manual. Format: `[YYYY-MM-DD] DECISION: ... REASONING: ... CONTEXT: ...`. You write here only when a real decision lands, especially ones with career, financial, architecture, or process weight.

Activity belongs in one log. Decisions with reasoning belong in the other. Mixing them dilutes both.

### 4. Skills only when stable.

A new skill is worth formalizing when:
- You've asked Claude to do the same thing three times.
- The workflow has settled.
- Capturing it as a skill is faster than re-describing it each session.

Until then, do it conversationally. Most one-off tasks don't need a skill.

When a skill IS worth building, the flow is: brainstorm → spec → plan → implement. Spec lives at `docs/superpowers/specs/YYYY-MM-DD-<name>-design.md`. Plan lives at `docs/superpowers/plans/YYYY-MM-DD-<name>.md`. The repo ships template versions of both at `EXAMPLE-spec-template.md` and `EXAMPLE-plan-template.md`.

### 5. Every page has frontmatter.

```yaml
---
title: Entity Name
type: organization | project | rule | rhythm-file | reference
last_updated: YYYY-MM-DD
sources: [list of sources]
---
```

Project READMEs use a richer frontmatter with `status`, `priority`, `domain`, `assigned`, `deadline`, `blockers`. The `show-priorities` skill reads these fields to regenerate the project dashboard in `priorities.md`. If the frontmatter is missing or stale, the dashboard goes stale with it. Frontmatter discipline is the price of dashboard reliability.

In the body, cross-reference with `[[wikilinks]]` (Obsidian-compatible, resolve by filename not path). Cite factual claims with `[Source: filename]`. Flag contradictions with `> CONTRADICTION: old vs new from source`. Dates are absolute (`2026-04-13`), never relative (`last week`).

---

## The Skills

Each skill lives at `.claude/skills/<name>.md` with a slash-command mirror at `.claude/commands/<name>.md`. The skill prompt explains what the skill does, when to use it, and the exact procedure Claude should follow. Forks are encouraged. The descriptions below are framework-level summaries.

### `/morning-coffee`: daily kickoff ritual

Reads your fixed events from both Google calendars for today, runs a two-pass dialog (must-dos then nice-to-haves), packs the day into time blocks with explicit packing rules, writes tagged events back to your personal calendar with consistent color coding, and produces `daily/YYYY-MM-DD.md`. The daily note is the canvas for inline captures (`#idea`, `#decision`, `#blocker`, `#win`, `#followup`) that the weekly and monthly skills aggregate later.

If you're going to use one skill, use this one. The rest of the system feeds off the daily notes it produces.

### `/close-week`: weekly rollup

Produces `weekly/YYYY-Www.md`. Reads the seven daily notes for the ISO week, `log.md`, `decisions/log.md`, and git commits within the window. Aggregates tagged captures from daily notes into structured sections. Drafts a narrative summary. Diff-and-approve gate. Default argument is the current ISO week; accepts `YYYY-Www` to close any week retroactively.

### `/close-month`: monthly rollup

Produces `monthly/YYYY-MM.md`. Hybrid source: narrative sections aggregate from the weekly rollups (canonical), tag sections re-read daily notes directly (mechanical grep). The two-pass approach is deliberate. Weekly rollups have already been edited by you, so trusting them for narrative is safe. Tag aggregation hits the raw daily notes to avoid drift.

### `/show-priorities`: regenerate the project dashboard

Walks `projects/**/README.md`, reads frontmatter `priority`, `domain`, `deadline`, `blockers`, bins projects by priority bucket, renders a markdown dashboard, diffs against the auto-zone in `context/priorities.md` (between `<!-- show-priorities:start -->` and `<!-- show-priorities:end -->`), and writes on approval. Nothing outside the auto-zone is touched.

Run this weekly. It keeps the dashboard honest with zero manual effort.

### `/promote-memory`: graduate memory to context

Scans the Claude auto-memory directory for unsuperseded entries, judges which ones are stable and worth promoting, proposes `context/` destinations, walks through each with either a drafted file (for short prose) or a manual-merge prompt (for long prose or existing-file merges), and chains into `/supersede --pre-approved` to finalize. A session-start hook prints a one-line reminder when three or more candidates are pending.

### `/supersede`: mark a file as replaced

`/supersede <old> <new>`. Moves the old file to `archives/`. Edits frontmatter on both ends (`superseded_by:` and `superseded_on:` on old, `supersedes:` on new). Prepends a warning banner to the old file's body. Rewrites every `[[wikilink]]` in the live tree that pointed at the old slug. Memory entries stay in place with just the frontmatter edit. Diff-and-approve gate. Workflows can pass `--pre-approved` to skip the gate.

The most-used maintenance skill in the framework. Run it every time you write a new canonical file that replaces something old.

### `/crystallize`: distill a session into a wiki page

Reads the current session's primary thread (research, design dive, debugging, decision-making) and drafts a structured wiki page under `context/`, `references/`, or `projects/*/pages/`. Includes frontmatter, summary, and citations. Shows a diff. On approval, writes the file and adds a wikilink to the relevant index page. Explicit-invocation only; the framework deliberately does not auto-crystallize.

### `/graduate`: promote tagged captures to canonical pages

Scans recent daily notes for `#idea` captures, clusters them by theme, proposes canonical-page destinations, drafts each page, shows a diff, and chains into `/crystallize --pre-approved` to finalize. Closes the inline-capture → canonical-page loop so that good ideas you scribbled at 7am don't rot at the bottom of a daily note.

### `/drift`: compare stated intentions vs actual behavior

Reads `priorities.md` and `goals.md` for what you said you were focused on. Reads `log.md`, `decisions/log.md`, git commits, calendar events, and daily-note tags for what you actually did. Produces a "say vs do" table over a configurable window (default: last 7 days). Identifies divergence. Optionally proposes edits to `priorities.md` behind a separate approval gate.

The most useful skill on a Friday afternoon. Tells you whether you spent the week on the thing you said was important.

### `/connect`: bridge two concepts via the graph

`/connect <a> <b>`. Walks the knowledge graph neighborhoods at depth two from both endpoints, synthesizes shared themes and implicit connections, outputs a structured "bridges" report with citations. Read-only by default; optional save to `outputs/`. Useful when you suspect two things in your wiki are related but haven't worked out how.

### `/trace`: show how your thinking on a topic has evolved

`/trace <topic>`. Walks git history for the topic's pages, `decisions/log.md` entries that touched it, `log.md` mentions, and frontmatter `last_updated` timestamps. Produces a dated timeline with phase headers. Read-only by default; optional save to `outputs/`. The introspection skill: useful before a major decision or quarterly review.

### `/graph`: query the knowledge graph

Subcommands:
- `list`: every node in the graph
- `node <name>`: node details, frontmatter, all edges
- `inbound <name>`: pages that link TO this node
- `outbound <name>`: pages this node links FROM
- `around <name>`: neighborhood at depth 2
- `low-confidence`: pages with weak provenance (few sources, stale, no inbound)
- `broken`: wikilinks pointing at nonexistent files
- `export`: full graph as JSON for external tooling

Confidence is bucketed `{high, medium, low, n/a}` per page based on source count, recency, contradictions, and inbound edge count. Low-confidence pages also appear automatically in `/lint` reports.

### `/lint`: scan for rot

Walks `context/`, `projects/`, `outputs/`. Reports:
- Stale `last_updated` (older than N days, configurable)
- Broken wikilinks (filename-stem resolution AND folder-name fallback via `index.md` / `README.md`)
- Orphan pages (no inbound links)
- Pages missing required frontmatter fields

Writes a dated report to `outputs/lint-report-YYYY-MM-DD.md`. Cron-schedule it weekly if you want passive rot detection.

### `/research`: last-30-days web research pipeline

`/research <query>`. Pulls recent web sources (filtered to the last 30 days), gathers cross-source evidence, synthesizes findings, cites every claim. Output goes to `outputs/`. Useful for "what's the current state of X" questions where your training data is stale.

### `/discord-scrape`: topic-filtered Discord scrape

`/discord-scrape <source> "<topic>" [--refresh]`. Pulls topic-filtered messages from a registered Discord source using DiscordChatExporter, maintains an incremental local archive outside the repo, synthesizes a markdown research artifact in `outputs/`. Registered sources live in `.claude/skills/discord-scrape/servers.yaml` (ship empty; you fill in server IDs and channel IDs for the servers you participate in). Bash helper at `.claude/skills/discord-scrape/scrape.sh`.

Note: Discord ToS prohibits self-botting. Realistic ban risk is low for read-only exports at low volume but the risk is real. Keep invocations modest. Never commit your Discord token.

---

## The Hooks

Hooks live at `.claude/hooks/` and are wired in `.claude/settings.json`. They run automatically on Claude Code events. The framework ships four hook events with seven hook scripts.

### `SessionStart`

- `memory-reminder.sh`: prints a one-line reminder at session start if three or more unsuperseded memory entries are pending promotion. Prevents memory dir bloat. The threshold is intentional: under three, the nudge would be noisy; at three or more, it's a real signal.
- `session-start-marker.sh`: writes a session marker file so other hooks know a fresh session started. Used by the log-nudge hook to scope its check to the current session only.

### `Stop`

- `log-nudge.sh`: BLOCKING. If the session did repo-modifying work (Edit/Write/Bash) but `log.md` wasn't touched, the hook blocks Claude's stop event and prompts for the entry. Once you write the log line, the nudge clears. This is the discipline mechanism that makes `log.md` actually trustworthy as an activity trail.

### `PostToolUse Write|Edit`

- `secret-scan.sh`: scans every written file for API keys, JWTs, PEM-format private keys, and AWS access keys. If a hit is found, the hook BLOCKS the write and reports the line. Cheap insurance against committing a secret. The patterns are conservative; tune them in the script itself.

### `UserPromptSubmit`

- `retrieval-hint.py` + `retrieval-hint.sh`: on every user prompt, the Python script greps the wiki for slug and name matches against the prompt content and injects matching paths into Claude's context as "possibly relevant wiki pages." A light alternative to full vector retrieval. Costs nothing per session, surfaces relevant pages you forgot you'd written.

### `test-secret-scan.sh`

Smoke test for `secret-scan.sh`. Run manually to verify the secret patterns still catch what they should.

---

## The Rules

`.claude/rules/*.md` holds your preferences. Three rule files ship with the framework as starting points. Each one is binding for Claude in your sessions. Edit them freely. Add your own as preferences harden.

### `communication-style.md`

Defines:
- Default tone for internal vs external messages
- Pet peeves (em dashes, AI-slop vocabulary, hollow intensifiers, formulaic openings)
- The Tier-1 and Tier-2 vocab list to avoid
- The "draft replies in a plain-text code block" rule for copy-paste safety
- When to use bullets vs paragraphs vs tables

This file is where you teach Claude to sound like you. Read it once, edit it as you go.

### `proactive-skill-recommendations.md`

Defines:
- When Claude should suggest `/crystallize` inline (substantive thread with durable conclusions)
- When Claude should suggest `/supersede` inline (new canonical file overlaps with old)
- When Claude should suggest `/promote-memory` inline (memory hardens through repetition)

The rule prevents two failure modes: false positives (suggesting `/crystallize` on every short answer) and false negatives (never suggesting it and letting the wiki decay). The middle path is judgment-driven inline suggestions, one per trigger.

### `daily-note-tags.md`

Defines the frozen five-tag vocabulary for inline captures in daily notes:

- `#idea`: a thought worth potentially graduating to a canonical page later
- `#decision`: a decision made today; pair with `decisions/log.md` if weighty
- `#blocker`: something blocking progress right now
- `#win`: a notable accomplishment worth remembering
- `#followup`: a thread to pick up later

Includes the strict matching regex (tags only at line start, optionally after a list marker, exact case) and explains why loose matching would erode rollup trust. Adding a sixth tag requires an explicit edit to this file and a bump to the regex in `/close-week` and `/close-month`.

Five is enough. Vocabs rot when they grow.

---

## Workflow Lifecycle

What happens in a typical week if you use this framework as designed.

### Every morning

`/morning-coffee` reads your calendars, you triage must-dos and nice-to-haves, the skill packs your day, writes events to your personal calendar, and produces today's daily note. As things happen during the day, you write inline captures in the daily note with the five-tag vocabulary.

### Every session

Read `context/priorities.md` and the relevant `projects/*/README.md` at session start. Log meaningful actions to `log.md` as they happen (the stop hook will nudge you if you forget). Update `last_updated` on any file you touch.

### Friday afternoon

`/close-week` aggregates the week's daily notes, log, decisions, and git commits into `weekly/YYYY-Www.md`. `/drift` reports whether you actually did what you said you'd do. `/lint` reports rot. `/show-priorities` regenerates the dashboard.

### Last day of the month

`/close-month` produces the monthly rollup from the weekly rollups plus a fresh tag re-read of the daily notes.

### Quarterly

Review `context/goals.md` at quarter boundaries. Move done goals to a completed section. Adjust targets that missed. Log substantive changes in `decisions/log.md`.

### Continuously

When memory hardens, `/promote-memory`. When a file is replaced, `/supersede`. When a session produces a wiki-worthy thread, `/crystallize`. When daily notes accumulate good `#idea` captures, `/graduate`.

---

## The Specs and Plans Workflow

When you decide to build a new skill, the framework wants you to write it down before you write the code. The flow:

1. **Brainstorm** the design conversationally with Claude. Resist the urge to start coding.
2. **Write the spec** at `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. The spec answers *what and why*. Use `EXAMPLE-spec-template.md` as a starting structure.
3. **Self-review the spec** for placeholders, internal consistency, scope, and ambiguity. Fix inline.
4. **Get a human review** of the spec before implementation. Iterate if requested.
5. **Write the plan** at `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`. The plan answers *how, in order*. Use `EXAMPLE-plan-template.md` as a starting structure.
6. **Execute the plan** task by task. Each task gets verified and acceptance-checked before moving to the next.
7. **Update the skill list** in `CLAUDE.md` and `README.md` so the new skill is discoverable.

This is overkill for trivial changes. It's the right weight for new skills. The discipline is the point: you don't get to build the skill until the spec exists, and you don't get to implement until the plan exists. It catches scope creep early and keeps future-you from wondering why something was built a certain way.

---

## Getting Started

```bash
git clone https://github.com/rohanc2k4/agentic-brain.git
cd agentic-brain
```

Open the repo in Claude Code. Then:

1. Read `CLAUDE.md` end to end. It's the system prompt for your sessions, and you'll edit it as you make the framework yours.
2. Edit `.claude/rules/communication-style.md` to your tone preferences.
3. Create `context/` and fill in your orgs, priorities, and goals.
4. Create `projects/` and write one README per active workstream with the project frontmatter.
5. Run `/morning-coffee` to start the daily rhythm.
6. Let the skills compound. Most of them stay quiet until they're useful.

---

## Inspired by

Andrej Karpathy's tweet on using Obsidian and Claude Code as an LLM-native wiki stack of `.md` files. The framework that grew from that tweet is what you're reading.

## License

MIT.
