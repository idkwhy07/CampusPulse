package main

import (
	"context"
	"log"
	"net/http"
	"os"

	database "go_backend/databases"
	"go_backend/handlers"
	"go_backend/middleware"
	"go_backend/models"
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

	// ket noi database
	pool, err := database.Connect(ctx, databaseURL)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()

	if err := database.RunMigrations(
		ctx,
		pool,
	); err != nil {
		log.Fatal(err)
	}

	// repositories
	userRepo := repositories.NewUserRepository(pool)

	// services
	authService := services.NewAuthService(
		userRepo,
		jwtSecret,
	)

	observationService := services.NewObservationService(
		pool,
	)

	incidentService := services.NewIncidentService(
		pool,
	)

	// handlers
	authHandler := handlers.NewAuthHandler(
		authService,
	)

	reportHandler := handlers.NewReportHandler(
		observationService,
	)

	incidentHandler := handlers.NewIncidentHandler(
		incidentService,
	)

	// router
	router := gin.Default()

	if err := router.SetTrustedProxies(nil); err != nil {
		log.Fatal(err)
	}

	// health check
	router.GET("/health", func(c *gin.Context) {
		if err := pool.Ping(c.Request.Context()); err != nil {
			c.JSON(
				http.StatusServiceUnavailable,
				gin.H{"status": "down"},
			)
			return
		}

		c.JSON(
			http.StatusOK,
			gin.H{"status": "ok"},
		)
	})

	api := router.Group("/api")

	// public routes
	api.POST(
		"/auth/login",
		authHandler.Login,
	)

	api.POST(
		"/auth/register",
		authHandler.Register,
	)

	// JWT protected routes
	protected := api.Group("")

	protected.Use(
		middleware.Auth(jwtSecret),
	)

	// STUDENT REPORT ROUTES
	studentReports := protected.Group("/reports")

	studentReports.Use(
		middleware.RequireRole(models.RoleStudent),
	)

	studentReports.POST(
		"",
		reportHandler.Create,
	)

	studentReports.GET(
		"/me",
		reportHandler.ListMine,
	)

	studentReports.GET(
		"/:id",
		reportHandler.GetMine,
	)

	studentReports.DELETE(
		"/:id",
		reportHandler.DeleteMine,
	)


	// STAFF INCIDENT ROUTES
	staffIncidents := protected.Group("/incidents")

	staffIncidents.Use(
		middleware.RequireRole(models.RoleStaff),
	)

	staffIncidents.GET(
		"",
		incidentHandler.List,
	)

	staffIncidents.GET(
		"/:id",
		incidentHandler.Get,
	)

	staffIncidents.GET(
		"/:id/observations",
		incidentHandler.Evidence,
	)

	staffIncidents.PATCH(
		"/:id/status",
		incidentHandler.UpdateStatus,
	)

	port := os.Getenv("PORT")

	if port == "" {
		port = "8080"
	}

	log.Printf(
		"CampusPulse running at http://127.0.0.1:%s",
		port,
	)

	if err := router.Run(":" + port); err != nil {
		log.Fatal(err)
	}
}
