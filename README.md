# CampusPulse

**Biến những phản ánh rời rạc thành sự cố có thể hành động.**

CampusPulse là nền tảng tiếp nhận và quản lý sự cố trong khuôn viên trường đại học, kết nối **sinh viên** — những người trực tiếp phát hiện vấn đề — với **bộ phận vận hành** — những người cần một bức tranh tổng thể để xử lý.

Thay vì coi mỗi phản ánh là một ticket độc lập, CampusPulse tổ chức các phản ánh có liên quan thành một **Incident** chung, giúp giảm trùng lặp, làm rõ mức độ ảnh hưởng và minh bạch tiến độ xử lý.

> **Thành tích:** Dự án đạt **Giải Nhì Hackathon**. Đây là phiên bản được phát triển từ sản phẩm hackathon và đang tiếp tục được hoàn thiện.
>
> **Trạng thái dự án:** Prototype / đang phát triển. Một số ý tưởng trong tài liệu thiết kế chưa được triển khai đầy đủ; các mục bên dưới phân biệt rõ chức năng hiện có và định hướng tương lai.

---

## Mục lục

- [01. Bối cảnh và bài toán](#01-bối-cảnh-và-bài-toán)
- [02. Giải pháp của CampusPulse](#02-giải-pháp-của-campuspulse)
- [03. Các khái niệm cốt lõi](#03-các-khái-niệm-cốt-lõi)
- [04. Tính năng hiện tại](#04-tính-năng-hiện-tại)
- [05. Cơ chế hình thành và quản lý sự cố](#05-cơ-chế-hình-thành-và-quản-lý-sự-cố)
- [06. Kiến trúc hệ thống](#06-kiến-trúc-hệ-thống)
- [07. Công nghệ sử dụng](#07-công-nghệ-sử-dụng)
- [08. Cấu trúc mã nguồn](#08-cấu-trúc-mã-nguồn)
- [09. Bắt đầu với CampusPulse](#09-bắt-đầu-với-campuspulse)
- [10. API chính](#10-api-chính)
- [11. Kiểm thử](#11-kiểm-thử)
- [12. Giới hạn hiện tại](#12-giới-hạn-hiện-tại)
- [13. Định hướng phát triển](#13-định-hướng-phát-triển)
- [14. Bảo mật và đóng góp](#14-bảo-mật-và-đóng-góp)

## 01. Bối cảnh và bài toán

Trong một trường đại học, các vấn đề như mất kết nối Wi-Fi, thiết bị phòng học hỏng, mất điện hay điều kiện vệ sinh không đảm bảo có thể ảnh hưởng đến nhiều sinh viên cùng lúc.

Tuy nhiên, ở cách tiếp nhận phản ánh thông thường, **mỗi người gửi một báo cáo riêng lẻ**. Bộ phận quản trị phải đọc, đối chiếu và xác định các báo cáo nào đang nói về cùng một sự cố.

**Ví dụ:** Bốn sinh viên ở phòng 24, tòa H1 lần lượt gửi:

> - “Wi-Fi phòng 24 H1 mất rồi.”
> - “Internet H1 phòng 24 không hoạt động.”
> - “Có kết nối Wi-Fi nhưng không truy cập mạng được.”
> - “Phòng 24 vẫn chưa vào Internet được.”

Nếu quản lý theo từng ticket, nhà trường có thể nhìn thấy bốn yêu cầu riêng biệt, trong khi vấn đề thực tế chỉ là **một sự cố mạng tại một địa điểm**.

### Những khó khăn cần giải quyết

| Đối tượng | Vấn đề |
| --- | --- |
| Sinh viên | Không biết phản ánh đã được ghi nhận hoặc sự cố liên quan đang được xử lý đến đâu. |
| Bộ phận vận hành | Phải rà soát nhiều phản ánh trùng lặp, khó ưu tiên sự cố ảnh hưởng nhiều người. |
| Nhà trường | Thiếu góc nhìn tổng hợp về các sự cố đang xảy ra trong khuôn viên. |

**Câu hỏi đặt ra:** Làm thế nào để chuyển nhiều tín hiệu riêng lẻ từ cộng đồng sinh viên thành một đầu mối xử lý thống nhất?

## 02. Giải pháp của CampusPulse

CampusPulse đi theo luồng:

**Student Report → Observation → Incident Fusion → Actionable Incident → Status Tracking**

1. **Thu thập tín hiệu:** Sinh viên chọn loại vấn đề, địa điểm và mô tả tình huống.
2. **Kiểm tra dữ liệu:** Backend kiểm tra thông tin bắt buộc; dịch vụ ML có thể đánh giá mức độ phù hợp giữa loại vấn đề đã chọn và nội dung mô tả.
3. **Liên kết phản ánh:** Hệ thống lưu từng phản ánh dưới dạng `Observation` rồi tìm `Incident` đang mở có cùng khóa nhóm.
4. **Hình thành sự cố:** Khi số báo cáo hỗ trợ đạt ngưỡng quy định, sự cố được xác nhận và xuất hiện trên bảng quản trị.
5. **Xử lý tập trung:** Quản trị viên theo dõi một Incident cùng những phản ánh liên quan và cập nhật trạng thái.
6. **Phản hồi đến sinh viên:** Trạng thái của Incident được thể hiện trên các báo cáo liên quan mà sinh viên có quyền xem.

### Điểm khác biệt

CampusPulse không chỉ hỗ trợ **quản lý từng phản ánh**, mà còn xây dựng một lớp nghiệp vụ **phát hiện sự cố từ nhiều phản ánh**. Một Incident đóng vai trò đầu mối vận hành, còn các Observation là bằng chứng/tín hiệu liên quan.

> **Phạm vi triển khai hiện tại:** Thuật toán hợp nhất ở Go backend dựa trên `category + building + room`. Việc dùng thời gian và độ tương đồng ngữ nghĩa để quyết định hai phản ánh có thuộc cùng Incident hay không là **hướng phát triển**, chưa phải cơ chế fusion hiện hành.

## 03. Các khái niệm cốt lõi

| Khái niệm | Ý nghĩa |
| --- | --- |
| **Report** | Bản phản ánh sinh viên gửi qua giao diện/API. |
| **Observation** | Biểu diễn nội bộ của một Report, được lưu trong bảng `observations`. |
| **Incident** | Sự cố tổng hợp được liên kết với nhiều Observation. |
| **Incident Fusion** | Quy trình tìm hoặc tạo Incident tương ứng và liên kết Observation mới. |
| **Supporter** | Tín hiệu/báo cáo hỗ trợ một Incident; hệ thống cũng đếm số sinh viên khác nhau. |
| **Confidence** | Điểm tin cậy tính bằng quy tắc dựa trên số người hỗ trợ, số báo cáo và tín hiệu mâu thuẫn; không phải xác suất do mô hình AI dự đoán. |

**Report ≠ Incident.** Một Observation có thể được liên kết với Incident đang ở trạng thái nội bộ `EMERGING`, nhưng Incident đó chưa hiển thị trên dashboard cho đến khi đạt ngưỡng.

## 04. Tính năng hiện tại

### Dành cho sinh viên (`STUDENT`)

- Đăng ký, đăng nhập và sử dụng tài khoản với JWT.
- Gửi phản ánh bằng **nhóm vấn đề, tòa nhà, phòng và mô tả**.
- Xem các báo cáo gần đây và lịch sử báo cáo **của chính mình**.
- Tìm kiếm/lọc báo cáo theo các trường được hỗ trợ.
- API hỗ trợ xem báo cáo theo ID và xóa mềm báo cáo của chính mình; giao diện hiện tập trung vào gửi và theo dõi danh sách báo cáo.
- Theo dõi trạng thái xử lý khi Incident liên quan đã đủ điều kiện hình thành.
- Sử dụng chatbot hỏi đáp tài liệu trường học khi dịch vụ Student RAG được cấu hình và chạy.

**Giới hạn quyền:** Sinh viên không có API liệt kê Incident, không được xem báo cáo của sinh viên khác và không có API sửa nội dung báo cáo sau khi gửi.

### Dành cho quản trị viên (`STAFF`)

- Xem **Incident Dashboard** với thống kê tổng số, chưa xử lý, đang xử lý và đã xử lý.
- Xem danh sách Incident đã đạt ngưỡng cùng số lượng báo cáo, vị trí và trạng thái.
- Xem chi tiết Incident cùng các Observation liên quan.
- Tìm kiếm và lọc theo trạng thái, nhóm vấn đề, tòa nhà, phòng hoặc nội dung.
- Chuyển trạng thái xử lý Incident.
- Truy cập trợ lý AI quản trị qua giao diện chat dạng nút nổi có thể kéo thả, khi Admin RAG đã hoạt động.

### Cập nhật giao diện

Giao diện Student và Admin hiện làm mới dữ liệu định kỳ bằng **HTTP polling khoảng 3 giây**. Đây chưa phải cơ chế push theo thời gian thực qua SSE hay WebSocket.

### Nhóm vấn đề và vị trí đang hỗ trợ

**Nhóm vấn đề:** Mạng / Đường truyền, Cơ sở vật chất, Điện / Chiếu sáng, Vệ sinh / Môi trường, An ninh / An toàn, Dịch vụ sinh viên và Khác.

**Tòa nhà:** H1, H2, H3, A1. Phòng hiện được giới hạn từ `10` đến `50` trong validation của backend.

Các danh mục này hiện được định nghĩa trong mã nguồn, chưa có giao diện để quản trị viên cấu hình động.

## 05. Cơ chế hình thành và quản lý sự cố

### 5.1. Quy tắc hợp nhất hiện hành

Khi một Observation mới được tạo:

1. Backend chuẩn hóa giá trị nhóm vấn đề và tòa nhà.
2. Tìm một Incident **chưa `RESOLVED`** có cùng `category`, `building`, `room`.
3. Nếu tìm thấy, liên kết Observation mới vào Incident đó.
4. Nếu chưa có, tạo Incident nội bộ ở trạng thái `EMERGING`.
5. Ghi liên kết `SUPPORT` vào bảng `incident_observations`.
6. Đếm lại các báo cáo hỗ trợ, số người báo cáo duy nhất và cập nhật `confidence`.
7. Khi có **ít nhất 4 báo cáo `SUPPORT`**, Incident `EMERGING` chuyển sang `CONFIRMED`.

```text
Report mới
    │
    ▼
Kiểm tra dữ liệu / kiểm tra ML (khi bật)
    │
    ▼
Lưu Observation
    │
    ▼
Tìm Incident đang mở theo category + building + room
    │
    ├── Có ──────► Liên kết Observation
    │
    └── Không ───► Tạo Incident EMERGING ──► Liên kết Observation
                                                      │
                                                      ▼
                                            Cập nhật confidence
                                                      │
                                                      ▼
                                          Đạt ít nhất 4 reports?
                                              │           │
                                            Chưa          Có
                                              │           │
                                              ▼           ▼
                                           Ẩn trên     CONFIRMED
                                           dashboard   Hiển thị cho Admin
```

**Lưu ý về ngưỡng:** Điều kiện tạo Incident hiện được tính theo **số báo cáo hỗ trợ**, không bắt buộc là bốn sinh viên khác nhau. Số người gửi duy nhất được sử dụng trong cách tính `confidence`.

### 5.2. Vòng đời Incident

| Trạng thái nội bộ | Hiển thị | Ý nghĩa |
| --- | --- | --- |
| `EMERGING` | Không hiển thị | Đã có Incident nội bộ nhưng chưa đủ ngưỡng báo cáo. |
| `CONFIRMED` | 🔴 Chưa xử lý | Đã đủ ngưỡng, chờ tiếp nhận. |
| `IN_PROGRESS` | 🟡 Đang xử lý | Quản trị viên đã chuyển sang giai đoạn xử lý. |
| `RESOLVED` | 🟢 Đã xử lý | Sự cố đã được đánh dấu hoàn tất. |

Khi Incident được đánh dấu `RESOLVED`, trường `resolved_at` được cập nhật. Một phản ánh mới cùng khóa nhóm sẽ không được nối vào Incident đã giải quyết mà có thể khởi tạo Incident mới.

### 5.3. Tính nhất quán dữ liệu

Quy trình **lưu Observation → tìm/tạo Incident → liên kết → tính toán** được thực hiện trong một **PostgreSQL transaction** bằng `pgx`. Nếu một bước thất bại, transaction được rollback để tránh lưu dở dang chuỗi nghiệp vụ.

## 06. Kiến trúc hệ thống

CampusPulse gồm một ứng dụng web do Go phục vụ và ba dịch vụ Python cho các chức năng AI/ML.

```mermaid
flowchart TB
    U["Sinh viên / Quản trị viên"] --> W["Web UI<br/>HTML · CSS · Vanilla JavaScript"]
    W --> G["Go Backend<br/>Gin REST API · JWT · Business Rules"]

    G <--> PG[("PostgreSQL<br/>Có thể dùng Supabase Postgres")]

    G --> ML["ML Validation Service<br/>FastAPI · scikit-learn"]
    G --> SR["Student RAG Service<br/>FastAPI · Hybrid Retrieval"]
    G --> AR["Admin RAG Service<br/>FastAPI · Report Retrieval"]

    SR <--> VS[("ChromaDB / BM25<br/>Redis, Supabase: tùy cấu hình")]
    AR --> PG
    SR -.-> LLM["Dịch vụ AI bên ngoài<br/>theo cấu hình"]
    AR -.-> LLM
```

### Vai trò từng thành phần

**Go Backend** là trung tâm nghiệp vụ, đảm nhiệm REST API, xác thực/phân quyền, xử lý báo cáo, quản lý vòng đời Incident, transaction và kết nối tới các dịch vụ hỗ trợ.

**ML Validation Service** (`ml_service/`) sử dụng mô hình đã huấn luyện để đánh giá mức phù hợp giữa loại vấn đề và mô tả. Model được đóng gói trong file `.joblib`.

**Student RAG** (`python_service/`) phục vụ hỏi đáp tài liệu. Pipeline có truy xuất kết hợp dense/sparse, hợp nhất thứ hạng và các thành phần reranking/LLM theo cấu hình.

**Admin RAG** (`RAGadmin/`) hỗ trợ truy vấn thông tin phản ánh và Incident, có nguồn dữ liệu từ PostgreSQL hoặc dữ liệu demo. Khi kết nối qua Go, quyền `STAFF` được kiểm tra ở backend và service sử dụng khóa nội bộ.

> **Phân tách trách nhiệm:** RAG/ML và thuật toán Incident Fusion là những thành phần khác nhau. Hiện tại, semantic retrieval của chatbot **không đồng nghĩa** với việc Incident Fusion đã sử dụng semantic similarity.

## 07. Công nghệ sử dụng

| Lớp | Công nghệ | Vai trò |
| --- | --- | --- |
| Frontend | HTML5, CSS3, Vanilla JavaScript | Giao diện sinh viên và quản trị viên |
| Backend | Go, Gin | REST API và nghiệp vụ |
| Database | PostgreSQL, `pgx/pgxpool` | Lưu dữ liệu và quản lý transaction |
| Authentication | JWT (HS256), bcrypt | Xác thực và kiểm tra quyền |
| ML service | Python, FastAPI, scikit-learn, joblib | Kiểm tra mô tả/nhóm vấn đề |
| Student RAG | Python, FastAPI, ChromaDB, BM25 | Hỏi đáp trên kho tài liệu |
| Admin RAG | Python, FastAPI, PostgreSQL, truy xuất ngữ nghĩa/từ khóa | Hỗ trợ phân tích, tra cứu phản ánh |
| AI providers | Gemini, DeepSeek; Groq tùy cấu hình | Embedding, suy luận và reranking |
| Hạ tầng bổ trợ | Redis, Supabase Storage (tùy cấu hình Student RAG) | Cache và lưu trữ chỉ mục |

**Lưu ý:** Supabase được dùng như một lựa chọn hạ tầng PostgreSQL/Storage; nghiệp vụ và phân quyền API chính nằm trong Go backend, không dựa vào Supabase Auth.

## 08. Cấu trúc mã nguồn

```text
CampusPulse/
├── go_backend/
│   ├── ai/                  # HTTP clients cho ML / chatbot
│   ├── databases/           # PostgreSQL pool, migrations, transactions
│   ├── handlers/            # HTTP handlers
│   ├── middleware/          # JWT, phân quyền, content classifier
│   ├── migrations/          # SQL schema
│   ├── models/              # Domain models
│   ├── repositories/        # Truy cập dữ liệu
│   ├── services/            # Nghiệp vụ Report / Incident / Fusion
│   ├── main.go              # Khởi tạo dịch vụ và router
│   └── go.mod
├── ml_service/
│   ├── app.py               # ML REST API
│   ├── campuspulse_predictor.py
│   └── compatibility_model.joblib
├── python_service/
│   ├── api/                 # Routes và schemas
│   ├── app/                 # FastAPI app
│   ├── core/                # Cấu hình, logging, cache
│   ├── knowledge_base/      # Document loaders, embeddings, retrieval
│   ├── service/             # Chat/document services
│   └── pyproject.toml
├── RAGadmin/
│   ├── app.py               # Admin chat API
│   ├── rag.py               # Logic RAG
│   ├── sources.py           # Nguồn report: file / PostgreSQL
│   └── tests/               # Kiểm thử chatbot
├── templates/               # Các trang HTML
├── static/
│   ├── css/                 # Styles
│   └── js/                  # Logic frontend
├── scripts/                 # Script chạy/kiểm tra AI services
└── README.md
```

Các thư mục môi trường ảo, cache, dữ liệu dựng chỉ mục, Git metadata và file chứa bí mật **không phải** là thành phần cần đóng gói khi phân phối mã nguồn.

## 09. Bắt đầu với CampusPulse

### 9.1. Yêu cầu môi trường

- **Go:** phiên bản phù hợp với [`go_backend/go.mod`](go_backend/go.mod) (hiện khai báo `go 1.27.1`).
- **Python:** từ `3.12` cho Student RAG; khuyến nghị Python 3.12 cho các dịch vụ Python khác.
- **PostgreSQL:** máy cục bộ hoặc PostgreSQL được quản lý từ xa (ví dụ Supabase).
- **Git** và trình quản lý gói Python (`uv` hoặc `pip`).
- Các API key cho AI **chỉ cần thiết** nếu muốn chạy chức năng AI tương ứng.

> Các bước bên dưới mô tả cách chạy từ mã nguồn. Đây không phải quy trình triển khai production và chưa được xác nhận là có thể chạy trên mọi hệ điều hành mà không điều chỉnh.

### 9.2. Chạy ứng dụng lõi (không cần bật toàn bộ AI)

**Bước 1 — Chuẩn bị cơ sở dữ liệu PostgreSQL.**

Tạo database, ví dụ `campuspulse`, hoặc sử dụng một kết nối PostgreSQL có sẵn. Không cần chạy file SQL thủ công ở lần khởi động đầu tiên: Go backend gọi migration `go_backend/migrations/001_init.sql` khi bắt đầu.

**Bước 2 — Cấu hình backend.**

Từ thư mục gốc dự án:

```bash
cp go_backend/.env.example go_backend/.env
```

Điền các biến cần thiết trong `go_backend/.env`:

```dotenv
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/campuspulse?sslmode=disable
JWT_SECRET=REPLACE_WITH_A_LONG_RANDOM_SECRET
PORT=8080

# Có thể tắt bước kiểm tra ML đồng bộ của ObservationService
# khi chỉ muốn thử nghiệp vụ Report / Incident.
CAMPUSPULSE_ML_ENABLED=false

CAMPUSPULSE_STUDENT_AI_URL=http://127.0.0.1:8003
CAMPUSPULSE_ADMIN_AI_URL=http://127.0.0.1:8001
CAMPUSPULSE_ADMIN_AI_KEY=REPLACE_WITH_A_SEPARATE_LONG_RANDOM_KEY
CAMPUSPULSE_CHAT_TIMEOUT=60s
```

Sửa `DATABASE_URL` theo database thật. Nếu dùng PostgreSQL trên Supabase, sử dụng connection string và SSL tương ứng do dịch vụ cung cấp. **Không dùng các chuỗi placeholder làm secret thực tế.**

**Bước 3 — Chạy backend.**

```bash
cd go_backend
go mod download
go run .
```

Mở `http://localhost:8080` hoặc `http://localhost:8080/login`.

Kiểm tra hoạt động:

```bash
curl http://localhost:8080/health
```

Kết quả thành công dự kiến: `{"status":"ok"}`.

**Bước 4 — Tạo tài khoản quản trị cho môi trường phát triển.**

API đăng ký công khai chỉ tạo tài khoản `STUDENT`. Để thử Admin Dashboard trong **database phát triển**, đăng ký một tài khoản riêng rồi chạy SQL:

```sql
UPDATE users
SET role = 'STAFF'
WHERE email = 'admin@example.com';
```

Đăng xuất rồi đăng nhập lại để nhận JWT mang quyền mới. Không sử dụng cách cấp quyền thủ công này như cơ chế quản trị tài khoản ở production.

**Bước 5 — Kiểm tra các trang.**

| Đường dẫn | Chức năng |
| --- | --- |
| `/` | Giao diện Student |
| `/login` | Đăng nhập |
| `/register` | Đăng ký |
| `/admin` | Incident Dashboard |
| `/admin/reports` | Tra cứu Incident và các Report liên quan |
| `/health` | Health check Go backend |

**Lưu ý về ML trong phiên bản hiện tại:** Ngoài `CAMPUSPULSE_ML_ENABLED`, endpoint tạo Report còn dùng `ContentClassifier` với cấu hình `ML_PREDICT_URL` (mặc định hướng tới một endpoint `/api/predict` riêng). Khi dịch vụ này không phản hồi, middleware hiện cho phép request đi tiếp. Hai đường kiểm tra ML chưa được thống nhất; xem [Giới hạn hiện tại](#12-giới-hạn-hiện-tại).

### 9.3. Bật ML Validation Service (tùy chọn)

Mở terminal mới tại thư mục gốc:

```bash
bash scripts/run_ml.sh
```

Script khởi chạy FastAPI trên `http://127.0.0.1:8002`.

Kiểm tra:

```bash
curl http://127.0.0.1:8002/health
```

Trong `go_backend/.env`:

```dotenv
CAMPUSPULSE_ML_ENABLED=true
CAMPUSPULSE_ML_API_URL=http://127.0.0.1:8002
CAMPUSPULSE_ML_TIMEOUT=3s
```

Khởi động lại Go backend để áp dụng cấu hình. **Không** tùy tiện trỏ `ML_PREDICT_URL` sang `:8002/predict`: middleware cũ và ML service này hiện sử dụng response schema khác nhau.

### 9.4. Bật Student RAG (tùy chọn)

```bash
cp python_service/.env.example python_service/.env
bash scripts/run_student_ai.sh
```

Cấu hình `DEEPSEEK_API_KEY`, các biến Gemini embedding và kho tài liệu theo [`python_service/core/config.py`](python_service/core/config.py). Service mặc định chạy tại `http://127.0.0.1:8003`.

- Tài liệu phải được đưa vào chỉ mục trước khi kỳ vọng chatbot trả lời dựa trên tài liệu đó.
- Kho ChromaDB, BM25 và các lớp cache cần dữ liệu/cấu hình phù hợp.
- `python_service/main.py` chứa ví dụ nạp `data.pdf` vào vector store, nhưng **không** phải tiến trình web server.

### 9.5. Bật Admin RAG (tùy chọn)

```bash
cp RAGadmin/.env.example RAGadmin/.env
bash scripts/run_admin_ai.sh
```

Trong `RAGadmin/.env`, cấu hình các giá trị tối thiểu theo chế độ tích hợp:

```dotenv
APP_MODE=internal
DATA_MODE=postgres
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB_NAME
INTERNAL_API_KEY=REPLACE_WITH_THE_SAME_ADMIN_AI_KEY_AS_GO
AI_MODE=cloud
AI_REQUIRED=false

DEEPSEEK_API_KEY=YOUR_DEEPSEEK_KEY
GEMINI_API_KEY=YOUR_GEMINI_KEY
```

`INTERNAL_API_KEY` phải giống `CAMPUSPULSE_ADMIN_AI_KEY` ở Go backend. Admin RAG mặc định chạy tại `http://127.0.0.1:8001`. Script khởi động tích hợp hiện kiểm tra kết nối cloud AI; cần cấu hình key hợp lệ để chạy theo đường này.

### 9.6. Kiểm tra các dịch vụ hỗ trợ

Khi đã bật đủ các dịch vụ:

```bash
bash scripts/test_chat_services.sh
bash scripts/test_ml_integration.sh
```

Các script kiểm tra endpoint/khả năng kết nối. Chúng **không thay thế** kiểm thử end-to-end của toàn bộ luồng nghiệp vụ.

## 10. API chính

### Public

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Đăng ký Student |
| `POST` | `/api/auth/login` | Đăng nhập, nhận JWT |
| `GET` | `/api/options` | Danh sách nhóm vấn đề, tòa nhà, phòng |
| `GET` | `/api/ai/health` | Trạng thái kết nối ML |
| `GET` | `/health` | Kiểm tra kết nối database của backend |

### Student — yêu cầu `Authorization: Bearer <token>`

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `POST` | `/api/reports` | Tạo báo cáo |
| `GET` | `/api/reports/me` | Danh sách báo cáo của tài khoản hiện tại |
| `GET` | `/api/reports/:id` | Xem báo cáo thuộc sở hữu của mình |
| `DELETE` | `/api/reports/:id` | Xóa mềm báo cáo của mình |
| `POST` | `/api/chat/student` | Hỏi chatbot Student RAG |

### Staff — yêu cầu `Authorization: Bearer <token>`

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/api/incidents` | Danh sách Incident đã hình thành |
| `GET` | `/api/incidents/:id` | Chi tiết Incident |
| `GET` | `/api/incidents/:id/observations` | Báo cáo liên kết với Incident |
| `PATCH` | `/api/incidents/:id/status` | Thay đổi trạng thái |
| `POST` | `/api/chat/admin` | Hỏi chatbot Admin RAG |

Ví dụ tạo báo cáo (sau khi đăng nhập và lấy token):

```bash
curl -X POST http://localhost:8080/api/reports \
  -H "Authorization: Bearer YOUR_STUDENT_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Mạng / Đường truyền",
    "location": "Tòa nhà H1",
    "room": "24",
    "description": "Wi-Fi phòng 24 kết nối được nhưng không truy cập Internet."
  }'
```

Ví dụ cập nhật trạng thái Incident:

```bash
curl -X PATCH http://localhost:8080/api/incidents/1/status \
  -H "Authorization: Bearer YOUR_STAFF_JWT" \
  -H "Content-Type: application/json" \
  -d '{"status":"IN_PROGRESS"}'
```

Trạng thái hợp lệ cho thao tác quản trị: `CONFIRMED`, `IN_PROGRESS`, `RESOLVED` (hoặc nhãn tiếng Việt tương ứng). `EMERGING` không được cho phép qua API cập nhật trạng thái.

### Mô hình dữ liệu

```mermaid
erDiagram
    users ||--o{ observations : submits
    observations ||--o{ incident_observations : linked_by
    incidents ||--o{ incident_observations : contains

    users {
        int id PK
        string name
        string email
        string role
    }
    observations {
        int id PK
        int user_id FK
        string raw_text
        string category
        string building
        string room
        string status
    }
    incidents {
        int id PK
        string title
        string category
        string building
        string room
        string status
        int confidence
    }
    incident_observations {
        int incident_id PK,FK
        int observation_id PK,FK
        string relation
        decimal match_score
    }
```

Chi tiết schema nằm tại [`go_backend/migrations/001_init.sql`](go_backend/migrations/001_init.sql).

## 11. Kiểm thử

Mã nguồn hiện có các bộ kiểm thử ở nhiều module. Có thể chạy tùy theo môi trường và dependencies đã cài:

```bash
# Go unit tests
cd go_backend
go test ./...
```

```bash
# ML service tests
cd ml_service
python -m pip install -r requirements.txt -r requirements_test.txt
python -m pytest -q
```

```bash
# Admin RAG tests
cd RAGadmin
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q tests
```

Các lệnh trên là **hướng dẫn chạy test có sẵn**, không phải khẳng định toàn bộ test đã được thực thi hoặc đang pass trong mọi môi trường. Một số test và quy trình tích hợp cần dịch vụ, dữ liệu, phiên bản phụ thuộc hoặc biến môi trường tương ứng.

## 12. Giới hạn hiện tại

CampusPulse đã có luồng cốt lõi Report → Incident → Admin cập nhật → Student theo dõi, nhưng vẫn còn những giới hạn cần giải quyết trước khi đưa vào vận hành thực tế:

1. **Fusion dựa trên khóa cố định.** Hai vấn đề khác nhau nhưng cùng category/tòa/phòng có thể bị gom chung; thời gian và semantic similarity chưa được áp dụng vào quyết định fusion.
2. **Ngưỡng đếm theo report, không theo tài khoản duy nhất.** Cần chính sách chống spam/trùng lặp và chống thao túng độ tin cậy.
3. **Cập nhật bằng polling.** Chưa có SSE/WebSocket để push trạng thái và sự kiện theo thời gian thực.
4. **Hai cơ chế kiểm tra ML chưa thống nhất.** `ContentClassifier` legacy và `ObservationService` có endpoint, schema và chính sách xử lý lỗi khác nhau.
5. **Upload hình ảnh chưa hoàn thiện end-to-end.** API/schema có `image_url`, nhưng form Student hiện chưa cung cấp luồng tải ảnh hoàn chỉnh.
6. **Danh mục địa điểm hard-coded.** Chưa có cấu hình nhiều trường/cơ sở, tòa, tầng, phòng từ database.
7. **Quản trị vận hành còn cơ bản.** Chưa có workflow phân công đội xử lý, SLA, lịch sử thao tác đầy đủ và hệ thống thông báo riêng.
8. **Chưa có quy trình chuẩn production.** Cần hoàn thiện CI/CD, quản lý migration có version, quan sát hệ thống, cấu hình bảo mật và kiểm thử tích hợp.

## 13. Định hướng phát triển

Các hạng mục dưới đây là **đề xuất cho giai đoạn sau hackathon**, không phải tuyên bố chúng đã tồn tại.

### Giai đoạn 1 — Làm vững sản phẩm lõi

- [ ] Chuẩn hóa cấu trúc repository, loại bỏ môi trường ảo, dữ liệu phát sinh và cache khỏi bản phân phối.
- [ ] Hợp nhất hai đường kiểm tra ML và thống nhất chính sách fallback.
- [ ] Bổ sung unit/integration tests cho nghiệp vụ Report, Fusion, Incident và phân quyền.
- [ ] Làm rõ quy tắc đóng/mở lại Incident, xử lý xóa report sau khi đã xác nhận.
- [ ] Thêm seed data và quy trình tạo tài khoản Staff an toàn cho phát triển.
- [ ] Xây dựng tài liệu OpenAPI/Swagger, cấu hình môi trường mẫu dễ tái lập.

### Giai đoạn 2 — Tăng chất lượng nhận diện sự cố

- [ ] Kết hợp category + location + **khoảng thời gian xảy ra**.
- [ ] Nghiên cứu semantic similarity để phân biệt các sự cố cùng vị trí nhưng khác bản chất.
- [ ] Ngăn trùng lặp và cân nhắc ngưỡng theo **người báo cáo duy nhất**.
- [ ] Bổ sung cơ chế điều chỉnh/sáp nhập/tách Incident bởi quản trị viên.
- [ ] Theo dõi chất lượng fusion bằng dữ liệu kiểm thử có nhãn.

### Giai đoạn 3 — Hoàn thiện trải nghiệm vận hành

- [ ] Tải ảnh minh chứng với giới hạn loại file/dung lượng và kiểm soát truy cập.
- [ ] SSE/WebSocket hoặc cơ chế push phù hợp cho cập nhật trạng thái.
- [ ] Phân công đơn vị xử lý, mức ưu tiên, SLA và lịch sử sự kiện.
- [ ] Thông báo khi trạng thái Incident thay đổi.
- [ ] Quản lý danh mục vị trí và phòng học qua dashboard.
- [ ] Thống kê xu hướng, khu vực xảy ra nhiều sự cố và thời gian xử lý.

### Giai đoạn 4 — Sẵn sàng triển khai thực tế

- [ ] Docker Compose/dev environment có thể tái lập.
- [ ] CI/CD, logging, metrics, tracing, health/readiness checks.
- [ ] Secrets management, rate limiting, audit log và các kiểm tra bảo mật tự động.
- [ ] Kiểm thử tải, sao lưu/khôi phục PostgreSQL và chiến lược triển khai nhiều môi trường.
- [ ] Chính sách dữ liệu, quyền riêng tư, vòng đời lưu trữ báo cáo và hình ảnh.

## 14. Bảo mật và đóng góp

### Các nguyên tắc bảo mật

- Không commit `.env`, API keys, JWT secrets, mật khẩu hoặc connection strings có thông tin xác thực.
- Dùng các file `.env.example` để mô tả biến cấu hình, không chứa secret thật.
- Hạn chế quyền database và các khóa dịch vụ; không đưa `SUPABASE_SERVICE_ROLE_KEY` ra trình duyệt.
- API chính kiểm tra JWT và role ở backend. Việc ẩn nút trên giao diện **không thay thế** phân quyền server-side.
- Trước khi công bố repository, cần quét lịch sử Git để tìm thông tin nhạy cảm; nếu đã công khai secret, hãy thu hồi/đổi khóa.
- Dữ liệu phản ánh và tài liệu dùng cho RAG cần được quản lý theo quyền truy cập phù hợp.

### Đóng góp

Dự án tiếp tục phát triển sau hackathon. Có thể tham gia bằng cách mở issue mô tả lỗi/đề xuất, thảo luận phạm vi thay đổi và tạo pull request kèm giải thích, kiểm thử liên quan.

Hiện repository **chưa có file giấy phép sử dụng (`LICENSE`)**. Quyền sử dụng, phân phối và đóng góp mã nguồn cần được nhóm xác định trước khi công bố theo một giấy phép cụ thể.

---

<div align="center">

**CampusPulse — Từ tiếng nói sinh viên đến hành động của nhà trường.**

*Không chỉ thu thập phản ánh. Giúp campus hiểu điều gì đang thực sự xảy ra.*

</div>
