import csv
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from schemas import Report
from query import normalize


class ReportSource(Protocol):
    def load_reports(self) -> list[Report]: ...


class FileReportSource:
    """Đọc JSON cũ hoặc CSV xuất từ CampusPulse, kiểm tra trước khi đồng bộ."""

    def __init__(self, path: Path):
        self.path = path

    def load_reports(self):
        if self.path.stat().st_size > 5_000_000:
            raise ValueError("Bản MVP nhận file tối đa 5 MB")
        if self.path.suffix.lower() == ".csv":
            payload = self._load_csv()
        elif self.path.suffix.lower() == ".json":
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        else:
            raise ValueError("Chỉ hỗ trợ file .csv hoặc .json")
        if not isinstance(payload, list) or len(payload) > 5000:
            raise ValueError("File cần chứa tối đa 5000 phản ánh")
        reports = [Report.model_validate(item) for item in payload]
        ids = [r.report_id for r in reports]
        if len(ids) != len(set(ids)):
            raise ValueError("Trùng report_id")
        statuses = {}
        for report in reports:
            if report.incident_id is not None:
                key = report.incident_id
                if key in statuses and statuses[key] != report.incident_status:
                    raise ValueError(f"Trạng thái sự cố #{key} không nhất quán")
                statuses[key] = report.incident_status
        return [r for r in reports if r.report_status == "ACTIVE"]



    def _load_csv(self):
        with self.path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)):
                raise ValueError("CSV có tên cột trùng")
            required = {"report_id", "category", "building", "room", "description",
                        "incident_id", "incident_status", "created_at"}
            if not required.issubset(headers):
                raise ValueError("CSV thiếu cột: " + ", ".join(sorted(required - set(headers))))
            legacy = headers == ["report_id", "category", "building", "room", "description",
                                 "incident_id", "incident_status", "confidence", "created_at"]
            result = []
            repaired = False
            for row in reader:
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Số ô không khớp tiêu đề CSV")
                    timestamp = row["created_at"].strip()
                    # Mẫu Tuấn gửi bị đặt sai hai tiêu đề cuối. Chỉ sửa khi cả
                    # cấu trúc header và dữ liệu nhận diện đúng mẫu đã biết.
                    if legacy and timestamp.startswith("Report #"):
                        timestamp = row["confidence"].strip()
                        repaired = True
                    created = datetime.fromisoformat(timestamp)
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone(timedelta(hours=7)))
                    description = row["description"].strip()
                    label = normalize(row["category"].strip())
                    category = {
                        "mang / duong truyen": "NETWORK",
                        "co so vat chat": "FACILITY",
                        "dien / chieu sang": "ELECTRICAL",
                        "ve sinh / moi truong": "SANITATION",
                        "an ninh / an toan": "SECURITY",
                        "dich vu sinh vien": "STUDENT_SERVICE",
                    }.get(label, row["category"].strip().upper())
                    # Giữ khả năng truy vấn các loại thiết bị của schema cũ.
                    if category == "FACILITY":
                        text = normalize(description)
                        if re.search(r"\b(may chieu|hdmi|trinh chieu|no signal)\b", text):
                            category = "PROJECTOR"
                        elif "thang may" in text:
                            category = "ELEVATOR"
                    building = re.sub(r"^(?:toa nha|toa)\s+", "", normalize(row["building"].strip())).upper()
                    report = dict(
                        report_id=int(row["report_id"]),
                        incident_id=int(row["incident_id"]) if row["incident_id"].strip() else None,
                        raw_text=description, category=category, building=building,
                        room=row["room"].strip() or None,
                        floor=row.get("floor", "").strip() or None,
                        report_status=row.get("report_status", "ACTIVE").strip().upper() or "ACTIVE",
                        incident_status=row["incident_status"].strip().upper() or None,
                        created_at=created,
                    )
                    Report.model_validate(report)
                    result.append(report)
                    if len(result) > 5000:
                        raise ValueError("File vượt quá 5000 phản ánh")
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"CSV dòng {reader.line_num}: dữ liệu không hợp lệ ({exc})") from exc
            if repaired:
                logging.getLogger(__name__).warning(
                    "CSV mẫu sai header: dùng cột confidence làm created_at; "
                    "cột created_at cũ là văn bản tổng hợp. Nên sửa header thành created_at,content.")
            return result
