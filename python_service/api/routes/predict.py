"""
Endpoint phân loại nội dung report.

ML pipeline trong checkpoint.joblib nhận DataFrame(Type, Describe)
và trả về nhãn 0 (không liên quan) hoặc 1 (có liên quan).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(tags=["Predict"])

# ═══════════════════════════════════════════════════════════════════════
# MODEL PATH — mặc định nằm cùng thư mục gốc python_service
# ═══════════════════════════════════════════════════════════════════════

_DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "checkpoint.joblib"

MODEL_PATH = os.getenv("MODEL_PATH", str(_DEFAULT_MODEL_PATH))


# ═══════════════════════════════════════════════════════════════════════
# LOAD PIPELINE — cache lại để không load lại mỗi request
# ═══════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def _load_pipeline():
    path = Path(MODEL_PATH)

    if not path.exists():
        raise RuntimeError(f"Model file not found: {path}")

    logger.info("Loading ML pipeline from %s", path)
    pipeline = joblib.load(path)
    logger.info("ML pipeline loaded successfully")
    return pipeline


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════

class PredictRequest(BaseModel):
    type: str = Field(
        ...,
        description="Loại report (category), ví dụ: NETWORK, FACILITY, …",
        alias="type",
    )
    describe: str = Field(
        ...,
        description="Mô tả chi tiết của report",
        alias="describe",
    )


class PredictResponse(BaseModel):
    label: int = Field(
        ...,
        description="0 = không liên quan, 1 = có liên quan",
    )
    relevant: bool = Field(
        ...,
        description="True nếu report có liên quan",
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /predict — Endpoint phân loại nội dung
# ═══════════════════════════════════════════════════════════════════════

@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    """
    Nhận Type + Describe, trả về label phân loại.

    - **label = 1**: Nội dung có liên quan → cho phép tạo report.
    - **label = 0**: Nội dung không liên quan → từ chối.
    """
    try:
        pipeline = _load_pipeline()
    except RuntimeError as exc:
        logger.error("Failed to load model: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="ML model is not available",
        ) from exc

    # Tạo DataFrame đúng format mà pipeline mong đợi
    df = pd.DataFrame([{
        "Type": req.type,
        "Describe": req.describe,
    }])

    try:
        prediction = pipeline.predict(df)
        label = int(prediction[0])
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Prediction failed",
        ) from exc

    logger.info(
        "Predict: type=%s, label=%d, relevant=%s",
        req.type,
        label,
        label == 1,
    )

    return PredictResponse(
        label=label,
        relevant=label == 1,
    )
