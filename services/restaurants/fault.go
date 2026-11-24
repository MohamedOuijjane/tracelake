// Fault injection for chaos fault F2: a share of the business requests fails with 503.
// The admin endpoints exist only when CHAOS_ENABLED=true and are not routed by the gateway.
package main

import (
	"encoding/json"
	"math"
	"math/rand"
	"net/http"
	"sync/atomic"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
)

const faultDescription = "injected fault F2"

// faultAttr marks spans of requests failed on purpose, so they can be told apart from real errors.
var faultAttr = attribute.String("chaos.fault", "F2")

// faultInjector holds the current error rate (0 to 1). Safe for concurrent use.
type faultInjector struct {
	bits atomic.Uint64 // math.Float64bits of the error rate
	rnd  func() float64
}

func newFaultInjector() *faultInjector {
	return &faultInjector{rnd: rand.Float64}
}

func (f *faultInjector) rate() float64 { return math.Float64frombits(f.bits.Load()) }

// setRate rejects values outside [0, 1] and NaN.
func (f *faultInjector) setRate(r float64) bool {
	if math.IsNaN(r) || r < 0 || r > 1 {
		return false
	}
	f.bits.Store(math.Float64bits(r))
	return true
}

// shouldFail draws once per request: true with probability rate.
func (f *faultInjector) shouldFail() bool {
	r := f.rate()
	return r > 0 && f.rnd() < r
}

// traced returns the handler of a business route. Normal requests go through otelhttp, which
// emits their SERVER span. A request failed on purpose answers 503 and gets its SERVER span here,
// with the same name and route, continuing the caller's trace. This layer sits in front of
// otelhttp on purpose: otelhttp sets the span status from the response code after the handler
// returns, which would replace the fault description with an empty one.
func (f *faultInjector) traced(route string, h http.HandlerFunc) http.Handler {
	normal := traced(route, h)
	tracer := otel.Tracer("github.com/tracelake/tracelake/services/restaurants/chaos")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !f.shouldFail() {
			normal.ServeHTTP(w, r)
			return
		}
		ctx := otel.GetTextMapPropagator().Extract(r.Context(), propagation.HeaderCarrier(r.Header))
		_, span := tracer.Start(ctx, route,
			trace.WithSpanKind(trace.SpanKindServer),
			trace.WithAttributes(
				attribute.String("http.request.method", r.Method),
				attribute.String("http.route", route),
				attribute.String("url.path", r.URL.Path),
				attribute.Int("http.response.status_code", http.StatusServiceUnavailable),
				attribute.String("error.type", "503"),
				faultAttr,
			))
		defer span.End()
		span.SetStatus(codes.Error, faultDescription)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": faultDescription})
	})
}

type faultRequest struct {
	ErrorRate *float64 `json:"error_rate"`
}

// admin serves POST /admin/fault {"error_rate":0.3}, DELETE /admin/fault and GET /admin/fault.
func (f *faultInjector) admin(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var req faultRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.ErrorRate == nil ||
			!f.setRate(*req.ErrorRate) {
			writeJSON(w, http.StatusBadRequest,
				map[string]string{"error": `body must be {"error_rate": <0 to 1>}`})
			return
		}
	case http.MethodDelete:
		f.setRate(0)
	case http.MethodGet:
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]float64{"error_rate": f.rate()})
}
