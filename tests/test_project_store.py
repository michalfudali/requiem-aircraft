"""Previously untested second SQLite store: persistence, rollback and API documents."""
from copy import deepcopy
import sqlite3

import pytest

from calculations import project_store
from calculations.presets import AIRCRAFT_PRESETS


def test_project_api_roundtrip_update_and_delete(client):
    initial = client.get('/api/projects').json['projects']
    project = {'id': 'test-project-api', 'name': 'Próba motoszybowca',
               'params': deepcopy(AIRCRAFT_PRESETS['motoglider_aos']), 'checklists': {'p1': True}}
    saved = client.put('/api/projects/' + project['id'], json=project)
    assert saved.status_code == 200, saved.get_data(as_text=True)
    assert saved.json['project']['params'] == project['params']
    assert saved.json['project']['checklists'] == project['checklists']
    project['name'] = 'Zmieniony projekt'
    assert client.put('/api/projects/' + project['id'], json=project).status_code == 200
    projects = client.get('/api/projects').json['projects']
    assert len(projects) == len(initial) + 1
    assert next(p for p in projects if p['id'] == project['id'])['name'] == project['name']
    assert client.delete('/api/projects/' + project['id']).json['deleted'] is True
    assert client.delete('/api/projects/' + project['id']).json['deleted'] is False
    assert client.get('/api/projects').json['projects'] == initial


@pytest.mark.parametrize('payload', [None, [], {}, {'id': 'another', 'params': {}}])
def test_project_api_rejects_mismatched_identity_without_saving(client, payload):
    before = project_store.list_projects()
    response = client.put('/api/projects/test-project-api', json=payload)
    assert response.status_code == 400
    assert project_store.list_projects() == before


def test_project_transaction_rolls_back_all_writes():
    before = project_store.list_projects()
    with pytest.raises(sqlite3.IntegrityError):
        with project_store.transaction() as con:
            con.execute("DELETE FROM projects")
            con.execute("INSERT INTO projects VALUES ('invalid id', '', '', '', '{}')")
    assert project_store.list_projects() == before


def test_project_and_reference_database_paths_are_separate_and_private():
    from calculations import aircraft_store
    assert project_store.database_path() != project_store.DEFAULT_PATH
    assert aircraft_store.database_path() != aircraft_store.DEFAULT_PATH
    assert project_store.database_path() != aircraft_store.database_path()
