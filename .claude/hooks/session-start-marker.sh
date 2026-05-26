#!/usr/bin/env bash
# SessionStart marker for the log-nudge hook.
# Writes an epoch-seconds timestamp keyed by session_id so the Stop
# hook can compare log.md's mtime against session start.
# Owned by the session-log-hooks feature.
set -u

CACHE_DIR="$HOME/.cache/ea-hooks"
mkdir -p "$CACHE_DIR"

# Best-effort old-marker cleanup (>30d). Quiet on failure.
find "$CACHE_DIR" -maxdepth 1 -name 'session-*.start' -mtime +30 -delete 2>/dev/null || true

INPUT=$(cat)
SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

if [ -z "$SESSION_ID" ]; then
  exit 0
fi

date +%s > "$CACHE_DIR/session-${SESSION_ID}.start"
exit 0
