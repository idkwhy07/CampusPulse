package handlers

import (
	"net/http"
	"strconv"
	"strings"
	"time"

	"go_backend/middleware"
	"go_backend/repositories"
	"go_backend/services"

	"github.com/gin-gonic/gin"
)

type ReportHandler struct {
	service *services.ObservationService
}

func NewReportHandler(service *services.ObservationService) *ReportHandler {
	return &ReportHandler{service: service}
}

type createReportRequest struct {
	Category    string     `json:"category" binding:"required"`
	Location    string     `json:"location" binding:"required"`
	Room        string     `json:"room" binding:"required"`
	Description string     `json:"description" binding:"required"`
	OccurredAt  *time.Time `json:"occurred_at"`
	ImageURL    *string    `json:"image_url"`
}

// POST /api/reports
func (h *ReportHandler) Create(c *gin.Context) {
	userID, ok := middleware.UserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "unauthenticated",
		})
		return
	}

	var req createReportRequest

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid report request",
		})
		return
	}

	report, err := h.service.Create(
		c.Request.Context(),
		userID,
		services.CreateObservationInput{
			Category:   req.Category,
			Building:   req.Location,
			Room:       req.Room,
			Text:       req.Description,
			OccurredAt: req.OccurredAt,
			ImageURL:   req.ImageURL,
		},
	)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(http.StatusCreated, report)
}

// GET /api/reports/me
func (h *ReportHandler) ListMine(c *gin.Context) {
	userID, ok := middleware.UserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "unauthenticated",
		})
		return
	}

	filter := repositories.ObservationFilter{
		Room:   strings.TrimSpace(c.Query("room")),
		Search: strings.TrimSpace(c.Query("q")),
	}

	if category := strings.TrimSpace(c.Query("category")); category != "" {
		code, valid := services.CategoryCode(category)

		if !valid {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "invalid category",
			})
			return
		}

		filter.Category = code
	}

	if location := strings.TrimSpace(c.Query("location")); location != "" {
		code, valid := services.BuildingCode(location)

		if !valid {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "invalid location",
			})
			return
		}

		filter.Building = code
	}

	reports, err := h.service.ListMine(
		c.Request.Context(),
		userID,
		filter,
	)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(http.StatusOK, reports)
}

// GET /api/reports/:id
func (h *ReportHandler) GetMine(
	c *gin.Context,
) {
	userID, ok := middleware.UserID(c)
	if !ok {
		c.JSON(
			http.StatusUnauthorized,
			gin.H{
				"error": "unauthenticated",
			},
		)
		return
	}

	id, err := strconv.Atoi(c.Param("id"))
	if err != nil || id <= 0 {
		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error": "invalid report id",
			},
		)
		return
	}

	report, err := h.service.GetMine(
		c.Request.Context(),
		userID,
		id,
	)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(
		http.StatusOK,
		report,
	)
}

// DELETE /api/reports/:id
func (h *ReportHandler) DeleteMine(
	c *gin.Context,
) {
	userID, ok := middleware.UserID(c)
	if !ok {
		c.JSON(
			http.StatusUnauthorized,
			gin.H{
				"error": "unauthenticated",
			},
		)
		return
	}

	id, err := strconv.Atoi(c.Param("id"))
	if err != nil || id <= 0 {
		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error": "invalid report id",
			},
		)
		return
	}

	err = h.service.DeleteMine(
		c.Request.Context(),
		userID,
		id,
	)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.Status(http.StatusNoContent)
}
