from datetime import date

import pytest

import planner
from config import Settings
from query import Query, parse_query
from rag import Chatbot
from sources import FileReportSource


class WrongSearchProvider:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def plan(self, question):
        return Query(kind='search', start_day=date(2020,1,1), end_day=date(2020,1,1), search_text='hôm nay')

    def answer(self, *args):
        raise AssertionError('Liệt kê không cần sinh LLM hoặc top-k')


@pytest.mark.parametrize('question', [
    'hôm nay có những phản ánh j', 'hôm nay có những phản ánh gì',
    'Liệt kê các phản ánh hôm nay', 'Cho tôi danh sách phản ánh hôm nay',
])
def test_list_today_complete_even_when_model_misroutes(question, monkeypatch):
    monkeypatch.setattr(planner,'parse_query',lambda q:parse_query(q,today=date(2026,10,2)))
    settings = Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake', ai_required=True)
    bot=Chatbot(settings,FileReportSource(settings.reports_path),WrongSearchProvider())
    bot.sync()
    result=bot.chat(question,top_k=1)
    assert result['intent']=='list'
    assert len(result['sources'])==16
    assert '16 phản ánh' in result['answer'] and '02/10/2026' in result['answer']


def test_tomorrow_does_not_pretend_old_data_is_today(monkeypatch):
    monkeypatch.setattr(planner,'parse_query',lambda q:parse_query(q,today=date(2026,10,3)))
    settings = Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake', ai_required=True)
    bot=Chatbot(settings,FileReportSource(settings.reports_path),WrongSearchProvider())
    bot.sync()
    result=bot.chat('Hôm nay có những phản ánh gì?')
    assert not result['sources']
    assert '03/10/2026' in result['answer']
    assert 'Dữ liệu hiện có từ 01/10/2026 đến 02/10/2026' in result['answer']


def test_unknown_content_not_ignored():
    parsed=parse_query('Liệt kê phản ánh về ghế gãy hôm nay',today=date(2026,10,2))
    assert parsed.clarification is not None
