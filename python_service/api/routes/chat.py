from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter


from api.dependencies import ChatServiceDep
from core.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# ROUTER — Tạo APIRouter cho chat endpoints
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(tags=["Chat"])


# ═══════════════════════════════════════════════════════════════════════
# HELPER — Tạo error response chuẩn hóa
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# POST /chat — Endpoint chính: nhận câu hỏi, trả response từ agent
# ═══════════════════════════════════════════════════════════════════════

@router.post("/chat")
async def chat(
    query: str,
    service: ChatServiceDep,
):

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,  # Default thread pool executor
            partial(service.ask, query),
        )

        return response

   

