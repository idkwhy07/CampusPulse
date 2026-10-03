package services

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"go_backend/models"
	"go_backend/repositories"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	users     *repositories.UserRepository
	jwtSecret []byte
}

type LoginResult struct {
	Token string      `json:"token"`
	User  models.User `json:"user"`
}

type Claims struct {
	UserID int    `json:"user_id"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

func NewAuthService(users *repositories.UserRepository, jwtSecret string) *AuthService {
	return &AuthService{users: users, jwtSecret: []byte(jwtSecret)}
}

// LOGIN
func (s *AuthService) Login(ctx context.Context, email, password string) (LoginResult, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	user, err := s.users.GetByEmail(ctx, email)
	if errors.Is(err, repositories.ErrNotFound) {
		return LoginResult{}, ErrUnauthorized
	}
	if err != nil {
		return LoginResult{}, err
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
		return LoginResult{}, ErrUnauthorized
	}

	return s.loginResult(user)
}

// REGISTER
func (s *AuthService) Register(ctx context.Context, name, email, password string) (LoginResult, error) {
	name = strings.TrimSpace(name)
	email = strings.ToLower(strings.TrimSpace(email))

	if len([]rune(name)) < 2 || len([]rune(name)) > 100 {
		return LoginResult{}, fmt.Errorf("%w: invalid name", ErrInvalidInput)
	}
	if len(password) < 6 || len(password) > 72 {
		return LoginResult{}, fmt.Errorf("%w: password must be 6-72 characters", ErrInvalidInput)
	}

	_, err := s.users.GetByEmail(ctx, email)
	if err == nil {
		return LoginResult{}, ErrConflict
	}
	if !errors.Is(err, repositories.ErrNotFound) {
		return LoginResult{}, err
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return LoginResult{}, fmt.Errorf("hash password: %w", err)
	}

	user := models.User{
		Name:         name,
		Email:        email,
		PasswordHash: string(hash),
		Role:         models.RoleStudent,
	}
	if err := s.users.Create(ctx, &user); err != nil {
		return LoginResult{}, err
	}

	return s.loginResult(user)
}

func (s *AuthService) loginResult(user models.User) (LoginResult, error) {
	now := time.Now()
	claims := Claims{
		UserID: user.ID,
		Role:   user.Role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(now.Add(8 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(now),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(s.jwtSecret)
	if err != nil {
		return LoginResult{}, fmt.Errorf("sign jwt: %w", err)
	}

	user.PasswordHash = ""
	return LoginResult{Token: signed, User: user}, nil
}
