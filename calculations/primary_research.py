"""Reproducible primary-source observations and their catalogue provenance."""
from functools import lru_cache
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/aircraft/research/primary_aircraft.json'
SOURCE_ID = 'primary_research'
SOURCE = dict(name='Dokumentacja producentów i certyfikatów typu',
    url='https://github.com/michalfudali/requiem-aircraft/tree/master/data/aircraft/research',
    license='Individually attributed factual observations; see original publication terms',
    license_file='PRIMARY-RESEARCH.txt',
    citation='Zestawienie własne: dokumentacja producentów, AFM/POH i TCDS; źródła poszczególnych parametrów w manifeście badań.',
    attribution='Wydawcy i autorzy dokumentów wskazani przy każdym rekordzie.')

# Exact definitions; the unit is selected from the source, never guessed from a number.
UNITS = {
    'kg':('mass',1), 'lb':('mass',.45359237),
    'm':('length',1), 'mm':('length',.001), 'ft':('length',.3048),
    'm2':('area',1), 'ft2':('area',.09290304),
    'kW':('power',1), 'hp_mechanical':('power',.7456998715822702), 'PS':('power',.73549875),
    'km/h':('speed',1), 'kt':('speed',1.852), 'mph':('speed',1.609344),
    'm/s':('vertical_speed',1), 'ft/min':('vertical_speed',.00508),
    'km':('distance',1), 'NM':('distance',1.852), 'mi':('distance',1.609344),
    '1':('ratio',1), 'deg':('angle',1), 'year':('year',1),
}
FIELDS = {'m0':'mass','me':'mass','s':'area','b':'length','h_tail_area':'area','v_tail_area':'area',
    'p_kw':'power','prop_diameter_m':'length','v_cruise_kmh':'speed','v_max':'speed','v_stall_kmh':'speed',
    'range_km':'distance','climb_rate_ms':'vertical_speed','w_z_min_ms':'vertical_speed',
    'takeoff_m':'length','landing_m':'length','ld_max':'ratio','year':'year','v_h':'ratio','v_v':'ratio',
    'aileron_span_fraction':'ratio','aileron_chord_ratio':'ratio','elevator_chord_ratio':'ratio',
    'rudder_chord_ratio':'ratio','dihedral_deg':'angle'}


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def validate_manifest(data):
    """Validate scientific provenance before touching the database; return canonical rows."""
    if data.get('schema') != 1 or not isinstance(data.get('records'),list):
        raise ValueError('Unsupported primary-research manifest.')
    documents = data['documents']
    for key, doc in documents.items():
        url = urlsplit(doc['url'])
        if url.scheme != 'https' or not url.netloc or not doc.get('publisher') or not doc.get('title'):
            raise ValueError(f'Incomplete publication: {key}')
        if not doc.get('retrieved'):
            raise ValueError(f'Missing retrieval date: {key}')
    rows, ids = [], set()
    for record in data['records']:
        identity = record['id']
        if not identity.startswith('pr-') or identity in ids:
            raise ValueError(f'Invalid or duplicate managed ID: {identity}')
        ids.add(identity)
        row = {k:record[k] for k in ('id','model','manufacturer','family','aircraft_type','engine_type','n_engines')}
        row['source_id'] = SOURCE_ID
        row['variable_sweep'] = False
        for key in ('engine_model','prop_type','empty_mass_definition','takeoff_basis','landing_basis','year_basis'):
            if key in record:
                row[key] = record[key]
        references, locators = {}, []
        for field, evidence in record['observations'].items():
            if field not in FIELDS or evidence.get('unit') not in UNITS:
                raise ValueError(f'{identity}.{field}: unsupported field or unit')
            dimension, factor = UNITS[evidence['unit']]
            if dimension != FIELDS[field] or not finite(evidence.get('value')):
                raise ValueError(f'{identity}.{field}: invalid quantity')
            doc_id = evidence.get('document',record.get('document'))
            if doc_id not in documents or not evidence.get('locator'):
                raise ValueError(f'{identity}.{field}: missing field-level evidence')
            doc = documents[doc_id]
            references[doc_id] = f"{doc['publisher']}: {doc['title']} — {doc['url']} (dostęp {doc['retrieved']})"
            number = float(evidence['value']*factor)
            if 'derivation' in evidence:
                derivation = evidence['derivation']
                empty_difference = (field == 'me' and derivation.get('formula') == 'MTOW - useful_load'
                    and all(finite(derivation.get(k)) for k in ('mtow','useful_load'))
                    and evidence['unit'] == 'kg'
                    and math.isclose(number,derivation['mtow']-derivation['useful_load'],abs_tol=1e-9))
                total_power = (field == 'p_kw' and derivation.get('formula') == 'n_engines * engine_power'
                    and finite(derivation.get('engine_power')) and derivation.get('n_engines') == record['n_engines']
                    and evidence['unit'] == 'kW'
                    and math.isclose(number,record['n_engines']*derivation['engine_power'],abs_tol=1e-9))
                if not (empty_difference or total_power):
                    raise ValueError(f'{identity}.{field}: invalid declared derivation')
            if field == 'year' and not number.is_integer():
                raise ValueError(f'{identity}: fractional certification year')
            row[field] = int(number) if field == 'year' else number
            locators.append(f"{field}: {evidence['locator']}" + (f" [{evidence['conditions']}]" if evidence.get('conditions') else ''))
        if 'm0' not in row or ('me' in row and not row.get('empty_mass_definition')):
            raise ValueError(f'{identity}: missing mass evidence or definition')
        if 'year' in row and row.get('year_basis') not in ('certification','production'):
            raise ValueError(f'{identity}: publication/retrieval is not a certification year')
        for field in ('takeoff','landing'):
            if f'{field}_m' in row and row.get(f'{field}_basis') not in ('ground_roll','15m','50ft','field_length','unknown'):
                raise ValueError(f'{identity}: undefined {field} distance')
        row['source_references'] = '\n'.join(references.values())
        row['source_locator'] = '; '.join(locators)
        if len(row['source_locator']) > 4000 or len(row['source_references']) > 4000:
            raise ValueError(f'{identity}: provenance exceeds catalogue limits')
        if 'p_kw' in row:
            row['engine_source_locator'] = next(e['locator'] for k,e in record['observations'].items() if k == 'p_kw')
        rows.append(row)
    return rows



@lru_cache(maxsize=1)
def _published_snapshot(path, modified_ns):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    canonical = {r['id']:r for r in validate_manifest(data)}
    return data, canonical


def evidence_for(record):
    """Attach the published observations to a live record without changing it.

    Local catalogue edits are allowed. They must never silently acquire the
    unmodified source document's claim of support.
    """
    if record.get('source_id') != SOURCE_ID:
        return None
    data, canonical = _published_snapshot(str(MANIFEST), MANIFEST.stat().st_mtime_ns)
    identity = record['id']
    expected = canonical.get(identity)
    if expected is None:
        return None
    from calculations.aircraft_store import COLUMN_NAMES
    source = next(r for r in data['records'] if r['id'] == identity)
    observations = []
    canonical_units = dict(mass='kg',length='m',area='m²',power='kW',speed='km/h',
                           vertical_speed='m/s',distance='km',ratio='1',angle='deg',year='year')
    for field, observation in source['observations'].items():
        doc_id = observation.get('document',source['document'])
        observations.append(dict(field=field,**observation,publication=data['documents'][doc_id],
            catalogue_value=record.get(field),catalogue_unit=canonical_units[FIELDS[field]]))
    return dict(id=identity,observations=observations,
        notes=source.get('notes',[]),excluded_observations=source.get('excluded_observations',[]),
        matches_catalogue=all(record.get(k) == expected.get(k) for k in COLUMN_NAMES))
