import json
from dataclasses import replace
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import BASE, Settings
from providers import DeepSeekGeminiProvider
from query import parse_query
from rag import Chatbot
from sources import FileReportSource


@pytest.fixture
def settings(tmp_path):
    path = tmp_path / "reports.json"
    path.write_bytes((BASE / "data/mock_reports.json").read_bytes())
    return Settings(reports_path=path)


@pytest.fixture
def bot(settings):
    result = Chatbot(settings, FileReportSource(settings.reports_path))
    result.sync()
    return result


def test_semantic_alias_offline_and_building_filter(bot):
    r = bot.chat("Mạng không ổn định ở H1")
    assert r["sources"] and all(s["building"] == "H1" for s in r["sources"])
    assert r["retrieval_mode"] == "lexical"
    assert 19 not in {s["report_id"] for s in r["sources"]}


def test_count_whole_dataset_not_top_k(bot):
    r = bot.chat("Có bao nhiêu phản ánh về mạng ở H1?", top_k=1)
    assert r["statistics"]["report_count"] == 4
    assert bot.chat("Có bao nhiêu sự cố về mạng ở H1?")["statistics"]["incident_count"] == 2
    all_rows = bot.chat("Có bao nhiêu phản ánh?")["statistics"]
    assert all_rows["report_count"] == 19
    assert all_rows["unlinked_reports"] == 2


def test_group_and_status(bot):
    assert bot.chat("Thống kê phản ánh theo tòa")["statistics"]["groups"] == {"H1":7,"H2":6,"H3":6}
    assert bot.chat("Tòa nào có nhiều phản ánh nhất?")["statistics"]["groups"] == {"H1":7,"H2":6,"H3":6}
    assert bot.chat("Có bao nhiêu phản ánh chưa xử lý ở H1?")["statistics"]["report_count"] == 7
    assert bot.chat("Có bao nhiêu phản ánh đã xử lý?")["statistics"]["report_count"] == 3


def test_exact_lookup_no_lexical_search(bot):
    assert [r["report_id"] for r in bot.chat("Cho tôi phản ánh số 12")["sources"]] == [12]
    assert len(bot.chat("Sự cố số 1")["sources"]) == 3
    assert bot.chat("Phản ánh số 999")["sources"] == []


def test_summary_complete_and_date(bot):
    r = bot.chat("Tóm tắt toàn bộ phản ánh ngày 02/10/2026", top_k=1)
    assert len(r["sources"]) == 16
    assert all(f'[PA{s["report_id"]}]' in r["answer"] for s in r["sources"])
    assert parse_query("hôm qua", today=date(2026,10,2)).day == date(2026,10,1)


@pytest.mark.parametrize("question", [
    "Có bao nhiêu phản ánh về ghế bị gãy?", "Thống kê tuần này",
    "Tóm tắt H1 và H2", "Có bao nhiêu phản ánh ngày 32/10/2026?",
    "Đổi trạng thái sự cố số 1", "Có bao nhiêu sinh viên phản ánh?",
])
def test_unsupported_constraints_clarified(bot, question):
    assert bot.chat(question)["intent"] == "clarification"


def test_no_results(bot):
    assert bot.chat("Wifi H99")["sources"] == []
    assert bot.chat("Công thức bánh pizza")["sources"] == []


def test_sync_add_delete_and_failed_sync_keeps_previous(bot, settings):
    rows = json.loads(settings.reports_path.read_text(encoding="utf-8"))
    rows[0]["report_status"] = "DELETED"
    rows.append({**rows[11], "report_id":21, "raw_text":"Wifi phòng 101 H1 chập chờn"})
    settings.reports_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    bot.sync()
    assert not bot.chat("Phản ánh số 1")["sources"]
    assert bot.chat("Phản ánh số 21")["sources"]
    previous = bot.snapshot
    rows.append(rows[0])
    settings.reports_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        bot.sync()
    assert bot.snapshot is previous


def test_sync_status_changes(bot, settings):
    rows = json.loads(settings.reports_path.read_text(encoding="utf-8"))
    for row in rows:
        if row['incident_id'] == 1:
            row['incident_status'] = 'RESOLVED'
    settings.reports_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    bot.sync()
    assert bot.chat('Phản ánh số 1')['sources'][0]['incident_status'] == 'RESOLVED'


def test_invalid_source(settings):
    rows = json.loads(settings.reports_path.read_text(encoding="utf-8"))
    rows[1]["incident_status"] = "RESOLVED"
    settings.reports_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        FileReportSource(settings.reports_path).load_reports()
    rows[1]["incident_status"] = "IN_PROGRESS"
    rows[0]["created_at"] = "2026-10-02T09:00:00"
    settings.reports_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        FileReportSource(settings.reports_path).load_reports()


def test_empty_source(settings):
    settings.reports_path.write_text('[]')
    bot = Chatbot(settings, FileReportSource(settings.reports_path))
    bot.sync()
    assert bot.chat('Có bao nhiêu phản ánh?')['statistics']['report_count'] == 0
    assert not bot.chat('Wifi H1')['sources']


class FakeProvider:
    def __init__(self, fail_embed=False, invalid=False):
        self.fail_embed, self.invalid = fail_embed, invalid

    def plan(self, question):
        return parse_query(question)

    def embed(self, texts):
        if self.fail_embed:
            raise TimeoutError()
        return [[1.0, 0.0] for _ in texts]

    def answer(self, question, reports):
        rid = 999 if self.invalid else reports[0].report_id
        return {'answer':f'Nội dung kiểm thử [PA{rid}]', 'report_ids':[rid]}


def test_model_path_and_fallback(settings):
    bot = Chatbot(settings, FileReportSource(settings.reports_path), FakeProvider())
    bot.sync()
    result = bot.chat('Wifi H1')
    assert result['retrieval_mode'] == 'semantic'
    assert result['generation_mode'] == 'llm'
    bot.provider.invalid = True
    result = bot.chat('Wifi H1')
    assert result['generation_mode'] == 'template'
    assert result['warnings'] and 'PA999' not in result['answer']
    bot.provider.fail_embed = True
    bot.embed_cache.clear()
    result = bot.chat('Wifi H1')
    assert result['retrieval_mode'] == 'lexical'
    bot.sync()
    assert bot.status()['retrieval_mode'] == 'lexical'


def test_provider_http_contract(settings, monkeypatch):
    requests = []
    def handle(req):
        payload = json.loads(req.content)
        requests.append((req.url.path, payload))
        if "batchEmbedContents" in req.url.path:
            return httpx.Response(200, json={'embeddings':[{'values':[1.0,0.0]} for _ in payload['requests']]})
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'insufficient_evidence':False,'sections':[{'text':'Nguồn','report_ids':[1]}]})}}]})
    real_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    cloud_settings = replace(settings, ai_mode="cloud", gemini_api_key="test_gemini", deepseek_api_key="test_deepseek")
    provider = DeepSeekGeminiProvider(cloud_settings)
    assert provider.embed(['abc']) == [[1.0,0.0]]
    reports = FileReportSource(settings.reports_path).load_reports()[:1]
    assert provider.answer('Wifi?', reports)['report_ids'] == [1]


def test_api_and_ui(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/').status_code == 200
        assert client.get('/static/app.js').status_code == 200
        assert client.get('/health').json()['ready']
        assert client.get('/internal/admin/status').json()['report_count'] == 19
        result = client.post('/internal/admin/chat',json={'question':'Có bao nhiêu phản ánh?'})
        assert result.status_code == 200 and result.json()['statistics']['report_count'] == 19
        assert client.post('/internal/admin/chat',json={'question':'   '}).status_code == 422
        assert client.post('/internal/admin/chat',content=b'x'*17000).status_code == 413
        assert client.post('/internal/admin/sync',json={}).status_code == 200
        assert client.post('/internal/admin/sync',headers={'origin':'https://untrusted.example'},json={}).status_code == 403


def test_internal_auth(settings):
    s = replace(settings, app_mode='internal', api_key='a-secret-for-service-only-12345')
    with TestClient(create_app(s)) as client:
        assert client.get('/internal/admin/status').status_code == 401
        assert client.post('/internal/admin/chat',json={'question':'Wifi H1'}).status_code == 401
        assert client.post('/internal/admin/sync',json={}).status_code == 401
        assert client.get('/internal/admin/status',headers={'X-Internal-Key':s.api_key}).status_code == 200
        assert client.get('/').status_code == 404
    with pytest.raises(ValueError):
        replace(settings, app_mode='internal').validate()
    with pytest.raises(ValueError):
        replace(settings, data_mode='file').validate()
