package main

import (
	"context"
	"log"
	"net/http"
	"os"

	database "go_backend/databases"
	"go_backend/handlers"
	"go_backend/repositories"
	"go_backend/services"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// lay gia tri tu file .env
	err := godotenv.Load()
	if err != nil {
		log.Fatal(err)
	}

	ctx := context.Background()
	databaseURL := os.Getenv("DATABASE_URL")
	jwtSecret := os.Getenv("JWT_SECRET")
	if jwtSecret == "" {
		log.Fatal("JWT_SECRET is required")
	}
	// ket noi db
	pool, err := database.Connect(ctx, databaseURL)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()

	userRepo := repositories.NewUserRepository(pool)
	authService := services.NewAuthService(userRepo, jwtSecret)

	// khoi tao router
	router := gin.Default()
	if err := router.SetTrustedProxies(nil); err != nil {
		log.Fatal(err)
	}

	authHandler := handlers.NewAuthHandler(authService)

	// check status ok
	router.GET("/health", func(c *gin.Context) {
		if err := pool.Ping(c.Request.Context()); err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"status": "down"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	api := router.Group("/api")
	api.POST("/auth/login", authHandler.Login)
	api.POST("/auth/register", authHandler.Register)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("CampusPulse running at http://127.0.0.1:%s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal(err)
	}
}
