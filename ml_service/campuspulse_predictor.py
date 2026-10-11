"""Dự đoán độ phù hợp giữa Type và Describe bằng model CampusPulse đã train.

Đặt file này, campuspulse_type_features.py và compatibility_model.joblib cùng
thư mục có thể import trong project. Cài requirements_model.txt trước khi chạy.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from threading import Lock
from typing import Any
import warnings

import joblib
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

# Giữ đúng tên module: model đã lưu tham chiếu đến lớp trong file này.
from campuspulse_type_features import (
    TYPES,
    normalize_text,
    normalize_type,
    positive_probability,
)

__all__ = ["IssuePredictor", "load_issue_model", "predict_issue", "predict_issues"]

_DEFAULT_MODEL = Path(__file__).resolve().with_name("compatibility_model.joblib")
_MODELS: dict[Path, "IssuePredictor"] = {}
_LOAD_LOCK = Lock()


def _request(type_name: str, describe: str) -> dict[str, str]:
    if not isinstance(type_name, str):
        raise ValueError("Type phải là chuỗi.")
    if not isinstance(describe, str):
        raise ValueError("Describe phải là chuỗi.")
    canonical_type = normalize_type(type_name)
    text = normalize_text(describe)
    if not text:
        raise ValueError("Describe không được rỗng.")
    return {"Type": canonical_type, "Describe": text}


class IssuePredictor:
    """Nạp model một lần; gọi predict nhiều lần mà không huấn luyện lại."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = (
            Path(model_path).expanduser().resolve()
            if model_path is not None else _DEFAULT_MODEL
        )
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy model: {self.model_path}")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                bundle = joblib.load(self.model_path)
        except InconsistentVersionWarning as exc:
            raise RuntimeError(
                "Phiên bản scikit-learn khác môi trường huấn luyện. "
                "Cài đúng requirements_model.txt trong môi trường Python của "
                "project rồi khởi động lại."
            ) from exc

        required = {"pipeline", "threshold", "model_name", "types", "features_version"}
        if not isinstance(bundle, dict) or not required.issubset(bundle):
            raise ValueError("File model không phải bundle CampusPulse TypeAware v3.")
        if bundle["features_version"] != "explicit_type_text_v3":
            raise ValueError("Phiên bản đặc trưng của model không được hỗ trợ.")
        if tuple(bundle["types"]) != TYPES:
            raise ValueError("Danh sách Type của model khác module đặc trưng.")
        pipeline = bundle["pipeline"]
        if not hasattr(pipeline, "predict_proba") or set(pipeline.classes_) != {0, 1}:
            raise ValueError("Pipeline cần là mô hình phân loại nhị phân 0/1.")
        threshold = float(bundle["threshold"])
        if not 0 < threshold < 1:
            raise ValueError("Ngưỡng lưu trong model không hợp lệ.")

        self._pipeline = pipeline
        self.threshold = threshold
        self.model_name = str(bundle["model_name"])
        self.types = tuple(bundle["types"])

    def predict(self, type_name: str, describe: str) -> dict[str, Any]:
        """label=1: mô tả phù hợp Type đã chọn; label=0: không phù hợp."""
        return self.predict_many([{"Type": type_name, "Describe": describe}])[0]

    def predict_many(self, items: Iterable[Mapping[str, str]]) -> list[dict[str, Any]]:
        """Mỗi phần tử phải có khóa Type và Describe; giữ thứ tự đầu vào."""
        if isinstance(items, (str, bytes, Mapping)):
            raise ValueError("Đầu vào cần là danh sách các mục gồm Type và Describe.")
        rows = []
        for index, item in enumerate(items):
            if not isinstance(item, Mapping) or not {"Type", "Describe"}.issubset(item):
                raise ValueError(f"Mục {index} thiếu Type hoặc Describe.")
            rows.append(_request(item["Type"], item["Describe"]))
        if not rows:
            return []

        frame = pd.DataFrame(rows, columns=["Type", "Describe"])
        probabilities = positive_probability(self._pipeline, frame)
        results = []
        for row, probability in zip(rows, probabilities):
            probability = float(probability)
            label = int(probability >= self.threshold)
            results.append({
                "type": row["Type"],
                "describe": row["Describe"],
                "label": label,
                "is_match": bool(label),
                "probability": probability,
                "threshold": self.threshold,
                "model": self.model_name,
            })
        return results


def load_issue_model(model_path: str | Path | None = None) -> IssuePredictor:
    """Có thể gọi khi backend khởi động. Cache một model cho mỗi đường dẫn/process.

    Khi thay file model, khởi động lại backend để nạp phiên bản mới.
    """
    path = Path(model_path).expanduser().resolve() if model_path is not None else _DEFAULT_MODEL
    with _LOAD_LOCK:
        if path not in _MODELS:
            _MODELS[path] = IssuePredictor(path)
        return _MODELS[path]


def predict_issue(
    type_name: str, describe: str, *, model_path: str | Path | None = None
) -> dict[str, Any]:
    """Hàm dùng trực tiếp trong project: nhận Type, Describe; trả dict cho JSON."""
    # Kiểm tra request trước để thông báo lỗi đầu vào không phụ thuộc việc nạp model.
    row = _request(type_name, describe)
    return load_issue_model(model_path).predict(row["Type"], row["Describe"])


def predict_issues(
    items: Iterable[Mapping[str, str]], *, model_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Dự đoán nhiều cặp Type/Describe trong một lần transform."""
    return load_issue_model(model_path).predict_many(items)
