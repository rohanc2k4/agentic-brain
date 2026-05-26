#!/usr/bin/env bash
# discord-scrape helper
#
# Fetches new Discord messages for a registered source via DiscordChatExporter,
# merges them into a local JSONL archive, and updates a per-channel cursor.
#
# Usage: scrape.sh <source-name> [--refresh] [--parallel N]
#        scrape.sh --help
#
# Reads: .claude/skills/discord-scrape/servers.yaml
#        macOS Keychain entry 'discord-user-token'
# Writes: ${DISCORD_SCRAPE_HOME:-~/.local/share/discord-scrape}/<source>/{messages.jsonl,cursor.json,meta.json}
# Prints: archive=<path>
#         channels_updated=<n>

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scrape.sh <source-name> [--refresh] [--parallel N]
       scrape.sh --help

Fetches new messages for a registered source and merges into the local archive.
Pass --refresh to ignore the cursor and re-fetch the default window.
Pass --parallel N to run up to N channel fetches concurrently (default: 4).

Prerequisites (see references/sops/discord-scrape-setup.md):
  - DiscordChatExporter.Cli on PATH
  - mikefarah/yq on PATH
  - jq on PATH
  - macOS Keychain entry: security add-generic-password -s discord-user-token -a "$USER" -w '<token>'
EOF
}

die() {
  printf 'scrape.sh: %s\n' "$1" >&2
  exit 1
}

# -------- arg parsing --------

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

SOURCE=""
REFRESH=0
MAX_PARALLEL=4
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --refresh) REFRESH=1; shift ;;
    --parallel)
      shift
      [[ $# -gt 0 ]] || die "--parallel requires an integer argument"
      MAX_PARALLEL="$1"
      shift
      ;;
    -*) die "unknown flag: $1" ;;
    *)
      if [[ -z "$SOURCE" ]]; then SOURCE="$1"; shift
      else die "unexpected positional arg: $1"
      fi
      ;;
  esac
done
[[ -z "$SOURCE" ]] && die "missing <source-name>; run with --help"
[[ "$MAX_PARALLEL" =~ ^[0-9]+$ ]] || die "--parallel must be an integer, got: $MAX_PARALLEL"
[[ "$MAX_PARALLEL" -ge 1 ]] || die "--parallel must be >= 1"

# -------- preflight --------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVERS_YAML="$SCRIPT_DIR/servers.yaml"
[[ -f "$SERVERS_YAML" ]] || die "servers.yaml not found at $SERVERS_YAML"

command -v DiscordChatExporter.Cli >/dev/null \
  || die "DiscordChatExporter.Cli not on PATH. See references/sops/discord-scrape-setup.md step 1."
command -v yq >/dev/null \
  || die "yq not on PATH. brew install yq (mikefarah variant)."
command -v jq >/dev/null \
  || die "jq not on PATH. brew install jq."

if ! yq --version 2>&1 | grep -qi "mikefarah\|github.com/mikefarah"; then
  die "wrong yq variant. Need mikefarah/yq (Go). See references/sops/discord-scrape-setup.md step 2."
fi

if ! TOKEN="$(security find-generic-password -s discord-user-token -w 2>/dev/null)"; then
  die "no Keychain entry 'discord-user-token'. Run: security add-generic-password -s discord-user-token -a \"\$USER\" -w '<token>'"
fi
[[ -n "$TOKEN" ]] || die "Keychain entry 'discord-user-token' is empty."
export DISCORD_TOKEN="$TOKEN"
unset TOKEN

if ! yq -e ".sources.\"$SOURCE\"" "$SERVERS_YAML" >/dev/null 2>&1; then
  printf 'scrape.sh: source "%s" not in servers.yaml.\nRegistered sources:\n' "$SOURCE" >&2
  yq '.sources | keys | .[]' "$SERVERS_YAML" >&2 || echo "  (none)" >&2
  exit 2
fi

# -------- paths --------

ARCHIVE_HOME="${DISCORD_SCRAPE_HOME:-$HOME/.local/share/discord-scrape}"
ARCHIVE_DIR="$ARCHIVE_HOME/$SOURCE"
MESSAGES_JSONL="$ARCHIVE_DIR/messages.jsonl"
CURSOR_JSON="$ARCHIVE_DIR/cursor.json"
META_JSON="$ARCHIVE_DIR/meta.json"
mkdir -p "$ARCHIVE_DIR"
[[ -f "$MESSAGES_JSONL" ]] || : > "$MESSAGES_JSONL"
[[ -f "$CURSOR_JSON" ]] || echo '{}' > "$CURSOR_JSON"

SCRATCH="$(mktemp -d -t discord-scrape.XXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT

# -------- read source config --------

SERVER_ID="$(yq -r ".sources.\"$SOURCE\".server_id" "$SERVERS_YAML")"
SERVER_NAME="$(yq -r ".sources.\"$SOURCE\".server_name // \"\"" "$SERVERS_YAML")"
WINDOW_DAYS="$(yq -r ".sources.\"$SOURCE\".default_window_days // 60" "$SERVERS_YAML")"
CHANNEL_COUNT="$(yq -r ".sources.\"$SOURCE\".channels | length" "$SERVERS_YAML")"
[[ "$CHANNEL_COUNT" -gt 0 ]] || die "source '$SOURCE' has no channels"

jq -n \
  --arg source "$SOURCE" \
  --arg server_id "$SERVER_ID" \
  --arg server_name "$SERVER_NAME" \
  --arg updated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{source: $source, server_id: $server_id, server_name: $server_name, last_run: $updated}' \
  > "$META_JSON"

# -------- per-channel fetch (parallel) --------

fetch_channel() {
  local CHANNEL_ID="$1"
  local CHANNEL_NAME="$2"
  local AFTER="$3"
  local OUT="$SCRATCH/$CHANNEL_ID.json"
  local LOG="$SCRATCH/$CHANNEL_ID.log"

  printf '[%s] fetching channel %s (%s) after %s\n' "$SOURCE" "$CHANNEL_ID" "$CHANNEL_NAME" "$AFTER" >&2

  if ! DiscordChatExporter.Cli export \
        -c "$CHANNEL_ID" \
        -f Json \
        -o "$OUT" \
        --after "$AFTER" \
        >"$LOG" 2>&1; then
    printf '[%s] WARN: export failed for channel %s; skipping. Log:\n' "$SOURCE" "$CHANNEL_ID" >&2
    sed 's/^/    /' "$LOG" >&2
    return 0
  fi

  # Inject channelId into each message so downstream filtering/attribution works.
  if ! jq -c --arg cid "$CHANNEL_ID" --arg cname "$CHANNEL_NAME" \
        '.messages[]? | select(type == "object") | . + {channelId: $cid, channelName: $cname}' \
        "$OUT" > "$SCRATCH/$CHANNEL_ID.jsonl" 2>>"$LOG"; then
    printf '[%s] WARN: could not parse DCE output for channel %s; skipping.\n' "$SOURCE" "$CHANNEL_ID" >&2
    return 0
  fi
  local NEW_COUNT
  NEW_COUNT="$(wc -l < "$SCRATCH/$CHANNEL_ID.jsonl" | tr -d ' ')"
  printf '[%s] channel %s: fetched %s messages\n' "$SOURCE" "$CHANNEL_ID" "$NEW_COUNT" >&2
}

# Launch with a job pool limited to MAX_PARALLEL.
active_jobs() { jobs -pr | wc -l | tr -d ' '; }

for i in $(seq 0 $((CHANNEL_COUNT - 1))); do
  CHANNEL_ID="$(yq -r ".sources.\"$SOURCE\".channels[$i].id" "$SERVERS_YAML")"
  CHANNEL_NAME="$(yq -r ".sources.\"$SOURCE\".channels[$i].name // \"\"" "$SERVERS_YAML")"

  if [[ "$REFRESH" -eq 1 ]]; then
    AFTER="$(date -u -v-"${WINDOW_DAYS}"d +%Y-%m-%dT%H:%M:%S)"
  else
    AFTER="$(jq -r --arg cid "$CHANNEL_ID" '.[$cid] // empty' "$CURSOR_JSON")"
    if [[ -z "$AFTER" ]]; then
      AFTER="$(date -u -v-"${WINDOW_DAYS}"d +%Y-%m-%dT%H:%M:%S)"
    fi
  fi

  while [[ "$(active_jobs)" -ge "$MAX_PARALLEL" ]]; do
    wait -n 2>/dev/null || true
  done

  fetch_channel "$CHANNEL_ID" "$CHANNEL_NAME" "$AFTER" &
done
wait

# -------- merge + cursor update (serial, after all fetches done) --------

CHANNELS_UPDATED=0
for i in $(seq 0 $((CHANNEL_COUNT - 1))); do
  CHANNEL_ID="$(yq -r ".sources.\"$SOURCE\".channels[$i].id" "$SERVERS_YAML")"
  CHANNEL_JSONL="$SCRATCH/$CHANNEL_ID.jsonl"
  [[ -s "$CHANNEL_JSONL" ]] || continue

  NEW_COUNT="$(wc -l < "$CHANNEL_JSONL" | tr -d ' ')"

  # Merge + dedupe by id.
  cat "$MESSAGES_JSONL" "$CHANNEL_JSONL" \
    | jq -cs 'unique_by(.id) | .[]' \
    > "$SCRATCH/merged.jsonl"
  mv "$SCRATCH/merged.jsonl" "$MESSAGES_JSONL"

  # Cursor: max timestamp from this channel's new batch. Slurp array, filter to
  # objects with timestamp, take max.
  MAX_TS="$(jq -rs '[.[] | select(type == "object") | .timestamp? // empty] | max // empty' "$CHANNEL_JSONL" 2>/dev/null || echo "")"
  if [[ -n "$MAX_TS" && "$MAX_TS" != "null" ]]; then
    # Normalize "2026-04-15T23:12:04.123-05:00" -> "2026-04-15T23:12:04".
    CURSOR_TS="$(printf '%s' "$MAX_TS" | sed -E 's/\.[0-9]+//; s/([+-][0-9]{2}:[0-9]{2}|Z)$//')"
    jq --arg cid "$CHANNEL_ID" --arg ts "$CURSOR_TS" '.[$cid] = $ts' "$CURSOR_JSON" \
      > "$SCRATCH/cursor.json" && mv "$SCRATCH/cursor.json" "$CURSOR_JSON"
  fi

  CHANNELS_UPDATED=$((CHANNELS_UPDATED + 1))
  printf '[%s] merged channel %s: +%s messages\n' "$SOURCE" "$CHANNEL_ID" "$NEW_COUNT" >&2
done

# -------- final output --------

printf 'archive=%s\n' "$MESSAGES_JSONL"
printf 'channels_updated=%s\n' "$CHANNELS_UPDATED"
