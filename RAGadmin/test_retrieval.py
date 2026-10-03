"""
Test retrieval pipeline:
  1. Load cấu hình từ .env
  2. Khởi tạo Provider (Gemini / DeepSeek)
  3. Load mock reports
  4. Tạo SearchIndex (semantic embedding)
  5. Chạy search với nhiều câu truy vấn mẫu
  6. In kết quả
"""
import sys
from pathlib import Path

# Thêm thư mục project vào sys.path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from dotenv import load_dotenv
load_dotenv(BASE / ".env")

from config import Settings
from sources import FileReportSource
from providers import get_provider
from index import SearchIndex

# ── màu terminal ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def sep(title=""):
    line = "─" * 60
    if title:
        print(f"\n{BOLD}{CYAN}{line}{RESET}")
        print(f"{BOLD}{CYAN}  {title}{RESET}")
        print(f"{BOLD}{CYAN}{line}{RESET}")
    else:
        print(f"{CYAN}{line}{RESET}")

def ok(msg):  print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET} {msg}")
def err(msg):  print(f"  {RED}✗{RESET} {msg}")

# ── 1. Config ────────────────────────────────────────────────────────────────────
sep("1. Đọc cấu hình .env")
settings = Settings.from_env()
print(f"  AI_MODE       = {settings.ai_mode}")
print(f"  EMBED_MODEL   = {settings.embed_model}")
print(f"  CHAT_MODEL    = {settings.chat_model}")
print(f"  AI_TIMEOUT    = {settings.timeout}s")

# ── 2. Kết nối Provider ─────────────────────────────────────────────────────────
sep("2. Kiểm tra Provider")
provider = get_provider(settings)
if not provider:
    err("Không khởi tạo được Provider!")
    sys.exit(1)
ok(f"Provider: {provider.__class__.__name__}")

# ── 3. Load dữ liệu ──────────────────────────────────────────────────────────────
sep("3. Load dữ liệu báo cáo")
try:
    source = FileReportSource(settings.reports_path)
    reports = list(source.load_reports())
    ok(f"Đã load {len(reports)} report từ {settings.reports_path.name}")
    if reports:
        r0 = reports[0]
        print(f"  Ví dụ report đầu tiên:")
        print(f"    ID={r0.report_id} | Tòa={r0.building} | Loại={r0.category}")
        print(f"    Nội dung: {r0.raw_text[:80]}...")
except Exception as e:
    err(f"Không load được data: {e}")
    sys.exit(1)

# ── 4. Test Embedding ────────────────────────────────────────────────────────────
sep(f"4. Test Embedding ({settings.embed_model})")
try:
    test_texts = [
        "Wi-Fi H1 bị mất kết nối",
        "Thang máy tòa H3 hỏng",
        "Máy chiếu phòng học không lên",
    ]
    vectors = provider.embed(test_texts)
    ok(f"Embedding thành công — dim={len(vectors[0])}")
    for txt, vec in zip(test_texts, vectors):
        print(f"    '{txt}' → vector[{len(vec)}] (3 giá trị đầu: {vec[:3]})")
except Exception as e:
    err(f"Embedding thất bại: {e}")
    sys.exit(1)

# ── 5. Tạo SearchIndex ───────────────────────────────────────────────────────────
sep("5. Xây dựng SearchIndex (semantic + lexical)")
try:
    index = SearchIndex(tuple(reports), provider)
    ok(f"SearchIndex sẵn sàng — {len(index.docs)} chunks, {len(index.idf)} unique terms")
    ok(f"Vectors: {len(index.vectors)} vectors đã được embed")
except Exception as e:
    err(f"Tạo SearchIndex thất bại: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── 6. Chạy các câu truy vấn test ────────────────────────────────────────────────
sep("6. Test Semantic Retrieval")
all_ids = {r.report_id for r in reports}
by_id   = {r.report_id: r for r in reports}

test_queries = [
    ("Mạng wifi yếu ở H1",                {"expected_category": "NETWORK",   "building": "H1"}),
    ("Thang máy bị kẹt rung lắc",         {"expected_category": "ELEVATOR",  "building": None}),
    ("Máy chiếu mờ không lên hình",       {"expected_category": "PROJECTOR", "building": None}),
    ("Điều hòa chảy nước nóng quá",       {"expected_category": "FACILITY",  "building": None}),
    ("Học online bị ngắt kết nối liên tục", {"expected_category": "NETWORK", "building": None}),
]

passed = 0
for q, meta in test_queries:
    print(f"\n  Câu hỏi: {BOLD}'{q}'{RESET}")
    result_ids = index.search(q, all_ids, top_k=3, provider=provider, min_score=settings.semantic_min_score)
    if not result_ids:
        warn(f"Không tìm thấy kết quả nào vượt ngưỡng min_score={settings.semantic_min_score}")
        continue
    top_r = by_id[result_ids[0]]
    cat_match = (top_r.category == meta["expected_category"])
    bld_match = (meta["building"] is None or top_r.building == meta["building"])
    mark = f"{GREEN}PASS{RESET}" if (cat_match and bld_match) else f"{YELLOW}CHECK{RESET}"
    print(f"    Kết quả [{mark}]: Top-1 là [PA{top_r.report_id}] (Tòa {top_r.building} | {top_r.category})")
    print(f"    Nội dung: {top_r.raw_text}")
    print(f"    Top-{len(result_ids)} IDs: {[f'PA{i}' for i in result_ids]}")
    if cat_match:
        passed += 1

sep()
print(f"\n{BOLD}KẾT QUẢ RETRIEVAL:{RESET} {passed}/{len(test_queries)} truy vấn khớp đúng category kỳ vọng.")
if passed == len(test_queries):
    print(f"{GREEN}{BOLD}Retrieval pipeline hoạt động hoàn hảo!{RESET}\n")
