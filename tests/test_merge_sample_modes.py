"""Both merged reference methods must share one sample across calculations and reports."""
import math

import pytest

from calculations import run_bipol_project
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trends import load_aircraft, design_reference, select_references, get_trend_suggestions
from calculations.validation import validate_parameters


def design(**changes):
    return dict(AIRCRAFT_PRESETS['motoglider_aos'], trend_reference_mode='design',
                trend_nearest_count=50, empty_mass_model='trend', **changes)


def test_initial_reference_remains_an_independent_assumption():
    p = dict(AIRCRAFT_PRESETS['motoglider_aos'], trend_reference_mode='initial',
             trend_nearest_count=20, mass_initial_guess=700)
    rows = select_references(p)
    pool = sorted((r for r in load_aircraft() if r['aircraft_type'] == 'motoglider' and r['engine_type'] == 'prop'),
                  key=lambda r: (abs(math.log(r['m0'] / 700)), r['id']))
    assert [r['id'] for r in rows] == [r['id'] for r in pool[:20]]


def test_design_reference_is_the_fixed_point_of_its_own_comparison_sample():
    result = run_bipol_project(design())
    params = result['params']
    reference = params['_reference_mass']
    assert reference == pytest.approx(design_reference(params, 50)['mass'])
    sample = result['bipol_projects']['p1']['trend_analysis']['similar_aircraft']
    assert len(sample) == 50
    pool = sorted((r for r in load_aircraft() if r['aircraft_type'] == 'motoglider' and r['engine_type'] == 'prop'),
                  key=lambda r: (abs(math.log(r['m0'] / reference)), r['id']))
    assert [r['id'] for r in sample] == [r['id'] for r in pool[:50]]
    law = result['mass']['empty_mass_law']
    points = result['bipol_projects']['p1']['trend_analysis']['two_point']
    assert (law['A'], law['C']) == (points['A'], points['C'])
    sheet = build_sheet(result)
    assert {'tr_A', 'tr_C'} <= set(sheet.entries['e_m0']['deps'])
    assert not {k for k, e in sheet.entries.items() if e['consistent'] is False}


def test_project_suggestions_use_the_identical_fixed_point_and_sample(client):
    params = design()
    result = run_bipol_project(params)
    response = client.post('/api/trends/suggestions', json=params)
    assert response.status_code == 200
    analysis = result['bipol_projects']['p1']['trend_analysis']
    assert response.get_json()['suggestions'] == analysis['suggestions']
    assert response.get_json()['sample'] == analysis['sample']
    assert get_trend_suggestions('motoglider', engine_type='prop', project=params)['sample'] == analysis['sample']


def test_migration_preserves_old_design_choice_but_recomputes_cached_values():
    params = design()
    params.pop('trend_reference_mode')
    params.update(_reference={'mass': 999999}, _reference_mass=999999, _similar_count=1)
    p = validate_parameters(params)
    assert p['trend_reference_mode'] == 'design'
    assert not {'_reference', '_reference_mass', '_similar_count'} & p.keys()
    result = run_bipol_project(params)
    assert result['params']['_reference_mass'] < 10000
    assert result['bipol_projects']['p1']['trend_analysis']['selected_n'] == 50


def test_explicit_reference_choice_takes_precedence_over_old_cached_results():
    params = design()
    params.update(trend_reference_mode='initial', mass_initial_guess=700, empty_mass_model='auto',
                  _reference={'mass': 999999})
    result = run_bipol_project(params)
    assert result['bipol_projects']['p1']['trend_analysis']['sample']['reference_mass'] == 700
    assert '_reference' not in result['params']


def test_catalog_engine_and_its_source_survive_iterative_sample_selection():
    result = run_bipol_project(dict(design(), engine_fuel_mode='catalog', engine_model_id='rotax_912_ul'))
    assert result['engine_selection']['model'] == 'Rotax 912 UL'
    assert result['params']['sfc'] == pytest.approx(16.2 * .72 * 1000 / 43.5)
    assert result['sizing']['design_point']['power_kw'] == 58
    assert result['params']['trend_reference_mode'] == 'design'


@pytest.mark.parametrize('invalid', ['unknown', 1, False])
def test_invalid_reference_method_is_rejected(invalid):
    with pytest.raises(ValueError):
        validate_parameters(dict(AIRCRAFT_PRESETS['motoglider_aos'], trend_reference_mode=invalid))
