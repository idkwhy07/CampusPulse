package repositories

import (
	"context"
	"fmt"

	"go_backend/models"
)

type IncidentObservationRepository struct {
	db DBTX
}

func NewIncidentObservationRepository(
	db DBTX,
) *IncidentObservationRepository {
	return &IncidentObservationRepository{
		db: db,
	}
}

// LINK OBSERVATION -> INCIDENT
func (r *IncidentObservationRepository) Link(
	ctx context.Context,
	link models.IncidentObservation,
) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO incident_observations (
			incident_id,
			observation_id,
			relation,
			match_score
		)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (
			incident_id,
			observation_id
		)
		DO NOTHING
	`,
		link.IncidentID,
		link.ObservationID,
		link.Relation,
		link.MatchScore,
	)

	if err != nil {
		return fmt.Errorf(
			"link incident observation: %w",
			err,
		)
	}

	return nil
}

// GET ALL ACTIVE OBSERVATIONS OF INCIDENT
func (r *IncidentObservationRepository) GetObservationsByIncidentID(
	ctx context.Context,
	incidentID int,
) ([]models.Observation, error) {
	rows, err := r.db.Query(ctx, `
		SELECT
			o.id,
			o.user_id,
			o.raw_text,
			o.category,
			o.building,
			o.floor,
			o.room,
			o.service_state,
			o.image_url,
			o.status,
			o.occurred_at,
			o.created_at,
			o.updated_at
		FROM incident_observations io

		JOIN observations o
			ON o.id = io.observation_id

		WHERE io.incident_id = $1
		  AND o.status <> 'DELETED'

		ORDER BY o.created_at ASC
	`, incidentID)

	if err != nil {
		return nil, fmt.Errorf(
			"get incident observations: %w",
			err,
		)
	}
	defer rows.Close()

	items := make([]models.Observation, 0)

	for rows.Next() {
		var obs models.Observation

		err := rows.Scan(
			&obs.ID,
			&obs.UserID,
			&obs.RawText,
			&obs.Category,
			&obs.Building,
			&obs.Floor,
			&obs.Room,
			&obs.ServiceState,
			&obs.ImageURL,
			&obs.Status,
			&obs.OccurredAt,
			&obs.CreatedAt,
			&obs.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf(
				"scan incident observation: %w",
				err,
			)
		}

		items = append(items, obs)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf(
			"iterate incident observations: %w",
			err,
		)
	}

	return items, nil
}

// COUNT ACTIVE SUPPORT REPORTS
//
// Day la count quan trong de xac dinh:
// >= 4 reports -> incident duoc hinh thanh.
func (r *IncidentObservationRepository) CountSupporters(
	ctx context.Context,
	incidentID int,
) (int, error) {
	var count int

	err := r.db.QueryRow(ctx, `
		SELECT COUNT(*)
		FROM incident_observations io

		JOIN observations o
			ON o.id = io.observation_id

		WHERE io.incident_id = $1
		  AND io.relation = 'SUPPORT'
		  AND o.status <> 'DELETED'
	`, incidentID).Scan(&count)

	if err != nil {
		return 0, fmt.Errorf(
			"count supporters: %w",
			err,
		)
	}

	return count, nil
}

// COUNT UNIQUE STUDENTS
//
// So student khac nhau se dung sau nay
// de tinh confidence cho incident.
func (r *IncidentObservationRepository) CountUniqueSupporters(
	ctx context.Context,
	incidentID int,
) (int, error) {
	var count int

	err := r.db.QueryRow(ctx, `
		SELECT COUNT(DISTINCT o.user_id)
		FROM incident_observations io

		JOIN observations o
			ON o.id = io.observation_id

		WHERE io.incident_id = $1
		  AND io.relation = 'SUPPORT'
		  AND o.status <> 'DELETED'
	`, incidentID).Scan(&count)

	if err != nil {
		return 0, fmt.Errorf(
			"count unique supporters: %w",
			err,
		)
	}

	return count, nil
}

// COUNT CONTRADICTIONS
func (r *IncidentObservationRepository) CountContradictions(
	ctx context.Context,
	incidentID int,
) (int, error) {
	var count int

	err := r.db.QueryRow(ctx, `
		SELECT COUNT(*)
		FROM incident_observations io

		JOIN observations o
			ON o.id = io.observation_id

		WHERE io.incident_id = $1
		  AND io.relation = 'CONTRADICT'
		  AND o.status <> 'DELETED'
	`, incidentID).Scan(&count)

	if err != nil {
		return 0, fmt.Errorf(
			"count contradictions: %w",
			err,
		)
	}

	return count, nil
}
