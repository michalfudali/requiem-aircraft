"""Database identity, upgrade safety and startup regressions, including commit 9f5719a."""
from contextlib import closing
import hashlib
import os
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from calculations import aircraft_store, project_store
from database_sandbox import backup, ROOT


@pytest.mark.parametrize('store', [aircraft_store, project_store], ids=['aircraft', 'projects'])
def test_shipped_store_contract_and_integrity(store):
    # Bypass the application's connection/migration code: test the actual Git seed.
    with closing(sqlite3.connect(f'{store.DEFAULT_PATH.as_uri()}?mode=ro', uri=True)) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == store.SCHEMA_VERSION
        assert con.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []


def test_catalogue_must_not_migrate_the_project_database(tmp_path):
    path = tmp_path / 'wrong-kind.sqlite3'
    backup(project_store.DEFAULT_PATH, path)
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match='baza katalogu'):
        with aircraft_store.connect(path):
            pass
    assert path.read_bytes() == before
    # Specifically guard against adding reference/engine tables and changing v1 to v3.
    assert project_store.load_presets(path)


def test_catalogue_v1_upgrade_preserves_aircraft(tmp_path):
    path = tmp_path / 'old-catalogue.sqlite3'
    backup(aircraft_store.DEFAULT_PATH, path)
    before = aircraft_store.export_source('geometry_trends', path)
    with closing(sqlite3.connect(path)) as con:
        for table in ('aircraft_supplements', 'wetted_area_examples', 'model_examples', 'engines'):
            con.execute(f'DROP TABLE {table}')
        con.execute('PRAGMA user_version=1')
        con.commit()
    assert aircraft_store.export_source('geometry_trends', path) == before
    with aircraft_store.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == aircraft_store.SCHEMA_VERSION


@pytest.mark.parametrize('version', [0, 99])
def test_unknown_project_schema_is_rejected_without_mutation(tmp_path, version):
    path = tmp_path / 'future.sqlite3'
    backup(project_store.DEFAULT_PATH, path)
    with closing(sqlite3.connect(path)) as con:
        con.execute(f'PRAGMA user_version={version}')
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match='schematu'):
        project_store.load_topics(path)
    assert path.read_bytes() == before


def test_preflight_works_before_application_import_and_does_not_write(tmp_path):
    path = tmp_path / 'bad-projects.sqlite3'
    backup(project_store.DEFAULT_PATH, path)
    with closing(sqlite3.connect(path)) as con:
        con.execute('PRAGMA user_version=3')
    before = path.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / 'tools/check_databases.py'), '--projects-db', str(path)],
                            cwd=tmp_path, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 1
    assert 'project: schema 3, expected 1' in result.stderr
    assert 'Traceback' not in result.stderr
    assert path.read_bytes() == before


def test_startup_in_subprocess_reads_isolated_databases_from_any_directory(tmp_path):
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (aircraft_store.DEFAULT_PATH, project_store.DEFAULT_PATH)}
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8='1')
    result = subprocess.run([sys.executable, '-c',
        "from app import app; c=app.test_client(); "
        "assert c.get('/').status_code==200; assert c.get('/api/topics').status_code==200; "
        "assert c.get('/api/presets').status_code==200"], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())


def test_failed_test_cannot_leak_either_database_or_flask_config(tmp_path):
    # Run a deliberately failing test in another pytest process. The following
    # test must see the pristine stores despite WAL/subprocess-visible commits.
    (tmp_path / 'conftest.py').write_text((ROOT / 'tests/conftest.py').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'test_isolation_probe.py').write_text('''
import sqlite3
from contextlib import closing
from app import app
from calculations import aircraft_store, project_store

BASELINE = project_store.list_projects()

def test_mutate_then_fail():
    app.config['LEAK_PROBE'] = True
    project_store.save_project({'id': 'isolation-probe', 'params': {}})
    with closing(sqlite3.connect(aircraft_store.database_path())) as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute("UPDATE aircraft SET model='__leak_probe__' WHERE entry_no=(SELECT MIN(entry_no) FROM aircraft)")
        con.commit()
    assert False, 'intentional isolation probe'

def test_next_case_sees_pristine_state():
    assert project_store.list_projects() == BASELINE
    assert 'LEAK_PROBE' not in app.config
    with aircraft_store.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM aircraft WHERE model='__leak_probe__'").fetchone()[0] == 0
''', encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / 'tests'))),
               PYTHONUTF8='1', PYTEST_ADDOPTS='')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-c', str(ROOT / 'pytest.ini'),
                             str(tmp_path / 'test_isolation_probe.py'), '--junitxml=' + str(tmp_path / 'probe.xml')],
                            cwd=tmp_path, env=env, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 1, result.stdout + result.stderr
    cases = ET.parse(tmp_path / 'probe.xml').findall('.//testcase')
    assert len(cases) == 2
    failure = cases[0].find('failure')
    assert failure is not None and 'intentional isolation probe' in failure.get('message', ''), result.stdout
    assert cases[1].find('failure') is None, result.stdout
    assert cases[1].find('error') is None, result.stdout
