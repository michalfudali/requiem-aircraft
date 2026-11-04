"""Production startup must retain database changes across restarts/deployments."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3

import pytest

from production import check_database, initialize_database, initialize_projects, check_projects


def test_new_volume_is_seeded_and_later_startup_preserves_user_edits(tmp_path):
    path = tmp_path / 'persistent' / 'aircraft.sqlite3'
    initialize_database(path)
    assert check_database(path) > 800
    with closing(sqlite3.connect(path)) as con:
        aircraft_id = con.execute('SELECT id FROM aircraft LIMIT 1').fetchone()[0]
        con.execute('UPDATE aircraft SET model = ? WHERE id = ?', ('Własna nazwa zachowana po restarcie', aircraft_id))
        con.commit()
    initialize_database(path)
    with closing(sqlite3.connect(path)) as con:
        assert con.execute('SELECT model FROM aircraft WHERE id = ?', (aircraft_id,)).fetchone()[0] == 'Własna nazwa zachowana po restarcie'


def test_concurrent_initialization_creates_one_complete_catalogue(tmp_path):
    path = tmp_path / 'aircraft.sqlite3'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: initialize_database(path), range(2))) == [path, path]
    assert check_database(path) > 800
    assert not list(tmp_path.glob('.aircraft-*'))


def test_damaged_existing_database_is_never_replaced_by_seed(tmp_path):
    path = tmp_path / 'aircraft.sqlite3'
    path.write_bytes(b'uszkodzona baza do odzyskania')
    with pytest.raises(sqlite3.DatabaseError):
        initialize_database(path)
    assert path.read_bytes() == b'uszkodzona baza do odzyskania'


def test_public_course_seed_bootstraps_without_private_projects_and_preserves_later_changes(tmp_path):
    path = tmp_path / 'private/projects.sqlite3'
    initialize_projects(path)
    assert check_projects(path) == 110
    with closing(sqlite3.connect(path)) as con:
        assert con.execute('SELECT COUNT(*) FROM presets').fetchone()[0] == 10
        assert con.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 0
        con.execute("INSERT INTO projects VALUES ('private', 'Projekt prywatny', '', '', '{}')")
        con.commit()
    before = path.read_bytes()
    initialize_projects(path)
    assert path.read_bytes() == before


def test_concurrent_project_initialization_is_atomic(tmp_path):
    path = tmp_path / 'projects.sqlite3'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: initialize_projects(path), range(2))) == [path, path]
    assert check_projects(path) == 110
    assert not list(tmp_path.glob('.projects-*'))


def test_damaged_existing_projects_are_not_overwritten(tmp_path):
    path = tmp_path / 'projects.sqlite3'
    path.write_bytes(b'uszkodzona baza projektow')
    with pytest.raises(sqlite3.DatabaseError):
        initialize_projects(path)
    assert path.read_bytes() == b'uszkodzona baza projektow'


def test_database_location_is_explicit_and_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'data' / 'catalogue.sqlite3'
    monkeypatch.setenv('BIPOL_AIRCRAFT_DB', str(path))
    assert initialize_database() == path
    assert check_database(path) > 800


def test_health_reports_database_availability_without_exposing_file_paths(client, monkeypatch, tmp_path):
    response = client.get('/healthz')
    assert response.status_code == 200 and response.json['status'] == 'ok'
    monkeypatch.setenv('BIPOL_AIRCRAFT_DB', str(tmp_path / 'missing.sqlite3'))
    response = client.get('/healthz')
    assert response.status_code == 503 and response.json == {'status': 'unavailable'}
