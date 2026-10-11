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

const maxChatResponseBytes = 1 << 20

type StudentChatClient struct {
	baseURL string
	client  *http.Client
}

type AdminChatClient struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

func NewStudentChatClient(baseURL string, timeout time.Duration) (*StudentChatClient, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		return nil, fmt.Errorf("student AI URL is required")
	}
	if _, err := url.ParseRequestURI(baseURL); err != nil {
		return nil, fmt.Errorf("invalid student AI URL: %w", err)
	}
	if timeout <= 0 {
		return nil, fmt.Errorf("student AI timeout must be positive")
	}
	return &StudentChatClient{
		baseURL: baseURL,
		client:  &http.Client{Timeout: timeout},
	}, nil
}

func NewAdminChatClient(baseURL, apiKey string, timeout time.Duration) (*AdminChatClient, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	apiKey = strings.TrimSpace(apiKey)
	if baseURL == "" {
		return nil, fmt.Errorf("admin AI URL is required")
	}
	if _, err := url.ParseRequestURI(baseURL); err != nil {
		return nil, fmt.Errorf("invalid admin AI URL: %w", err)
	}
	if apiKey == "" {
		return nil, fmt.Errorf("admin AI internal key is required")
	}
	if timeout <= 0 {
		return nil, fmt.Errorf("admin AI timeout must be positive")
	}
	return &AdminChatClient{
		baseURL: baseURL,
		apiKey:  apiKey,
		client:  &http.Client{Timeout: timeout},
	}, nil
}

func (c *StudentChatClient) Ask(ctx context.Context, message string) (string, error) {
	payload, err := json.Marshal(map[string]string{
		"query": strings.TrimSpace(message),
	})
	if err != nil {
		return "", fmt.Errorf("encode student AI request: %w", err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/api/chat",
		bytes.NewReader(payload),
	)
	if err != nil {
		return "", fmt.Errorf("create student AI request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("student AI request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, maxChatResponseBytes))
	if err != nil {
		return "", fmt.Errorf("read student AI response: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("student AI status %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}

	var result struct {
		Answer string `json:"answer"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("decode student AI response: %w", err)
	}
	result.Answer = strings.TrimSpace(result.Answer)
	if result.Answer == "" {
		return "", fmt.Errorf("student AI returned empty answer")
	}
	return result.Answer, nil
}

func (c *AdminChatClient) Ask(ctx context.Context, message string) (string, error) {
	payload, err := json.Marshal(map[string]any{
		"question": strings.TrimSpace(message),
		"top_k":    5,
	})
	if err != nil {
		return "", fmt.Errorf("encode admin AI request: %w", err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/internal/admin/chat",
		bytes.NewReader(payload),
	)
	if err != nil {
		return "", fmt.Errorf("create admin AI request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", c.apiKey)

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("admin AI request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, maxChatResponseBytes))
	if err != nil {
		return "", fmt.Errorf("read admin AI response: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("admin AI status %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}

	var result struct {
		Answer string `json:"answer"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("decode admin AI response: %w", err)
	}
	result.Answer = strings.TrimSpace(result.Answer)
	if result.Answer == "" {
		return "", fmt.Errorf("admin AI returned empty answer")
	}
	return result.Answer, nil
}
