"""A student must be able to reproduce the reported choices from the selected aircraft."""
from copy import deepcopy

import pytest

from app import app
from calculations import run_bipol_project
from calculations.bipol1 import empty_mass_law
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trend_workings import report_trend_workings, regression_working
from calculations.trends import (analyze_trends, forecast_rejection, get_trend_suggestions,
                                 mass_trend, sample_weights, select_references, valid_value)
from calculations.validation import validate_parameters


def test_mass_law_is_always_equation_one_of_the_sample_trend_line():
    # BIPOL_1, s. 1 and 4: no class correlation, typed fraction or own A, C in the project path.
    for changes in ({}, {'empty_mass_fraction': .61}, {'empty_mass_model': 'class_correlation'},
                    {'empty_mass_model': 'auto'}, {'empty_mass_model': 'coefficients', 'empty_mass_a': .9, 'empty_mass_c': -.05}):
        p = validate_parameters(dict(AIRCRAFT_PRESETS['regional_turboprop'], **changes))
        assert p['empty_mass_model'] == 'trend'
        _, fit = mass_trend(p)
        share, meta = empty_mass_law(p)
        assert meta['mode'] == 'trend' and (meta['A'], meta['C']) == pytest.approx((fit['A'], fit['C']))
        assert share(22000) == pytest.approx(fit['A'] * 22000 ** fit['C'])


def test_a_weak_trend_is_used_and_reported_not_replaced():
    r = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer']))
    law, ta = r['mass']['empty_mass_law'], r['bipol_projects']['p1']['trend_analysis']
    assert law['mode'] == 'trend' and (law['A'], law['C']) == (ta['two_point']['A'], ta['two_point']['C'])


def test_applied_mass_law_remains_bound_to_the_selected_sample():
    project = dict(AIRCRAFT_PRESETS['regional_turboprop'])
    old = run_bipol_project(project)['mass']['empty_mass_law']
    changed = run_bipol_project(dict(project, trend_nearest_count=30))
    law, ta = changed['mass']['empty_mass_law'], changed['bipol_projects']['p1']['trend_analysis']
    assert (law['A'], law['C']) == (ta['two_point']['A'], ta['two_point']['C'])
    assert law['A'] != pytest.approx(old['A'])


def test_selected_observations_and_weights_are_identical_for_all_entry_points():
    p = {**AIRCRAFT_PRESETS['motoglider_aos'], 'trend_nearest_count': 24, 'trend_weighting': 'family'}
    result = run_bipol_project(p)
    analysis = result['bipol_projects']['p1']['trend_analysis']
    wizard = get_trend_suggestions(p['aircraft_type'], engine_type=p['engine_type'], project=p)
    assert wizard['suggestions'] == analysis['suggestions'] and wizard['sample'] == analysis['sample']
    rows = select_references(result['params'])
    assert [r['id'] for r in rows] == [r['id'] for r in analysis['similar_aircraft']]
    weights = sample_weights(p['trend_weighting'])
    for metric in analysis['geometry_trends_analysis']['metrics']:
        subset = [r for r in rows if valid_value(metric['key'], r)]
        stats = metric['class_stats']
        assert stats['n'] == len(subset)
        ws = weights(subset)
        assert stats['mean'] == pytest.approx(sum(r[metric['key']] * w for r, w in zip(subset, ws)) / sum(ws))
    workings = report_trend_workings(analysis)
    for chart in analysis['report_charts']:
        working = workings['charts'][chart['mode']]
        if working:
            assert working['n'] == chart['n']
            assert working['slope'] == pytest.approx(chart['fit']['slope'])
            assert working['intercept'] == pytest.approx(chart['fit']['intercept'])
    for mean in workings['averages']:
        assert mean['value'] == pytest.approx(analysis['averages'][mean['key']]['mean'])


def test_good_extrapolation_is_not_rejected_for_exceeding_historical_values():
    fit = dict(r2=.99, x_min=2000, x_max=2025, y_min=8, y_max=10)
    assert forecast_rejection(fit, 11, 'ar', 2031) is None
    assert forecast_rejection(dict(fit, r2=.01), 11, 'ar', 2031)
    assert forecast_rejection(fit, -2, 'ar', 2031)
    assert forecast_rejection(fit, 11, 'ar', 2100)


def test_report_has_one_sample_eight_required_means_and_reproducible_workings():
    with app.test_client() as client:
        response = client.post('/report/project/p1', json=AIRCRAFT_PRESETS['motoglider_aos'])
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('data-trend-average=') == 8
    assert 'Proporcje geometryczne projektu na tle' not in html
    assert 'Przykłady proporcji geometrycznych samolotów tej klasy' not in html
    assert 'id="tab-sample-averages"' in html
    assert html.count('data-trend-choice=') <= 4
    assert 'S_{xy}' in html and r'\sum w_i' in html
    assert 'data-trend-choice="vh"' not in html
    assert html.count('id="q-tr_A"') == 1


def test_reporting_does_not_mutate_or_round_the_analysis():
    a = analyze_trends(validate_parameters(AIRCRAFT_PRESETS['glider_pw5']), 350, 200)
    original = deepcopy(a)
    report_trend_workings(a)
    assert a == original


@pytest.mark.parametrize('preset', ['ga_trainer', 'regional_turboprop', 'motoglider_aos', 'vlj_jet', 'uav_tactical'])
def test_report_relates_performance_to_each_required_design_axis(preset):
    p = validate_parameters(AIRCRAFT_PRESETS[preset])
    a = analyze_trends(p, 1000, 600)
    relations = [c['mode'].split(':') for c in a['report_charts'] if c['kind'] == 'relation']
    assert {x for x, y in relations} == {'ar', 'wing_loading_kg_m2',
                                       'thrust_to_weight' if p['engine_type'] == 'jet' else 'power_loading_kg_kw'}
    assert not {y for x, y in relations} & {'v_h', 'dihedral_deg', 'aileron_chord_ratio'}
