"""Arkusz obliczeń raportów: każdy wzór z podstawieniem daje wynik programu (zapis jak w Mathcadzie)."""
import math
import re

import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.calc_sheet import REF, build_sheet, tex_value, worked_iteration
from calculations.mass_iteration import TOLERANCE, auto_start, guideline_masses

VARIANTS = {
    'drop_return_task': ('ga_trainer', dict(m_cargo=200, payload_drop_kg=150, return_range_km=300, mass_method='iterative',
                                            max_power_time_min=10, max_power_sfc=300, max_power_kw=150)),
    'two_point_law': ('ga_trainer', dict(empty_mass_model='two_point', mass_point_x1=800, mass_point_y1=.62,
                                         mass_point_x2=3000, mass_point_y2=.55)),
    'raymer_polar': ('ga_trainer', dict(preliminary_polar_mode='raymer', sketch_swet_ratio=4.2, raymer_family='prop_fixed')),
    'trend_coefficients': ('ga_trainer', dict(empty_mass_trend_A=.9, empty_mass_trend_C=-.05)),
    'fixed_fraction': ('pzl_kos', dict(empty_mass_model='fixed_fraction', empty_mass_fraction=.6)),
    'elliptical': ('ga_trainer', dict(wing_planform='elliptical')),
    'rectangular': ('ga_trainer', dict(wing_planform='rectangular')),
    'compound': ('ga_trainer', dict(wing_planform='compound_trapezoid')),
    'flaperon_slats': ('ga_trainer', dict(flap_type='flaperon', slat_type='slats_auto')),
    'swept_jet': ('vlj_jet', dict(sweep_quarter_deg=15)),
    'turbocharged': ('ga_trainer', dict(turbocharged=True)),
    'sized_wing': ('ga_trainer', dict(wing_input_mode='loading')),
    'span_and_area': ('motoglider_aos', dict(wing_input_mode='span_area', wingspan_m=17.0, wing_area_m2=17.5)),
    'span_and_aspect': ('glider_pw5', dict(wing_input_mode='span_aspect', wingspan_m=13.5)),
}


def sheets():
    for key, preset in AIRCRAFT_PRESETS.items():
        yield key, dict(preset)
    for key, (base, change) in VARIANTS.items():
        yield key, {**AIRCRAFT_PRESETS[base], **change}


@pytest.fixture(scope='module')
def built():
    out = {}
    for key, params in sheets():
        result = run_bipol_project(params)
        out[key] = (result, build_sheet(result))
    return out


@pytest.mark.parametrize('key', [k for k, _ in sheets()])
def test_every_substituted_formula_reproduces_the_program_result(built, key):
    _, sheet = built[key]
    wrong = {e['key']: (e['value'], e['computed']) for e in sheet.entries.values() if e['consistent'] is False}
    assert not wrong
    checked = [e for e in sheet.entries.values() if e['consistent']]
    assert len(checked) >= 180


@pytest.mark.parametrize('key', [k for k, _ in sheets()])
def test_entries_have_formula_substitution_unit_and_source(built, key):
    _, sheet = built[key]
    for e in sheet.entries.values():
        assert e['label'], e['key']
        if e['kind'] == 'calc':
            assert e['formula'] and ' = ' in e['tex'], e['key']
            if e['subst']:
                assert not REF.search(e['tex']), 'Każdy symbol podstawienia ma wartość.'
        if e['kind'] == 'given':
            assert e['source'] or e['note'], e['key']
    for key in ('m0', 'S', 'b', 'mac', 'Cx0', 'k', 'Kmax', 'V_S', 'V_A', 'V_D', 'n_ult_p', 'x_N', 'e_m0', 'm_e'):
        assert key in sheet.entries, key


def test_aspect_ratio_and_wing_area_are_written_out_in_report_style(built):
    for key in ('span_and_area', 'span_and_aspect'):
        result, sheet = built[key]
        span = sheet.entries['AR']
        assert sheet.entries['b']['kind'] == 'given' and 'AR_1' in sheet.entries
        assert span['tex'].startswith(r'\Lambda = \frac{b^2}{S} = \frac{')
        assert span['tex'].endswith(tex_value(span['value'], 2))
        assert sheet.entries['S']['kind'] == ('given' if key == 'span_and_area' else 'calc')
    _, sheet = built['span_and_area']
    assert sheet.entries['WS']['formula'] == r'\frac{m_0 g}{S}'
    _, sheet = built['sized_wing']
    area = sheet.entries['S']
    assert area['formula'] == r'\frac{m_0 g}{W/S}' and r'\;\mathrm{m^2}' in area['tex']
    assert set(area['deps']) == {'m0', 'g', 'WS'}
    assert sheet.entries['b']['formula'] == r'\sqrt{S\Lambda}' and sheet.entries['AR']['kind'] == 'given'
    assert sheet.entries['WS']['formula'].startswith(r'\min')


def test_dependency_chain_reaches_the_inputs_and_the_mass_iteration(built):
    _, sheet = built['ga_trainer']
    keys, blocks = sheet.chain(['n_ult_p'])
    assert keys[-1] == 'n_ult_p' and 'm0' in keys and 'g' in keys
    assert blocks == ['mass_iteration_proportion']
    # Dane poprzedzają wszystkie wzory, które z nich korzystają. Między obliczeniami występują
    # sprzężenia z projektu (masa ↔ masa pusta, powierzchnia ↔ mechanizacja), więc tylko dla danych.
    position = {k: i for i, k in enumerate(keys)}
    for key in keys:
        for dep in sheet.entries[key]['deps']:
            if dep in position and sheet.entries[dep]['kind'] == 'given':
                assert position[dep] < position[key], (dep, key)
    _, single = sheet.chain(['S_H'], follow=False)
    assert sheet.chain(['S_H'], follow=False)[0] == ['S_H'] and single == []


def test_numbers_use_polish_decimals_and_scientific_notation():
    assert tex_value(1619.94, 1) == r'1\,619{,}9'
    assert tex_value(7.36e-8, 3) == r'7{,}360\cdot 10^{-8}'
    assert tex_value(None) == r'\text{—}'


def test_iterative_method_follows_bipol1_points_1_to_12(built):
    result, _ = built['drop_return_task']
    mass = result['mass']
    trace = mass['guideline_traces']['iterative']
    rows = trace['rows']
    assert rows[0]['m0'] == auto_start(mass['m_payload'] + mass['m_crew'])
    assert rows[1]['m0'] == pytest.approx(rows[0]['m0'] - rows[0]['delta'])
    for before, prev, row in zip(rows, rows[1:], rows[2:]):
        slope = (prev['m0'] - before['m0']) / (prev['delta'] - before['delta'])
        assert row['m0'] == pytest.approx(prev['m0'] - prev['delta'] * slope)
    for row in rows:
        masses = row['masses']
        phases = {p['key']: p for p in row['phases']}
        assert masses['m1'] == pytest.approx(row['m0'] * phases['takeoff']['ratio'])
        assert masses['m4'] == pytest.approx(masses['m3'] - phases['task']['fuel'] - phases['drop']['release'])
        burn = row['m0'] - masses['m7'] - trace['drop']
        assert row['me_mission'] == pytest.approx(masses['m7'] - (trace['payload'] - trace['drop']) - trace['crew'] - .06 * burn)
        assert row['delta'] == pytest.approx(row['me_mission'] - row['me_trend'])
    assert rows[trace['converged_at'] - 1]['relative'] <= TOLERANCE
    assert trace['m0'] == pytest.approx(mass['m0'], abs=.1)
    steps = worked_iteration(trace, 2)
    assert [s['point'] for s in steps] == ['1', '2', '3', '4', '5', '6', '7', '8', '9a', '9b', '9c', '10', '11', '11']
    assert r'\Delta^{(2)}-\Delta^{(1)}' in steps[0]['tex']


@pytest.mark.parametrize('key', list(AIRCRAFT_PRESETS))
def test_proportion_method_solves_equation_5_with_equation_1(built, key):
    result, _ = built[key]
    mass = result['mass']
    trace = mass['guideline_traces']['proportion']
    for row in trace['rows']:
        if row['rule'] == 'fixed_point':
            assert row['next_m0'] == pytest.approx(trace['useful'] / (1 - row['fuel_fraction'] - row['empty_fraction']))
    assert trace['converged'] and trace['m0'] == pytest.approx(mass['m0'], abs=.1)
    assert guideline_masses(mass['mission_phases'])['m7'] == pytest.approx(mass['mission_phases'][-1]['mass_end_kg'])


def test_author_sets_the_first_iteration_mass():
    result = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'mass_iteration_start_kg': 2500})
    trace = result['mass']['guideline_traces']['proportion']
    assert trace['rows'][0]['m0'] == 2500 and trace['start_rule'] == 'założenie autora'
    assert trace['m0'] == pytest.approx(result['mass']['m0'], abs=.1)


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def test_project_report_writes_every_part_as_formulas(client):
    html = client.post('/report', json=AIRCRAFT_PRESETS['vlj_jet']).get_data(as_text=True)
    for key in ('m_lad', 'Kmax_1', 'm0', 'WS', 'S', 'b', 'S_H', 'x_N', 'Cx0', 'Cz_L', 'V_S', 's_TO15', 'V_A', 'mu_g', 'n_ult_p'):
        assert f'data-calc="{key}"' in html, key
    assert 'data-mass-iteration="proportion"' in html and 'class="report-chart flow"' in html
    assert 'Paliwo i zrzut ładunku w poszczególnych fazach' in html and '<script src=' not in html
    single = client.post('/report/project/p3', json=AIRCRAFT_PRESETS['vlj_jet']).get_data(as_text=True)
    assert 'data-sheet-section="p3.neutral"' in single and 'data-sheet-section="p6.gust"' not in single


def test_catalog_lists_parameters_and_iteration_schemes(client):
    data = client.post('/api/report/catalog', json=AIRCRAFT_PRESETS['ga_trainer']).get_json()
    keys = {item['key'] for section in data['sections'] for item in section['items']}
    assert {'AR', 'm0', 'S', 'V_A'} <= keys
    assert [b['key'] for b in data['blocks']] == ['@mass_iteration_proportion', '@mass_iteration_iterative']
    assert data['projects']['p2'].startswith('P2')
    item = next(i for s in data['sections'] for i in s['items'] if i['key'] == 'AR')
    assert item['value_tex'] and item['sym'] == r'\Lambda'


def test_parameter_report_with_full_chain_or_single_formula(client):
    params = AIRCRAFT_PRESETS['ga_trainer']
    chain = client.post('/report/parameters?keys=m0&chain=1', json=params).get_data(as_text=True)
    assert 'data-mass-iteration="proportion"' in chain and 'data-calc="e_m0"' in chain and 'data-given="m_os"' in chain
    assert chain.count('class="iteration-heading"') >= 3, 'Każda iteracja w pełnym zapisie.'
    single = client.post('/report/parameters?keys=S_H&chain=0', json=params).get_data(as_text=True)
    assert 'data-calc="S_H"' in single and 'data-calc="mac"' not in single and 'data-ref="mac"' in single
    scheme = client.post('/report/parameters?keys=@mass_iteration_iterative&chain=0&iterations=first', json=params)
    html = scheme.get_data(as_text=True)
    assert scheme.status_code == 200 and 'data-mass-iteration="iterative"' in html and html.count('class="iteration-heading"') == 2
    assert 'Różnica mas pustego w funkcji zakładanej masy startowej' in html


@pytest.mark.parametrize('query', ['keys=', 'keys=nieznany', 'keys=@nieznany'])
def test_parameter_report_rejects_unknown_selection(client, query):
    response = client.post(f'/report/parameters?{query}', json=AIRCRAFT_PRESETS['ga_trainer'])
    assert response.status_code == 400


def test_iteration_figures_are_inline_svg_with_accessible_titles(built):
    from calculations import report_figures
    result, _ = built['drop_return_task']
    trace = result['mass']['guideline_traces']['iterative']
    for svg in (report_figures.flow_diagram(trace), report_figures.convergence_chart(trace), report_figures.error_chart(trace),
                report_figures.secant_chart(trace), report_figures.mission_chart_for(trace, result['mass'])):
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"') and '<title>' in svg and 'role="img"' in svg
        assert not re.search(r'\bnan\b|\binf\b', svg.lower())
    assert math.isfinite(trace['m0'])
