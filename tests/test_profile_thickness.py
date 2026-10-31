"""Selected profile thickness reaches geometry, drag, stiffness and reports."""
from copy import deepcopy

import pytest

from app import app
from calculations import run_bipol_project
from calculations.airfoils import airfoil_200mm
from calculations.aeroelastics import estimate_aeroelastics
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.profile_geometry import resolve_profile_geometry
from calculations.validation import validate_parameters

# Maximum is between the former 0.5%-chord samples, and not rounded to mm.
X_MAX = .30321789
TC = .15367239
ORDINATES = 'Precise custom profile\n' + '\n'.join(f'{x} {y}' for x, y in [
    (1, 0), (.8, .03), (.5, .05), (X_MAX, TC / 2), (.1, .04), (0, 0),
    (.1, -.04), (X_MAX, -TC / 2), (.5, -.05), (.8, -.03), (1, 0)])


def resolve(**changes):
    params = validate_parameters(changes)
    states = {}
    context = resolve_profile_geometry(params, states)
    return params, states, context


@pytest.mark.parametrize('name,value', [('NACA 0015', .15), ('naca-4418', .18), ('NACA 23021', .21)])
def test_nominal_naca_thickness_is_resolved_before_sizing(name, value):
    params, states, context = resolve(airfoil=name)
    assert params['tc_ratio'] == value
    assert states['tc_ratio']['state'] == 'derived'
    assert context['assessment']['thickness_definition'] == 'nominal_naca'
    assert not context['assessment']['mismatch']


def test_pasted_geometry_overrides_its_naca_label_without_sampling_or_rounding_loss():
    profile = airfoil_200mm('NACA 0012', ORDINATES)
    assert profile['thickness_ratio'] == pytest.approx(TC, abs=1e-14)
    assert profile['thickness_x_ratio'] == pytest.approx(X_MAX, abs=1e-14)
    params, _, context = resolve(airfoil='NACA 0012', airfoil_coordinates=ORDINATES)
    assert params['tc_ratio'] == pytest.approx(TC, abs=1e-14)
    assert context['assessment']['thickness_definition'] == 'vertical_gap'


@pytest.mark.parametrize('name,coordinates', [('', ''), ('UNKNOWN', ''), ('NACA 0015', 'INVALID')])
def test_missing_geometry_retains_an_explicit_assumption_and_explains_it(name, coordinates):
    params, states, context = resolve(airfoil=name, airfoil_coordinates=coordinates, tc_ratio=.17)
    assert params['tc_ratio'] == .17
    assert states['tc_ratio']['state'] == 'input'
    assert not context['assessment']['derived']
    assert context['assessment']['profile_tc_ratio'] is None


def test_manual_mode_preserves_the_assumption_and_reports_the_mismatch():
    params, states, context = resolve(airfoil='NACA 0015', tc_ratio=.12, profile_thickness_mode='assumed')
    assert params['tc_ratio'] == .12 and states['tc_ratio']['state'] == 'input'
    assert context['assessment']['mismatch']
    assert context['assessment']['profile_tc_ratio'] == .15
    assert '12% zamiast 15%' in context['assessment']['note']


@pytest.mark.parametrize('name', ['NACA 0001', 'NACA 0035'])
def test_auto_mode_rejects_out_of_scope_thickness_without_clamping(name):
    with pytest.raises(ValueError, match='zakres modelu'):
        resolve(airfoil=name)
    # A preliminary assumption is still possible, with a visible mismatch.
    params, _, context = resolve(airfoil=name, profile_thickness_mode='assumed')
    assert params['tc_ratio'] == .12 and context['assessment']['mismatch']


def test_a_conflicting_lock_requires_explicit_resolution():
    with pytest.raises(ValueError, match='Zablokowane t/c'):
        resolve(airfoil='NACA 0015', locked_params=['tc_ratio'])
    _, states, _ = resolve(airfoil='NACA 0015', tc_ratio=.15, locked_params=['tc_ratio'])
    assert states['tc_ratio']['state'] == 'derived'
    params, states, _ = resolve(airfoil='NACA 0015', locked_params=['tc_ratio'], profile_thickness_mode='assumed')
    assert params['tc_ratio'] == .12 and states['tc_ratio']['state'] == 'locked'


@pytest.mark.parametrize('replacement', ['nan', 'inf', '-inf', '1e309'])
def test_nonfinite_pasted_ordinates_are_rejected(replacement):
    with pytest.raises(ValueError, match='skończonymi'):
        airfoil_200mm('', ORDINATES.replace(str(TC / 2), replacement))


def test_crossing_and_zero_thickness_surfaces_are_rejected():
    for text in (ORDINATES.replace(f'{X_MAX} {TC / 2}', f'{X_MAX} -0.2'),
                 '\n'.join(' '.join([line.split()[0], '0']) for line in ORDINATES.splitlines()[1:])):
        with pytest.raises(ValueError, match='dodatnią grubość'):
            airfoil_200mm('', text)


@pytest.fixture(scope='module')
def result():
    return run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'], airfoil='NACA 0015'))


def test_thickness_reaches_wet_area_compressibility_and_stiffness(result):
    wing = result['geometry']['wing']
    assert result['params']['tc_ratio'] == wing['tc_ratio'] == .15
    assert wing['S_wet'] == pytest.approx(2 * wing['S_exposed'] * (1 + .25 * .15), rel=1e-12)
    cp = result['aerodynamics']['compressibility']
    # On this unswept conventional profile, Korn's estimate uses t/c = .15.
    assert cp['m_dd'] == pytest.approx(round(.87 - .15 - result['aerodynamics']['cz_opt'] / 10, 3))
    thinner = deepcopy(result['geometry'])
    thinner['wing']['tc_ratio'] = .12
    thin_stiffness = estimate_aeroelastics(thinner, result['aerodynamics'], result['mass'],
                                          result['envelope'], result['params'])
    assert result['aeroelastics']['torsional_stiffness_gj'] > thin_stiffness['torsional_stiffness_gj']
    assert result['aeroelastics']['bending_stiffness_ei'] > thin_stiffness['bending_stiffness_ei']


def test_recalculation_and_formula_sheet_use_the_same_raw_thickness(result):
    again = run_bipol_project(result['params'])
    assert again['geometry']['wing']['tc_ratio'] == .15
    sheet = build_sheet(again)
    assert sheet.entries['tc']['value'] == .15
    assert 'NACA' in sheet.entries['tc']['source']
    assert not {k: v for k, v in sheet.entries.items() if v['consistent'] is False}


@pytest.mark.parametrize('section', ['p3', 'p4'])
def test_reports_explain_the_mismatch_and_reference_polar(section):
    params = dict(AIRCRAFT_PRESETS['ga_trainer'], airfoil='NACA 0015',
                  profile_thickness_mode='assumed', tc_ratio=.12)
    response = app.test_client().post('/report/project/' + section, json=params)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'profile-thickness-assessment" data-mismatch="true"' in html
    assert '12% zamiast 15%' in html and 'NACA 23012' in html


def test_api_rejects_unknown_source_mode():
    response = app.test_client().post('/api/calculate', json={'profile_thickness_mode': 'unknown'})
    assert response.status_code == 400


@pytest.mark.parametrize('preset', list(AIRCRAFT_PRESETS))
def test_selected_thickness_is_consistent_for_every_aircraft_preset(preset):
    result = run_bipol_project(dict(AIRCRAFT_PRESETS[preset], airfoil='NACA 0015'))
    assert result['geometry']['wing']['tc_ratio'] == .15
    assert result['profile_geometry']['derived']
    sheet = build_sheet(result)
    assert not {k: v for k, v in sheet.entries.items() if v['consistent'] is False}


@pytest.mark.parametrize('name,tc', [('NACA 0004', .04), ('NACA 0005', .05), ('NACA 0025', .25), ('NACA 0030', .30)])
def test_compressibility_does_not_silently_replace_a_valid_wing_thickness(name, tc):
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'], airfoil=name))
    comp = result['aerodynamics']['compressibility']
    assert comp['tc_ratio'] == result['geometry']['wing']['tc_ratio'] == tc
    assert comp['m_dd'] == round(.87 - tc - result['aerodynamics']['cz_opt'] / 10, 3)


def test_pasted_ordinates_that_overflow_at_drawing_scale_are_rejected():
    with pytest.raises(ValueError, match='skończone skalowanie'):
        airfoil_200mm('', ORDINATES.replace(str(TC / 2), '1e307'))
