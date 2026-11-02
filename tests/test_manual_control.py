"""Tryb sterowania ręcznego: wartości domyślne wpisuje użytkownik, etapami P1 → P6."""
import pytest

from app import app
from calculations.presets import AIRCRAFT_PRESETS


@pytest.fixture()
def client():
    with app.test_client() as test_client:
        yield test_client


def manual(preset='pzl_kos', **state):
    return {**AIRCRAFT_PRESETS[preset], 'manual_control': {'enabled': True, 'typed': [], 'accepted': {}, **state}}


def calculate(client, params):
    response = client.post('/api/calculate', json=params)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_without_manual_control_nothing_is_gated(client):
    result = calculate(client, dict(AIRCRAFT_PRESETS['pzl_kos']))
    assert 'manual_control' not in result
    assert client.get('/report?preset=pzl_kos').status_code == 200


def test_first_stage_lists_concept_defaults_with_suggestions_and_blocks_reports(client):
    params = manual()
    state = calculate(client, params)['manual_control']
    assert state['stage'] == 'p1' and state['remaining'] == state['total'] and state['accepted'] == 0
    keys = {point['key'] for point in state['pending']}
    assert {'n_pas', 'm_os', 'AR', 'e_1'} <= keys
    point = next(p for p in state['pending'] if p['key'] == 'e_1')
    assert point['suggested'] == pytest.approx(0.78) and point['origin'].startswith('Założenie początkowe')
    assert point['editable'] and point['param'] == 'oswald_e'
    assert all(p['project'] == 'p1' for p in state['pending'])
    blocked = client.post('/report?sections=p1', json=params)
    assert blocked.status_code == 409 and 'sterowania ręcznego' in blocked.get_json()['message']
    assert client.post('/report/project/p2', json=params).status_code == 409
    assert client.post('/report/parameters?keys=m0', json=params).status_code == 409


def test_accepting_every_stage_unlocks_the_report(client):
    params = manual()
    stages = []
    for _ in range(12):
        state = calculate(client, params)['manual_control']
        if not state['remaining']:
            break
        stages.append(state['stage'])
        for point in state['pending']:
            params['manual_control']['accepted'][point['key']] = point['suggested']
    assert state['remaining'] == 0 and state['accepted'] == state['total']
    assert stages == sorted(set(stages), key=lambda key: int(key[1:])) and stages[0] == 'p1'
    assert client.post('/report', json=params).status_code == 200


def test_typed_parameters_count_as_entered_by_the_user(client):
    state = calculate(client, manual(typed=['n_pax', 'n_crew', 'm_pax', 'm_crew_person']))['manual_control']
    keys = {point['key'] for point in state['pending']}
    assert not {'n_pas', 'n_zal', 'm_pas', 'm_os'} & keys


def test_entered_value_is_used_in_the_calculation(client):
    base = calculate(client, dict(AIRCRAFT_PRESETS['pzl_kos']))
    changed = calculate(client, manual(accepted={'k_rez': 1.10}))
    assert changed['mass']['mission_assumptions']['reserve_factor'] == pytest.approx(1.10)
    assert changed['mass']['m_fuel'] > base['mass']['m_fuel']
    assert not changed['manual_control']['conflicts']


def test_method_constant_cannot_be_silently_changed(client):
    params = manual(accepted={'Cz_L_2': 3.5})
    for _ in range(4):
        state = calculate(client, params)['manual_control']
        if state['stage'] == 'p2':
            break
        for point in state['pending']:
            params['manual_control']['accepted'][point['key']] = point['suggested']
    conflict = next(p for p in state['conflicts'] if p['key'] == 'Cz_L_2')
    assert 'przyjętej metody' in conflict['message'] and 'rodzaj i zasięg klap' in conflict['message']


def test_invalid_entry_is_rejected(client):
    response = client.post('/api/calculate', json=manual(accepted={'k_rez': 'dużo'}))
    assert response.status_code == 400
