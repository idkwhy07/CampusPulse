package repositories

import (
	"context"
	"errors"
	"fmt"

	"go_backend/models"

	"github.com/jackc/pgx/v5"
)

type IncidentRepository struct {
	db DBTX
}

func NewIncidentRepository(db DBTX) *IncidentRepository {
	return &IncidentRepository{
		db: db,
	}
}

// CREATE INCIDENT
func (r *IncidentRepository) Create(
	ctx context.Context,
	incident *models.Incident,
) error {
	err := r.db.QueryRow(ctx, `
		INSERT INTO incidents (
			title,
			category,
			building,
			floor,
			room,
			status,
			severity,
			confidence,
			assigned_team
		)
		VALUES (
			$1, $2, $3, $4, $5,
			$6, $7, $8, $9
		)
		RETURNING
			id,
			created_at,
			updated_at
	`,
		incident.Title,
		incident.Category,
		incident.Building,
		incident.Floor,
		incident.Room,
		incident.Status,
		incident.Severity,
		incident.Confidence,
		incident.AssignedTeam,
	).Scan(
		&incident.ID,
		&incident.CreatedAt,
		&incident.UpdatedAt,
	)

	if err != nil {
		return fmt.Errorf(
			"create incident: %w",
			err,
		)
	}

	return nil
}

// FIND EXISTING OPEN INCIDENT
//
// CampusPulse gom report dua tren:
// category + building + room.
//
// Neu incident cung key da ton tai va chua RESOLVED,
// report moi se duoc noi vao incident do.
func (r *IncidentRepository) FindOpenByKey(
	ctx context.Context,
	category string,
	building string,
	room *string,
) (models.Incident, error) {
	var incident models.Incident

	err := r.db.QueryRow(ctx, `
		SELECT
			id,
			title,
			category,
			building,
			floor,
			room,
			status,
			severity,
			confidence,
			assigned_team,
			created_at,
			updated_at,
			resolved_at
		FROM incidents
		WHERE category = $1
		  AND building = $2
		  AND room IS NOT DISTINCT FROM $3
		  AND status <> 'RESOLVED'
		ORDER BY
			CASE status
				WHEN 'IN_PROGRESS' THEN 1
				WHEN 'CONFIRMED' THEN 2
				ELSE 3
			END,
			created_at DESC
		LIMIT 1
	`,
		category,
		building,
		room,
	).Scan(
		&incident.ID,
		&incident.Title,
		&incident.Category,
		&incident.Building,
		&incident.Floor,
		&incident.Room,
		&incident.Status,
		&incident.Severity,
		&incident.Confidence,
		&incident.AssignedTeam,
		&incident.CreatedAt,
		&incident.UpdatedAt,
		&incident.ResolvedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return models.Incident{}, ErrNotFound
	}

	if err != nil {
		return models.Incident{}, fmt.Errorf(
			"find open incident by key: %w",
			err,
		)
	}

	return incident, nil
}

// UPDATE CONFIDENCE
func (r *IncidentRepository) UpdateConfidence(
	ctx context.Context,
	id int,
	confidence int,
) error {
	tag, err := r.db.Exec(ctx, `
		UPDATE incidents
		SET
			confidence = $2,
			updated_at = NOW()
		WHERE id = $1
	`,
		id,
		confidence,
	)

	if err != nil {
		return fmt.Errorf(
			"update incident confidence: %w",
			err,
		)
	}

	if tag.RowsAffected() == 0 {
		return ErrNotFound
	}

	return nil
}

// CONFIRM INCIDENT
//
// Incident bat dau o EMERGING.
// Khi du 4 reports, FusionService se goi method nay
// de chuyen incident thanh CONFIRMED.
func (r *IncidentRepository) ConfirmFormation(
	ctx context.Context,
	id int,
) error {
	_, err := r.db.Exec(ctx, `
		UPDATE incidents
		SET
			status = 'CONFIRMED',
			updated_at = NOW()
		WHERE id = $1
		  AND status = 'EMERGING'
	`, id)

	if err != nil {
		return fmt.Errorf(
			"confirm incident formation: %w",
			err,
		)
	}

	return nil
}
