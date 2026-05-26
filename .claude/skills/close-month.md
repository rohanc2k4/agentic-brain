---
name: close-month
description: Produce a monthly rollup note at monthly/YYYY-MM.md by aggregating from weekly rollups (narrative) and daily notes (tags). Hybrid source: weeklies are canonical for narrative, dailies are re-read for tag aggregation. Diff-and-approve gate before writing.
---

# close-month

Produce the monthly rollup note for a given month. Narrative sections aggregate from the weekly rollups (treating them as canonical, one interpretation per week). Tag sections (ideas, decisions, blockers, wins, followups) re-read daily notes directly for completeness, since tags are structured data with no interpretation risk. Shows a diff, writes on approval.

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 1.1 plus Resolved Design Decisions #4. Follow this skill exactly.

## Prerequisites you assume

- `monthly/` directory exists at the repo root.
- `weekly/` directory exists with zero or more `YYYY-Www.md` rollups.
- `daily/` directory exists with daily notes.
- Tag rule file at `.claude/rules/daily-note-tags.md`.
- `git` is available.

## Inputs you read

1. All `weekly/YYYY-Www.md` files whose `month` frontmatter field equals the target month.
2. All `daily/YYYY-MM-DD.md` files inside the calendar month (first to last day), for tag aggregation only.
3. `log.md`, filtered to action lines inside the month.
4. `decisions/log.md`, filtered to entries inside the month.
5. `git log` for the month window.

## Outputs you write

1. `monthly/YYYY-MM.md`, auto-zones replaced, manual sections preserved.
2. One line appended to `log.md`.

## Invocation

`/close-month` defaults to the current calendar month.
`/close-month 2026-04` runs for the specified month.

## Execution sequence

### Phase 1: Resolve the month window

Compute:
- `year`, `month_num` zero-padded.
- `month_start`: first calendar day of the month, `YYYY-MM-DD`.
- `month_end`: last calendar day, `YYYY-MM-DD`.
- `weeks`: every ISO week whose Thursday falls in this month. Produces the same assignment as `/close-week`. Typically 4 or 5 weeks.
- `partial`: true if the month contains today's date, else false.

Print the resolved window.

### Phase 2: Read weekly rollups

For each week in `weeks`, read `weekly/YYYY-Www.md` if it exists. Collect missing weeks — these will be gaps in the narrative but not in tag aggregation.

### Phase 3: Read daily notes for tag aggregation

Read every `daily/YYYY-MM-DD.md` inside the month window. Apply the canonical tag regex from `.claude/rules/daily-note-tags.md`. Strip fenced code blocks first.

Group captures by tag, preserving daily-note wikilink citations.

### Phase 4: Read log.md, decisions/log.md, and git commits

Filter to the month window. Same pattern as `/close-week` but broader.

### Phase 5: Draft the rollup body

**Frontmatter:**

```yaml
---
title: <Month name> <year>
type: rollup
period: monthly
period_start: <month_start>
period_end: <month_end>
weeks: [<comma-separated list of YYYY-Www>]
quarter: <YYYY-Qn>
status: <partial | final>
last_updated: <ISO 8601 with offset>
sources:
  - <one entry per weekly rollup that existed>
  - <one entry per daily note that existed>
  - log.md
  - decisions/log.md
---
```

**Banner image embed.** Directly after the frontmatter, before the `# <Month name> <year>` heading, insert an inline wikilink-embed pointing at the correct monthly banner:

```
![[MonthlyBanner<((month_num - 1) % 4) + 1>.gif]]
```

Files live at `assets/banners/monthly/MonthlyBanner{1..4}.gif`. Obsidian resolves by filename globally.

**Body sections:**

1. `# <Month name> <year>` heading.
2. `<!-- close-month:start -->` marker.

3. `## Narrative` — 3 to 6 paragraph arc of the month. **Aggregate from the weekly rollups' narratives**, do not re-interpret daily notes. Quote or paraphrase weekly narratives; cite `[[weekly/YYYY-Www]]` wikilinks. If a week is missing (no weekly rollup exists), write `_Week <n> was not closed — no narrative available._` and continue.

4. `## Top wins` — `#win` captures from daily notes inside the month, grouped or deduplicated if the same win appears multiple times. Source citations.

5. `## Top blockers` — `#blocker` captures from daily notes.

6. `## Decisions made` — merged list of `#decision` tag captures and `decisions/log.md` entries dated inside the month. Citations to both sources.

7. `## Open threads` — `#followup` captures, plus threads from weekly narratives marked unfinished. Source citations.

8. `## Ideas captured` — `#idea` captures, each with source wikilink.

9. `## Weekly ratings` — list of `[[weekly/YYYY-Www]]` wikilinks with a one-line summary pulled from each weekly's narrative first paragraph (or its title alias if present).

10. `## Commit summary` — git activity across the month, grouped by week.

11. `<!-- close-month:end -->` marker.

12. `## Notes` — hand-written zone, preserved across re-runs.

### Phase 6: Preserve manual zones

Same pattern as `/close-week`. Respect `<!-- manual -->` blocks and the `## Notes` section.

### Phase 7: Diff and approve

Print unified diff. Wait for approval.

### Phase 8: Write

Use Write tool.

### Phase 9: Log and confirm

Append to `log.md`:

```
## [YYYY-MM-DD] update | close-month: wrote monthly/YYYY-MM.md (<W> weeklies, <D> daily notes, <T> tag captures, partial=<yes|no>)
```

Print confirmation with any gaps (missing weeklies especially — they leave narrative holes).

## Behavior notes

- **Hybrid source is intentional.** Narrative = weekly rollups (one canonical interpretation per week). Tags = daily notes (mechanical grep, no interpretation risk). Do not re-read dailies for narrative.
- **Missing weeklies leave narrative gaps but not tag gaps.** The right failure mode — the user can run `/close-week` for the missing weeks and re-run `/close-month` to fill the narrative.
- **Partial months** are handled the same way as partial weeks.
- **Do not modify weeklies or dailies.** Read-only.
