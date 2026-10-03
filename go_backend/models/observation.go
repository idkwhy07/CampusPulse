package models

import "time"

const (
	ObservationActive  = "ACTIVE"
	ObservationDeleted = "DELETED"
)

type Observation struct {
	ID           int        `json:"id"`
	UserID       int        `json:"user_id"`
	RawText      string     `json:"text"`
	Category     string     `json:"category"`
	Building     string     `json:"building"`
	Floor        *string    `json:"floor,omitempty"`
	Room         *string    `json:"room,omitempty"`
	ServiceState string     `json:"service_state"`
	Status       string     `json:"status"`
	OccurredAt   *time.Time `json:"occurred_at,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}
