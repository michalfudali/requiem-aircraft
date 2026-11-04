"""Check shipped SQLite databases without importing or starting the application."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import runpy
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]


def check_database(path, store):
    """Read-only validation against the schema declared by the selected store."""
    definition = runpy.run_path(str(ROOT / 'calculations' / f'{store}_store.py'))
    with closing(sqlite3.connect(':memory:')) as expected:
        expected.executescript(definition['SCHEMA'])
        tables = {row[0] for row in expected.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro', uri=True)) as con:
            version = con.execute('PRAGMA user_version').fetchone()[0]
            if version != definition['SCHEMA_VERSION']:
                raise ValueError(f'{store}: schema {version}, expected {definition["SCHEMA_VERSION"]}')
            actual = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if actual != tables:
                raise ValueError(f'{store}: missing tables {sorted(tables-actual)}, unexpected tables {sorted(actual-tables)}')
            for table in sorted(tables):
                if con.execute(f'PRAGMA table_info({table})').fetchall() != expected.execute(f'PRAGMA table_info({table})').fetchall():
                    raise ValueError(f'{store}: incompatible columns in {table}')
            integrity = con.execute('PRAGMA integrity_check').fetchall()
            if integrity != [('ok',)]:
                raise ValueError(f'{store}: integrity_check failed: {integrity}')
            foreign_keys = con.execute('PRAGMA foreign_key_check').fetchall()
            if foreign_keys:
                raise ValueError(f'{store}: foreign_key_check failed: {foreign_keys}')
            return {'store': store, 'schema': version, 'integrity': 'ok',
                    'rows': {table: con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in sorted(tables)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aircraft-db', type=Path, default=ROOT / 'data/aircraft/aircraft.sqlite3')
    parser.add_argument('--projects-db', type=Path, default=ROOT / 'data/projects/projects.sqlite3')
    args = parser.parse_args()
    if not args.projects_db.exists() and args.projects_db == ROOT / 'data/projects/projects.sqlite3':
        # The private SQLite store is generated from public course data on a fresh checkout.
        sys.path.insert(0, str(ROOT))
        from production import initialize_projects
        initialize_projects(args.projects_db)
    errors = []
    for store, path in (('aircraft', args.aircraft_db), ('project', args.projects_db)):
        try:
            print(json.dumps(check_database(path, store), ensure_ascii=False))
        except (ValueError, sqlite3.Error, OSError) as error:
            errors.append(str(error))
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
