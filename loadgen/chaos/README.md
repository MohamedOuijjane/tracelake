# chaos

Fault injection with [Toxiproxy](https://github.com/Shopify/toxiproxy). Each fault has a known cause, start and end, so it doubles as a test for the detection pipeline: we inject a fault on one service and check that the detector names that service. The F5 control does the opposite: it raises traffic with no fault, and the detector must stay quiet.

## How it works

The `toxiproxy` service (full and demo profiles) creates its proxies at startup from [toxiproxy.json](toxiproxy.json):

| Proxy | Listens on | Forwards to | Used by |
|---|---|---|---|
| `payments` | `toxiproxy:8666` | `payments:8000` | `orders` (`PAYMENTS_URL=http://toxiproxy:8666`) |

With no toxic, the proxy passes traffic through unchanged. Only the `orders -> payments` call goes through it; the gateway `/api/payments` route still calls payments directly.

The Toxiproxy API is published on `127.0.0.1:8474`. [chaos.sh](chaos.sh) drives it with bash and curl only, nothing to install on the host. F2 switches errors on inside restaurants through its internal `/admin/fault` endpoint, called with `docker compose exec` (not published, not routed by the gateway, enabled by `CHAOS_ENABLED=true`). F5 uses `docker compose` to run the k6 service.

## Faults

| Id | Target | Effect |
|---|---|---|
| F1 | payments | 2000 ms latency on every response from payments to orders (`latency` toxic, downstream) |
| F2 | restaurants | 30% of the menu and check requests handled by restaurants fail with 503, SERVER span status ERROR "injected fault F2" |
| F5 | none | Control: a lunch shaped k6 peak at 60 peak virtual users (12x normal) for 3 minutes, no fault |

## Commands

| Command | What it does |
|---|---|
| `make chaos` | Starts F1 and appends an open incident to `incidents.csv`. Refuses if an incident is already open. |
| `make chaos FAULT=F2` | Starts F2 (error rate 0.3 on restaurants, `F2_ERROR_RATE` to change it) and appends an open incident. Same refusal rule. |
| `make heal` | Clears every fault (all toxics, restaurants error rate back to 0) and writes `end_ts` of the open incident. |
| `make chaos-status` | Shows the active toxics per proxy, the restaurants error rate and the open incident. |
| `make control` | Runs F5: opens an incident, runs k6 at the control peak, closes the incident when k6 finishes (also on failure or Ctrl+C). Refuses if an incident is already open. |

Typical run:

```
make up-full
make demo          # k6 traffic
make chaos         # wait a few minutes
make heal
make control       # F5, blocks until the peak is over (about 3 minutes)
cat loadgen/chaos/incidents.csv
```

F5 settings, overridable from the environment: `F5_PEAK_VUS` (default `60`) and `F5_DURATION` (default `3m`), for example `F5_PEAK_VUS=30 F5_DURATION=5m make control`.

## Ground truth: incidents.csv

Every injected fault is recorded in `loadgen/chaos/incidents.csv`. It is produced at runtime and not committed; [incidents.example.csv](incidents.example.csv) shows the format.

| Column | Example | Meaning |
|---|---|---|
| `incident_id` | `F1-20261122T120000Z` | Fault id and start time |
| `fault` | `F1` | Fault id |
| `target_service` | `payments` | Service the fault is applied to, the expected root cause (`payments` for F1, `restaurants` for F2). `none` for F5 |
| `start_ts` | `2026-11-22T12:00:00Z` | When `make chaos` switched the fault on, or when the F5 k6 run started, UTC ISO 8601 |
| `end_ts` | `2026-11-22T12:02:00Z` | When `make heal` cleared the fault, or when the F5 k6 run ended. Empty while the incident is open |

This file is the ground truth for detection quality: precision, recall and detection delay are computed against it.

## Note for the processing layer

Under F1 the extra latency is visible on the caller's CLIENT span (orders -> payments), not on the payments SERVER span. Call latency and root cause must be computed from the caller side, with the callee identified through the child SERVER span (`parent_span_id`).

Measured on real `otel.traces` spans, k6 traffic, one 2 minute F1 run. Each row pairs every orders CLIENT span to payments with its child payments SERVER span (100% of calls paired):

| Phase | Paired calls | orders CLIENT -> payments, median / p95 | payments SERVER `POST /payments`, median / p95 | CLIENT minus SERVER, median / p95 |
|---|---|---|---|---|
| before (1.5 min) | 17 | 88 ms / 164 ms | 81 ms / 155 ms | 6 ms / 12 ms |
| during F1 (2 min) | 41 | 2094 ms / 2159 ms | 89 ms / 151 ms | 2007 ms / 2014 ms |
| after heal (1.7 min) | 86 | 92 ms / 149 ms | 88 ms / 145 ms | 5 ms / 10 ms |

Incident `F1-20261122T173453Z`, 17:34:53Z to 17:36:53Z.

The payments SERVER span keeps its normal duration because the delay is added in the network, between the two services. A detector that only looks at SERVER spans of payments would miss F1; it would see orders and gateway slow down instead. Pair each CLIENT span with its child SERVER span to name payments as the slow dependency.

## F2: errors on restaurants

Under F2 the errors start on restaurants and spread to its callers. The root cause is the deepest service in the call graph whose own SERVER spans are in error: restaurants, not gateway or orders.

Unlike F1, the fault is visible on the service itself: each failed restaurants request has a SERVER span with status `ERROR`, description `injected fault F2` and attribute `chaos.fault=F2`.

### Measured run

Background traffic was the normal profile stretched to 60 minutes (flat 1 virtual user in its first stage). 1 minute before, `make chaos FAULT=F2` for 2 minutes, `make heal`, 2 minutes after. SERVER spans from `otel.traces`, health checks left out:

| Service | Phase | Requests | Error rate | p95 |
|---|---|---|---|---|
| gateway | before | 82 | 1.2% | 257 ms |
| gateway | during | 183 | 25.1% | 257 ms |
| gateway | after | 167 | 0.0% | 265 ms |
| orders | before | 18 | 0.0% | 301 ms |
| orders | during | 37 | 0.0% | 312 ms |
| orders | after | 37 | 0.0% | 290 ms |
| restaurants | before | 67 | 0.0% | 48 ms |
| restaurants | during | 148 | 36.5% | 42 ms |
| restaurants | after | 135 | 0.0% | 46 ms |
| payments | before | 33 | 6.1% | 145 ms |
| payments | during | 61 | 1.6% | 148 ms |
| payments | after | 70 | 4.3% | 144 ms |
| delivery | before | 17 | 0.0% | 62 ms |
| delivery | during | 27 | 0.0% | 61 ms |
| delivery | after | 34 | 0.0% | 64 ms |

Incident `F2-20261124T194500Z`, 19:45:00Z to 19:47:00Z. Restaurants fails 54 of 148 requests (36.5%, the draw is random per request around 30%) and only during F2. Latency does not change. Payments errors are its configured 5% card declines.

All 54 restaurants ERROR spans pair with a caller CLIENT span through `parent_span_id`: 45 from gateway (`/api/menu`, the 503 is passed through, hence 25% errors on gateway) and 9 from orders (the availability check).

orders shows its errors on the caller side only. Its 9 CLIENT spans to restaurants have status `ERROR` (503), but orders then answers `409 REJECTED`, the same answer as an unavailable dish, so its SERVER spans stay without error. A detector must read the CLIENT spans to see that orders is affected, and should not take orders 409s as a cause.

## F5: control peak

F5 raises traffic only. A detector that alerts on F5 is reacting to volume alone; volume must not be an anomaly by itself when latency and errors are normal. Each F5 alert counts as a false positive.

### Calibration

The peak must stay healthy, otherwise it is a real overload and not a valid control. Each level was run alone for 2 minutes with the lunch profile and measured by k6 at the gateway. Normal traffic (`make demo`) is `PEAK_VUS=5`.

| Peak VUs | Requests | Requests/s | Failed | Gateway p95 |
|---|---|---|---|---|
| 5 (baseline) | 354 | 2.9 | 0.28% | 294 ms |
| 10 | 658 | 5.4 | 0.45% | 275 ms |
| 15 | 991 | 8.1 | 0.20% | 272 ms |
| 20 | 1310 | 10.7 | 0.30% | 253 ms |
| 30 | 1990 | 16.3 | 0.55% | 242 ms |
| 45 | 2954 | 23.9 | 0.27% | 234 ms |
| 60 | 3899 | 31.2 | 0.25% | 258 ms |

The failed requests are the simulated card declines of payments (502 on part of the direct `/api/payments` calls), present at every level. Gateway p95 stays below the baseline, far from the 2x limit, and service CPU stays near idle, so 60 is the default: the highest level tried, on a laptop with 8 GB for Docker. On a smaller machine, lower it with `F5_PEAK_VUS`.

### Measured run

Background traffic was the normal profile stretched to 60 minutes, so its first stage gives a flat 1 virtual user during the whole window. Then 2 minutes before, `make control`, 2 minutes after. SERVER spans from `otel.traces`, health checks left out:

| Service | Phase | Requests/min | Error rate | p95 |
|---|---|---|---|---|
| gateway | before | 82 | 1.8% | 299 ms |
| gateway | during | 1981 | 0.3% | 259 ms |
| gateway | after | 83 | 1.2% | 264 ms |
| orders | before | 18.5 | 0.0% | 311 ms |
| orders | during | 402 | 0.0% | 286 ms |
| orders | after | 18.5 | 0.0% | 284 ms |
| restaurants | before | 65 | 0.0% | 45 ms |
| restaurants | during | 1853 | 0.0% | 42 ms |
| restaurants | after | 66 | 0.0% | 44 ms |
| payments | before | 35.5 | 5.6% | 151 ms |
| payments | during | 515 | 5.5% | 148 ms |
| payments | after | 35.5 | 4.2% | 151 ms |
| delivery | before | 17.5 | 0.0% | 64 ms |
| delivery | during | 365 | 0.0% | 63 ms |
| delivery | after | 18 | 0.0% | 62 ms |

Incident `F5-20261122T181748Z`, 18:17:48Z to 18:20:53Z. Volume rises 20x to 28x on every service while error rates and p95 stay at their baseline levels. The payments error rate is its configured 5% decline rate (`PAYMENT_FAILURE_RATE`); the gateway error rate is those declines seen on `/api/payments`, diluted by the extra menu traffic during F5.

## Next faults

- F3, F4: network partition and resource saturation, if time remains.
