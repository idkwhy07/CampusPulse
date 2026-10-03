package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"go_backend/services"

	"github.com/gin-gonic/gin"
)

type IncidentHandler struct {
	service *services.IncidentService
}

func NewIncidentHandler(
	service *services.IncidentService,
) *IncidentHandler {
	return &IncidentHandler{
		service: service,
	}
}

func (h *IncidentHandler) List(
	c *gin.Context,
) {
	search :=
		strings.TrimSpace(
			c.Query("search"),
		)

	if search == "" {
		search =
			strings.TrimSpace(
				c.Query("q"),
			)
	}

	filter, err :=
		services.BuildIncidentFilter(
			strings.TrimSpace(
				c.Query("status"),
			),
			strings.TrimSpace(
				c.Query("category"),
			),
			strings.TrimSpace(
				c.Query("location"),
			),
			strings.TrimSpace(
				c.Query("room"),
			),
			search,
		)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	items, err := h.service.List(
		c.Request.Context(),
		filter,
	)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(
		http.StatusOK,
		items,
	)
}

func (h *IncidentHandler) Get(
	c *gin.Context,
) {
	id, ok := parsePositiveID(c)

	if !ok {
		return
	}

	item, err :=
		h.service.Get(
			c.Request.Context(),
			id,
		)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(
		http.StatusOK,
		item,
	)
}

func (h *IncidentHandler) Evidence(
	c *gin.Context,
) {
	id, ok := parsePositiveID(c)

	if !ok {
		return
	}

	items, err :=
		h.service.Evidence(
			c.Request.Context(),
			id,
		)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(
		http.StatusOK,
		items,
	)
}

type updateStatusRequest struct {
	Status string `json:"status" binding:"required"`
}

func (h *IncidentHandler) UpdateStatus(
	c *gin.Context,
) {
	id, ok := parsePositiveID(c)

	if !ok {
		return
	}

	var req updateStatusRequest

	if err :=
		c.ShouldBindJSON(&req); err != nil {

		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error":
				"invalid status request",
			},
		)

		return
	}

	item, err :=
		h.service.UpdateStatus(
			c.Request.Context(),
			id,
			req.Status,
		)

	if err != nil {
		writeServiceError(c, err)
		return
	}

	c.JSON(
		http.StatusOK,
		gin.H{
			"ok":       true,
			"incident": item,
		},
	)
}

func parsePositiveID(
	c *gin.Context,
) (int, bool) {
	id, err :=
		strconv.Atoi(
			c.Param("id"),
		)

	if err != nil ||
		id <= 0 {

		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error": "invalid id",
			},
		)

		return 0, false
	}

	return id, true
}
