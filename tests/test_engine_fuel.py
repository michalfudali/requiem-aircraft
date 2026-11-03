"""Fuel must trace to an actual engine, with independently checked physical units."""
from copy import deepcopy

import pytest

from calculations import run_bipol_project
from calculations.engine_fuel import catalog, normalized_sfc, fuel_check
from calculations.validation import validate_parameters


def proposal(**changes):
    return dict(engine_fuel_mode='catalog', engine_model_id='rotax_912_ul',
                engine_fuel_point='cruise75', **changes)


def test_rotax_flow_at_75_percent_continuous_not_75_percent_takeoff():
    p = validate_parameters(proposal())
    assert p['sfc'] == pytest.approx(16.2 * .72 * 1000 / (.75 * 58))
    assert p['engine_power_kw'] == 58
    assert p['_engine_fuel']['point']['power_kw'] == 43.5
    assert '5.2' in p['_engine_fuel']['locator']
    assert p['power_input_mode'] == 'fixed'


@pytest.mark.parametrize('count', [1, 2, 4, 8])
def test_specific_consumption_does_not_multiply_by_number_of_engines(count):
    p = validate_parameters(proposal(n_engines=count, engine_power_kw=999, sfc=999))
    assert p['sfc'] == pytest.approx(268.13793103448273)
    assert p['engine_power_kw'] == 58 * count


def test_lycoming_uses_us_gallons_and_mechanical_horsepower():
    p = validate_parameters(dict(proposal(), engine_model_id='lycoming_o360_a1a'))
    # 135 HP and 10.5 US gal/h, Lycoming 60297-12 page 3-12.
    expected = 10.5 * 3.785411784 * .72 * 1000 / (135 * .7456998715822702)
    assert p['sfc'] == pytest.approx(expected)
    assert p['engine_power_kw'] == pytest.approx(180 * .7456998715822702)


def test_jet_mass_tsfc_is_converted_to_weight_specific_convention_once():
    p = validate_parameters(dict(proposal(engine_type='jet', n_engines=2),
                                 engine_model_id='pbs_tj100', engine_fuel_point='catalog'))
    assert p['sfc'] == pytest.approx(.118 * 9.80665)
    assert p['engine_static_thrust_kn'] == 2.2
    replay = validate_parameters(p)
    assert replay['sfc'] == p['sfc']
    assert replay['engine_static_thrust_kn'] == p['engine_static_thrust_kn']


def test_pbs_does_not_invent_a_power_or_altitude_for_the_sfc_point():
    engine = next(r for r in catalog() if r['id'] == 'pbs_tp100')
    assert engine['rating_basis'] == 'maximum'
    assert 'power_kw' not in engine['points'][0]
    assert normalized_sfc(engine['points'][0]) == 548


def test_density_is_an_explicit_assumption_only_for_volume_flow():
    one = validate_parameters(proposal(fuel_density_kg_l=.72))
    two = validate_parameters(proposal(fuel_density_kg_l=.74))
    assert two['sfc'] / one['sfc'] == pytest.approx(.74 / .72)
    direct = validate_parameters(dict(proposal(), engine_fuel_point='continuous', fuel_density_kg_l=.74))
    assert direct['sfc'] == 285


@pytest.mark.parametrize('point', [dict(value=1, unit='l/h', power_kw=0),
                                  dict(value=float('nan'), unit='g/(kW h)'),
                                  dict(value=1, unit='UK gal/h', power_kw=100)])
def test_incomplete_or_ambiguous_flow_data_are_rejected(point):
    with pytest.raises(ValueError):
        normalized_sfc(point)


@pytest.mark.parametrize('changes', [dict(engine_model_id='invented'), dict(engine_type='jet'),
                                     dict(engine_fuel_point='not_a_point')])
def test_catalog_must_match_real_model_and_operating_point(changes):
    with pytest.raises(ValueError):
        validate_parameters(dict(proposal(), **changes))


def custom():
    return dict(engine_fuel_mode='custom', engine_custom_model='Rotax 912 UL',
                engine_custom_power_kw=58, sfc=285,
                engine_fuel_source='BRP-Rotax OM-912 Ed.4 Rev.1, §5.2 page 5-8',
                engine_fuel_conditions='Maximum continuous 58 kW, 5500 rpm, ISA')


@pytest.mark.parametrize('key', ['engine_custom_model', 'engine_custom_power_kw',
                               'engine_fuel_source', 'engine_fuel_conditions', 'sfc'])
def test_custom_engine_requires_rating_consumption_document_and_conditions(key):
    data = custom()
    del data[key]
    with pytest.raises(ValueError):
        validate_parameters(data)


def test_custom_engine_is_attributed_to_the_author_not_independently_verified():
    p = validate_parameters(custom())
    assert p['_engine_fuel']['status'] == 'author_source'
    assert p['engine_power_kw'] == 58
    assert p['sfc'] == 285


def test_maximum_task_needs_its_own_source_and_conditions():
    data = dict(custom(), max_power_time_min=5, max_power_kw=59.6, max_power_sfc=290)
    p = validate_parameters(data)
    assert not fuel_check(p['_engine_fuel'])['passed']
    p = validate_parameters(dict(data, engine_max_fuel_source='OM-912 §5.2 page 5-8',
                                 engine_max_fuel_conditions='59.6 kW, 5800 rpm, takeoff, 5 min'))
    assert fuel_check(p['_engine_fuel'])['passed']
    assert p['_engine_fuel']['maximum_point']['value'] == 290


def test_catalog_maximum_task_cannot_exceed_installed_jet_thrust():
    data = dict(proposal(), engine_type='jet', engine_model_id='pbs_tj100', engine_fuel_point='catalog',
                max_power_time_min=5, max_thrust_kn=3, max_power_sfc=1.16, n_engines=2)
    with pytest.raises(ValueError, match='Ciąg zadania przekracza'):
        validate_parameters(data)


def test_cached_source_cannot_authenticate_arbitrary_sfc():
    p = validate_parameters(dict(sfc=300, _engine_fuel=dict(supported=True, model='Fake'),
                                 engine_static_thrust_kn=1000))
    assert p['_engine_fuel']['status'] == 'missing'
    assert not fuel_check(p['_engine_fuel'])['passed']
    assert p['sfc'] == 300
    assert 'engine_static_thrust_kn' not in p


def test_rotax_takeoff_limit_is_not_continuous_rating():
    data = proposal(max_power_time_min=5, max_power_kw=59.6)
    p = validate_parameters(data)
    assert p['max_power_sfc'] == pytest.approx(24 * .72 * 1000 / 59.6)
    assert p['engine_power_kw'] == 58
    with pytest.raises(ValueError, match='5 minut'):
        validate_parameters(dict(data, max_power_time_min=6))
    with pytest.raises(ValueError, match='przekracza'):
        validate_parameters(dict(data, max_power_kw=60))


def test_rotax_continuous_task_uses_continuous_sfc_and_allows_more_than_5_minutes():
    p = validate_parameters(proposal(max_power_time_min=15, max_power_kw=58))
    assert p['max_power_sfc'] == 285
    assert p['_engine_fuel']['maximum_point']['id'] == 'continuous'


def test_each_proposal_is_sourced_and_cannot_mutate_the_catalog(client):
    rows = client.get('/api/engines').get_json()['engines']
    assert len(rows) == 7
    for row in rows:
        assert row['source_url'].startswith('https://')
        assert row['source_title'] and row['source_locator'] and row['checked_on']
        assert row['points']
        assert all(point['conditions'] for point in row['points'])
    before = catalog()
    rows[0]['points'][0]['value'] = 1
    assert catalog() == before


def test_source_selection_reaches_mass_performance_graph_and_report(client):
    from calculations.calc_sheet import build_sheet
    presets = client.get('/api/presets').get_json()
    params = dict(presets['motoglider_aos'], **proposal())
    original = deepcopy(params)
    result = run_bipol_project(params)
    other = run_bipol_project(dict(params, engine_fuel_point='continuous'))
    assert params == original
    assert result['params']['sfc'] == pytest.approx(268.13793103448273)
    assert result['mass']['m_fuel'] != other['mass']['m_fuel']
    assert result['engine_selection']['installed_total'] == 58
    assert result['constraints']['parameter_states']['sfc']['state'] == 'derived'
    replay = run_bipol_project(result['params'])
    assert replay['params']['sfc'] == result['params']['sfc']
    assert replay['mass']['m0'] == pytest.approx(result['mass']['m0'], rel=1e-8)
    sheet = build_sheet(result)
    assert not [row for row in sheet.entries.values() if row.get('consistent') is False]
    assert 'engine_flow_ref' in sheet.entries
    assert 'engine_power_ref' in sheet.entries
    assert sheet.entries['SFC']['kind'] == 'calc'
    assert set(sheet.entries['SFC']['deps']) >= {'engine_flow_ref', 'engine_power_ref', 'fuel_density'}
    for part in ('p2', 'p4', 'p5'):
        response = client.post('/report/project/' + part, json=params)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Rotax 912 UL' in html
        assert 'OM-912' in html
        assert 'tab-engine-fuel' in html
        assert 'pełnej mapy silnika' in html


def test_real_jet_is_not_magically_upsized_to_matching_chart_or_takeoff_requirement(client):
    from calculations.calc_sheet import build_sheet
    presets = client.get('/api/presets').get_json()
    params = dict(presets['vlj_jet'], engine_fuel_mode='catalog', engine_model_id='pbs_tj100',
                  engine_fuel_point='catalog', locked_params=['engine_power_kw'], power_input_mode='fixed')
    result = run_bipol_project(params)
    dp = result['sizing']['design_point']
    assert dp['thrust_kn'] == 2.2
    assert dp['required_thrust_kn'] > dp['thrust_kn']
    assert not result['engine_selection']['adequate']
    assert result['engine_selection']['supported']
    assert result['params']['sfc'] == pytest.approx(.118 * 9.80665)
    sheet = build_sheet(result)
    assert not [e for e in sheet.entries.values() if e['consistent'] is False]
    assert 'engine_rating_ref' in sheet.entries['TW']['deps']


def test_glider_does_not_need_fictional_fuel_evidence(client):
    presets = client.get('/api/presets').get_json()
    result = run_bipol_project(presets['glider_pw5'])
    assert result['engine_selection']['status'] == 'not_applicable'
    assert result['engine_selection']['candidates'] == []


def test_missing_engine_source_is_a_gap_in_the_mass_submission_not_only_a_footnote(client):
    presets = client.get('/api/presets').get_json()
    result = run_bipol_project(presets['motoglider_aos'])
    check = next(c for c in result['bipol1_review']['checks'] if c['key'] == 'engine_fuel')
    assert not check['passed']
    item = next(i for i in result['submission_review']['items'] if i['key'] == 'p2_1')
    assert item['status'] == 'blocked'
    assert any('rzeczywisty silnik' in c['label'] and not c['passed'] for c in item['checks'])
    response = client.post('/report/project/p2', json=presets['motoglider_aos'])
    assert 'Brak rzeczywistej propozycji silnika z danymi zużycia paliwa.' in response.get_data(as_text=True)


@pytest.mark.parametrize('engine_id,preset', [('rotax_912_ul', 'motoglider_aos'),
    ('rotax_912_uls', 'motoglider_aos'), ('lycoming_o360_a1a', 'ga_trainer'),
    ('lycoming_io360_a1a', 'ga_trainer'), ('hirth_4103', 'uav_tactical'),
    ('pbs_tp100', 'regional_turboprop'), ('pbs_tj100', 'vlj_jet')])
def test_each_proposal_retains_a_consistent_calculation_chain(engine_id, preset, client):
    from calculations.calc_sheet import build_sheet
    presets = client.get('/api/presets').get_json()
    result = run_bipol_project(dict(presets[preset], engine_fuel_mode='catalog', engine_model_id=engine_id))
    sheet = build_sheet(result)
    assert not {k: (e['value'], e['computed']) for k, e in sheet.entries.items() if e['consistent'] is False}
    source = next(c for c in result['bipol1_review']['checks'] if c['key'] == 'engine_fuel')
    assert source['passed']
    installed = 'TW' if result['params']['engine_type'] == 'jet' else 'P'
    assert 'engine_rating_ref' in sheet.entries[installed]['deps']
