"""Reference provenance, unit conversions and independently checked P1 equations."""
import copy
from datetime import date
import json
import math
from pathlib import Path

import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0
from calculations.performance import calculate_performance
from calculations.trends import analyze_trends, fit_regression, load_aircraft, predict, select_references


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_catalog_contains_hundreds_of_traceable_unique_observations(client):
    catalog = client.get('/api/aircraft').json
    assert catalog['total'] >= 700
    assert len({r['id'] for r in catalog['aircraft']}) == catalog['total']
    assert sum(catalog['counts'].values()) == catalog['total']
    for r in catalog['aircraft']:
        assert r['m0'] > 0 and r['source_locator'] and r['source_references']
        assert r['source_id'] in catalog['sources']
        assert r['me'] is None or 0 < r['me'] < r['m0']
        assert r['p_kw'] is None if r['engine_type'] == 'jet' else r['t_kn'] is None
    json.dumps(catalog, allow_nan=False)


def test_cado_converts_per_engine_ratings_without_mixing_mach_and_kmh():
    rows = {r['model']: r for r in load_aircraft() if r['source_id'] == 'cado'}
    seneca = rows['PA-34-220TSeneca5']
    assert seneca['n_engines'] == 2 and seneca['p_kw'] == 328
    assert seneca['thrust_to_weight'] is None
    a320 = rows['A320-200']
    assert a320['t_kn'] == pytest.approx(240.204)
    assert a320['cruise_mach'] == .78
    assert a320['v_cruise_kmh'] is None and a320['v_max'] is None
    assert a320['thrust_to_weight'] == pytest.approx(240204/(77020*G0))
    assert a320['ar'] == pytest.approx(33.89**2/122.63)


def test_fast_installed_power_and_linked_engine_thrust():
    rows = {r['model']: r for r in load_aircraft() if r['source_id'] == 'fast'}
    assert rows['ATR42-300']['p_kw'] == pytest.approx(2*1323.898)
    assert rows['A340-211']['t_kn'] == pytest.approx(4*138780/1000)
    assert rows['A340-211']['engine_source_locator'].startswith('Jet Engines!')
    assert rows['Learjet23']['me'] is None  # Missing is not an estimated average.
    assert rows['A300-F4-203']['aircraft_type'] == 'jet_transport'


def test_known_linear_and_power_laws_are_recovered():
    fit = fit_regression([(1950+i*5, 7+2*i*5) for i in range(8)])
    assert fit['slope'] == pytest.approx(2)
    assert predict(fit, 1990) == pytest.approx(87)
    fit = fit_regression([(m, .92*m**(-.06)) for m in [100,300,1000,3000,9000]], power=True)
    assert fit['A'] == pytest.approx(.92) and fit['C'] == pytest.approx(-.06)
    assert fit['r2'] == pytest.approx(1)
    assert predict(fit, 1600) == pytest.approx(.92*1600**(-.06))


def test_weighting_limits_the_effect_of_repeated_variants():
    base = [(1,1), (2,4), (3,3)]
    a = fit_regression(base)
    repeated = [base[0]]*100 + base[1:]
    weighted = fit_regression(repeated, [1/100]*100+[1,1])
    unweighted = fit_regression(repeated)
    assert weighted['slope'] == pytest.approx(a['slope'])
    assert weighted['intercept'] == pytest.approx(a['intercept'])
    assert unweighted['slope'] != pytest.approx(a['slope'])


@pytest.mark.parametrize('points,power', [([],False), ([(1,2),(2,3)],False), ([(2,1),(2,2),(2,3)],False), ([(0,2),(-1,2),(1,1)],True)])
def test_degenerate_regressions_have_no_fictitious_fit(points, power):
    assert fit_regression(points, power=power) is None


def test_cohort_respects_class_source_engine_count_and_manual_ids():
    params = {'aircraft_type':'piston_ga','engine_type':'prop','trend_source':'cado','trend_engine_count':2,
              'trend_nearest_count':20,'mass_initial_guess':1200}
    rows = select_references(params)
    assert rows and all(r['aircraft_type']=='piston_ga' and r['source_id']=='cado' and r['n_engines']==2 for r in rows)
    ids = [r['id'] for r in rows[:3]]
    chosen = select_references({**params,'trend_aircraft_ids':ids})
    assert {r['id'] for r in chosen} == set(ids)
    assert select_references({**params,'trend_aircraft_ids':[]}) == []


def test_sample_is_independent_of_the_computed_mass_and_of_the_old_count_key():
    base = {'aircraft_type':'motoglider','engine_type':'prop'}
    whole = select_references(base)
    # Projects saved before the change keep trend_count=50; it no longer narrows the sample.
    assert select_references({**base,'trend_count':50}) == whole
    near = select_references({**base,'trend_nearest_count':20,'mass_initial_guess':700})
    assert len(near) == 20 and set(r['id'] for r in near) <= set(r['id'] for r in whole)
    a = analyze_trends(base, 650, 400)
    b = analyze_trends(base, 900, 560)
    assert a['sample'] == b['sample'] and a['suggestions']['ar']['suggested_value'] == b['suggestions']['ar']['suggested_value']


def test_forecast_is_five_years_after_design_year_and_does_not_invent_production_dates():
    a=analyze_trends({'aircraft_type':'jet_transport','engine_type':'jet','trend_source':'fast','trend_count':0},70000,42000)
    assert a['mass_fit']['n'] >= 20
    # BIPOL_1, s. 1: extrapolate five years ahead of the design, not of the newest record.
    assert a['forecast_year'] == date.today().year + 5 == a['reference_year'] + 5
    for trend in a['time_trends']:
        if trend['fit']:
            assert trend['forecast_year'] == a['forecast_year']
            assert trend['extrapolation_years'] == pytest.approx(a['forecast_year'] - trend['fit']['x_max'])
            assert trend['forecast'] == pytest.approx(predict(trend['fit'],trend['forecast_year']))
    assert all(r['year_basis']=='certification' for r in a['similar_aircraft'])
    ga=analyze_trends({'aircraft_type':'piston_ga','engine_type':'prop','trend_source':'cado','trend_count':0},1100,700)
    assert ga['selected_n']>=20 and ga['time_trends'][0]['available_n']<20
    assert any('dat' in w for w in ga['warnings'])


@pytest.mark.parametrize('preset', ['glider_pw5','motoglider_aos','uav_tactical'])
def test_new_upstream_cohorts_never_fall_back_to_powered_ga(preset):
    r=run_bipol_project(AIRCRAFT_PRESETS[preset])
    a=r['bipol_projects']['p1']['trend_analysis']
    assert all(row['aircraft_type']==r['params']['aircraft_type'] and row['engine_type']==r['params']['engine_type'] for row in a['similar_aircraft'])
    if a['selected_n']<20:
        assert a['warnings']
    if not a['selected_n']:
        assert a['reg_A'] is None and a['we_wo_trend'] is None
    json.dumps(r,allow_nan=False)


def test_variable_sweep_factor_is_applied_only_to_project_prediction():
    p={'aircraft_type':'piston_ga','engine_type':'prop','_reference_mass':1200}
    a=analyze_trends(p,1200,700)
    b=analyze_trends({**p,'variable_sweep':True},1200,700)
    assert a['mass_fit']==b['mass_fit']
    assert b['we_wo_trend']==pytest.approx(a['we_wo_trend']*1.04)


@pytest.mark.parametrize('payload',[{'trend_count':1.5},{'trend_source':'invented'},{'trend_weighting':'unknown'},
    {'trend_year_min':2000,'trend_year_max':1950},{'trend_aircraft_ids':['fake']},{'trend_aircraft_ids':'bad'},
    {'fuel_reserve_factor':.5},{'mission_ld_factor':0},{'variable_sweep':'false'}])
def test_invalid_analysis_controls_return_400(client,payload):
    assert client.post('/api/calculate',json=payload).status_code==400


@pytest.mark.parametrize('preset', ['pzl_kos','vlj_jet','glider_pw5'])
def test_all_seven_mission_phases_close_and_reserve_matches_equation_four(preset):
    r=run_bipol_project(AIRCRAFT_PRESETS[preset]);m=r['mass'];f=m['fuel_fractions_detail']
    product=math.prod(f[key] for key in ('warmup','takeoff','climb','cruise','descent','loiter','landing'))
    assert product==pytest.approx(f['total_mff'],abs=.0003)
    assert m['m_fuel']/m['m0']==pytest.approx(1.06*(1-f['total_mff']),abs=.0001)
    assert r['bipol_projects']['p2']['mission_profile'][-1]['mass_end_kg']==pytest.approx(m['m0']*f['total_mff'],abs=.06)
    phases=r['bipol_projects']['p2']['mission_profile']
    assert phases[-1]['mass_end_kg']==pytest.approx(phases[-2]['mass_end_kg']*f['landing'],abs=.1)
    assert m['mission_assumptions']['mass_residual_relative']<.001


def test_galinski_start_is_not_double_counted_as_taxi():
    r=run_bipol_project({**AIRCRAFT_PRESETS['pzl_kos'],'mission_phase_model':'galinski'})
    f=r['mass']['fuel_fractions_detail']
    assert f['warmup']==1 and f['takeoff']==.975 and f['landing']==.975


def test_analytical_operating_points_optimize_the_correct_objectives():
    r=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer']);p=r['bipol_projects']['p1']['preliminary']
    cd0,k=r['aerodynamics']['cx0_clean'],r['aerodynamics']['k_clean']
    points={v['key']:v for v in p['operating_points']}
    assert p['cx0_from_kmax']==pytest.approx(cd0)
    for key,power in [('max_ld',1),('jet_range',.5),('prop_endurance',1.5)]:
        cl=points[key]['cl'];objective=lambda c:c**power/(cd0+k*c*c)
        assert objective(cl)>objective(cl*.95) and objective(cl)>objective(cl*1.05)
    turn=p['turn_45'];v=r['params']['cruise_speed_kmh']/3.6
    assert turn['radius_m']==pytest.approx(v*v/G0)
    assert turn['rate_deg_s']==pytest.approx(math.degrees(G0/v))


def test_insufficient_thrust_cannot_create_a_sustained_level_turn():
    r=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer']);sizing=copy.deepcopy(r['sizing'])
    sizing['design_point']['pw']=1e-8
    perf=calculate_performance(r['mass']['m0'],r['geometry'],r['aerodynamics'],sizing,r['params'])
    assert perf['turn']['mode']=='unavailable' and not perf['turn']['level_sustained']
    assert perf['turn']['r_min_m'] is None and perf['turn']['t_360_s'] is None
    glider=run_bipol_project(AIRCRAFT_PRESETS['glider_pw5'])
    assert glider['performance']['turn']['mode']=='gliding'
    assert not glider['performance']['turn']['level_sustained']


@pytest.mark.parametrize('source',['cado','fast'])
def test_source_files_and_licenses_are_available_offline(client,source,monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    data=client.get(f'/download/aircraft/{source}/data')
    assert data.status_code==200 and json.loads(data.data)
    assert client.get(f'/download/aircraft/{source}/license').status_code==200
    assert client.get('/download/aircraft/unknown/data').status_code==404


@pytest.mark.parametrize('url',['/report?sections=p1','/report/project/p1','/report?sections=p1&preset=glider_pw5'])
def test_reports_share_real_sample_sources_and_inline_plots(client,url):
    response=client.get(url)
    assert response.status_code==200
    text=response.get_data(as_text=True)
    assert 'data-trend-report' in text
    # Only sources actually present in the chosen cohort belong in the report.
    # Gliders do not acquire a CADO citation just because the database also holds GA aircraft.
    from calculations.trends import SOURCES
    from calculations.validation import validate_parameters
    params = validate_parameters(AIRCRAFT_PRESETS['glider_pw5' if 'glider_pw5' in url else 'pzl_kos'])
    analysis = analyze_trends(params, 1000, 600)
    for source_id in analysis['sources']:
        assert SOURCES[source_id]['license'] in text
    assert ('Apache-2.0' in text) == ('fast' in analysis['sources'])
    assert 'nie rok produkcji' in text and 'Jane\'s Aircraft' not in text
    assert 'statistical_averages' not in text
    if 'glider_pw5' not in url:assert '<svg xmlns=' in text
