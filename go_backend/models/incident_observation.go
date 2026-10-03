package models

import "time"

const (
	RelationSupport    = "SUPPORT"
	RelationContradict = "CONTRADICT"
	RelationUnknown    = "UNKNOWN"
)

type IncidentObservation struct {
	IncidentID    int       `json:"incident_id"`
	ObservationID int       `json:"observation_id"`
	Relation      string    `json:"relation"`
	MatchScore    float64   `json:"match_score"`
	CreatedAt     time.Time `json:"created_at"`
}
