package handlers

import (
	"errors"
	"log"
	"net/http"

	"go_backend/services"

	"github.com/gin-gonic/gin"
)

func writeServiceError(c *gin.Context, err error) {
	var mismatch *services.AIValidationError
	if errors.As(err, &mismatch) {
		c.JSON(http.StatusUnprocessableEntity, gin.H{
			"error": "Mô tả chưa phù hợp với loại sự cố đã chọn. Hãy kiểm tra lại loại sự cố hoặc mô tả.",
			"code":  "AI_CATEGORY_MISMATCH",
			"ai": gin.H{
				"probability": mismatch.Prediction.Probability,
				"threshold":   mismatch.Prediction.Threshold,
				"model":       mismatch.Prediction.Model,
			},
		})
		return
	}

	var unavailable *services.AIUnavailableError
	if errors.As(err, &unavailable) {
		log.Printf("ML validation unavailable: %v", unavailable)
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Dịch vụ AI kiểm tra report hiện chưa sẵn sàng. Vui lòng thử lại sau.",
			"code":  "AI_UNAVAILABLE",
		})
		return
	}

	switch {
	case errors.Is(err, services.ErrInvalidInput), errors.Is(err, services.ErrInvalidStatus):
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid input"})
	case errors.Is(err, services.ErrUnauthorized):
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid email or password"})
	case errors.Is(err, services.ErrForbidden):
		c.JSON(http.StatusForbidden, gin.H{"error": "forbidden"})
	case errors.Is(err, services.ErrConflict):
		c.JSON(http.StatusConflict, gin.H{"error": "email already registered"})
	case errors.Is(err, services.ErrNotFound):
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
	default:
		// Keep database/internal details out of the HTTP response, but always print
		// the real error in the server terminal so a 500 is diagnosable.
		log.Printf("request failed with internal error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
	}
}
