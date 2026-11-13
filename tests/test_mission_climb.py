"""Independent force, energy, unit and analytic checks of climb fuel integration."""
import math

import pytest

from calculations.atmosphere import G0
from calculations.mission_climb import climb_segment, assess_climb


def inputs(engine='prop', **extra):
    return dict(engine_type=engine, cruise_speed_kmh=144., cruise_altitude_m=2000.,
                climb_start_altitude_m=0., mission_climb_rate_ms=3.,
                sfc=270. if engine == 'prop' else .6, prop_efficiency=.82, **extra)


@pytest.mark.parametrize('engine', ['prop', 'jet'])
def test_constant_ld_climb_has_an_independent_analytic_solution(engine):
    p = inputs(engine)
    v, roc, ld, mass = 40., 3., 20., 600.
    cosine = math.sqrt(1-(roc/v)**2)
    if engine == 'prop':
        # Independent substitution of the documented P4 efficiency curve.
        eta = .82*(1-.18*(1/1.15-1)**2)
        exponent = p['sfc']/3.6e9/eta*G0*(1+v*cosine/(ld*roc))*2000
    else:
        exponent = p['sfc']/3600*(cosine/ld+roc/v)/roc*2000
    expected = mass*math.exp(-exponent)
    actual = climb_segment(mass, p, ld=ld)
    assert actual['end_mass_kg'] == pytest.approx(expected, abs=1e-9)
    assert actual['duration_s'] == pytest.approx(2000/3)
    assert actual['fuel_kg'] > 0


@pytest.mark.parametrize('engine', ['prop', 'jet'])
def test_integrated_fuel_equals_work_or_thrust_impulse_in_manufacturer_units(engine):
    p = inputs(engine, climb_start_speed_kmh=110.)
    polar = dict(S=16., cx0=.025, k=.014)
    r = climb_segment(600., p, polar)
    fuel = (p['sfc']/3.6e9*r['shaft_work_j'] if engine == 'prop'
            else p['sfc']/(3600*G0)*r['thrust_impulse_ns'])
    assert r['fuel_kg'] == pytest.approx(fuel, abs=2e-11)
    for point in r['nodes']:
        dvdt = ((144-110)/3.6/2000)*3
        assert point['useful_power_w'] == pytest.approx(
            point['drag_n']*point['tas_ms']+point['mass_kg']*(G0*3+point['tas_ms']*dvdt))
    finer = climb_segment(600., p, polar, max_step_m=25.)
    assert r['fuel_kg'] == pytest.approx(finer['fuel_kg'], rel=1e-8)
    fast = climb_segment(600., p, polar, detailed=False)
    assert fast['fuel_kg'] == pytest.approx(r['fuel_kg'], abs=1e-10)


def test_zero_height_and_no_acceleration_burns_no_climb_fuel():
    p = inputs()
    p['cruise_altitude_m'] = 0.
    r = climb_segment(600., p, ld=20.)
    assert r['fuel_kg'] == r['duration_s'] == 0.


@pytest.mark.parametrize('change', [dict(mission_climb_rate_ms=0), dict(mission_climb_rate_ms=50),
                                  dict(cruise_altitude_m=-1), dict(sfc=float('nan')),
                                  dict(cruise_altitude_m=0, climb_start_speed_kmh=100)])
def test_unphysical_or_undefined_profile_is_rejected(change):
    with pytest.raises(ValueError):
        climb_segment(600., {**inputs(), **change}, ld=20.)


def test_actual_installed_engine_and_stall_limit_are_checked():
    p = inputs()
    r = climb_segment(600., p, dict(S=16., cx0=.025, k=.014))
    assert assess_climb(r, p, dict(design_point=dict(power_kw=58)), 1.4)['passed']
    assert not assess_climb(r, p, dict(design_point=dict(power_kw=10)), 1.4)['passed']
    assert not assess_climb(r, p, dict(design_point=dict(power_kw=58)), .1)['passed']


@pytest.fixture(scope='module')
def topic7():
    import json
    from pathlib import Path
    from calculations import run_bipol_project
    p = json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    return run_bipol_project(p)


def test_topic7_climb_pays_for_height_and_drag_instead_of_using_zero_fuel(topic7):
    r = topic7
    cl = r['mass']['mission_assumptions']['climb']
    dh = cl['altitude_end_m']-cl['altitude_start_m']
    assert dh == 2000
    assert cl['end_mass_kg']*G0*dh <= cl['potential_work_j'] <= cl['start_mass_kg']*G0*dh
    assert cl['fuel_kg'] > r['params']['sfc']/3.6e9*cl['potential_work_j']/r['params']['prop_efficiency'] > 0
    assert cl['drag_model'] == 'p4_polar' and cl['assessment']['passed']
    assert r['design_iteration']['converged']
    phase = next(p for p in r['mass']['mission_phases'] if p['key'] == 'climb')
    assert phase['fuel_burn_kg'] == pytest.approx(cl['fuel_kg'])
    from calculations.calc_sheet import build_sheet
    sheet = build_sheet(r)
    assert sheet.entries['cl_mfuel']['consistent'] and sheet.entries['r_CL']['consistent']
    assert all(e['consistent'] is not False for e in sheet.entries.values())


def test_explicit_corke_cannot_turn_a_below_chart_point_into_a_zero_fuel_pass(client):
    response = client.post('/api/calculate', json=dict(inputs(), cruise_speed_kmh=115., climb_fraction_mode='corke'))
    assert response.status_code == 400
    assert 'zakresem wykresu Corke' in response.get_data(as_text=True)


def test_omitted_profile_uses_positive_design_rate_but_preserves_explicit_profile():
    from calculations.validation import validate_parameters
    from calculations.official_topics import ALL_TOPICS
    from calculations.mass import calculate_mass_sizing
    jet = next(t['parameters'] for t in ALL_TOPICS if t['num'] == 61)
    assert jet['climb_rate_ms'] == 12
    normalized = validate_parameters(jet)
    assert normalized['mission_climb_rate_ms'] == 12
    assert validate_parameters({**jet, 'mission_climb_rate_ms': 7.5})['mission_climb_rate_ms'] == 7.5
    legacy = calculate_mass_sizing(jet)
    assert legacy['mission_assumptions']['climb']['duration_s'] == pytest.approx(11000/12)
    assert validate_parameters({**jet, 'climb_rate_ms': 0})['mission_climb_rate_ms'] == 3
    with pytest.raises(ValueError, match='mission_climb_rate_ms'):
        validate_parameters({**jet, 'mission_climb_rate_ms': 0})


@pytest.mark.parametrize('required', [0, .000001, .01, .049, .05, 12])
def test_inherited_profile_stays_in_its_input_domain_on_replay(required):
    from calculations.validation import validate_parameters
    p = validate_parameters({'climb_rate_ms': required})
    expected = max(.05, required) if required > 0 else 3.
    assert p['mission_climb_rate_ms'] == expected
    assert validate_parameters(p)['mission_climb_rate_ms'] == expected
