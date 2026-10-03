package middleware

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════════════════════════════
// REQUEST / RESPONSE — schema khớp với Python service
// ═══════════════════════════════════════════════════════════════════════

type predictRequest struct {
	Type     string `json:"type"`
	Describe string `json:"describe"`
}

type predictResponse struct {
	Label    int  `json:"label"`
	Relevant bool `json:"relevant"`
}

// ═══════════════════════════════════════════════════════════════════════
// CLASSIFIER — gọi ML service để kiểm tra nội dung report
// ═══════════════════════════════════════════════════════════════════════

// ContentClassifier trả về một Gin middleware kiểm tra nội dung
// report trước khi cho phép tạo report.
//
// Middleware đọc request body, extract category + description,
// gọi Python ML service → nếu label == 0 → từ chối (422).
//
// predictURL: URL đầy đủ đến endpoint predict,
// ví dụ: "http://localhost:8000/api/predict"
func ContentClassifier(predictURL string) gin.HandlerFunc {
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	return func(c *gin.Context) {
		// ── 1. Đọc body gốc ─────────────────────────────────────
		bodyBytes, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.AbortWithStatusJSON(
				http.StatusBadRequest,
				gin.H{"error": "cannot read request body"},
			)
			return
		}

		// Ghi lại body để handler phía sau vẫn đọc được.
		c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

		// ── 2. Parse body lấy category + description ─────────────
		var payload struct {
			Category    string `json:"category"`
			Description string `json:"description"`
		}

		if err := json.Unmarshal(bodyBytes, &payload); err != nil {
			// Không parse được → bỏ qua, handler sẽ validate.
			c.Next()
			return
		}

		// Nếu thiếu field → bỏ qua, handler sẽ trả lỗi validate.
		if payload.Category == "" || payload.Description == "" {
			c.Next()
			return
		}

		// ── 3. Gọi Python ML service ─────────────────────────────
		reqBody, _ := json.Marshal(predictRequest{
			Type:     payload.Category,
			Describe: payload.Description,
		})

		resp, err := client.Post(
			predictURL,
			"application/json",
			bytes.NewReader(reqBody),
		)

		if err != nil {
			log.Printf(
				"[ContentClassifier] ML service unavailable: %v",
				err,
			)

			// ML service down → cho qua (fail-open).
			// Đổi sang AbortWithStatusJSON nếu muốn fail-close.
			c.Next()
			return
		}

		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			log.Printf(
				"[ContentClassifier] ML service returned status %d",
				resp.StatusCode,
			)

			// Lỗi từ ML service → cho qua (fail-open).
			c.Next()
			return
		}

		// ── 4. Parse kết quả phân loại ───────────────────────────
		var prediction predictResponse
		if err := json.NewDecoder(resp.Body).Decode(&prediction); err != nil {
			log.Printf(
				"[ContentClassifier] cannot decode prediction: %v",
				err,
			)
			c.Next()
			return
		}

		// ── 5. Từ chối nếu nội dung không liên quan ──────────────
		if !prediction.Relevant {
			c.AbortWithStatusJSON(
				http.StatusUnprocessableEntity,
				gin.H{
					"error": "Nội dung report không liên quan đến hoạt động trường học",
				},
			)
			return
		}

		// ── 6. Nội dung hợp lệ → tiếp tục ───────────────────────
		c.Next()
	}
}

// PredictURL trả về URL của ML predict endpoint.
// Ưu tiên từ env ML_PREDICT_URL, fallback localhost:8000.
func PredictURL() string {
	if url := os.Getenv("ML_PREDICT_URL"); url != "" {
		return url
	}
	port := os.Getenv("ML_SERVICE_PORT")
	if port == "" {
		port = "8000"
	}
	return fmt.Sprintf("http://localhost:%s/api/predict", port)
}
