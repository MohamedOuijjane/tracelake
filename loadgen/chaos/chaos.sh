#!/usr/bin/env bash
# Fault injection through toxiproxy, with a ground truth record in incidents.csv.
#
#   chaos.sh start [F1]   inject a fault and open an incident
#   chaos.sh start F5     control: run a traffic peak with no fault, record it, close it when done
#   chaos.sh heal         remove all toxics and close the open incident
#   chaos.sh status       show active toxics and the open incident
#
# Needs only bash, curl and docker compose. Talks to the toxiproxy API published on
# 127.0.0.1:8474. F5 runs the k6 service of docker-compose.yml.
set -euo pipefail

API="${TOXIPROXY_API:-http://127.0.0.1:8474}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV="${INCIDENTS_CSV:-$DIR/incidents.csv}"
HEADER="incident_id,fault,target_service,start_ts,end_ts"
ROOT="$(cd "$DIR/../.." && pwd)"

# F5 control peak: k6 virtual users at the peak and run length. The default peak is the
# highest level calibrated as healthy on a reference machine (see README.md).
F5_PEAK_VUS="${F5_PEAK_VUS:-60}"
F5_DURATION="${F5_DURATION:-3m}"

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
    F5)
      TARGET=none
      DESCRIPTION="control peak, no fault: k6 at PEAK_VUS=$F5_PEAK_VUS for $F5_DURATION"
      ;;
    *) die "unknown fault: $1 (supported: F1, F5)" ;;
  esac
}

start() {
  local fault="${1:-F1}"
  fault_spec "$fault"
  local open
  open="$(open_incident)"
  [ -z "$open" ] || die "an incident is already open, run make heal first: $open"

  if [ "$fault" = F5 ]; then
    control
    return
  fi

  api POST "/proxies/$PROXY/toxics" "$TOXIC" > /dev/null
  open_new "$fault"
  echo "chaos: $INCIDENT_ID started ($DESCRIPTION)"
}

# Appends an open incident line and sets INCIDENT_ID.
open_new() {
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  INCIDENT_ID="$1-${now//[-:]/}"
  ensure_csv
  echo "$INCIDENT_ID,$1,$TARGET,$now," >> "$CSV"
}

# Writes end_ts of an open incident. awk + mv works with GNU and BSD tools alike.
close_incident() {
  local id="$1" now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  awk -F, -v OFS=, -v id="$id" -v now="$now" '$1 == id && $5 == "" {$5 = now} {print}' \
    "$CSV" > "$CSV.tmp" && mv "$CSV.tmp" "$CSV"
  CLOSED_AT="$now"
}

# F5: no toxic. The incident covers exactly the k6 run, and is closed even if k6 fails or the
# run is interrupted.
control() {
  open_new F5
  echo "chaos: $INCIDENT_ID started ($DESCRIPTION)"
  trap 'close_incident "$INCIDENT_ID"; echo "chaos: $INCIDENT_ID closed at $CLOSED_AT (interrupted)"; exit 130' INT TERM
  local rc=0
  (cd "$ROOT" && docker compose --profile demo run --rm --no-deps \
    -e PEAK_VUS="$F5_PEAK_VUS" -e LOAD_DURATION="$F5_DURATION" k6) || rc=$?
  trap - INT TERM
  close_incident "$INCIDENT_ID"
  echo "chaos: $INCIDENT_ID finished at $CLOSED_AT (k6 exit code $rc)"
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
  local id="${open%%,*}"
  close_incident "$id"
  echo "chaos: $id healed at $CLOSED_AT"
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
  *) die "usage: chaos.sh start [F1|F5] | heal | status" ;;
esac
