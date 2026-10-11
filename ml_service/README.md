# CampusPulse ML API

Đây là dịch vụ FastAPI dùng đúng model trong file bạn đã gửi:
`Type × TFIDF | LR C=10`, ngưỡng `0.5`.

Backend project gửi `Type` và `Describe` qua HTTP; API trả nhãn và P(1).
Toàn bộ model, hàm dự đoán và lớp TF-IDF đã có trong gói.

## 1. Chạy trên Windows PowerShell

Giải nén ZIP, mở thư mục bằng VS Code và mở Terminal PowerShell ngay trong thư
mục có `app.py`. Dùng Python 3.11–3.13; gói đã được kiểm tra bằng Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8002
```

Giữ Terminal này mở. Khi xuất hiện `Application startup complete`, mở:

- Trang thử API: <http://127.0.0.1:8002/docs>
- Kiểm tra API/model sẵn sàng: <http://127.0.0.1:8002/health>
- Danh sách nhóm: <http://127.0.0.1:8002/types>

Tại `/docs`, mở **POST /predict → Try it out**, nhập JSON sau rồi bấm **Execute**:

```json
{
  "Type": "Mạng và đường truyền",
  "Describe": "wifi tầng 4 bắt được mà load mãi không xong"
}
```

API trả HTTP 200 với kết quả:

```json
{
  "type": "Mạng và đường truyền",
  "describe": "wifi tầng 4 bắt được mà load mãi không xong",
  "label": 1,
  "is_match": true,
  "probability": 0.9981916096259621,
  "threshold": 0.5,
  "model": "Type × TFIDF | LR C=10"
}
```

## 2. Chạy trên WSL/Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8002
```

## 3. Các endpoint

| Method | Đường dẫn | Chức năng |
|---|---|---|
| GET | `/health` | Model đã nạp và API sẵn sàng |
| GET | `/types` | Sáu Type hợp lệ |
| POST | `/predict` | Kiểm tra một cặp Type/Describe |
| POST | `/predict/batch` | Kiểm tra 1–256 cặp trong một request |
| GET | `/docs` | Trang thử API |
| GET | `/openapi.json` | Hợp đồng API cho công cụ tích hợp |

`/predict` nhận khóa `Type`, `Describe`; cũng chấp nhận `type`, `describe`.
Cả hai giá trị phải là chuỗi. Mô tả tối đa 10.000 ký tự và không được trống.
Type được chuẩn hóa chữ hoa/thường, khoảng trắng và alias `Mạng / đường truyền`.
Các khóa thừa, ví dụ `Label`, bị từ chối.

- `label=1`, `is_match=true`: mô tả phù hợp với Type được truyền vào.
- `label=0`, `is_match=false`: mô tả không phù hợp với Type được truyền vào.
- `probability`: P(1) của model; không phải xác suất đã được hiệu chuẩn độc lập.
- `threshold`: ngưỡng đã lưu trong model, giữ nguyên `0.5`.

Đầu vào thiếu/sai Type/rỗng/sai kiểu dữ liệu trả HTTP **422** với trường `detail`.
Nhãn `0` vẫn trả HTTP **200**, vì đây là dự đoán hợp lệ.
Model thiếu hoặc thư viện scikit-learn không khớp sẽ làm dịch vụ báo lỗi lúc
khởi động. Dùng đúng `requirements.txt` và giữ các file đi kèm cùng thư mục.

Request nhiều câu:

```json
{
  "items": [
    {"Type": "Vệ sinh / môi trường", "Describe": "nvs tầng 5 hết nước từ sáng"},
    {"Type": "Cơ sở vật chất", "Describe": "nvs tầng 5 hết nước từ sáng"}
  ]
}
```

Kết quả có `count` và `results`, giữ nguyên thứ tự đầu vào.

## 4. Gọi từ backend Node.js

File `examples/ml_client.mjs` có sẵn hàm HTTP client, dùng Node.js 18+.
Khi API đang chạy, mở Terminal thứ hai và chạy:

```powershell
node examples/ml_client.mjs
```

Copy file client vào project Node.js và import theo đường dẫn thực tế:

```javascript
import { predictIssue } from "./ml_client.mjs";

// Lấy hai giá trị này từ form phản ánh trong project.
const result = await predictIssue(
  "An ninh / an toàn",
  "để mũ ở xe lúc quay lại không thấy đâu"
);

console.log(result.label, result.probability);
```

Backend gửi dữ liệu thực từ form vào hai tham số này. Hàm client có timeout
10 giây và báo lỗi khi API trả mã HTTP lỗi. Không chuyển lỗi API thành nhãn 0.

Nếu API ở địa chỉ khác, cấu hình URL trước khi chạy backend:

```powershell
$env:CAMPUSPULSE_ML_API_URL = "http://127.0.0.1:8002"
```

Phía client chỉ cần địa chỉ HTTP và hợp đồng JSON; các file model nằm ở dịch vụ API.

## 5. Gọi từ backend Python hoặc PowerShell

File `examples/client_python.py` dùng thư viện chuẩn Python:

```powershell
.\.venv\Scripts\python.exe examples/client_python.py
```

Hoặc gửi request trực tiếp trong PowerShell, ở Terminal thứ hai:

```powershell
$body = @{
    Type = "Mạng và đường truyền"
    Describe = "wifi tầng 4 bắt được mà load mãi không xong"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8002/predict" -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

## 6. Gọi từ frontend và CORS

Nếu frontend gọi API trực tiếp từ trình duyệt, cho phép đúng địa chỉ frontend
trước khi khởi động API. Ví dụ frontend Vite chạy ở `http://localhost:5173`:

```powershell
$env:CAMPUSPULSE_CORS_ORIGINS = "http://localhost:5173"
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8002
```

Nhiều địa chỉ phân cách bằng dấu phẩy. `localhost` và `127.0.0.1` là hai origin
khác nhau; dùng đúng địa chỉ đang mở frontend. CORS mặc định không được bật.
Lời gọi giữa hai backend không cần cấu hình CORS.

Frontend có thể dùng `fetch`:

```javascript
const response = await fetch("http://127.0.0.1:8002/predict", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ Type: selectedType, Describe: description }),
});
const result = await response.json();
if (!response.ok) throw new Error(JSON.stringify(result.detail));
```

## 7. Chạy bằng Docker

Docker Desktop cần đang chạy. Tại thư mục gói API:

```powershell
docker compose up --build -d
docker compose logs -f campuspulse-ml-api
```

Trang thử vẫn là <http://127.0.0.1:8002/docs>. Chọn chạy Docker hoặc Python để
tránh hai dịch vụ cùng dùng cổng 8001. Dockerfile đã có model và healthcheck.

```powershell
docker compose down
```

Khi thêm dịch vụ vào cùng Compose với backend, backend dùng URL
`http://campuspulse-ml-api:8001`. Địa chỉ `127.0.0.1` trong mỗi container trỏ về
chính container đó.

Dockerfile được cung cấp để chạy trên máy bạn. Môi trường kiểm tra hiện tại
không có Docker nên chưa build/run image; dịch vụ Python và HTTP đã được kiểm tra.

## 8. Cấu trúc chính và vận hành

- `app.py`: endpoint FastAPI, kiểm tra đầu vào và nạp model lúc khởi động.
- `campuspulse_predictor.py`: gọi pipeline để dự đoán.
- `campuspulse_type_features.py`: lớp đặc trưng được model tham chiếu tới.
- `compatibility_model.joblib`: model gốc bạn đã train, không huấn luyện lại.
- `requirements_model.txt`: phiên bản thư viện model từ ZIP gốc.
- `requirements.txt`: thư viện model và API.
- `Dockerfile`, `compose.yaml`: chạy API bằng Docker.
- `examples/`: ví dụ client Node.js/Python.
- `test_api.py`: kiểm tra HTTP, dữ liệu sai, CORS và model startup.

Model được nạp một lần cho mỗi process API bằng lifespan của FastAPI. Request
chỉ transform/predict; không fit lại TF-IDF và không huấn luyện lại. Khi thay
model, khởi động lại dịch vụ. Nếu chạy nhiều workers, mỗi worker nạp một bản.

Có thể đặt `CAMPUSPULSE_MODEL_PATH` để dùng model ở đường dẫn khác. File đặc
trưng vẫn phải giữ đúng phiên bản tương ứng với model.

API kiểm tra một Type đã chọn. Nếu cùng mô tả được chấp nhận ở nhiều Type,
API giữ nguyên hành vi đó; không ép chọn top 1. Các lỗi ngữ nghĩa còn có ở
model, ví dụ câu mất mũ bị chấp nhận ở một số nhóm sai, vẫn cần xử lý ở bước
cải thiện model.

Để chạy kiểm tra:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_test.txt
.\.venv\Scripts\python.exe test_api.py
```

Tài liệu chính thức dùng cho cách đóng gói:

- <https://fastapi.tiangolo.com/advanced/events/>
- <https://fastapi.tiangolo.com/tutorial/body/>
- <https://fastapi.tiangolo.com/tutorial/cors/>
