import json
from pathlib import Path
from typing import Protocol

from schemas import Report


class ReportSource(Protocol):
    def load_reports(self) -> list[Report]: ...


class FileReportSource:
    """Đổi lớp này khi nhóm cung cấp CSV/Word/API; RAG không cần sửa."""

    def __init__(self, path: Path):
        self.path = path

    def load_reports(self):
        if self.path.stat().st_size > 5_000_000:
            raise ValueError("Bản MVP nhận file tối đa 5 MB")
        payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or len(payload) > 5000:
            raise ValueError("File cần là mảng JSON tối đa 5000 phản ánh")
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


