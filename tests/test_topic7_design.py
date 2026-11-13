"""Temat 7: wynik programu sprawdzony rachunkiem ręcznym, niezależnym od modułów obliczeniowych."""
import json
import math
import statistics
from pathlib import Path

import pytest

from calculations import run_bipol_project
from calculations.mass import estimate_component_masses, group_masses
from calculations.trends import load_aircraft

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
    n_z = m['component_closure']['n_ult']
    wing = (.036 * (w['S'] * ft2) ** .758 * (m['m_fuel'] * lb) ** .0035 * p['aspect_ratio'] ** .6 * q ** .006
            * p['taper_ratio'] ** .04 * (100 * w['tc_ratio']) ** -.3 * (n_z * m['m0'] * lb) ** .49 * .85) / lb
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


def test_design_documents_the_installation_mass_and_keeps_authors_confirmations(design):
    assert all(c['passed'] for c in design['compliance_checks'])
    assert {c['id'] for c in design['engineering_audit']['checks'] if not c['passed']} == {'aeroelastic_substantiation'}
    assert {c['key'] for c in design['bipol1_review']['checks'] if not c['passed']} == {'sketch', 'mission'}


def test_installed_engine_mass_is_the_documented_build_up_kept_unscaled(design):
    """Rotax 55,4 kg + zważona zabudowa CH750 (48,4 + 5,95 + 3,3 lb) + śmigło E-Props 1,6 kg."""
    hand = 55.4 + (48.4 + 5.95 + 3.3) * .45359237 + 1.6
    evidence = design['engine_selection']['mass']
    assert evidence['basis'] == 'documented_installed_assembly'
    assert evidence['installed_mass_total_kg'] == pytest.approx(hand, abs=.01)
    assert design['mass']['component_allocation']['assigned_masses_kg']['propulsion'] == pytest.approx(evidence['installed_mass_total_kg'])
    assert 'zenith.aero' in evidence['installed_source'] and 'Nie obejmuje' in evidence['installed_conditions']


def test_engine_is_never_weightless_in_sized_mode():
    topic = json.loads(CASE.read_text(encoding='utf-8'))
    for key in ('engine_installed_mass_kg', 'engine_mass_source', 'engine_mass_conditions'):
        topic.pop(key)  # the documented installation belongs to the Rotax 912 UL, not to an unselected engine
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
    limits = design['envelope']['limits']
    assert design['mass']['component_closure']['n_ult'] == pytest.approx(max(limits['n_ult_pos'], abs(limits['n_ult_neg'])))


REAL_MOTOGLIDERS = ('mg-hoffmann-h36-dimona', 'mg-scheibe-sf-28a-tandem-falke', 'mg-hb-flugtechnik-hb-23-hobbyliner',
                    'mg-valentin-taifun-17s', 'mod-pl-21', 'mod-pl-22', 'mod-pl-23', 'mod-pl-24', 'mod-pl-10', 'mod-pl-14', 'mod-pl-11',
                    'mg-avo-68-samburo', 'mg-fournier-rf5b', 'mg-grob-g109b', 'mg-stemme-s10vt', 'mg-szd-45-ogar', 'mg-vivat-l13se',
                    'mg-schleicher-ash31mi', 'mg-scheibe-sf25c-rotax', 'mg-diamond-hk36ts', 'mg-fournier-rf4d')


def test_mass_equations_reproduce_real_motogliders():
    """Wzory Raymera z korektą kompozytową a masa własna 21 konstrukcji z bazy: bez błędu systematycznego."""
    rows = {r['id']: r for r in load_aircraft()}
    ratios = []
    for key in REAL_MOTOGLIDERS:
        r = rows[key]
        area, span, m0 = r['s'], r['b'], r['m0']
        length = max(5.5, min(.45 * span, 8.5))
        arm, diameter = .55 * length, .85
        geom = dict(wing=dict(S=area, AR=span ** 2 / area, b=span, tc_ratio=.14, sweep_deg=0, eta=.5),
                    fuselage=dict(length=length, diameter=diameter, S_wet=math.pi * diameter * length * .75),
                    horizontal_tail=dict(S_h=.55 * area * area / span / arm, AR_h=4.5, l_h=arm),
                    vertical_tail=dict(S_v=.03 * area * span / arm, AR_v=1.5))
        params = dict(aircraft_type='motoglider', engine_type='prop', n_engines=1, engine_power_kw=r['p_kw'], m_fuel=.07 * m0,
                      n_crew=1, n_pax=1, technology='composite', cruise_speed_kmh=140, cruise_altitude_m=2000,
                      landing_gear_type='tailwheel')
        estimate = estimate_component_masses(m0, params, geom=geom, flight_envelope=dict(n_ult=7.95))
        engine = estimate['breakdown']['propulsion']
        ratios.append((r['me'] - engine) / (estimate['m_empty'] - engine))
    assert statistics.median(ratios) == pytest.approx(1, abs=.03)
    assert .84 < min(ratios) and max(ratios) < 1.22
