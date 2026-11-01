"""BIPOL_1 trend suggestions: one sample, the handout's method and a traceable origin of every value."""
import math
from datetime import date

import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.mass import calculate_mass_sizing
from calculations.trends import analyze_trends, get_trend_suggestions, predict, two_point_coefficients
from calculations.validation import validate_parameters


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture(scope='module')
def ga():
    return run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])


def test_suggestions_use_the_p1_sample(ga):
    a = ga['bipol_projects']['p1']['trend_analysis']
    models = {r['model'] for r in a['similar_aircraft']}
    assert a['sample']['selected_n'] == a['selected_n']
    for s in a['suggestions'].values():
        if s['provenance']:
            assert {o['model'] for o in s['provenance']['observations']} <= models
            assert s['provenance']['basis'].startswith('BIPOL_1.pdf')


def test_two_point_reading_reproduces_the_fitted_mass_line(ga):
    a = ga['bipol_projects']['p1']['trend_analysis']
    tp = a['two_point']
    assert tp['C'] == pytest.approx(math.log(tp['y1'] / tp['y2']) / math.log(tp['x1'] / tp['x2']))
    assert tp['A'] == pytest.approx(tp['y1'] / tp['x1'] ** tp['C'])
    assert (tp['A'], tp['C']) == pytest.approx((a['reg_A'], a['reg_C']))
    assert two_point_coefficients(a['mass_fit'])['A'] == pytest.approx(tp['A'])


def test_averages_are_weighted_means_of_the_listed_observations(ga):
    s = ga['bipol_projects']['p1']['trend_analysis']['suggestions']
    for key in ('vh', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio', 'dihedral_deg'):
        item = s[key]
        obs = item['provenance']['observations']
        mean = sum(o['value'] * o['weight'] for o in obs) / sum(o['weight'] for o in obs)
        assert item['model_type'] == 'mean' and item['n'] == len(obs)
        assert item['suggested_value'] == pytest.approx(mean, abs=10 ** -(3 if key != 'dihedral_deg' else 1))


def test_missing_vertical_tail_volume_is_reported_not_invented(ga):
    v_v = ga['bipol_projects']['p1']['trend_analysis']['suggestions']['v_v']
    assert v_v['suggested_value'] is None and v_v['available_n'] == 0
    assert any('nie podstawia' in w for w in v_v['provenance']['warnings'])
    motoglider = get_trend_suggestions('motoglider')['suggestions']['v_v']
    assert motoglider['model_type'] == 'mean' and 0.015 < motoglider['suggested_value'] < 0.04


def test_time_forecast_is_five_years_after_the_design_year():
    data = get_trend_suggestions('jet_transport', m0=77000)
    assert data['forecast_year'] == date.today().year + 5
    ar = data['suggestions']['ar']
    assert ar['model_type'] == 'time_trend'
    fit = ar['provenance']['fit']
    assert ar['suggested_value'] == pytest.approx(predict(fit, data['forecast_year']), abs=0.01)
    assert fit['y_min'] <= ar['suggested_value'] <= fit['y_max']


def test_forecast_outside_every_similar_aircraft_falls_back_to_the_mean():
    ar = get_trend_suggestions('turboprop_regional', m0=22000)['suggestions']['ar']
    fit = ar['provenance']['fit']
    assert ar['model_type'] == 'mean'
    forecast = ar['provenance']['alternatives'][0]['value']
    assert forecast > fit['y_max']
    assert any('poza zakres próby' in w for w in ar['provenance']['warnings'])


def test_empty_mass_suggestion_inserts_equation_one_into_the_mass_balance():
    preset = AIRCRAFT_PRESETS['regional_turboprop']
    me = run_bipol_project(preset)['bipol_projects']['p1']['trend_analysis']['suggestions']['me_m0']
    apply = me['apply']
    assert apply['empty_mass_fraction'] is None and apply['empty_mass_trend_C'] < 0
    params = {**preset, 'empty_mass_trend_A': apply['empty_mass_trend_A'],
              'empty_mass_trend_C': apply['empty_mass_trend_C'], 'variable_sweep': True}
    mass = calculate_mass_sizing(validate_parameters(params))
    assert mass['empty_mass_model'] == 'bipol1_trend'
    expected = apply['empty_mass_trend_A'] * mass['m0'] ** apply['empty_mass_trend_C'] * 1.04
    assert mass['empty_fraction'] == pytest.approx(expected, abs=1e-4)


def test_rising_empty_mass_trend_is_explained_when_equation_five_has_no_solution(ga):
    apply = ga['bipol_projects']['p1']['trend_analysis']['suggestions']['me_m0']['apply']
    assert apply['empty_mass_trend_C'] > 0
    # A positive C alone does not prove absence of a root. Force an
    # impossible law (me/m0 > 1 throughout the admissible mass interval).
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'empty_mass_trend_A': 20,
              'empty_mass_trend_C': apply['empty_mass_trend_C']}
    with pytest.raises(ValueError, match=r'Równanie \(1\).*C < 0'):
        calculate_mass_sizing(validate_parameters(params))


def test_equation_one_is_not_clamped_in_the_mass_balance():
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'empty_mass_trend_A': 0.3, 'empty_mass_trend_C': 0.0}
    assert calculate_mass_sizing(validate_parameters(params))['empty_fraction'] == pytest.approx(0.3)


def test_equation_one_needs_both_coefficients():
    with pytest.raises(ValueError, match='A i C'):
        validate_parameters({**AIRCRAFT_PRESETS['ga_trainer'], 'empty_mass_trend_A': 0.9})


def test_api_filters_by_propulsion(client):
    data = client.get('/api/trends/suggestions?aircraft_type=motoglider&engine_type=jet').get_json()
    assert data['engine_type'] == 'jet' and data['sample']['selected_n'] >= 1
    assert data['suggestions']['pw']['provenance'] is None
    assert client.get('/api/trends/suggestions?aircraft_type=piston_ga&engine_type=rocket').status_code == 400


def test_p1_and_p2_reports_state_the_method(client):
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'empty_mass_trend_A': 0.5, 'empty_mass_trend_C': 0.035}
    html = client.post('/report?sections=p1,p2', json=params).get_data(as_text=True)
    assert 'Średnie wartości parametrów w próbie' in html
    assert 'Wartości parametrów wynikające z analizy trendów' in html
    assert 'pięć lat po roku opracowania projektu' in html
    assert 'wyznaczonej w analizie trendów (projekt 1)' in html


def test_wizard_and_panel_offer_the_origin_of_values(client):
    html = client.get('/').get_data(as_text=True)
    for marker in ('wizTrendProvenanceBasis', 'wizTrendProvenanceGeometry', 'trend_variable_sweep',
                   '/static/js/trend-provenance.js'):
        assert marker in html


def test_wizard_trend_charts_payload_and_dom_containers(client):
    html = client.get('/').get_data(as_text=True)
    for dom_id in ('wizTrendChartDetailsBasis', 'wizTrendChartSelectBasis', 'wizTrendChartStageBasis',
                   'wizTrendChartDetailsMission', 'wizTrendChartStageMission',
                   'wizTrendChartDetailsPropulsion', 'wizTrendChartStagePropulsion',
                   'wizTrendChartDetailsGeometry', 'wizTrendChartStageGeometry'):
        assert dom_id in html
    ga = client.get('/api/trends/suggestions?aircraft_type=piston_ga').get_json()
    charts = ga['charts']
    assert charts['ar']['kind'] == 'time' and len(charts['ar']['points']) >= 20 and charts['ar']['fit'] is not None
    assert charts['me_m0']['kind'] == 'mass' and charts['me_m0']['fit']['kind'] == 'power'
    assert 'pw' in charts and 'tw' not in charts
    assert charts['vh']['kind'] == 'mean' and len(charts['vh']['points']) >= 10
    glider = client.get('/api/trends/suggestions?aircraft_type=glider').get_json()['charts']
    assert 'pw' not in glider and 'tw' not in glider and len(glider['ar']['points']) >= 10
