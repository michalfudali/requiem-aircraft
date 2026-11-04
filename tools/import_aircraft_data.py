"""Reproducible, offline conversion of the upstream FAST and CADO downloads.

Usage: python tools/import_aircraft_data.py --fast path.xlsx --cado path.csv
Replaces the fast and cado records in the aircraft database, one transaction per source.
Only this development tool needs openpyxl.
No missing values, dates, wing areas or performance figures are imputed.
"""
import argparse
import csv
import hashlib
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calculations import aircraft_store  # noqa: E402
FAST_REVISION = "482e77b921d616d00d9cdb5c0c673d55f511c52b"
FAST_SHA256 = "3f31aadde6b71dab9c8a41b46d9b9707aceb9f2f4e35c02b9b5436b7f02eeaa4"
CADO_SHA256 = "6b986349811e66f50039347f7c3450636f8700b1ed0ad5ee7e523d89b8777180"


def number(value):
    try:
        n = float(value)
        return round(n, 6) if math.isfinite(n) and n > 0 else None
    except (TypeError, ValueError):
        return None


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def family_name(name):
    """Conservative grouping; never infer an aircraft's missing numerical data."""
    name = str(name).upper().replace('_', '-').replace(' ', '')
    name = name.replace('BOMBARDIERLEARJET', 'LEARJET').replace('BOEING', 'B')
    if re.match(r'7[0-9]{2}', name):
        name = 'B' + name
    if name.startswith('BEECH1900'):
        return 'BEECH1900'
    if name.startswith('BOMBARDIERGLOBAL') or name.startswith('GLOBAL') or name.startswith('BD-700'):
        return 'GLOBAL'
    if name.startswith('BD-100') or name.startswith('BOMBARDIERCHALLENGER300'):
        return 'CHALLENGER300'
    if name.startswith('CL-600') or re.match('BOMBARDIERCHALLENGER60', name):
        return 'CHALLENGER600'
    if name.startswith('CHALLENGER'):
        return 'CHALLENGER'
    rules = [r'A3\d\d', r'A22[01]', r'B7\d\d', r'B73', r'B74', r'B77',
             r'CRJ', r'ERJ-?\d+', r'EMB-?\d+', r'DHC-?\d', r'ATR-?\d+',
             r'LEARJET\d+', r'PA-?\d+', r'DR400', r'DC-?\d+', r'MD-?\d+',
             r'SR\d+', r'SKYH[AO]WK172', r'SK[YI]LANE182', r'STATIONAIR206']
    for rule in rules:
        match = re.match(rule, name)
        if match:
            return match.group().replace('-', '')
    return name.split('-')[0]


# Designations classified as business jets are data of the comparison-aircraft database.
try:
    BUSINESS_JETS = [name.strip() for name in aircraft_store.model_examples()['fast_import']['business_jets'].split(',')]
except (FileNotFoundError, KeyError):
    BUSINESS_JETS = []

def record(source, model, cls, engine, family, **values):
    return {"id": source + "-" + slug(model), "model": model,
            "aircraft_type": cls, "engine_type": engine, "family": family_name(family or model),
            "source_id": source, "empty_mass_definition": "OEW / operating empty weight",
            "year_basis": "certification", "variable_sweep": False, **values}


def import_fast(path):
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
    workbook = load_workbook(path, data_only=True)
    engines = workbook['Jet Engines']
    engine_data = {str(engines.cell(2, c).value): (number(engines.cell(10, c).value),
                   f"Jet Engines!{get_column_letter(c)}") for c in range(5, engines.max_column + 1)
                   if engines.cell(2, c).value}
    result, seen = [], set()
    for sheet_name in ('Jet Aircraft', 'Propeller Aircraft'):
        sheet = workbook[sheet_name]
        rows = {str(sheet.cell(r, 1).value): r for r in range(1, sheet.max_row + 1)
                if sheet.cell(r, 1).value is not None}
        for col in range(8, sheet.max_column + 1):
            def val(key):
                return sheet.cell(rows[key], col).value if key in rows else None
            def num(key):
                return number(val(key))
            model, mtow, refs = val('AircraftDesignation'), num('MTOW'), val('Sources')
            if not model or not mtow or not refs:
                continue
            # An upstream repeated designation must not become a second observation.
            if model in seen:
                continue
            seen.add(model)
            jet = sheet_name == 'Jet Aircraft'
            pax = num('MaximumPassengers') or num('TypicalPassengers')
            business = (pax is not None and pax <= 19 and mtow < 50000 and val('Payload Type  (P, C, M)') != 'C')
            business = business or any(str(model).startswith(name[:-1]) if name.endswith('*') else str(model) == name
                                       for name in BUSINESS_JETS)
            cls = 'jet_business' if jet and business else ('jet_transport' if jet else 'turboprop_regional')
            engine_name = str(val('EngineDesignation') or '')
            count = num('NumberEngines')
            engine_thrust, engine_ref = engine_data.get(engine_name, (None, None))
            thrust = num('Maximum Thrust (PER ENGINE)') or engine_thrust if jet else None
            power = num('Takeoff') if not jet else None  # Per-engine, aircraft installation rating.
            area, span = num('WingArea'), num('Wingspan')
            result.append(record('fast', str(model).replace('_', '-'), cls, 'jet' if jet else 'prop',
                model if str(model).startswith(('CL_600', 'BD_100', 'BD_700')) else val('Family') or val('SubFamily') or model,
                manufacturer=str(val('Manufacturer') or '').strip(),
                source_locator=f"{sheet_name}!{get_column_letter(col)}",
                source_references=str(refs).strip(), engine_source_locator=engine_ref if jet else None,
                m0=mtow, me=num('OEW'), s=area, b=span,
                year=int(num('CertificationDate')) if num('CertificationDate') else None,
                n_engines=int(count) if count else None, engine_model=engine_name,
                p_kw=round(power * count, 3) if power and count else None,
                t_kn=round(thrust * count / 1000, 4) if thrust and count else None,
                cruise_mach=num('M_Cr'), mmo=num('M_MO'), v_cruise_kmh=None, v_max=None,
                range_km=num('DesignRange'), takeoff_m=num('TakeoffDistance'), takeoff_basis='field_length',
                h_tail_area=None, v_tail_area=None))
    return result


def import_cado(path):
    result = []
    for line, row in enumerate(csv.DictReader(path.open(encoding='utf-8-sig'), delimiter=';'), start=2):
        mtow = number(row['mtow'])
        if not mtow:
            continue  # Two rows describe column units, not aircraft.
        engine = row['engine_type']
        cls = 'piston_ga' if engine == 'piston' else ('turboprop_regional' if engine == 'turboprop' else
              ('jet_business' if row['airplane_type'] == 'business' else 'jet_transport'))
        count = number(row['n_engine'])
        power, thrust = number(row['max_power']), number(row['max_thrust'])
        cruise, vmax = number(row['cruise_speed']), number(row['max_speed'])
        jet = engine == 'turbofan'
        # CADO explicitly uses Mach for sub-unit speeds and km/h otherwise.
        date = re.search(r'(?:19|20)\d{2}', row['tcds_app_date'])
        result.append(record('cado', row['name'], cls, 'jet' if jet else 'prop', row['name'],
            manufacturer='', source_locator=f"CADO_airplane_database_v1.0.csv:{line}",
            source_references='ENAC CADO v1.0 (2024), DOI:10.57745/LLRJO0',
            m0=mtow, me=number(row['owe']), s=number(row['wing_area']), b=number(row['wing_span']),
            year=int(date.group()) if date else None, n_engines=int(count) if count else None,
            engine_model=row['powerplant'],
            p_kw=round(power * count, 3) if not jet and power and count else None,
            t_kn=round(thrust * count / 1000, 4) if jet and thrust and count else None,
            cruise_mach=cruise if cruise and cruise < 2 else None,
            mmo=vmax if vmax and vmax < 2 else None,
            v_cruise_kmh=cruise if cruise and cruise >= 2 else None,
            v_max=vmax if vmax and vmax >= 2 else None,
            range_km=number(row['nominal_range']), takeoff_m=number(row['tofl']), takeoff_basis='field_length',
            landing_m=number(row['lfl']), landing_basis='field_length',
            h_tail_area=number(row['htp_area']), v_tail_area=number(row['vtp_area'])))
    return result


def write(name, records):
    aircraft_store.replace_source(name, records)
    print(f'{aircraft_store.database_path()}: {len(records)} aircraft from {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fast', type=Path, required=True)
    parser.add_argument('--cado', type=Path, required=True)
    args = parser.parse_args()
    for path, expected in ((args.fast, FAST_SHA256), (args.cado, CADO_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Unexpected upstream revision: {path}. Review the new source before importing.')
    write('fast', import_fast(args.fast))
    write('cado', import_cado(args.cado))


if __name__ == '__main__':
    main()
