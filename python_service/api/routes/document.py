"""
Document Routes — FastAPI endpoints cho Document Upload & Management (Module 6).

Endpoints:
    POST   /documents/upload   — Upload file tài liệu cá nhân (PDF, DOCX, CSV, MD).
    GET    /documents          — Liệt kê tài liệu đã upload của user.
    DELETE /documents/{doc_id} — Xóa tài liệu của user.

Tất cả endpoints yêu cầu JWT Authentication (Authorization: Bearer <token>).

Pipeline upload:
    ┌─────────────────────────────────────────────────────────────┐
    │  Client                                                     │
    │    │                                                        │
    │    ├── POST /documents/upload (multipart/form-data + JWT)   │
    │    │     file: UploadFile                                   │
    │    │                                                        │
    │    ▼                                                        │
    │  DocumentService.upload()                                   │
    │    ├── Validate extension (.pdf, .docx, .csv, .md)          │
    │    ├── Save file tạm → data/uploads/{user_id}/              │
    │    ├── Parse text (DataLoader)                               │
    │    ├── Embed text chunks (Embedder)                          │
    │    ├── Lưu VectorDB với metadata user_id                    │
    │    ├── Lưu metadata vào SQL DB                              │
    │    └── Dọn dẹp file tạm                                     │
    │                                                             │
    │    ─→ 200 DocumentUploadResponse                            │
    └─────────────────────────────────────────────────────────────┘

Tham khảo:
    - Plan.md Module 6: FastAPI REST API (Document Routes)
    - services/document_service.py: DocumentService
    - api/dependencies.py: CurrentUserDep, DocumentServiceDep
    - api/schemas.py: DocumentUploadResponse, DocumentListResponse
"""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, Depends, File, UploadFile, status, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from api.dependencies import (
    DocumentServiceDep
)

from core.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/documents", tags=["Documents"])


# ═══════════════════════════════════════════════════════════════════════
# POST /documents/upload — Upload file tài liệu
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/upload",
    summary="Upload tài liệu cá nhân",
    description=(
        "Upload file tài liệu (PDF, DOCX, CSV, MD) để xây dựng "
        "knowledge base cá nhân. File sẽ được parse, chunk, embed "
        "và lưu vào vector database với user_id metadata.\n\n"
        "**Yêu cầu:** Authorization: Bearer <access_token>"
    ),
    responses={
        200: {"description": "Upload và indexing thành công"},
        400: {"description": "File type không hỗ trợ hoặc file rỗng"},
        401: {"description": "Token không hợp lệ"},
        500: {"description": "Lỗi server nội bộ"},
    },
)
async def upload_document(
    
    service: DocumentServiceDep,
    file_path:str | Path
):
    """Upload file tài liệu và ingest vào knowledge base.

    - Yêu cầu ``Authorization: Bearer <access_token>`` header.
    - File được parse, chunk, embed và lưu vào vector store.
    - Metadata gắn ``user_id`` để đảm bảo multi-tenant isolation.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
            None,
            partial(
                service.upload,
                file_path = file_path
            ),
        )
    return {
            "success": True,
            "message": result.message,
            "filename": result.filename,
            "chunks_indexed": result.chunks_indexed,
            "duration_seconds": result.duration_seconds,
        }


