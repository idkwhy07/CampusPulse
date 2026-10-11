"""
Document Service — Dịch vụ quản lý tài liệu (Upload, Delete).

Module này cung cấp DocumentService để:
    1. Upload: Load file → Chunk → Embed → Lưu ChromaDB + Build BM25 → Lưu BM25 cache
    2. Delete: Xóa từ ChromaDB + Xóa từ BM25 → Lưu BM25 cache

Pipeline Upload:
    File → LoaderRegistry.load()
         → Embedder.embed_batch()
         → VectorStore.add_documents()
         → VietnameseTokenizer.tokenize_batch()
         → BM25Store.add_documents() / BM25Store.build()
         → CacheManager.save_bm25()

Pipeline Delete:
    source_file → VectorStore.get_ids_by_source_file()
               → VectorStore.delete_documents()
               → BM25Store.remove_documents()
               → CacheManager.save_bm25()

Cách sử dụng:
    from service.document import DocumentService

    doc_service = DocumentService()

    # Upload
    result = doc_service.upload("data.pdf")

    # Delete
    result = doc_service.delete("data.pdf")
"""

from __future__ import annotations

from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    """
    Service quản lý tài liệu — Upload & Delete với đồng bộ ChromaDB + BM25.

    Mỗi lần upload/delete đều tự động:
        - Cập nhật ChromaDB (Dense search)
        - Cập nhật BM25Store (Sparse search)
        - Lưu BM25 qua CacheManager (L1 → L2 Redis → Supabase Origin)

    Tất cả components được khởi tạo lazy để tối ưu startup time.
    """

    def __init__(self) -> None:
        self._vector_store = None
        self._embedder = None
        self._tokenizer = None
        self._cache_manager = None

    # ─── Lazy initialization ─────────────────────────────────────────

    def _get_vector_store(self):
        if self._vector_store is None:
            from knowledge_base.vector_store import VectorStore
            self._vector_store = VectorStore()
            logger.info("DocumentService: VectorStore initialized")
        return self._vector_store

    def _get_embedder(self):
        if self._embedder is None:
            from knowledge_base.embed import Embedder
            self._embedder = Embedder()
            logger.info("DocumentService: Embedder initialized")
        return self._embedder

    def _get_tokenizer(self):
        if self._tokenizer is None:
            from knowledge_base.tokenize import VietnameseTokenizer
            self._tokenizer = VietnameseTokenizer()
            logger.info("DocumentService: VietnameseTokenizer initialized")
        return self._tokenizer

    def _get_cache_manager(self):
        if self._cache_manager is None:
            from knowledge_base.cache_manager import CacheManager
            self._cache_manager = CacheManager()
            logger.info("DocumentService: CacheManager initialized")
        return self._cache_manager

    # ═════════════════════════════════════════════════════════════════
    # UPLOAD — Load, Embed, Lưu ChromaDB + BM25
    # ═════════════════════════════════════════════════════════════════

    def upload(self, file_path: str | Path) -> dict:
        """
        Upload tài liệu vào hệ thống knowledge base.

        Pipeline:
            1. LoaderRegistry: Detect file type → load → chunk thành Documents
            2. Embedder: Embed tất cả chunks thành vectors
            3. VectorStore: Lưu documents + embeddings vào ChromaDB
            4. VietnameseTokenizer: Tokenize tất cả chunks cho BM25
            5. BM25Store: Thêm documents vào BM25 index (hoặc build mới)
            6. CacheManager: Lưu BM25 vào cả 3 tầng cache

        Args:
            file_path: Đường dẫn tới file cần upload (pdf, docx, csv, md).

        Returns:
            dict với các key:
                - source_file: Tên file đã upload.
                - num_chunks: Số chunks đã tạo.
                - num_embedded: Số vectors đã embed.
                - total_docs_chroma: Tổng documents trong ChromaDB sau upload.
                - total_docs_bm25: Tổng documents trong BM25 sau upload.

        Raises:
            DataLoadError: File không tồn tại hoặc format không hỗ trợ.
            EmbeddingError: Lỗi khi embed.
            VectorStoreError: Lỗi khi lưu ChromaDB.
        """
        file_path = Path(file_path)
        source_file = file_path.name

        logger.info(f"DocumentService.upload() | file='{source_file}'")

        # ── Step 1: Load file thành chunks ────────────────────────────
        from knowledge_base.document_loader import LoaderRegistry

        ext = file_path.suffix.lower()
        loader = LoaderRegistry.get_loader(ext)

        if loader is None:
            from core.exceptions import DataLoadError
            supported = LoaderRegistry.supported_extensions()
            raise DataLoadError(
                f"Không hỗ trợ file type: {ext}",
                details={
                    "file": source_file,
                    "extension": ext,
                    "supported": supported,
                },
            )

        documents = loader.load(file_path)

        ids = [doc.doc_id for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        logger.info(
            f"Step 1 done | Loaded {len(documents)} chunks from '{source_file}'"
        )

        # ── Step 2: Embed tất cả chunks ──────────────────────────────
        embedder = self._get_embedder()
        embeddings = embedder.embed_batch(contents)

        logger.info(
            f"Step 2 done | Embedded {len(embeddings)} vectors "
            f"({len(embeddings[0])}D each)"
        )

        # ── Step 3: Lưu vào ChromaDB ─────────────────────────────────
        vector_store = self._get_vector_store()
        vector_store.add_documents(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        total_chroma = vector_store.count()

        logger.info(
            f"Step 3 done | ChromaDB upserted {len(ids)} docs, "
            f"total={total_chroma}"
        )

        # ── Step 4: Tokenize cho BM25 ────────────────────────────────
        tokenizer = self._get_tokenizer()
        tokenized_docs = tokenizer.tokenize_batch(contents)

        logger.info(
            f"Step 4 done | Tokenized {len(tokenized_docs)} documents"
        )

        # ── Step 5: Cập nhật BM25Store ───────────────────────────────
        cache_manager = self._get_cache_manager()
        bm25_store = cache_manager.get_bm25()

        if bm25_store is None or bm25_store.is_empty:
            # Chưa có BM25 index → build mới
            from knowledge_base.bm25_store import BM25Store
            bm25_store = BM25Store.build(
                doc_ids=ids,
                documents=contents,
                metadatas=metadatas,
                tokenized_corpus=tokenized_docs,
            )
            logger.info("Step 5 done | BM25Store built from scratch")
        else:
            # Đã có → thêm documents mới
            bm25_store.add_documents(
                doc_ids=ids,
                documents=contents,
                metadatas=metadatas,
                tokenized_docs=tokenized_docs,
            )
            logger.info(
                f"Step 5 done | BM25Store updated, "
                f"total={len(bm25_store.doc_ids)}"
            )

        total_bm25 = len(bm25_store.doc_ids)

        # ── Step 6: Lưu BM25 vào cache (3 tầng) ─────────────────────
        cache_manager.save_bm25(store=bm25_store)

        logger.info(
            f"Step 6 done | BM25 saved to all cache tiers"
        )

        logger.info(
            f"DocumentService.upload() completed | "
            f"file='{source_file}', chunks={len(documents)}, "
            f"chroma_total={total_chroma}, bm25_total={total_bm25}"
        )

        return {
            "source_file": source_file,
            "num_chunks": len(documents),
            "num_embedded": len(embeddings),
            "total_docs_chroma": total_chroma,
            "total_docs_bm25": total_bm25,
        }

    # ═════════════════════════════════════════════════════════════════
    # DELETE — Xóa tài liệu từ ChromaDB + BM25
    # ═════════════════════════════════════════════════════════════════

    def delete(self, source_file: str) -> dict:
        """
        Xóa tài liệu theo tên file nguồn khỏi hệ thống.

        Pipeline:
            1. VectorStore.get_ids_by_source_file() → lấy danh sách chunk IDs
            2. VectorStore.delete_documents() → xóa khỏi ChromaDB
            3. BM25Store.remove_documents() → xóa khỏi BM25 index
            4. CacheManager.save_bm25() → lưu BM25 cập nhật vào cache

        Args:
            source_file: Tên file nguồn cần xóa (vd: "data.pdf").

        Returns:
            dict với các key:
                - source_file: Tên file đã xóa.
                - num_deleted: Số chunks đã xóa.
                - total_docs_chroma: Tổng documents còn lại trong ChromaDB.
                - total_docs_bm25: Tổng documents còn lại trong BM25.

        Raises:
            VectorStoreError: Lỗi khi truy cập ChromaDB.
        """
        logger.info(f"DocumentService.delete() | source_file='{source_file}'")

        # ── Step 1: Lấy danh sách IDs cần xóa ───────────────────────
        vector_store = self._get_vector_store()
        ids_to_delete = vector_store.get_ids_by_source_file(source_file)

        if not ids_to_delete:
            logger.warning(
                f"No documents found for source_file='{source_file}'"
            )
            return {
                "source_file": source_file,
                "num_deleted": 0,
                "total_docs_chroma": vector_store.count(),
                "total_docs_bm25": 0,
            }

        logger.info(
            f"Step 1 done | Found {len(ids_to_delete)} chunks to delete"
        )

        # ── Step 2: Xóa khỏi ChromaDB ───────────────────────────────
        vector_store.delete_documents(ids=ids_to_delete)
        total_chroma = vector_store.count()

        logger.info(
            f"Step 2 done | Deleted from ChromaDB, remaining={total_chroma}"
        )

        # ── Step 3: Xóa khỏi BM25Store ──────────────────────────────
        cache_manager = self._get_cache_manager()
        bm25_store = cache_manager.get_bm25()
        total_bm25 = 0

        if bm25_store is not None and not bm25_store.is_empty:
            bm25_store.remove_documents(doc_ids_to_remove=ids_to_delete)
            total_bm25 = len(bm25_store.doc_ids)

            # ── Step 4: Lưu BM25 cập nhật vào cache ─────────────────
            if bm25_store.is_empty:
                # Nếu BM25 rỗng sau khi xóa → invalidate toàn bộ cache
                cache_manager.invalidate()
                logger.info("Step 4 done | BM25 empty, cache invalidated")
            else:
                cache_manager.save_bm25(store=bm25_store)
                logger.info("Step 4 done | BM25 saved to all cache tiers")
        else:
            logger.info("Step 3 skipped | No BM25 index found")

        logger.info(
            f"DocumentService.delete() completed | "
            f"file='{source_file}', deleted={len(ids_to_delete)}, "
            f"chroma_remaining={total_chroma}, bm25_remaining={total_bm25}"
        )

        return {
            "source_file": source_file,
            "num_deleted": len(ids_to_delete),
            "total_docs_chroma": total_chroma,
            "total_docs_bm25": total_bm25,
        }
