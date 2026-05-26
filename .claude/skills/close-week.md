---
name: close-week
description: Produce a weekly rollup note at weekly/YYYY-Www.md by reading the seven daily notes plus log.md, decisions/log.md, and git commits for that ISO week. Aggregates tagged captures (#idea, #decision, #blocker, #win, #followup) into structured sections and drafts a narrative summary. Diff-and-approve gate before writing.
---

# close-week

Produce the weekly rollup note for a given ISO week. Reads daily notes + log.md + decisions/log.md + git commits across the week window, aggregates tagged captures, drafts narrative, shows a diff, writes on approval.

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 1.1. Follow this skill exactly, do not improvise.

## Prerequisites you assume

- `weekly/` directory exists at the repo root.
- `daily/` directory exists with zero or more `YYYY-MM-DD.md` daily notes.
- Tag vocabulary rule file at `.claude/rules/daily-note-tags.md` is the source of truth for the five tags.
- `git` is available and the working directory is the repo root.

If any prerequisite is missing, stop and report before touching anything.

## Inputs you read

1. `daily/YYYY-MM-DD.md` for each of the seven days in the ISO week window. Skip silently if a given day's file is missing.
2. `log.md`, filtered to action lines dated inside the window.
3. `decisions/log.md`, filtered to entries dated inside the window.
4. `git log --since=<period_start> --until=<period_end+1d> --pretty=format:'%h %ad %s' --date=short`, run at the repo root.
5. `monthly/YYYY-MM.md` if it exists, to update the `weeks:` list (see Phase 8).

## Outputs you write

1. `weekly/YYYY-Www.md`, created if missing, auto-zones replaced on re-run, any `<!-- manual -->` sections preserved verbatim.
2. One line appended to `log.md`.
3. (If the monthly note for the containing month already exists) updated `weeks:` list in its frontmatter.

## Invocation

`/close-week` with no argument defaults to the current ISO week.
`/close-week 2026-W17` runs for the specified week.

Resolve the week to `period_start` (Monday) and `period_end` (Sunday) using ISO-8601 rules. If the week spans a year boundary, store under the year of the Thursday (ISO-8601).

## Execution sequence

Follow these nine phases in order.

### Phase 1: Resolve the week window

Parse the argument or default to current ISO week. Compute:
- `year`, `week_num`, zero-padded to W01..W53.
- `period_start`: Monday of the week, `YYYY-MM-DD`.
- `period_end`: Sunday of the week, `YYYY-MM-DD`.
- `days`: list of seven `YYYY-MM-DD` strings.
- `month`: the month containing the Thursday of the week (ISO rule), `YYYY-MM`.
- `partial`: true if today's date is inside the window, else false.

Print the resolved window to the user: `Closing week 2026-W17 (2026-04-20 to 2026-04-26). Month: 2026-04. Partial: yes.`

### Phase 2: Read inputs

Read each `daily/YYYY-MM-DD.md` for the seven days. Missing files: note which days are missing, do not fail.

Read `log.md` and filter to lines matching `^## \[(YYYY-MM-DD)\]` where the date falls inside the window.

Read `decisions/log.md` and filter to entries dated inside the window.

Run `git log --since=<period_start> --until=<period_end+1d> --pretty=format:'%h %ad %s' --date=short` and collect commits. Separate commits by repo area if easily visible from the subject line.

### Phase 3: Aggregate tagged captures

For each daily note read, scan for lines matching the canonical regex from `.claude/rules/daily-note-tags.md`:

```
^\s*(?:[-*]\s+|\d+\.\s+)?#(idea|decision|blocker|win|followup)(?::|\b)
```

Strip fenced code blocks (triple-backtick regions) before scanning.

Group matches by tag. For each match record: the source daily note (wikilink form `[[daily/2026-04-22]]`), the line content, and the raw text after the tag.

### Phase 4: Draft the rollup body

Draft the following sections. All sections except Notes are auto-zones, rewritten on every run.

**Frontmatter:**

```yaml
---
title: Week <week_num>, <year> (<period_start_short> – <period_end_short>)
type: rollup
period: weekly
period_start: <period_start>
period_end: <period_end>
days: [<comma-separated list of seven dates>]
month: <YYYY-MM>
status: <partial | final>
last_updated: <ISO 8601 with offset>
sources:
  - <one entry per daily note that existed>
  - log.md
  - decisions/log.md
---
```

**Banner image embed.** Directly after the frontmatter, before the `# Week ...` heading, insert an inline wikilink-embed pointing at the correct weekly banner:

```
![[WeeklyBanner<((week_num - 1) % 4) + 1>.gif]]
```

Files live at `assets/banners/weekly/WeeklyBanner{1..4}.gif`. Obsidian resolves wikilink-embeds by filename globally, so the short form works.

**Body sections, in order:**

1. `# Week <week_num>, <year>` heading.

2. `<!-- close-week:start -->` marker.

3. `## Narrative` — 2 to 4 paragraph arc of the week. Cite specific days with wikilinks. Ground in real content from daily notes and commits. Do not invent events. If the week is partial, frame the narrative as "so far this week."

4. `## Top wins` — bulleted list of `#win` captures, each citing its source daily note. If none, write `_No wins captured this week._`

5. `## Top blockers` — bulleted list of `#blocker` captures with source citations.

6. `## Decisions made` — merged list of `#decision` tag captures AND any `decisions/log.md` entries dated inside the window. Cite both the daily-note wikilink (for tag captures) and `decisions/log.md:YYYY-MM-DD` (for log entries). Deduplicate if a decision appears in both.

7. `## Open threads` — `#followup` captures plus anything from the narrative that feels unfinished. Source citations.

8. `## Ideas captured` — `#idea` captures, each with source wikilink. This is the input to `/graduate`.

9. `## Commits` — short summary of git commits across the week, grouped by subject prefix if obvious (e.g. `feat:`, `fix:`, `lint:`, `spec:`). List the top 10-15; truncate and note count if more.

10. `## Days` — bulleted wikilinks to the seven daily notes: `- [[daily/2026-04-20]]`, etc. Mark missing days as `- 2026-04-20 _(no daily note)_`.

11. `<!-- close-week:end -->` marker.

12. `## Notes` — hand-written zone. On first creation, leave empty with a placeholder line. On re-run, preserve verbatim.

### Phase 5: Check for existing file and preserve manual zones

If `weekly/YYYY-Www.md` already exists:

- Read it.
- Preserve verbatim any section bounded by `<!-- manual -->` and `<!-- /manual -->` markers.
- Preserve the `## Notes` section verbatim.
- Replace everything between `<!-- close-week:start -->` and `<!-- close-week:end -->` with the newly drafted body.
- Preserve frontmatter fields the user may have added that are not in the schema (leave unknown keys alone).

### Phase 6: Diff and approve

Print a unified diff of the proposed write against the existing file (or against "empty" if new). Wait for the user to approve. Do not proceed on ambiguous responses — require a clear yes.

If rejected, print "Rollup not written. Run `/close-week <week>` again to retry." and stop.

### Phase 7: Write the file

Write `weekly/YYYY-Www.md` with the approved content. Use the Write tool.

### Phase 8: Update the monthly note's `weeks:` list (if applicable)

If `monthly/<month>.md` exists, read its frontmatter. Ensure the current week's `YYYY-Www` string is in the `weeks:` list (add if missing, preserve order). Do not touch its body.

If the monthly note does not exist, do nothing. `/close-month` will pick it up when run.

### Phase 9: Log and confirm

Append one line to `log.md`:

```
## [YYYY-MM-DD] update | close-week: wrote weekly/YYYY-Www.md (<N> daily notes, <M> tag captures, <K> commits, partial=<yes|no>)
```

Print a one-paragraph confirmation to the user with the path written and any notable gaps (missing daily notes, empty tag categories, etc.).

## Behavior notes

- **Partial weeks are fine.** If today is Wednesday of week 17, `/close-week` produces a rollup covering Mon-Wed with `status: partial`. The first run after the week ends clears `status: partial` to `status: final`.
- **Zero daily notes in the window** is not an error. Produce a minimal rollup with the `## Days` section listing missing days and a narrative that says "no daily notes were written this week."
- **Manual sections.** Anything inside `<!-- manual -->` / `<!-- /manual -->` is treated as user-authored and preserved across re-runs. Use sparingly.
- **Do not modify daily notes.** Read-only.
- **Timezone.** Use `America/New_York`. Git's `--since` / `--until` accept naive dates; use the calendar date, not a timestamp.
