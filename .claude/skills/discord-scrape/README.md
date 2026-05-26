# discord-scrape skill assets

- `servers.yaml` — user-maintained source registry (friendly name → server + channel IDs).
- `scrape.sh` — deterministic helper invoked by the skill prompt (token fetch, DCE export, archive merge).

Raw Discord archive lives outside the repo at `~/.local/share/discord-scrape/<source>/`.

## Pointers

- Setup: `references/sops/discord-scrape-setup.md`
- Design: `docs/superpowers/specs/2026-04-16-discord-scrape-design.md`
- Plan: `docs/superpowers/plans/2026-04-16-discord-scrape.md`
- Prompt: `.claude/skills/discord-scrape.md`
- Command wrapper: `.claude/commands/discord-scrape.md`
