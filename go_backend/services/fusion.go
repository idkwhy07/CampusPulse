package services

import (
	"context"
	"fmt"
	"strings"

	"go_backend/models"
	"go_backend/repositories"
)

type FusionResult struct {
	Incident models.Incident
	Matched  bool
}

type FusionService struct {
	incidents *repositories.IncidentRepository
	links     *repositories.IncidentObservationRepository
}

func NewFusionService(
	incidents *repositories.IncidentRepository,
	links *repositories.IncidentObservationRepository,
) *FusionService {
	return &FusionService{
		incidents: incidents,
		links:     links,
	}
}

// AttachObservation gom observation vao incident.
//
// Rule MVP cua CampusPulse:
//
//	cung category
//	cung building
//	cung room
//
// -> cung mot incident neu incident do chua RESOLVED.
func (s *FusionService) AttachObservation(
	ctx context.Context,
	obs models.Observation,
) (FusionResult, error) {
	incident, err := s.incidents.FindOpenByKey(
		ctx,
		obs.Category,
		obs.Building,
		obs.Room,
	)

	matched := err == nil

	if err != nil && err != repositories.ErrNotFound {
		return FusionResult{}, fmt.Errorf(
			"find incident candidate: %w",
			err,
		)
	}

	// Chua co incident phu hop -> tao incident EMERGING.
	if !matched {
		incident = models.Incident{
			Title:      incidentTitle(obs),
			Category:   obs.Category,
			Building:   obs.Building,
			Floor:      obs.Floor,
			Room:       obs.Room,
			Status:     models.IncidentEmerging,
			Severity:   "MEDIUM",
			Confidence: 0,
		}

		if err := s.incidents.Create(
			ctx,
			&incident,
		); err != nil {
			return FusionResult{}, fmt.Errorf(
				"create emerging incident: %w",
				err,
			)
		}
	}

	// Observation nay la evidence SUPPORT cua incident.
	if err := s.links.Link(
		ctx,
		models.IncidentObservation{
			IncidentID:    incident.ID,
			ObservationID: obs.ID,
			Relation:      models.RelationSupport,
			MatchScore:    1.0,
		},
	); err != nil {
		return FusionResult{}, fmt.Errorf(
			"link observation to incident: %w",
			err,
		)
	}

	// Dem so student khac nhau.
	uniqueSupporters, err :=
		s.links.CountUniqueSupporters(
			ctx,
			incident.ID,
		)

	if err != nil {
		return FusionResult{}, fmt.Errorf(
			"count unique supporters: %w",
			err,
		)
	}

	// Tong so report SUPPORT.
	supporters, err :=
		s.links.CountSupporters(
			ctx,
			incident.ID,
		)

	if err != nil {
		return FusionResult{}, fmt.Errorf(
			"count supporters: %w",
			err,
		)
	}

	// Evidence mau thuan.
	contradictions, err :=
		s.links.CountContradictions(
			ctx,
			incident.ID,
		)

	if err != nil {
		return FusionResult{}, fmt.Errorf(
			"count contradictions: %w",
			err,
		)
	}

	confidence := CalculateConfidence(
		uniqueSupporters,
		supporters,
		contradictions,
	)

	if err := s.incidents.UpdateConfidence(
		ctx,
		incident.ID,
		confidence,
	); err != nil {
		return FusionResult{}, fmt.Errorf(
			"update incident confidence: %w",
			err,
		)
	}

	incident.Confidence = confidence

	// Du 4 report SUPPORT -> incident chinh thuc hinh thanh.
	if incident.Status == models.IncidentEmerging &&
		supporters >= IncidentFormationThreshold {

		if err := s.incidents.ConfirmFormation(
			ctx,
			incident.ID,
		); err != nil {
			return FusionResult{}, fmt.Errorf(
				"confirm incident formation: %w",
				err,
			)
		}

		incident.Status = models.IncidentConfirmed
	}

	return FusionResult{
		Incident: incident,
		Matched:  matched,
	}, nil
}

func incidentTitle(obs models.Observation) string {
	room := ""

	if obs.Room != nil &&
		strings.TrimSpace(*obs.Room) != "" {

		room = " phòng " + strings.TrimSpace(*obs.Room)
	}

	return fmt.Sprintf(
		"%s tại %s%s",
		CategoryLabel(obs.Category),
		BuildingLabel(obs.Building),
		room,
	)
}
