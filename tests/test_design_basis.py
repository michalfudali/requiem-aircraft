"""Independent design assumptions must stay consistent throughout P1–P6."""
import json
import pytest
from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0
from calculations.official_topics import ALL_TOPICS


@pytest.mark.parametrize('topic', [t for t in ALL_TOPICS if t['category']=='motoszybowce'], ids=lambda t:t['id'])
def test_motor_glider_topics_use_their_own_geometry_and_mass_assumptions(topic):
    r=run_bipol_project(topic['parameters'])
    w=r['geometry']['wing'];p=r['params']
    assert w['b']==topic['defaults']['span_limit']
    assert w['AR']==topic['parameters']['aspect_ratio']
    assert w['S']==pytest.approx(w['b']**2/w['AR'],abs=.006)
    assert r['sizing']['design_point']['ws']==pytest.approx(r['mass']['m0']*G0/w['S'],rel=.001)
    assert p['aircraft_type']=='motoglider'
    assert r['bipol_projects']['p1']['topic']['id']==topic['num']
    if topic['num'] in (7,8):assert w['b']>20 and w['AR']<35
    json.dumps(r,allow_nan=False)


@pytest.mark.parametrize('mode,values,dependent,expected',[
    ('span_aspect',{'wingspan_m':22,'aspect_ratio':25,'wing_area_m2':1},'wing_area_m2',19.36),
    ('span_area',{'wingspan_m':22,'wing_area_m2':20,'aspect_ratio':999},'aspect_ratio',24.2),
    ('area_aspect',{'wing_area_m2':20,'aspect_ratio':20,'wingspan_m':99},'wingspan_m',20),
    ('loading',{'wing_area_m2':100,'wingspan_m':99},'wing_area_m2',None),
])
def test_geometry_outputs_cannot_override_the_selected_independent_pair(mode,values,dependent,expected):
    r=run_bipol_project({**AIRCRAFT_PRESETS['motoglider_aos'],**values,'wing_input_mode':mode})
    state=r['constraints']['parameter_states'][dependent]
    assert state['state']=='derived'
    if expected is not None:assert r['params'][dependent]==pytest.approx(expected,abs=.006)
    else:assert r['geometry']['wing']['S']<100 and r['geometry']['wing']['b']<99
    replay=run_bipol_project(r['params'])
    for key in ('m0','m_empty','m_fuel'):assert replay['mass'][key]==r['mass'][key]
    assert replay['geometry']['wing']==r['geometry']['wing']


def test_payload_total_accounts_for_baggage_and_rejects_impossible_passenger_mass():
    params={**AIRCRAFT_PRESETS['ga_trainer'],'payload_input_mode':'total',
            'n_pax':3,'m_pax':80,'m_bag':20,'m_payload':360,'m_cargo':-999}
    r=run_bipol_project(params)
    assert r['mass']['m_payload']==360
    assert r['params']['m_cargo']==60
    assert r['constraints']['parameter_states']['m_cargo']['state']=='derived'
    with app.test_client() as c:
        response=c.post('/api/calculate',json={**params,'m_payload':250})
    assert response.status_code==400
    assert 'mniejsza od masy pasażerów' in response.json['message']


def test_payload_from_seats_ignores_cached_total_and_restores_cargo_as_input():
    r=run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'],'payload_input_mode':'seats',
                        'n_pax':2,'m_pax':80,'m_bag':10,'m_cargo':25,'m_payload':10000})
    assert r['mass']['m_payload']==205
    states=r['constraints']['parameter_states']
    assert states['m_payload']['state']=='derived'
    assert states['m_cargo']['state']=='input'


def test_engine_free_aircraft_has_no_location_fuel_or_power_input():
    r=run_bipol_project({**AIRCRAFT_PRESETS['glider_pw5'],'engine_location':'rear',
                        'sfc':265,'engine_power_kw':100,'takeoff_run_m':200,'climb_rate_ms':4})
    assert r['params']['engine_location']=='none'
    assert r['mass']['m_fuel']==0
    for key in ('sfc','engine_power_kw','takeoff_run_m','climb_rate_ms'):
        assert r['params'][key]==0
        assert r['constraints']['parameter_states'][key]['state']=='derived'


def test_known_engine_power_is_used_for_performance_instead_of_automatic_sizing():
    params={**AIRCRAFT_PRESETS['pzl_kos'],'power_input_mode':'fixed','engine_power_kw':40}
    low=run_bipol_project(params)
    high=run_bipol_project({**params,'engine_power_kw':100})
    assert low['sizing']['design_point']['power_kw']==40
    assert high['sizing']['design_point']['power_kw']==100
    assert low['performance']['climb']['wy_max_ms']<high['performance']['climb']['wy_max_ms']
    assert low['constraints']['parameter_states']['engine_power_kw']['state']=='locked'


@pytest.mark.parametrize('topic_num', [1, 7, 32])
def test_coupled_project_replay_does_not_turn_sized_power_into_an_engine_assumption(topic_num):
    topic = next(t for t in ALL_TOPICS if t['num'] == topic_num)
    original = run_bipol_project(topic['parameters'])
    assert original['params']['power_input_mode'] == 'sized'
    assert original['params']['engine_power_kw'] > 0
    assert original['design_iteration']['converged']
    # Same serialization as the JSON backup / saved variant / report request.
    params = json.loads(json.dumps(original['params']))
    replay = run_bipol_project(params)
    assert params['engine_power_kw'] == original['params']['engine_power_kw']
    for key in ('m0', 'm_empty', 'm_fuel'):
        assert replay['mass'][key] == original['mass'][key]
    assert replay['mass']['breakdown'] == original['mass']['breakdown']
    assert replay['geometry'] == original['geometry']
    assert replay['aerodynamics']['cx0_clean'] == original['aerodynamics']['cx0_clean']
    assert replay['balance']['cg_range'] == original['balance']['cg_range']


@pytest.mark.parametrize('planform,expected',[('rectangular',1),('elliptical',0)])
def test_taper_is_an_output_for_fixed_planform_shapes(planform,expected):
    r=run_bipol_project({**AIRCRAFT_PRESETS['pzl_kos'],'wing_planform':planform,'taper_ratio':.6})
    assert r['params']['taper_ratio']==expected
    assert r['geometry']['wing']['eta']==expected
    assert r['constraints']['parameter_states']['taper_ratio']['state']=='derived'


def test_three_geometry_inputs_cannot_be_pinned_without_selecting_an_independent_pair():
    with pytest.raises(ValueError,match='dwa niezależne'):
        run_bipol_project({**AIRCRAFT_PRESETS['pzl_kos'],'wingspan_m':15,'wing_area_m2':10,
                          'locked_params':['wingspan_m','wing_area_m2','aspect_ratio']})


def test_official_open_span_topic_keeps_strict_greater_than_20_requirement():
    topic=next(t for t in ALL_TOPICS if t['num']==7)
    with pytest.raises(ValueError,match='większej niż 20'):
        run_bipol_project({**topic['parameters'],'wingspan_m':20})
    result=run_bipol_project({**topic['parameters'],'wingspan_m':20.001})
    assert result['params']['wingspan_m']==20.001


def test_dependent_values_are_not_reported_as_user_locks():
    r=run_bipol_project({**AIRCRAFT_PRESETS['pzl_kos'],'wing_input_mode':'loading',
                        'locked_params':['wing_area_m2','wingspan_m']})
    assert 'wing_area_m2' not in r['params']['locked_params']
    assert 'wingspan_m' not in r['constraints']['locked_keys']
