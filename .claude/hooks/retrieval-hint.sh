#!/usr/bin/env bash
# UserPromptSubmit hook. Thin wrapper around retrieval-hint.py.
exec python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/retrieval-hint.py"
