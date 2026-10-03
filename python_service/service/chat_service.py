"""
Chat Service — Dịch vụ trả lời câu hỏi qua pipeline RAG.

Pipeline đầy đủ:
    Query → HybridRetriever.search()
          → GroqReranker.rerank()
          → DeepSeekProvider.ask()
          → Answer

Cách sử dụng:
    from service.chat import ChatService

    chat_service = ChatService()
    answer = chat_service.ask("Điều kiện tốt nghiệp là gì?")
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """
    Service xử lý chat — điều phối toàn bộ pipeline RAG.

    Kết hợp:
        - HybridRetriever: Dense + Sparse + RRF search
        - GroqReranker: Neural re-ranking & filtering
        - DeepSeekProvider: LLM generation

    Tất cả components được khởi tạo lazy để tối ưu startup time.
    """

    def __init__(self) -> None:
        self._retriever = None
        self._reranker = None
        self._llm = None

    # ─── Lazy initialization ─────────────────────────────────────────

    def _get_retriever(self):
        if self._retriever is None:
            from knowledge_base.hybrid_retrievel import HybridRetriever
            self._retriever = HybridRetriever()
            logger.info("ChatService: HybridRetriever initialized")
        return self._retriever

    def _get_reranker(self):
        if self._reranker is None:
            from knowledge_base.reranker import GroqReranker
            self._reranker = GroqReranker()
            logger.info("ChatService: GroqReranker initialized")
        return self._reranker

    def _get_llm(self):
        if self._llm is None:
            from knowledge_base.llm import DeepSeekProvider
            from core.config import settings
            self._llm = DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                model=settings.DEEPSEEK_MODEL,
            )
            logger.info("ChatService: DeepSeekProvider initialized")
        return self._llm

    # ═════════════════════════════════════════════════════════════════
    # ASK — Điểm vào chính cho chat
    # ═════════════════════════════════════════════════════════════════

    def ask(
        self,
        query: str,
        temperature: float = 0.5,
    ) -> dict:
        """
        Xử lý câu hỏi qua pipeline RAG đầy đủ.

        Pipeline:
            1. HybridRetriever.search() → candidates (Dense + Sparse + RRF)
            2. GroqReranker.rerank() → filtered & sorted chunks
            3. DeepSeekProvider.ask() → câu trả lời

        Args:
            query: Câu hỏi gốc của sinh viên.
            temperature: Sampling temperature cho LLM (mặc định 0.2 cho RAG).

        Returns:
            dict với các key:
                - answer: Câu trả lời từ LLM.
                - search_mode: Chế độ search đã dùng (hybrid/dense_only/sparse_only).
                - num_candidates: Số ứng viên từ hybrid search.
                - num_reranked: Số chunks sau reranking.
                - rerank_fallback: True nếu reranker fallback về RRF.

        Raises:
            Exception: Khi pipeline gặp lỗi critical (VectorStore down, ...).
        """
        logger.info(f"ChatService.ask() | query='{query[:80]}'")

        # ── Step 1: Hybrid Search ─────────────────────────────────────
        retriever = self._get_retriever()
        search_result = retriever.search(query=query)

        if search_result.is_empty:
            logger.info("ChatService: No search results, generating no-context answer")
            llm = self._get_llm()
            answer = llm.ask(query=query, temperature=temperature)
            return {
                "answer": answer,
                "search_mode": search_result.mode,
                "num_candidates": 0,
                "num_reranked": 0,
                "rerank_fallback": False,
            }

        # ── Step 2: Re-ranking ────────────────────────────────────────
        reranker = self._get_reranker()
        rerank_result = reranker.rerank(
            query=query,
            documents=search_result.documents,
            metadatas=search_result.metadatas,
            scores=search_result.rrf_scores,
        )

        # ── Step 3: LLM Generation ───────────────────────────────────
        llm = self._get_llm()
        answer = llm.ask(
            query=query,
            rerank_result=rerank_result,
            temperature=temperature,
        )

        logger.info(
            f"ChatService.ask() completed | "
            f"mode={search_result.mode}, "
            f"candidates={len(search_result.documents)}, "
            f"reranked={len(rerank_result.documents)}, "
            f"fallback={rerank_result.fallback_used}"
        )

        return {
            "answer": answer,
            "search_mode": search_result.mode,
            "num_candidates": len(search_result.documents),
            "num_reranked": len(rerank_result.documents),
            "rerank_fallback": rerank_result.fallback_used,
        }
