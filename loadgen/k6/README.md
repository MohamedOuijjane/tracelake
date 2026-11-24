# k6

Load generator for the food delivery platform, [scenarios.js](scenarios.js). Three scenarios run together through the gateway:

| Scenario | What a virtual user does | Share of the peak users |
|---|---|---|
| `browse_menu` | `GET /api/menu/{id}`, then waits 1 to 3 s | 100% |
| `place_order` | reads a menu, then `POST /api/orders`, waits 1 to 3 s | 60% |
| `pay` | `POST /api/payments` (a direct charge such as a tip), waits 2 to 5 s | 20% |

`402` (card declined) and `409` (dish unavailable) are business answers and do not count as failed requests.

## Profiles

`LOAD_PROFILE` picks the shape of the load, the same for the three scenarios.

### lunch (default)

One lunch peak over `LOAD_DURATION`: quiet morning (20% of the peak), ramp up, lunch peak, ramp down, quiet afternoon. `make demo` and `make control` (fault F5) use it.

### day

A full food delivery day on real clock hours, 24 hourly levels as a share of the dinner peak:

| Hours | Level | Period |
|---|---|---|
| 00:00 to 06:00 | 5% to 10% | night |
| 06:00 to 12:00 | 10% to 40% | morning, building up |
| 12:00 to 14:00 | 70% | lunch peak |
| 14:00 to 19:00 | 20% to 50% | quiet afternoon, then early evening |
| 19:00 to 22:00 | 100% | dinner peak, the highest of the day |
| 22:00 to 24:00 | 50%, then 20% | late evening |

Each simulated hour ramps to its level in one sixth of the hour, then holds it, so the load can be read hour by hour. A level never goes below 1 virtual user.

`LOAD_DURATION` is the length of the replayed day. The default `24m` is the accelerated day: 1 minute per hour, so a full day replays in 24 minutes. `24h` replays it at real speed; then set `DAY_START_HOUR` to the current hour to follow the wall clock.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | Gateway URL (`http://gateway:8080` inside compose) |
| `LOAD_PROFILE` | `lunch` | `lunch` or `day` |
| `PEAK_VUS` | `5` | Browsing users at the highest peak: lunch for `lunch`, dinner for `day` |
| `LOAD_DURATION` | `2m` (`lunch`), `24m` (`day`) | Run length, or length of the replayed day |
| `DAY_START_HOUR` | `0` | `day` only: clock hour the run starts at (0 to 23) |

Do not use `K6_VUS` or `K6_DURATION` in the k6 container environment: k6 reads them as its own options and they replace the scenarios. In `.env`, `K6_VUS` and `K6_DURATION` are mapped to `PEAK_VUS` and `LOAD_DURATION` by `docker-compose.yml`.

## Commands

| Command | Profile |
|---|---|
| `make demo` | `lunch`, `PEAK_VUS=K6_VUS` (5), `LOAD_DURATION=K6_DURATION` (2m), in the background |
| `make control` | `lunch` at 60 peak users for 3 minutes, recorded as F5 (see [chaos](../chaos/README.md)) |
| `make day` | `day`, accelerated: `DAY_PEAK_VUS` (20) dinner users over `DAY_DURATION` (24m), in the foreground |

`make day` needs the full profile up (`make up-full`). Change the run with `make day DAY_PEAK_VUS=40 DAY_DURATION=48m`.

## Measured accelerated day

`make day` with the defaults (20 dinner users, 24 minutes), on the full profile with no fault. Gateway SERVER spans from `otel.traces`, health checks left out, one line per simulated hour (1 minute of the run):

| Simulated hour | Browsing users | Gateway requests | Chart |
|---|---|---|---|
| 00:00 to 01:00 | 2 | 102 | `####` |
| 01:00 to 02:00 | 1 | 92 | `###` |
| 02:00 to 03:00 | 1 | 79 | `###` |
| 03:00 to 04:00 | 1 | 79 | `###` |
| 04:00 to 05:00 | 1 | 86 | `###` |
| 05:00 to 06:00 | 1 | 80 | `###` |
| 06:00 to 07:00 | 2 | 108 | `####` |
| 07:00 to 08:00 | 3 | 166 | `######` |
| 08:00 to 09:00 | 4 | 199 | `#######` |
| 09:00 to 10:00 | 4 | 207 | `#######` |
| 10:00 to 11:00 | 5 | 257 | `#########` |
| 11:00 to 12:00 | 8 | 423 | `###############` |
| 12:00 to 13:00 | 14 | 722 | `##########################` |
| 13:00 to 14:00 | 14 | 744 | `###########################` |
| 14:00 to 15:00 | 8 | 496 | `##################` |
| 15:00 to 16:00 | 5 | 305 | `###########` |
| 16:00 to 17:00 | 4 | 218 | `########` |
| 17:00 to 18:00 | 5 | 273 | `##########` |
| 18:00 to 19:00 | 10 | 523 | `###################` |
| 19:00 to 20:00 | 20 | 1043 | `#####################################` |
| 20:00 to 21:00 | 20 | 1115 | `########################################` |
| 21:00 to 22:00 | 20 | 1114 | `########################################` |
| 22:00 to 23:00 | 10 | 611 | `######################` |
| 23:00 to 24:00 | 4 | 256 | `#########` |

9298 requests in total (k6 counted 9305, the last ones fall in the grace period after minute 24), 0 errors, gateway p95 256 ms. The lunch peak reaches 722 to 744 requests per hour and the dinner peak 1043 to 1115, about 1.5 times lunch. The night stays at 80 to 100 requests per hour because each of the three scenarios keeps at least one user.
