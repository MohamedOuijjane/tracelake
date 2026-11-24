package main

import (
	"context"
	"math/rand"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

func TestErrorRateBounds(t *testing.T) {
	f := newFaultInjector()
	if f.rate() != 0 {
		t.Fatalf("default rate = %v, want 0", f.rate())
	}
	for _, bad := range []float64{-0.1, 1.5} {
		if f.setRate(bad) {
			t.Errorf("setRate(%v) accepted", bad)
		}
	}
	if !f.setRate(0.3) || f.rate() != 0.3 {
		t.Errorf("setRate(0.3) not applied, rate = %v", f.rate())
	}
}

func TestShouldFailFollowsRate(t *testing.T) {
	f := newFaultInjector()
	f.rnd = rand.New(rand.NewSource(42)).Float64
	const n = 20000
	for _, want := range []float64{0, 0.3, 1} {
		f.setRate(want)
		fails := 0
		for i := 0; i < n; i++ {
			if f.shouldFail() {
				fails++
			}
		}
		got := float64(fails) / n
		if got < want-0.02 || got > want+0.02 {
			t.Errorf("rate %v: failed %.3f of requests", want, got)
		}
	}
}

func TestAdminEndpoint(t *testing.T) {
	f := newFaultInjector()
	do := func(method, body string) int {
		rec := httptest.NewRecorder()
		f.admin(rec, httptest.NewRequest(method, "/admin/fault", strings.NewReader(body)))
		return rec.Code
	}
	if code := do(http.MethodPost, `{"error_rate":0.3}`); code != 200 || f.rate() != 0.3 {
		t.Fatalf("POST: code %d rate %v", code, f.rate())
	}
	if code := do(http.MethodPost, `{"error_rate":2}`); code != 400 || f.rate() != 0.3 {
		t.Fatalf("POST invalid: code %d rate %v", code, f.rate())
	}
	if code := do(http.MethodPost, `{}`); code != 400 {
		t.Fatalf("POST without error_rate: code %d", code)
	}
	if code := do(http.MethodDelete, ""); code != 200 || f.rate() != 0 {
		t.Fatalf("DELETE: code %d rate %v", code, f.rate())
	}
}

// A failed request answers 503 and its SERVER span ends with status ERROR, the fault
// description, and the caller's trace as parent.
func TestInjectedFailureSpan(t *testing.T) {
	rec := tracetest.NewSpanRecorder()
	tp := sdktrace.NewTracerProvider(sdktrace.WithSpanProcessor(rec))
	otel.SetTracerProvider(tp)
	defer func() { _ = tp.Shutdown(context.Background()) }()

	f := newFaultInjector()
	f.setRate(1)
	h := f.traced("GET /restaurants/{id}/menu", menu)
	w := httptest.NewRecorder()
	otel.SetTextMapPropagator(propagation.TraceContext{})
	req := httptest.NewRequest(http.MethodGet, "/restaurants/1/menu", nil)
	req.Header.Set("traceparent", "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01")
	h.ServeHTTP(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("code = %d, want 503", w.Code)
	}
	spans := rec.Ended()
	if len(spans) != 1 {
		t.Fatalf("got %d spans, want 1", len(spans))
	}
	s := spans[0]
	if s.SpanKind() != trace.SpanKindServer || s.Name() != "GET /restaurants/{id}/menu" {
		t.Errorf("span = %v %q, want SERVER span named after the route", s.SpanKind(), s.Name())
	}
	if s.Parent().SpanID().String() != "b7ad6b7169203331" ||
		s.SpanContext().TraceID().String() != "0af7651916cd43dd8448eb211c80319c" {
		t.Errorf("span does not continue the caller trace: parent %v", s.Parent())
	}
	st := s.Status()
	if st.Code != codes.Error || st.Description != faultDescription {
		t.Errorf("span status = %v %q, want Error %q", st.Code, st.Description, faultDescription)
	}
}

// Requests that are not failed keep the normal otelhttp span and response.
func TestNoFaultKeepsNormalSpan(t *testing.T) {
	rec := tracetest.NewSpanRecorder()
	tp := sdktrace.NewTracerProvider(sdktrace.WithSpanProcessor(rec))
	otel.SetTracerProvider(tp)
	defer func() { _ = tp.Shutdown(context.Background()) }()

	h := newFaultInjector().traced("GET /restaurants/{id}/menu", menu)
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/restaurants/1/menu", nil)
	req.SetPathValue("id", "1")
	h.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("code = %d, want 200", w.Code)
	}
	if spans := rec.Ended(); len(spans) != 1 || spans[0].Status().Code == codes.Error {
		t.Fatalf("want one non error span, got %d", len(spans))
	}
}
