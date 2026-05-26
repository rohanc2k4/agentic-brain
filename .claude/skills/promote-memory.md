---
name: promote-memory
description: Scan the memory dir for stable observations, propose context destinations via model judgment, walk through each pick with a drafted file (short prose) or a manual-merge prompt (long prose or existing file), and chain into /supersede --pre-approved to finalize
---

# promote-memory

Turn a pile of unsuperseded memory entries into a set of approved supersessions. Scans the memory directory, proposes a destination per candidate, walks the user through a batch pick and per-candidate lifecycle, and chains into `/supersede --pre-approved` to finalize each one. The approval surface lives inside this skill; `/supersede` runs in pre-approved mode because this skill already did the gating.

Spec: `docs/superpowers/specs/2026-04-14-promote-memory-design.md`. Follow this skill exactly, do not improvise steps.

## Prerequisites you assume

- `/supersede` skill exists at `.claude/skills/supersede.md` and accepts a `--pre-approved` flag.
- The memory directory is at `$HOME/.claude/projects/<project-slug>/memory/`.
- Today's date is available; compute it as `YYYY-MM-DD` with the current-time call you already use in other skills, or from environment.

If any prerequisite is missing, stop and report before touching anything.

## Inputs you read

1. The memory directory, one markdown file per entry (excluding `MEMORY.md`).
2. Each candidate memory file's frontmatter and body.
3. The repo's `context/` tree (for destination proposal).
4. The repo's `projects/` tree (for destination proposal when the candidate is `type: project`).
5. The repo's `MEMORY.md` file (for detecting the `parked` tag).

## Outputs you write

1. Zero or more new files under `context/`, `projects/`, `references/`, depending on the user's per-candidate choices.
2. Zero or more `/supersede --pre-approved` calls, each of which moves a memory entry or repo file per the supersede skill's contract.
3. One new line appended to `log.md`.

## Execution sequence

### Phase 1: Locate the memory directory

Compute `memoryDir = $HOME/.claude/projects/<project-slug>/memory`. Use the Bash tool:

```bash
ls -d "$HOME/.claude/projects/<project-slug>/memory" 2>&1
```

If the directory does not exist, print `memory dir not found at <path>, nothing to do` and stop.

Also record `today` (today's date, `YYYY-MM-DD`) for the log line in Phase 7.

### Phase 2: Scan candidates

Glob `<memoryDir>/*.md`. For each file:

1. If the basename is `MEMORY.md`, skip.
2. Read the full file content.
3. Parse the frontmatter block (from the first `---` to the next `---`).
4. If the frontmatter contains a `superseded_by:` field, skip — already promoted.
5. Compute `age_days` from the file's mtime (use `stat -f %m <path>` on macOS or `stat -c %Y <path>` on Linux; subtract from `date +%s`, divide by 86400).
6. If `age_days < 1`, skip — too fresh.
7. Detect the `parked` flag:
   - `parked = true` if the frontmatter contains a `parked:` field, OR
   - `parked = true` if `<memoryDir>/MEMORY.md` contains the basename of this file on a line that also contains the word `parked` (case-insensitive).
   - Otherwise `parked = false`.
8. Record `{ path, name, description, type, age_days, parked, body }` as a candidate.

If the resulting list is empty, print `no memory entries ready to promote, nothing to do` and stop.

### Phase 3: Propose destinations

For each candidate, produce a destination proposal using your own judgment (not a keyword match). The proposal is one of:

- `update <relative-path>` — an existing file in `context/`, `projects/`, or `references/` is the likely destination.
- `new <proposed-relative-path>` — no existing home; suggest a path following the repo's conventions (`context/people/*.md` for people, `context/orgs/<slug>/*.md` for org concepts, `projects/work/<slug>/README.md` for work projects, `references/sops/*.md` for SOPs, etc.).
- `unclear` — no confident placement.

To make each proposal, consider:

- The candidate's `type` field (`user`, `feedback`, `project`, `reference`).
- The candidate's `name` and `description` frontmatter.
- The first ~200 characters of its body.
- A Glob of `context/**/*.md` to know what exists. For `type: project`, also Glob `projects/**/README.md`.

Record the proposal as `{ kind: "update" | "new" | "unclear", path?: string, reason: string }` per candidate.

### Phase 4: Print the batch report

Print a markdown table (with index, age, type, name truncated to ~35 chars, and destination). Mark parked candidates with a `[parked]` prefix on the destination column.

```
Candidates (<N>):

  #  age   type       name                                 destination (proposed)
  1  12d   user       Role at current employer             update context/people/me.md
  2  12d   feedback   Negotiation style                    update .claude/rules/communication-style.md
  3   8d   project    Active side projects                 [parked] new projects/work/some-cleanup/README.md
  4   5d   reference  Observability stack                  new context/orgs/some-org/observability.md
  5   2d   user       Thought on compound interest         unclear, no obvious home

Type indices to promote (e.g. "1,2,4" or "all" or "none"), or "skip N[,N...]" to defer in this run:
```

### Phase 5: Accept pick input

Parse the user's response. Accept these forms:

- Comma-separated indices: `1,2,4`.
- Single index: `3`.
- `all` → every candidate, in index order.
- `none` → exit cleanly. Log line with `N=0, M=0, K=0`, report, stop.
- `skip N` or `skip N,M` → defer those indices for this run. Proceed with the remaining (non-skipped, non-deferred) candidates in index order. Track `deferred_count` for Phase 7.

If input is invalid (unparseable indices, out-of-range numbers, mixing `all` with `skip`, etc.), re-prompt once with a clarifying message. If still invalid, abort with `invalid pick input, exiting`.

Build the `picked` list preserving the order the user typed.

### Phase 6: Per-candidate lifecycle loop

Initialize counters: `promoted = 0`, `skipped = 0`. For each candidate in `picked`, branch on the proposal `kind`:

**6a. `new <path>` AND `wordCount(body) <= 800`.**

Compute `wordCount` as whitespace-separated token count of the candidate body (excluding frontmatter).

Draft the new file content:

- **Frontmatter:** keep a subset of fields — map the memory frontmatter to the canonical context shape:
  - `title`: the memory's `name` field
  - `type`: pick one of `person` / `organization` / `project` / `rule` / `rhythm-file` / `reference` based on the candidate's content. If unclear, use the memory's original `type` field.
  - `last_updated`: `<today>`
  - `sources: [memory/<basename>.md]`

- **Body:** the memory body with any existing `> **SUPERSEDED ...` banner stripped if present (defensive — should not exist yet).

Print the drafted content as a preview, bracketed by `--- DRAFT START ---` and `--- DRAFT END ---` lines for visual clarity. Then ask:

```
Create this file at <path>? [yes / edit / skip]
```

Parse response:
- `yes` or `y` → use the Write tool to create the file at `<path>`, then proceed to the /supersede call below.
- `edit` → accept the user's pasted-back edited content. Validate that the result still has frontmatter. Write the file with the edited content. Proceed.
- `skip` or `n` → increment `skipped`, move to next candidate.

**6b. `new <path>` AND `wordCount(body) > 800`.**

Print:

```
This entry is long (<N> words). Draft the new file manually at <path>, then reply "ready" (or "skip") to continue.
```

Wait for response.
- `ready` → verify the file exists at `<path>` with the Read tool; if missing, print `file not found at <path>, try again or skip` and re-prompt once. If still missing, treat as `skip`. If present, proceed to the /supersede call.
- `skip` → increment `skipped`, move on.

**6c. `update <path>`.**

Print the full memory body (strip frontmatter) bracketed by `--- MEMORY CONTENT START ---` / `--- MEMORY CONTENT END ---`. Then print:

```
Merge this into [[<slug>]] (<path>) manually, then reply "ready" (or "skip") to continue.
```

Wait for response.
- `ready` → proceed to the /supersede call. No verification of the merge; trust the user.
- `skip` → increment `skipped`, move on.

**6d. `unclear`.**

Print the candidate name and reason, then:

```
Where should this go? Reply with a repo-relative path, or "skip".
```

On path reply:
- If the path exists, branch to 6c (update).
- If the path does not exist AND `wordCount(body) <= 800`, branch to 6a (new, short).
- If the path does not exist AND `wordCount(body) > 800`, branch to 6b (new, long).

On `skip`, increment `skipped`, move on.

**Per-candidate /supersede call (shared by 6a, 6b, 6c, 6d).**

When a candidate is ready to finalize, invoke the supersede skill. The skill is normally called via its slash command, but inside another skill you simulate the invocation by:

1. Reading the supersede skill's content (you know what it does).
2. Applying its Phase 1-8 steps with `--pre-approved = true`, where the destination path is the candidate's resolved destination and the old path is the candidate's memory path.

Alternatively, if your environment supports nested slash-command invocation, call `/supersede <memory-path> <destination-path> --pre-approved` directly. Whichever mechanism is available, the operation must:

- Edit the old file's frontmatter to add `superseded_by` and `superseded_on`, prepend the warning banner, and leave it in place (since it's a memory entry, not a repo file — supersede skill's Phase 2 classifies memory correctly).
- Update the new file's frontmatter to add/merge a `supersedes:` entry pointing at the memory path.
- Rewrite wikilinks in the live tree (if any point at the memory slug — usually not, but do the grep for correctness).
- Append the standard supersede log line to `log.md`.
- Skip the approval prompt (because `--pre-approved`).

If `/supersede` fails for this candidate, stop the per-candidate loop immediately. Print which candidates succeeded before the failure and which one failed. Do NOT continue to remaining picks. Proceed to Phase 7 with partial counters.

On success, increment `promoted` and move to the next candidate.

### Phase 7: Append log line

Append exactly one line to `log.md`:

```
## [<today>] update | promote-memory | promoted <promoted> entries (skipped <skipped>, deferred <deferred_count>)
```

Where `deferred_count` came from Phase 5's `skip` list.

### Phase 8: Report

Print:

```
promote-memory done.
  promoted: <promoted>
  skipped:  <skipped>
  deferred: <deferred_count>
  log:      log.md
```

Stop. Do not invoke any further skill.

## Error handling summary

- Memory dir missing → clean exit with message.
- No candidates after filter → clean exit with message.
- Pick input invalid → re-prompt once, then abort.
- Lifecycle `skip` → count and continue.
- `ready` response for 6b where the file is still missing → re-prompt once, then treat as `skip`.
- `/supersede --pre-approved` fails for one candidate → stop the loop, proceed to Phase 7 with partial counters.
- `log.md` append fails → print error but keep completed promotions. The repo state after /supersede is truth; the log is a paper trail.

## Anti-patterns you must avoid

- Do NOT auto-merge memory content into existing context files. `update` destinations always route to manual merge.
- Do NOT promote memory entries without a destination confirmed by the user.
- Do NOT call `/supersede` WITHOUT `--pre-approved` from inside this skill — this skill has already done the gating and a second prompt would be wrong.
- Do NOT call `/supersede --pre-approved` without first resolving the destination file to a real path.
- Do NOT touch `MEMORY.md` as a candidate; it's the index, not an entry.
- Do NOT promote entries less than 1 day old.
- Do NOT defer state persistently; `skip N` only defers for this run.
