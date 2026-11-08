"""Temat 7: wynik programu sprawdzony rachunkiem ręcznym, niezależnym od modułów obliczeniowych."""
import json
import math
from pathlib import Path

import pytest

from calculations import run_bipol_project
from calculations.mass import group_masses

G, RHO0 = 9.80665, 1.225
CASE = Path(__file__).parents[1] / 'data/design_cases/topic7_motoszybowiec_21m.json'


def isa_density(height):
    temperature = 288.15 - .0065 * height
    pressure = 101325 * (temperature / 288.15) ** 5.25588
    return pressure / (287.053 * temperature)


@pytest.fixture(scope='module')
def design():
    return run_bipol_project(json.loads(CASE.read_text(encoding='utf-8')))


def test_topic_configuration_and_mass_closure(design):
    p, m, w = design['params'], design['mass'], design['geometry']['wing']
    assert p['n_crew'] + p['n_pax'] == 1 and w['b'] > 20
    assert p['engine_location'] == 'nose' and p['engine_type'] == 'prop' and int(p['n_engines']) == 1
    assert m['m_empty'] + m['m_crew'] + m['m_payload'] + m['m_fuel'] == pytest.approx(m['m0'], rel=1e-3)
    assert w['S'] == pytest.approx(w['b'] ** 2 / p['aspect_ratio'], rel=1e-9)
    assert sum(m['scaled_components'].values()) == pytest.approx(m['m_empty'], rel=1e-9)
    assert m['component_closure']['sum_kg'] == pytest.approx(m['m_empty'], rel=1e-3)


def test_jar22_limits_from_hand_calculation(design):
    p, m, w, a = design['params'], design['mass'], design['geometry']['wing'], design['aerodynamics']
    m0, area, span = m['m0'], w['S'], w['b']
    assert m0 <= 850 and m0 / span ** 2 <= 3
    vs0 = math.sqrt(2 * m0 * G / (RHO0 * area * a['cz_max_lnd'])) * 3.6
    assert vs0 == pytest.approx(design['envelope']['speeds']['v_s0_kmh'], rel=2e-3) and vs0 <= 72
    assert design['performance']['takeoff']['distance_to_15m'] <= 500
    assert design['performance']['climb']['wy_max_ms'] >= 1.5
    assert m['m_fuel'] >= .5 * 58 * p['sfc'] / 1000


def test_cruise_fuel_by_numerical_integration(design):
    """Paliwo przelotu krokami 1 km: D(m)·c/η, bez wzoru zamkniętego z mission_cruise."""
    p, m = design['params'], design['mass']
    polar = p['_mission_polar']
    q = .5 * isa_density(p['cruise_altitude_m']) * (p['cruise_speed_kmh'] / 3.6) ** 2
    phase = next(x for x in m['mission_phases'] if x['key'] == 'cruise')
    mass, burn_per_joule = phase['mass_start_kg'], p['sfc'] / 3.6e9 / p['prop_efficiency']
    for _ in range(600):
        lift = mass * G
        drag = q * polar['S'] * polar['cx0'] + polar['k'] * lift ** 2 / (q * polar['S'])
        mass -= drag * 1001 * burn_per_joule
    assert mass == pytest.approx(phase['mass_end_kg'], rel=2e-4)


def test_holding_phase_uses_the_polar_of_the_balance(design):
    p, assumptions = design['params'], design['mass']['mission_assumptions']
    polar = p['_mission_polar']
    assert assumptions['loiter_ld'] == pytest.approx(.8 / (2 * math.sqrt(polar['cx0'] * polar['k'])), rel=1e-9)


def test_envelope_speeds_from_jar22(design):
    env, m, w, a = design['envelope']['speeds'], design['mass'], design['geometry']['wing'], design['aerodynamics']
    vs1 = math.sqrt(2 * m['m0'] * G / (RHO0 * w['S'] * a['cz_max_clean'])) * 3.6
    assert env['v_a_kmh'] == pytest.approx(vs1 * math.sqrt(5.3), rel=3e-3)
    ws_dan = m['m0'] * G / w['S'] / 10
    assert env['v_d_kmh'] >= 18 * (ws_dan / a['cx0_clean']) ** (1 / 3) - .5
    assert env['v_d_kmh'] >= 1.35 * design['performance']['speeds']['v_max_sl_kmh'] - .5


def test_wing_mass_from_the_equation_of_analiza_masowa(design):
    """W_wing = 0,036 S^0,758 W_fw^0,0035 (A/cos²Λ)^0,6 q^0,006 λ^0,04 (100 t/c /cosΛ)^-0,3 (N_z W_dg)^0,49 × 0,85."""
    p, m, w = design['params'], design['mass'], design['geometry']['wing']
    lb, ft2, psf = 2.2046226, 10.76391, .0208854
    q = .5 * isa_density(p['cruise_altitude_m']) * (p['cruise_speed_kmh'] / 3.6) ** 2 * psf
    wing = (.036 * (w['S'] * ft2) ** .758 * (m['m_fuel'] * lb) ** .0035 * p['aspect_ratio'] ** .6 * q ** .006
            * p['taper_ratio'] ** .04 * (100 * w['tc_ratio']) ** -.3 * (1.5 * 5.3 * m['m0'] * lb) ** .49 * .85) / lb
    assert m['detailed_breakdown']['wing'] == pytest.approx(wing, rel=1e-3)


def test_centre_of_gravity_from_the_mass_table(design):
    balance, p3 = design['balance'], design['bipol_projects']['p3']
    rows = p3['table_3_1_components']
    total = sum(r['mass_kg'] for r in rows)
    mtow = next(s for s in balance['loading_states'] if s['key'] == 'mtow')
    assert total == pytest.approx(mtow['mass_kg'], rel=1e-6)
    assert sum(r['mass_kg'] * r['x_m'] for r in rows) / total == pytest.approx(mtow['xcg_m'], abs=.01)
    assert design['balance']['ground_check']['passed']
    assert 25 - 1e-6 <= balance['cg_range']['forward_pct'] and balance['cg_range']['aft_pct'] <= 35


def test_design_retains_the_missing_installation_mass_and_authors_confirmations(design):
    assert all(c['passed'] for c in design['compliance_checks'])
    assert {c['id'] for c in design['engineering_audit']['checks'] if not c['passed']} == {'engine_installation_mass'}
    assert {c['key'] for c in design['bipol1_review']['checks'] if not c['passed']} == {'sketch', 'mission'}


def test_engine_is_never_weightless_in_sized_mode():
    topic = json.loads(CASE.read_text(encoding='utf-8'))
    topic.update(engine_fuel_mode='unselected', power_input_mode='sized', engine_power_kw=0, locked_params=['n_pax', 'range_km', 'wingspan_m'])
    result = run_bipol_project(topic)
    power = result['sizing']['design_point']['power_kw']
    assert result['mass']['scaled_components']['propulsion'] > .5 * power


def test_engine_keeps_its_mass_and_airframe_absorbs_the_difference():
    detail = dict(wing=100., horizontal_tail=5., vertical_tail=5., fuselage=60., landing_gear=20., propulsion=50., fuel_system=5.,
                  flight_controls=10., avionics=5., electrical=10., furnishings=5.)
    scaled, groups, factor = group_masses(detail, 200.)
    assert scaled['propulsion'] == 50 and factor == pytest.approx(150 / 225)
    assert sum(groups.values()) == pytest.approx(200)
    assert group_masses(dict(detail, propulsion=150.), 200.)[0]['propulsion'] < 150


def test_component_masses_use_the_ultimate_factor_of_the_envelope(design):
    assert design['mass']['component_closure']['n_ult'] == pytest.approx(design['envelope']['limits']['n_ult_pos'])
