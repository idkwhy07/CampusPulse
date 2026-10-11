import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    reports_path: Path = BASE / "data/phananh.json"
    app_mode: str = "demo"
    data_mode: str = "mock"
    api_key: str = ""
    ai_mode: str = "offline"
    embed_model: str = "gemini-embedding-001"
    chat_model: str = "deepseek-chat"
    timeout: float = 60
    semantic_min_score: float = 0.35
    ai_required: bool = False
    deepseek_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = ""

    @classmethod
    def from_env(cls):
        load_dotenv(BASE / ".env")
        path = Path(os.getenv("REPORTS_PATH", "data/phananh.json"))
        return cls(
            reports_path=path if path.is_absolute() else BASE / path,
            app_mode=os.getenv("APP_MODE", "demo"),
            data_mode=os.getenv("DATA_MODE", "mock"),
            api_key=os.getenv("INTERNAL_API_KEY", ""),
            ai_mode=os.getenv("AI_MODE", "offline").lower(),
            embed_model=os.getenv("EMBED_MODEL", "gemini-embedding-001"),
            chat_model=os.getenv("CHAT_MODEL", "deepseek-chat"),
            timeout=float(os.getenv("AI_TIMEOUT", "60")),
            semantic_min_score=float(os.getenv("SEMANTIC_MIN_SCORE", "0.35")),
            ai_required=os.getenv("AI_REQUIRED", "false").lower() == "true",
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            database_url=os.getenv("DATABASE_URL", ""),
        )

    def validate(self):
        if self.app_mode not in {"demo", "internal"}:
            raise ValueError("APP_MODE phải là demo hoặc internal")
        if self.data_mode not in {"mock", "file", "postgres"}:
            raise ValueError("DATA_MODE phải là mock, file hoặc postgres")
        if self.app_mode == "demo" and self.data_mode != "mock":
            raise ValueError("Dữ liệu thật phải chạy APP_MODE=internal")
        if self.data_mode == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL là bắt buộc khi DATA_MODE=postgres")
        if self.app_mode == "internal" and len(self.api_key) < 24:
            raise ValueError("INTERNAL_API_KEY cần ít nhất 24 ký tự")
        if self.ai_mode not in {"offline", "cloud"}:
            raise ValueError("AI_MODE phải là offline hoặc cloud")
        if self.ai_required and self.ai_mode != "cloud":
            raise ValueError("AI_REQUIRED=true cần AI_MODE là cloud")
        if self.ai_mode == "cloud":
            if not self.gemini_api_key:
                raise ValueError("Cần GEMINI_API_KEY khi dùng AI_MODE=cloud")
            if not self.deepseek_api_key:
                raise ValueError("Cần DEEPSEEK_API_KEY khi dùng AI_MODE=cloud")
        if self.timeout <= 0 or not 0 <= self.semantic_min_score <= 1:
            raise ValueError("Cấu hình timeout/ngưỡng tìm kiếm không hợp lệ")