import json
from datetime import datetime

from jobs.gold_red_metrics import red_metrics
from jobs.silver_spans import flatten_spans


def _payload(trace_id, span_id, start_ns, end_ns, status=1, parent=""):
    return json.dumps(
        {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [{"key": "service.name", "value": {"stringValue": "orders"}}]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": trace_id,
                                    "spanId": span_id,
                                    "parentSpanId": parent,
                                    "name": "POST /orders",
                                    "kind": 2,
                                    "startTimeUnixNano": str(start_ns),
                                    "endTimeUnixNano": str(end_ns),
                                    "attributes": [
                                        {
                                            "key": "http.response.status_code",
                                            "value": {"intValue": "201"},
                                        }
                                    ],
                                    "status": {"code": status},
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    )


def test_flatten_spans_matches_contract(spark):
    start = 1_762_646_400_000_000_000  # 2025-11-09T00:00:00Z
    bronze = spark.createDataFrame(
        [(_payload("a" * 32, "b" * 16, start, start + 25_000_000),)], ["payload"]
    )
    row = flatten_spans(bronze).collect()[0]
    assert row.trace_id == "a" * 32
    assert row.parent_span_id is None
    assert row.service == "orders"
    assert row.duration_ms == 25.0
    assert row.status_code == "OK"
    assert row.attributes["http.response.status_code"] == "201"
    assert row.date == "2025-11-09"


def test_red_metrics_per_minute(spark):
    t = datetime(2026, 11, 9, 10, 0, 5)
    rows = [("orders", 2, t, float(d), "ERROR" if d == 100 else "OK") for d in range(1, 101)]
    spans = spark.createDataFrame(
        rows, ["service", "kind", "start_ts", "duration_ms", "status_code"]
    )
    out = red_metrics(spans).collect()
    assert len(out) == 1
    r = out[0]
    assert r.request_count == 100
    assert r.error_count == 1
    assert abs(r.error_rate - 0.01) < 1e-9
    assert r.p50_ms == 50.0
    assert r.p99_ms == 99.0
