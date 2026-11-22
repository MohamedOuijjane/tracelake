# chaos

Fault injection with [Toxiproxy](https://github.com/Shopify/toxiproxy). Each fault has a known cause, start and end, so it doubles as a test for the detection pipeline: we inject a fault on one service and check that the detector names that service.

## How it works

The `toxiproxy` service (full and demo profiles) creates its proxies at startup from [toxiproxy.json](toxiproxy.json):

| Proxy | Listens on | Forwards to | Used by |
|---|---|---|---|
| `payments` | `toxiproxy:8666` | `payments:8000` | `orders` (`PAYMENTS_URL=http://toxiproxy:8666`) |

With no toxic, the proxy passes traffic through unchanged. Only the `orders -> payments` call goes through it; the gateway `/api/payments` route still calls payments directly.

The Toxiproxy API is published on `127.0.0.1:8474`. [chaos.sh](chaos.sh) drives it with bash and curl only, nothing to install on the host.

## Faults

| Id | Target | Effect |
|---|---|---|
| F1 | payments | 2000 ms latency on every response from payments to orders (`latency` toxic, downstream) |

## Commands

| Command | What it does |
|---|---|
| `make chaos` | Starts F1 and appends an open incident to `incidents.csv`. Refuses if an incident is already open. |
| `make heal` | Removes all toxics on all proxies and writes `end_ts` of the open incident. |
| `make chaos-status` | Shows the active toxics per proxy and the open incident. |

Typical run:

```
make up-full
make demo          # k6 traffic
make chaos         # wait a few minutes
make heal
cat loadgen/chaos/incidents.csv
```

## Ground truth: incidents.csv

Every injected fault is recorded in `loadgen/chaos/incidents.csv`. It is produced at runtime and not committed; [incidents.example.csv](incidents.example.csv) shows the format.

| Column | Example | Meaning |
|---|---|---|
| `incident_id` | `F1-20261122T120000Z` | Fault id and start time |
| `fault` | `F1` | Fault id |
| `target_service` | `payments` | Service the fault is applied to, the expected root cause |
| `start_ts` | `2026-11-22T12:00:00Z` | When `make chaos` added the toxic, UTC ISO 8601 |
| `end_ts` | `2026-11-22T12:02:00Z` | When `make heal` removed it, empty while the incident is open |

This file is the ground truth for detection quality: precision, recall and detection delay are computed against it.

## Note for the processing layer

Under F1 the extra latency is visible on the caller's CLIENT span (orders -> payments), not on the payments SERVER span. Call latency and root cause must be computed from the caller side, with the callee identified through the child SERVER span (`parent_span_id`).

Measured on real `otel.traces` spans, k6 traffic, one 2 minute F1 run:

| Phase | orders CLIENT -> payments, median / p95 | payments SERVER `POST /payments`, median / p95 | Paired calls: CLIENT minus SERVER, median |
|---|---|---|---|
| before (1 min) | 104 ms / 163 ms (18 calls) | 95 ms / 152 ms (19 spans) | 6 ms (1 pair) |
| during F1 (2 min) | 2102 ms / 2155 ms (43 calls) | 103 ms / 146 ms (47 spans) | 2008 ms (15 pairs) |
| after heal | 93 ms / 152 ms (88 calls) | 77 ms / 150 ms (29 spans) | no pair in this run (recorded before #55) |

Incident `F1-20261122T165841Z`, 16:58:41Z to 17:00:41Z.

The payments SERVER span keeps its normal duration because the delay is added in the network, between the two services. A detector that only looks at SERVER spans of payments would miss F1; it would see orders and gateway slow down instead. Pair each CLIENT span with its child SERVER span to name payments as the slow dependency.

## Next faults

- F2: error rate on restaurants.
- F5: lunch peak without fault, as a control (no alert expected).
- F3, F4: network partition and resource saturation, if time remains.
