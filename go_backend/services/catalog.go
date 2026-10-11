package services

import (
	"fmt"
	"strings"
)

const IncidentFormationThreshold = 4

var categoryLabelToCode = map[string]string{
	"Mạng / Đường truyền":  "NETWORK",
	"Cơ sở vật chất":       "FACILITY",
	"Điện / Chiếu sáng":    "ELECTRICAL",
	"Vệ sinh / Môi trường": "CLEANLINESS",
	"An ninh / An toàn":    "SAFETY",
	"Dịch vụ sinh viên":    "STUDENT_SERVICE",
	"Khác":                 "OTHER",
}

var categoryCodeToLabel = map[string]string{
	"NETWORK":         "Mạng / Đường truyền",
	"FACILITY":        "Cơ sở vật chất",
	"PROJECTOR":       "Cơ sở vật chất",
	"ELEVATOR":        "Cơ sở vật chất",
	"ELECTRICAL":      "Điện / Chiếu sáng",
	"CLEANLINESS":     "Vệ sinh / Môi trường",
	"SAFETY":          "An ninh / An toàn",
	"STUDENT_SERVICE": "Dịch vụ sinh viên",
	"OTHER":           "Khác",
}

var buildingLabelToCode = map[string]string{
	"Tòa nhà H1": "H1",
	"Tòa nhà H2": "H2",
	"Tòa nhà H3": "H3",
	"Tòa nhà A1": "A1",
}

var buildingCodeToLabel = map[string]string{
	"H1": "Tòa nhà H1",
	"H2": "Tòa nhà H2",
	"H3": "Tòa nhà H3",
	"A1": "Tòa nhà A1",
}

func CategoryCode(labelOrCode string) (string, bool) {
	value := strings.TrimSpace(labelOrCode)

	if code, ok := categoryLabelToCode[value]; ok {
		return code, true
	}

	upper := strings.ToUpper(value)
	_, ok := categoryCodeToLabel[upper]

	return upper, ok
}

func CategoryLabel(code string) string {
	code = strings.ToUpper(strings.TrimSpace(code))

	if label, ok := categoryCodeToLabel[code]; ok {
		return label
	}

	return "Khác"
}

func BuildingCode(labelOrCode string) (string, bool) {
	value := strings.TrimSpace(labelOrCode)

	if code, ok := buildingLabelToCode[value]; ok {
		return code, true
	}

	upper := strings.ToUpper(value)
	_, ok := buildingCodeToLabel[upper]

	return upper, ok
}

func BuildingLabel(code string) string {
	code = strings.ToUpper(strings.TrimSpace(code))

	if label, ok := buildingCodeToLabel[code]; ok {
		return label
	}

	return code
}

func IsValidRoom(room string) bool {
	room = strings.TrimSpace(room)

	if len(room) != 2 {
		return false
	}

	return room >= "10" && room <= "50"
}

func UIStatus(internal string) string {
	switch strings.ToUpper(strings.TrimSpace(internal)) {
	case "CONFIRMED":
		return "Chưa xử lý"

	case "IN_PROGRESS":
		return "Đang xử lý"

	case "RESOLVED":
		return "Đã xử lý"

	default:
		return ""
	}
}

func InternalStatus(labelOrCode string) (string, bool) {
	value := strings.TrimSpace(labelOrCode)

	switch value {
	case "Chưa xử lý":
		return "CONFIRMED", true

	case "Đang xử lý":
		return "IN_PROGRESS", true

	case "Đã xử lý":
		return "RESOLVED", true
	}

	upper := strings.ToUpper(value)

	switch upper {
	case "EMERGING",
		"CONFIRMED",
		"IN_PROGRESS",
		"RESOLVED":

		return upper, true

	default:
		return "", false
	}
}

func Categories() []string {
	return []string{
		"Mạng / Đường truyền",
		"Cơ sở vật chất",
		"Điện / Chiếu sáng",
		"Vệ sinh / Môi trường",
		"An ninh / An toàn",
		"Dịch vụ sinh viên",
		"Khác",
	}
}

func Locations() []string {
	return []string{
		"Tòa nhà H1",
		"Tòa nhà H2",
		"Tòa nhà H3",
		"Tòa nhà A1",
	}
}

func RoomsByLocation() map[string][]string {
	result := make(map[string][]string)

	for _, location := range Locations() {
		rooms := make([]string, 0, 41)

		for room := 10; room <= 50; room++ {
			rooms = append(
				rooms,
				fmt.Sprintf("%02d", room),
			)
		}

		result[location] = rooms
	}

	return result
}
