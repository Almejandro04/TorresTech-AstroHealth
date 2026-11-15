"""Isolated #9 import, rollback, chronology and API regressions."""
import json
import shutil
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.config import SEED_PATH
from app.database import connect, init_database
from app.database.ingestion import ImportFailure, import_mission
from app.database.__main__ import main
from app.main import create_app


def bundle_file(tmp_path, change=lambda b: None):
    bundle = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    change(bundle)
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def snapshot():
    with closing(connect()) as conn:
        return {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                for t in ("sources", "astronauts", "readings", "journal", "alerts", "sqlite_sequence")}


def test_staged_import_api_retry_and_backward_request(tmp_path):
    path = bundle_file(tmp_path)
    init_database()
    import_mission(path, until_day=3)
    before = snapshot()
    assert len(before["readings"]) == len(before["journal"]) == 3
    with TestClient(create_app()) as client:
        summary = client.get('/api/astronauts/AST-001/summary').json()
        assert summary['meta']['as_of'] == '2026-11-03T12:00:00Z'
        assert summary['data']['latest_metrics']['heart_rate_bpm']['mission_day'] == 3
        assert client.get('/api/astronauts/AST-001/readings', params={'from_day':4}).json()['data'] == []
        import_mission(path, until_day=5)
        expected = snapshot()
        repeated = import_mission(path, until_day=5)
        assert snapshot() == expected
        assert repeated['records']['readings'] == dict(created=0, repeated=5, updated=0)
        historical = client.get('/api/astronauts/AST-001/readings', params={'as_of':'2026-11-03T23:59:59Z'}).json()
        assert len(historical['data']) == 3
        assert client.get('/api/astronauts/AST-001/summary').json()['data']['mission_day'] == 5
        assert import_mission(path, until_day=3)['profiles_with_later_data'] == ['AST-001']
        assert snapshot() == expected


def csv_files(tmp_path):
    manifest = bundle_file(tmp_path)
    for name in ('readings.csv','journal.csv'):
        shutil.copyfile(SEED_PATH.parent / name, tmp_path / name)
    return manifest


def test_csv_equivalent_bom_and_no_json_observations(tmp_path):
    manifest = csv_files(tmp_path)
    import_mission(manifest)
    expected = snapshot()
    # Selected CSV must ignore even invalid observation arrays in the manifest.
    raw = json.loads(manifest.read_text())
    raw['readings'] = 'DO NOT IMPORT JSON'
    raw['journal'] = [{'invalid': True}]
    manifest.write_text(json.dumps(raw), encoding='utf-8-sig')
    csv_path = tmp_path/'readings.csv'
    csv_path.write_text(csv_path.read_text(), encoding='utf-8-sig')
    import_mission(manifest, readings='readings.csv', journal='journal.csv')
    assert snapshot() == expected


@pytest.mark.parametrize('change', [
    lambda b: b.update(schema_version='9'),
    lambda b: b.update(extra=[]),
    lambda b: b.update(readings={}),
    lambda b: b['readings'][-1].update(heart_rate_bpm='83'),
    lambda b: b['readings'][-1].update(heart_rate_bpm=True),
    lambda b: b['readings'][-1].update(heart_rate_bpm=float('nan')),
    lambda b: b['readings'][-1].update(heart_rate_bpm=float('inf')),
    lambda b: b['readings'][-1].update(source_type='terrestrial_biomedical'),
    lambda b: b['readings'][-1].update(source_id='MISSING'),
    lambda b: b['readings'][-1].update(astronaut_id='MISSING'),
    lambda b: b['readings'][-1].update(mission_day=6),
    lambda b: b['readings'][-1].update(measurement_context='medical'),
    lambda b: b['journal'][-1].pop('notes'),
    lambda b: b['astronauts'][0].update(is_fictional=False),
    lambda b: b['readings'].append({**b['readings'][0], 'heart_rate_bpm':99}),
    lambda b: b['journal'].append({**b['journal'][0], 'notes':'conflict'}),
])
def test_invalid_entire_bundle_preserves_previous_rows_even_future(tmp_path, change):
    path = bundle_file(tmp_path)
    import_mission(path, until_day=2)
    before = snapshot()
    invalid = bundle_file(tmp_path, change)
    with pytest.raises(ImportFailure):
        import_mission(invalid, until_day=3)
    assert snapshot() == before


@pytest.mark.parametrize('kind', ['readings','journal','astronauts','source'])
def test_stored_conflicts_preserve_all_rows(tmp_path, kind):
    path = bundle_file(tmp_path)
    import_mission(path)
    before = snapshot()
    def change(b):
        if kind == 'source': b[kind]['description'] = 'different'
        elif kind == 'astronauts': b[kind][0]['name'] = 'different'
        elif kind == 'readings': b[kind][0]['heart_rate_bpm'] = 99
        else: b[kind][0]['notes'] = 'corrected'
    with pytest.raises(ImportFailure):
        import_mission(bundle_file(tmp_path, change))
    assert snapshot() == before


def test_explicit_journal_update_keeps_id_and_is_atomic(tmp_path):
    path = bundle_file(tmp_path)
    import_mission(path)
    with TestClient(create_app()) as client:
        old = client.get('/api/astronauts/AST-001/journal').json()['data'][0]
        path = bundle_file(tmp_path, lambda b: b['journal'][0].update(notes='updated'))
        report = import_mission(path, update_journal=True)
        new = client.get('/api/astronauts/AST-001/journal').json()['data'][0]
        assert new['journal_id'] == old['journal_id'] and new['notes'] == 'updated'
        assert report['records']['journal']['updated'] == 1
        before = snapshot()
        raw = json.loads(path.read_text()); raw['journal'][0]['notes']='should roll back'; raw['journal'][-1]['source_id']='missing'
        path.write_text(json.dumps(raw))
        with pytest.raises(ImportFailure): import_mission(path, update_journal=True)
        assert snapshot() == before


@pytest.mark.parametrize('edit', [
    lambda s: s.replace('heart_rate_bpm,','wrong,'),
    lambda s: s.replace('heart_rate_bpm,','timestamp,'),
    lambda s: s.replace(',source_id',''),
    lambda s: s.replace(',72,98,',',NaN,98,'),
    lambda s: s.replace(',72,98,',',null,98,'),
    lambda s: s.replace(',72,98,',',N/A,98,'),
    lambda s: s.replace(',1,72,',',true,72,'),
    lambda s: s.replace(',72,98,',',72,98,extra,'),
    lambda s: s.replace(',72,98,',',98,'),
    lambda s: s.replace('AST-001,',' ,'),
])
def test_invalid_csv_rolls_back_with_file_location(tmp_path, edit):
    manifest = csv_files(tmp_path)
    import_mission(manifest, until_day=1)
    before = snapshot()
    path=tmp_path/'readings.csv'
    path.write_text(edit(path.read_text()), encoding='utf-8')
    with pytest.raises(ImportFailure, match='readings.csv'):
        import_mission(manifest, readings='readings.csv', journal='journal.csv')
    assert snapshot() == before


def test_day_includes_all_fraction_digits_and_keeps_null_zero(tmp_path):
    path = bundle_file(tmp_path, lambda b: (
        b['readings'][2].update(timestamp='2026-11-03T23:59:59.999999999999Z', respiratory_rate_bpm=None),
        b['journal'][2].update(sleep_hours_last_night=0)))
    import_mission(path, until_day=3)
    with TestClient(create_app()) as client:
        r=client.get('/api/astronauts/AST-001/readings').json()
        assert r['meta']['total']==3 and r['data'][-1]['timestamp'].endswith('.999999999999Z')
        assert r['data'][-1]['respiratory_rate_bpm'] is None
        assert client.get('/api/astronauts/AST-001/journal').json()['data'][-1]['sleep_hours_last_night']==0


def test_cli_reports_failure_without_created_counts(tmp_path, capsys):
    path=bundle_file(tmp_path)
    assert main(['import-json', str(path), '--until-day','3'])==0
    report=json.loads(capsys.readouterr().out)
    assert report['committed'] and report['post_import']['evaluation_status']=='not_implemented'
    before=snapshot()
    bundle_file(tmp_path, lambda b:b['journal'][-1].update(mood_score=99))
    assert main(['import-json', str(path)])==1
    error=json.loads(capsys.readouterr().err)
    assert not error['committed'] and error['created']==0 and error['rejected']>0
    assert snapshot()==before


@pytest.mark.parametrize('value', [[], None, 'not an object'])
def test_invalid_top_level_is_reported(tmp_path, value, capsys):
    path=tmp_path/'bad.json'; path.write_text(json.dumps(value))
    assert main(['import-json',str(path)])==1
    assert not json.loads(capsys.readouterr().err)['committed']


def test_bad_second_csv_keeps_all_previous_content(tmp_path):
    manifest=csv_files(tmp_path)
    import_mission(manifest, until_day=1)
    before=snapshot()
    path=tmp_path/'journal.csv'
    path.write_text(path.read_text().replace(',5.5,2,', ',5.5,99,'))
    with pytest.raises(ImportFailure, match='journal.csv'):
        import_mission(manifest,readings='readings.csv',journal='journal.csv',until_day=3)
    assert snapshot()==before


def test_fresh_invalid_reference_rolls_back_metadata_too(tmp_path):
    init_database()
    before=snapshot()
    path=bundle_file(tmp_path,lambda b:b['journal'][-1].update(source_id='MISSING'))
    with pytest.raises(ImportFailure): import_mission(path,until_day=1)
    assert snapshot()==before


@pytest.mark.parametrize('text', ['{"schema_version":"0.1.0","schema_version":"0.1.0"}',
                                '{"unknown":NaN}', '{"unknown":1e9999}'])
def test_invalid_json_constants_and_duplicate_keys_leave_data_unchanged(tmp_path, text):
    init_database()
    before=snapshot()
    path=tmp_path/'bad.json'; path.write_text(text)
    with pytest.raises(ImportFailure): import_mission(path)
    assert snapshot()==before
