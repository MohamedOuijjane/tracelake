// Inventory service: stock lookup and reservation, instrumented with OpenTelemetry.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

type store struct {
	mu    sync.Mutex
	stock map[string]int
}

type reserveRequest struct {
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
}

func newStore() *store {
	return &store{stock: map[string]int{
		"SKU-001": 1000,
		"SKU-002": 1000,
		"SKU-003": 200,
		"SKU-004": 500,
	}}
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func (s *store) get(w http.ResponseWriter, r *http.Request) {
	sku := r.PathValue("sku")
	s.mu.Lock()
	qty, ok := s.stock[sku]
	s.mu.Unlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "unknown sku"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"sku": sku, "available": qty})
}

func (s *store) reserve(w http.ResponseWriter, r *http.Request) {
	var req reserveRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Quantity <= 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid body"})
		return
	}
	// Simulate a slow storage call.
	time.Sleep(time.Duration(5+rand.Intn(40)) * time.Millisecond)

	s.mu.Lock()
	defer s.mu.Unlock()
	qty, ok := s.stock[req.SKU]
	if !ok || qty < req.Quantity {
		writeJSON(w, http.StatusConflict, map[string]string{"error": "not enough stock"})
		return
	}
	s.stock[req.SKU] = qty - req.Quantity
	writeJSON(w, http.StatusOK, map[string]any{"sku": req.SKU, "reserved": req.Quantity})
}

// initTracer reads OTEL_SERVICE_NAME and OTEL_EXPORTER_OTLP_ENDPOINT from the environment.
func initTracer(ctx context.Context) (func(context.Context) error, error) {
	exporter, err := otlptracehttp.New(ctx)
	if err != nil {
		return nil, err
	}
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter))
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{}, propagation.Baggage{}))
	return tp.Shutdown, nil
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	shutdown, err := initTracer(ctx)
	if err != nil {
		log.Fatalf("otel init: %v", err)
	}

	s := newStore()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "UP"})
	})
	mux.Handle("GET /inventory/{sku}", otelhttp.WithRouteTag("/inventory/{sku}", http.HandlerFunc(s.get)))
	mux.Handle("POST /inventory/reserve", otelhttp.WithRouteTag("/inventory/reserve", http.HandlerFunc(s.reserve)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           otelhttp.NewHandler(mux, "inventory"),
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		log.Printf("inventory listening on :%s", port)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("listen: %v", err)
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
	_ = shutdown(shutdownCtx)
}
