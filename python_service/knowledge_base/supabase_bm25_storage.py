"""
Supabase BM25 Storage — Tầng Gốc (Origin) cho BM25 Index.

Module này quản lý lưu trữ vĩnh viễn file chỉ mục BM25 (.pkl)
trên Supabase Storage (S3-compatible), đóng vai trò Single Source of Truth
trong kiến trúc Two-Tier Cache.

Cấu trúc lưu trữ trên Supabase Storage:
    bm25-indexes/
    └── global/index.pkl

Cách sử dụng:
    from knowledge_base.supabase_bm25_storage import SupabaseBM25Storage

    storage = SupabaseBM25Storage()
    storage.upload_index(data=serialized_bytes)
    data = storage.download_index()
    storage.delete_index()
"""

from __future__ import annotations

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# SUPABASE BM25 STORAGE
# ═══════════════════════════════════════════════════════════════════════

class SupabaseBM25Storage:
    """
    Giao tiếp Supabase Storage để lưu/lấy/xóa file chỉ mục BM25.

    Sử dụng Supabase Python SDK (supabase-py).
    Hệ thống dùng duy nhất 1 file index.pkl chung.

    Attributes:
        _client: Supabase client instance.
        _bucket: Tên bucket trên Supabase Storage.
    """

    # Path cố định cho file index duy nhất
    _INDEX_PATH = "global/index.pkl"

    def __init__(self) -> None:
        self._client = None
        self._bucket = settings.SUPABASE_BM25_BUCKET
        self._init_client()

    def _init_client(self) -> None:
        """Khởi tạo Supabase client."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(
                "Supabase credentials not configured. "
                "BM25 origin storage will be disabled."
            )
            return

        try:
            from supabase import create_client

            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )
            logger.info(
                f"SupabaseBM25Storage initialized | "
                f"bucket='{self._bucket}'"
            )
        except Exception as e:
            logger.error(f"Failed to init Supabase client: {e}")
            self._client = None

    @property
    def is_available(self) -> bool:
        """Kiểm tra Supabase Storage có sẵn sàng không."""
        return self._client is not None

    def upload_index(self, data: bytes) -> bool:
        """
        Upload file chỉ mục BM25 lên Supabase Storage.

        Ghi đè nếu file đã tồn tại (upsert).

        Args:
            data: Serialized bytes từ BM25Store.serialize().

        Returns:
            True nếu upload thành công, False nếu thất bại.
        """
        if not self.is_available:
            logger.warning("Supabase not available, skip upload")
            return False

        try:
            self._client.storage.from_(self._bucket).upload(
                path=self._INDEX_PATH,
                file=data,
                file_options={
                    "content-type": "application/octet-stream",
                    "upsert": "true",
                },
            )
            logger.info(
                f"BM25 index uploaded to Supabase | size={len(data)} bytes"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to upload BM25 index | error={e}"
            )
            return False

    def download_index(self) -> bytes | None:
        """
        Download file chỉ mục BM25 từ Supabase Storage.

        Returns:
            Bytes data nếu tìm thấy, None nếu không có hoặc lỗi.
        """
        if not self.is_available:
            logger.warning("Supabase not available, skip download")
            return None

        try:
            response = self._client.storage.from_(self._bucket).download(
                self._INDEX_PATH
            )
            if response:
                logger.info(
                    f"BM25 index downloaded from Supabase | "
                    f"size={len(response)} bytes"
                )
                return response
            return None

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                logger.debug("BM25 index not found on Supabase")
                return None

            logger.error(f"Failed to download BM25 index | error={e}")
            return None

    def delete_index(self) -> bool:
        """
        Xóa file chỉ mục BM25 trên Supabase Storage.

        Returns:
            True nếu xóa thành công, False nếu thất bại.
        """
        if not self.is_available:
            logger.warning("Supabase not available, skip delete")
            return False

        try:
            self._client.storage.from_(self._bucket).remove([self._INDEX_PATH])
            logger.info("BM25 index deleted from Supabase")
            return True

        except Exception as e:
            logger.error(f"Failed to delete BM25 index | error={e}")
            return False
