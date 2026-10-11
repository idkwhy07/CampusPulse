package services

import (
	"context"
	"fmt"

	"go_backend/ai"
)

type CompatibilityValidator interface {
	Predict(
		ctx context.Context,
		typeName string,
		description string,
	) (ai.Prediction, error)
}

type AIValidationView struct {
	Checked     bool    `json:"checked"`
	Matched     bool    `json:"matched"`
	Probability float64 `json:"probability"`
	Threshold   float64 `json:"threshold"`
	Model       string  `json:"model"`
}

type AIValidationError struct {
	Prediction ai.Prediction
}

func (e *AIValidationError) Error() string {
	return fmt.Sprintf(
		"%v: probability %.4f is below threshold %.4f",
		ErrCategoryMismatch,
		e.Prediction.Probability,
		e.Prediction.Threshold,
	)
}

func (e *AIValidationError) Unwrap() error {
	return ErrCategoryMismatch
}

type AIUnavailableError struct {
	Cause error
}

func (e *AIUnavailableError) Error() string {
	if e.Cause == nil {
		return ErrAIUnavailable.Error()
	}
	return fmt.Sprintf("%v: %v", ErrAIUnavailable, e.Cause)
}

func (e *AIUnavailableError) Unwrap() error {
	return ErrAIUnavailable
}
