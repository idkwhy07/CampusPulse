"""Gọi API bằng thư viện chuẩn Python, không cần nạp model ở phía client."""

import json
import os
from urllib.request import Request, urlopen


def predict_issue(type_name: str, describe: str) -> dict:
    base_url = os.getenv("CAMPUSPULSE_ML_API_URL", "http://127.0.0.1:8001").rstrip("/")
    body = json.dumps({"Type": type_name, "Describe": describe}, ensure_ascii=False)
    request = Request(
        f"{base_url}/predict",
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


if __name__ == "__main__":
    result = predict_issue(
        "Mạng và đường truyền", "wifi tầng 4 bắt được mà load mãi không xong"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
