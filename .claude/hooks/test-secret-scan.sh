#!/usr/bin/env bash
# Manual test harness for secret-scan.sh. Synthesizes example tokens
# at runtime so this file itself doesn't contain matchable strings.
set -e
HOOK="$(dirname "$0")/secret-scan.sh"

ANT_PREFIX='sk-ant'
ANT_TOKEN="${ANT_PREFIX}-test1234567890abcdefghij"
AWS_TOKEN='AKIA'"IOSFODNN7EXAMPLE"

run() {
  local label="$1" file="$2" tool="$3" expect="$4"
  local out
  out=$(echo '{"tool_name":"'"$tool"'","tool_input":{"file_path":"'"$file"'"}}' | "$HOOK")
  if [ "$expect" = "silent" ]; then
    [ -z "$out" ] && echo "OK: $label" || { echo "FAIL: $label — got $out"; return 1; }
  else
    echo "$out" | grep -q "$expect" && echo "OK: $label" || { echo "FAIL: $label — got $out"; return 1; }
  fi
}

echo 'just plain markdown' > /tmp/ea-clean.md
echo "oops $ANT_TOKEN pasted" > /tmp/ea-ant.md
echo "cfg $AWS_TOKEN end" > /tmp/ea-aws.md
PEM_BEGIN='-----BEGIN'' RSA PRIVATE KEY-----'
printf '%s\nMIIEowIBAAKCAQEA...\n' "$PEM_BEGIN" > /tmp/ea-pem.md

run "clean file → silent"        /tmp/ea-clean.md Write silent
run "Anthropic token → warning"  /tmp/ea-ant.md   Write "Anthropic API key"
run "AWS token → warning"        /tmp/ea-aws.md   Write "AWS access key"
run "PEM block → warning"        /tmp/ea-pem.md   Edit  "Private key block"
run "Read tool → silent"         /tmp/ea-ant.md   Read  silent
run "missing file → silent"      /tmp/ea-nope.md  Write silent

rm -f /tmp/ea-clean.md /tmp/ea-ant.md /tmp/ea-aws.md /tmp/ea-pem.md
echo "--- all tests passed ---"
