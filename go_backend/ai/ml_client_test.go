package ai

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestMLClientPredict(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/predict" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if r.Method != http.MethodPost {
			t.Fatalf("unexpected method: %s", r.Method)
		}

		var payload map[string]string
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("decode request: %v", err)
		}
		if payload["Type"] != "Mạng / Đường truyền" {
			t.Fatalf("unexpected Type: %q", payload["Type"])
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(Prediction{
			Type:        "Mạng và đường truyền",
			Describe:    payload["Describe"],
			Label:       1,
			IsMatch:     true,
			Probability: 0.98,
			Threshold:   0.5,
			Model:       "test-model",
		})
	}))
	defer server.Close()

	client, err := NewMLClient(server.URL, time.Second)
	if err != nil {
		t.Fatalf("NewMLClient: %v", err)
	}

	result, err := client.Predict(
		context.Background(),
		"Mạng / Đường truyền",
		"wifi không vào được mạng",
	)
	if err != nil {
		t.Fatalf("Predict: %v", err)
	}
	if !result.IsMatch || result.Label != 1 {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestMLClientHealth(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok","ready":true,"model":"test-model","threshold":0.5}`))
	}))
	defer server.Close()

	client, err := NewMLClient(server.URL, time.Second)
	if err != nil {
		t.Fatalf("NewMLClient: %v", err)
	}

	health, err := client.Health(context.Background())
	if err != nil {
		t.Fatalf("Health: %v", err)
	}
	if !health.Ready || health.Model != "test-model" {
		t.Fatalf("unexpected health: %+v", health)
	}
}
