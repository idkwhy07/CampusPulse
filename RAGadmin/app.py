import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import BASE, Settings
from rag import AIUnavailable, Chatbot
from schemas import ChatRequest
from sources import FileReportSource, PostgresReportSource


def create_app(settings=None, provider=None):
    settings = settings or Settings.from_env()
    settings.validate()

    source = (
        PostgresReportSource(settings.database_url)
        if settings.data_mode == "postgres"
        else FileReportSource(settings.reports_path)
    )
    bot = Chatbot(settings, source, provider)

    @asynccontextmanager
    async def lifespan(app):
        bot.sync()
        yield

    app = FastAPI(title="CampusPulse Admin Chatbot", version="1.0.0", lifespan=lifespan)
    app.state.bot = bot

    @app.exception_handler(AIUnavailable)
    async def ai_error(request, exc):
        return JSONResponse(status_code=503, content={"error": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=422, content={"error": "Câu hỏi cần 1–1000 ký tự; top_k từ 1 đến 10. Kiểm tra cấu trúc JSON."})

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    def authorize(request: Request, x_internal_key: str = Header(default="")):
        if settings.app_mode == "internal":
            if not secrets.compare_digest(x_internal_key, settings.api_key):
                raise HTTPException(401, "Thiếu hoặc sai khóa dịch vụ nội bộ")
        else:
            # Demo chỉ cho loopback, không chỉ dựa vào --host 127.0.0.1.
            host = request.client.host if request.client else ""
            if host not in {"127.0.0.1", "::1", "testclient"}:
                raise HTTPException(403, "Demo chỉ dùng trên máy cục bộ")
            if request.headers.get("origin") and request.headers["origin"] != str(request.base_url).rstrip("/"):
                raise HTTPException(403, "Yêu cầu khác nguồn bị từ chối")

    @app.middleware("http")
    async def guard_body(request, call_next):
        if request.method == "POST":
            # Giới hạn cả request không có Content-Length.
            total, parts = 0, []
            async for part in request.stream():
                total += len(part)
                if total > 16384:
                    return JSONResponse(status_code=413, content={"error": "Request quá lớn"})
                parts.append(part)
            request._body = b"".join(parts)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "ready": bot.snapshot is not None}

    @app.get("/internal/admin/status", dependencies=[Depends(authorize)])
    def status():
        return bot.status()

    @app.post("/internal/admin/sync", dependencies=[Depends(authorize)])
    def sync():
        try:
            return bot.sync()
        except Exception:
            logging.getLogger(__name__).warning("Đồng bộ thất bại; giữ snapshot cũ.")
            raise HTTPException(400, "Không đồng bộ được. Kiểm tra file CSV/JSON, mã trùng, múi giờ và trạng thái sự cố. Dữ liệu cũ vẫn được giữ.")

    @app.post("/internal/admin/chat", dependencies=[Depends(authorize)])
    def chat(body: ChatRequest):
        if settings.data_mode == "postgres":
            try:
                bot.sync()
            except Exception:
                logging.getLogger(__name__).exception("Không đồng bộ được PostgreSQL trước khi chat.")
                raise HTTPException(503, "Không đọc được dữ liệu CampusPulse hiện tại")
        return bot.chat(body.question, body.top_k)

    if settings.app_mode == "demo":
        app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

        @app.get("/", dependencies=[Depends(authorize)])
        def home():
            return FileResponse(BASE / "static/index.html")

    return app


app = create_app()
