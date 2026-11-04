"""One comparison sample — the aircraft nearest in MTOW to the design — for every calculation and report."""
import math

import pytest

from calculations import run_bipol_project
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trends import load_aircraft, design_reference, select_references, get_trend_suggestions
from calculations.validation import validate_parameters


def design(**changes):
    return dict(AIRCRAFT_PRESETS['motoglider_aos'], **changes)


def test_an_assumed_reference_mass_is_not_a_second_sample_method():
    # Projects saved with the former "initial" method get the one method of the guide path.
    p = validate_parameters(design(trend_reference_mode='initial', mass_initial_guess=700, trend_nearest_count=20))
    assert 'trend_reference_mode' not in p and 'mass_initial_guess' not in p
    result = run_bipol_project(dict(p))
    assert result['params']['_reference_mass'] != 700
    assert len(result['bipol_projects']['p1']['trend_analysis']['similar_aircraft']) >= 20


def test_design_reference_is_the_fixed_point_of_its_own_comparison_sample():
    result = run_bipol_project(design())
    params = result['params']
    reference = params['_reference_mass']
    assert reference == pytest.approx(design_reference(params, 50)['mass'])
    sample = result['bipol_projects']['p1']['trend_analysis']['similar_aircraft']
    assert len(sample) == 50
    pool = sorted(select_references({**params, '_similar_count': 0, '_reference_mass': None}),
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


def test_cached_reference_numbers_are_recomputed():
    params = design()
    params.update(_reference={'mass': 999999}, _reference_mass=999999, _similar_count=1)
    p = validate_parameters(params)
    assert not {'_reference', '_reference_mass', '_similar_count'} & p.keys()
    result = run_bipol_project(params)
    assert result['params']['_reference_mass'] < 10000
    assert result['bipol_projects']['p1']['trend_analysis']['selected_n'] == 50


def test_catalog_engine_and_its_source_survive_iterative_sample_selection():
    result = run_bipol_project(dict(design(), engine_fuel_mode='catalog', engine_model_id='rotax_912_ul'))
    assert result['engine_selection']['model'] == 'Rotax 912 UL'
    assert result['params']['sfc'] == pytest.approx(16.2 * .72 * 1000 / 43.5)
    assert result['sizing']['design_point']['power_kw'] == 58
    assert result['params']['_similar_count'] == 50
