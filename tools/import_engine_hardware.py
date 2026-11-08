"""Apply source hardware observations atomically; keep SQLite the live engine catalogue."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
MANIFEST=ROOT/'data/aircraft/research/engine_hardware.json'


def apply_manifest(data,path,check=False):
    from calculations import aircraft_store
    from calculations.engine_mass import validate_hardware
    if data.get('version')!=1 or not isinstance(data.get('records'),list):
        raise ValueError('Nieobsługiwany format obserwacji mas silników.')
    records=[(row['engine_id'],validate_hardware(row['hardware'])) for row in data['records']]
    if len({key for key,_ in records})!=len(records):
        raise ValueError('Powtórzony identyfikator silnika.')
    changed=0
    with aircraft_store.transaction(path) as con:
        for key,hardware in records:
            row=con.execute('SELECT document FROM engines WHERE id=?',(key,)).fetchone()
            if row is None:
                raise ValueError(f'Nieznany silnik: {key}')
            document=json.loads(row[0])
            if document.get('hardware')!=hardware:
                changed+=1
                if not check:
                    document['hardware']=hardware
                    con.execute('UPDATE engines SET document=? WHERE id=?',
                        (json.dumps(document,ensure_ascii=False,allow_nan=False),key))
        if changed and not check:
            con.execute('UPDATE catalog_state SET revision=random() WHERE singleton=1')
    return dict(observations=len(records),changed=changed,check_only=check)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=MANIFEST)
    parser.add_argument('--database',type=Path,default=ROOT/'data/aircraft/aircraft.sqlite3')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    print(json.dumps(apply_manifest(json.loads(args.manifest.read_text(encoding='utf8')),args.database,args.check)))


if __name__=='__main__':main()
