---
name: lint
description: Scan the repo for stale pages, broken wikilinks, orphans, and missing frontmatter. Writes a dated report to outputs/.
---

# /lint

Run the repo linter and write the report.

## What it does

Scans `context/`, `projects/`, `outputs/` for:

1. **Stale `last_updated`** — active pages whose frontmatter is older than 60 days.
2. **Broken wikilinks** — `[[target]]` that resolves to no file-stem or folder-with-index in the live tree.
3. **Orphan pages** — files in `context/` or `projects/` with no inbound wikilinks or CLAUDE.md `@import`. Indices (README.md, index.md) are excluded.
4. **Missing frontmatter** — content pages (non-index) that don't start with `---`.

Skips: `archives/`, `raw/`, `daily/`, `.obsidian/`, `.git/`, `node_modules/`, `.claude/`.

## How to invoke

```
/lint
```

Or directly:

```
python3 .claude/skills/lint/scanner.py --root . --out outputs/lint-report-$(date +%Y-%m-%d).md
```

## On-demand vs scheduled

The same scanner runs both from the `/lint` command (on demand) and from a weekly cron trigger (Sundays via `schedule`). Both call `python3 .claude/skills/lint/scanner.py`.

## When you run /lint

1. Run the scanner with `--out outputs/lint-report-YYYY-MM-DD.md` using today's date.
2. Log an action line to `log.md`: `## [YYYY-MM-DD] lint | <report path> — N broken, M orphans, K missing-fm`.
3. Print a one-line summary to the user with the counts.

Do not auto-fix. Issues are surfaced for human triage. A future `/lint --fix` or self-healing hook is separate.
