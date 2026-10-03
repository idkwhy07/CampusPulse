import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import BASE, Settings
from planner import QueryPlan
from providers import DeepSeekGeminiProvider
from query import Query
from rag import AIUnavailable, Chatbot
from sources import FileReportSource


def plan_data(**changes):
    data = dict(kind="search", entity="report", report_id=None, incident_id=None,
                buildings=[], categories=[], floor=None, room=None, statuses=[],
                start_day=None, end_day=None, group_by=None,
                search_text="mạng chập chờn", content_filter=None, clarification=None)
    data.update(changes)
    return data


def test_validated_multi_building_date_plan():
    reports_file = (BASE / 'data/mock_reports.json') if (BASE / 'data/mock_reports.json').exists() else (BASE / 'data/phananh.json')
    query = QueryPlan.model_validate(plan_data(buildings=['h1','h2'], start_day='2026-10-01', end_day='2026-10-02')).to_query()
    reports = FileReportSource(reports_file).load_reports()
    assert len([r for r in reports if query.accepts(r)]) == 13
    with pytest.raises(ValueError):
        QueryPlan.model_validate(plan_data(kind='run_sql'))
    with pytest.raises(ValueError):
        QueryPlan.model_validate(plan_data(start_day='2026-10-03', end_day='2026-10-01'))


class NaturalProvider:
    def __init__(self, fail_plan=False, fail_embed=False):
        self.fail_plan, self.fail_embed = fail_plan, fail_embed
        self.examined = []

    def embed(self, texts):
        if self.fail_embed:
            raise RuntimeError('offline')
        return [[1.0, 0.0] for text in texts]

    def plan(self, question):
        if self.fail_plan:
            raise RuntimeError('offline')
        if 'ghế' in question:
            return QueryPlan.model_validate(plan_data(kind='count', content_filter='ghế bị hỏng')).to_query()
        return QueryPlan.model_validate(plan_data(buildings=['H1'])).to_query()

    def filter_reports(self, condition, reports):
        self.examined = [r.report_id for r in reports]
        return {18}

    def answer(self, question, reports):
        rid = reports[0].report_id
        return {'answer':f'Kết quả tự nhiên [PA{rid}]', 'report_ids':[rid]}


def make_bot(provider, required=True):
    settings = Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake', ai_required=required)
    bot = Chatbot(settings, FileReportSource(settings.reports_path), provider)
    bot.sync()
    return bot


def test_natural_question_bypasses_rules():
    bot = make_bot(NaturalProvider())
    result = bot.chat('Chỗ H1 có vấn đề gì làm các bạn không học online được?')
    assert result['understanding_mode'] == 'llm'
    assert result['generation_mode'] == 'llm'
    assert result['sources'] and all(r['building'] == 'H1' for r in result['sources'])


def test_content_count_examines_all_records():
    provider = NaturalProvider()
    result = make_bot(provider).chat('Có bao nhiêu phản ánh ghế bị hỏng?', top_k=1)
    assert len(provider.examined) == 19
    assert result['statistics']['report_count'] == 1
    assert result['sources'][0]['report_id'] == 18


def test_required_ai_never_silently_falls_back():
    bot = make_bot(NaturalProvider(fail_plan=True))
    with pytest.raises(AIUnavailable):
        bot.chat('wifi H1')
    with pytest.raises(AIUnavailable):
        make_bot(NaturalProvider(fail_embed=True))
    result = make_bot(NaturalProvider(fail_plan=True), required=False).chat('wifi H1')
    assert result['understanding_mode'] == 'rules'
    assert any('quy tắc' in s for s in result['warnings'])


def test_plan_provider_contract(monkeypatch):
    p = DeepSeekGeminiProvider(Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake'))
    calls = []
    def structured(system, payload, schema):
        calls.append((payload, schema))
        return plan_data(buildings=['H1'])
    monkeypatch.setattr(p, 'structured', structured)
    assert p.plan('H1 sao hay rớt mạng?').buildings == ['H1']
    assert calls[0][1]['properties']['kind']
    assert 'today' in calls[0][0]


def test_classification_requires_complete_unique_decisions(monkeypatch):
    p = DeepSeekGeminiProvider(Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake'))
    reports_file = (BASE / 'data/mock_reports.json') if (BASE / 'data/mock_reports.json').exists() else (BASE / 'data/phananh.json')
    reports = FileReportSource(reports_file).load_reports()[:2]
    monkeypatch.setattr(p, 'structured', lambda *args: {'decisions':[{'report_id':1,'matches':True}]})
    with pytest.raises(ValueError):
        p.filter_reports('wifi', reports)
    monkeypatch.setattr(p, 'structured', lambda *args: {'decisions':[{'report_id':1,'matches':True},{'report_id':2,'matches':False}]})
    assert p.filter_reports('wifi', reports) == {1}


def test_api_reports_ai_error():
    settings = Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake', ai_required=True)
    with TestClient(create_app(settings, NaturalProvider(fail_plan=True))) as client:
        response = client.post('/internal/admin/chat', json={'question':'wifi H1'})
        assert response.status_code == 503
        assert 'LLM' in response.json()['error']
