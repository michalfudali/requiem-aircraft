"""Validate and apply independently sourced aircraft observations, without network access.

The versioned manifest is the reproducible import input, not a second live
catalogue. Application calculations continue to read SQLite only.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from calculations.primary_research import MANIFEST, SOURCE_ID, SOURCE, validate_manifest  # noqa: E402


def apply_manifest(data, path, check=False):
    rows = validate_manifest(data)
    # Source registration belongs to the same atomic import as its records.
    if str(ROOT) not in sys.path:
        sys.path.insert(0,str(ROOT))
    from calculations import aircraft_store
    from calculations.aircraft_db import validate_aircraft
    rows = [validate_aircraft(row) for row in rows]
    if check:
        return dict(records=len(rows),families=len({(r['aircraft_type'],r['family']) for r in rows}),changed=0)
    changed = 0
    with aircraft_store.transaction(path) as con:
        existing_source = con.execute('SELECT * FROM sources WHERE id=?',(SOURCE_ID,)).fetchone()
        order = existing_source['sort_order'] if existing_source else con.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM sources').fetchone()[0]
        if not existing_source or any(existing_source[k] != v for k,v in SOURCE.items()):
            con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                'name=excluded.name,url=excluded.url,license=excluded.license,license_file=excluded.license_file,'
                'citation=excluded.citation,attribution=excluded.attribution',
                (SOURCE_ID,order,*(SOURCE[k] for k in ('name','url','license','license_file','citation','attribution'))))
        for row in rows:
            previous = aircraft_store.fetch(con,row['id'])
            if previous and previous['source_id'] != SOURCE_ID:
                raise ValueError(f"Refusing to overwrite a foreign-source record: {row['id']}")
            if previous is None:
                aircraft_store.insert(con,row); changed += 1
            elif any(previous.get(k) != row.get(k) for k in aircraft_store.COLUMN_NAMES):
                aircraft_store.update(con,row['id'],row); changed += 1
    return dict(records=len(rows),families=len({(r['aircraft_type'],r['family']) for r in rows}),changed=changed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=MANIFEST)
    parser.add_argument('--database',type=Path,default=ROOT/'data/aircraft/aircraft.sqlite3')
    parser.add_argument('--check',action='store_true',help='Validate without writing')
    args=parser.parse_args()
    print(json.dumps(apply_manifest(json.loads(args.manifest.read_text(encoding='utf-8')),args.database,args.check)))


if __name__ == '__main__':
    main()
