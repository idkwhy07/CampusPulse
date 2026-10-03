import httpx
import pytest

from ai_errors import explain_ai_error
from config import Settings
from providers import NO_EVIDENCE, OllamaProvider
from rag import Chatbot
from sources import FileReportSource


def test_citations_attached_by_code():
    data = {'insufficient_evidence':False,'sections':[{'text':'Wi-Fi chập chờn.', 'report_ids':[1,2]}]}
    result = OllamaProvider.assemble_answer(data,{1,2})
    assert '[PA1]' in result['answer'] and '[PA2]' in result['answer']
    Chatbot.validate_answer(result,{1,2})


def test_unknown_citation_rejected():
    data = {'insufficient_evidence':False,'sections':[{'text':'Wi-Fi chập chờn.', 'report_ids':[999]}]}
    with pytest.raises(ValueError):
        OllamaProvider.assemble_answer(data,{1,2})


def test_no_evidence_not_treated_as_failure():
    result = OllamaProvider.assemble_answer({'insufficient_evidence':True,'sections':[]},{1})
    assert result['answer'] == NO_EVIDENCE
    Chatbot.validate_answer(result,{1})


def test_invalid_output_retried_once(monkeypatch):
    provider = OllamaProvider(Settings())
    calls = []
    def structured(*args):
        calls.append(args)
        if len(calls)==1:
            return {'answer':'Wrong shape'}
        return {'insufficient_evidence':False,'sections':[{'text':'Mất kết nối.', 'report_ids':[1]}]}
    monkeypatch.setattr(provider,'structured',structured)
    reports = FileReportSource(Settings().reports_path).load_reports()[:1]
    assert provider.answer('wifi?',reports)['report_ids'] == [1]
    assert len(calls) == 2


def test_errors_distinguished():
    assert explain_ai_error(httpx.ReadTimeout('raw secret'))[0] == 'AI_TIMEOUT'
    assert explain_ai_error(httpx.ConnectError('raw secret'))[0] == 'AI_CONNECTION'
    code,message=explain_ai_error(ValueError('raw student data'))
    assert code == 'AI_RESPONSE_INVALID' and 'raw student data' not in message


def test_timeout_not_retried(monkeypatch):
    provider=OllamaProvider(Settings())
    calls=[]
    def fail(*args):
        calls.append(1)
        raise httpx.ReadTimeout('slow')
    monkeypatch.setattr(provider,'structured',fail)
    with pytest.raises(httpx.ReadTimeout):
        provider.answer('wifi',FileReportSource(Settings().reports_path).load_reports()[:1])
    assert len(calls)==1
