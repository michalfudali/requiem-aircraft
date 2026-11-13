"""Existing catalogues may upgrade defaults without replacing any personal data."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from calculations import project_store
from calculations.course_catalog import COLUMNS, JSON_COLUMNS, ROOT, refresh_unchanged_topics
from production import initialize_projects


HISTORY = json.loads((ROOT/'topic_history.json').read_text(encoding='utf8'))['known_defaults']


def replace_record(connection, record):
    columns = [key for key in COLUMNS if key != 'num']
    values = [json.dumps(record[key], ensure_ascii=False) if key in JSON_COLUMNS else record[key] for key in columns]
    connection.execute('UPDATE topics SET '+','.join(key+'=?' for key in columns)+' WHERE num=?', (*values, record['num']))


@pytest.fixture
def legacy(tmp_path):
    path = tmp_path/'projects.sqlite3'
    initialize_projects(path)
    with project_store.connect(path) as con:
        for item in HISTORY[:2]:
            replace_record(con, item['topic'])
    project_store.save_project(dict(id='personal-aircraft', name='Własny wariant',
                                   params=dict(airfoil='NACA 4415', aspect_ratio=19.25),
                                   checklist={'approved': False}), path)
    return path


def personal_document(path):
    with project_store.connect(path) as con:
        return con.execute('SELECT document FROM projects WHERE id=?', ('personal-aircraft',)).fetchone()[0]


def test_exact_legacy_topics_upgrade_to_the_current_geometry_and_airfoil(legacy):
    before = personal_document(legacy)
    topics = {t['num']: t for t in project_store.load_topics(legacy)}
    p = topics[7]['parameters']
    assert (p['aspect_ratio'], p['cruise_speed_kmh'], p['airfoil']) == (28, 115, 'FX 61-163')
    assert p['technology'] == 'composite' and p['empty_mass_closure'] == 'components'
    design = json.loads((ROOT.parent/'design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    assert p['airfoil_coordinates'] == design['airfoil_coordinates']
    assert len(p['airfoil_coordinates'].splitlines()) > 80
    assert topics[25]['parameters']['seats_config'] == 'tandem'
    assert personal_document(legacy) == before
    snapshot = legacy.read_bytes()
    project_store.load_topics(legacy)
    assert legacy.read_bytes() == snapshot


def test_later_legacy_id_revision_is_recognized_too(legacy):
    with project_store.connect(legacy) as con:
        replace_record(con, HISTORY[2]['topic'])
    assert next(t for t in project_store.load_topics(legacy) if t['num'] == 7)['parameters']['airfoil'] == 'FX 61-163'


@pytest.mark.parametrize('section', ['title', 'defaults', 'parameters', 'requirements'])
def test_any_local_edit_protects_the_complete_topic_record(legacy, section):
    edited = deepcopy(HISTORY[0]['topic'])
    if section == 'title':
        edited[section] = 'Temat 7 — własne założenia'
    else:
        edited[section]['local_author_note'] = 'Zachować bez nadpisywania'
    with project_store.connect(legacy) as con:
        replace_record(con, edited)
        before = dict(con.execute('SELECT * FROM topics WHERE num=7').fetchone())
    project_store.load_topics(legacy)
    with project_store.connect(legacy) as con:
        assert dict(con.execute('SELECT * FROM topics WHERE num=7').fetchone()) == before


def test_failed_catalog_update_rolls_back_every_topic_and_preserves_projects(legacy, tmp_path):
    seed = json.loads((ROOT/'course_seed.json').read_text(encoding='utf8'))
    next(t for t in seed['topics'] if t['num'] == 25)['category'] = 'missing-category'
    broken = tmp_path/'broken-seed.json'
    broken.write_text(json.dumps(seed), encoding='utf8')
    with project_store.connect(legacy) as con:
        before = [dict(t) for t in con.execute('SELECT * FROM topics ORDER BY num')]
        personal = personal_document(legacy)
        with pytest.raises(sqlite3.IntegrityError):
            refresh_unchanged_topics(con, seed_path=broken)
        assert [dict(t) for t in con.execute('SELECT * FROM topics ORDER BY num')] == before
        assert personal_document(legacy) == personal


def test_concurrent_readers_cannot_overwrite_each_others_catalogue(legacy):
    before = personal_document(legacy)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: project_store.load_topics(legacy), range(2)))
    assert all(next(t for t in topics if t['num'] == 7)['parameters']['aspect_ratio'] == 28 for topics in results)
    assert personal_document(legacy) == before


def test_already_current_database_is_not_rewritten(tmp_path):
    path = tmp_path/'current.sqlite3'
    initialize_projects(path)
    before = path.read_bytes()
    assert len(project_store.load_topics(path)) == 110
    assert path.read_bytes() == before


def test_last_published_topic_gains_the_explicit_energy_profile_and_preserves_personal_projects(legacy):
    old = HISTORY[-1]
    assert old['source_commit'].startswith('9de2d2b') and old['topic']['num'] == 7
    before = personal_document(legacy)
    with project_store.connect(legacy) as con:
        replace_record(con, old['topic'])
    p = next(t for t in project_store.load_topics(legacy) if t['num'] == 7)['parameters']
    assert (p['climb_fraction_mode'], p['mission_climb_rate_ms'], p['climb_start_speed_kmh']) == ('energy', 3., 115.)
    assert personal_document(legacy) == before
