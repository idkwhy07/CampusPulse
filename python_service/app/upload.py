import sys
import os

# Thêm thư mục gốc (python_service) vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from service.document_service import DocumentService

service = DocumentService()

service.upload(file_path="data/raw/KHOA XÂY DỰNG DÂN DỤNG VÀ CÔNG NGHIỆP.docx")
print("success")