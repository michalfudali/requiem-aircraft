"""SQLite catalogue: schema constraints, change detection, committed database and tools."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from calculations import aircraft_store, project_store
from calculations.trends import SOURCES, load_aircraft

ROOT = Path(__file__).resolve().parents[1]
VALID_ROW = dict(id='store-test-plane', source_id='geometry_trends', model='Store Test', manufacturer='Test',
                 aircraft_type='piston_ga', engine_type='prop', m0=1000.0, me=600.0, s=14.0, b=10.0, p_kw=100.0)


def test_committed_database_is_consistent():
    uri = f'{aircraft_store.DEFAULT_PATH.as_uri()}?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == aircraft_store.SCHEMA_VERSION
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        counts = dict(con.execute('SELECT source_id, COUNT(*) FROM aircraft GROUP BY source_id'))
    assert {'fast', 'cado', 'motogliders', 'geometry_trends'} <= set(counts) <= set(SOURCES)


def test_record_layout_matches_table_columns():
    with aircraft_store.connect() as con:
        names = [row['name'] for row in con.execute('PRAGMA table_info(aircraft)')]
    assert names == ['entry_no', *aircraft_store.COLUMN_NAMES]


@pytest.mark.parametrize('change', [
    {'me': 1000.0}, {'engine_type': 'jet', 't_kn': 10.0}, {'source_id': 'unknown_source'},
    {'id': 'bad id'}, {'m0': 'heavy'}, {'aircraft_type': 'airship'}, {'takeoff_basis': 'guess'},
    {'v_cruise_kmh': 100.0, 'v_stall_kmh': 120.0}, {'year': 1800}, {'model': '  '},
])
def test_database_rejects_invalid_rows_without_application_validation(isolated_db, change):
    before = len(load_aircraft())
    with pytest.raises(sqlite3.IntegrityError):
        with aircraft_store.transaction() as con:
            aircraft_store.insert(con, {**VALID_ROW, **change})
    assert len(load_aircraft()) == before


def test_duplicate_id_is_rejected_by_unique_constraint(isolated_db):
    with aircraft_store.transaction() as con:
        aircraft_store.insert(con, VALID_ROW)
    with pytest.raises(sqlite3.IntegrityError, match='UNIQUE'):
        with aircraft_store.transaction() as con:
            aircraft_store.insert(con, VALID_ROW)


def test_external_edit_is_seen_without_clearing_the_cache(isolated_db):
    first = load_aircraft()[0]
    # Another tool writes directly to the file (e.g. DB Browser for SQLite).
    with closing(sqlite3.connect(aircraft_store.database_path())) as con:
        con.execute("UPDATE aircraft SET model = 'Edited elsewhere' WHERE id = ?", (first['id'],))
        con.commit()
    assert load_aircraft()[0]['model'] == 'Edited elsewhere'


def test_unknown_fields_are_rejected_instead_of_dropped(client, isolated_db):
    payload = {**VALID_ROW, 'wing_span_typo': 11.0, 'source_references': 'Test'}
    response = client.post('/api/aircraft', json=payload)
    assert response.status_code == 400
    assert 'wing_span_typo' in response.json['message']


def test_new_records_without_source_go_to_the_user_source(client, isolated_db):
    assert 'user' in SOURCES and 'user' not in client.get('/api/aircraft').json['sources']
    payload = {key: value for key, value in VALID_ROW.items() if key != 'source_id'}
    response = client.post('/api/aircraft', json=payload)
    assert response.status_code == 201 and response.json['source_id'] == 'user'
    catalog = client.get('/api/aircraft').json
    assert catalog['sources']['user']['license_file'] == 'USER-DATA.txt'
    assert client.get('/download/aircraft/user/license').status_code == 200
    assert [r['id'] for r in json.loads(client.get('/download/aircraft/user/data').data)] == [VALID_ROW['id']]


def test_unknown_source_is_rejected(client, isolated_db):
    response = client.post('/api/aircraft', json={**VALID_ROW, 'source_id': 'my_notes'})
    assert response.status_code == 400 and 'my_notes' in response.json['message']


def test_missing_database_is_reported_and_not_created(tmp_path):
    missing = tmp_path / 'missing.sqlite3'
    with pytest.raises(FileNotFoundError):
        with aircraft_store.connect(missing):
            pass
    assert not missing.exists()


def test_projects_database_is_never_upgraded_into_a_catalogue(tmp_path):
    """Both databases start at schema version 1; only the catalogue may receive aircraft tables."""
    path = tmp_path / 'projects.sqlite3'
    shutil.copyfile(project_store.DEFAULT_PATH, path)
    with pytest.raises(RuntimeError, match='nie jest bazą samolotów'):
        with aircraft_store.connect(path):
            pass
    with project_store.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == project_store.SCHEMA_VERSION
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'engines'").fetchone()


def test_committed_projects_database_has_its_own_schema():
    with project_store.connect() as con:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {'presets', 'topic_categories', 'topics', 'projects'}


def test_new_database_round_trips_sources_and_records(tmp_path):
    path = tmp_path / 'new.sqlite3'
    sources = {'geometry_trends': SOURCES['geometry_trends']}
    aircraft_store.create_database(path, sources, [VALID_ROW])
    assert aircraft_store.load_sources(path) == sources
    _, records = aircraft_store.read_catalog(path=path)
    assert records == [{**dict.fromkeys(aircraft_store.COLUMN_NAMES), **VALID_ROW, 'variable_sweep': False}]
    with pytest.raises(FileExistsError):
        aircraft_store.create_database(path, sources)


def test_download_exports_the_stored_rows(client):
    response = client.get('/download/aircraft/cado/data')
    assert response.status_code == 200
    assert 'attachment' in response.headers['Content-Disposition']
    assert json.loads(response.data) == aircraft_store.export_source('cado')


@pytest.mark.parametrize('command,expected', [(['check'], 'integrity_check: ok'),
                                              (['dump'], 'CREATE TABLE aircraft'),
                                              (['export', 'motogliders'], '"source_id": "motogliders"')])
def test_maintenance_tool(command, expected):
    result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'aircraft_db.py'), *command],
                            capture_output=True, text=True, encoding='utf-8', timeout=60, env=os.environ)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
