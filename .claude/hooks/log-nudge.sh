#!/usr/bin/env bash
# Stop hook that nudges when the session did repo-modifying work but
# log.md wasn't touched. Self-clearing: once log.md is written,
# the mtime check passes and subsequent Stop events stay silent.
# Owned by the session-log-hooks feature.
set -u

CACHE_DIR="$HOME/.cache/ea-hooks"
REPO="${CLAUDE_PROJECT_DIR:-$PWD}"
LOG_FILE="$REPO/log.md"

INPUT=$(cat)
SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
TRANSCRIPT=$(printf '%s' "$INPUT" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

# Fail open on any missing input.
[ -n "$SESSION_ID" ] || exit 0
[ -n "$TRANSCRIPT" ] && [ -r "$TRANSCRIPT" ] || exit 0

MARKER="$CACHE_DIR/session-${SESSION_ID}.start"
[ -r "$MARKER" ] || exit 0
[ -r "$LOG_FILE" ] || exit 0

# Did the session call a repo-modifying tool?
if ! grep -qE '"name":[[:space:]]*"(Edit|Write|Bash)"' "$TRANSCRIPT"; then
  exit 0
fi

MARKER_TS=$(cat "$MARKER" 2>/dev/null)
LOG_TS=$(stat -f %m "$LOG_FILE" 2>/dev/null || stat -c %Y "$LOG_FILE" 2>/dev/null)

# If we can't read either timestamp, fail open.
[ -n "$MARKER_TS" ] && [ -n "$LOG_TS" ] || exit 0

# log.md already updated this session → silent.
if [ "$LOG_TS" -gt "$MARKER_TS" ]; then
  exit 0
fi

# Emit blocking JSON so the model gets prompted to write the entry.
cat <<'JSON'
{"decision":"block","reason":"You did repo-modifying work this session (Edit/Write/Bash) but log.md wasn't updated. Before stopping, append one or more action lines in the form `## [YYYY-MM-DD] ingest|update|query|lint | <description>` covering the meaningful actions, plus a session-summary line for the overall session. Then you can stop."}
JSON
exit 0
