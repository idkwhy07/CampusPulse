"""Bộ hiểu câu hỏi có giới hạn, chạy không cần LLM; luôn hỏi lại khi mơ hồ."""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
CATEGORIES = {
    "NETWORK": ("wifi", "wi fi", "wi-fi", "mang", "internet", "ket noi"),
    "ELEVATOR": ("thang may",),
    "PROJECTOR": ("may chieu", "hdmi"),
    "FACILITY": ("dieu hoa", "co so vat chat"),
    "ELECTRICAL": ("dien", "chieu sang", "den", "bong den"),
    "SANITATION": ("ve sinh", "moi truong", "rac", "mui la"),
    "SECURITY": ("an ninh", "an toan", "mat do", "trom cap"),
    "STUDENT_SERVICE": ("dich vu sinh vien", "hoc phi"),
}


def normalize(text):
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def contains(text, phrase):
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


@dataclass
class Query:
    kind: str = "search"
    entity: str = "report"
    report_id: int | None = None
    incident_id: int | None = None
    building: str | None = None
    floor: str | None = None
    room: str | None = None
    category: str | None = None
    statuses: set[str] = field(default_factory=set)
    day: date | None = None
    group_by: str | None = None
    clarification: str | None = None
    buildings: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    start_day: date | None = None
    end_day: date | None = None
    search_text: str | None = None
    content_filter: str | None = None

    def accepts(self, report):
        return (
            (self.report_id is None or report.report_id == self.report_id)
            and (self.incident_id is None or report.incident_id == self.incident_id)
            and (not self.building or report.building == self.building)
            and (not self.floor or report.floor == self.floor)
            and (not self.room or report.room == self.room)
            and (not self.category or report.category == self.category or
                 (self.category == "FACILITY" and report.category in {"PROJECTOR", "ELEVATOR"}))
            and (not self.statuses or report.incident_status in self.statuses)
            and (not self.day or report.created_at.astimezone(VN).date() == self.day)
            and (not self.buildings or report.building in self.buildings)
            and (not self.categories or report.category in self.categories or
                 ("FACILITY" in self.categories and report.category in {"PROJECTOR", "ELEVATOR"}))
            and (not self.start_day or report.created_at.astimezone(VN).date() >= self.start_day)
            and (not self.end_day or report.created_at.astimezone(VN).date() <= self.end_day)
        )


def parse_query(question, today=None):
    text = normalize(question)
    text = re.sub(r"\bj\b", "gi", text)
    q = Query(entity="incident" if "su co" in text and "phan anh" not in text else "report")
    if any(x in text for x in ("cap nhat", "doi trang thai", "xoa phan anh", "phan cong")):
        q.clarification = "Chatbot chỉ đọc dữ liệu. Hãy dùng trang quản lý sự cố để cập nhật."
        return q
    buildings = set(re.findall(r"\b[a-z]\d+\b", text))
    if len(buildings) > 1:
        q.clarification = "Bản này lọc một tòa mỗi lần. Bạn muốn xem tòa nào?"
    q.building = next(iter(buildings)).upper() if len(buildings) == 1 else None
    for field_name, pattern in (("floor", r"tang\s+(\d+)"), ("room", r"phong\s+(\d+)")):
        matches = set(re.findall(pattern, text))
        if len(matches) > 1:
            q.clarification = "Hãy chọn một tầng/phòng mỗi lần."
        if matches:
            setattr(q, field_name, sorted(matches)[0])
    for field_name, pattern in (
        ("report_id", r"(?:phan anh|report|pa)\s*(?:so|ma)?\s*#?\s*(\d+)\b"),
        ("incident_id", r"(?:su co|incident)\s*(?:so|ma)?\s*#?\s*(\d+)\b"),
    ):
        found = re.findall(pattern, text)
        if len(set(found)) > 1:
            q.clarification = "Hãy tra cứu một mã mỗi lần."
        if found:
            setattr(q, field_name, int(found[0]))
            q.kind = "lookup"
    if q.kind != "lookup" and re.fullmatch(r"\s*#\d+\s*", text):
        q.report_id, q.kind = int(text.strip()[1:]), "lookup"
    cats = [key for key, aliases in CATEGORIES.items()
            if contains(text, key.lower()) or any(contains(text, a) for a in aliases)]
    if contains(text, "other"):
        cats.append("OTHER")
    if len(cats) > 1:
        q.clarification = "Hãy chọn một loại vấn đề mỗi lần (mạng, máy chiếu, thang máy, điều hòa)."
    if cats:
        q.category = cats[0]
    if "chua xu ly" in text or "chua giai quyet" in text:
        q.statuses = {"EMERGING", "CONFIRMED", "IN_PROGRESS"}
    else:
        for key, phrases in {
            "IN_PROGRESS": ("dang xu ly", "in_progress"),
            "RESOLVED": ("da xu ly", "da giai quyet", "resolved"),
            "CONFIRMED": ("da xac nhan", "confirmed"),
            "EMERGING": ("moi phat sinh", "emerging"),
        }.items():
            if any(contains(text, phrase) for phrase in phrases):
                q.statuses.add(key)
    today = today or datetime.now(VN).date()
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b", text)
    if any(x in text for x in ("tuan", "thang nay", "thang truoc", "tu ngay", "den ngay")) or len(dates) > 1:
        q.clarification = "Bản này lọc theo một ngày gửi. Hãy nhập ngày dạng 02/10/2026."
    elif dates:
        try:
            q.day = datetime.strptime(dates[0], "%Y-%m-%d" if "-" in dates[0] else "%d/%m/%Y").date()
        except ValueError:
            q.clarification = "Ngày không hợp lệ. Hãy dùng DD/MM/YYYY hoặc YYYY-MM-DD."
    elif "hom nay" in text:
        q.day = today
    elif "hom qua" in text:
        q.day = today - timedelta(days=1)
    if any(x in text for x in ("bao nhieu", "thong ke", "dem ", "so luong", "tong so")) or re.search(r"nhieu\b.*\bnhat", text):
        q.kind = "count"
        if re.search(r"(?:bao nhieu|so luong|dem)\s+(?:sinh vien|nguoi)", text):
            q.clarification = "Dữ liệu chatbot không chứa định danh người gửi nên chưa đếm được số sinh viên khác nhau. Có thể đếm số phản ánh hoặc số sự cố."
        if any(x in text for x in ("toa nao", "theo toa", "khu nao")):
            q.group_by = "building"
        elif "theo loai" in text:
            q.group_by = "category"
        elif "theo trang thai" in text:
            q.group_by = "incident_status"
    elif "tom tat" in text or "tong hop" in text:
        q.kind = "summary"
    elif q.kind != "lookup" and (any(x in text for x in ("liet ke", "danh sach")) or
                                 re.search(r"(?:co nhung|co cac|phan anh (?:gi|nao))", text)):
        q.kind = "list"
    if q.kind in {"count", "summary", "list"} and contains(text, "dieu hoa"):
        q.clarification = "Hãy bật AI để lọc nội dung điều hòa trong nhóm cơ sở vật chất."
    if q.kind in {"count", "summary", "list"}:
        # Không đếm một điều kiện nội dung chưa được bộ lọc cấu trúc hiểu.
        residue = text
        for aliases in CATEGORIES.values():
            for alias in sorted(aliases, key=len, reverse=True):
                residue = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", " ", residue)
        residue = re.sub(r"\b[a-z]\d+\b|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d+", " ", residue)
        allowed = set(normalize("co bao nhieu phan anh report reports su co incident incidents thong ke dem so luong tong tat ca toan bo du lieu tom tat hop ve tai o toa nha khu nao nhieu nhat theo loai trang thai chua da dang xu ly giai quyet xac nhan moi phat sinh hom nay qua ngay tang phong so ma la va cac cua sinh vien network elevator projector facility other emerging confirmed in_progress resolved").split())
        allowed.update("liet ke danh sach nhung gi xem cho toi minh electrical sanitation security student_service".split())
        unknown = [word for word in re.findall(r"\w+", residue) if word not in allowed]
        if unknown:
            q.clarification = "Mình chưa hiểu đầy đủ điều kiện thống kê/tóm tắt. Hãy dùng loại vấn đề, tòa H1/H2/H3, tầng, phòng, trạng thái hoặc một ngày cụ thể."
    return q
