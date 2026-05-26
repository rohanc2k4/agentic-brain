---
title: "EXAMPLE — Design Spec Template"
type: spec-template
last_updated: 2026-05-26
---

# EXAMPLE — Design Spec Template

A spec is the design doc you write BEFORE you start coding a new skill. Its job is to capture *what you're building and why* so that you (or Claude) can write a focused implementation plan next, and so future-you can understand the choices six months later.

Use this file as a starting structure when you run `/brainstorming` (or just sit down to design a skill). Save the resulting spec at `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. Pair it with a plan at `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`.

---

## Problem

One paragraph. What's the actual problem you're trying to solve? When did it bite? What's the cost of doing nothing?

> Example: "Every week I lose 20 minutes reconciling my `priorities.md` against what's actually active. The dashboard at the bottom drifts and I don't notice until I'm planning the week."

## Goal

One sentence. The single outcome that says "we shipped it." Avoid scope creep here — additional goals belong in a separate spec.

> Example: "Regenerate the project dashboard in `priorities.md` from project frontmatter, behind a diff-and-approve gate."

## Non-goals

Bullet list. What this spec is NOT trying to do. This is where you put the temptations that would otherwise grow the scope.

> Example:
> - Not auto-detecting which projects to show (frontmatter `priority` field is the source of truth).
> - Not rewriting the rest of `priorities.md`; only the dashboard auto-zone.
> - Not running on every commit; user-triggered only.

## User experience

How a user invokes the skill and what they see. Be concrete — show the actual command, the actual prompts, the actual output snippets.

> Example:
> ```
> /show-priorities
> ```
> ↓ Skill reads `projects/**/README.md` frontmatter, bins by `priority` field, builds a candidate dashboard. Shows a diff against the current `priorities.md` auto-zone (between HTML comment markers). User approves or rejects.

## Inputs and outputs

What does the skill read? What does it write? Cite specific files and frontmatter fields.

> Example:
> - **Reads**: every `projects/**/README.md` with frontmatter fields `title`, `priority`, `domain`, `deadline`, `blockers`.
> - **Writes**: the auto-zone in `context/priorities.md` between `<!-- show-priorities:start -->` and `<!-- show-priorities:end -->`. Nothing else in the file is touched.

## Components

Break the skill into smaller units that each have one clear purpose. For each unit: what it does, how it's used, what it depends on.

> Example:
> - **Scanner** — walks `projects/**/README.md`, parses YAML frontmatter, returns a list of project records.
> - **Binner** — groups records by `priority` field (this-week / this-month / parked / not-priority).
> - **Renderer** — writes each bin to markdown, stable ordering by `deadline` ASC then `title` ASC.
> - **Differ** — diffs against the current auto-zone, presents to user.
> - **Writer** — replaces the auto-zone in place, leaves the rest of the file untouched.

## Edge cases

The boring but important ones. Each gets a bullet and a planned behavior.

> Example:
> - Project README missing `priority` field → exclude from dashboard, warn the user.
> - Two projects with the same `title` → include both, suffix with `(domain)`.
> - Auto-zone markers missing → bail out, ask user to add them.

## Open questions

Things you don't yet know the answer to. Resolving them moves them out of this section into the spec proper.

> Example:
> - Should the diff present per-bin or whole-file? (Probably whole-file, since reordering matters.)

## Implementation hand-off

Once this spec is approved, the next step is `docs/superpowers/plans/<date>-<topic>.md` — the task-by-task implementation plan. Specs answer *what + why*; plans answer *how, in order*.
