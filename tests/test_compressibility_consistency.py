"""Independent Korn/Lock cases, geometry convention, raw limits and scope reporting."""
import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.atmosphere import G0, isa_atmosphere
from calculations.calc_sheet import build_sheet
from calculations.compressibility import calculate_compressibility, airfoil_technology
from calculations.presets import AIRCRAFT_PRESETS


@pytest.mark.parametrize('name', ['NACA 0016', 'NACA 6618', 'NACA 2416', 'NACA 23016', 'NACA 63112', 'NACA 0012-64'])
def test_digit_six_does_not_turn_a_classical_profile_into_a_six_series_profile(name):
    tech = airfoil_technology(name)
    assert tech['family'] == 'conventional_assumption'
    assert tech['kappa_a'] == .87


@pytest.mark.parametrize('name', ['NACA 64-212', 'NACA 64A212', 'NACA 63(2)-215', 'NACA 65,3-218', 'NACA 632215'])
def test_naca_six_series_uses_the_published_reference_factor(name):
    tech = airfoil_technology(name)
    assert tech['family'] == 'naca6' and tech['kappa_a'] == .87


@pytest.mark.parametrize('name', ['NASA SC(2)-0412', 'sc2-0610', 'SC (2) 0714'])
def test_standard_supercritical_designations_use_the_reference_factor(name):
    tech = airfoil_technology(name)
    assert tech['family'] == 'supercritical' and tech['kappa_a'] == .95


@pytest.mark.parametrize('name', ['CUSTOM NACA 6 TEST', 'SCOTT2', 'SUPERCRITICAL IDEA', 'NACA 6', ''])
def test_arbitrary_label_does_not_claim_a_calibrated_profile_technology(name):
    tech = airfoil_technology(name)
    assert tech['family'] == 'conventional_assumption'
    assert 'Założenie' in tech['technology_source']


def test_korn_and_lock_match_a_hand_calculated_unswept_case():
    result = calculate_compressibility(.75, .4, .12, 0, 'NACA 64-212')
    raw = result['terms']
    assert raw['m_dd'] == pytest.approx(.71, abs=1e-14)
    assert raw['m_crit'] == pytest.approx(.6022782654984058, abs=1e-14)
    assert raw['delta_cx_wave'] == pytest.approx(20 * (.75 - .6022782654984058)**4, rel=1e-12)


def test_lock_curve_has_continuous_slope_and_derivative_point_one_at_drag_divergence():
    def wave(mach):
        return calculate_compressibility(mach, .4)['terms']['delta_cx_wave']
    for point in (.6022782654984058, .71):
        h = 1e-6
        left = (wave(point) - wave(point-h)) / h
        right = (wave(point+h) - wave(point)) / h
        assert left == pytest.approx(right, abs=5e-6)
        if point == .71:
            assert (left+right)/2 == pytest.approx(.1, abs=1e-9)


def test_rounding_does_not_decide_the_scope_or_drag_divergence_margin():
    mdd = .71
    below = calculate_compressibility(mdd-1e-8, .4)
    above = calculate_compressibility(mdd+1e-8, .4)
    assert below['mach'] == below['m_dd'] == above['mach'] == above['m_dd']
    assert below['drag_divergence_safe'] and not above['drag_divergence_safe']
    crit = .6022782654984058
    below = calculate_compressibility(crit-1e-9, .4)
    above = calculate_compressibility(crit+1e-9, .4)
    assert below['delta_cx_wave'] == above['delta_cx_wave'] == 0.
    assert not below['requires_wave_polar'] and above['requires_wave_polar']


@pytest.mark.parametrize('changes', [dict(mach=1.), dict(mach=1.2), dict(cz=10.), dict(tc=.04, sweep_deg=55.)])
def test_out_of_scope_points_are_not_replaced_by_artificial_mach_limits(changes):
    result = calculate_compressibility(**dict(dict(mach=.8, cz=.4), **changes))
    assert not result['model_applicable'] and result['requires_wave_polar']
    assert result['delta_cx_wave'] is result['terms']['delta_cx_wave'] is None
    if changes.get('mach', 0) >= 1:
        assert result['prandtl_glauert_factor'] is None
    if changes.get('cz') == 10:
        assert result['terms']['m_dd'] < 0  # preserves the result instead of silently returning 0.4


@pytest.mark.parametrize('field,value', [('mach', -1.), ('mach', float('inf')), ('cz', float('nan')),
                                        ('cz', -.1), ('tc', .01), ('sweep_deg', 60.), ('mach', None)])
def test_invalid_correlation_inputs_fail_clearly(field, value):
    with pytest.raises(ValueError):
        calculate_compressibility(**dict(dict(mach=.2, cz=.4), **{field: value}))


@pytest.fixture(scope='module')
def high_speed():
    return run_bipol_project(dict(AIRCRAFT_PRESETS['vlj_jet'], cruise_speed_kmh=800, airfoil='NACA 0016'))


def test_project_diagnostic_uses_actual_lift_at_mtow_and_half_chord_secant(high_speed):
    r = high_speed
    comp = r['aerodynamics']['compressibility']; w = r['geometry']['wing']; p = r['params']
    atmosphere = isa_atmosphere(p['cruise_altitude_m'])
    speed = p['cruise_speed_kmh']/3.6
    expected_cl = r['mass']['m0']*G0/(.5*atmosphere['rho']*speed**2*w['S'])
    half_sweep = math.atan(math.tan(math.radians(w['sweep_deg'])) - (w['cr']-w['ct'])/(2*w['b']))
    assert comp['terms']['cl'] == pytest.approx(expected_cl, rel=1e-12)
    assert comp['terms']['sweep_half_chord_deg'] == pytest.approx(math.degrees(half_sweep), abs=1e-12)
    assert comp['terms']['cl'] != r['aerodynamics']['cz_opt']
    assert comp['family'] == 'conventional_assumption'
    assert comp['tc_ratio'] == .16


def test_wave_drag_is_explicitly_diagnostic_and_extrapolated_cruise_is_unverified(high_speed):
    assert high_speed['aerodynamics']['compressibility']['requires_wave_polar']
    scope = [c for c in high_speed['compliance_checks'] if c['parameter'].startswith('[Ściśliwość]')]
    assert len(scope) == 1 and not scope[0]['passed']
    assert 'Niezweryfikowane' in scope[0]['actual']
    assert any('nie jest dodany' in note for note in high_speed['model_scope']['limitations'])
    sheet = build_sheet(high_speed)
    assert not {k: v for k, v in sheet.entries.items() if v['consistent'] is False}
    assert sheet.entries['wave_cx']['value'] == high_speed['aerodynamics']['compressibility']['terms']['delta_cx_wave']


@pytest.mark.parametrize('section', ['p4', 'p5'])
def test_partial_reports_keep_the_cruise_scope_warning_and_correlation_provenance(section):
    params = dict(AIRCRAFT_PRESETS['vlj_jet'], cruise_speed_kmh=800, airfoil='NACA 0016')
    response = app.test_client().post('/report/project/' + section, json=params)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-wave-polar-required="true"' in html
    assert 'Niezweryfikowane dla zadanej prędkości' in html
    assert 'ConfigAeroTransonics.pdf' in html
    assert 'nie jest dodany' in html


def test_low_speed_cruise_does_not_acquire_a_wave_scope_warning():
    result = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    assert not result['aerodynamics']['compressibility']['requires_wave_polar']
    assert not any(c['parameter'].startswith('[Ściśliwość]') for c in result['compliance_checks'])


@pytest.mark.parametrize('section', ['p4', 'p5'])
def test_api_reports_handle_a_supersonic_point_without_fabricated_wave_values(section):
    params = dict(AIRCRAFT_PRESETS['vlj_jet'], cruise_speed_kmh=1200, airfoil='NACA 0016')
    result = run_bipol_project(params)
    comp = result['aerodynamics']['compressibility']
    assert comp['mach'] > 1 and comp['delta_cx_wave'] is None
    assert comp['prandtl_glauert_factor'] is None
    response = app.test_client().post('/report/project/' + section, json=params)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'poza zakresem' in html and 'data-wave-polar-required="true"' in html
    assert 'wave_cx' not in build_sheet(result).entries
