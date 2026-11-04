"""Maintenance commands for the reference aircraft database (data/aircraft/aircraft.sqlite3).

Usage:
  python tools/aircraft_db.py check [DB]          integrity, foreign keys, record counts
  python tools/aircraft_db.py dump [DB]           SQL text of the whole database (git diff, backup)
  python tools/aircraft_db.py export SOURCE [DB]  stored records of one source as JSON

DB defaults to BIPOL_AIRCRAFT_DB or data/aircraft/aircraft.sqlite3. Readable git diffs:
  git config diff.sqlite3.textconv "python tools/aircraft_db.py dump"
"""
import argparse
from contextlib import closing
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def check(path):
    from calculations import aircraft_store
    with aircraft_store.connect(path) as con:
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        foreign_keys = con.execute('PRAGMA foreign_key_check').fetchall()
        counts = con.execute('SELECT source_id, aircraft_type, COUNT(*) FROM aircraft '
                             'GROUP BY source_id, aircraft_type ORDER BY source_id, aircraft_type').fetchall()
    print(f'integrity_check: {integrity}; foreign_key_check: {len(foreign_keys)} problems')
    for source_id, aircraft_type, count in counts:
        print(f'  {source_id:16} {aircraft_type:20} {count:4}')
    print(f'  total {sum(row[2] for row in counts)}')
    return integrity == 'ok' and not foreign_keys


def dump(path):
    # Git textconv applies to *both* stores and historical schema versions.
    # Never import the app or run migrations just to display a diff.
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro', uri=True)) as con:
        con.execute('BEGIN')
        print(f'PRAGMA user_version = {con.execute("PRAGMA user_version").fetchone()[0]};')
        for line in con.iterdump():
            print(line)
    return True


def export(source_id, path):
    from calculations import aircraft_store
    if source_id not in aircraft_store.load_sources(path):
        print(f'Nieznane źródło: {source_id}', file=sys.stderr)
        return False
    json.dump(aircraft_store.export_source(source_id, path), sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
    print()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'dump'):
        commands.add_parser(name).add_argument('db', nargs='?', type=Path)
    exporter = commands.add_parser('export')
    exporter.add_argument('source')
    exporter.add_argument('db', nargs='?', type=Path)
    args = parser.parse_args()
    args.db = args.db or Path(os.environ.get('BIPOL_AIRCRAFT_DB') or ROOT / 'data/aircraft/aircraft.sqlite3')
    sys.stdout.reconfigure(encoding='utf-8')
    ok = export(args.source, args.db) if args.command == 'export' else {'check': check, 'dump': dump}[args.command](args.db)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
