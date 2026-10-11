package services

import "errors"

var (
	ErrNotFound         = errors.New("not found")
	ErrForbidden        = errors.New("forbidden")
	ErrInvalidInput     = errors.New("invalid input")
	ErrInvalidStatus    = errors.New("invalid status")
	ErrUnauthorized     = errors.New("unauthorized")
	ErrConflict         = errors.New("conflict")
	ErrCategoryMismatch = errors.New("category description mismatch")
	ErrAIUnavailable    = errors.New("ai validation unavailable")
)
