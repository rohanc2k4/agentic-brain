---
name: trace
description: Track how the user's thinking on a topic has evolved over time. Walks git history, frontmatter last_updated, and decisions/log.md entries to produce a dated timeline with phase headers. Read-only.
---

# trace

Produce a chronological narrative of how the user's thinking on a topic has evolved. Pulls from git history (content diffs on matched files), frontmatter `last_updated` fields, `decisions/log.md` entries, and `log.md` action lines. Outputs a dated timeline with phase headers.

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 2.2. Follow this skill exactly.

## Prerequisites you assume

- The repo is a git repository with commit history.
- Topic is expressible as either a slug (matches filenames) or a keyword (matches content).

## Inputs you read

1. All files in the repo whose filename or title-frontmatter matches the topic.
2. `git log --all --follow -p --date=short` filtered to those files, plus any file that historically had a matching filename.
3. `git log --all --date=short --pretty=format:'%H %ad %s'` filtered by commit message keyword match for topics without filename hits.
4. `decisions/log.md` entries that mention the topic.
5. `log.md` action lines that mention the topic.

## Outputs you write

Read-only by default. Print the timeline to the terminal. Optionally save to `outputs/trace-<topic>-YYYY-MM-DD.md`.

## Invocation

`/trace <topic>`. Topic can be a slug (`some-project`), a page title, or a keyword phrase (`"offer one vs offer two"`).

## Execution sequence

### Phase 1: Resolve the topic

Two resolution paths:

- **Slug resolution.** If the topic matches one or more files by filename (stem or folder), use those files as the primary trace target.
- **Keyword resolution.** If no filename matches, use grep across the repo to find pages mentioning the topic. Take the top 10 by match density.

Print the resolved targets: `Tracing 'offer one vs offer two' across 4 files: decisions/log.md, context/people/me.md, daily/2026-04-16.md, daily/2026-04-17.md.`

### Phase 2: Collect git history for target files

For each target file, run:

```
git log --all --follow --date=short --pretty=format:'%H|%ad|%s' -- <file>
```

Collect every commit that touched the file. For each commit, optionally pull the diff via `git show <hash> -- <file>` if the content evolution matters for narrative (cap at 15 diffs total to keep context bounded).

If the topic resolved via keyword (no filename), also run:

```
git log --all --date=short --pretty=format:'%H|%ad|%s' --grep='<topic>'
```

For commit-message matches.

### Phase 3: Collect log.md and decisions/log.md mentions

Grep `log.md` for lines mentioning the topic (case-insensitive). Collect with dates.

Grep `decisions/log.md` for entries mentioning the topic. Decision entries carry the most interpretive weight — include them even if only marginally related.

### Phase 4: Build the timeline

Merge all events (commits, log lines, decision entries, frontmatter `last_updated` changes) into a single chronological sequence.

Identify phase boundaries. A phase shift is marked by:

- A jump in commit frequency (quiet period → burst or vice versa).
- A decision entry that changes direction.
- A new file being created that supersedes an older one.
- A `supersedes:` / `superseded_by:` chain (treat as explicit phase boundary).
- A shift in vocabulary — the topic being discussed in different terms before vs after a date.

Aim for 3 to 6 phases. Each phase gets a short name and a date range.

### Phase 5: Format the output

Print to the terminal:

```
# Trace: <topic>

## Targets

<list of files and their date spans>

## Timeline

### Phase 1: <phase name> (<date range>)

<2-4 sentence narrative>

Key events:
- YYYY-MM-DD: <event, citing commit hash or log line or decision entry>
- ...

### Phase 2: ...

## Current state

<1-2 paragraphs on where the topic stands as of today, citing the most recent sources>

## Unresolved or open

<bullets of threads that are still in flight>
```

### Phase 6: Offer to save

Same pattern as `/connect`. Offer to write `outputs/trace-<topic>-YYYY-MM-DD.md`. Log one line either way:

```
## [YYYY-MM-DD] query | trace: <topic> (<N> phases, <M> events, saved=<yes|no>)
```

## Behavior notes

- **Do not fabricate events.** Every phase event cites a commit hash, a log line, or a decision entry. If a phase boundary feels right but you can't cite it, downgrade to prose without a date.
- **Quote sparingly.** Don't paste commit diffs wholesale. Paraphrase and cite the hash.
- **Respect supersession.** If a file has `superseded_by:`, include that transition explicitly in the timeline — it's a strong phase marker.
- **Handle the "no history" case.** If the topic has only one or two events, produce a single-phase summary and say so. Don't manufacture phases.
- **Special case: `decisions/log.md` entries.** Always include every decision-log entry that mentions the topic, even if small. Decisions are the highest-weight events in a trace.
