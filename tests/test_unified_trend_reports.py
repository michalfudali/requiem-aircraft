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


def test_auto_mass_model_prefers_a_supported_trend_and_preserves_manual_choices():
    p = validate_parameters(dict(AIRCRAFT_PRESETS['regional_turboprop'], aircraft_type='jet_transport', engine_type='jet', sfc=.6))
    assert p['empty_mass_model'] == 'auto'
    _, fit = mass_trend(p)
    share, meta = empty_mass_law(p)
    assert meta['mode'] == 'trend' and meta['selection_mode'] == 'auto'
    assert (meta['A'], meta['C']) == pytest.approx((fit['A'], fit['C']))
    assert share(77000) == pytest.approx(fit['A'] * 77000 ** fit['C'])
    share, meta = empty_mass_law(dict(p, empty_mass_fraction=.61))
    assert meta['mode'] == 'fixed_fraction' and share(77000) == .61
    _, meta = empty_mass_law(dict(p, empty_mass_model='class_correlation'))
    assert meta['mode'] == 'class_correlation'


def test_auto_does_not_treat_a_weak_rising_fit_as_a_design_mass_law():
    p = validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer']))
    _, meta = empty_mass_law(p)
    assert meta['mode'] == 'class_correlation'
    assert 'nie spełnia' in meta['selection_reason']


def test_applied_mass_law_remains_bound_to_the_selected_sample():
    settings = dict(AIRCRAFT_PRESETS['regional_turboprop'], trend_nearest_count=50, mass_initial_guess=22000)
    old = get_trend_suggestions('turboprop_regional', m0=22000, settings=settings)['suggestions']['me_m0']['apply']
    assert old['empty_mass_model'] == 'trend'
    changed = {**settings, **{k: v for k, v in old.items() if v is not None}, 'trend_nearest_count': 40}
    _, fit = mass_trend(changed)
    _, law = empty_mass_law(changed)
    assert law['A'] == pytest.approx(fit['A'])
    assert law['C'] == pytest.approx(fit['C'])
    assert law['A'] != pytest.approx(old['empty_mass_trend_A'])


def test_selected_observations_and_weights_are_identical_for_all_entry_points():
    p = validate_parameters({**AIRCRAFT_PRESETS['motoglider_aos'], 'trend_nearest_count': 24,
                             'mass_initial_guess': 600, 'trend_weighting': 'family'})
    analysis = analyze_trends(p, 600, 350)
    wizard = get_trend_suggestions(p['aircraft_type'], m0=600, engine_type=p['engine_type'], settings=p)
    assert wizard['suggestions'] == analysis['suggestions']
    rows = select_references(p)
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
