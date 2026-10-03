"""
Test LLM pipeline (DeepSeek / Gemini):
  1. plan()   — LLM hiểu câu hỏi → QueryPlan
  2. answer() — LLM sinh câu trả lời từ evidence
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from dotenv import load_dotenv
load_dotenv(BASE / ".env")

from config import Settings
from sources import FileReportSource
from providers import get_provider
from index import SearchIndex

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def sep(title=""):
    line = "─" * 60
    print(f"\n{BOLD}{CYAN}{line}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{line}{RESET}")

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET} {msg}")
def err(msg):  print(f"  {RED}✗ {msg}{RESET}")

# ── Setup ────────────────────────────────────────────────────────────────────────
settings = Settings.from_env()
provider = get_provider(settings)
if not provider:
    err("Không khởi tạo được Provider!")
    sys.exit(1)

source   = FileReportSource(settings.reports_path)
reports  = tuple(source.load_reports())
index    = SearchIndex(reports, provider)
all_ids  = {r.report_id for r in reports}
by_id    = {r.report_id: r for r in reports}

print(f"\n{BOLD}Provider:{RESET} {provider.__class__.__name__} | {BOLD}Chat Model:{RESET} {settings.chat_model} | {BOLD}Timeout:{RESET} {settings.timeout}s")

# ── TEST 1: plan() ───────────────────────────────────────────────────────────────
sep("TEST 1: LLM plan() — hiểu câu hỏi")

plan_queries = [
    "Wi-Fi tòa H1 bị mất kết nối",
    "Thang máy H2 hỏng ở tầng mấy?",
    "Có bao nhiêu phản ánh về máy chiếu?",
    "Tóm tắt tình trạng điều hòa H3",
]

plan_ok = 0
for q in plan_queries:
    print(f"\n  Query: \"{q}\"")
    try:
        result = provider.plan(q)
        ok(f"plan() thành công")
        print(f"    kind={result.kind}  buildings={result.buildings}  "
              f"categories={result.categories}  search_text={result.search_text!r}")
        plan_ok += 1
    except Exception as e:
        err(f"plan() thất bại: {type(e).__name__}: {e}")

print(f"\n  Kết quả plan: {plan_ok}/{len(plan_queries)} thành công")

# ── TEST 2: answer() ─────────────────────────────────────────────────────────────
sep("TEST 2: LLM answer() — sinh câu trả lời từ evidence")

answer_queries = [
    "Wi-Fi H1 bị mất kết nối như thế nào?",
    "Thang máy tòa H2 có vấn đề gì?",
]

answer_ok = 0
for q in answer_queries:
    print(f"\n  Query: \"{q}\"")
    try:
        # Retrieval
        ids = index.search(q, all_ids, top_k=3, provider=provider,
                           min_score=settings.semantic_min_score)
        selected = [by_id[i] for i in ids]
        print(f"  Đã lấy {len(selected)} evidence: IDs={ids}")

        if not selected:
            warn("Không có evidence để test answer()")
            continue

        # LLM answer
        result = provider.answer(q, selected)
        ok(f"answer() thành công")
        print(f"\n  {BOLD}Câu trả lời:{RESET}")
        for line in result["answer"].split("\n\n"):
            print(f"    {line}")
        print(f"\n  report_ids dẫn nguồn: {result['report_ids']}")
        answer_ok += 1

    except Exception as e:
        err(f"answer() thất bại: {type(e).__name__}: {e}")

print(f"\n  Kết quả answer: {answer_ok}/{len(answer_queries)} thành công")

# ── Tóm tắt ─────────────────────────────────────────────────────────────────────
sep("Tóm tắt")
total = plan_ok + answer_ok
total_max = len(plan_queries) + len(answer_queries)
status = GREEN + "PASS" if total == total_max else (YELLOW + "PARTIAL" if total > 0 else RED + "FAIL")
print(f"  {status}{RESET}: {total}/{total_max} test thành công\n")
