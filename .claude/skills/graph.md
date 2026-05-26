---
name: graph
description: Query the repo knowledge graph (wikilinks, frontmatter edges) and per-page confidence buckets.
---

# /graph

Query the knowledge graph built from wikilinks and frontmatter across `context/`, `projects/`, `references/`, `outputs/`.

## What the graph encodes

Edges:
- `references` — from `[[wikilink]]` in body or frontmatter
- `sourced_from` — when a frontmatter `sources:` entry resolves to a repo file
- `supersedes` / `superseded_by` — from frontmatter fields of the same name

Index/README files are keyed by their folder name, so `[[some-org]]` resolves to `context/orgs/some-org/index.md`. Other pages key by filename stem.

External link sources (like `CLAUDE.md` `@imports` and wikilinks) contribute inbound edges for orphan accounting but aren't themselves nodes.

## Confidence buckets

Computed per page; index/README pages are `n/a`.

- **high**: ≥3 sources AND `last_updated` within 30 days AND 0 contradiction markers
- **medium**: ≥1 source AND `last_updated` within 90 days AND 0 contradictions
- **low**: everything else (no frontmatter, no sources and stale, any contradiction marker, etc.)

## Subcommands

```
/graph list                       # every node + its path
/graph node <name>                # dossier for one node (path, counts, confidence)
/graph inbound <name>             # pages linking to <name>
/graph outbound <name>            # pages <name> links to
/graph around <name>              # inbound + outbound + supersede chain
/graph low-confidence [--low-only]  # pages in the low/medium buckets with reasons
/graph refresh-queue              # load-bearing pages (inbound ≥ 2) with last_updated missing or >180d
/graph broken                     # all unresolved wikilinks
/graph export                     # TSV edge list (src, dst, type)
```

Run directly:

```
python3 .claude/skills/graph/query.py <subcommand> [args]
```

Or via `/graph <subcommand> [args]`.

## When to invoke

- Scoping a change: "what links to `[[some-page]]`?" before renaming or superseding.
- Trust calibration: "confidence of `context/people/me.md`?" to decide whether a claim there is load-bearing.
- Orphan triage: "what pages are low-confidence AND have no inbound links?" to find dead content.
- Dependency checks: before touching a high-inbound node, glance at `around <name>` to understand blast radius.

## Integration

The `/lint` skill already surfaces the low-confidence list automatically (added as part of this skill). So a weekly `/lint` run gives you the triage view without remembering to invoke `/graph low-confidence`.
