# chaos

Placeholder for fault injection with [Toxiproxy](https://github.com/Shopify/toxiproxy). Planned for the Hardening milestone.

## Plan

1. Add a `toxiproxy` service to the `demo` profile.
2. Point `orders -> restaurants` and `orders -> delivery` through proxies by changing `RESTAURANTS_URL` and `DELIVERY_URL`.
3. Add scripts that toggle toxics:
   - `latency` on restaurants (for example +300 ms, jitter 100 ms), a busy kitchen at lunch
   - `timeout` on delivery, no courier answers
   - `bandwidth` limits on payments
4. Check that the anomaly job flags the right service within a few minutes and that the Grafana RED dashboard shows it.

## Expected outcome

Each experiment has a known cause, so it doubles as a test for the detection pipeline: we inject latency in one service and assert that `alerts` names that service.
