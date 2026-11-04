"""Both starting routes produce the same parabolic polar and retain their evidence."""
import math

import pytest

from calculations import run_bipol_project
from calculations.bipol1 import preliminary_polar
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.validation import validate_parameters


@pytest.mark.parametrize('preset', ['ga_trainer', 'motoglider_aos', 'glider_pw5'])
def test_aircraft_cd0_is_not_replaced_or_incremented_twice(preset):
    params = {**AIRCRAFT_PRESETS[preset], 'preliminary_polar_mode':'input', 'cx0':.027,
              'wing_config':'braced_high', 'flap_type':'junkers', 'slat_type':'fixed_slot',
              'graph_source':'Biegunowa całego samolotu, podwozie stałe', 'design_iteration_mode':'preliminary'}
    result = run_bipol_project(params)
    polar = result['mass']['preliminary_polar']
    assert result['params']['preliminary_polar_mode'] == 'input'
    assert result['params']['preliminary_polar_includes_configuration']
    assert polar['cx0'] == result['sizing']['terms']['cx0'] == .027
    assert polar['swet_ratio'] is None
    assert polar['kmax'] == pytest.approx(.5*math.sqrt(math.pi*polar['aspect_ratio']*polar['oswald_e']/.027))
    sheet = build_sheet(result)
    assert sheet.entries['Cx0_1']['source'] == params['graph_source']
    assert all(e['consistent'] is not False for e in sheet.entries.values())
    replay = run_bipol_project(result['params'])
    assert replay['mass']['m0'] == result['mass']['m0']


def test_wetted_and_direct_routes_agree_for_the_same_polar(client):
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'preliminary_polar_mode':'raymer',
              'wetted_example':'sketch', 'sketch_swet_ratio':4.2}
    wetted = client.post('/api/preliminary-polar', json=params)
    assert wetted.status_code == 200
    polar = wetted.json['polar']
    direct = client.post('/api/preliminary-polar', json={**params, 'preliminary_polar_mode':'input', 'cx0':polar['cx0']})
    assert direct.status_code == 200
    assert direct.json['polar']['kmax'] == pytest.approx(polar['kmax'])
    assert direct.json['polar']['swet_ratio'] is None
    assert polar['swet_ratio'] == 4.2


@pytest.mark.parametrize('value', [0, -.1, .301, 'NaN', 'Infinity', None])
def test_invalid_cd0_is_rejected_without_saving(client, value):
    response = client.post('/api/preliminary-polar', json={'preliminary_polar_mode':'input', 'cx0':value})
    assert response.status_code == 400
    assert response.json['message']


@pytest.mark.parametrize('body', [[], 'abc', None])
def test_preview_rejects_non_object_payload(client, body):
    assert client.post('/api/preliminary-polar', json=body).status_code == 400


def test_manual_raymer_reading_uses_given_kmax():
    params = validate_parameters({**AIRCRAFT_PRESETS['ga_trainer'], 'preliminary_polar_mode':'reading',
                                  'wetted_example':'sketch', 'sketch_swet_ratio':4.2, 'raymer_kmax':17})
    polar = preliminary_polar(params)
    assert polar['kmax'] == 17
    assert polar['cx0'] == pytest.approx(math.pi*params['aspect_ratio']*params['oswald_e']/(4*17**2))
