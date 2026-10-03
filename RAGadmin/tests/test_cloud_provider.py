"""Kiểm thử DeepSeekGeminiProvider bằng httpx.MockTransport, không gọi mạng thật."""
import json
from types import SimpleNamespace

import httpx
import pytest

import providers
from providers import DeepSeekGeminiProvider

SECRET_GEMINI = "GEMINI-SECRET-123"
SECRET_DEEPSEEK = "sk-deepseek-secret-456"


def make_provider(monkeypatch, handler):
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs.pop("trust_env", None)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(providers.httpx, "Client", client_factory)
    settings = SimpleNamespace(gemini_api_key=SECRET_GEMINI, deepseek_api_key=SECRET_DEEPSEEK,
                               chat_model="deepseek-chat", embed_model="gemini-embedding-001", timeout=5)
    return DeepSeekGeminiProvider(settings)


def chat_reply(content, finish="stop"):
    return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"content": content}}]})


def test_structured_sends_max_tokens_and_json_mode(monkeypatch):
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        return chat_reply('{"ok": true}')

    p = make_provider(monkeypatch, handler)
    assert p.structured("hệ thống", {"q": 1}, {"type": "object"}) == {"ok": True}
    assert seen["body"]["max_tokens"] == 4096
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert "json" in seen["body"]["messages"][0]["content"].lower()
    assert seen["auth"] == f"Bearer {SECRET_DEEPSEEK}"


def test_structured_retries_once_on_empty_content(monkeypatch):
    replies = iter([chat_reply(None), chat_reply('{"ok": true}')])
    calls = []

    def handler(request):
        calls.append(1)
        return next(replies)

    p = make_provider(monkeypatch, handler)
    assert p.structured("s", {}, {}) == {"ok": True}
    assert len(calls) == 2


def test_structured_empty_twice_raises_value_error(monkeypatch):
    p = make_provider(monkeypatch, lambda request: chat_reply(""))
    with pytest.raises(ValueError, match="rỗng"):
        p.structured("s", {}, {})


def test_structured_truncated_output_is_not_retried(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        return chat_reply('{"a": ', finish="length")

    p = make_provider(monkeypatch, handler)
    with pytest.raises(ValueError, match="chưa hoàn tất"):
        p.structured("s", {}, {})
    assert len(calls) == 1


def test_structured_strips_code_fences(monkeypatch):
    p = make_provider(monkeypatch, lambda request: chat_reply('```json\n{"ok": 1}\n```'))
    assert p.structured("s", {}, {}) == {"ok": 1}


def test_gemini_key_is_in_header_not_url(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        n = len(json.loads(request.content)["requests"])
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]} for _ in range(n)]})

    p = make_provider(monkeypatch, handler)
    assert p.embed(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]
    assert seen["key"] == SECRET_GEMINI
    assert SECRET_GEMINI not in seen["url"] and "key=" not in seen["url"]


def test_gemini_error_message_does_not_leak_key(monkeypatch):
    p = make_provider(monkeypatch, lambda request: httpx.Response(429))
    with pytest.raises(httpx.HTTPStatusError) as info:
        p.embed(["a"])
    assert SECRET_GEMINI not in str(info.value)


def test_gemini_batches_over_32(monkeypatch):
    sizes = []

    def handler(request):
        n = len(json.loads(request.content)["requests"])
        sizes.append(n)
        return httpx.Response(200, json={"embeddings": [{"values": [1.0]} for _ in range(n)]})

    p = make_provider(monkeypatch, handler)
    assert len(p.embed([f"t{i}" for i in range(70)])) == 70
    assert sizes == [32, 32, 6]
