---
name: connect
description: Bridge two concepts using the repo's knowledge graph and page content. Walk graph neighborhoods, surface shared themes and implicit connections, output a structured "bridges" report with citations. Read-only.
---

# connect

Find non-obvious bridges between two concepts in the repo. Walks the graph neighborhood of each, reads nearby pages, synthesizes the connections. Output is a structured report with numbered bridges, each citing 2 to 4 source pages.

Spec: `docs/superpowers/specs/2026-04-22-ea-upgrade-roadmap-design.md` Section 2.1. Follow this skill exactly.

## Prerequisites you assume

- The repo graph is walkable via `.claude/skills/graph/` (confidence scoring, wikilink edges, `sources`/`supersedes` frontmatter edges).
- Both concepts resolve to something: a page filename (with or without `.md`), a folder name, an index page, or free-text matched against page titles/slugs.

If a concept does not resolve at all, stop and report — do not guess.

## Inputs you read

1. For each of the two concepts: the anchor page (if a direct match exists) plus its graph neighborhood at depth 2. Cap at 15 pages per concept to keep context tractable.
2. Frontmatter of all neighborhood pages (title, type, sources, last_updated, confidence bucket if present).
3. Body content of the top 8 most-connected neighborhood pages per concept (rank by inbound+outbound edge count).

## Outputs you write

Read-only skill. No file writes. Report printed to the terminal. Optionally offer to save the report to `outputs/connect-<a>-<b>-YYYY-MM-DD.md` at the end.

## Invocation

`/connect <a> <b>` where `a` and `b` are the two concepts. Quote multi-word concepts: `/connect "project a" "course b"`.

## Execution sequence

### Phase 1: Resolve each concept to an anchor

For each concept, attempt resolution in this order:

1. Exact filename match in the repo (e.g. `some-project` → `projects/work/some-project/README.md`).
2. Folder name match (e.g. `<org>` → `context/orgs/<org>/index.md`).
3. Title match in frontmatter (case-insensitive).
4. Fuzzy slug match.
5. Free-text — treat the concept as a topic with no single anchor page. Flag this case; the graph walk will use grep-based discovery instead.

Print the resolved anchors: `Resolved 'some-project' → projects/work/some-project/README.md. Resolved 'course-b' → projects/school/course-b/index.md.`

### Phase 2: Walk each graph neighborhood at depth 2

Using the graph infrastructure under `.claude/skills/graph/`:

- Starting from the anchor, collect all wikilink targets (outbound edges) and all pages that wikilink to the anchor (inbound edges).
- Expand to depth 2: for each neighbor, collect its neighbors.
- Deduplicate. Cap at 15 pages per concept. If the cap is hit, prefer pages with higher edge count and higher confidence bucket.
- For free-text concepts without an anchor, substitute grep against the repo for the concept string and use the top 10 matching pages as the neighborhood.

Print the two neighborhoods as short lists: anchor + neighbors with edge count.

### Phase 3: Read neighborhood bodies

Read the body of the top 8 most-connected pages in each neighborhood. Skip pages already clearly irrelevant (wrong domain, zero overlap in frontmatter tags).

### Phase 4: Synthesize bridges

Bridges are non-obvious connections between the two neighborhoods. Strong bridges:

- Shared vocabulary that isn't just both domains using the same generic word. Look for technical concepts, named patterns, tools, or people that appear in both neighborhoods.
- Structural parallels: one neighborhood solves X the same way the other solves Y.
- Implicit dependencies: concept A requires thinking that also shows up in concept B.
- Shared constraints: time pressure, a person involved in both, a technology stack overlap.
- Cross-domain analogies the user has already written somewhere (grep for "like" / "similar to" / "reminds me of" in the neighborhoods).

Weak bridges to avoid:

- Generic surface words ("system," "process," "workflow") that appear everywhere.
- Bridges built only from frontmatter tags without content backing.
- Speculation beyond what the text supports.

Aim for 3 to 6 bridges. Fewer strong bridges beats more weak ones.

### Phase 5: Format the report

Print to the terminal in this structure:

```
# Bridges: <concept A> ↔ <concept B>

## Anchors

- <concept A>: <anchor page path>
- <concept B>: <anchor page path>

## Neighborhood summary

<one paragraph each, describing what each neighborhood actually contains>

## Bridges

### Bridge 1: <short name>

<2-4 sentences on the connection>

Supporting pages:
- [[page-a]] (from <concept A>)
- [[page-b]] (from <concept B>)
- [[page-c]] (shared neighbor)

### Bridge 2: ...

## Unexplored but suggestive

<1-3 bullets of connections that didn't rise to bridge-strength but are worth naming, with 1 citation each>
```

### Phase 6: Offer to save

After the report prints, ask: "Save this to `outputs/connect-<a>-<b>-YYYY-MM-DD.md`?" If yes, write it with minimal frontmatter (`title`, `type: reference`, `last_updated`, `sources: [list of cited pages]`). If no, skip. Either way, append one line to `log.md`:

```
## [YYYY-MM-DD] query | connect: <a> ↔ <b> (<N> bridges, saved=<yes|no>)
```

## Behavior notes

- **Read-only by default.** Only the optional `outputs/` save writes anything.
- **No graph infra is not a blocker.** If `.claude/skills/graph/` scripts are not runnable, fall back to grep-based discovery of wikilinks and frontmatter.
- **Cap neighborhoods at 15 pages each.** More than that bloats context without improving bridge quality. The ranking by edge count captures the informative subset.
- **Do not invent bridges.** If the concepts genuinely don't connect in the repo, say so. Output: "No substantive bridges found. The neighborhoods don't overlap meaningfully in the current repo state." That's a useful answer — it tells the user the concepts live in different worlds.
