from datetime import date

import pytest

from config import Settings
from planner import respect_explicit_request
from query import Query
from rag import Chatbot
from sources import FileReportSource


class ConfusedProvider:
    def embed(self, texts):
        return [[1.0,0.0] for _ in texts]

    def plan(self, question):
        # Tái hiện ảnh: chọn sai entity, tự thêm group và ngày.
        return Query(kind='count', entity='incident', categories=['NETWORK'],
                     buildings=['H1'], group_by='category', start_day=date(2026,10,2))


@pytest.mark.parametrize('question,entity,expected', [
    ('Có bao nhiêu phản ánh về mạng ở H1?', 'phản ánh', 4),
    ('Có bao nhiêu sự cố về mạng ở H1?', 'sự cố', 2),
    ('co bao nhieu phan anh ve mang o H1?', 'phản ánh', 4),
])
def test_exact_user_entity_wins_over_wrong_llm(question,entity,expected):
    settings = Settings(ai_mode='cloud', gemini_api_key='fake', deepseek_api_key='fake', ai_required=True)
    bot=Chatbot(settings,FileReportSource(settings.reports_path),ConfusedProvider())
    bot.sync()
    result=bot.chat(question)
    assert result['answer'].startswith(f'Có {expected} {entity}')
    assert len(result['sources'])==4
    assert result['statistics']['groups']=={}
    assert 'Ngày lọc' not in result['answer']


def test_natural_content_condition_still_uses_llm():
    proposed=Query(kind='count',entity='incident',content_filter='ghế bị gãy')
    result=respect_explicit_request('Có bao nhiêu phản ánh về ghế bị gãy?',proposed)
    assert result.entity=='report'
    assert result.content_filter=='ghế bị gãy'


def test_ambiguous_request_keeps_clarification():
    proposed=Query(kind='clarification',clarification='Bạn muốn lọc ngày nào?')
    assert respect_explicit_request('Có bao nhiêu phản ánh?',proposed) is proposed
