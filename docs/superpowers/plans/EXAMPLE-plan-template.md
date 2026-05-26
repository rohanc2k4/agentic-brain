---
title: "EXAMPLE — Implementation Plan Template"
type: plan-template
spec: docs/superpowers/specs/EXAMPLE-spec-template.md
last_updated: 2026-05-26
---

# EXAMPLE — Implementation Plan Template

A plan is the ordered list of tasks that turns an approved spec into shipped code. Its job is to make every step explicit so that you (or Claude executing the plan in subagent-driven mode) can knock them out one at a time without re-deciding architecture mid-flight.

Save plans at `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`. Link the corresponding spec in the frontmatter so the pair stays connected.

---

## Pre-flight

Quick sanity checks before starting. Useful when picking up a stale plan weeks later.

- [ ] Spec is approved and at the path in frontmatter
- [ ] No conflicting work in flight on the same files
- [ ] Branch cut (`feat/<topic>`) if the change is non-trivial

## Tasks

Each task is small enough to complete and verify in one short focused session. Tasks are ordered so that earlier tasks don't depend on later ones. Each task has a clear acceptance criterion.

### T1 — Scaffolding

**Goal**: create the skill file at `.claude/skills/<name>.md` with frontmatter, one-paragraph description, and a placeholder body. Mirror the slash-command at `.claude/commands/<name>.md`.

**Acceptance**: `/help` shows the new command. Invoking it returns the placeholder body without erroring.

### T2 — Scanner

**Goal**: implement the file walker that produces the in-memory record list.

**Acceptance**: a unit-test script or one-shot bash call produces a sorted JSON dump of all matching records.

### T3 — Binner

**Goal**: group records by the configured field. Stable ordering inside each bin.

**Acceptance**: given a fixture set, returns the expected bins in a deterministic order.

### T4 — Renderer

**Goal**: render the binned records to markdown matching the design spec exactly.

**Acceptance**: byte-identical output across two consecutive runs on the same input.

### T5 — Differ + writer

**Goal**: diff the rendered output against the current auto-zone, present to the user, write on approval.

**Acceptance**: changes outside the auto-zone are never touched. Reject path leaves the file unchanged.

### T6 — Edge cases

Knock out each edge case from the spec one at a time. Add a fixture per case.

**Acceptance**: every edge case from the spec has a fixture and the skill behaves as specified.

### T7 — Docs

**Goal**: update the skill list in `CLAUDE.md` and `README.md`. Add to the slash-command index.

**Acceptance**: skill is discoverable from both files.

### T8 — Manual smoke

**Goal**: run the skill on real project data. Capture the output. Confirm it matches expectations.

**Acceptance**: at least one real-world invocation produces a useful diff. Iterate the renderer if formatting feels off.

## Post-flight

- [ ] Spec linked from skill .md
- [ ] CHANGELOG / `log.md` entry added
- [ ] Commit message uses conventional commit prefix (`feat`, `fix`, `docs`, etc.)
- [ ] If the skill writes files, confirm a dry-run / diff-and-approve gate exists

## When to deviate from the plan

If a task uncovers something the spec missed, stop and update the spec. Don't silently expand scope inside a task. The plan should always trail the spec, not lead it.
