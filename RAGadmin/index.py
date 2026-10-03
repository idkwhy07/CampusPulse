import hashlib
import math
import re
from collections import Counter

from query import normalize

STOP = set("co la thi va cac cua cho toi nhung gi the nao dang bi phan anh sinh vien ve tai o hay tim xem tom tat tong hop toan bo du lieu".split())


def tokens(text):
    text = normalize(text)
    for old, new in (("wi-fi", "wifi"), ("wi fi", "wifi"), ("internet", "wifi"),
                     ("ket noi", "wifi"), ("mang", "wifi"),
                     ("khong on dinh", "chap chon"), ("network", "wifi"),
                     ("projector", "may chieu"), ("elevator", "thang may")):
        text = re.sub(r"(?<!\w)" + re.escape(old) + r"(?!\w)", new, text)
    return [word for word in re.findall(r"\w+", text) if word not in STOP]


def chunks(report):
    prefix = f"{report.category} {report.building} tầng {report.floor or ''} phòng {report.room or ''}. "
    # Overlap giúp nội dung ở ranh giới không bị mất; kết quả gộp theo report_id.
    return [prefix + report.raw_text[i:i + 900] for i in range(0, len(report.raw_text), 750)]


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError("Vector không cùng số chiều")
    na, nb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def _chunk_key(text):
    """Hash SHA-256 của nội dung chunk — dùng làm khoá embed cache."""
    return hashlib.sha256(text.encode()).hexdigest()


class SearchIndex:
    def __init__(self, reports, provider=None, embed_cache=None):
        """
        embed_cache: dict[str, list[float]] | None
            Cache dùng chung qua nhiều lần sync, khoá là hash(chunk_text).
            Chunk đã có trong cache thì không gọi Ollama lại.
            Truyền None để tắt cache (hành vi cũ).
        """
        self.docs = [(r.report_id, text) for r in reports for text in chunks(r)]
        self.bags = [Counter(tokens(text)) for _, text in self.docs]
        df = Counter(word for bag in self.bags for word in bag)
        self.idf = {word: math.log((1 + len(self.docs)) / (1 + count)) + 1 for word, count in df.items()}
        self.vectors = None
        if provider and self.docs:
            # Tách chunk cần embed mới (cache miss) và chunk dùng lại (cache hit).
            keys = [_chunk_key(text) for _, text in self.docs]
            placeholders = [None] * len(self.docs)
            miss_indices, miss_keys, miss_texts = [], [], []
            for i, (key, (_, text)) in enumerate(zip(keys, self.docs)):
                if embed_cache is not None and key in embed_cache:
                    placeholders[i] = embed_cache[key]  # cache hit
                else:
                    miss_indices.append(i)
                    miss_keys.append(key)
                    miss_texts.append(text)
            # Embed batch các chunk còn thiếu.
            if miss_texts:
                new_vectors = []
                for b in range(0, len(miss_texts), 32):
                    new_vectors.extend(provider.embed(miss_texts[b:b + 32]))
                for idx, key, vec in zip(miss_indices, miss_keys, new_vectors):
                    placeholders[idx] = vec
                    if embed_cache is not None:
                        embed_cache[key] = vec  # ghi vào cache để lần sau dùng lại
            self.vectors = placeholders
            if len({len(v) for v in self.vectors}) != 1:
                raise ValueError("Kích thước embedding thay đổi giữa các batch")

    def search(self, question, allowed_ids, top_k, provider=None, min_score=0.35):
        query = Counter(tokens(question))
        qweights = {t: n * self.idf[t] for t, n in query.items() if t in self.idf}
        qnorm = math.sqrt(sum(w*w for w in qweights.values()))
        semantic = provider.embed([question])[0] if provider and self.vectors else None
        scores = {}
        for i, (report_id, _) in enumerate(self.docs):
            if report_id not in allowed_ids:
                continue
            bag = self.bags[i]
            weights = {t: n * self.idf[t] for t, n in bag.items()}
            norm = math.sqrt(sum(w*w for w in weights.values()))
            lex = sum(w * weights.get(t, 0) for t, w in qweights.items()) / (qnorm * norm) if qnorm and norm else 0
            if semantic is not None:
                sem = cosine(semantic, self.vectors[i])
                score = .8 * sem + .2 * lex
                valid = sem >= min_score or lex >= .12
            else:
                score, valid = lex, lex >= .08
            if valid:
                scores[report_id] = max(score, scores.get(report_id, -1))
        return sorted(scores, key=lambda key: (-scores[key], key))[:top_k]
