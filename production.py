"""Initialize persistent storage, then replace this process with Gunicorn."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SEED_DATABASE = ROOT / 'data' / 'aircraft' / 'aircraft.sqlite3'
SEED_PROJECTS = ROOT / 'data' / 'projects' / 'projects.sqlite3'
# Older schema versions are upgraded in place by calculations.aircraft_store on first use.
AIRCRAFT_SCHEMA_VERSIONS = (1, 2, 3)


def check_database(path, readonly=False):
    mode = 'ro' if readonly else 'rw'
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=' + mode, uri=True)) as con:
        if con.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Kontrola integralności bazy samolotów nie powiodła się.')
        if con.execute('PRAGMA user_version').fetchone()[0] not in AIRCRAFT_SCHEMA_VERSIONS:
            raise RuntimeError('Nieobsługiwana wersja schematu bazy samolotów.')
        con.execute('SELECT revision FROM catalog_state WHERE singleton = 1').fetchone()
        return con.execute('SELECT COUNT(*) FROM aircraft').fetchone()[0]


def initialize_database(target=None, seed=SEED_DATABASE):
    """Seed a new volume once; preserve all records on subsequent deployments."""
    target = Path(target or os.environ.get('BIPOL_AIRCRAFT_DB') or SEED_DATABASE)
    if target.exists():
        check_database(target)
        return target
    check_database(seed, readonly=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.aircraft-', suffix='.sqlite3', dir=target.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(Path(seed).resolve().as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
        check_database(temporary)
        # Atomic creation without replacing a database created by another starter.
        try:
            os.link(temporary, target)
        except FileExistsError:
            pass
        check_database(target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def check_projects(path, readonly=False):
    mode = 'ro' if readonly else 'rw'
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=' + mode, uri=True)) as con:
        if con.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Kontrola integralności bazy projektów nie powiodła się.')
        return con.execute('SELECT COUNT(*) FROM topics').fetchone()[0]


def initialize_projects(target=None, seed=SEED_PROJECTS):
    """The projects database (presets, topics, user projects) is seeded once like the catalogue."""
    target = Path(target or os.environ.get('BIPOL_PROJECTS_DB') or seed)
    if target.exists():
        check_projects(target)
        return target
    check_projects(seed, readonly=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.projects-', suffix='.sqlite3', dir=target.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(Path(seed).resolve().as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
        try:
            os.link(temporary, target)
        except FileExistsError:
            pass
        check_projects(target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def main():
    initialize_database()
    initialize_projects()
    os.chdir(ROOT)
    os.execv(sys.executable, [sys.executable, '-m', 'gunicorn', '--config',
                            str(ROOT / 'gunicorn.conf.py'), 'app:app'])


if __name__ == '__main__':
    main()
