"""One documented propeller choice reaches P4/P5, kinematics and noise screening."""
import math

import pytest

from calculations import run_bipol_project
from calculations.acoustics import estimate_aircraft_noise
from calculations.atmosphere import isa_atmosphere
from calculations.empennage import calculate_propulsion_clearance
from calculations.official_topics import ALL_TOPICS
from calculations.propeller import helical_tip_mach


@pytest.mark.parametrize('rpm,diameter',[(2100,1.7),(2850,2.05)])
def test_topic7_uses_the_selected_propeller_in_all_calculations(rpm,diameter):
    p=dict(next(t['parameters'] for t in ALL_TOPICS if t['num']==7),
           propeller_rpm=rpm,propeller_diameter_m=diameter,
           engine_fuel_mode='catalog',engine_model_id='rotax_912_ul',engine_fuel_point='continuous')
    r=run_bipol_project(p)
    selected=r['bipol_projects']['p4']['paturski_propulsion']['propeller_selection']
    assert selected['diameter_m']==diameter
    assert selected['rpm_prop']==rpm
    assert selected['diameter_basis']=='input'
    assert r['geometry']['propeller']['diameter_m']==diameter
    noise=r['acoustics']
    v=r['performance']['climb']['v_wy_max_kmh']/3.6
    expected=math.hypot(math.pi*diameter*rpm/60,v)/isa_atmosphere(0)['a']
    assert noise['propeller_tip_mach']==pytest.approx(expected,abs=.0005)
    assert noise['propeller_diameter_m']==diameter
    assert noise['propeller_rpm']==rpm
    assert r['params']['sfc']==285  # Producer's actual maximum-continuous point, not a fitted assumption.
    assert r['engine_selection']['model']=='Rotax 912 UL'
    assert noise['certification_compliant'] is None


def test_automatic_noise_geometry_is_p4_geometry_instead_of_a_second_default():
    r=run_bipol_project(next(t['parameters'] for t in ALL_TOPICS if t['num']==7))
    selected=r['bipol_projects']['p4']['paturski_propulsion']['propeller_selection']
    assert r['acoustics']['propeller_diameter_m']==selected['diameter_unrounded_m']
    assert r['geometry']['propeller']['basis']=='preliminary_sizing'


@pytest.mark.parametrize('layout,clearance', [('tricycle', .23), ('tailwheel', .18)])
@pytest.mark.parametrize('declared_height', [0, 2.5])
def test_published_ground_plane_uses_the_final_automatic_propeller(layout, clearance, declared_height):
    import json
    from pathlib import Path
    p = json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_source_engine.json').read_text(encoding='utf8'))
    p.pop('propeller_diameter_m', None)
    p.update(landing_gear_type=layout, gear_height_m=declared_height)
    r = run_bipol_project(p)
    diameter = r['bipol_projects']['p4']['paturski_propulsion']['propeller_selection']['diameter_unrounded_m']
    expected = max(.8*r['geometry']['fuselage']['diameter'], diameter/2+clearance, declared_height)
    assert r['geometry']['gear']['axis_height_m'] == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize('params',[{'propeller_rpm':0},{'propeller_rpm':6001},
    {'propeller_rpm':'fast'},{'propeller_diameter_m':0},{'propeller_diameter_m':8.1},
    {'propeller_rpm':2100,'prop_rpm':2400}])
def test_invalid_propeller_inputs_fail_before_any_design_calculation(client,params):
    response=client.post('/api/calculate',json=params)
    assert response.status_code==400,response.json


def test_legacy_rpm_has_the_same_meaning_and_is_normalized(client):
    response=client.post('/api/calculate',json={'prop_rpm':2100})
    assert response.status_code==200,response.json
    assert response.json['params']['propeller_rpm']==2100
    assert 'prop_rpm' not in response.json['params']
    assert response.json['acoustics']['propeller_rpm']==2100
    clearance=calculate_propulsion_clearance(dict(power_kw=58,propeller_rpm=2100,
        propeller_diameter_m=1.8,cruise_speed_ms=50,altitude_m=0))
    expected=math.hypot(math.pi*1.8*2100/60,50)/isa_atmosphere(0)['a']
    assert clearance['tip_mach']==pytest.approx(expected,abs=.0005)


def test_tip_speed_includes_translation_and_high_noise_is_not_guaranteed_quiet():
    assert helical_tip_mach(2,1800,150,300)==pytest.approx(math.hypot(60*math.pi,150)/300)
    noise=estimate_aircraft_noise(
        dict(engine_type='prop',propeller_diameter_m=1,propeller_rpm=1800),
        dict(design_point={'power_kw':500}),dict(climb={'wy_max_ms':2,'v_wy_max_kmh':108}),
        {},{'m0':500})
    assert noise['propeller_tip_mach']<.72
    assert not noise['estimate_within_limit']
    assert 'przekracza' in noise['didactic_advice']
    assert 'gwarantuje cichą pracę' not in noise['didactic_advice']
    assert noise['assessment_scope']=='preliminary_comparison'
    assert noise['certification_compliant'] is None
