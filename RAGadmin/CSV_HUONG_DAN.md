# RAG admin — nhận CSV của Tuấn

Bản cập nhật đọc được CSV và JSON. File mẫu `data/rag_knowledge.csv` có 28 phản ánh, liên kết với 7 sự cố. Dữ liệu gửi ngày 02/10/2026; hỏi ngày 03/10/2026 sẽ được 0 phản ánh.

## Chạy

Gói dự án đã trỏ `REPORTS_PATH` trong `.env` sang `data/rag_knowledge.csv`. Giữ các khóa AI của bạn. Nếu chép riêng thư mục RAGadmin vào dự án khác, sửa dòng này trong `.env`:

```ini
REPORTS_PATH=data/rag_knowledge.csv
```

Chạy `run_ai.bat` như trước. Nếu chỉ kiểm tra đọc dữ liệu và thống kê bằng quy tắc, đặt `AI_MODE=offline`, `AI_REQUIRED=false` rồi chạy `run_demo.bat`. Các câu hỏi tự nhiên phức tạp vẫn cần AI cloud hoạt động. File này được coi là dữ liệu mẫu theo thông tin bạn cung cấp; khi dùng dữ liệu thật, cấu hình `APP_MODE=internal`, `DATA_MODE=file` và khóa nội bộ như cơ chế sẵn có.

Sau khi thay file CSV, khởi động lại hoặc gọi `POST /internal/admin/sync` để nạp lại. Nếu đồng bộ lỗi, snapshot cũ được giữ.

## Lỗi tiêu đề trong file mẫu

Hai cột cuối hiện có tiêu đề `confidence,created_at`, nhưng dữ liệu thực tế là thời gian gửi và văn bản tổng hợp. Bộ đọc chỉ tự nhận diện trường hợp này khi đúng bộ tiêu đề mẫu, cột cuối bắt đầu bằng `Report #`, và cột `confidence` chứa thời gian hợp lệ. Có ghi cảnh báo trong terminal.

Đề nghị phía xuất CSV sửa tiêu đề thành:

```csv
report_id,category,building,room,description,incident_id,incident_status,created_at,content
```

Nếu thực sự cần confidence, thêm một cột riêng và giá trị tương ứng; không dùng thời gian làm confidence. Bộ đọc cũng nhận CSV có `created_at` đúng vị trí theo tên cột. `content` là văn bản tổng hợp dư thừa, không dùng để thay thế nội dung gốc `description`.

## Chuẩn hóa

- `description` → `raw_text`; mã phản ánh/sự cố chuyển sang số nguyên.
- `Tòa nhà H1` → `H1`; `Tòa nhà A1` → `A1`; phòng giữ dạng chuỗi, không suy đoán tầng từ số phòng.
- Thời gian không ghi múi giờ được hiểu là giờ Việt Nam UTC+7. Thời gian có múi giờ được giữ nguyên. Cần xác nhận quy ước này nếu backend xuất UTC.
- Ô trống của mã/trạng thái sự cố, phòng, tầng → `None`.
- CSV thiếu `report_status` được coi là `ACTIVE`; giả định bên xuất đã loại phản ánh bị xóa. Muốn biểu diễn xóa, thêm `report_status=DELETED`.
- Mạng / Đường truyền → NETWORK; Điện / Chiếu sáng → ELECTRICAL; Vệ sinh / Môi trường → SANITATION; An ninh / An toàn → SECURITY; Dịch vụ sinh viên → STUDENT_SERVICE.
- Cơ sở vật chất → FACILITY. Nội dung máy chiếu/HDMI/trình chiếu/no signal được xếp PROJECTOR, thang máy → ELEVATOR để tương thích bộ lọc thiết bị cũ. Bộ lọc FACILITY bao gồm cả PROJECTOR/ELEVATOR. Đếm theo loại hiển thị các nhóm thiết bị đã chuẩn hóa, không giữ nguyên cách nhóm rộng trong CSV.
- Giữ các kiểm tra mã trùng, dữ liệu sai, trạng thái sự cố không nhất quán và giới hạn 5 MB / 5000 phản ánh; không tự bỏ dòng hỏng.

## Đối chiếu mẫu

| Câu hỏi | Phản ánh | Sự cố liên kết |
|---|---:|---:|
| Tất cả | 28 | 7 |
| Mạng H1 | 4 | 1 |
| Máy chiếu | 4 | 1 |
| Điện | 4 | 1 |
| Vệ sinh | 6 | 2 |
| An ninh | 5 | 1 |
| Học phí / dịch vụ sinh viên | 5 | 1 |
| Tòa A1 | 2 | 1 |
| Chưa xử lý | 15 | 4 |

Số sự cố đếm theo `incident_id` khác nhau. Bộ đọc giữ cách gom nhóm của nguồn, không tự sửa: chẳng hạn incident #5 chứa nhiều nội dung an ninh khác nhau. Nhóm nên kiểm tra quy tắc gom sự cố ở backend.

## Kiểm thử

```bash
python -m pytest tests/test_csv_source.py -q
```

Bộ kiểm thử CSV chạy offline, kiểm tra dữ liệu mẫu, số đếm toàn bộ (kể cả top_k=1), ngày, tòa A1, CSV chuẩn/sai header đã biết, BOM, dấu phẩy/xuống dòng trong nội dung, ô trống, dữ liệu lỗi, JSON cũ và giữ snapshot khi đồng bộ lỗi. Không xác nhận kết nối AI cloud bằng bộ test này.
