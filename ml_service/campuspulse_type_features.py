"""Đặc trưng văn bản chung và Type × văn bản; không gán nhãn bằng từ khóa."""

import re
import unicodedata
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.utils.validation import check_is_fitted

TYPES = (
    "Mạng và đường truyền", "Cơ sở vật chất", "Điện / chiếu sáng",
    "Vệ sinh / môi trường", "An ninh / an toàn", "Dịch vụ sinh viên",
)


def normalize_text(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(text))).strip()


def normalize_type(text):
    key = normalize_text(text).casefold()
    aliases = {name.casefold(): name for name in TYPES}
    aliases["mạng / đường truyền"] = TYPES[0]
    if key not in aliases:
        raise ValueError(f"Type không hợp lệ: {text!r}. Dùng đúng 6 Type đã khai báo.")
    return aliases[key]


def plain_text(text):
    text = normalize_text(text).casefold().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def group_key(text):
    # Khóa bảo thủ: giữ cả từ phủ định, số lần lặp từ; gom đảo thứ tự và số phòng.
    text = re.sub(r"\b[a-z]*\d+[a-z]*\b", " number ", plain_text(text))
    return " ".join(sorted(re.findall(r"\w+", text)))


def prepare_frame(frame):
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Đầu vào cần là DataFrame gồm Type và Describe.")
    required = ["Type", "Describe"]
    if not set(required).issubset(frame.columns):
        raise ValueError("Thiếu cột Type hoặc Describe.")
    result = frame[required].copy()
    if result.isna().any().any():
        raise ValueError("Type/Describe không được thiếu.")
    result["Type"] = result["Type"].map(normalize_type)
    result["Describe"] = result["Describe"].map(normalize_text)
    if result["Describe"].eq("").any():
        raise ValueError("Describe không được rỗng.")
    return result


class TypeTextFeatures(TransformerMixin, BaseEstimator):
    """Tách mỗi TF-IDF token thành trọng số riêng theo Type trong ma trận sparse.

    include_interactions=False cho đối chứng text + one-hot Type.
    include_interactions=True thêm 6 khối Type × text, không chỉ nối tên Type.
    """

    def __init__(self, include_interactions=True, word_features=15000,
                 char_features=25000, min_df=2):
        self.include_interactions = include_interactions
        self.word_features = word_features
        self.char_features = char_features
        self.min_df = min_df

    def fit(self, X, y=None):
        frame = prepare_frame(X)
        texts = frame["Describe"].map(plain_text).tolist()
        self.word_ = TfidfVectorizer(
            ngram_range=(1, 2), min_df=self.min_df,
            max_features=self.word_features, sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b", dtype=np.float32)
        self.char_ = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=self.min_df,
            max_features=self.char_features, sublinear_tf=True, dtype=np.float32)
        self.word_.fit(texts)
        self.char_.fit(texts)
        self.n_text_features_ = len(self.word_.vocabulary_) + len(self.char_.vocabulary_)
        self.types_ = np.array(TYPES, dtype=object)
        return self

    def transform(self, X):
        check_is_fitted(self, ["word_", "char_", "types_"])
        frame = prepare_frame(X)
        texts = frame["Describe"].map(plain_text).tolist()
        text = sparse.hstack(
            [self.word_.transform(texts), self.char_.transform(texts)],
            format="csr", dtype=np.float32)
        mapping = {name: index for index, name in enumerate(self.types_)}
        type_ids = frame["Type"].map(mapping).to_numpy(dtype=np.int32)
        n_rows = len(frame)
        category = sparse.csr_matrix(
            (np.ones(n_rows, dtype=np.float32), (np.arange(n_rows), type_ids)),
            shape=(n_rows, len(self.types_)))
        if not self.include_interactions:
            return sparse.hstack([text, category], format="csr")
        coo = text.tocoo()
        conditional = sparse.csr_matrix(
            (coo.data, (coo.row, coo.col + type_ids[coo.row] * self.n_text_features_)),
            shape=(n_rows, len(self.types_) * self.n_text_features_))
        return sparse.hstack([text, conditional, category], format="csr")


def positive_probability(pipeline, frame):
    positive_index = list(pipeline.classes_).index(1)
    return pipeline.predict_proba(frame)[:, positive_index]


def predict_compatibility(type_name, describe, bundle):
    """Dùng bundle vừa train; đầu vào là một Type và một mô tả."""
    frame = prepare_frame(pd.DataFrame([{"Type": type_name, "Describe": describe}]))
    probability = float(positive_probability(bundle["pipeline"], frame)[0])
    label = int(probability >= bundle["threshold"])
    return {"Type": frame.iloc[0]["Type"], "Describe": frame.iloc[0]["Describe"],
            "Label": label, "P(1)": probability, "Model": bundle["model_name"]}
