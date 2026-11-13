"""Wymagania z materiałów kursu: Schemat_projektu.pdf, Opis projektów (P5) i Ogólne wymagania (spis oznaczeń)."""
import json
from pathlib import Path

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS

CASE = Path(__file__).parents[1] / 'data/design_cases/topic7_motoszybowiec_21m.json'


@pytest.fixture(scope='module')
def design():
    return run_bipol_project(json.loads(CASE.read_text(encoding='utf-8')))


def test_drawing_procedure_is_checked_step_by_step(design):
    rows = {row['name']: row for row in design['drawing_checks']['rows']}
    assert rows['Kąt widoczności pilota do przodu w dół']['passed'] is None  # shown on the author's drawing
    clearance = rows['Odległość końcówki śmigła od podłoża']
    gear, diameter = design['geometry']['gear'], design['bipol_projects']['p3']['blueprint_checks']['propeller_diameter_m']
    assert clearance['passed'] and gear['axis_height_m'] - diameter / 2 >= .18 - 1e-9
    assert design['bipol_projects']['p3']['blueprint_checks']['prop_ground_clearance_m'] == pytest.approx(gear['axis_height_m'] - diameter / 2)
    assert rows['Część steru kierunku poza cieniem usterzenia poziomego (wyjście z korkociągu)']['passed']
    assert all(row['passed'] for row in rows.values() if row['passed'] is not None)
    wing, tail = design['geometry']['wing'], design['geometry']['horizontal_tail']
    assert rows['Cecha objętościowa usterzenia poziomego na rysunku']['value'] == f"{tail['S_h'] * tail['l_h'] / (wing['S'] * wing['mac']):.3f}".replace('.', ',')


@pytest.mark.parametrize('preset', ['pzl_kos', 'regional_turboprop', 'glider_pw5', 'uav_male'])
def test_drawing_checks_exist_for_every_class(preset):
    result = run_bipol_project(AIRCRAFT_PRESETS[preset])
    assert result['drawing_checks']['rows'] and result['drawing_checks']['assessed'] >= 3


def test_report_has_symbol_list_drawing_table_and_critical_review(client, design):
    html = client.post('/report', json=design['params']).get_data(as_text=True)
    assert 'Spis ważniejszych oznaczeń' in html and 'tab-drawing-checks' in html
    assert 'Krytyczna ocena projektu' in html and 'Zespół napędowy jest przewymiarowany' in html


def test_a2_sheet_for_the_p3_drawing_doubles_the_scale(design):
    from calculations.drawing_sheet import drawing_sheet
    import re
    a4, a2 = str(drawing_sheet(design)), str(drawing_sheet(design, True))
    scale = lambda text: int(re.search(r'skala 1:(\d+)', text).group(1))  # noqa: E731
    assert 'A2 • skala' in a2 and scale(a4) == 2 * scale(a2)
    assert 'id="millimeterA2" width="0.5"' in a2 and 'id="millimeter" width="1"' in a4


def test_flap_envelope_is_drawn_on_the_aircraft_envelope(client, design):
    html = client.post('/report', json=design['params']).get_data(as_text=True)
    assert 'flapEnvelope(e.flap, e.composite_polygon)' in html
    assert 'na tle obwiedni samolotu' in html
    assert 'print-drawing-a2' in html and 'Jakość dopasowania' in html
