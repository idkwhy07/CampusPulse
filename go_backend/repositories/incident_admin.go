package repositories

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"go_backend/models"

	"github.com/jackc/pgx/v5"
)

type IncidentFilter struct {
	Status   string
	Category string
	Building string
	Room     string
	Search   string
}

type IncidentSummary struct {
	Incident       models.Incident
	ReportCount    int
	UniqueSupport  int
	FirstReportAt  *time.Time
	LatestReportAt *time.Time
}

func (r *IncidentRepository) GetByID(
	ctx context.Context,
	id int,
) (IncidentSummary, error) {
	var item IncidentSummary

	err := r.db.QueryRow(ctx, `
		SELECT
			i.id,
			i.title,
			i.category,
			i.building,
			i.floor,
			i.room,
			i.status,
			i.severity,
			i.confidence,
			i.assigned_team,
			i.created_at,
			i.updated_at,
			i.resolved_at,

			COUNT(o.id) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			COUNT(DISTINCT o.user_id) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			MIN(o.created_at) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			MAX(o.created_at) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			)

		FROM incidents i

		LEFT JOIN incident_observations io
			ON io.incident_id = i.id

		LEFT JOIN observations o
			ON o.id = io.observation_id

		WHERE i.id = $1

		GROUP BY i.id
	`, id).Scan(
		&item.Incident.ID,
		&item.Incident.Title,
		&item.Incident.Category,
		&item.Incident.Building,
		&item.Incident.Floor,
		&item.Incident.Room,
		&item.Incident.Status,
		&item.Incident.Severity,
		&item.Incident.Confidence,
		&item.Incident.AssignedTeam,
		&item.Incident.CreatedAt,
		&item.Incident.UpdatedAt,
		&item.Incident.ResolvedAt,
		&item.ReportCount,
		&item.UniqueSupport,
		&item.FirstReportAt,
		&item.LatestReportAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return IncidentSummary{}, ErrNotFound
	}

	if err != nil {
		return IncidentSummary{}, fmt.Errorf(
			"get incident: %w",
			err,
		)
	}

	return item, nil
}

func (r *IncidentRepository) GetAll(
	ctx context.Context,
	filter IncidentFilter,
	minReportCount int,
) ([]IncidentSummary, error) {
	query := `
		SELECT
			i.id,
			i.title,
			i.category,
			i.building,
			i.floor,
			i.room,
			i.status,
			i.severity,
			i.confidence,
			i.assigned_team,
			i.created_at,
			i.updated_at,
			i.resolved_at,

			COUNT(o.id) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			COUNT(DISTINCT o.user_id) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			MIN(o.created_at) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			),

			MAX(o.created_at) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			)

		FROM incidents i

		LEFT JOIN incident_observations io
			ON io.incident_id = i.id

		LEFT JOIN observations o
			ON o.id = io.observation_id

		WHERE 1 = 1
	`

	args := make([]any, 0)

	add := func(condition string, value any) {
		args = append(args, value)

		query += fmt.Sprintf(
			" AND "+condition,
			len(args),
		)
	}

	if filter.Status != "" {
		add("i.status = $%d", filter.Status)
	}

	if filter.Category != "" {
		add("i.category = $%d", filter.Category)
	}

	if filter.Building != "" {
		add("i.building = $%d", filter.Building)
	}

	if filter.Room != "" {
		add("i.room = $%d", filter.Room)
	}

	if filter.Search != "" {
		args = append(
			args,
			"%"+strings.TrimSpace(filter.Search)+"%",
		)

		p := len(args)

		query += fmt.Sprintf(`
			AND (
				i.title ILIKE $%d
				OR i.category ILIKE $%d
				OR i.building ILIKE $%d
				OR COALESCE(i.room, '') ILIKE $%d
				OR EXISTS (
					SELECT 1
					FROM incident_observations sx

					JOIN observations so
						ON so.id = sx.observation_id

					WHERE sx.incident_id = i.id
					  AND so.status <> 'DELETED'
					  AND so.raw_text ILIKE $%d
				)
			)
		`,
			p,
			p,
			p,
			p,
			p,
		)
	}

	query += ` GROUP BY i.id`

	if minReportCount > 0 {
		args = append(
			args,
			minReportCount,
		)

		query += fmt.Sprintf(`
			HAVING COUNT(o.id) FILTER (
				WHERE o.status <> 'DELETED'
				  AND io.relation = 'SUPPORT'
			) >= $%d
		`, len(args))
	}

	query += `
		ORDER BY COALESCE(
			MAX(o.created_at),
			i.created_at
		) DESC
	`

	rows, err := r.db.Query(
		ctx,
		query,
		args...,
	)

	if err != nil {
		return nil, fmt.Errorf(
			"list incidents: %w",
			err,
		)
	}
	defer rows.Close()

	items := make(
		[]IncidentSummary,
		0,
	)

	for rows.Next() {
		var item IncidentSummary

		err := rows.Scan(
			&item.Incident.ID,
			&item.Incident.Title,
			&item.Incident.Category,
			&item.Incident.Building,
			&item.Incident.Floor,
			&item.Incident.Room,
			&item.Incident.Status,
			&item.Incident.Severity,
			&item.Incident.Confidence,
			&item.Incident.AssignedTeam,
			&item.Incident.CreatedAt,
			&item.Incident.UpdatedAt,
			&item.Incident.ResolvedAt,
			&item.ReportCount,
			&item.UniqueSupport,
			&item.FirstReportAt,
			&item.LatestReportAt,
		)

		if err != nil {
			return nil, fmt.Errorf(
				"scan incident: %w",
				err,
			)
		}

		items = append(
			items,
			item,
		)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf(
			"iterate incidents: %w",
			err,
		)
	}

	return items, nil
}

func (r *IncidentRepository) UpdateStatus(
	ctx context.Context,
	id int,
	status string,
) error {
	var rowsAffected int64

	if status == models.IncidentResolved {
		tag, err := r.db.Exec(ctx, `
			UPDATE incidents
			SET
				status = $2,
				updated_at = NOW(),
				resolved_at = NOW()
			WHERE id = $1
		`, id, status)

		if err != nil {
			return fmt.Errorf(
				"update incident status: %w",
				err,
			)
		}

		rowsAffected = tag.RowsAffected()
	} else {
		tag, err := r.db.Exec(ctx, `
			UPDATE incidents
			SET
				status = $2,
				updated_at = NOW(),
				resolved_at = NULL
			WHERE id = $1
		`, id, status)

		if err != nil {
			return fmt.Errorf(
				"update incident status: %w",
				err,
			)
		}

		rowsAffected = tag.RowsAffected()
	}

	if rowsAffected == 0 {
		return ErrNotFound
	}

	return nil
}
