---
name: discord-scrape
description: Pull topic-filtered Discord chatter from a registered source, maintain an incremental local archive, and synthesize a research artifact to outputs/
---

# discord-scrape

Pull topic-filtered Discord chatter from servers the user is in, maintain an incremental local archive outside the repo, and synthesize a markdown artifact into `outputs/`. Raw Discord content never enters git; artifacts are anonymized and day-rounded.

**Design:** `docs/superpowers/specs/2026-04-16-discord-scrape-design.md`
**Setup:** `references/sops/discord-scrape-setup.md`

## Inputs

- `<source>` — friendly name from `.claude/skills/discord-scrape/servers.yaml`
- `<topic>` — free-text topic, quoted
- `--refresh` (optional) — ignore cursor, re-fetch the source's default window
- `--list-sources` (special) — print registered sources and exit

## Steps

### 1. Handle `--list-sources` early

If the first argument is `--list-sources`, run:

```bash
yq '.sources | keys | .[]' .claude/skills/discord-scrape/servers.yaml
```

Print the output and stop. If `sources` is empty, tell the user to populate `servers.yaml` per `references/sops/discord-scrape-setup.md` Step 6.

### 2. Preflight (fail fast with the exact fix command)

Check each in order. On any failure, print the fix line and stop.

```bash
command -v DiscordChatExporter.Cli >/dev/null \
  || echo "MISSING: DiscordChatExporter.Cli — see references/sops/discord-scrape-setup.md step 1"
command -v yq >/dev/null \
  || echo "MISSING: yq — brew install yq"
command -v jq >/dev/null \
  || echo "MISSING: jq — brew install jq"
security find-generic-password -s discord-user-token -w >/dev/null 2>&1 \
  || echo 'MISSING: Keychain entry — security add-generic-password -s discord-user-token -a "$USER" -w "<token>"'
[ "$(yq '.sources | length' .claude/skills/discord-scrape/servers.yaml)" -gt 0 ] \
  || echo "MISSING: servers.yaml has no sources — see references/sops/discord-scrape-setup.md step 6"
```

If any line printed, stop and show the user the fix. Do not proceed.

### 3. Validate the source name

```bash
yq -e ".sources.\"<source>\"" .claude/skills/discord-scrape/servers.yaml >/dev/null
```

On non-zero exit, run `yq '.sources | keys | .[]'` and print the registered sources, then stop.

### 4. Keyword expansion (approval gate)

Expand `<topic>` into 5–15 concrete keywords and short phrases. Cover:

- Literal topic terms
- Common abbreviations and synonyms
- Entity names / handles likely mentioned alongside the topic
- Adjacent jargon the community uses for this topic

Example for topic `"offer one vs offer two"`:

```
company-a, company-b, tc, comp, total comp, city-a, city-b, offer, return offer,
conversion rate, team-a, team-b, product-x, product-y
```

Present the list to the user with this exact prompt shape:

```
Proposed keywords for "<topic>":
  <keyword1>, <keyword2>, ...

OK / edit / cancel?
```

On `edit`: take his revised list. On `cancel`: stop with no side effects. Only proceed on explicit approval.

### 5. Fetch via helper

Invoke the helper. Include `--refresh` only if the user passed it.

```bash
./.claude/skills/discord-scrape/scrape.sh <source> [--refresh]
```

Capture the two output lines:

```
archive=<path-to-messages.jsonl>
channels_updated=<n>
```

If `channels_updated=0` and the archive is empty, stop and tell the user there's nothing to synthesize yet — most likely the channels are quiet in the current window, or preflight missed an access problem. Suggest `--refresh` with a longer `default_window_days` in `servers.yaml`.

### 6. Filter pass 1 — keyword grep

Read the archive and collect candidate messages. Use `jq` to keep things streaming; do not load the full JSONL into the prompt.

For each approved keyword `<kw>`:

```bash
jq -c --arg kw "<kw>" '
  select((.content // "") | ascii_downcase | contains($kw | ascii_downcase))
  | {id, timestamp, channelId, channelName, content}
' "$ARCHIVE"
```

The helper injects `channelId` and `channelName` into every archived message during extraction. Collect matching message IDs, then expand each match to ±5 messages in the same channel by timestamp proximity. Deduplicate the expanded set by `id`.

**Cap:** hard limit 2000 messages in the candidate set. If the cap trips, warn the user and truncate to the most recent 2000. Suggest narrower keywords if this happens repeatedly.

### 7. Filter pass 2 — semantic

Load the candidate set into your context. Drop messages that keyword-matched but are off-topic (stale hits, sarcasm, unrelated use of an ambiguous word). Deduplicate near-identical opinions. Cluster viewpoints.

### 8. Synthesize the artifact

Write to:

```
outputs/discord-<source>-<topic-slug>-YYYY-MM-DD.md
```

Slug: lowercase, replace whitespace/punctuation with `-`, collapse repeats, trim. Date: today, UTC.

Artifact shape:

```markdown
---
title: Discord — <source> — <topic>
type: research
source: discord
discord_source: <source>
topic: <topic>
window_start: YYYY-MM-DD
window_end: YYYY-MM-DD
message_count: N
last_updated: YYYY-MM-DD
---

# Discord — <source> — <topic>

## Summary

3–5 bullet synthesis.

## Viewpoints

Clustered opinions with `[#channel-name]` attribution and approximate dates.
Anonymized: no usernames, no user IDs. Timestamps rounded to day.

## Notable threads

- [#channel-name, 2026-04-14](discord-permalink) — one-line why-this-is-worth-rereading

## Gaps / contradictions

Where the chatter disagreed, where coverage was thin, or where you're pattern-matching on too few messages to be confident.
```

**Hard rules for the artifact:**

- No usernames, display names, nicknames, or user IDs anywhere in the body.
- Timestamps in the body are `YYYY-MM-DD` only (day granularity).
- Permalinks in "Notable threads" are OK — they link back to Discord, no leaked metadata.
- Quoted content is paraphrased unless a quote is clearly public-enough to preserve verbatim; when quoting, strip any usernames or @-mentions.
- If the candidate set was effectively empty, still write the artifact with a `## Summary` that says "No relevant messages found" plus a one-line suggestion (widen keywords, `--refresh`, adjust `default_window_days`).

### 9. Log

Append one line to `log.md`:

```
## [YYYY-MM-DD] ingest | discord-scrape <source> "<topic>" -> outputs/discord-<source>-<slug>-YYYY-MM-DD.md
```

### 10. Report

Print to the user:

- Artifact path (relative to repo root).
- Counts: N candidate messages, M after semantic filter, K clusters.
- One-line hook: the single most interesting finding.

## Promotion (not part of this skill)

This skill never writes to `context/` or project folders. If the artifact earns promotion, the user triggers it manually (e.g. a follow-up prompt to move content into a `context/` page). Keep that separation: research artifact in `outputs/`, canonical content in `context/`, and `/supersede` for the transition when it happens.

## Privacy and ToS reminders

- Token stays in Keychain. The helper loads it into `DISCORD_TOKEN` in its own subshell; do not print, log, or echo it.
- Raw archive at `~/.local/share/discord-scrape/` is local-only. Never move it into the repo.
- Keep scrapes modest. Not a mass-export tool.
