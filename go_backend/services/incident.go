package services

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"go_backend/models"
	"go_backend/repositories"

	"github.com/jackc/pgx/v5/pgxpool"
)

type IncidentView struct {
	IncidentID     int          `json:"incident_id"`
	Title          string       `json:"title"`
	Category       string       `json:"category"`
	Location       string       `json:"location"`
	Room           string       `json:"room"`
	ReportCount    int          `json:"report_count"`
	UniqueSupport  int          `json:"unique_supporters"`
	Status         string       `json:"status"`
	Confidence     int          `json:"confidence"`
	EmergedAt      string       `json:"emerged_at"`
	FirstReportAt  string       `json:"first_report_at"`
	LatestReportAt string       `json:"latest_report_at"`
	Reports        []ReportView `json:"reports,omitempty"`
}

type IncidentService struct {
	incidents *repositories.IncidentRepository
	links     *repositories.IncidentObservationRepository
}

func NewIncidentService(
	pool *pgxpool.Pool,
) *IncidentService {
	return &IncidentService{
		incidents:
			repositories.NewIncidentRepository(pool),

		links:
			repositories.NewIncidentObservationRepository(pool),
	}
}

func (s *IncidentService) List(
	ctx context.Context,
	filter repositories.IncidentFilter,
) ([]IncidentView, error) {
	items, err := s.incidents.GetAll(
		ctx,
		filter,
		IncidentFormationThreshold,
	)

	if err != nil {
		return nil, err
	}

	result := make(
		[]IncidentView,
		0,
		len(items),
	)

	for _, item := range items {
		result = append(
			result,
			incidentView(item, nil),
		)
	}

	return result, nil
}

func (s *IncidentService) Get(
	ctx context.Context,
	id int,
) (IncidentView, error) {
	item, err :=
		s.incidents.GetByID(
			ctx,
			id,
		)

	if errors.Is(
		err,
		repositories.ErrNotFound,
	) {
		return IncidentView{}, ErrNotFound
	}

	if err != nil {
		return IncidentView{}, err
	}

	// Incident chua du 4 reports
	// thi admin cung khong duoc thay.
	if item.ReportCount <
		IncidentFormationThreshold {

		return IncidentView{}, ErrNotFound
	}

	observations, err :=
		s.links.GetObservationsByIncidentID(
			ctx,
			id,
		)

	if err != nil {
		return IncidentView{}, err
	}

	reports := make(
		[]ReportView,
		0,
		len(observations),
	)

	for _, obs := range observations {
		reports = append(
			reports,
			plainReportView(obs),
		)
	}

	return incidentView(
		item,
		reports,
	), nil
}

func (s *IncidentService) Evidence(
	ctx context.Context,
	id int,
) ([]ReportView, error) {
	item, err :=
		s.incidents.GetByID(
			ctx,
			id,
		)

	if errors.Is(
		err,
		repositories.ErrNotFound,
	) ||
		(err == nil &&
			item.ReportCount <
				IncidentFormationThreshold) {

		return nil, ErrNotFound
	}

	if err != nil {
		return nil, err
	}

	observations, err :=
		s.links.GetObservationsByIncidentID(
			ctx,
			id,
		)

	if err != nil {
		return nil, err
	}

	reports := make(
		[]ReportView,
		0,
		len(observations),
	)

	for _, obs := range observations {
		reports = append(
			reports,
			plainReportView(obs),
		)
	}

	return reports, nil
}

func (s *IncidentService) UpdateStatus(
	ctx context.Context,
	id int,
	requested string,
) (IncidentView, error) {
	status, ok :=
		InternalStatus(requested)

	if !ok ||
		status == models.IncidentEmerging {

		return IncidentView{},
			ErrInvalidStatus
	}

	item, err :=
		s.incidents.GetByID(
			ctx,
			id,
		)

	if errors.Is(
		err,
		repositories.ErrNotFound,
	) ||
		(err == nil &&
			item.ReportCount <
				IncidentFormationThreshold) {

		return IncidentView{},
			ErrNotFound
	}

	if err != nil {
		return IncidentView{}, err
	}

	err = s.incidents.UpdateStatus(
		ctx,
		id,
		status,
	)

	if errors.Is(
		err,
		repositories.ErrNotFound,
	) {
		return IncidentView{},
			ErrNotFound
	}

	if err != nil {
		return IncidentView{}, err
	}

	return s.Get(
		ctx,
		id,
	)
}

func incidentView(
	item repositories.IncidentSummary,
	reports []ReportView,
) IncidentView {
	room := ""

	if item.Incident.Room != nil {
		room = *item.Incident.Room
	}

	format := func(
		value *time.Time,
	) string {
		if value == nil {
			return ""
		}

		return value.Format(
			"02/01/2006 15:04:05",
		)
	}

	emerged :=
		item.Incident.CreatedAt.Format(
			"02/01/2006 15:04:05",
		)

	if item.LatestReportAt != nil &&
		item.ReportCount >=
			IncidentFormationThreshold {

		emerged =
			format(item.LatestReportAt)
	}

	return IncidentView{
		IncidentID:
		item.Incident.ID,

		Title:
		item.Incident.Title,

		Category:
		CategoryLabel(
			item.Incident.Category,
		),

		Location:
		BuildingLabel(
			item.Incident.Building,
		),

		Room:
		room,

		ReportCount:
		item.ReportCount,

		UniqueSupport:
		item.UniqueSupport,

		Status:
		UIStatus(
			item.Incident.Status,
		),

		Confidence:
		item.Incident.Confidence,

		EmergedAt:
		emerged,

		FirstReportAt:
		format(item.FirstReportAt),

		LatestReportAt:
		format(item.LatestReportAt),

		Reports:
		reports,
	}
}

func plainReportView(
	obs models.Observation,
) ReportView {
	room := ""

	if obs.Room != nil {
		room = *obs.Room
	}

	return ReportView{
		ID: obs.ID,

		Category:
		CategoryLabel(
			obs.Category,
		),

		Location:
		BuildingLabel(
			obs.Building,
		),

		Room:
		room,

		Description:
		obs.RawText,

		CreatedAt:
		obs.CreatedAt,

		CreatedText:
		obs.CreatedAt.Format(
			"02/01/2006 15:04:05",
		),
	}
}

func BuildIncidentFilter(
	status string,
	category string,
	building string,
	room string,
	search string,
) (
	repositories.IncidentFilter,
	error,
) {
	filter :=
		repositories.IncidentFilter{
			Room:
			strings.TrimSpace(room),

			Search:
			strings.TrimSpace(search),
		}

	if strings.TrimSpace(status) != "" {
		internal, ok :=
			InternalStatus(status)

		if !ok ||
			internal ==
				models.IncidentEmerging {

			return filter,
				fmt.Errorf(
					"%w: invalid status filter",
					ErrInvalidInput,
				)
		}

		filter.Status = internal
	}

	if strings.TrimSpace(category) != "" {
		code, ok :=
			CategoryCode(category)

		if !ok {
			return filter,
				fmt.Errorf(
					"%w: invalid category filter",
					ErrInvalidInput,
				)
		}

		filter.Category = code
	}

	if strings.TrimSpace(building) != "" {
		code, ok :=
			BuildingCode(building)

		if !ok {
			return filter,
				fmt.Errorf(
					"%w: invalid building filter",
					ErrInvalidInput,
				)
		}

		filter.Building = code
	}

	return filter, nil
}
