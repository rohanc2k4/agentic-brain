---
title: Communication Style
type: rule
last_updated: 2026-04-13
sources: []
---

# Communication Style

Rules for how Claude should help you draft messages, emails, and responses. Also rules for how Claude itself should communicate with you in this repo.

## Negotiation and personal connections

When advising on negotiations or communications with people you have **personal relationships** with (e.g., a family friend or long-time mentor at the negotiating company), prioritize **transparency and directness** over tactical leverage plays.

- **Do not** suggest deflecting, stalling, or withholding information when a personal connection asks a direct question.
- **Do** match tone to the relationship: warmer, more conversational, more personable.
- Reserve tactical advice (withholding comp, creating competing-offer pressure, etc.) for arms-length negotiations with recruiters or companies where there's no personal connection.

**Why:** the relationship is usually worth more than marginal negotiating advantage. Dodging direct questions from a personal connection damages trust.

**How to apply:** before drafting a negotiation message, identify whether the recipient is a personal connection or an arms-length party. If personal, lean transparent and warm. If arms-length, tactical framing is fine.

## Default tones

**Internal messages** (immediate teammates, direct manager, peers): casual with a touch of professional. Friendly, conversational, not stiff. Avoid formalities like "Hi [Name], I hope this finds you well", just get to the point in a relaxed register.

**External / formal content** (emails to advisors, negotiation replies, anything that goes outside the immediate team): professional and warm. Still personable, not corporate-stiff, but composed and respectful of the recipient's role.

## Pet peeves

- **No em dashes.** Do not use em dashes in drafted messages or in Claude's own writing in this repo. Rewrite with commas, periods, parentheses, or colons instead.
- **No AI slop in markdown.** The rules: no em dashes; no Tier 1 vocabulary (`leverage`, `robust`, `comprehensive`, `seamless`, `holistic`, `actionable`, `utilize`, `cutting-edge`, `showcasing`, etc.); no clusters of Tier 2 cluster words (`harness`, `elevate`, `empower`, `streamline`, `bolster`, `nuanced`, `crucial`, `myriad`, `transformative`); no "it's not X, it's Y" constructions, rewrite as direct claims; minimal `**bold**` (at most one bolded phrase per major section, only when the emphasis genuinely earns it); no formulaic openings like "In today's world" or "When it comes to"; no hollow intensifiers ("genuinely," "truly," "it's worth noting"); no compulsive rule-of-three patterns; prefer prose over bullet sprawl when prose flows. Voice target: a smart founder taking notes, not a chatbot rendering a wiki.

  **For substantial new markdown work** (new files, large rewrites in `projects/`, `context/`, `docs/`, `outputs/`, `references/`), apply these rules in the first draft, then dispatch a finishing-pass agent with an AI-writing-auditor profile if you have one. For small edits (one-line tweaks, link fixes, frontmatter touches), self-apply the rules without dispatching a second agent.

  **Why:** a reader's eye gets calibrated to AI-isms. Anything bolded-up, em-dashed, or Tier-1-vocab-laden reads as un-edited and loses trust.

  **Hook option:** if you want this enforced mechanically rather than as a default, the `update-config` skill can wire a PostToolUse hook on Write/Edit for `*.md` that flags AI-ism candidates before the file ships.

## Draft replies format (copy-paste safety)

Whenever Claude drafts a reply meant to be sent (Slack, email, DM, etc.), render the draft inside a single fenced code block as plain text. No markdown formatting inside: no backticks on identifiers, no `**bold**`, no `> quotes`, no bullet or numbered list markers, no headers. Use blank lines between paragraphs and plain prose lists ("First, ... Second, ...").

**Why:** drafts get copied straight into the target surface (Slack, Gmail). Markdown syntax pastes literally and creates formatting noise to strip by hand.

**How to apply:** separate "analysis" (normal markdown, can be rich) from "the draft reply" (fenced plain-text block). Only the draft itself is constrained; surrounding commentary stays normal.

## Information format (when Claude is advising)

No single format, pick the one that fits the information:

- **Bullets** for lists of independent items or quick scans
- **Numbered options** when there's a decision to make between alternatives, or when order matters
- **Tables** for comparisons across multiple dimensions
- **Paragraphs** for reasoning chains, context, or nuance that would be flattened by bullets

Default to whichever actually helps comprehension for the specific content. Don't bullet-ify prose that flows as paragraphs, and don't paragraph-ify a list of discrete items.
