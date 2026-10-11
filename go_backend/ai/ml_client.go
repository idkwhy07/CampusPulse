package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Prediction struct {
	Type        string  `json:"type"`
	Describe    string  `json:"describe"`
	Label       int     `json:"label"`
	IsMatch     bool    `json:"is_match"`
	Probability float64 `json:"probability"`
	Threshold   float64 `json:"threshold"`
	Model       string  `json:"model"`
}

type Health struct {
	Status    string  `json:"status"`
	Ready     bool    `json:"ready"`
	Model     string  `json:"model"`
	Threshold float64 `json:"threshold"`
}

type MLClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewMLClient(baseURL string, timeout time.Duration) (*MLClient, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		return nil, nil
	}

	parsed, err := url.Parse(baseURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid CAMPUSPULSE_ML_API_URL: %q", baseURL)
	}

	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return nil, fmt.Errorf("unsupported ML API scheme: %s", parsed.Scheme)
	}

	if timeout <= 0 {
		timeout = 3 * time.Second
	}

	return &MLClient{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}, nil
}

func (c *MLClient) Predict(
	ctx context.Context,
	typeName string,
	description string,
) (Prediction, error) {
	if c == nil {
		return Prediction{}, fmt.Errorf("ML client is disabled")
	}

	payload := map[string]string{
		"Type":     typeName,
		"Describe": description,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return Prediction{}, fmt.Errorf("marshal ML request: %w", err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/predict",
		bytes.NewReader(body),
	)
	if err != nil {
		return Prediction{}, fmt.Errorf("create ML request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return Prediction{}, fmt.Errorf("call ML API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 16*1024))
		message := strings.TrimSpace(string(raw))
		if message == "" {
			message = http.StatusText(resp.StatusCode)
		}
		return Prediction{}, fmt.Errorf(
			"ML API returned %d: %s",
			resp.StatusCode,
			message,
		)
	}

	var prediction Prediction
	if err := json.NewDecoder(resp.Body).Decode(&prediction); err != nil {
		return Prediction{}, fmt.Errorf("decode ML response: %w", err)
	}

	if prediction.Label != 0 && prediction.Label != 1 {
		return Prediction{}, fmt.Errorf("ML API returned invalid label: %d", prediction.Label)
	}
	if prediction.Probability < 0 || prediction.Probability > 1 {
		return Prediction{}, fmt.Errorf("ML API returned invalid probability: %f", prediction.Probability)
	}
	if prediction.Threshold <= 0 || prediction.Threshold >= 1 {
		return Prediction{}, fmt.Errorf("ML API returned invalid threshold: %f", prediction.Threshold)
	}

	return prediction, nil
}

func (c *MLClient) Health(ctx context.Context) (Health, error) {
	if c == nil {
		return Health{}, fmt.Errorf("ML client is disabled")
	}

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		c.baseURL+"/health",
		nil,
	)
	if err != nil {
		return Health{}, fmt.Errorf("create ML health request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return Health{}, fmt.Errorf("call ML health: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return Health{}, fmt.Errorf("ML health returned %d", resp.StatusCode)
	}

	var health Health
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return Health{}, fmt.Errorf("decode ML health: %w", err)
	}
	if !health.Ready {
		return Health{}, fmt.Errorf("ML service is not ready")
	}

	return health, nil
}
