# Daily Note Tag Vocabulary

A frozen, five-tag vocabulary for inline captures in daily notes. These tags are the structured signal that `/close-week` and `/close-month` aggregate into rollup notes. Do not invent new tags — additions require an explicit edit to this file.

## The tags

| Tag | Meaning | Example |
|---|---|---|
| `#idea` | A thought worth potentially graduating to a canonical page later. | `#idea maybe ArgoCD should cache chart templates between runs` |
| `#decision` | A decision made today. Pair with a full entry in `decisions/log.md` when it carries weight. | `#decision chose Helm over Kustomize for the policy-server chart` |
| `#blocker` | Something blocking progress right now. | `#blocker waiting on a teammate to merge dependency PR` |
| `#win` | A notable accomplishment worth remembering. | `#win got the deploy syncing on first try` |
| `#followup` | A thread to pick up later. | `#followup ask manager about signing policy` |

## Placement rules

Tags match **only at the start of a line**, optionally after a bullet marker (`-`, `*`, or `1.`), exact case, followed by whitespace, a colon, or end-of-line. Tags inside fenced code blocks or backticks are ignored.

The canonical regex used by `/close-week` and `/close-month` (applied per-line, after stripping fenced code blocks):

```
^\s*(?:[-*]\s+|\d+\.\s+)?#(idea|decision|blocker|win|followup)(?::|\b)
```

**Matches:**
- `#idea use kustomize`
- `- #blocker teammate PR not merged`
- `#decision: stick with Helm`
- `1. #win ArgoCD working`

**Does not match (intentional):**
- `Here's my #idea about this` — tag mid-sentence, too loose to trust.
- `#ideation` — word continuation, wrong tag.
- `` `#idea` `` inside backticks or code blocks — documentation or examples, not real captures.
- `##idea` — markdown heading that happens to look like a tag.

## Why the strict placement

Rollups are only useful if aggregation is trustworthy. Loose matching produces false positives from code snippets, documentation (including this file), and meta-discussion, which erodes trust in the rollup. Strict placement also enforces cleaner capture style: a tag on its own line is more likely to be a real, promotable thought than one buried in a paragraph.

## Why only five

Tag vocabs rot when they grow. Five is small enough to remember, broad enough to catch 90% of what rollups need. Adding a sixth tag requires an explicit edit to this file and a bump to the regex in the rollup skills. Don't invent tags inline.

## Mental model

| Tag | Lives on | Maybe graduates to |
|---|---|---|
| `#idea` | Daily note → weekly rollup | Canonical page in `context/` or `projects/*/pages/` via `/graduate` |
| `#decision` | Daily note → weekly rollup | `decisions/log.md` entry |
| `#blocker` | Daily note → weekly rollup | `priorities.md` "blockers" list on project |
| `#win` | Daily note → weekly rollup → monthly rollup | Referenced in retrospectives; seed for "top wins" sections |
| `#followup` | Daily note → weekly rollup | Either done and cleared, or promoted to a project/decision entry |
