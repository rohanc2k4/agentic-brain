---
name: supersede
description: Supersede an old file with a new canonical one — move repo files to archives/, edit frontmatter on both ends, rewrite wikilinks, log the operation, all behind an approval gate
---

# supersede

Formalize "this file replaced that file" across the repo. Given an old path and a new path, moves the old file to `archives/` (or leaves memory entries in place), edits frontmatter on both ends, rewrites every wikilink in the live tree that pointed at the old slug, and appends a log line. Always runs behind a diff-and-approve gate.

Spec: `docs/superpowers/specs/2026-04-14-supersession-design.md`. Follow this skill exactly, do not improvise steps.

## Invocation

```
/supersede <old-path> <new-path>
```

Both paths are relative to the repo root, unless `<old-path>` points at a memory entry (an absolute path inside the Claude Code memory directory under `$HOME/.claude/`). The successor file must already exist; the user authors it first, then invokes supersession.

## Pre-approved invocation

`/supersede <old-path> <new-path> --pre-approved` skips the Phase 6 approval gate. This is a trust boundary intended for upstream skills (such as `/promote-memory`) that have already done their own approval gating. Manual invocation should never use `--pre-approved`. When the flag is set, Phase 6 still prints its preview block as a record, but does not wait for input.

## Inputs you read

1. The old file at `<old-path>` — existence, frontmatter, full body.
2. The new file at `<new-path>` — existence, frontmatter.
3. Every markdown file under `context/`, `projects/`, `decisions/`, `references/`, `.claude/skills/` — for the wikilink grep.
4. Every `<old-slug>.md` file anywhere in the repo — for the ambiguity check.

## Outputs you write

1. The old file moved to `archives/<old-relative-path>-<YYYY-MM-DD>.md` (repo files) or overwritten in place (memory entries), with updated frontmatter and a warning banner.
2. The new file's frontmatter gains a `supersedes:` entry.
3. Zero or more other markdown files under the live tree, with wikilinks rewritten from `[[<old-slug>]]` to `[[<new-slug>]]`.
4. One new line at the bottom of `log.md`.

## Execution sequence

### Phase 1: Parse and validate inputs

Parse `<old-path>` and `<new-path>` from the invocation. Compute:
- `today`: today's date as `YYYY-MM-DD`.
- `oldSlug`: basename of `<old-path>` without `.md` extension.
- `newSlug`: basename of `<new-path>` without `.md` extension.

Check, in order, stopping with a specific error on any failure:

1. `<old-path>` exists. If not: `error: old file not found at <old-path>`.
2. `<new-path>` exists. If not: `error: new file not found at <new-path>`.
3. `<old-path>` != `<new-path>`. If equal: `error: old and new paths are identical`.
4. Old file has YAML frontmatter (first non-blank line is `---`, closed by a later `---`). If not: `error: old file <old-path> has no frontmatter`.
5. New file has YAML frontmatter. If not: `error: new file <new-path> has no frontmatter`.
6. Old file frontmatter has no `superseded_by:` field. If it does: `error: <old-path> is already superseded by <existing superseded_by>`.

### Phase 2: Classify old file

If `<old-path>` is an absolute path under `$HOME/.claude/` OR contains `/memory/` as a path segment, classify as **memory**. Otherwise classify as **repo**.

Remember this classification — Phase 3, Phase 7, and the banner-insertion step branch on it.

### Phase 3: Compute archive path (repo only)

Skip for memory entries.

For repo files, compute:

```
archivePath = "archives/" + <old-path-relative-to-repo-root without .md> + "-" + today + ".md"
```

Example: `context/people/alex.md` on 2026-04-14 → `archives/context/people/alex-2026-04-14.md`.

Check if `archivePath` already exists. If it does, try `...-<today>-2.md`, `...-<today>-3.md`, and so on until you find an unused path. Use that as the final `archivePath`.

### Phase 4: Grep for wikilinks

Use the Grep tool with these parameters:

- `pattern`: `\[\[<oldSlug>(\|[^\]]*)?\]\]` (escape `oldSlug` to avoid regex metacharacters; `oldSlug` is a filename, typically `a-z0-9-` only, so escaping is usually a no-op)
- `output_mode`: `content`
- `-n`: true
- `glob`: `*.md`

Run the grep four times, once for each live tree root:
- `context/`
- `projects/`
- `decisions/`
- `references/`
- `.claude/skills/`

Collect all hits into a single `wikilinkHits` list: `[{ path, line, match }]`. Filter out any hit whose `path` starts with `archives/`, `daily/`, `outputs/`, `.obsidian/`, or is literally `log.md`.

If the resulting list is empty, remember that `0 links` will be rewritten and continue.

### Phase 5: Ambiguity check

Use the Glob tool with pattern `**/<oldSlug>.md` to find every file in the repo with the old slug basename.

Filter the result to:
- Exclude the old file itself at `<old-path>`.
- Exclude any hit inside `archives/`.
- Exclude any hit inside `daily/`, `outputs/`, `.obsidian/`.

If the filtered list is non-empty, stop and print:

```
error: slug <oldSlug> is ambiguous — multiple files with this basename exist:
  - <old-path> (the file you're superseding)
  - <other path 1>
  - <other path 2>
Rename the unrelated file first or confirm which should be rewritten.
```

Do not proceed.

### Phase 6: Show the diff preview

Print a preview block, then wait for approval. The preview has five sections:

**Move.** For repo files: `<old-path>` → `<archive-path>`. For memory: `<old-path>` (stays in place).

**Wikilink rewrites.** A table:

| File | Hits |
|---|---|
| context/people/alex.md | 3 |
| projects/work/some-project/README.md | 1 |
| ... | ... |

Total: N hits across M files.

**Frontmatter edit on old file.** Show the exact additions:

```yaml
superseded_by: <new-path>
superseded_on: <today>
```

**Banner on old file body.** Show the exact line to be inserted immediately below the closing `---` of frontmatter, followed by a blank line:

```markdown
> **SUPERSEDED <today>.** Canonical source: [[<newSlug>]]. Kept for history only.
```

**Frontmatter edit on new file.** Show the addition (or merge) to `supersedes:`:

```yaml
supersedes:
  - <archivePath or memory path>
```

After the preview, check whether the invocation included `--pre-approved`:

**If `--pre-approved` was passed** (e.g., `/supersede <old> <new> --pre-approved`): skip the interactive gate. The preview block above still prints as a record, but do NOT wait for any user input. Proceed directly to Phase 7. The `--pre-approved` flag is a trust boundary — it should only appear when an upstream skill (such as `/promote-memory`) has already done its own approval gating. A manual invocation should never pass this flag.

**If `--pre-approved` was NOT passed** (the default, including all manual invocations): print:

```
Type approve to execute, or cancel to abort.
```

Wait for the user's response. Accept `approve`, `yes`, `y` as approval. Anything else aborts with `supersede cancelled`.

### Phase 7: Execute

On approval, execute in this order. If any step fails, stop, print which steps completed, and recommend `git status` for recovery. Do not attempt automatic rollback.

**Step 7a: Rewrite the old file's frontmatter and body.**

Read the full content of `<old-path>`. Parse the frontmatter block (from line 1 `---` to the next `---`). Build a new frontmatter block that preserves every existing field in its original order, then appends:

```yaml
superseded_by: <new-path>
superseded_on: <today>
```

Build the new body as: the original body (everything after the closing `---` of the old frontmatter) with this line prepended directly after the new closing `---`, followed by a blank line:

```
> **SUPERSEDED <today>.** Canonical source: [[<newSlug>]]. Kept for history only.
```

Concatenate: new frontmatter (with opening and closing `---`) + newline + banner + blank line + original body. This is the new content.

**Step 7b: Place the new content at the target location.**

- **Repo files:** use Bash `mkdir -p` on the archive directory, then use the Write tool to create `<archivePath>` with the new content. Then use Bash `rm` to delete `<old-path>`.
  ```bash
  mkdir -p "$(dirname <archivePath>)"
  ```
  Then Write `<archivePath>` with the new content. Then:
  ```bash
  rm <old-path>
  ```
- **Memory entries:** use the Write tool to overwrite `<old-path>` in place with the new content. No move, no delete.

**Step 7c: Rewrite wikilinks.**

For each entry in `wikilinkHits`, use the Edit tool with `replace_all: true` on the hit's `path`:

- `old_string`: `[[<oldSlug>]]` (plain form)
- `new_string`: `[[<newSlug>]]`

Then, separately for the anchored form, run another Edit with `replace_all: true`:

- `old_string`: `[[<oldSlug>|` (partial match, escaped with a unique suffix? NO — this is ambiguous)

**Correction:** the anchored form `[[<oldSlug>|<anchor>]]` has variable content. Use Grep again per-file with pattern `\[\[<oldSlug>\|[^\]]*\]\]` in `content` mode to find each literal match string, then Edit each one individually with `replace_all: true`:

- `old_string`: the exact literal match from the grep, e.g. `[[alex|manager]]`
- `new_string`: the same anchor but with new slug, e.g. `[[alex-v2|manager]]`

Repeat for every anchored hit. Plain-form hits use a single Edit per file as described above.

If a file has both plain and anchored hits, apply the plain Edit first, then the anchored Edits.

**Step 7d: Update the new file's `supersedes:` field.**

Read the new file. Parse its frontmatter. If `supersedes:` already exists, append the old file's final resting path (`archivePath` for repo files, the memory path for memory entries). If not, add the field:

```yaml
supersedes:
  - <archivePath or memory path>
```

Preserve all other frontmatter fields. Write the file back.

**Step 7e: Append to log.md.**

Append exactly one line (no blank-line buffer):

```
## [<today>] update | supersede | <old-path> → <new-path> (rewrote <N> links across <M> files)
```

Where `N` is the total wikilink-hit count and `M` is the number of distinct files touched.

### Phase 8: Report

Print:

```
superseded <old-path> → <new-path>
  archived to: <archivePath>          (or "in place" for memory)
  wikilinks rewritten: <N> across <M> files
  log: log.md
```

Stop. Do not invoke any further skill.

## Error handling summary

- Old file not found → stop, error.
- New file not found → stop, error.
- Old path = new path → stop, error.
- Missing or malformed frontmatter on either file → stop, error.
- Old file already superseded → stop, error.
- Slug ambiguity → stop, list candidates, ask the user to disambiguate manually.
- No wikilink hits → proceed, report `0 links`.
- Mid-execute failure (Phase 7) → stop, print completed steps, recommend `git status`.

## Anti-patterns you must avoid

- Do NOT chain supersessions. If `<old-path>` is already superseded, stop. Fresh A → C is the chaining workaround.
- Do NOT rewrite wikilinks inside `archives/`, `log.md`, `daily/`, `outputs/`, or `.obsidian/`.
- Do NOT rewrite raw markdown links `[text](path.md)` or plain text mentions. Only `[[wikilinks]]`.
- Do NOT proceed past Phase 6 without explicit approval.
- Do NOT delete the old file until Phase 7b has successfully written the archive copy.
- Do NOT resolve `oldSlug` to multiple files silently. Ambiguity always stops the skill.
- Do NOT move memory entries — they stay in place.
- Do NOT pass `--pre-approved` from a manual invocation. The flag is for upstream skills only; using it manually bypasses the approval gate that exists to protect against destructive mistakes.
