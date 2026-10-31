"""Project limits use lift equilibrium without speed rounding or hidden tolerance."""
import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.atmosphere import G0, RHO0
from calculations.high_lift import stall_requirement
from calculations.presets import AIRCRAFT_PRESETS


@pytest.mark.parametrize('actual,passed', [(99.99, True), (100, True), (100.004, False), (100.8, False)])
def test_stall_requirement_uses_raw_speed_even_when_display_rounds_to_limit(actual, passed):
    result = stall_requirement({'v_stall_kmh': 100},
                               {'terms': {'vs_lnd': actual / 3.6}, 'speeds': {'vs_lnd_kmh': round(actual, 1)}})
    assert result['actual_kmh'] == pytest.approx(actual, abs=1e-12)
    assert result['passed'] is passed
    assert result['margin_kmh'] == pytest.approx(100 - actual, abs=1e-12)
    assert result['certification_verified'] is False


@pytest.mark.parametrize('invalid', [0, -1, float('nan'), float('inf')])
def test_stall_requirement_rejects_invalid_physical_input(invalid):
    with pytest.raises(ValueError):
        stall_requirement({'v_stall_kmh': 100}, {'terms': {'vs_lnd': invalid}})


@pytest.mark.parametrize('name', AIRCRAFT_PRESETS)
def test_p4_and_global_check_use_same_physical_stall_requirement(name):
    result = run_bipol_project(AIRCRAFT_PRESETS[name])
    high_lift = result['bipol_projects']['p4']['high_lift']
    check = high_lift['stall_requirement']
    expected = math.sqrt(2 * result['mass']['m0'] * G0 /
                         (RHO0 * result['geometry']['wing']['S'] * result['aerodynamics']['cz_max_lnd'])) * 3.6
    assert check['actual_kmh'] == pytest.approx(expected, rel=1e-12)
    assert check['mass_basis'] == 'MTOW' and check['speed_basis'] == 'EAS'
    assert check['limit_kmh'] == result['params']['v_stall_kmh']
    global_check = next(c for c in result['compliance_checks'] if c['parameter'].startswith('Prędkość przeciągnięcia z klapami'))
    assert global_check['passed'] == check['passed'] == (expected <= check['limit_kmh'])
    assert 'is_cs23_compliant' not in high_lift
    assert 'cs23_stall_limit_kmh' not in high_lift


def fixed_wing_exceedance():
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'wing_input_mode': 'area_aspect', 'wing_area_m2': 20,
              'design_iteration_mode': 'coupled'}
    first = run_bipol_project(params)
    params['v_stall_kmh'] = first['performance']['terms']['vs_lnd'] * 3.6 - .04
    return params


def test_reducing_project_limit_by_four_hundredths_is_not_accepted():
    result = run_bipol_project(fixed_wing_exceedance())
    check = result['bipol_projects']['p4']['high_lift']['stall_requirement']
    assert check['margin_kmh'] == pytest.approx(-.04, abs=1e-7)
    assert not check['passed']


def test_report_and_api_explain_failed_project_requirement_without_certification_claim():
    params = fixed_wing_exceedance()
    client = app.test_client()
    result = client.post('/api/calculate', json=params)
    assert result.status_code == 200
    check = result.get_json()['bipol_projects']['p4']['high_lift']['stall_requirement']
    assert check['passed'] is False
    response = client.post('/report/project/p4', json=params)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="p4-stall-requirement"' in html
    assert 'Wymaganie nie jest spełnione' in html
    assert 'Nie stanowi wykazania zgodności certyfikacyjnej' in html
