from fastapi import status
import uuid
from typing import Annotated
from fastapi import Depends, Request


from core.logger import get_logger

logger = get_logger(__name__)


_chat_service_instance = None
_document_service_instance = None


def get_chat_service():
    """
    Dependency trả về ChatService singleton.

    ChatService được khởi tạo 1 lần duy nhất (lazy initialization)
    và cache ở module-level. Tất cả requests share cùng instance.

    Tại sao singleton:
        - Business logic không có state per-request
        - Tránh overhead tạo mới mỗi request

    Returns:
        ChatService instance.

    Raises:
        ServiceUnavailableError: Nếu không thể khởi tạo ChatService.

    Ví dụ trong route handler:
        @router.post("/chat")
        async def chat(
            request: ChatRequest,
            service: ChatService = Depends(get_chat_service),
        ):
            return service.chat(request)
    """
    global _chat_service_instance

    if _chat_service_instance is None:
        try:
            from service.chat_service import ChatService
            _chat_service_instance = ChatService()
            logger.info("ChatService dependency initialized (singleton)")
        except Exception as e:
            logger.error(
                f"Failed to initialize ChatService: {e}",
                exc_info=True,
            )
            from core.exceptions import ServiceUnavailableError
            raise ServiceUnavailableError(
                "ChatService is not available",
                details={"error": str(e), "type": type(e).__name__},
            )

    return _chat_service_instance


def get_document_service():
    """
    Dependency trả về DocumentService singleton.

    DocumentService xử lý pipeline upload tài liệu:
    parse → embed → lưu vector store với user_id.

    Returns:
        DocumentService instance.

    Raises:
        ServiceUnavailableError: Nếu không thể khởi tạo DocumentService.
    """
    global _document_service_instance

    if _document_service_instance is None:
        try:
            from service.document_service import DocumentService
            _document_service_instance = DocumentService()
            logger.info("DocumentService dependency initialized (singleton)")
        except Exception as e:
            logger.error(
                f"Failed to initialize DocumentService: {e}",
                exc_info=True,
            )
            from core.exceptions import ServiceUnavailableError
            raise ServiceUnavailableError(
                "DocumentService is not available",
                details={"error": str(e), "type": type(e).__name__},
            )

    return _document_service_instance



from service.chat_service import ChatService
from service.document_service import DocumentService

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]