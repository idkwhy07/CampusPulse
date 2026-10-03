package repositories

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"go_backend/models"

	"github.com/jackc/pgx/v5"
)

type ObservationFilter struct {
	Category string
	Building string
	Room     string
	Search   string
}

type ObservationWithIncident struct {
	Observation         models.Observation
	IncidentID          *int
	IncidentStatus      *string
	IncidentConfidence  *int
	IncidentReportCount *int
}

type ObservationRepository struct {
	db DBTX
}

func NewObservationRepository(db DBTX) *ObservationRepository {
	return &ObservationRepository{db: db}
}

// CREATE
func (r *ObservationRepository) Create(ctx context.Context, obs *models.Observation) error {
	err := r.db.QueryRow(
		ctx, `
		INSERT INTO observations (
			user_id,
			raw_text,
			category,
			building,
			floor,
			room,
			service_state,
			image_url,
			status,
			occurred_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		RETURNING id, created_at, updated_at
	`,
		obs.UserID,
		obs.RawText,
		obs.Category,
		obs.Building,
		obs.Floor,
		obs.Room,
		obs.ServiceState,
		obs.ImageURL,
		obs.Status,
		obs.OccurredAt,
	).Scan(
		&obs.ID,
		&obs.CreatedAt,
		&obs.UpdatedAt,
	)
	if err != nil {
		return fmt.Errorf("create observation: %w", err)
	}

	return nil
}

// GET BY ID
func (r *ObservationRepository) GetByID(
	ctx context.Context,
	id int,
) (models.Observation, error) {
	var obs models.Observation

	err := r.db.QueryRow(ctx, `
		SELECT
			id,
			user_id,
			raw_text,
			category,
			building,
			floor,
			room,
			service_state,
			image_url,
			status,
			occurred_at,
			created_at,
			updated_at
		FROM observations
		WHERE id = $1
		  AND status <> 'DELETED'
	`, id).Scan(
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

	if errors.Is(err, pgx.ErrNoRows) {
		return models.Observation{}, ErrNotFound
	}

	if err != nil {
		return models.Observation{}, fmt.Errorf("get observation: %w", err)
	}

	return obs, nil
}

// GET BY ID + INCIDENT
func (r *ObservationRepository) GetByIDWithIncident(
	ctx context.Context,
	id int,
) (ObservationWithIncident, error) {
	var item ObservationWithIncident

	err := r.db.QueryRow(ctx, `
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
			o.updated_at,

			i.id,
			i.status,
			i.confidence,

			CASE
				WHEN i.id IS NULL THEN NULL
				ELSE (
					SELECT COUNT(*)::int
					FROM incident_observations support_io
					JOIN observations support_o
						ON support_o.id = support_io.observation_id
					WHERE support_io.incident_id = i.id
					  AND support_io.relation = 'SUPPORT'
					  AND support_o.status <> 'DELETED'
				)
			END AS report_count

		FROM observations o

		LEFT JOIN incident_observations io
			ON io.observation_id = o.id
			AND io.relation = 'SUPPORT'

		LEFT JOIN incidents i
			ON i.id = io.incident_id

		WHERE o.id = $1
		  AND o.status <> 'DELETED'

		ORDER BY i.id DESC NULLS LAST
		LIMIT 1
	`, id).Scan(
		&item.Observation.ID,
		&item.Observation.UserID,
		&item.Observation.RawText,
		&item.Observation.Category,
		&item.Observation.Building,
		&item.Observation.Floor,
		&item.Observation.Room,
		&item.Observation.ServiceState,
		&item.Observation.ImageURL,
		&item.Observation.Status,
		&item.Observation.OccurredAt,
		&item.Observation.CreatedAt,
		&item.Observation.UpdatedAt,

		&item.IncidentID,
		&item.IncidentStatus,
		&item.IncidentConfidence,
		&item.IncidentReportCount,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return ObservationWithIncident{}, ErrNotFound
	}

	if err != nil {
		return ObservationWithIncident{}, fmt.Errorf(
			"get observation with incident: %w",
			err,
		)
	}

	return item, nil
}

// GET REPORTS OF ONE USER
func (r *ObservationRepository) GetByUserID(
	ctx context.Context,
	userID int,
	filter ObservationFilter,
) ([]ObservationWithIncident, error) {
	query := `
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
			o.updated_at,

			i.id,
			i.status,
			i.confidence,

			CASE
				WHEN i.id IS NULL THEN NULL
				ELSE (
					SELECT COUNT(*)::int
					FROM incident_observations support_io
					JOIN observations support_o
						ON support_o.id = support_io.observation_id
					WHERE support_io.incident_id = i.id
					  AND support_io.relation = 'SUPPORT'
					  AND support_o.status <> 'DELETED'
				)
			END AS report_count

		FROM observations o

		LEFT JOIN incident_observations io
			ON io.observation_id = o.id
			AND io.relation = 'SUPPORT'

		LEFT JOIN incidents i
			ON i.id = io.incident_id

		WHERE o.user_id = $1
		  AND o.status <> 'DELETED'
	`

	args := []any{userID}

	add := func(condition string, value any) {
		args = append(args, value)

		query += fmt.Sprintf(
			" AND "+condition,
			len(args),
		)
	}

	if filter.Category != "" {
		add(
			"o.category = $%d",
			filter.Category,
		)
	}

	if filter.Building != "" {
		add(
			"o.building = $%d",
			filter.Building,
		)
	}

	if filter.Room != "" {
		add(
			"o.room = $%d",
			filter.Room,
		)
	}

	if filter.Search != "" {
		args = append(
			args,
			"%"+strings.TrimSpace(filter.Search)+"%",
		)

		index := len(args)

		query += fmt.Sprintf(
			`
			AND (
				o.raw_text ILIKE $%d
				OR o.category ILIKE $%d
				OR o.building ILIKE $%d
				OR COALESCE(o.room, '') ILIKE $%d
			)
		`,
			index,
			index,
			index,
			index,
		)
	}

	query += `
		ORDER BY o.created_at DESC
	`

	rows, err := r.db.Query(
		ctx,
		query,
		args...,
	)
	if err != nil {
		return nil, fmt.Errorf(
			"list observations by user: %w",
			err,
		)
	}
	defer rows.Close()

	items := make([]ObservationWithIncident, 0)

	for rows.Next() {
		var item ObservationWithIncident

		err := rows.Scan(
			&item.Observation.ID,
			&item.Observation.UserID,
			&item.Observation.RawText,
			&item.Observation.Category,
			&item.Observation.Building,
			&item.Observation.Floor,
			&item.Observation.Room,
			&item.Observation.ServiceState,
			&item.Observation.ImageURL,
			&item.Observation.Status,
			&item.Observation.OccurredAt,
			&item.Observation.CreatedAt,
			&item.Observation.UpdatedAt,

			&item.IncidentID,
			&item.IncidentStatus,
			&item.IncidentConfidence,
			&item.IncidentReportCount,
		)
		if err != nil {
			return nil, fmt.Errorf(
				"scan observation by user: %w",
				err,
			)
		}

		items = append(items, item)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf(
			"iterate observations by user: %w",
			err,
		)
	}

	return items, nil
}

// SOFT DELETE
func (r *ObservationRepository) SoftDelete(
	ctx context.Context,
	id int,
	userID int,
) error {
	tag, err := r.db.Exec(
		ctx, `
		UPDATE observations
		SET
			status = 'DELETED',
			updated_at = NOW()
		WHERE id = $1
		  AND user_id = $2
		  AND status <> 'DELETED'
	`,
		id,
		userID,
	)
	if err != nil {
		return fmt.Errorf(
			"soft delete observation: %w",
			err,
		)
	}

	if tag.RowsAffected() == 0 {
		return ErrNotFound
	}

	return nil
}
