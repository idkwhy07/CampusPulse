"""Kiểm tra hợp đồng HTTP và model startup: python test_api.py"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as api_module


class ApiTests(unittest.TestCase):
    def test_model_loaded_once_and_http_predictions(self):
        with patch.object(api_module, "IssuePredictor", wraps=api_module.IssuePredictor) as loader:
            with TestClient(api_module.create_app()) as client:
                self.assertEqual(loader.call_count, 1)
                self.assertEqual(client.get("/health").json()["ready"], True)
                self.assertEqual(client.get("/types").json()["count"], 6)
                self.assertEqual(client.get("/docs").status_code, 200)
                schema = client.get("/openapi.json").json()
                self.assertIn("/predict", schema["paths"])

                payload = {"Type": "Mạng và đường truyền", "Describe": "wifi tầng 4 bắt được mà load mãi không xong"}
                response = client.post("/predict", json=payload)
                self.assertEqual(response.status_code, 200)
                expected = client.app.state.predictor.predict(payload["Type"], payload["Describe"])
                self.assertEqual(response.json(), expected)
                self.assertEqual(expected["label"], 1)
                self.assertAlmostEqual(expected["probability"], 0.9981916096259621, places=12)

                response = client.post("/predict", json={"type": "  MẠNG / ĐƯỜNG TRUYỀN  ", "describe": payload["Describe"]})
                self.assertEqual(response.json(), expected)

                items = [
                    {"Type": "Vệ sinh / môi trường", "Describe": "nvs tầng 5 hết nước từ sáng"},
                    {"Type": "Cơ sở vật chất", "Describe": "nvs tầng 5 hết nước từ sáng"},
                ]
                batch = client.post("/predict/batch", json={"items": items})
                self.assertEqual(batch.status_code, 200)
                self.assertEqual(batch.json()["count"], 2)
                self.assertEqual([r["label"] for r in batch.json()["results"]], [1, 0])

                with ThreadPoolExecutor(max_workers=8) as pool:
                    replies = list(pool.map(lambda _: client.post("/predict", json=payload).json(), range(16)))
                self.assertTrue(all(reply == expected for reply in replies))
                self.assertEqual(loader.call_count, 1)
            self.assertIsNone(client.app.state.predictor)

    def test_invalid_requests_are_rejected(self):
        with TestClient(api_module.create_app()) as client:
            invalid = [
                {},
                {"Type": "Nhóm không tồn tại", "Describe": "wifi hỏng"},
                {"Type": [], "Describe": "wifi hỏng"},
                {"Type": "An ninh / an toàn", "Describe": "   "},
                {"Type": "An ninh / an toàn", "Describe": None},
                {"Type": "An ninh / an toàn", "Describe": 123},
                {"Type": "An ninh / an toàn", "Describe": "x" * 10001},
                {"Type": "An ninh / an toàn", "Describe": "mất mũ", "Label": 1},
            ]
            for payload in invalid:
                with self.subTest(payload=str(payload)[:100]):
                    self.assertEqual(client.post("/predict", json=payload).status_code, 422)
            self.assertEqual(client.post("/predict/batch", json={"items": []}).status_code, 422)
            self.assertEqual(client.post("/predict/batch", json={"items": [{"Type": "An ninh / an toàn", "Describe": "mất mũ"}] * 257}).status_code, 422)
            self.assertEqual(client.post("/predict", content="{", headers={"Content-Type": "application/json"}).status_code, 422)

    def test_cors_configuration(self):
        with TestClient(api_module.create_app(cors_origins=["http://localhost:5173"])) as client:
            allowed = client.options("/predict", headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            })
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed.headers["access-control-allow-origin"], "http://localhost:5173")
            denied = client.options("/predict", headers={
                "Origin": "http://localhost:9999",
                "Access-Control-Request-Method": "POST",
            })
            self.assertEqual(denied.status_code, 400)

    def test_missing_model_prevents_startup(self):
        missing = Path(__file__).with_name("model_not_present.joblib")
        with self.assertRaises(FileNotFoundError):
            with TestClient(api_module.create_app(model_path=missing)):
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
