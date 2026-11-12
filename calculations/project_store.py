"""SQLite storage of the designed aircraft (data/projects/projects.sqlite3).

A second database, separate from the catalogue of comparison aircraft
(data/aircraft/aircraft.sqlite3). It holds everything that defines a designed
aircraft: the example projects (presets), the official course topics with their
starting parameters and requirements, and the user's own projects. The code keeps
no project or topic data of its own. BIPOL_PROJECTS_DB selects another file.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'data' / 'projects' / 'projects.sqlite3'
SCHEMA_VERSION = 1

SCHEMA = f"""
CREATE TABLE presets (
    key        TEXT PRIMARY KEY CHECK (key <> '' AND key NOT GLOB '*[^a-z0-9_]*'),
    sort_order INTEGER NOT NULL UNIQUE,
    name       TEXT NOT NULL CHECK (trim(name) <> ''),
    parameters TEXT NOT NULL CHECK (json_valid(parameters))
) STRICT;

CREATE TABLE topic_categories (
    key        TEXT PRIMARY KEY CHECK (key <> ''),
    sort_order INTEGER NOT NULL UNIQUE,
    label      TEXT NOT NULL
) STRICT;

CREATE TABLE topics (
    num          INTEGER PRIMARY KEY CHECK (num > 0),
    id           TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL CHECK (trim(title) <> ''),
    category     TEXT NOT NULL REFERENCES topic_categories (key),
    defaults     TEXT NOT NULL CHECK (json_valid(defaults)),
    parameters   TEXT NOT NULL CHECK (json_valid(parameters)),
    requirements TEXT NOT NULL CHECK (json_valid(requirements))
) STRICT;

-- The user's projects: one JSON document per project (parameters, summary, checklists).
CREATE TABLE projects (
    id         TEXT PRIMARY KEY CHECK (length(id) BETWEEN 1 AND 128 AND id NOT GLOB '*[^A-Za-z0-9_.-]*'),
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    document   TEXT NOT NULL CHECK (json_valid(document))
) STRICT;

PRAGMA user_version = {SCHEMA_VERSION};
"""


def database_path():
    return Path(os.environ.get('BIPOL_PROJECTS_DB') or DEFAULT_PATH)


@contextmanager
def connect(path=None, create=False):
    implicit_path = path is None
    path = Path(path or database_path())
    if implicit_path and not create and not path.is_file():
        from production import initialize_projects
        initialize_projects(path)
    if not create and not path.is_file():
        raise FileNotFoundError(f'Brak bazy projektów: {path}')
    con = sqlite3.connect(f'{path.resolve().as_uri()}?mode={"rwc" if create else "rw"}', uri=True,
                          timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    try:
        if not create:
            version = con.execute('PRAGMA user_version').fetchone()[0]
            if version not in (SCHEMA_VERSION, 3):
                raise RuntimeError(f'Nieobsługiwana wersja schematu bazy projektów: {version} (oczekiwano {SCHEMA_VERSION}).')
        yield con
    finally:
        con.close()


@contextmanager
def transaction(path=None):
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        try:
            yield con
        except BaseException:
            con.execute('ROLLBACK')
            raise
        con.execute('COMMIT')


def create_database(path, presets, categories, topics):
    """New database with presets {key: parameters}, categories {key: label} and topics."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f'Baza już istnieje: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path, create=True) as con:
        con.executescript(SCHEMA)
        con.execute('BEGIN IMMEDIATE')
        for order, (key, params) in enumerate(presets.items(), start=1):
            con.execute('INSERT INTO presets VALUES (?, ?, ?, ?)', (key, order, params['name'], json.dumps(params)))
        for order, (key, label) in enumerate(categories.items(), start=1):
            con.execute('INSERT INTO topic_categories VALUES (?, ?, ?)', (key, order, label))
        for topic in topics:
            con.execute('INSERT INTO topics VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (topic['num'], topic['id'], topic['title'], topic['category'], json.dumps(topic['defaults']),
                         json.dumps(topic['parameters']), json.dumps(topic['requirements'])))
        con.execute('COMMIT')


# --- Public course data, with safe updates of recognized defaults -----------------------------
def _jar_categories(params):
    """Stored CS-23 Amdt 5 level keys are read as the JAR categories of the course regulations."""
    from calculations.polish_law import stored_category
    if isinstance(params, dict) and params.get('category'):
        params['category'] = stored_category(params)
        if params.get('category_seed'):
            params['category_seed'] = params['category']
    return params


def load_presets(path=None):
    with connect(path) as con:
        rows = con.execute('SELECT key, parameters FROM presets ORDER BY sort_order').fetchall()
    return {row['key']: _jar_categories(json.loads(row['parameters'])) for row in rows}


def load_categories(path=None):
    with connect(path) as con:
        rows = con.execute('SELECT key, label FROM topic_categories ORDER BY sort_order').fetchall()
    return {row['key']: row['label'] for row in rows}


def load_topics(path=None):
    with connect(path) as con:
        from calculations.course_catalog import refresh_unchanged_topics
        refresh_unchanged_topics(con)
        rows = con.execute('SELECT * FROM topics ORDER BY num').fetchall()
    return [dict(id=row['id'], num=row['num'], title=row['title'], category=row['category'], defaults=json.loads(row['defaults']),
                 parameters=_jar_categories(json.loads(row['parameters'])), requirements=json.loads(row['requirements']))
            for row in rows]


# --- The user's projects --------------------------------------------------------------------
def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def list_projects(path=None):
    with connect(path) as con:
        rows = con.execute('SELECT document FROM projects ORDER BY updated_at DESC, id').fetchall()
    return [json.loads(row['document']) for row in rows]


def get_project(project_id, path=None):
    with connect(path) as con:
        row = con.execute('SELECT document FROM projects WHERE id = ?', (project_id,)).fetchone()
    return json.loads(row['document']) if row else None


def save_project(project, path=None):
    """Insert or replace one project document; returns the stored document."""
    if not isinstance(project, dict) or not isinstance(project.get('id'), str) or not isinstance(project.get('params'), dict):
        raise ValueError('Projekt musi mieć identyfikator (id) i parametry (params).')
    document = dict(project)
    document.setdefault('createdAt', _now())
    document['updatedAt'] = document.get('updatedAt') or _now()
    with transaction(path) as con:
        con.execute('INSERT INTO projects (id, name, created_at, updated_at, document) VALUES (?, ?, ?, ?, ?) '
                    'ON CONFLICT (id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at, '
                    'document = excluded.document',
                    (document['id'], str(document.get('name') or ''), document['createdAt'], document['updatedAt'],
                     json.dumps(document)))
    return document


def delete_project(project_id, path=None):
    with transaction(path) as con:
        return con.execute('DELETE FROM projects WHERE id = ?', (project_id,)).rowcount > 0
