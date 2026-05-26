#!/usr/bin/env bash
# Session-start reminder for unsuperseded memory entries.
# Prints a one-liner if three or more candidates are sitting
# in the memory directory waiting to be promoted.
# Owned by the promote-memory skill.
set -u

# Claude Code stores auto-memory under a project-specific directory.
# The slug is derived from the absolute path of the project, with slashes
# replaced by dashes and a leading dash prepended.
project_slug() {
  printf '%s' "${CLAUDE_PROJECT_DIR:-$PWD}" | sed 's|/|-|g'
}

MEMORY_DIR="$HOME/.claude/projects/$(project_slug)/memory"
if [ ! -d "$MEMORY_DIR" ]; then
  exit 0
fi

COUNT=$(grep -L "^superseded_by:" "$MEMORY_DIR"/*.md 2>/dev/null \
  | grep -v "/MEMORY\.md$" \
  | wc -l \
  | tr -d ' ')

if [ "$COUNT" -ge 3 ]; then
  echo "reminder: $COUNT memory entries may be ready to promote — run /promote-memory to review"
fi
exit 0
