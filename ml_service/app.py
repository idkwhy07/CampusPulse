"""CampusPulse ML API: kiểm tra độ phù hợp của Type và Describe."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from campuspulse_predictor import IssuePredictor
from campuspulse_type_features import normalize_text, normalize_type

logger = logging.getLogger("uvicorn.error")


class IssueRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, populate_by_name=True,
        json_schema_extra={"examples": [{
            "Type": "Mạng và đường truyền",
            "Describe": "wifi tầng 4 bắt được mà load mãi không xong",
        }]},
    )
    type: str = Field(alias="Type", min_length=1, max_length=128)
    describe: str = Field(alias="Describe", min_length=1, max_length=10000)

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        return normalize_type(value)

    @field_validator("describe")
    @classmethod
    def valid_description(cls, value: str) -> str:
        value = normalize_text(value)
        if not value:
            raise ValueError("Describe không được rỗng.")
        return value


class PredictionResponse(BaseModel):
    type: str
    describe: str
    label: Literal[0, 1]
    is_match: bool
    probability: float = Field(ge=0, le=1)
    threshold: float = Field(gt=0, lt=1)
    model: str


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[IssueRequest] = Field(min_length=1, max_length=256)


class BatchResponse(BaseModel):
    count: int
    results: list[PredictionResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    ready: bool
    model: str
    threshold: float


class TypesResponse(BaseModel):
    count: int
    types: list[str]


def _predictor(request: Request) -> IssuePredictor:
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model chưa sẵn sàng.")
    return predictor


def create_app(
    model_path: str | Path | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    selected_path = model_path or os.getenv("CAMPUSPULSE_MODEL_PATH") or None
    if cors_origins is None:
        cors_origins = [
            origin.strip()
            for origin in os.getenv("CAMPUSPULSE_CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Model và TF-IDF chỉ được nạp một lần trước khi nhận request.
        application.state.predictor = IssuePredictor(selected_path)
        logger.info("CampusPulse model ready: %s", application.state.predictor.model_name)
        try:
            yield
        finally:
            application.state.predictor = None

    application = FastAPI(
        title="CampusPulse ML API",
        version="3.0.0",
        description=(
            "Kiểm tra mô tả có phù hợp Type được chọn hay không. "
            "label=1: phù hợp; label=0: không phù hợp."
        ),
        lifespan=lifespan,
    )
    application.state.predictor = None
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @application.get("/health", response_model=HealthResponse, tags=["Service"])
    def health(request: Request):
        predictor = _predictor(request)
        return {
            "status": "ok", "ready": True,
            "model": predictor.model_name, "threshold": predictor.threshold,
        }

    @application.get("/types", response_model=TypesResponse, tags=["Service"])
    def types(request: Request):
        names = list(_predictor(request).types)
        return {"count": len(names), "types": names}

    # Dùng def để FastAPI chạy phép tính đồng bộ trong thread pool.
    @application.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
    def predict(item: IssueRequest, request: Request):
        return _predictor(request).predict(item.type, item.describe)

    @application.post(
        "/predict/batch", response_model=BatchResponse, tags=["Prediction"]
    )
    def predict_batch(body: BatchRequest, request: Request):
        items = [item.model_dump(by_alias=True) for item in body.items]
        results = _predictor(request).predict_many(items)
        return {"count": len(results), "results": results}

    return application


app = create_app()
