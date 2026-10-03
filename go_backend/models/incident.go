package models

import "time"

const (
	IncidentEmerging   = "EMERGING"
	IncidentConfirmed  = "CONFIRMED"
	IncidentInProgress = "IN_PROGRESS"
	IncidentResolved   = "RESOLVED"
)

type Incident struct {
	ID           int        `json:"id"`
	Title        string     `json:"title"`
	Category     string     `json:"category"`
	Building     string     `json:"building"`
	Floor        *string    `json:"floor,omitempty"`
	Room         *string    `json:"room,omitempty"`
	Status       string     `json:"status"`
	Severity     string     `json:"severity"`
	Confidence   int        `json:"confidence"`
	AssignedTeam *string    `json:"assigned_team,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
	ResolvedAt   *time.Time `json:"resolved_at,omitempty"`
}
