package services

import "testing"

func TestCalculateConfidence(t *testing.T) {
	tests := []struct {
		name           string
		unique         int
		supporters     int
		contradictions int
		expected       int
	}{
		{
			name:           "one unique supporter",
			unique:         1,
			supporters:     1,
			contradictions: 0,
			expected:       28,
		},
		{
			name:           "two unique supporters",
			unique:         2,
			supporters:     2,
			contradictions: 0,
			expected:       50,
		},
		{
			name:           "three unique supporters",
			unique:         3,
			supporters:     3,
			contradictions: 0,
			expected:       72,
		},
		{
			name:           "four unique supporters",
			unique:         4,
			supporters:     4,
			contradictions: 0,
			expected:       88,
		},
		{
			name:           "duplicate supporter",
			unique:         2,
			supporters:     3,
			contradictions: 0,
			expected:       52,
		},
		{
			name:           "contradiction lowers confidence",
			unique:         4,
			supporters:     4,
			contradictions: 1,
			expected:       76,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := CalculateConfidence(
				tt.unique,
				tt.supporters,
				tt.contradictions,
			)

			if got != tt.expected {
				t.Fatalf(
					"CalculateConfidence() = %d, want %d",
					got,
					tt.expected,
				)
			}
		})
	}
}
