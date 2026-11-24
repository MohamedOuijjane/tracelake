// Restaurants service: menus and dish availability checks, instrumented with OpenTelemetry.
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
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

type dish struct {
	ID          string  `json:"id"`
	Name        string  `json:"name"`
	Price       float64 `json:"price"`
	Available   bool    `json:"available"`
	PrepMinutes int     `json:"prep_minutes"`
}

type restaurant struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Cuisine string `json:"cuisine"`
	Menu    []dish `json:"menu"`
}

type checkItem struct {
	DishID   string `json:"dish_id"`
	Quantity int    `json:"quantity"`
}

type checkRequest struct {
	Items []checkItem `json:"items"`
}

// catalog is static and read only, so handlers can share it without locking.
var catalog = map[string]restaurant{
	"1": {ID: "1", Name: "Napoli Express", Cuisine: "pizza", Menu: []dish{
		{"pz-margherita", "Margherita", 9.50, true, 12},
		{"pz-diavola", "Diavola", 11.00, true, 12},
		{"pz-truffle", "Truffle Bianca", 15.50, false, 15},
		{"ds-tiramisu", "Tiramisu", 5.00, true, 2},
	}},
	"2": {ID: "2", Name: "Kaze Sushi", Cuisine: "japanese", Menu: []dish{
		{"su-salmon", "Salmon Maki x8", 8.90, true, 10},
		{"su-dragon", "Dragon Roll", 13.40, true, 14},
		{"su-ramen", "Tonkotsu Ramen", 12.00, true, 18},
		{"su-mochi", "Mochi x3", 4.50, false, 1},
	}},
	"3": {ID: "3", Name: "Burger Lab", Cuisine: "burgers", Menu: []dish{
		{"bg-classic", "Classic Burger", 10.90, true, 9},
		{"bg-double", "Double Smash", 13.90, true, 11},
		{"bg-veggie", "Veggie Burger", 11.50, true, 9},
		{"sd-fries", "Fries", 3.50, true, 5},
	}},
	"4": {ID: "4", Name: "Tajine House", Cuisine: "moroccan", Menu: []dish{
		{"tj-chicken", "Chicken Tajine", 14.00, true, 25},
		{"tj-kefta", "Kefta Tajine", 13.50, true, 22},
		{"cs-royal", "Couscous Royal", 16.00, false, 30},
		{"dr-tea", "Mint Tea", 2.50, true, 3},
	}},
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

// work simulates a lookup in the restaurant backend.
func work(minMs, maxMs int) {
	time.Sleep(time.Duration(minMs+rand.Intn(maxMs-minMs+1)) * time.Millisecond)
}

func menu(w http.ResponseWriter, r *http.Request) {
	work(5, 30)
	rest, ok := catalog[r.PathValue("id")]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "unknown restaurant"})
		return
	}
	writeJSON(w, http.StatusOK, rest)
}

// check verifies that every dish is on the menu and available, then estimates the
// preparation time: the slowest dish, plus one minute per extra portion, plus kitchen jitter.
func check(w http.ResponseWriter, r *http.Request) {
	rest, ok := catalog[r.PathValue("id")]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "unknown restaurant"})
		return
	}
	var req checkRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || len(req.Items) == 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid body"})
		return
	}
	work(10, 50)

	dishes := make(map[string]dish, len(rest.Menu))
	for _, d := range rest.Menu {
		dishes[d.ID] = d
	}

	var unavailable []string
	total, slowest, portions := 0.0, 0, 0
	for _, it := range req.Items {
		d, found := dishes[it.DishID]
		if !found || !d.Available || it.Quantity <= 0 {
			unavailable = append(unavailable, it.DishID)
			continue
		}
		total += d.Price * float64(it.Quantity)
		portions += it.Quantity
		slowest = max(slowest, d.PrepMinutes)
	}
	if len(unavailable) > 0 {
		writeJSON(w, http.StatusConflict, map[string]any{
			"restaurant_id": rest.ID,
			"available":     false,
			"unavailable":   unavailable,
		})
		return
	}

	prep := slowest + (portions - 1) + rand.Intn(5)
	writeJSON(w, http.StatusOK, map[string]any{
		"restaurant_id":       rest.ID,
		"available":           true,
		"total":               float64(int(total*100+0.5)) / 100,
		"preparation_minutes": prep,
	})
}

// initTracer reads OTEL_SERVICE_NAME and OTEL_EXPORTER_OTLP_ENDPOINT from the environment.
func initTracer(ctx context.Context) (func(context.Context) error, error) {
	exporter, err := otlptracehttp.New(ctx)
	if err != nil {
		return nil, err
	}
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter))
	otel.SetTracerProvider(tp)
	// W3C traceparent and baggage: incoming context from orders becomes the parent span.
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{}, propagation.Baggage{}))
	return tp.Shutdown, nil
}

// traced wraps a handler in a SERVER span named after its route.
func traced(route string, h http.HandlerFunc) http.Handler {
	return otelhttp.NewHandler(otelhttp.WithRouteTag(route, h), route)
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	shutdown, err := initTracer(ctx)
	if err != nil {
		log.Fatalf("otel init: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "UP"})
	})
	fault := newFaultInjector()
	mux.Handle("GET /restaurants/{id}/menu", fault.traced("GET /restaurants/{id}/menu", menu))
	mux.Handle("POST /restaurants/{id}/check", fault.traced("POST /restaurants/{id}/check", check))
	// Chaos admin endpoints, internal to the docker network (the gateway does not route /admin).
	if os.Getenv("CHAOS_ENABLED") == "true" {
		mux.HandleFunc("/admin/fault", fault.admin)
		log.Printf("chaos admin enabled on /admin/fault")
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		log.Printf("restaurants listening on :%s", port)
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
