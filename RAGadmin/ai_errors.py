import json

import httpx


def explain_ai_error(exc):
    """Không đưa nội dung phản ánh, raw response hoặc secret vào log/thông báo."""
    if isinstance(exc, httpx.ConnectError):
        return "AI_CONNECTION", "Không kết nối được dịch vụ AI. Hãy kiểm tra kết nối mạng và URL dịch vụ."
    if isinstance(exc, httpx.TimeoutException):
        return "AI_TIMEOUT", "Dịch vụ AI chưa phản hồi trong thời gian cho phép. Tăng AI_TIMEOUT trong .env rồi thử lại."
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return "AI_HTTP_401", "Khóa API không hợp lệ hoặc hết hạn. Kiểm tra DEEPSEEK_API_KEY hoặc GEMINI_API_KEY trong .env."
        if status == 403:
            return "AI_HTTP_403", "Bị từ chối truy cập (403). Kiểm tra quyền hạn của API key hoặc tài khoản."
        if status == 404:
            return "AI_HTTP_404", "Không tìm thấy model hoặc endpoint. Kiểm tra CHAT_MODEL và EMBED_MODEL trong .env."
        if status == 429:
            return "AI_HTTP_429", "Vượt quá giới hạn lượt gọi (Rate limit / Quota). Vui lòng chờ giây lát rồi thử lại."
        return f"AI_HTTP_{status}", f"Dịch vụ AI trả mã lỗi HTTP {status}. Vui lòng kiểm tra log hoặc cấu hình."
    if isinstance(exc, (ValueError, KeyError, TypeError, json.JSONDecodeError)):
        return "AI_RESPONSE_INVALID", "Model trả cấu trúc hoặc nguồn không hợp lệ sau khi kiểm tra. Thử lại; nếu lặp lại hãy gửi mã lỗi này và tên model."
    return "AI_UNEXPECTED", "Có lỗi xử lý phản hồi AI. Gửi mã lỗi này và tên model để kiểm tra."
