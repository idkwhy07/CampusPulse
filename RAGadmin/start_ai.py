"""Chạy trên máy người dùng: kết nối Cloud AI (Gemini Embedding + DeepSeek LLM), kiểm tra rồi mở app."""
import os
import subprocess
import sys
from dotenv import load_dotenv

from config import BASE, Settings
from providers import get_provider


def main():
    load_dotenv(BASE / ".env")
    env_ai_mode = os.getenv("AI_MODE", "").lower()
    if env_ai_mode not in {"cloud", "deepseek", "offline"}:
        os.environ["AI_MODE"] = "cloud"

    # Mặc định cho phép lùi về quy tắc/từ khóa kèm cảnh báo; đặt AI_REQUIRED=true trong .env nếu muốn nghiêm ngặt.
    os.environ.setdefault("AI_REQUIRED", "false")
    os.environ.setdefault("AI_TIMEOUT", "60")
    settings = Settings.from_env()
    settings.validate()

    print("Kiểm tra kết nối Gemini Embedding & DeepSeek LLM...", flush=True)

    provider = get_provider(settings)
    if not provider:
        raise RuntimeError(f"Không khởi tạo được provider cho AI_MODE={settings.ai_mode}")

    print("  - Đang kiểm tra Gemini Embedding API...", flush=True)
    provider.embed(["Wi-Fi H1 bị mất kết nối"])
    print("  - Đang kiểm tra DeepSeek LLM Planner API...", flush=True)
    provider.plan("Tìm các phản ánh mạng chập chờn ở H1")

    mode_label = f"Gemini Embedding ({settings.embed_model}) + DeepSeek LLM ({settings.chat_model})"
    print(f"AI đã kết nối thành công ({mode_label}). Mở http://127.0.0.1:8001 | Ctrl+C để dừng.", flush=True)
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8001"],
                   cwd=BASE, check=True, env=os.environ.copy())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"\nKHÔNG BẬT ĐƯỢC AI: {exc}\nKhông tự động chuyển sang lexical.", file=sys.stderr)
        sys.exit(1)
