package services

func CalculateConfidence(
	uniqueSupporters int,
	supporters int,
	contradictions int,
) int {
	confidence := 20

	switch {
	case uniqueSupporters >= 4:
		confidence = 88

	case uniqueSupporters == 3:
		confidence = 72

	case uniqueSupporters == 2:
		confidence = 50

	case uniqueSupporters == 1:
		confidence = 28

	default:
		confidence = 0
	}

	// Neu mot student gui nhieu report cung incident,
	// confidence chi tang nhe.
	if supporters > uniqueSupporters {
		extra := supporters - uniqueSupporters

		if extra > 3 {
			extra = 3
		}

		confidence += extra * 2
	}

	// Contradiction lam giam do tin cay.
	confidence -= contradictions * 12

	if confidence < 0 {
		return 0
	}

	if confidence > 100 {
		return 100
	}

	return confidence
}
