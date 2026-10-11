# CampusPulse — Go + ML Validation + Student RAG + Admin RAG

CampusPulse hiện chạy 4 service song song:

- **Go web/backend**: `http://127.0.0.1:8080`
- **Admin RAG**: `http://127.0.0.1:8001`
- **ML Type/Description validation**: `http://127.0.0.1:8002`
- **Student document RAG**: `http://127.0.0.1:8003`

## AI pipelines đã được nối thật

### 1. Kiểm tra Type × Description khi student gửi report

```text
Student submit report
    -> Go validate input
    -> ML :8002 /predict
    -> mismatch: 422, không ghi DB, không Fusion
    -> match: transaction -> observation -> Fusion -> incident
```

Model: `ml_service/compatibility_model.joblib`.

### 2. Student chatbot

```text
Student UI
    -> JWT STUDENT
    -> Go POST /api/chat/student
    -> Student RAG :8003 POST /api/chat
    -> ChromaDB + BM25 + reranker fallback
    -> DeepSeek sinh câu trả lời dựa trên tài liệu trường
```

Frontend không còn dùng `getBotReply()` hard-code.

### 3. Admin chatbot

```text
Admin UI
    -> JWT STAFF
    -> Go POST /api/chat/admin
    -> Admin RAG :8001
    -> đọc PostgreSQL/Supabase live
    -> Gemini retrieval + DeepSeek / deterministic statistics
```

Frontend không còn trả lời incident bằng if/else demo. Admin RAG dùng dữ liệu thật từ
`observations`, `incidents`, `incident_observations`. Chỉ incident đủ 4 SUPPORT reports
được coi là incident đã hình thành.

---

## Chuẩn bị môi trường

Không commit file `.env` thật.

### Go backend

```bash
cp go_backend/.env.example go_backend/.env
```

Điền `DATABASE_URL`, `JWT_SECRET` và một internal key dài. Ví dụ:

```ini
CAMPUSPULSE_ADMIN_AI_KEY=your-long-random-internal-key
```

### Admin RAG

```bash
cp RAGadmin/.env.example RAGadmin/.env
```

- `DATABASE_URL` phải trỏ tới cùng DB với Go.
- `INTERNAL_API_KEY` phải **giống hệt** `CAMPUSPULSE_ADMIN_AI_KEY` của Go.
- Điền `DEEPSEEK_API_KEY` và `GEMINI_API_KEY` nếu dùng `AI_MODE=cloud`.

### Student RAG

```bash
cp python_service/.env.example python_service/.env
```

Điền `DEEPSEEK_API_KEY` và `GEMINI_API_KEY`.

**Không đổi `EMBEDDING_MODEL=gemini-embedding-2` nếu đang dùng ChromaDB đi kèm ZIP này**, vì index hiện có được tạo ở 3072 chiều bằng model đó.

---

## Chạy hệ thống

Mở 4 terminal.

### Terminal 1 — ML validation :8002

```bash
./scripts/run_ml.sh
```

### Terminal 2 — Admin RAG :8001

```bash
./scripts/run_admin_ai.sh
```

### Terminal 3 — Student RAG :8003

```bash
./scripts/run_student_ai.sh
```

### Terminal 4 — Go :8080

```bash
cd go_backend
go run .
```

Mở web:

```text
http://127.0.0.1:8080/login
```

---

## Health checks

```bash
./scripts/test_chat_services.sh
```

Hoặc:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/ai/health
```

## Lưu ý Student RAG

ZIP đã chứa `python_service/data/chroma_db` được index sẵn. Nếu bạn thay tài liệu nguồn
hoặc muốn rebuild index, hãy dùng `DocumentService`/pipeline trong `python_service` để
index lại. Query embedding phải dùng cùng embedding model/dimension với index.

## Lưu ý Admin RAG

`DATA_MODE=postgres` đọc dữ liệu trực tiếp từ DB trước mỗi câu hỏi Admin, vì vậy trạng
thái incident vừa đổi ở Go sẽ được chatbot nhìn thấy ở lần hỏi tiếp theo. `AI_REQUIRED=false`
cho phép fallback an toàn về rule/lexical nếu cloud AI tạm lỗi; đặt `true` nếu demo yêu cầu
AI cloud phải hoạt động và muốn trả 503 thay vì fallback.
