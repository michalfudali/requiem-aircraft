"""Methods from the BIPOL I course aids: BIPOL_2 (matching chart), BIPOL_3 (mass analysis),
BIPOL_5 and the project description (take-off time, range at three altitudes)."""
import math

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import RHO0
from calculations.sizing import calculate_matching_chart, landing_ws, takeoff_tw

POWERED = [name for name, p in AIRCRAFT_PRESETS.items() if p['engine_type'] != 'none']


def test_matching_chart_reproduces_lecture_example():
    # Handout 2: 33 100 kg jet, 9 700 kg fuel, 780 km/h at 10 000 m, Vmin 200 km/h, A = 8, K = 15.
    cx0 = math.pi * 8 * 0.8 / (4 * 15 ** 2)
    params = dict(aircraft_type='jet_transport', engine_type='jet', v_stall_kmh=200, cruise_speed_kmh=780,
                  cruise_altitude_m=10000, aspect_ratio=8, oswald_e=0.8, cx0=cx0, cz_max_to=2.0,
                  cz_max_lnd=2.17, takeoff_distance_m=1100, landing_distance_m=1100, climb_rate_ms=9.0)
    mass = {'m_fuel': 9700.0, 'fuel_fractions_detail': {'total_mff': 0.72, 'landing': 0.975}}
    s = calculate_matching_chart(params, m0=33100.0, mass=mass)
    assert s['assumptions']['v_climb_kmh'] == pytest.approx(345, abs=1)       # Vmin + 0,25(Vmax − Vmin)
    assert s['assumptions']['climb_gradient'] == pytest.approx(0.094, abs=0.001)
    assert s['assumptions']['m_mid_cruise_kg'] == pytest.approx(28250)
    assert s['ws_max_range'] == pytest.approx(4405, rel=0.01)                 # 3757 N/m² at mid-cruise mass
    assert landing_ws(2.17, 1100) == pytest.approx((1100 - 122) * 2.17 / 0.75)
    assert takeoff_tw(4130, 2.0, 1100) == pytest.approx(0.297, abs=0.001)


def test_minimum_speed_line_keeps_the_cz_safety_factor():
    p = AIRCRAFT_PRESETS['ga_trainer']
    r = run_bipol_project(p)
    s = r['sizing']
    p = r['params']  # The same high-lift configuration as the downstream stall check.
    assert s['ws_stall_max'] == pytest.approx(0.5 * RHO0 * (p['v_stall_kmh'] / 3.6) ** 2 * p['cz_max_lnd'] / 1.1, abs=0.1)
    assert s['takeoff_basis'] == '15m'


def test_short_landing_distance_limits_the_wing_loading():
    r = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'landing_distance_m': 300})
    s = r['sizing']
    assert s['design_point']['limit_by'] == 'długość lądowania'
    assert s['design_point']['ws'] == pytest.approx(s['ws_landing'], abs=0.1)
    assert s['ws_landing'] < s['ws_stall_max']


def test_takeoff_curve_without_15m_distance_is_labelled_as_ground_roll():
    s = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'takeoff_distance_m': 0})['sizing']
    assert s['takeoff_basis'] == 'ground_roll'
    assert s['assumptions']['takeoff_run_m'] == AIRCRAFT_PRESETS['ga_trainer']['takeoff_run_m']


@pytest.mark.parametrize('name', AIRCRAFT_PRESETS)
def test_flight_cg_range_reports_the_unrounded_mass_analysis_criterion(name):
    r = run_bipol_project(AIRCRAFT_PRESETS[name])
    b = r['balance']
    cg = b['cg_range']
    expected=cg['aft_pct'] <= 35.0 and (cg['forward_pct'] >= 25.0 or cg['delta_pct'] > 10.0)
    assert b['cg_check']['passed'] is expected
    global_check=next(c for c in r['compliance_checks'] if c['parameter'].startswith('Zakres położeń ŚC'))
    assert global_check['passed'] is expected
    if not expected:
        # A preliminary preset need not be feasible. Keep the physical layout
        # bounds and report the failure instead of moving masses to pass it.
        assert b['x_lemac_m']/r['geometry']['fuselage']['length'] == pytest.approx(.25) or \
            b['x_lemac_m']/r['geometry']['fuselage']['length'] == pytest.approx(.56)
        assert 'niespełnione' in b['cg_check']['note']
    assert b['loading_states'][-1]['key'] == 'mtow'
    assert b['stability']['static_margin_aft_pct'] >= 5.0
    if AIRCRAFT_PRESETS[name]['aircraft_type'] != 'uav':
        keys = {v['key'] for v in b['pilot_variants']}
        assert 'mtow' in keys
        assert all(min(v['light_pct'], v['heavy_pct']) >= cg['forward_pct'] for v in b['pilot_variants'])


def test_no_payload_states_are_included():
    keys = [s['key'] for s in run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])['balance']['loading_states']]
    assert {'tow_no_payload', 'mlw_no_payload', 'mlw', 'mtow', 'oew'} <= set(keys)


@pytest.mark.parametrize('name', POWERED)
def test_takeoff_time_follows_the_takeoff_segments(name):
    r = run_bipol_project(AIRCRAFT_PRESETS[name])
    t = r['performance']['takeoff']
    assert 0 < t['ground_roll_time_s'] < t['time_to_15m_s']
    # Constant mean acceleration: ground roll = V_LOF · t / 2, with V_LOF = 1.15 V_S,TO of the take-off model.
    ws = r['mass']['m0'] * 9.80665 / r['geometry']['wing']['S']
    v_lof = 1.15 * math.sqrt(2 * ws / (RHO0 * r['aerodynamics']['cz_max_to']))
    assert 2 * t['ground_roll_m'] / t['ground_roll_time_s'] == pytest.approx(v_lof, rel=0.02)


@pytest.mark.parametrize('name', POWERED)
def test_range_and_endurance_at_three_altitudes_use_offer_chart_speeds(name):
    ra = run_bipol_project(AIRCRAFT_PRESETS[name])['bipol_projects']['p5']['paturski_p6']['range_endurance_6_5']
    labels = [a['label'] for a in ra['by_altitude']]
    assert labels == ['0 m', 'wysokość przelotowa', 'pułap praktyczny']
    for altitude in ra['by_altitude']:
        assert all(altitude['v_min_kmh'] <= row['v_kmh'] <= altitude['v_max_kmh'] for row in altitude['rows'])
