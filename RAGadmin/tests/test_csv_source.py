import csv
import json
from datetime import timedelta

import pytest
from config import BASE, Settings
from sources import FileReportSource
from rag import Chatbot
from planner import QueryPlan


def test_sample_loads_correctly(caplog):
    reports = FileReportSource(BASE / 'data/rag_knowledge.csv').load_reports()
    assert len(reports) == 28
    assert len({r.incident_id for r in reports}) == 7
    first = reports[0]
    assert first.report_id == 14 and first.building == 'A1'
    assert first.created_at.isoformat() == '2026-10-02T21:21:11+07:00'
    assert first.category == 'SANITATION'
    assert 'sai header' in caplog.text


@pytest.mark.parametrize('question, reports, incidents', [
    ('Có bao nhiêu phản ánh?', 28, 7),
    ('Có bao nhiêu sự cố?', 28, 7),
    ('Có bao nhiêu phản ánh về mạng ở H1?', 4, 1),
    ('Có bao nhiêu phản ánh về máy chiếu?', 4, 1),
    ('Có bao nhiêu phản ánh về cơ sở vật chất?', 4, 1),
    ('Có bao nhiêu phản ánh về học phí?', 5, 1),
    ('Có bao nhiêu phản ánh về vệ sinh?', 6, 2),
    ('Có bao nhiêu phản ánh về điện?', 4, 1),
    ('Có bao nhiêu phản ánh về an ninh?', 5, 1),
    ('Có bao nhiêu phản ánh ở A1?', 2, 1),
    ('Có bao nhiêu phản ánh ngày 02/10/2026?', 28, 7),
    ('Có bao nhiêu phản ánh ngày 03/10/2026?', 0, 0),
    ('Có bao nhiêu phản ánh chưa xử lý?', 15, 4),
])
def test_csv_count(question, reports, incidents):
    settings = Settings(reports_path=BASE / 'data/rag_knowledge.csv')
    bot = Chatbot(settings, FileReportSource(settings.reports_path))
    bot.sync()
    result = bot.chat(question, top_k=1)
    assert result['statistics']['report_count'] == reports
    assert result['statistics']['incident_count'] == incidents


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def sample_row():
    return dict(report_id='1', category='Mạng / Đường truyền', building='Tòa nhà H1',
                room='01', description='Mạng yếu,\nkhông kết nối được', incident_id='',
                incident_status='', confidence='0.9', created_at='2026-10-02 12:30:00')


def test_correct_header_bom_quotes_and_nulls(tmp_path):
    path = tmp_path / 'data.csv'
    row = sample_row(); write_csv(path, [row])
    report, = FileReportSource(path).load_reports()
    assert report.incident_id is None and report.incident_status is None
    assert report.room == '01' and report.raw_text == row['description']
    assert report.created_at.utcoffset() == timedelta(hours=7)
    row.pop('confidence'); row['content'] = 'Report #1'; row['created_at'] = '2026-10-02T05:30:00Z'
    write_csv(path, [row])
    report, = FileReportSource(path).load_reports()
    assert report.created_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize('change', ['duplicate', 'time', 'category', 'missing', 'status'])
def test_invalid_csv_rejected(tmp_path, change):
    path = tmp_path / 'data.csv'; row = sample_row(); rows = [row]
    if change == 'duplicate': rows.append(dict(row))
    if change == 'time': row['created_at'] = 'khong phai ngay'
    if change == 'category': row['category'] = 'unknown category'
    if change == 'missing': row.pop('description')
    if change == 'status': row['incident_status'] = 'RESOLVED'
    write_csv(path, rows)
    with pytest.raises(ValueError): FileReportSource(path).load_reports()


def test_json_compatibility_and_snapshot_on_failure(tmp_path):
    reports = FileReportSource(BASE / 'data/phananh.json').load_reports()
    assert reports
    path = tmp_path / 'data.csv'; write_csv(path, [sample_row()])
    bot = Chatbot(Settings(reports_path=path), FileReportSource(path)); bot.sync()
    snapshot = bot.snapshot
    path.write_text('bad header\n')
    with pytest.raises(ValueError): bot.sync()
    assert bot.snapshot is snapshot


def test_planner_schema_includes_csv_categories():
    schema = QueryPlan.model_json_schema()
    assert 'STUDENT_SERVICE' in json.dumps(schema)
    assert 'SANITATION' in json.dumps(schema)
