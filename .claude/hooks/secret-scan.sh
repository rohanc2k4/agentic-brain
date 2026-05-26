#!/usr/bin/env bash
# PostToolUse hook: scan files written by Write/Edit tools for
# credential-shaped strings. Warns (does not block) by emitting
# additionalContext. Tidiness tool, private-repo threat model.
# Owned by the privacy-filter feature.
#
# Manual test: see .claude/hooks/test-secret-scan.sh
set -u

INPUT=$(cat)

TOOL=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
case "$TOOL" in
  Write|Edit) ;;
  *) exit 0 ;;
esac

FILE=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -n "$FILE" ] && [ -r "$FILE" ] || exit 0

# Patterns: label|regex. First match wins.
# Order matters: sk-ant- must be checked before generic sk-.
PATTERNS=(
  'Anthropic API key|sk-ant-[A-Za-z0-9_-]{20,}'
  'OpenAI API key|sk-[A-Za-z0-9]{20,}'
  'AWS access key|AKIA[0-9A-Z]{16}'
  'GitHub personal access token|ghp_[A-Za-z0-9]{20,}'
  'GitHub OAuth token|gho_[A-Za-z0-9]{20,}'
  'GitHub app install token|ghs_[A-Za-z0-9]{20,}'
  'GitHub fine-grained PAT|github_pat_[A-Za-z0-9_]{20,}'
  'Slack token|xox[abpr]-[A-Za-z0-9-]{10,}'
  'Google API key|AIza[0-9A-Za-z_-]{35}'
  'Private key block|-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----'
  'JWT|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'
)

MATCH_LABEL=""
for entry in "${PATTERNS[@]}"; do
  label="${entry%%|*}"
  regex="${entry#*|}"
  if grep -qE -- "$regex" "$FILE" 2>/dev/null; then
    MATCH_LABEL="$label"
    break
  fi
done

[ -n "$MATCH_LABEL" ] || exit 0

# Emit additionalContext JSON. Escape double quotes in file path.
ESCAPED_FILE=${FILE//\"/\\\"}
cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"secret-scan: ${ESCAPED_FILE} contains what looks like a ${MATCH_LABEL}. Scrub it if unintentional."}}
JSON
exit 0
