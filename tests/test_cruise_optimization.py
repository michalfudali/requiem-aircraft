"""Finite-fuel analytic optima, feasible bounds and independent dense sweeps."""
import math

import pytest

from calculations import run_bipol_project
from calculations.atmosphere import G0, isa_atmosphere
from calculations.cruise_optimization import optimize_cruise
from calculations.mission_cruise import cruise_distance
from calculations.presets import AIRCRAFT_PRESETS


def inputs(engine):
    params = dict(engine_type=engine, aircraft_type='jet_business' if engine=='jet' else 'piston_ga',
                  prop_efficiency=.82, sfc=.62 if engine=='jet' else 265, cruise_speed_kmh=250,
                  cruise_altitude_m=2000)
    sizing = {'design_point': {'power_kw':500, 'thrust_kn':20}}
    return params, sizing


@pytest.mark.parametrize('engine,key', [('prop','max_range'), ('jet','max_endurance')])
def test_finite_fuel_optimum_matches_analytic_geometric_mean_mass(engine, key):
    params, sizing = inputs(engine)
    result = optimize_cruise(params, sizing, 1000, 800, 16, .03, .05, 1.5, 2000)
    # Maximizing the arctangent mass integral gives CL at sqrt(m_start*m_end)
    # equal to sqrt(CD0/k), not a CL based on the arithmetic mean mass.
    expected = math.sqrt(2*G0*math.sqrt(1000*800)/(isa_atmosphere(2000)['rho']*16)*math.sqrt(.05/.03))*3.6
    assert result['available']
    assert result[key]['speed_kmh'] == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize('engine', ['prop','jet'])
def test_continuous_optima_dominate_a_dense_independent_speed_sweep(engine):
    params, sizing = inputs(engine)
    result = optimize_cruise(params, sizing, 1000, 800, 16, .03, .05, 1.5, 2000)
    low, high = result['min_speed_kmh'], result['max_speed_kmh']
    best_range = best_time = 0
    for i in range(2001):
        speed = low + (high-low)*i/2000
        distance = cruise_distance(1000, 800, dict(params,cruise_speed_kmh=speed), dict(S=16,cx0=.03,k=.05))
        best_range = max(best_range,distance/1000)
        best_time = max(best_time,distance/(speed/3.6)/3600)
    assert result['max_range']['range_km'] >= best_range*(1-1e-10)
    assert result['max_endurance']['endurance_h'] >= best_time*(1-1e-10)
    for key in ('max_range','max_endurance'):
        point = result[key]
        assert low <= point['speed_kmh'] <= high
        assert point['cl_start'] <= 1.5 + 1e-10
        assert point['excess_power_start_w'] >= -1e-5


def test_stall_boundary_can_be_the_range_optimum():
    params, sizing = inputs('prop')
    result = optimize_cruise(params, sizing, 1000, 800, 16, .03, .05, .4, 2000)
    assert result['max_range']['speed_kmh'] == pytest.approx(result['min_speed_kmh'], rel=1e-9)
    assert result['max_range']['cl_start'] == pytest.approx(.4, rel=1e-9)


def test_available_power_can_limit_optimum_to_upper_speed_boundary():
    params, sizing = inputs('prop')
    sizing['design_point']['power_kw']=30
    result = optimize_cruise(params,sizing,1000,800,16,.03,.05,1.5,0)
    assert result['available']
    assert result['max_range']['speed_kmh'] == pytest.approx(result['max_speed_kmh'], rel=1e-8)
    assert abs(result['max_range']['excess_power_start_w']) < 1e-5


@pytest.mark.parametrize('engine,start,end,status', [('none',1000,800,'unpowered'),
    ('prop',1000,1000,'no_cruise_fuel'), ('prop',1000,1100,'invalid_masses')])
def test_inapplicable_cases_do_not_invent_zero_range_optima(engine,start,end,status):
    params, sizing = inputs(engine)
    result = optimize_cruise(params,sizing,start,end,16,.03,.05,1.5,2000)
    assert not result['available'] and result['status']==status
    assert result['max_range'] is None and result['max_endurance'] is None


def test_underpowered_cruise_has_no_optimum():
    params, sizing = inputs('prop')
    sizing['design_point']['power_kw']=.001
    result = optimize_cruise(params,sizing,1000,800,16,.03,.05,1.5,2000)
    assert result['status']=='unreachable' and result['max_range'] is None


@pytest.mark.parametrize('name', AIRCRAFT_PRESETS)
def test_project_optima_and_requested_point_retain_unrounded_physics(name):
    result = run_bipol_project(AIRCRAFT_PRESETS[name])
    data = result['performance']['paturski_p6']['range_endurance_6_5']
    optimum = data['optimization']
    if result['params']['engine_type']=='none':
        assert data['l_max_km'] is None
        return
    assert optimum['available']
    rows = data['table_6_3']
    for row in rows:
        assert optimum['max_range']['range_km'] >= row['l_const_v_km_unrounded']*(1-1e-9)
        assert optimum['max_endurance']['endurance_h'] >= row['t_const_v_h_unrounded']*(1-1e-9)
    requested = [row for row in rows if row['requested_speed']]
    if requested:
        assert len(requested)==1
        assert requested[0]['v_kmh_unrounded'] == pytest.approx(result['params']['cruise_speed_kmh'], rel=1e-12)
        assert data['range_at_requested_speed_km']==requested[0]['l_const_v_km_unrounded']
    for altitude in data['by_altitude']:
        assert altitude['optimization']['start_mass_kg']==optimum['start_mass_kg']
