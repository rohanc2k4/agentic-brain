---
name: morning-coffee
description: Daily kickoff ritual — refresh priorities, read today's fixed events from both Google calendars, run a two-pass dialog, pack time blocks, write tagged events to personal calendar, and produce a daily note
---

# morning-coffee

Run the daily kickoff ritual end to end. Produces three artifacts: a time-blocked schedule visible in the terminal, real calendar events on the personal Google calendar, and `daily/YYYY-MM-DD.md` with a preserved hand-written notes section. Idempotent: safe to re-run the same day, preserves past blocks, replaces future ones.

Spec: `docs/superpowers/specs/2026-04-14-morning-coffee-design.md`. Follow this skill exactly, do not improvise steps.

## Prerequisites you assume

- `google-calendar` MCP is live with two account nicknames: `personal` (your personal Google account) and `work` (your work Google account).
- `show-priorities` skill exists at `.claude/skills/show-priorities.md`.
- Timezone is set to the user's local zone (e.g., `America/New_York`). Hardcode it, do not detect.
- `daily/` directory exists at the repo root.

If any prerequisite is missing, stop and report before touching anything.

## Inputs you read

1. `context/priorities.md`, after `show-priorities` refreshes it.
2. Frontmatter of all `projects/work/*/README.md` files and all `projects/personal/*/README.md` files when that tree exists. You only need the fields used to infer "This week" projects: `title`, `status`, `priority`, `deadline`, `blockers`.
3. `projects/school/<course>/exam*-scope.md` when such files exist.
4. Today's events on `personal` account, `primary` calendar, 00:00 to 23:59 local.
5. Today's events on `work` account, `primary` calendar, same window.

## Outputs you write

1. Events on `personal` primary calendar, tagged via `extendedProperties.private.morningCoffee = "true"`, `.date = "<YYYY-MM-DD>"`, `.runId = "<ISO timestamp of this run>"`.
2. `daily/YYYY-MM-DD.md`, created if missing, auto-zone replaced on re-run, `## Notes` section preserved verbatim.
3. One line appended to `log.md`.

## Execution sequence

Follow these ten phases in order. Do not skip or reorder.

### Phase 1: Get current time and date

Call `mcp__google-calendar__get-current-time` with `timeZone: "America/New_York"`. Record:
- `today`: the date in `YYYY-MM-DD` form.
- `now`: the current time as an ISO 8601 string with offset (used for the `runId` and `last_updated` fields and for the "day already mostly gone" check).

### Phase 2: Refresh the priorities dashboard

Invoke the `show-priorities` skill. It has its own diff-and-approve gate; let it run to completion. If it errors or the user rejects the diff, print a one-line warning (`warning: show-priorities did not update, proceeding with existing context/priorities.md`) and continue. Do not stop.

### Phase 3: Read today's fixed schedule from both accounts

Call `mcp__google-calendar__list-events` twice in parallel:

- `{ account: "personal", calendarId: "primary", timeMin: "<today>T00:00:00", timeMax: "<today>T23:59:59", timeZone: "America/New_York" }`
- `{ account: "work", calendarId: "primary", timeMin: "<today>T00:00:00", timeMax: "<today>T23:59:59", timeZone: "America/New_York" }`

Include `extendedProperties` in the `fields` parameter on the personal call so you can detect prior-run blocks.

From the personal-account result, set aside any event whose `extendedProperties.private.morningCoffee == "true"`. These are prior-run blocks, not fixed commitments. You will handle them in Phase 8.

Merge the remaining events from both accounts into a single `fixedEvents` list, each tagged with its source account. Sort by `start.dateTime` ascending.

If either `list-events` call fails, stop. Print the error and exit without writing anything.

### Phase 4: Print and triage the fixed schedule

Print a markdown table of `fixedEvents`:

| # | Time | Title | Calendar | Location |
|---|---|---|---|---|
| 1 | HH:MM–HH:MM | <summary> | personal \| work | <location or blank> |

If `fixedEvents` is empty, print `_Nothing fixed today._` and skip the rest of this phase.

Otherwise, triage each event in order. For each, ask:

> Using <title> (<account>, HH:MM–HH:MM)? [keep / drop]

Accept `keep` / `k` / `yes` / `y` / silence → keep. Accept `drop` / `d` / `no` / `n` / `delete` / `decline` → drop.

For a dropped event:

- **`account == "personal"`**: call `mcp__google-calendar__delete-event` with:
  ```
  { account: "personal", calendarId: "primary", eventId: "<the instance event id>", sendUpdates: "none" }
  ```
  The instance event id (the one returned by `list-events` for recurring events, e.g. `0fp0s6d588cful6as0k7k0ib8m_20260414T170000Z`) targets this occurrence only, not the whole series. Do not resolve to the `recurringEventId` — that would delete the series.

- **`account == "work"`**: call `mcp__google-calendar__respond-to-event` with the event id and response status `declined`. This declines the single instance, not the series. If the MCP signature differs from what you expect, try `respond-to-event` with `{ account: "work", calendarId: "primary", eventId: "<id>", responseStatus: "declined", sendUpdates: "none" }` first and adjust field names on error.

If a delete or decline call fails, print the error and stop. Do not proceed to planning with an inconsistent triage state.

Remove every dropped event from `fixedEvents` before moving to Phase 5. The dropped events are also recorded in a `droppedFixed` list so Phase 9 can mention them in the daily note's "Dropped" section.

**Batch shortcut.** If the user says `drop all`, `none of it`, or similar before you start the per-event loop, interpret it as drop every event in `fixedEvents`. Confirm once (`drop all 3 events listed above?`) before executing the deletes/declines.

### Phase 5: Run the two-pass dialog

**Pass 1, must-dos.** Print:

> What are your 1-3 must-dos today? List them with rough time estimates if you know them; I'll default to 90 min for anything you don't estimate.

Wait for the user's response. Parse into a list of `{ title, estimateMinutes, notes }` entries. For any item without an estimate, follow up once: "How long for <item>?" If the user says "default" or gives no estimate twice, use 90.

**Pass 2, nice-to-haves.** Print:

> What would be nice to fit in if there's room?

Wait for response. Parse same shape. Same estimate treatment.

Either list may be empty; that is valid. If both are empty, tell the user "nothing to schedule, exiting" and stop.

### Phase 6: Pack the blocks

Apply these eleven rules in order. Do not reinterpret them.

1. **Day window:** `09:00`–`22:00` `America/New_York`. If `now > 09:00`, use `max(now rounded up to next :00 or :30, 09:00)` as the effective start. Print a one-line warning: `starting late, effective window HH:MM–22:00`.
2. **Carve out fixed events:** every event in `fixedEvents` is immovable. Never overlap one.
3. **Carve out lunch:** 45 minutes, default centered on `12:30` (so `12:15`–`13:00`). If a fixed event overlaps, shift lunch to the nearest 45-minute gap between `11:30` and `14:00`. If no such gap exists, drop lunch and record it in the daily note's "Dropped" section.
4. **Compute free intervals:** day window minus fixed events minus lunch. Each interval has a start and an end.
5. **Minimum usable interval:** 30 minutes. Discard shorter intervals from packing (they become slack).
6. **Default block size:** 90 minutes. If an item has an estimate, round it up to the nearest 15 minutes and floor at 30 minutes.
7. **Inter-block break:** 15 minutes between two morning-coffee blocks. No break required between a fixed event and a morning-coffee block.
8. **Place must-dos first,** in listed order. For each, find the earliest free interval large enough to hold `block + trailing break`. If none exists, stop packing and ask the user: `Can't fit <title> (needs X min, longest free interval is Y min). What should give?` Accept his answer, re-run Phase 6 from the top with the revised list.
9. **Place nice-to-haves second,** same algorithm, same order. If one doesn't fit, skip it and record in the "Dropped" section. Do not stop.
10. **Tail slack:** do not place blocks past `20:00` unless a must-do forces it.
11. **Block titles:** `<project-slug-or-topic>: <short intent>`. Examples: `some-project: deep work`, `course-b: exam review`, `email: advisor follow-up`. No visible prefix.

Produce a `plannedBlocks` list: each entry is `{ title, startIso, endIso, source, description }` where `source` is one of `must-do`, `nice-to-have`, `auto`. Lunch is `auto`.

### Phase 7: Propose and iterate

Print the full proposed schedule as a markdown table:

| Time | Block | Source |
|---|---|---|
| HH:MM–HH:MM | <title> | must-do \| nice-to-have \| auto \| fixed (personal) \| fixed (work) |

Include `fixedEvents` and `plannedBlocks` interleaved in chronological order. Fixed events are shown with their `Source` column as `fixed (<account>)`.

After the table, ask:

> Want to change anything?

If the user says any form of "looks good" / "yes" / "ship it", proceed to Phase 8. Otherwise accept their edit instruction (e.g., "move some-project to after lunch", "drop the course review", "add a 30-min call with a teammate at 16:00"), update the inputs accordingly, and re-run Phase 6 from the top. Loop until approved. Do not write to the calendar until the user explicitly approves.

### Phase 8: Wipe future tagged events, then create new ones

**Wipe.** For the prior-run blocks you set aside in Phase 3, filter to those whose `end.dateTime` is strictly greater than `now`. For each such event, call `mcp__google-calendar__delete-event` with:

```
{
  account: "personal",
  calendarId: "primary",
  eventId: "<the event id>",
  sendUpdates: "none"
}
```

If any delete fails, stop. Print which events were deleted and which failed, and exit without creating new events.

**Create.** For each entry in `plannedBlocks` where `source` is `must-do` or `nice-to-have` (NOT `auto` lunch — lunch is not a calendar event, only a daily-note row), determine the `colorId` using the rules below, then call `mcp__google-calendar__create-event`:

**Color rules.** Lowercase the block title and match the first keyword in this order (first match wins):

| Keywords in title | colorId | Google name |
|---|---|---|
| `work`, `infra`, `deploy`, `pipeline`, `api`, `backend`, `frontend` | `"3"` | Grape |
| `class`, `course`, `exam`, `quiz`, `lecture`, `school`, `study`, `review` | `"11"` | Tomato |
| `meal`, `lunch`, `snack`, `breakfast`, `dinner`, `break`, `eat`, `food` | `"5"` | Banana |
| `going out`, `social`, `party`, `drinks`, `friends`, `happy hour`, `hh`, `bar`, `dinner out` | `"9"` | Blueberry |
| `lift`, `gym`, `workout`, `run`, `running`, `volleyball`, `sport`, `bouldering`, `climb`, `fitness`, `yoga` | `"2"` | Sage |
| `email`, `admin`, `errand`, `call`, `paperwork`, `form` | `"8"` | Graphite |
| anything else | `"10"` | Basil |

**Color-coding is mandatory.** Every create-event call MUST include `colorId`. If no keyword matches, use `"10"` (Basil) as the default. Do not omit `colorId` from any create-event or update-event call.

**Social titles without literal keywords.** Some titles are clearly social but don't contain a listed keyword (e.g., "Happy hour with cohort" explicitly matches `happy hour`, but a title like "Drinks with a friend" only matches if `drinks` is in the literal lowercase title). If the title obviously describes a social activity but misses the keyword table, use `"9"` Blueberry and flag the gap at the end of the run so the keyword list can be extended. Do not silently default to Basil on obvious social blocks.

Then call:

```
{
  account: "personal",
  calendarId: "primary",
  summary: "<title>",
  start: "<startIso>",
  end: "<endIso>",
  timeZone: "America/New_York",
  description: "<description>\ngenerated by morning-coffee",
  colorId: "<colorId from rules above>",
  transparency: "opaque",
  reminders: { useDefault: false, overrides: [] },
  extendedProperties: {
    private: {
      morningCoffee: "true",
      date: "<today>",
      runId: "<now ISO>"
    }
  },
  sendUpdates: "none",
  allowDuplicates: true
}
```

If any create fails, stop. Print which blocks were written and which failed. Do not roll back.

### Phase 9: Write the daily note and log line

**Daily note path:** `daily/<today>.md`. Read the file first with the Read tool. Three cases:

**Case A: file does not exist.** Create it with the full template:

```markdown
---
title: <today> Daily
type: daily-note
date: <today>
last_updated: <now ISO>
---

![[<DayOfWeek>Banner.gif]]

# <today>

<!-- morning-coffee:start -->

## Fixed today

<fixed events table, or `_Nothing fixed today._`>

## Must-dos

<numbered list from Phase 5 Pass 1, or `_None._`>

## Nice-to-haves

<bulleted list from Phase 5 Pass 2, or `_None._`>

## Schedule

<full interleaved schedule table from Phase 7>

## Dropped

<bulleted list of dropped nice-to-haves and a line for dropped lunch if applicable, or `_None._`>

## On this day

<throwback section per Phase 9b, or omit if no history exists>

<!-- morning-coffee:end -->

## Notes

_Hand-written below this line, preserved across re-runs. Inline capture tags: `#idea` `#decision` `#blocker` `#win` `#followup` (see `.claude/rules/daily-note-tags.md`)._
```

**Banner image embed.** Directly after the frontmatter, insert `![[<DayOfWeek>Banner.gif]]` where `<DayOfWeek>` is one of `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday` (capitalized). Files live at `assets/banners/daily/<DayOfWeek>Banner.gif`. Obsidian resolves wikilink-embeds by filename globally; the short form is enough. On re-run (Case B), if the embed line is missing directly after the frontmatter, insert it. If present, leave unchanged.

**Phase 9b: Throwback.** Before writing the daily note body, build the "On this day" section:

- Let `MM-DD` be today's month+day.
- For each `daily/YYYY-MM-DD.md` where `YYYY` is a prior year and `MM-DD` matches today's: read the file, pull the first 2-3 sentences of `## Notes` (if non-placeholder) or the auto-zone `## Must-dos` first 2 items. Format as:

  ```
  ### YYYY (<N> years ago)
  <short extract>

  Source: [[daily/YYYY-MM-DD]]
  ```

- Grep `decisions/log.md` for entries dated `YYYY-MM-DD` matching any prior year on this date. For each match, format:

  ```
  ### Decision from YYYY
  <one-line summary>

  Source: `decisions/log.md` entry dated YYYY-MM-DD
  ```

- Cap at 3 throwbacks total; prefer newer over older.
- If no prior-year history exists, omit the `## On this day` section entirely (do not write the heading with an empty body).

**Case B: file exists and has both markers.** Locate the lines containing `<!-- morning-coffee:start -->` and `<!-- morning-coffee:end -->`. Replace everything strictly between those two marker lines (the markers themselves stay) with the auto-zone body (Fixed today / Must-dos / Nice-to-haves / Schedule / Dropped sections in that order). Update the frontmatter `last_updated` to the current ISO timestamp. Preserve everything after the end marker verbatim.

**Case C: file exists but markers are missing or malformed.** Stop. Print `daily note at daily/<today>.md is malformed (missing morning-coffee auto-zone markers); fix manually before re-running`. Calendar writes already landed in Phase 8 — that is fine, the calendar is the source of truth.

**Log line.** Append exactly one line to `log.md`:

```
## [<today>] update | morning-coffee | wrote N blocks to personal calendar
```

`N` is the count of created events (must-dos + nice-to-haves, excluding lunch and fixed events).

### Phase 10: Report

Print a short confirmation:

```
morning-coffee done.
  blocks written: N
  daily note: daily/<today>.md
  log: log.md
```

Stop. Do not invoke any further skill.

## Error handling summary

- `show-priorities` fails or is declined: warn and proceed.
- `list-events` fails on either account: stop, no writes.
- `delete-event` fails in Phase 8 wipe: stop, no creates.
- `create-event` fails mid-batch: stop, no rollback, report partial state.
- Daily note write fails (Case C or I/O): print the error but keep the calendar writes.
- Both must-do and nice-to-have lists empty: tell the user "nothing to schedule, exiting" and stop.
- Must-do doesn't fit: loop back to Phase 6 after the user decides what gives.
- Nice-to-have doesn't fit: silently drop, record in daily note.

## Anti-patterns you must avoid

- Do NOT create events on the `work` calendar. Phase 4 may decline work events (via `respond-to-event`), but NEVER create or delete them.
- Do NOT create events without `extendedProperties.private.morningCoffee = "true"`.
- Do NOT delete or decline an untagged event without an explicit `drop` answer from the user in Phase 4. Silence means keep.
- Do NOT resolve a recurring-event instance id to its series id before deleting. Phase 4 drops this instance only.
- Do NOT skip the Phase 7 iterate step and jump straight to writing.
- Do NOT pack blocks outside the day window or across fixed events.
- Do NOT invent tasks; only schedule what the user provided in Phase 5.
- Do NOT rewrite the `## Notes` section below the end marker on re-runs.
