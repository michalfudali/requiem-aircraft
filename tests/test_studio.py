import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0
from calculations.glide import calculate_glide_polar


@pytest.mark.parametrize('key', AIRCRAFT_PRESETS)
def test_exact_glide_balances_both_force_components(key):
    result = run_bipol_project(AIRCRAFT_PRESETS[key])
    glide = result['performance']['glide']
    weight = result['mass']['m0'] * G0
    area = result['geometry']['wing']['S']
    for row in glide['points'][::17]:
        gamma = math.radians(row['gamma_deg'])
        q = .5 * glide['rho'] * row['v_ms'] ** 2
        assert q * area * row['cz'] == pytest.approx(weight * math.cos(gamma), rel=1e-10)
        assert q * area * row['cx'] == pytest.approx(weight * math.sin(gamma), rel=1e-10)
        assert row['horizontal_ms'] / row['sink_ms'] == pytest.approx(row['ld'])


def test_glide_scales_with_square_root_of_mass_at_fixed_polar_point():
    result = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    geometry, aero = result['geometry'], result['aerodynamics']
    a = calculate_glide_polar(400, geometry, aero)
    b = calculate_glide_polar(1600, geometry, aero)
    for one, two in zip(a['points'], b['points']):
        assert two['v_ms'] == pytest.approx(2 * one['v_ms'])
        assert two['sink_ms'] == pytest.approx(2 * one['sink_ms'])
        assert two['ld'] == one['ld']


@pytest.mark.parametrize('key,category', [('glider_pw5', 'cs22_glider'), ('motoglider_aos', 'cs22_motoglider')])
def test_new_upstream_aircraft_types_keep_correct_classification(key, category):
    result = run_bipol_project(AIRCRAFT_PRESETS[key])
    assert result['easa_compliance']['suggested_category'] == category
    if key == 'glider_pw5':
        assert result['params']['engine_type'] == 'none'
        assert result['mass']['m_fuel'] == 0
        # Paturski P6 uses zero for "no powered climb"; sink lives in the glide model.
        assert result['performance']['climb']['wy_max_ms'] <= 0
        assert result['mass']['breakdown']['m_propulsion'] == 0
        assert sum(result['mass']['breakdown'].values()) == pytest.approx(result['mass']['m_empty'], abs=.3)
    assert result['geometry']['fuselage']['diameter'] <= 1.5


@pytest.mark.parametrize('sections', ['p1', 'p2,p4', 'p3,p5,p6', 'p6'])
def test_report_renders_only_requested_sections(sections):
    with app.test_client() as client:
        response = client.get('/report', query_string={'sections': sections})
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    for section in ('p1', 'p2', 'p3', 'p4', 'p5', 'p6'):
        assert (f'data-report-section="{section}"' in text) == (section in sections.split(','))
    assert 'Podsumowanie i zgodność' in text
    assert 'Ograniczenia przyjętych metod' in text
    assert '<script src=' not in text
    assert '<link rel="stylesheet"' not in text


@pytest.mark.parametrize('sections', ['', 'p7', 'p1,unknown', 'p1,'])
def test_invalid_report_selection_is_rejected(sections):
    with app.test_client() as client:
        assert client.get('/report', query_string={'sections': sections}).status_code == 400


def test_report_notes_are_escaped_and_limited():
    with app.test_client() as client:
        params = {**AIRCRAFT_PRESETS['ga_trainer'], 'report_notes': '<img src=x onerror=alert(1)>', 'source_notes': 'Instrukcja, strona 21'}
        text = client.post('/report?sections=p3', json=params).get_data(as_text=True)
        assert '&lt;img src=x onerror=alert(1)&gt;' in text
        assert 'Instrukcja, strona 21' in text
        params['report_notes'] = 'x' * 15001
        assert client.post('/report', json=params).status_code == 400


def test_upstream_sample_removal_is_preserved_in_new_ui():
    with app.test_client() as client:
        text = client.get('/').get_data(as_text=True)
    assert 'id="presetSelect"' not in text
    assert 'quick-preset-chip' not in text
    assert 'id="studioSidebar"' in text
    assert 'id="tab-variants"' in text
    assert 'id="studioNotes"' in text
