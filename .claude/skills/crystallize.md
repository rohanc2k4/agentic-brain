---
name: crystallize
description: Distill a research, debugging, or discussion thread from the current session into a structured wiki page under context/, references/, or projects/*/pages/.
---

# /crystallize

Capture a thread from the current session as a durable wiki page. Explicit-invocation only; no auto-detection.

## When to invoke

After a session thread that produced findings worth keeping beyond the session: research into a topic, a debugging resolution with a non-obvious root cause, a discussion that landed on a specific architectural or process decision, a distilled summary of a long back-and-forth.

Don't invoke for: transient work (an edit that landed fine, a one-off question already answered in code), content that already has a better home (a project README, a decision log entry), or memory-layer observations (those belong in the auto-memory flow and `/promote-memory`).

## Invocation

```
/crystallize [topic-hint]
```

`topic-hint` is optional but helpful when the session covered multiple threads. Free-form string.

## Flow

### 1. Scope the thread

Scan the current session. Identify the thread matching the hint (or the dominant thread if no hint). If the hint is ambiguous or multiple threads plausibly match, list them and ask the user to pick.

### 2. Propose destination

Pick one of:

| Bucket | When |
|---|---|
| `context/` (topic-level file) | The finding is a durable fact about a person, org, or concept the repo already tracks. |
| `references/` | The finding is external domain knowledge (API behavior, library internals, formal definition). |
| `projects/<domain>/<slug>/pages/` | The finding is scoped to a specific project's working knowledge. |

Show the proposed path and a one-sentence justification. Offer to override.

### 3. Draft the page

Structure:

```
---
title: <Human title>
type: reference | concept | finding | resolution
last_updated: YYYY-MM-DD
sources:
  - session: 2026-04-19
  - url: https://...         # if web fetch was used
  - file: path/to/file.md    # if repo file was referenced
---

# <Human title>

<One-paragraph summary: what was investigated, what was concluded.>

## Key findings

- <Fact or conclusion>. [Source: session turn / url / file]
- ...

## Background / context

<Why this matters, what led to the investigation. Short.>

## Open questions

<If any — things that surfaced but weren't resolved. Omit section if none.>

## Connections

- [[related-page]] — one-line relation
- [[other-page]] — one-line relation
```

Cite every substantive claim. Session-turn citations use `[Source: session 2026-04-19]`; external content uses the URL or file path.

### 4. Show diff and get approval

Present the proposed file path and the full content in a fenced block. Wait for approve / revise / cancel.

### 5. On approval

1. Write the file.
2. Find the most relevant index page (e.g., for `context/orgs/<org>/X.md` the index is `context/orgs/<org>/index.md`; for `references/X.md` no index, skip; for `projects/<slug>/pages/X.md` the index is that project's README). Offer to add a `[[new-page]]` link in the right section, show the diff, ask approval before writing.
3. Log the action to `log.md`: `## [YYYY-MM-DD] crystallize | <topic> → <path>`.
4. Print a one-line confirmation.

## Non-goals

- Auto-detection of "completed threads." User invokes explicitly.
- Cross-session crystallization. Current session only.
- Multi-thread per call. One call, one thread.
- Replacing `/promote-memory` (which handles stable auto-memory observations, a different source) or `decisions/log.md` entries (which capture decisions with reasoning, not research findings).

## Example invocations

- `/crystallize` — after a long thread, no hint needed, one dominant topic.
- `/crystallize MPI collective algorithms` — disambiguating when the session covered multiple things.
- `/crystallize root cause of the deploy sync failure` — debugging resolution worth capturing for future selves.
