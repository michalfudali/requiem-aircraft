"""Configuration requirements from the actual BIPOL topic wording."""
from copy import deepcopy

import pytest

from calculations.official_topics import ALL_TOPICS, check_topic_requirements


def topic(number):
    return next(t for t in ALL_TOPICS if t['num']==number)


@pytest.mark.parametrize('number',range(1,15))
def test_all_motoglider_topics_keep_their_explicit_propulsion_layout_and_seat_count(number,client):
    original=topic(number)
    exported=next(t for t in client.get('/api/topics').json['topics'] if t['num']==number)
    req=exported['requirements']
    title=original['title'].casefold()
    expected='nose' if 'ciągnący' in title else 'rear' if 'pchający' in title else 'retractable'
    assert req['engine_location']==expected
    assert req['occupants_exact']==(1 if number<=8 else 2)
    assert req['engine_location']==original['parameters']['engine_location']


@pytest.mark.parametrize('change',[{'engine_location':'rear'},{'engine_location':'retractable'},
                                    {'n_crew':2},{'n_engines':2}])
def test_topic7_cannot_claim_a_different_aircraft_configuration(change):
    params=dict(topic(7)['parameters'],**change)
    original=deepcopy(params)
    checks=check_topic_requirements(params,{'design_point':{'power_kw':20}})
    assert any(not c['passed'] for c in checks)
    assert params==original


def test_topic7_backend_reports_the_wrong_engine_location_instead_of_overwriting_it(client):
    params=dict(topic(7)['parameters'],engine_location='rear')
    response=client.post('/api/calculate',json=params)
    assert response.status_code==200,response.json
    result=response.json
    assert result['params']['engine_location']=='rear'
    check=next(c for c in result['compliance_checks'] if c['parameter'].endswith('Zabudowa zespołu napędowego'))
    assert not check['passed'] and check['required']=='w nosie kadłuba'


def test_two_crew_are_not_a_single_seat_topic_even_when_there_are_no_passengers(client):
    response=client.post('/api/calculate',json=dict(topic(7)['parameters'],n_crew=2))
    assert response.status_code==200,response.json
    check=next(c for c in response.json['compliance_checks'] if c['parameter'].endswith('Liczba osób na pokładzie'))
    assert not check['passed'] and check['actual']=='2' and check['required']=='1'
