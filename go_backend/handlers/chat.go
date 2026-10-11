package handlers

import (
	"context"
	"log"
	"net/http"
	"strings"
	"time"

	"go_backend/ai"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct {
	student *ai.StudentChatClient
	admin   *ai.AdminChatClient
	timeout time.Duration
}

func NewChatHandler(
	student *ai.StudentChatClient,
	admin *ai.AdminChatClient,
	timeout time.Duration,
) *ChatHandler {
	return &ChatHandler{
		student: student,
		admin:   admin,
		timeout: timeout,
	}
}

type chatRequest struct {
	Message string `json:"message" binding:"required"`
}

func (h *ChatHandler) Student(c *gin.Context) {
	h.handle(c, func(ctx context.Context, message string) (string, error) {
		return h.student.Ask(ctx, message)
	})
}

func (h *ChatHandler) Admin(c *gin.Context) {
	h.handle(c, func(ctx context.Context, message string) (string, error) {
		return h.admin.Ask(ctx, message)
	})
}

func (h *ChatHandler) handle(
	c *gin.Context,
	ask func(context.Context, string) (string, error),
) {
	var req chatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Tin nhắn không hợp lệ.",
		})
		return
	}

	message := strings.TrimSpace(req.Message)
	if length := len([]rune(message)); length == 0 || length > 1000 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Tin nhắn cần từ 1 đến 1000 ký tự.",
		})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), h.timeout)
	defer cancel()

	answer, err := ask(ctx, message)
	if err != nil {
		log.Printf("chat service error: %v", err)
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Trợ lý AI hiện chưa sẵn sàng. Vui lòng thử lại sau.",
			"code":  "AI_CHAT_UNAVAILABLE",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{"answer": answer})
}
