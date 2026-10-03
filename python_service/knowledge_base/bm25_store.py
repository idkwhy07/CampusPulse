"""
BM25 Store — Wrapper BM25Okapi + Serialization.

Module này quản lý chỉ mục BM25, hỗ trợ:
    - Xây dựng chỉ mục BM25Okapi trên tokenized corpus
    - Tìm kiếm sparse (keyword matching)
    - Serialize/Deserialize (pickle + zstd compression) để lưu trữ vào
      Redis (L2 Cache) và Supabase Storage (Origin)

Cách sử dụng:
    from knowledge_base.bm25_store import BM25Store

    store = BM25Store.build(
        doc_ids=["chunk_1", "chunk_2"],
        documents=["nội dung chunk 1", "nội dung chunk 2"],
        metadatas=[{"source_file": "report.pdf"}, ...],
        tokenized_corpus=[["nội_dung", "chunk", "1"], ...],
    )

    results = store.search(query_tokens=["nội_dung"], top_k=5)
    # [(doc_id, score), ...]

    # Serialize để lưu vào cache/storage
    data = store.serialize()
    restored = BM25Store.deserialize(data)
"""

from __future__ import annotations

import pickle
import zlib
from dataclasses import dataclass, field

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# BM25 STORE — Wrapper BM25Okapi
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BM25Store:
    """
    Encapsulate BM25Okapi model cùng dữ liệu corpus.

    Chứa đầy đủ thông tin để tái tạo lại model từ serialized bytes.

    Attributes:
        doc_ids: Danh sách chunk_id map 1-1 với ChromaDB.
        documents: Nội dung văn bản gốc của các chunks.
        metadatas: Metadata đi kèm (source_file, chunk_index, ...).
        tokenized_corpus: Mảng tokens đã qua PyVi cho mỗi document.
        bm25_model: Đối tượng BM25Okapi đã fit trên corpus.
    """
    doc_ids: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    metadatas: list[dict] = field(default_factory=list)
    tokenized_corpus: list[list[str]] = field(default_factory=list)
    bm25_model: object = None  # rank_bm25.BM25Okapi instance

    # ─── Factory method ───────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        doc_ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        tokenized_corpus: list[list[str]],
    ) -> BM25Store:
        """
        Xây dựng BM25Store mới từ corpus đã tokenize.

        Args:
            doc_ids: Danh sách chunk IDs.
            documents: Nội dung text gốc.
            metadatas: Metadata (source_file, page, ...).
            tokenized_corpus: Tokens đã qua VietnameseTokenizer.

        Returns:
            BM25Store instance với BM25Okapi model đã fit.
        """
        from rank_bm25 import BM25Okapi

        if not tokenized_corpus:
            logger.warning("BM25Store.build: empty corpus")
            return cls(
                doc_ids=doc_ids,
                documents=documents,
                metadatas=metadatas,
                tokenized_corpus=tokenized_corpus,
                bm25_model=None,
            )

        bm25 = BM25Okapi(tokenized_corpus)

        logger.info(
            f"BM25Store built | "
            f"{len(doc_ids)} documents, "
            f"{sum(len(t) for t in tokenized_corpus)} total tokens"
        )

        return cls(
            doc_ids=doc_ids,
            documents=documents,
            metadatas=metadatas,
            tokenized_corpus=tokenized_corpus,
            bm25_model=bm25,
        )

    # ─── Search ───────────────────────────────────────────────────────

    def search(
        self,
        query_tokens: list[str],
        top_k: int = settings.N_RESULT_RETRIEVEL,
    ) -> list[tuple[str, str, dict, float]]:
        """
        Tìm kiếm sparse BM25 trên corpus.

        Args:
            query_tokens: Tokens đã qua VietnameseTokenizer.
            top_k: Số kết quả trả về.

        Returns:
            Danh sách tuple (doc_id, document, metadata, bm25_score),
            sắp xếp giảm dần theo score.
        """
        if self.bm25_model is None or not self.doc_ids:
            return []

        if not query_tokens:
            return []

        import numpy as np

        scores = self.bm25_model.get_scores(query_tokens)

        # Lấy top_k indices có score cao nhất
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            results.append((
                self.doc_ids[idx],
                self.documents[idx],
                self.metadatas[idx] if idx < len(self.metadatas) else {},
                score,
            ))

        return results

    # ─── Thêm / Xóa documents ────────────────────────────────────────

    def add_documents(
        self,
        doc_ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        tokenized_docs: list[list[str]],
    ) -> None:
        """
        Thêm documents mới vào store và rebuild BM25 model.

        Args:
            doc_ids: IDs mới.
            documents: Nội dung mới.
            metadatas: Metadata mới.
            tokenized_docs: Tokens đã tách từ mới.
        """
        self.doc_ids.extend(doc_ids)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.tokenized_corpus.extend(tokenized_docs)

        self._rebuild_model()

        logger.info(
            f"BM25Store updated | "
            f"added {len(doc_ids)} docs, total={len(self.doc_ids)}"
        )

    def remove_documents(self, doc_ids_to_remove: list[str]) -> None:
        """
        Xóa documents theo IDs và rebuild BM25 model.

        Args:
            doc_ids_to_remove: Danh sách doc_ids cần xóa.
        """
        if not doc_ids_to_remove:
            return

        remove_set = set(doc_ids_to_remove)
        keep_indices = [
            i for i, did in enumerate(self.doc_ids)
            if did not in remove_set
        ]

        self.doc_ids = [self.doc_ids[i] for i in keep_indices]
        self.documents = [self.documents[i] for i in keep_indices]
        self.metadatas = [self.metadatas[i] for i in keep_indices]
        self.tokenized_corpus = [self.tokenized_corpus[i] for i in keep_indices]

        self._rebuild_model()

        logger.info(
            f"BM25Store pruned | "
            f"removed {len(doc_ids_to_remove)} docs, "
            f"remaining={len(self.doc_ids)}"
        )

    def _rebuild_model(self) -> None:
        """Rebuild BM25Okapi model từ tokenized_corpus hiện tại."""
        if not self.tokenized_corpus:
            self.bm25_model = None
            return

        from rank_bm25 import BM25Okapi
        self.bm25_model = BM25Okapi(self.tokenized_corpus)

    # ─── Serialization ────────────────────────────────────────────────

    def serialize(self) -> bytes:
        """
        Serialize BM25Store thành bytes (pickle + zlib compression).

        Lưu toàn bộ state trừ bm25_model (sẽ rebuild khi deserialize
        từ tokenized_corpus).

        Returns:
            Compressed bytes.
        """
        payload = {
            "doc_ids": self.doc_ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "tokenized_corpus": self.tokenized_corpus,
        }
        raw = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(raw, level=6)

        logger.debug(
            f"BM25Store serialized | "
            f"raw={len(raw)} bytes, compressed={len(compressed)} bytes "
            f"(ratio={len(compressed)/max(len(raw),1):.2%})"
        )
        return compressed

    @classmethod
    def deserialize(cls, data: bytes) -> BM25Store:
        """
        Deserialize bytes thành BM25Store và rebuild BM25Okapi model.

        Args:
            data: Compressed bytes từ serialize().

        Returns:
            BM25Store instance với model đã fit.
        """
        raw = zlib.decompress(data)
        payload = pickle.loads(raw)

        return cls.build(
            doc_ids=payload["doc_ids"],
            documents=payload["documents"],
            metadatas=payload["metadatas"],
            tokenized_corpus=payload["tokenized_corpus"],
        )

    @property
    def is_empty(self) -> bool:
        """Kiểm tra store có rỗng không."""
        return len(self.doc_ids) == 0
