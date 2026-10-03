from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import chat, document, predict
import os




app = FastAPI()

# ── CORS Middleware — cho phép frontend gọi API cross-origin ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: thay bằng domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat.router,
    prefix="/api"
)

app.include_router(
    document.router,
    prefix="/api"
)

app.include_router(
    predict.router,
    prefix="/api"
)


