package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"go_backend/ai"
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
	if err := godotenv.Load(); err != nil {
		log.Printf(".env not loaded; using process environment: %v", err)
	}

	ctx := context.Background()

	databaseURL := os.Getenv("DATABASE_URL")
	jwtSecret := os.Getenv("JWT_SECRET")

	mlTimeout := 3 * time.Second
	if raw := strings.TrimSpace(os.Getenv("CAMPUSPULSE_ML_TIMEOUT")); raw != "" {
		parsed, err := time.ParseDuration(raw)
		if err != nil || parsed <= 0 {
			log.Fatal("CAMPUSPULSE_ML_TIMEOUT must be a positive Go duration, e.g. 3s")
		}
		mlTimeout = parsed
	}

	chatTimeout := 60 * time.Second
	if raw := strings.TrimSpace(os.Getenv("CAMPUSPULSE_CHAT_TIMEOUT")); raw != "" {
		parsed, err := time.ParseDuration(raw)
		if err != nil || parsed <= 0 {
			log.Fatal("CAMPUSPULSE_CHAT_TIMEOUT must be a positive Go duration, e.g. 60s")
		}
		chatTimeout = parsed
	}

	studentAIURL := strings.TrimSpace(os.Getenv("CAMPUSPULSE_STUDENT_AI_URL"))
	if studentAIURL == "" {
		studentAIURL = "http://127.0.0.1:8003"
	}

	adminAIURL := strings.TrimSpace(os.Getenv("CAMPUSPULSE_ADMIN_AI_URL"))
	if adminAIURL == "" {
		adminAIURL = "http://127.0.0.1:8001"
	}

	adminAIKey := strings.TrimSpace(os.Getenv("CAMPUSPULSE_ADMIN_AI_KEY"))
	if adminAIKey == "" {
		log.Fatal("CAMPUSPULSE_ADMIN_AI_KEY is required")
	}

	mlEnabled := strings.ToLower(strings.TrimSpace(os.Getenv("CAMPUSPULSE_ML_ENABLED"))) != "false"
	mlURL := strings.TrimSpace(os.Getenv("CAMPUSPULSE_ML_API_URL"))
	if mlURL == "" {
		mlURL = "http://127.0.0.1:8002"
	}

	var mlClient *ai.MLClient
	if mlEnabled {
		client, mlErr := ai.NewMLClient(mlURL, mlTimeout)
		if mlErr != nil {
			log.Fatal(mlErr)
		}
		mlClient = client
		log.Printf("CampusPulse ML validation enabled: %s", mlURL)
	} else {
		log.Printf("CampusPulse ML validation disabled by CAMPUSPULSE_ML_ENABLED=false")
	}

	studentChatClient, err := ai.NewStudentChatClient(studentAIURL, chatTimeout)
	if err != nil {
		log.Fatal(err)
	}

	adminChatClient, err := ai.NewAdminChatClient(adminAIURL, adminAIKey, chatTimeout)
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("CampusPulse student chatbot: %s", studentAIURL)
	log.Printf("CampusPulse admin chatbot: %s", adminAIURL)

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

	var validator services.CompatibilityValidator
	if mlClient != nil {
		validator = mlClient
	}

	observationService := services.NewObservationService(
		pool,
		validator,
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

	chatHandler := handlers.NewChatHandler(
		studentChatClient,
		adminChatClient,
		chatTimeout,
	)

	// router
	router := gin.Default()

	if err := router.SetTrustedProxies(nil); err != nil {
		log.Fatal(err)
	}

	// Frontend HTML/CSS/JS.
	router.LoadHTMLGlob("../templates/*.html")
	router.Static("/static", "../static")

	router.GET("/", func(c *gin.Context) {
		c.HTML(
			http.StatusOK,
			"student.html",
			nil,
		)
	})

	router.GET("/login", func(c *gin.Context) {
		c.HTML(
			http.StatusOK,
			"login.html",
			nil,
		)
	})

	router.GET("/register", func(c *gin.Context) {
		c.HTML(
			http.StatusOK,
			"register.html",
			nil,
		)
	})

	router.GET("/admin", func(c *gin.Context) {
		c.HTML(
			http.StatusOK,
			"admin.html",
			nil,
		)
	})

	router.GET("/admin/reports", func(c *gin.Context) {
		c.HTML(
			http.StatusOK,
			"admin_reports.html",
			nil,
		)
	})

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

	api.GET("/ai/health", func(c *gin.Context) {
		if mlClient == nil {
			c.JSON(http.StatusOK, gin.H{
				"enabled": false,
				"ready":   false,
			})
			return
		}

		healthCtx, cancel := context.WithTimeout(c.Request.Context(), mlTimeout)
		defer cancel()

		health, err := mlClient.Health(healthCtx)
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"enabled": true,
				"ready":   false,
				"error":   "ML service unavailable",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"enabled":   true,
			"ready":     health.Ready,
			"model":     health.Model,
			"threshold": health.Threshold,
		})
	})

	// Public options used by Student/Admin frontend.
	api.GET("/options", func(c *gin.Context) {
		c.JSON(
			http.StatusOK,
			gin.H{
				"categories":        services.Categories(),
				"locations":         services.Locations(),
				"rooms_by_location": services.RoomsByLocation(),
			},
		)
	})

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

	// POST tạo report — qua middleware phân loại nội dung trước
	studentReports.POST(
		"",
		middleware.ContentClassifier(
			middleware.PredictURL(),
		),
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

	// STUDENT CHATBOT ROUTE
	studentChat := protected.Group("/chat/student")
	studentChat.Use(
		middleware.RequireRole(models.RoleStudent),
	)
	studentChat.POST(
		"",
		chatHandler.Student,
	)

	// ADMIN CHATBOT ROUTE
	adminChat := protected.Group("/chat/admin")
	adminChat.Use(
		middleware.RequireRole(models.RoleStaff),
	)
	adminChat.POST(
		"",
		chatHandler.Admin,
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
