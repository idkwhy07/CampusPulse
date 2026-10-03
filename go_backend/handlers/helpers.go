package handlers

import (
	"errors"
	"log"
	"net/http"

	"go_backend/services"

	"github.com/gin-gonic/gin"
)

func writeServiceError(c *gin.Context, err error) {
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
