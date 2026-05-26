---
name: graduate
description: Scan recent daily notes for #idea captures, cluster them, propose canonical-page destinations, draft each page, diff-and-approve, chain into /crystallize. Closes the capture → canonical loop.
---

# graduate

Promote ideas captured inline in daily notes (via `#idea` tags) to canonical pages in `context/`, `references/`, or `projects/*/pages/`. Scans, clusters, proposes, drafts, diffs, writes. Works hand-in-hand with `/close-week` (which aggregates `#idea` into the weekly rollup) and `/crystallize` (which actually writes the page).

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 2.3. Follow this skill exactly.

## Prerequisites you assume

- Tag vocabulary rule file at `.claude/rules/daily-note-tags.md` is the source of truth for the `#idea` tag.
- `/crystallize` skill exists and supports `--pre-approved` to skip its own diff gate (since `/graduate` has one).
- `daily/` directory exists with zero or more daily notes.

## Inputs you read

1. All `daily/YYYY-MM-DD.md` files in the window (default: last 14 days, accept `--days N`).
2. `weekly/YYYY-Www.md` rollups in the window (if they exist) — use the pre-aggregated `## Ideas captured` sections as a shortcut when available.
3. All existing pages under `context/`, `references/`, and `projects/*/pages/` — needed to detect "this idea already has a page" cases.

## Outputs you write

Per approved cluster:

1. A new page at the chosen destination (via chained `/crystallize --pre-approved`), OR
2. An append to an existing page (via manual merge prompt).

Always:

3. One line appended to `log.md` per graduation.
4. Final summary printed to the terminal.

## Invocation

- `/graduate` — default window of 14 days, scans all daily notes and weekly rollups.
- `/graduate --days 30` — custom window.
- `/graduate --daily 2026-04-22` — single-day scan.

## Execution sequence

### Phase 1: Resolve window

Default: last 14 calendar days ending today. Collect all `daily/YYYY-MM-DD.md` files in range. Collect all `weekly/YYYY-Www.md` files whose `period_start` or `period_end` falls in range.

Print: `Scanning <N> daily notes and <M> weekly rollups from <start> to <end>.`

### Phase 2: Extract `#idea` captures

For each daily note, apply the canonical tag regex from `.claude/rules/daily-note-tags.md` (strict placement, fenced-code-block stripping). Collect every `#idea` line with:

- Source daily note (wikilink).
- Line content (the text after `#idea` or `#idea:`).
- Line number.

For each weekly rollup that exists, also pull the pre-aggregated `## Ideas captured` section. If the weekly already aggregated, prefer its list over re-reading the dailies (avoids duplication); otherwise fall back to direct daily scan.

If zero `#idea` captures, stop and print: "No `#idea` captures in the window. Nothing to graduate." Exit.

### Phase 3: Cluster captures by theme

Group captures by theme. Clustering signals:

- Shared keywords or phrases across multiple captures.
- Shared wikilinks in the surrounding context.
- Shared domain (work, school, personal).
- Temporal proximity (captures on consecutive days may be iterating on the same thought).

Target cluster sizes: 1 to 5 captures per cluster. A single-capture cluster is valid — sometimes an idea is whole in one line. Do not over-cluster: if two captures are genuinely distinct, keep them separate.

Print the proposed clusters to the terminal with a short theme name for each. Ask the user to confirm or adjust. Allow merge/split/skip/defer per cluster.

### Phase 4: Propose destination per cluster

For each confirmed cluster, propose a destination. Options:

1. **New canonical page.** When the idea is stable, stand-alone, and worth a dedicated page. Destination folder depends on type:
   - `context/` for identity/entity knowledge
   - `references/` for how-to / SOP content
   - `projects/<domain>/<slug>/pages/` for project-specific thinking
2. **Append to existing page.** When the idea belongs inside a page that already exists. Detect by matching cluster keywords against frontmatter titles, filenames, and page bodies across `context/`, `references/`, and `projects/*/pages/`.
3. **Defer.** The idea is not yet ready. Leaves the capture in the daily note; does nothing this run.
4. **Dismiss.** The idea is not worth keeping. Does nothing (idea stays in the daily note as history).

Propose one destination per cluster. Show the proposal; let the user override.

### Phase 5: Draft + approve per cluster

For each cluster destined for a new page:

- Draft the page content: frontmatter (`title`, `type`, `last_updated`, `sources` citing source daily notes), one-paragraph summary, expansion of the captures into prose, wikilinks to related pages.
- Hand off to `/crystallize --pre-approved <draft> <destination>`. Crystallize writes the file and updates the relevant index.
- Append one line to `log.md`: `## [YYYY-MM-DD] update | graduate: promoted <cluster-theme> → <destination> (<N> captures from <M> daily notes)`.

For each cluster destined to append:

- Show the current target page.
- Draft the addition (2 to 6 sentences that slot into the existing structure).
- Diff-and-approve.
- On approval, use Edit to add the content; do not use Write.
- Append log line as above.

For deferred or dismissed clusters: no file writes, no log line.

### Phase 6: Summary

Print a summary:

```
Graduated <N> clusters (<P> new pages, <A> appends).
Deferred <D> clusters.
Dismissed <X> clusters.
```

List each graduated cluster with its destination. Print source daily notes so the user knows where the captures came from.

## Behavior notes

- **Do not modify daily notes.** The `#idea` captures stay in their source daily notes as history. They're "graduated" by existing as a canonical page; the capture itself is not deleted or moved.
- **No auto-graduation.** Every cluster gets user approval on theme, destination, and content before anything writes.
- **Respect `/crystallize` behavior.** Pre-approval skips its diff gate but not its index updates or log line. Expect two `log.md` lines per graduation (one from `/graduate`, one from `/crystallize`).
- **Existing-page detection is soft.** When a cluster could go to multiple existing pages, surface all candidates and let the user pick. Don't silently pick one.
- **Small windows are fine.** `/graduate --daily 2026-04-22` on a single day with 2 captures is a valid invocation.
- **Clustering is the hard part.** Spend context here. Sloppy clustering dumps related ideas into separate pages or mixes unrelated ones; both are worse than no graduation.
