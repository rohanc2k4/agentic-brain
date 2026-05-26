# Proactive Skill Recommendations

Three wiki-maintenance skills should be offered inline when their trigger fires, not only when the user thinks to ask. Surface them as a short suggestion with the reason; don't run them without approval.

## `/crystallize`

**Trigger:** the current session produced a substantive, reusable thread worth a wiki page. Signals:
- A focused research / debugging / design dive with durable conclusions
- Decisions or frameworks that will be referenced again
- A stretch of ~15 minutes or more on one topic with a concrete output

**Do not trigger for:** routine edits, one-off answers, status checks, or activity that already lives in a project README.

**How to surface:** "This thread looks wiki-worthy (topic: X). Want to `/crystallize` it into `<proposed destination>`?"

## `/supersede`

**Trigger:** a newer canonical file has been created, edited, or identified that makes an older file stale or redundant. Signals:
- Just wrote a `context/*` file that covers what a `memory/*` entry already stored
- Edited a page in a way that directly contradicts another page
- Noticed two files claiming authority over the same entity/topic

**How to surface:** "`<old>` looks superseded by `<new>`, want to `/supersede <old> <new>`?" Include the specific pair; don't be vague.

## `/promote-memory`

**Trigger:** during conversation, a memory entry visibly hardens (confirmed multiple times, stable, fits a clear `context/` slot). Also: SessionStart hook already nudges when 3+ unsuperseded entries exist, respect that nudge and don't re-flag the same session.

**How to surface:** "`memory/<entry>` looks ready to promote, it fits `context/<slot>`. Want to run `/promote-memory`?"

## Discipline

- One suggestion per trigger, not a dashboard of options.
- Always name the specific file/pair, never "you might want to crystallize something."
- If the user declines, don't re-suggest the same thing in the same session.
- Suggestions go in normal prose, not as blocking prompts.

**Why:** these skills are the bridge from staging (memory, loose session output) to canonical wiki. If the user has to remember to run them, the wiki decays. If they auto-run, false positives pollute `context/`. Inline recommendations with judgment are the middle path.
