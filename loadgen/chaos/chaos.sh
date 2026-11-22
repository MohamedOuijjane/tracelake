#!/usr/bin/env bash
# Fault injection through toxiproxy, with a ground truth record in incidents.csv.
#
#   chaos.sh start [F1]   inject a fault and open an incident
#   chaos.sh heal         remove all toxics and close the open incident
#   chaos.sh status       show active toxics and the open incident
#
# Needs only bash and curl. Talks to the toxiproxy API published on 127.0.0.1:8474.
set -euo pipefail

API="${TOXIPROXY_API:-http://127.0.0.1:8474}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV="${INCIDENTS_CSV:-$DIR/incidents.csv}"
HEADER="incident_id,fault,target_service,start_ts,end_ts"

die() { echo "chaos: $*" >&2; exit 1; }

api() {
  local method="$1" path="$2" body="${3:-}"
  local args=(-fsS -X "$method" "$API$path")
  [ -n "$body" ] && args+=(-H 'Content-Type: application/json' -d "$body")
  curl "${args[@]}" || die "toxiproxy API call failed: $method $path (is the full profile up?)"
}

# Prints the open incident line (end_ts empty), if any.
open_incident() {
  [ -f "$CSV" ] || return 0
  awk -F, 'NR > 1 && $5 == "" {line = $0} END {if (line != "") print line}' "$CSV"
}

ensure_csv() {
  [ -s "$CSV" ] || echo "$HEADER" > "$CSV"
}

# Sets PROXY, TARGET, TOXIC (toxiproxy JSON) and DESCRIPTION for a fault id.
fault_spec() {
  case "$1" in
    F1)
      PROXY=payments
      TARGET=payments
      TOXIC='{"name":"f1_latency","type":"latency","stream":"downstream","toxicity":1.0,"attributes":{"latency":2000,"jitter":0}}'
      DESCRIPTION="2000 ms latency on orders -> payments"
      ;;
    *) die "unknown fault: $1 (supported: F1)" ;;
  esac
}

start() {
  local fault="${1:-F1}"
  fault_spec "$fault"
  local open
  open="$(open_incident)"
  [ -z "$open" ] || die "an incident is already open, run make heal first: $open"

  api POST "/proxies/$PROXY/toxics" "$TOXIC" > /dev/null

  local now id
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  id="$fault-${now//[-:]/}"
  ensure_csv
  echo "$id,$fault,$TARGET,$now," >> "$CSV"
  echo "chaos: $id started ($DESCRIPTION)"
}

heal() {
  # POST /reset removes every toxic on every proxy and re-enables them.
  api POST /reset > /dev/null
  local open
  open="$(open_incident)"
  if [ -z "$open" ]; then
    echo "chaos: toxics removed, no open incident"
    return
  fi
  local now id
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  id="${open%%,*}"
  # Close the open line (empty end_ts). awk + mv works with GNU and BSD tools alike.
  awk -F, -v OFS=, -v id="$id" -v now="$now" '$1 == id && $5 == "" {$5 = now} {print}' \
    "$CSV" > "$CSV.tmp" && mv "$CSV.tmp" "$CSV"
  echo "chaos: $id healed at $now"
}

status() {
  echo "toxics per proxy:"
  local proxies
  proxies="$(api GET /proxies | grep -o '"name":"[^"]*","listen"' | cut -d'"' -f4)"
  for p in $proxies; do
    echo "  $p: $(api GET "/proxies/$p/toxics")"
  done
  local open
  open="$(open_incident)"
  echo "open incident: ${open:-none}"
}

case "${1:-}" in
  start) shift; start "$@" ;;
  heal) heal ;;
  status) status ;;
  *) die "usage: chaos.sh start [F1] | heal | status" ;;
esac
