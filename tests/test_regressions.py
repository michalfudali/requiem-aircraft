"""Regresje błędów wykrytych po commicie 9fef4f5."""
import json
import math
import os
from pathlib import Path

import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0, RHO0
from calculations.polish_law import resolve_category, SUBCATEGORIES, check_compliance, suggest_subcategory


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.mark.parametrize('preset', AIRCRAFT_PRESETS)
def test_presets_close_mass_balance_and_obey_lift_equation(preset):
    result = run_bipol_project(AIRCRAFT_PRESETS[preset])
    mass = result['mass']
    total = sum(mass[k] for k in ('m_empty', 'm_fuel', 'm_payload', 'm_crew'))
    assert total == pytest.approx(mass['m0'], abs=0.2)
    wing = result['geometry']['wing']
    aero = result['aerodynamics']
    vs = result['performance']['speeds']['vs_lnd_kmh'] / 3.6
    lift = .5 * RHO0 * vs ** 2 * wing['S'] * aero['cz_max_lnd']
    assert lift == pytest.approx(mass['m0'] * G0, rel=.002)
    assert result['performance']['ceiling']['absolute_ceiling_m'] >= result['performance']['ceiling']['service_ceiling_m']
    assert not any(c['name'].startswith('Klasa konstrukcyjna') and not c['ok'] for c in result['easa_compliance']['checks'])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('payload', [None, [], 3, {'aspect_ratio': 0}, {'oswald_e': 0},
    {'aspect_ratio': 'NaN'}, {'cx0': float('inf')}, {'n_pax': 1.5},
    {'m_cargo': -1}, {'range_km': None}, {'prop_efficiency': 0},
    {'takeoff_run_m': 0}, {'v_stall_kmh': 300, 'cruise_speed_kmh': 100},
    {'v_stall_kmh': 1, 'takeoff_distance_m': 500}])
def test_invalid_inputs_are_json_400(client, payload):
    response = client.post('/api/calculate', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert response.json['message']


def test_low_stall_speed_with_takeoff_distance_never_divides_by_zero(client):
    params = dict(AIRCRAFT_PRESETS['pzl_kos'], v_stall_kmh=30, cz_max_lnd=2.2, takeoff_distance_m=400)
    response = client.post('/api/calculate', json=params)
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert min(response.json['sizing']['ws_values']) > 0


def test_propeller_takeoff_power_uses_mean_ground_roll_speed():
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos'], takeoff_distance_m=0))
    p, sizing = result['params'], result['sizing']
    ws = sizing['ws_values'][10]
    tw = 1.21 * ws / (G0 * RHO0 * p['cz_max_to'] * p['takeoff_run_m']) + .04
    v_lof = 1.15 * math.sqrt(2 * ws / (RHO0 * p['cz_max_to']))
    # Same convention as runway.takeoff_distance(): power at V_LOF/sqrt(2), not at V_LOF.
    assert sizing['curve_takeoff'][10] == pytest.approx(tw * v_lof / math.sqrt(2) / p['prop_eff_to'], abs=.01)


@pytest.mark.parametrize('category,vb_gust', [('cs23_level2', False), ('cs23_commuter', True), ('cs25_transport', True)])
def test_vb_gust_only_for_commuter_and_transport(category, vb_gust):
    preset = 'pzl_kos' if category == 'cs23_level2' else 'vlj_jet'
    env = run_bipol_project(dict(AIRCRAFT_PRESETS[preset], category=category))['envelope']
    assert env['gust_factors']['vb_gust'] is vb_gust
    assert (env['speeds']['v_b_kmh'] is not None) is vb_gust
    assert len(env['gust_pos']) == (4 if vb_gust else 3)
    assert 'JAR 23.333(c)' in env['gust_factors']['gust_basis'] or 'Pratta' in env['gust_factors']['gust_basis']


def test_impossible_mission_is_not_hidden_by_clamped_fuel_fraction(client):
    params = dict(AIRCRAFT_PRESETS['pzl_kos'], range_km=30000, sfc=1000)
    response = client.post('/api/calculate', json=params)
    assert response.status_code == 400
    assert 'bilansu' in response.json['message']


def test_no_fictitious_payload_added_to_zero_payload_uav(client):
    params = dict(AIRCRAFT_PRESETS['uav_tactical'], m_cargo=0)
    response = client.post('/api/calculate', json=params)
    assert response.status_code == 400
    assert 'dodatnią masę' in response.json['message']


def test_explicit_span_uses_same_aspect_ratio_for_sizing_and_aerodynamics():
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos'], wingspan_m=13.5))
    wing = result['geometry']['wing']
    assert wing['b'] == 13.5
    assert result['params']['aspect_ratio'] == pytest.approx(wing['AR'], abs=.006)
    # 76d212d derives the effective aspect ratio from the selected planform.
    k_expected = 1 / (math.pi * result['aerodynamics']['lambda_e'])
    assert result['aerodynamics']['k_clean'] == pytest.approx(k_expected, rel=.001)
    assert result['sizing']['design_point']['ws'] == pytest.approx(result['mass']['m0'] * G0 / wing['S'], rel=.001)


@pytest.mark.parametrize('category,mtom,seats', [('jar23_normal', 5670, 9), ('jar23_utility', 5670, 9),
                                                 ('jar23_aerobatic', 5670, 9), ('jar23_commuter', 8618, 19)])
def test_jar23_scope_follows_jar_23_1(category, mtom, seats):
    # JAR 23.1(a)(1): N/U/A ≤ 9 seats besides pilots and ≤ 5670 kg; (a)(2): propeller twin commuter ≤ 19 and ≤ 8618 kg.
    assert (SUBCATEGORIES[category]['mtom_max'], SUBCATEGORIES[category]['pax_max']) == (mtom, seats)
    assert suggest_subcategory(5000, 1, 5, False, 'jet', 'jet_business') == 'jar23_normal'
    assert suggest_subcategory(7000, 2, 15, False, 'prop', 'turboprop_regional', 2) == 'jar23_commuter'
    assert suggest_subcategory(7000, 2, 8, False, 'jet', 'jet_business', 2) == 'cs25_transport'


@pytest.mark.parametrize('old,new', [('cs23_level1', 'jar23_normal'), ('cs23_level2', 'jar23_normal'),
                                     ('cs23_level3', 'jar23_normal'), ('cs23_aerobatic', 'jar23_aerobatic'),
                                     ('cs23_commuter', 'jar23_commuter')])
def test_saved_cs23_level_keys_open_as_jar23_categories(old, new):
    assert resolve_category(old) == new


@pytest.mark.parametrize('category,mass', [('easa_uas_specific', 750), ('easa_uas_certified', 100)])
def test_uas_operation_category_has_no_600_kg_cutoff(category, mass):
    params = {'category': category, 'aircraft_type': 'uav', 'n_crew': 0, 'n_pax': 0}
    result = check_compliance(params, {'m0': mass})
    assert not any('granica masy' in c['name'] or 'masa startowa' in c['name'] for c in result['checks'])
    assert result['suggested_category'] == category
    assert result['n_warnings'] >= 1


def test_every_compliance_check_cites_its_paragraph_or_program_assumption():
    p = {'category': 'jar23_normal', 'aircraft_type': 'jet_business', 'n_crew': 1, 'n_pax': 5, 'cruise_speed_kmh': 680}
    result = check_compliance(p, {'m0': 6000})
    mtom = next(c for c in result['checks'] if c['name'] == 'Maksymalna masa startowa MTOM')
    assert not mtom['ok'] and mtom['paragraph'] == 'JAR 23.1(a)(1)' and mtom['url'].endswith('JAR-23_Ogolne.pdf')
    assert result['suggested_category'] == 'cs25_transport'
    for check in result['checks']:
        assert check['paragraph'] or check['source'].startswith('Założenie programu'), check['name']


def test_passengers_are_not_silently_removed_to_make_project_compliant():
    # JAR-VLA 1(a): at most two seats — a third occupant stays and is reported.
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'], category='cs_vla', n_pax=2))
    assert result['params']['n_pax'] == 2
    assert result['mass']['n_pax'] == 2
    assert result['easa_compliance']['n_errors'] > 0


def test_one_engine_inoperative_climb_comes_from_the_take_off_polar_and_sizes_the_power(client):
    # JAR 25.121, second segment: two engines need 2,4% at V2 with the remaining one.
    result = client.post('/api/calculate', json=AIRCRAFT_PRESETS['regional_turboprop']).json
    check = next(c for c in result['compliance_checks'] if 'jednym silnikiem niepracującym' in c['parameter'])
    assert check['rule'] == 'jar25.121' and check['passed']
    gradient = result['performance']['oei_gradient_pct']
    assert check['actual'] == f'{gradient:.1f} %' and gradient >= 2.4


@pytest.mark.parametrize('url', ['/', '/holistic', '/projekty', '/report', '/report/project/folder_cover'] + [f'/report/project/p{i}' for i in range(1,7)])
def test_all_views_render(client, url):
    assert client.get(url).status_code == 200


@pytest.mark.parametrize('url', ['/report?params_json=bad', '/report?params_json=null', '/report?preset=missing', '/report/project/p2?params_json=[]'])
def test_invalid_report_never_silently_replaces_project_with_default(client, url):
    assert client.get(url).status_code == 400


def test_material_paths_are_independent_of_working_directory(client, monkeypatch, tmp_path):
    assert os.path.isabs(client.application.config['MATERIALS_DIR'])
    materials = tmp_path / 'materials'
    (materials / 'bipol').mkdir(parents=True)
    (materials / 'bipol' / 'BIPOL_1.pdf').write_bytes(b'%PDF-1.4 local copy')
    monkeypatch.setitem(client.application.config, 'MATERIALS_DIR', str(materials))
    monkeypatch.chdir(tmp_path)
    response = client.get('/api/scraped-files')
    assert response.json['total_count'] == 1
    doc = response.json['bipol'][0]
    assert client.get(doc['path']).status_code == 200
    assert client.get('/download/scraped/unknown/BIPOL_1.pdf').status_code == 404
    assert client.get('/report/project/unknown').status_code == 404


def test_materials_link_to_sources_without_local_copies(client, monkeypatch, tmp_path):
    monkeypatch.setitem(client.application.config, 'MATERIALS_DIR', str(tmp_path / 'missing'))
    response = client.get('/api/scraped-files').json
    assert response['total_count'] == 0
    assert all(s['url'].startswith('https://') for s in response['sources'])
    assert client.get('/download/scraped/bipol/BIPOL_1.pdf').status_code == 404
