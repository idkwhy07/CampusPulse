import logging
import re
import threading
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from datetime import date

from index import SearchIndex
from providers import NO_EVIDENCE, get_provider
from ai_errors import explain_ai_error
from query import VN, parse_query
from planner import respect_explicit_request

logger = logging.getLogger(__name__)


class AIUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Snapshot:
    reports: tuple
    index: SearchIndex
    synced_at: str
    retrieval_mode: str
    warning: str | None = None


class Chatbot:
    def __init__(self, settings, source, provider=None):
        self.settings, self.source = settings, source
        self.provider = provider or get_provider(settings)
        self.snapshot = None
        self.sync_lock = threading.Lock()
        # Cache embedding trong RAM: hash(chunk_text) → vector.
        # Tồn tại suốt vòng đời tiến trình; không persist khi khởi động lại.
        self.embed_cache: dict = {}

    def sync(self):
        # Chỉ thay snapshot sau khi đọc/kiểm tra/xây index thành công.
        with self.sync_lock:
            reports = tuple(self.source.load_reports())
            mode, warning = "lexical", None
            if self.provider:
                try:
                    index = SearchIndex(reports, self.provider, embed_cache=self.embed_cache)
                    mode = "semantic"
                except Exception:
                    if self.settings.ai_required:
                        raise AIUnavailable("Không tạo được embedding. Kiểm tra cấu hình AI (Gemini API key) và EMBED_MODEL; AI_REQUIRED không cho phép chuyển sang từ khóa.")
                    logger.warning("Không tạo được embedding; dùng tìm kiếm từ khóa.")
                    index = SearchIndex(reports)
                    warning = "Embedding chưa sẵn sàng; đang dùng tìm kiếm từ khóa."
            else:
                index = SearchIndex(reports)
            self.snapshot = Snapshot(reports, index, datetime.now(timezone.utc).isoformat(), mode, warning)
        return self.status()

    def status(self):
        s = self.snapshot
        return {
            "ready": s is not None, "data_mode": self.settings.data_mode,
            "ai_mode": self.settings.ai_mode,
            "understanding_mode": "llm" if self.provider else "rules",
            "chat_model": self.settings.chat_model if self.provider else None,
            "ai_required": self.settings.ai_required,
            "retrieval_mode": s.retrieval_mode if s else None,
            "report_count": len(s.reports) if s else 0,
            "synced_at": s.synced_at if s else None,
            "warning": s.warning if s else None,
        }

    def chat(self, question, top_k=5):
        s = self.snapshot  # Một câu hỏi sử dụng cùng một phiên bản dữ liệu.
        if s is None:
            raise RuntimeError("Chưa nạp dữ liệu")
        understanding_mode, planner_warning = "rules", None
        if self.provider:
            try:
                q = respect_explicit_request(question, self.provider.plan(question))
                understanding_mode = "llm"
            except Exception:
                if self.settings.ai_required:
                    raise AIUnavailable("LLM chưa hiểu được câu hỏi hoặc không kết nối được. Kiểm tra cấu hình AI (CHAT_MODEL / DeepSeek API key) rồi thử lại.")
                q = parse_query(question)
                planner_warning = "LLM hiểu câu hỏi chưa sẵn sàng; đang dùng bộ quy tắc giới hạn."
        else:
            q = parse_query(question)
        result = {
            "answer": "", "sources": [], "intent": q.kind,
            "data_mode": self.settings.data_mode, "synced_at": s.synced_at,
            "retrieval_mode": s.retrieval_mode, "generation_mode": "template",
            "understanding_mode": understanding_mode,
            "warnings": [s.warning] if s.warning else [], "statistics": None,
            "filters": {key: sorted(value) if isinstance(value, set) else value.isoformat() if isinstance(value, date) else value
                        for key, value in asdict(q).items() if value is not None},
        }
        if planner_warning:
            result["warnings"].append(planner_warning)
        if q.clarification:
            result.update(answer=q.clarification, intent="clarification")
            return result
        selected = [r for r in s.reports if q.accepts(r)]
        if q.content_filter and q.kind in {"count", "summary", "list"}:
            # Không bao giờ đưa số lượng từ một subset truy xuất top-k.
            if len(selected) > 100:
                result.update(intent="clarification", answer="Điều kiện nội dung cần AI xét hơn 100 phản ánh. Hãy thu hẹp theo tòa/ngày để kiểm tra đầy đủ.")
                return result
            try:
                ids = self.provider.filter_reports(q.content_filter, selected)
                selected = [r for r in selected if r.report_id in ids]
                result["warnings"].append("Điều kiện nội dung do LLM phân loại trên toàn bộ ứng viên; số lượng được code đếm. Hãy kiểm tra nguồn để đối chiếu.")
            except Exception:
                raise AIUnavailable("AI chưa kiểm tra đầy đủ điều kiện nội dung; chưa thể đưa kết quả thống kê/tổng hợp.")
        if q.kind == "count":
            result.update(self.count(selected, q))
            return result
        if q.kind == "list":
            days = sorted({r.created_at.astimezone(VN).date() for r in s.reports})
            scope = ""
            if q.day:
                scope = " ngày " + q.day.strftime("%d/%m/%Y")
            elif q.start_day or q.end_day:
                scope = " trong khoảng " + (q.start_day.isoformat() if q.start_day else "đầu dữ liệu") + " đến " + (q.end_day.isoformat() if q.end_day else "cuối dữ liệu")
            if q.entity == "incident":
                grouped = {}
                for report in selected:
                    if report.incident_id is not None:
                        grouped.setdefault(report.incident_id, []).append(report)
                lines = [f"Có {len(grouped)} sự cố liên kết với các phản ánh phù hợp{scope}."]
                for incident_id, reports in sorted(grouped.items()):
                    lines.append(f"Sự cố #{incident_id}: {reports[0].incident_status or 'chưa rõ'} — " + ", ".join(f"[PA{r.report_id}]" for r in reports))
            else:
                lines = [f"Có {len(selected)} phản ánh phù hợp{scope} trong bản dữ liệu đã nạp."]
                lines.extend(self.report_line(r) for r in sorted(selected, key=lambda r: r.created_at, reverse=True))
            if not selected and days:
                lines.append(f"Dữ liệu hiện có từ {days[0]:%d/%m/%Y} đến {days[-1]:%d/%m/%Y}. 'Hôm nay' tính theo UTC+7.")
            result.update(answer="\n".join(lines), generation_mode="deterministic",
                          sources=[r.model_dump(mode="json") for r in selected])
            return result
        if q.kind == "summary":
            # Tổng hợp xác định trên TẤT CẢ bản ghi phù hợp, không top-k hoặc cắt context.
            counts = Counter(r.category for r in selected)
            lines = [f"Tổng hợp đầy đủ {len(selected)} phản ánh phù hợp trong bản dữ liệu đã nạp."]
            for category, number in sorted(counts.items()):
                lines.append(f"{category}: {number} phản ánh.")
            lines.extend(self.report_line(r) for r in selected)
            if not selected:
                lines = ["Không có phản ánh phù hợp trong bản dữ liệu đã nạp."]
            result["answer"] = "\n".join(lines)
        elif q.kind == "lookup":
            result["answer"] = "\n".join(self.report_line(r) for r in selected)
        else:
            provider = self.provider if s.retrieval_mode == "semantic" else None
            try:
                ids = s.index.search(q.search_text or question, {r.report_id for r in selected}, top_k, provider,
                                     self.settings.semantic_min_score)
            except Exception:
                if self.settings.ai_required:
                    raise AIUnavailable("Không truy xuất được embedding. Kiểm tra kết nối AI rồi thử lại.")
                ids = s.index.search(question, {r.report_id for r in selected}, top_k)
                result["retrieval_mode"] = "lexical"
                result["warnings"].append("Không tìm kiếm được bằng embedding; chuyển sang từ khóa.")
            by_id = {r.report_id: r for r in selected}
            selected = [by_id[i] for i in ids]
            result["answer"] = "\n".join(self.report_line(r) for r in selected)
            if selected:
                result["answer"] = "Các phản ánh liên quan (không phải thống kê toàn bộ):\n" + result["answer"]
        if selected and self.provider:
            if sum(len(r.raw_text) for r in selected) > 16000:
                result["warnings"].append("Nguồn dài; hiển thị trích xuất đầy đủ thay vì cắt nguồn gửi cho AI.")
            else:
                try:
                    generated = self.provider.answer(question, selected)
                    self.validate_answer(generated, {r.report_id for r in selected})
                    result["answer"] = generated["answer"]
                    result["generation_mode"] = "llm"
                except Exception as exc:
                    code, message = explain_ai_error(exc)
                    logger.warning("AI answer failed: %s (%s)", code, type(exc).__name__)
                    if self.settings.ai_required:
                        raise AIUnavailable(f"[{code}] {message}") from exc
                    result["warnings"].append(f"[{code}] {message} Hiển thị dữ liệu gốc.")
        if not selected:
            result["answer"] = "Không tìm thấy phản ánh phù hợp trong bản dữ liệu đã nạp. Hãy nêu loại vấn đề, tòa nhà hoặc mã phản ánh."
        result["sources"] = [r.model_dump(mode="json") for r in selected]
        return result

    @staticmethod
    def report_line(r):
        location = " / ".join(filter(None, [r.building, f"tầng {r.floor}" if r.floor else None,
                                           f"phòng {r.room}" if r.room else None]))
        incident = f"Sự cố #{r.incident_id}: {r.incident_status or 'chưa rõ trạng thái'}" if r.incident_id else "Chưa liên kết sự cố"
        # Đây là nội dung gốc, không được thực thi hoặc render HTML.
        return f"[PA{r.report_id}] {location} — {r.raw_text}\n  {incident}."

    @staticmethod
    def validate_answer(data, allowed):
        if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
            raise ValueError("Sai cấu trúc câu trả lời")
        ids = data.get("report_ids")
        if data.get("insufficient_evidence") is True and ids == [] and data["answer"] == NO_EVIDENCE:
            return
        if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
            raise ValueError("Thiếu nguồn")
        cited = {int(i) for i in re.findall(r"\[PA(\d+)\]", data["answer"])}
        if not data["answer"].strip() or len(data["answer"]) > 12000 or not set(ids) <= allowed or cited != set(ids):
            raise ValueError("Nguồn không khớp dữ liệu truy xuất")

    @staticmethod
    def count(reports, q):
        linked = {r.incident_id for r in reports if r.incident_id is not None}
        unlinked = sum(r.incident_id is None for r in reports)
        stats = {"report_count": len(reports), "incident_count": len(linked), "unlinked_reports": unlinked,
                 "unknown_status_reports": sum(r.incident_status is None for r in reports), "groups": {}}
        # Incident count ở đây là số sự cố liên kết với các phản ánh phù hợp,
        # không thể biết các sự cố hoàn toàn không có trong file.
        if q.entity == "incident":
            answer = f"Có {len(linked)} sự cố khác nhau liên kết với các phản ánh phù hợp trong bản dữ liệu đã nạp."
            if unlinked:
                answer += f" Có {unlinked} phản ánh chưa liên kết, không tính thành sự cố."
        else:
            answer = f"Có {len(reports)} phản ánh phù hợp trong bản dữ liệu đã nạp."
        if q.group_by:
            groups = {}
            for r in reports:
                key = getattr(r, q.group_by) or "UNKNOWN"
                groups.setdefault(key, set())
                value = r.incident_id if q.entity == "incident" else r.report_id
                if value is not None:
                    groups[key].add(value)
            stats["groups"] = dict(sorted(((key, len(values)) for key, values in groups.items()), key=lambda x: (-x[1], x[0])))
            answer += "\n" + "\n".join(f"{key}: {value}" for key, value in stats["groups"].items())
            if q.entity == "incident":
                answer += "\nMột sự cố có thể xuất hiện ở nhiều nhóm nếu phản ánh thuộc nhiều vị trí/ngành mục."
        if q.day or q.start_day or q.end_day:
            answer += "\nNgày lọc là ngày gửi phản ánh, không phải ngày tạo hoặc giải quyết sự cố."
        return {"answer": answer, "statistics": stats,
                "sources": [r.model_dump(mode="json") for r in reports], "generation_mode": "deterministic"}
