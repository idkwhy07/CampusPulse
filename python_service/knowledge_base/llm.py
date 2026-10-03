"""
LLM Provider — DeepSeek V4 Flash + RAG Prompt Builder.

Module này cung cấp:
    1. DeepSeekProvider: LLM client sử dụng OpenAI-compatible API của DeepSeek.
    2. RAGPromptBuilder: Xây dựng messages phù hợp cho pipeline RAG
       (Hybrid Search → Re-ranking → LLM Generation).

Kiến trúc:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  Pipeline: Query → Hybrid Search → Re-ranking → RAGPromptBuilder  │
    │                                                                     │
    │  RAGPromptBuilder                                                   │
    │    ├── SYSTEM_PROMPT: Vai trò CampusPulse AI Assistant              │
    │    ├── build_context_block() — format RerankResult → context text   │
    │    ├── build_rag_messages() — tạo messages cho DeepSeek             │
    │    └── estimate_tokens() — ước lượng token count                    │
    │                                                                     │
    │  DeepSeekProvider                                                   │
    │    ├── _client: OpenAI (base_url=https://api.deepseek.com)          │
    │    ├── _model: "deepseek-flash"                                     │
    │    ├── generate() — gọi chat.completions.create()                   │
    │    └── ask() — high-level: RerankResult + query → answer            │
    └─────────────────────────────────────────────────────────────────────┘

Message format (DeepSeek OpenAI-compatible):
    [
        {"role": "system", "content": "..."},       # System prompt
        {"role": "user", "content": "..."},          # Context + Query
    ]

    DeepSeek hỗ trợ system/user/assistant roles giống OpenAI.
    Với RAG, chỉ cần 2 messages: system (định nghĩa vai trò) + user (context + câu hỏi).

Cách sử dụng:
    from knowledge_base.llm import DeepSeekProvider

    provider = DeepSeekProvider(
        api_key=settings.DEEPSEEK_API_KEY,
        model=settings.DEEPSEEK_MODEL,
    )

    # High-level RAG answer:
    answer = provider.ask(
        query="Điều kiện tốt nghiệp là gì?",
        rerank_result=rerank_result,   # Kết quả từ GroqReranker
    )

    # Low-level generate:
    response = provider.generate(
        messages=RAGPromptBuilder.build_rag_messages(
            query="...", rerank_result=rerank_result,
        ),
    )

Tham khảo:
    - core/config.py: DEEPSEEK_API_KEY, DEEPSEEK_MODEL, TEMPERATURE, MAX_TOKENS_OUTPUT
    - knowledge_base/reranker.py: RerankResult (input cho prompt builder)
    - knowledge_base/hybrid_retrievel.py: HybridSearchResult (upstream data)
    - DeepSeek API docs: https://api-docs.deepseek.com/
"""

from __future__ import annotations

from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Vai trò CampusPulse AI Assistant
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là CampusPulse AI — trợ lý thông minh chuyên cung cấp thông tin chính xác cho sinh viên đại học.

## Vai trò
Bạn giúp sinh viên tra cứu và hiểu rõ các thông tin liên quan đến trường đại học, bao gồm nhưng không giới hạn:
- Quy chế đào tạo, quy định học vụ
- Chương trình đào tạo, kế hoạch học tập
- Thủ tục hành chính (đăng ký học, bảo lưu, chuyển ngành, ...)
- Học phí, học bổng, chính sách hỗ trợ
- Hoạt động ngoại khóa, câu lạc bộ, sự kiện
- Thông tin tuyển sinh, điều kiện tốt nghiệp

## Nguyên tắc trả lời
1. **Chỉ trả lời dựa trên tài liệu được cung cấp**: Nếu thông tin không có trong phần TÀI LIỆU THAM KHẢO bên dưới, hãy nói rõ rằng bạn không tìm thấy thông tin này trong dữ liệu hiện có và khuyên sinh viên liên hệ phòng ban phù hợp.
2. **Trích dẫn nguồn**: Khi trả lời, nếu có thể hãy ghi rõ thông tin lấy từ tài liệu nào (dựa trên metadata nguồn).
3. **Chính xác và cụ thể**: Ưu tiên đưa ra con số, điều khoản, thời hạn cụ thể thay vì nói chung chung.
4. **Ngôn ngữ thân thiện**: Dùng tiếng Việt tự nhiên, thân thiện với sinh viên nhưng vẫn chuyên nghiệp.
5. **Cấu trúc rõ ràng**: Sử dụng bullet points, đánh số, in đậm cho các điểm quan trọng.
6. **Thành thật khi không biết**: Tuyệt đối KHÔNG bịa thông tin. Nếu không chắc chắn, hãy nói rõ mức độ tin cậy.

## Định dạng trả lời
- Trả lời bằng tiếng Việt.
- Sử dụng Markdown formatting để dễ đọc.
- Với câu hỏi phức tạp, chia thành các phần rõ ràng.
- Nếu câu hỏi mơ hồ, hỏi lại để làm rõ trước khi trả lời."""


# ═══════════════════════════════════════════════════════════════════════
# NO-CONTEXT PROMPT — Khi không có tài liệu nào phù hợp
# ═══════════════════════════════════════════════════════════════════════

NO_CONTEXT_RESPONSE_INSTRUCTION = """⚠️ KHÔNG CÓ TÀI LIỆU THAM KHẢO nào phù hợp với câu hỏi này.

Hãy trả lời theo đúng nguyên tắc:
- Thông báo rằng bạn không tìm thấy thông tin liên quan trong cơ sở dữ liệu hiện có.
- Gợi ý sinh viên liên hệ phòng ban phù hợp (Phòng Đào tạo, Phòng Công tác sinh viên, ...) hoặc kiểm tra website trường.
- KHÔNG bịa thông tin."""


# ═══════════════════════════════════════════════════════════════════════
# RAG PROMPT BUILDER — Xây dựng messages cho DeepSeek
# ═══════════════════════════════════════════════════════════════════════

class RAGPromptBuilder:
    """
    Xây dựng messages list phù hợp với DeepSeek API format.

    Nhận kết quả từ pipeline: HybridSearch → RRF → GroqReranker (RerankResult)
    và build thành messages cho DeepSeek chat.completions.

    DeepSeek message format (OpenAI-compatible):
        [
            {"role": "system", "content": "<system prompt>"},
            {"role": "user",   "content": "<context + query>"},
        ]

    Lưu ý cho DeepSeek:
        - DeepSeek xử lý tốt system prompt dài, không cần tách nhỏ.
        - Không cần prefix/suffix đặc biệt (khác với một số model khác).
        - Temperature thấp (0.1-0.3) cho RAG để đảm bảo trung thực.
        - DeepSeek hỗ trợ tiếng Việt tốt, không cần dịch sang tiếng Anh.
    """

    @staticmethod
    def build_context_block(
        documents: list[str],
        metadatas: list[dict],
        scores: list[float],
        max_context_chars: int = 6000,
    ) -> str:
        """
        Format danh sách documents thành context block cho prompt.

        Mỗi tài liệu được đánh số, kèm metadata nguồn và điểm relevance.
        Tổng chiều dài được giới hạn để tránh vượt token limit.

        Args:
            documents: Danh sách nội dung tài liệu (đã qua re-ranking).
            metadatas: Danh sách metadata tương ứng.
            scores: Danh sách điểm relevance từ re-ranker.
            max_context_chars: Giới hạn tổng ký tự context.

        Returns:
            Context text đã format sẵn.

        Ví dụ output:
            === TÀI LIỆU THAM KHẢO ===

            📄 [Tài liệu 1] (Nguồn: quy_che_dao_tao.pdf | Trang: 5 | Độ liên quan: 9.2/10)
            Sinh viên phải hoàn thành tối thiểu 130 tín chỉ...
            ---
        """
        if not documents:
            return ""

        parts = ["=== TÀI LIỆU THAM KHẢO ===\n"]
        total_chars = 0

        for i, (doc, meta, score) in enumerate(zip(documents, metadatas, scores)):
            # ── Build header với metadata ──
            source_info = _extract_source_info(meta)
            header = (
                f"📄 [Tài liệu {i + 1}] "
                f"({source_info} | Độ liên quan: {score:.1f}/10)"
            )

            # ── Truncate document nếu cần ──
            doc_text = doc.strip()
            remaining = max_context_chars - total_chars
            if remaining <= 0:
                break
            if len(doc_text) > remaining:
                doc_text = doc_text[:remaining] + "... [cắt ngắn]"

            block = f"{header}\n{doc_text}\n---\n"
            parts.append(block)
            total_chars += len(block)

        return "\n".join(parts)

    @staticmethod
    def build_rag_messages(
        query: str,
        documents: list[str] | None = None,
        metadatas: list[dict] | None = None,
        scores: list[float] | None = None,
        rerank_result: Any = None,
        system_prompt: str = SYSTEM_PROMPT,
        max_context_chars: int = 6000,
    ) -> list[dict[str, str]]:
        """
        Xây dựng messages list cho DeepSeek API từ kết quả RAG.

        Có thể nhận input trực tiếp (documents, metadatas, scores)
        hoặc từ RerankResult object.

        Args:
            query: Câu hỏi gốc của sinh viên.
            documents: Danh sách nội dung tài liệu.
            metadatas: Danh sách metadata.
            scores: Danh sách điểm relevance.
            rerank_result: RerankResult object (ưu tiên hơn nếu có).
            system_prompt: System prompt tùy chỉnh.
            max_context_chars: Giới hạn ký tự context.

        Returns:
            List[dict] messages theo format DeepSeek/OpenAI:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
            ]
        """
        # ── Extract từ RerankResult nếu có ──
        if rerank_result is not None:
            documents = rerank_result.documents
            metadatas = rerank_result.metadatas
            scores = rerank_result.scores

        # ── Build context block ──
        has_context = documents and len(documents) > 0

        if has_context:
            context_block = RAGPromptBuilder.build_context_block(
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                scores=scores or [0.0] * len(documents),
                max_context_chars=max_context_chars,
            )

            user_content = (
                f"{context_block}\n\n"
                f"=== CÂU HỎI CỦA SINH VIÊN ===\n"
                f"{query}\n\n"
                f"Hãy trả lời câu hỏi trên dựa trên các tài liệu tham khảo được cung cấp."
            )
        else:
            # Không có tài liệu phù hợp
            user_content = (
                f"{NO_CONTEXT_RESPONSE_INSTRUCTION}\n\n"
                f"=== CÂU HỎI CỦA SINH VIÊN ===\n"
                f"{query}"
            )

        # ── Build messages (DeepSeek format) ──
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        logger.debug(
            f"RAGPromptBuilder | has_context={has_context}, "
            f"num_docs={len(documents) if documents else 0}, "
            f"query='{query[:80]}...'"
        )

        return messages

    @staticmethod
    def estimate_tokens(messages: list[dict[str, str]]) -> int:
        """
        Ước lượng số tokens cho messages (xấp xỉ, ~4 chars/token cho tiếng Việt).

        DeepSeek sử dụng tokenizer riêng nhưng tỷ lệ ~3-5 chars/token
        cho tiếng Việt là ước lượng hợp lý.

        Args:
            messages: Danh sách messages.

        Returns:
            Estimated token count.
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4  # ~4 chars per token for Vietnamese


# ═══════════════════════════════════════════════════════════════════════
# HELPER — Extract source info từ metadata
# ═══════════════════════════════════════════════════════════════════════

def _extract_source_info(metadata: dict) -> str:
    """
    Trích xuất thông tin nguồn từ metadata để hiển thị trong context.

    Hỗ trợ các trường metadata phổ biến từ document_loader:
        - source_file: Tên file gốc
        - page_number / page: Số trang (PDF)
        - chunk_index: Vị trí chunk trong document
        - section: Tên section/heading

    Args:
        metadata: Dict metadata từ ChromaDB/BM25.

    Returns:
        Chuỗi mô tả nguồn, ví dụ: "Nguồn: quy_che.pdf | Trang: 5"
    """
    if not metadata:
        return "Nguồn: không xác định"

    parts = []

    # Source file
    source = metadata.get("source_file") or metadata.get("source", "")
    if source:
        parts.append(f"Nguồn: {source}")

    # Page number
    page = metadata.get("page_number") or metadata.get("page")
    if page is not None:
        parts.append(f"Trang: {page}")

    # Section
    section = metadata.get("section") or metadata.get("heading", "")
    if section:
        parts.append(f"Mục: {section}")

    # Chunk index
    chunk_idx = metadata.get("chunk_index")
    if chunk_idx is not None:
        parts.append(f"Đoạn: {chunk_idx}")

    return " | ".join(parts) if parts else "Nguồn: không xác định"


# ═══════════════════════════════════════════════════════════════════════
# DEEPSEEK PROVIDER — DeepSeek V4 Flash via OpenAI-compatible SDK
# ═══════════════════════════════════════════════════════════════════════

class DeepSeekProvider:
    """
    DeepSeek V4 Flash LLM provider.

    Sử dụng OpenAI SDK (package: openai) với base_url đổi sang DeepSeek.
    API format: messages với role="system"/"user"/"assistant" và content="...".

    Attributes:
        _client: OpenAI client configured cho DeepSeek API.
        _model: Tên model (mặc định "deepseek-flash").

    Ví dụ:
        provider = DeepSeekProvider(
            api_key="sk-xxx",
            model="deepseek-flash",
        )
        text = provider.generate(
            messages=[{"role": "user", "content": "Hello"}],
        )
    """

    def __init__(self, api_key: str, model: str = "deepseek-flash") -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self._model = model
        logger.info(
            f"DeepSeekProvider initialized | model={model}"
        )

    @property
    def provider_name(self) -> str:
        """Tên provider."""
        return "deepseek"

    @property
    def model_name(self) -> str:
        """Tên model đang sử dụng."""
        return self._model

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = settings.TEMPERATURE,
        max_tokens: int = settings.MAX_TOKENS_OUTPUT,
        user_id: int | None = None,
    ) -> str:
        """
        Gọi DeepSeek API và trả về response text.

        Messages sử dụng OpenAI format:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
            ]

        Args:
            messages: List of message dicts ở OpenAI format.
            temperature: Sampling temperature (0.0 - 2.0).
            max_tokens: Max output tokens.

        Returns:
            Response text từ DeepSeek.

        Raises:
            Exception: Các lỗi từ API (rate limit, network, ...).
        """
        extra_body = {}
        if user_id:
            extra_body["user_id"] = str(user_id)
            
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body if extra_body else None,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            error_str = str(e).lower()
            # Log chi tiết cho quota/rate limit errors
            if any(keyword in error_str for keyword in [
                "429", "rate_limit", "quota",
                "too many requests", "rate limit",
            ]):
                logger.warning(
                    f"DeepSeek rate limit error: {e}"
                )
            raise

    def ask(
        self,
        query: str,
        rerank_result: Any = None,
        documents: list[str] | None = None,
        metadatas: list[dict] | None = None,
        scores: list[float] | None = None,
        temperature: float = 0.2,
        max_tokens: int = settings.MAX_TOKENS_OUTPUT,
    ) -> str:
        """
        High-level RAG answer: nhận query + kết quả re-ranking → trả lời.

        Đây là method cấp cao nhất, kết hợp:
            1. RAGPromptBuilder.build_rag_messages() → tạo messages
            2. self.generate() → gọi DeepSeek API

        Pipeline đầy đủ:
            Query → HybridRetriever.search() → GroqReranker.rerank()
                  → DeepSeekProvider.ask() → Answer

        Args:
            query: Câu hỏi gốc của sinh viên.
            rerank_result: RerankResult từ GroqReranker (ưu tiên).
            documents: Danh sách documents (nếu không dùng rerank_result).
            metadatas: Danh sách metadata (nếu không dùng rerank_result).
            scores: Danh sách scores (nếu không dùng rerank_result).
            temperature: Sampling temperature (mặc định 0.2 cho RAG).
            max_tokens: Max output tokens.

        Returns:
            Câu trả lời từ DeepSeek.

        Ví dụ:
            # Từ rerank_result:
            answer = provider.ask(
                query="Điều kiện tốt nghiệp?",
                rerank_result=rerank_result,
            )

            # Từ raw documents:
            answer = provider.ask(
                query="Học phí bao nhiêu?",
                documents=["Học phí 2024: 15 triệu/kỳ..."],
                metadatas=[{"source_file": "hoc_phi.pdf"}],
                scores=[9.5],
            )
        """
        # ── Build messages ──
        messages = RAGPromptBuilder.build_rag_messages(
            query=query,
            rerank_result=rerank_result,
            documents=documents,
            metadatas=metadatas,
            scores=scores,
        )

        # ── Log token estimate ──
        estimated_tokens = RAGPromptBuilder.estimate_tokens(messages)
        logger.info(
            f"DeepSeekProvider.ask() | query='{query[:60]}...' | "
            f"estimated_input_tokens≈{estimated_tokens}, "
            f"temperature={temperature}"
        )

        # ── Generate ──
        return self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
