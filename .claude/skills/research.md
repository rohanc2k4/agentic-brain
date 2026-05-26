---
name: research
description: Research any topic using recent web sources (last 30 days) — runs the last30days pipeline for cross-source evidence gathering, synthesis, and citation
---

# Research

Research any topic using recent cross-source evidence from the last 30 days. Wraps the `last30days` skill pipeline.

## Inputs

- **query**: the topic or question to research (passed as arguments)
- **mode** (optional): `--quick` (fast), default (balanced), `--deep` (max recall)

## Steps

### 1. Resolve the skill root

Run in Bash:

```bash
SKILL_ROOT=""
for dir in \
  "$HOME/.claude/plugins/marketplaces/last30days-skill" \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "$HOME/.openclaw/workspace/skills/last30days" \
  "$HOME/.claude/skills/last30days"; do
  [ -n "$dir" ] && [ -f "$dir/scripts/last30days.py" ] && SKILL_ROOT="$dir" && break
done
echo "SKILL_ROOT=$SKILL_ROOT"
```

If `SKILL_ROOT` is empty, tell the user: "last30days plugin not found. Install with `/plugin marketplace add mvanhorn/last30days-skill`."

### 2. Resolve Python

```bash
LAST30DAYS_PYTHON=""
for py in python3.14 python3.13 python3.12 python3; do
  command -v "$py" >/dev/null 2>&1 || continue
  "$py" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null || continue
  LAST30DAYS_PYTHON="$py"
  break
done
echo "PYTHON=$LAST30DAYS_PYTHON"
```

If no Python 3.12+ found, tell the user to install it.

### 3. X handle resolution (optional)

If the topic could have its own X/Twitter account (person, brand, product, company), do a quick WebSearch:

```
WebSearch("{TOPIC} X twitter handle site:x.com")
```

If a verified handle is found, add `--x-handle={handle}` (without @) to the command. Skip this for generic concepts.

### 4. Run the pipeline

```bash
"${LAST30DAYS_PYTHON}" "${SKILL_ROOT}/scripts/last30days.py" {query} --emit=compact
```

Modes:
- Default: balanced recall and speed
- `--quick`: fast iteration, fewer sources
- `--deep`: maximum recall, more latency
- `--emit=json`: for structured downstream consumption
- `--search=reddit,x,grounding`: restrict to specific sources

### 5. Synthesize results

**Rules:**

1. **Synthesize, don't summarize.** Extract key facts, then build a unified narrative across sources. Lead with patterns that appear in multiple clusters.

2. **Ground in actual research.** Use exact names, specific quotes, and what sources actually say. Do NOT fill gaps with training data.

3. **Source weighting (highest to lowest signal):**
   - Cross-cluster corroboration (same evidence across sources = strongest)
   - Reddit top comments (quote directly when upvotes high)
   - YouTube transcript highlights (quote and attribute to channel)
   - X/Twitter @handles (quote with engagement context)
   - Hacker News (cite as "per HN")
   - Web/Brave/Serper (cite only when social sources don't cover a fact)

4. **Citation format:** Cite the single strongest source per point: "per @handle" or "per r/subreddit". Save engagement metrics for a stats section.

5. **Empty results:** State what's missing. Don't fill the gap with training data.

6. **Contradictions:** Present both sides with attribution.

### 6. Structure output by query type

**Comparison queries ("X vs Y"):**

```
## Quick Verdict
[1-2 sentences: community preference + why]

## [Entity A]
**Sentiment:** [Positive/Mixed/Negative] (N mentions)
**Strengths / Weaknesses**

## [Entity B]
[Same structure]

## Head-to-Head table

## Bottom Line
Choose A if... Choose B if...
```

**Recommendation queries ("best X", "top X"):**

```
Most mentioned:
- [Name] — Nx mentions
  Sources: @handle, r/subreddit, [YouTube channel]

Notable mentions: [1-2 mention items]
```

**General research:**

Lead with the synthesized finding, then supporting evidence by source weight, then gaps/caveats.

### 7. Follow-up

After research completes, treat yourself as an expert on the topic. Answer follow-ups from the findings. Only run new research if the user asks about a DIFFERENT topic.

## Required API Keys

- **One reasoning provider required:** `GOOGLE_API_KEY` (Gemini), `OPENAI_API_KEY`, or `XAI_API_KEY`
- **Recommended:** `BRAVE_API_KEY` (web search) or `SERPER_API_KEY` (fallback)
- **Optional:** `SCRAPECREATORS_API_KEY` (Reddit/TikTok/Instagram), `XAI_API_KEY` (X search)

## Security

- Does NOT post, like, or modify content on any platform
- Does NOT access personal accounts
- Does NOT share API keys between providers
