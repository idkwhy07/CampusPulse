from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter

from api.dependencies import ChatServiceDep
from api.schemas import ChatRequest

router = APIRouter(tags=["Chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    service: ChatServiceDep,
):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(service.ask, body.query),
    )
