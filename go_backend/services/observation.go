package services

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	database "go_backend/databases"
	"go_backend/models"
	"go_backend/repositories"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type CreateObservationInput struct {
	Category   string
	Building   string
	Room       string
	Text       string
	OccurredAt *time.Time
	ImageURL   *string
}

type IncidentTracking struct {
	ID         int    `json:"id"`
	Status     string `json:"status"`
	Confidence int    `json:"confidence"`
}

type ReportView struct {
	ID           int               `json:"id"`
	Category     string            `json:"category"`
	Location     string            `json:"location"`
	Room         string            `json:"room"`
	Description  string            `json:"description"`
	CreatedAt    time.Time         `json:"created_at_raw"`
	CreatedText  string            `json:"created_at"`
	Status       *string           `json:"status"`
	Incident     *IncidentTracking `json:"incident,omitempty"`
	AIValidation *AIValidationView `json:"ai_validation,omitempty"`
}

type ObservationService struct {
	pool         *pgxpool.Pool
	observations *repositories.ObservationRepository
	validator    CompatibilityValidator
}

func NewObservationService(
	pool *pgxpool.Pool,
	validators ...CompatibilityValidator,
) *ObservationService {
	var validator CompatibilityValidator
	if len(validators) > 0 {
		validator = validators[0]
	}

	return &ObservationService{
		pool:         pool,
		observations: repositories.NewObservationRepository(pool),
		validator:    validator,
	}
}

// CREATE REPORT
//
// Toan bo:
// observation -> fusion -> link -> incident
//
// duoc chay trong cung mot transaction.
func (s *ObservationService) Create(
	ctx context.Context,
	userID int,
	input CreateObservationInput,
) (ReportView, error) {
	category, ok := CategoryCode(input.Category)
	if !ok {
		return ReportView{}, fmt.Errorf(
			"%w: invalid category",
			ErrInvalidInput,
		)
	}

	building, ok := BuildingCode(input.Building)
	if !ok {
		return ReportView{}, fmt.Errorf(
			"%w: invalid building",
			ErrInvalidInput,
		)
	}

	room := strings.TrimSpace(input.Room)

	if !IsValidRoom(room) {
		return ReportView{}, fmt.Errorf(
			"%w: invalid room",
			ErrInvalidInput,
		)
	}

	text := strings.TrimSpace(input.Text)

	if len([]rune(text)) < 10 ||
		len([]rune(text)) > 1000 {

		return ReportView{}, fmt.Errorf(
			"%w: description must be 10-1000 characters",
			ErrInvalidInput,
		)
	}

	var imageURL *string

	if input.ImageURL != nil {
		value := strings.TrimSpace(*input.ImageURL)

		if value != "" {
			imageURL = &value
		}
	}

	var aiValidation *AIValidationView

	// Model hien tai chi ho tro 6 nhom cu the.
	// "Khac" duoc phep gui ma khong chan boi AI.
	if category != "OTHER" && s.validator != nil {
		prediction, err := s.validator.Predict(
			ctx,
			CategoryLabel(category),
			text,
		)
		if err != nil {
			return ReportView{}, &AIUnavailableError{Cause: err}
		}

		aiValidation = &AIValidationView{
			Checked:     true,
			Matched:     prediction.IsMatch,
			Probability: prediction.Probability,
			Threshold:   prediction.Threshold,
			Model:       prediction.Model,
		}

		if !prediction.IsMatch {
			return ReportView{}, &AIValidationError{
				Prediction: prediction,
			}
		}
	}

	obs := models.Observation{
		UserID:       userID,
		RawText:      text,
		Category:     category,
		Building:     building,
		Room:         &room,
		ServiceState: "UNKNOWN",
		ImageURL:     imageURL,
		Status:       models.ObservationActive,
		OccurredAt:   input.OccurredAt,
	}

	err := database.WithTx(
		ctx,
		s.pool,
		func(tx pgx.Tx) error {
			// Tao repository gan voi transaction.
			observationRepo :=
				repositories.NewObservationRepository(tx)

			incidentRepo :=
				repositories.NewIncidentRepository(tx)

			linkRepo :=
				repositories.NewIncidentObservationRepository(tx)

			fusionService :=
				NewFusionService(
					incidentRepo,
					linkRepo,
				)

			// 1. Luu report.
			if err := observationRepo.Create(
				ctx,
				&obs,
			); err != nil {
				return fmt.Errorf(
					"create observation: %w",
					err,
				)
			}

			// 2. Gom report vao incident.
			if _, err := fusionService.AttachObservation(
				ctx,
				obs,
			); err != nil {
				return fmt.Errorf(
					"fusion observation: %w",
					err,
				)
			}

			return nil
		},
	)

	if err != nil {
		return ReportView{}, err
	}

	// Transaction da commit.
	//
	// Doc lai report de response co thong tin incident
	// neu incident vua duoc hinh thanh.
	item, err := s.observations.GetByIDWithIncident(
		ctx,
		obs.ID,
	)

	if errors.Is(err, repositories.ErrNotFound) {
		return ReportView{}, ErrNotFound
	}

	if err != nil {
		return ReportView{}, err
	}

	view := reportView(item)
	view.AIValidation = aiValidation

	return view, nil
}

// LIST REPORTS OF CURRENT STUDENT
func (s *ObservationService) ListMine(
	ctx context.Context,
	userID int,
	filter repositories.ObservationFilter,
) ([]ReportView, error) {
	items, err := s.observations.GetByUserID(
		ctx,
		userID,
		filter,
	)

	if err != nil {
		return nil, err
	}

	result := make(
		[]ReportView,
		0,
		len(items),
	)

	for _, item := range items {
		result = append(
			result,
			reportView(item),
		)
	}

	return result, nil
}

// GET ONE REPORT OF CURRENT STUDENT
func (s *ObservationService) GetMine(
	ctx context.Context,
	userID int,
	id int,
) (ReportView, error) {
	item, err :=
		s.observations.GetByIDWithIncident(
			ctx,
			id,
		)

	if errors.Is(err, repositories.ErrNotFound) {
		return ReportView{}, ErrNotFound
	}

	if err != nil {
		return ReportView{}, err
	}

	// Student khong duoc xem report cua student khac.
	if item.Observation.UserID != userID {
		return ReportView{}, ErrForbidden
	}

	return reportView(item), nil
}

// DELETE ONE REPORT OF CURRENT STUDENT
func (s *ObservationService) DeleteMine(
	ctx context.Context,
	userID int,
	id int,
) error {
	obs, err :=
		s.observations.GetByID(
			ctx,
			id,
		)

	if errors.Is(err, repositories.ErrNotFound) {
		return ErrNotFound
	}

	if err != nil {
		return err
	}

	// Student chi duoc xoa report cua chinh minh.
	if obs.UserID != userID {
		return ErrForbidden
	}

	err = s.observations.SoftDelete(
		ctx,
		id,
		userID,
	)

	if errors.Is(err, repositories.ErrNotFound) {
		return ErrNotFound
	}

	if err != nil {
		return err
	}

	return nil
}

func reportView(
	item repositories.ObservationWithIncident,
) ReportView {
	room := ""

	if item.Observation.Room != nil {
		room = *item.Observation.Room
	}

	view := ReportView{
		ID:          item.Observation.ID,
		Category:    CategoryLabel(item.Observation.Category),
		Location:    BuildingLabel(item.Observation.Building),
		Room:        room,
		Description: item.Observation.RawText,
		CreatedAt:   item.Observation.CreatedAt,
		CreatedText: item.Observation.CreatedAt.Format(
			"02/01/2006 15:04:05",
		),
	}

	// Student chi thay incident khi du threshold.
	formed :=
		item.IncidentReportCount != nil &&
			*item.IncidentReportCount >=
				IncidentFormationThreshold

	if item.IncidentID != nil &&
		item.IncidentStatus != nil &&
		item.IncidentConfidence != nil &&
		formed {

		status := UIStatus(
			*item.IncidentStatus,
		)

		if status != "" {
			view.Status = &status

			view.Incident =
				&IncidentTracking{
					ID: *item.IncidentID,

					Status: *item.IncidentStatus,

					Confidence: *item.IncidentConfidence,
				}
		}
	}

	return view
}
