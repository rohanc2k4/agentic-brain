# executive-assistant

A file-based executive assistant / second brain for [Claude Code](https://claude.com/claude-code).

Markdown notes. Opinionated skills. Hooks that nudge good habits. A wikilink-driven knowledge graph that grows as you use it. Obsidian-compatible so you can browse with a UI when you want, but the source of truth is plain markdown.

## What's in here

```
.claude/skills/    ~15 workflows you can /invoke as slash commands
.claude/hooks/     session start, post-write, and stop hooks
.claude/rules/     three preference files you should edit
templates/         scaffolds for daily/weekly/monthly notes
docs/superpowers/  spec + plan templates for designing new skills
CLAUDE.md          the system prompt Claude Code sees each session
```

## The skills

| Command | What it does |
|---|---|
| `/morning-coffee` | Daily kickoff: reads your calendar, packs the day, writes `daily/YYYY-MM-DD.md` |
| `/close-week` | Weekly rollup from daily notes + log + git |
| `/close-month` | Monthly rollup from weekly rollups |
| `/show-priorities` | Regenerate the project dashboard in `priorities.md` |
| `/promote-memory` | Promote stable memory entries to canonical `context/` files |
| `/supersede` | Mark a file as replaced; rewrite every wikilink that pointed at the old slug |
| `/crystallize` | Distill the current session's primary thread into a wiki page |
| `/graduate` | Promote `#idea` captures from daily notes to canonical pages |
| `/drift` | Compare stated priorities against what your git + calendar actually show |
| `/connect` | Bridge two concepts via the knowledge graph |
| `/trace` | Show how your thinking on a topic has evolved over time |
| `/graph` | Query the wikilink + frontmatter graph; per-page confidence buckets |
| `/lint` | Scan for stale dates, broken wikilinks, orphan pages, missing frontmatter |
| `/research` | Last-30-days web-source research pipeline |
| `/discord-scrape` | Topic-filtered Discord chatter into a synthesis artifact |

## Quick start

```bash
git clone https://github.com/rohanc2k4/executive-assistant.git
cd executive-assistant
# Open in Claude Code
```

Then edit `CLAUDE.md` to your taste, fill `context/` with your own people / orgs / priorities, and start the daily rhythm with `/morning-coffee`.

## Design principles

- **Memory is staging, `context/` is canonical.** Auto-memory captures the conversational firehose. `context/` is curated, versioned, trusted. Promote with `/promote-memory`, mark replacements with `/supersede`.
- **Every page has frontmatter.** Title, type, last_updated, sources. Wikilinks for cross-reference, `[Source: ...]` for citations, `> CONTRADICTION:` flags when sources disagree.
- **Two logs, distinct roles.** `log.md` for activity. `decisions/log.md` for decisions with reasoning. Never conflate them.
- **Skills only when stable.** If you've asked Claude the same thing three times and the workflow has settled, formalize it as a skill. Otherwise, do it conversationally.
- **Archives over deletion.** When content goes dormant, move to `archives/`. Git is the ultimate backstop; archives keep the recent stuff one directory away.

## Inspired by

Andrej Karpathy's tweet on using Obsidian + Claude Code as an LLM-native wiki stack of .md files.

## License

MIT.
