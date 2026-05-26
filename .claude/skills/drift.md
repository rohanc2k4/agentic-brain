---
name: drift
description: Compare stated intentions (priorities.md, goals.md) against actual behavior (log.md, decisions/log.md, git commits, calendar events, daily-note tags) over a configurable window. Surfaces divergence; optionally proposes edits to priorities.md.
---

# drift

Compare what the user says is important (stated intent) against what they actually spent time on (real activity) over a configurable window. Output is a structured "say vs do" report with a divergence narrative and optional proposed edits to `priorities.md`. Read-only by default.

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 2.4. Follow this skill exactly.

## Prerequisites you assume

- `context/priorities.md` and `context/goals.md` exist as the source of stated intent.
- `log.md` and `decisions/log.md` exist as the source of truth for actual activity.
- `git` is available for commit signals.
- Google Calendar MCP is authenticated (for `list-events` signals). If not, skip the calendar signal and note the gap.

## Inputs you read

1. `context/priorities.md` — every bullet under `## This week`, `## This month`, `## Parked`, `## Not a priority right now`, and the auto-generated `## Project dashboard`.
2. `context/goals.md` — every goal across the quarterly buckets.
3. `log.md` — action lines dated inside the window.
4. `decisions/log.md` — entries dated inside the window.
5. `git log --since=<start> --until=<end>` across the repo, plus (optionally) any known work repos if locally cloned.
6. Google Calendar events across the window, both `personal` and `work` accounts.
7. Daily-note tag captures (`#win`, `#blocker`, `#followup`) inside the window — signals of what actually happened and what stalled.

## Outputs you write

Read-only by default. Print the drift report to the terminal. Two optional writes, each behind a separate approval gate:

1. Save the report to `outputs/drift-YYYY-MM-DD.md`.
2. Propose edits to `context/priorities.md` based on drift findings (move items between buckets, add items the user is actually doing, etc.).

## Invocation

- `/drift` — default 30-day window.
- `/drift --days 60` or `/drift --days 90` — longer windows.
- `/drift --since 2026-04-01` — from a specific date.

## Execution sequence

### Phase 1: Resolve the window

Default `start` = today minus 30 days. `end` = today. Print: `Drift window: <start> to <end> (<N> days).`

### Phase 2: Extract stated intent

Parse `priorities.md` into a structured list:

- `this_week`: bulleted items under `## This week`.
- `this_month`: under `## This month`.
- `parked`: under `## Parked`.
- `not_priority`: under `## Not a priority right now`.
- `project_dashboard`: auto-zone items with their bucket.

Parse `goals.md` into grouped goals by domain.

For each item, extract a short canonical name plus keywords useful for matching against activity.

### Phase 3: Extract actual activity

For each signal source, collect events inside the window and tag each event with which priority/goal it most plausibly belongs to (or "unattributed"):

- **`log.md`.** Each action line with its date + description. Match against priority keywords.
- **`decisions/log.md`.** Each entry is a high-signal activity event.
- **Git commits.** `git log --pretty=format:'%h %ad %s' --date=short --since=<start> --until=<end>`. Match subjects against priority keywords.
- **Calendar events.** Events from both accounts. Title + description matched against priorities. Filter out standing recurring events that carry no signal (lunch, social time, etc.) — use a small denylist of title patterns.
- **Daily-note tags.** `#win` and `#blocker` captures, with the priority they touch on.

### Phase 4: Build the say-vs-do table

For each priority and goal, compute:

- **Stated:** is this in priorities.md or goals.md? Which bucket?
- **Touched:** count of activity events matched to this item.
- **Last touched:** most recent activity event date, or "never in window."
- **Bucket drift:** is the stated bucket consistent with the actual touch pattern? Examples:
  - In `## This week` but zero activity in 7 days → drift.
  - In `## Parked` but multiple activity events → drift (should be active).
  - In `## Not a priority right now` but showing up in commits → drift.
  - In `## This week` with heavy activity → consistent (no drift).

Also compute the inverse: **unattributed activity.** Events that don't match any stated priority or goal. High unattributed count = you're spending time on things you haven't articulated as priorities.

### Phase 5: Format the report

Print to the terminal:

```
# Drift report — <start> to <end>

## Say vs do

| Priority | Stated bucket | Touches | Last touched | Drift |
|---|---|---|---|---|
| <name> | this week | 12 | 2026-04-24 | none |
| <name> | this week | 0 | never | ⚠ avoidance |
| <name> | parked | 8 | 2026-04-22 | ⚠ should be active |
| ... | | | | |

## Unattributed activity

<top 5 themes of activity that don't match any stated priority, each with event counts and example citations>

## Divergence narrative

<2-4 paragraphs calling out the most significant drift patterns. What you said you'd do but didn't. What you're doing but haven't claimed. What's in the wrong bucket.>

## Proposed priorities.md edits

<numbered list of specific edits: move X to parked; promote Y to this week; add Z as a new item; etc.>
```

### Phase 6: Offer to save and optionally apply

Two separate approval gates:

**Gate 1.** "Save this report to `outputs/drift-YYYY-MM-DD.md`?" If yes, write it with standard reference frontmatter.

**Gate 2.** "Apply the proposed edits to `context/priorities.md`?" If yes, show a unified diff of the priorities.md changes. Only the hand-written sections (`## This week`, `## This month`, etc.) are edited — never the `## Project dashboard` auto-zone, which is `show-priorities` territory. On approval, Edit the file. If no, print "Proposed edits not applied; run `/show-priorities` manually when ready."

Either way, append one line to `log.md`:

```
## [YYYY-MM-DD] query | drift: <window> (<N> drift flags, <M> unattributed themes, saved=<yes|no>, applied=<yes|no>)
```

## Behavior notes

- **Read-heavy skill.** Writing is gated and opt-in. Default path is informational only.
- **Unattributed activity is the key signal.** It's easy to notice what you stopped doing; it's harder to notice what you started doing without declaring it. Spend context there.
- **Denylist recurring calendar noise.** Lunches, standing socials, office-hours blocks should not inflate the activity counts. Seed a small denylist in the prompt; extend in-place as new patterns emerge.
- **Do not touch the `## Project dashboard` auto-zone.** That's `/show-priorities`'s domain. Edits land only in hand-written sections.
- **Small drift is normal.** A one-week stall on a "this week" item is not necessarily drift — weeks have other weight. Only flag drift when the pattern is sustained (e.g., stated as priority for 2+ weeks with zero activity).
- **Interact with `/morning-coffee` output.** If daily-note tag captures exist in the window, their signal is high-quality and should weight heavily. In weeks with no daily notes, fall back to log.md and commits.
