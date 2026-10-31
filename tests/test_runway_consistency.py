"""Runway force balance and a continuous straight/circular landing trajectory."""
from copy import deepcopy
import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.atmosphere import G0
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.runway import landing_air_path, refine_takeoff_sizing, rolling_coefficient, takeoff_distance


@pytest.mark.parametrize('speed', [25, 60, 105, 115, 150])
def test_landing_path_intersects_obstacle_and_ground_without_artificial_height_cap(speed):
    angle = math.radians(3.5)
    radius = speed ** 2 / (.15 * G0)
    flare_height = radius * (1 - math.cos(angle))
    path = landing_air_path(speed)
    # Circle equation: x^2 + (R-h)^2 = R^2, independently of angle parametrization.
    arc_height = min(15, flare_height)
    arc_x = math.sqrt(2 * radius * arc_height - arc_height ** 2)
    straight_x = (15 - arc_height) / math.tan(angle)
    assert path['distance_m'] == pytest.approx(arc_x + straight_x, rel=1e-12)
    assert path['straight_m'] * math.tan(angle) + arc_height == pytest.approx(15, abs=1e-10)
    assert path['straight_m'] >= 0


def test_landing_path_is_continuous_and_smooth_where_obstacle_enters_flare():
    angle = math.radians(3.5)
    speed = math.sqrt(15 * .15 * G0 / (1 - math.cos(angle)))
    before, at, after = [landing_air_path(speed * ratio)['distance_m'] for ratio in (1-1e-6, 1, 1+1e-6)]
    assert 0 < at - before < .01 and 0 < after - at < .01
    assert at - before == pytest.approx(after - at, rel=1e-5)
    assert landing_air_path(speed, obstacle_height_m=0)['distance_m'] == 0


@pytest.mark.parametrize('kwargs', [dict(approach_speed_ms=0), dict(approach_speed_ms=float('nan')),
    dict(approach_speed_ms=50, approach_angle_deg=0), dict(approach_speed_ms=50, obstacle_height_m=-1),
    dict(approach_speed_ms=50, load_factor=1)])
def test_landing_path_rejects_invalid_geometry(kwargs):
    with pytest.raises(ValueError):
        landing_air_path(**kwargs)


@pytest.mark.parametrize('params,mu', [({}, .03), ({'runway_surface':'grass'}, .055),
    ({'runway_surface':'grass','mu_ground':.12}, .12), ({'mu_ground':0}, 0)])
def test_rolling_assumption_preserves_surface_or_explicit_value(params, mu):
    assert rolling_coefficient(params) == mu


def test_takeoff_sizing_meets_the_same_grass_model_used_for_performance():
    mass, area = 1200, 20
    geom = {'wing': {'S': area}}
    aero = {'cz_max_to': 1.6, 'cx0_to': .03, 'k_to': .05}
    base = {'design_point': {'required_power_kw': 0, 'power_kw': 0}}
    params = dict(engine_type='prop', takeoff_distance_m=500, prop_efficiency=.82,
                  prop_eff_to=.65, runway_surface='grass')
    sizing = deepcopy(base)
    refine_takeoff_sizing(sizing, geom, aero, params, mass)
    loading = sizing['takeoff_model_requirement']
    actual = takeoff_distance(mass*G0/area, 1.6, .03, .05, 'prop', loading, mu_ground=.055)
    assert actual['available'] and actual['distance_to_15m'] <= 500 + 1e-8
    below = takeoff_distance(mass*G0/area, 1.6, .03, .05, 'prop', loading*.99999, mu_ground=.055)
    assert below['distance_to_15m'] > 500
    paved = deepcopy(base)
    refine_takeoff_sizing(paved, geom, aero, dict(params, runway_surface='paved'), mass)
    assert loading > paved['takeoff_model_requirement']


def test_high_speed_landing_report_uses_only_arc_below_fifteen_metres():
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['vlj_jet'], wing_input_mode='area_aspect',
        wing_area_m2=3, range_km=100, cruise_speed_kmh=800, v_stall_kmh=350,
        design_iteration_mode='preliminary'))
    landing = result['performance']['landing']
    assert landing['terms']['h_flare'] > 15
    assert landing['approach_straight_m'] == 0
    assert landing['air_approach_m'] == pytest.approx(landing['flare_horizontal_m'], abs=.051)
    sheet = build_sheet(result)
    assert 'gamma_fl' in sheet.entries
    for key in ('R_fl', 'h_fl', 'gamma_fl', 's_air', 's_L15'):
        assert sheet.entries[key]['consistent'] is True
    assert not {key: (value['value'], value['computed']) for key, value in sheet.entries.items()
                if value['consistent'] is False}
    assert sheet.entries['L_R']['computed'] == pytest.approx(sheet.entries['L_R']['value'], rel=1e-12)


@pytest.mark.parametrize('params', [{'runway_surface':'ice'}, {'mu_ground':-0.1}, {'mu_ground':float('inf')}])
def test_api_rejects_unknown_or_invalid_rolling_inputs(params):
    assert app.test_client().post('/api/calculate', json={**AIRCRAFT_PRESETS['ga_trainer'], **params}).status_code == 400
