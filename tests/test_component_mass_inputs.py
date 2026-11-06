"""Class-II inputs use the actual design, not lookalike keys or surrogate dimensions."""
from copy import deepcopy
import math

import pytest

from calculations import run_bipol_project
from calculations.mass import estimate_component_masses
from calculations.presets import AIRCRAFT_PRESETS


def geometry():
    return dict(wing=dict(S=16,b=math.sqrt(128),AR=8,eta=.6,tc_ratio=.12,sweep_deg=10),
        fuselage=dict(length=7.2,diameter=1.1,S_wet=19),
        horizontal_tail=dict(S_h=2.5,AR_h=4,l_h=3.8),vertical_tail=dict(S_v=1.4,AR_v=1.5))


def parameters():
    return dict(aircraft_type='piston_ga',engine_type='prop',engine_power_kw=90,n_engines=1,
                cruise_speed_kmh=200,cruise_altitude_m=2000,m_fuel=60,n_pax=1,n_crew=1)


def test_canonical_project_geometry_has_same_meaning_as_legacy_formula_inputs():
    current=geometry();legacy=deepcopy(current)
    wing=legacy['wing']
    wing['thickness_ratio']=wing.pop('tc_ratio')
    wing['sweep_25']=math.radians(wing.pop('sweep_deg'))
    wing['taper_ratio']=wing.pop('eta')
    legacy['horizontal_tail']['arm']=legacy['horizontal_tail'].pop('l_h')
    a=estimate_component_masses(900,parameters(),current,{'n_ult':5.7})
    b=estimate_component_masses(900,parameters(),legacy,{'n_ult':5.7})
    assert a['breakdown']==pytest.approx(b['breakdown'])
    assert a['inputs']['tc_ratio']==.12
    assert a['inputs']['horizontal_tail_arm_m']==3.8


def test_actual_geometry_overrides_stale_input_thickness_and_has_correct_sensitivity():
    p=dict(parameters(),tc_ratio=.3)
    thin=geometry();thin['wing']['tc_ratio']=.1
    thick=geometry();thick['wing']['tc_ratio']=.2
    a=estimate_component_masses(900,p,thin,{'n_ult':5.7})
    b=estimate_component_masses(900,p,thick,{'n_ult':5.7})
    assert a['breakdown']['wing']/b['breakdown']['wing']==pytest.approx(2**.3)
    assert a['inputs']['tc_ratio']==.1


def test_full_envelope_ultimate_limits_take_priority_and_keep_the_safety_factor_once():
    low=estimate_component_masses(900,parameters(),geometry(),{'n_ult':5.7})
    high=estimate_component_masses(900,parameters(),geometry(),
        {'limits':{'n_ult_pos':9,'n_ult_neg':-12,'safety_factor_nu':1.5}})
    assert high['inputs']['ultimate_load_factor']==12
    assert high['inputs']['ultimate_load_basis']=='final_envelope_limits'
    assert high['breakdown']['wing']/low['breakdown']['wing']==pytest.approx((12/5.7)**.49)


@pytest.mark.parametrize('preset',['ga_trainer','motoglider_aos','glider_pw5','regional_turboprop','vlj_jet','uav_tactical'])
def test_every_main_aircraft_class_refines_mass_distribution_with_its_actual_design(preset):
    r=run_bipol_project(AIRCRAFT_PRESETS[preset])
    mass=r['mass'];used=mass['component_masses']['inputs'];wing=r['geometry']['wing']
    assert used['tc_ratio']==wing['tc_ratio']
    assert used['sweep_quarter_rad']==pytest.approx(math.radians(wing['sweep_deg']))
    assert used['fuselage_length_m']==r['geometry']['fuselage']['length']
    assert used['horizontal_tail_arm_m']==r['geometry']['horizontal_tail']['l_h']
    assert used['mission_fuel_mass_kg']==mass['m_fuel']
    limits=r['envelope']['limits']
    assert used['ultimate_load_factor']==pytest.approx(max(abs(limits['n_ult_pos']),abs(limits['n_ult_neg'])))
    if r['params']['engine_type']=='prop':
        assert used['engine_total_power_kw']==r['sizing']['design_point']['power_kw']>0
    factor=mass['component_allocation']['normalization_factor']
    assert mass['breakdown']['m_wing']==pytest.approx(factor*mass['parametric_breakdown']['wing'])
    assert sum(mass['breakdown'].values())==pytest.approx(mass['m_empty'],abs=1e-10)
    rows=r['bipol_projects']['p3']['component_mass_estimation']['rows']
    assert sum(v['assigned_mass_kg'] for v in rows)==pytest.approx(mass['m_empty'],abs=1e-10)


def test_report_component_table_keeps_real_tail_and_equipment_proportions(client):
    r=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    p3=r['bipol_projects']['p3'];factor=r['mass']['component_allocation']['normalization_factor']
    table=p3['table_3_1_components']
    ht=next(row for row in table if 'Usterzenie poziome' in row['item'])
    assert ht['mass_kg']==pytest.approx(factor*r['mass']['parametric_breakdown']['horizontal_tail'])
    response=client.post('/report/project/p3',json=r['params'])
    assert response.status_code==200
    assert 'tab-component-estimates' in response.get_data(as_text=True)


def test_adopted_mass_prior_keeps_the_actual_empirical_exponent_and_open_review():
    r=run_bipol_project(AIRCRAFT_PRESETS['motoglider_aos'])
    law=r['mass']['empty_mass_law']
    assert law['constrained']
    assert law['raw_exponent']>=-.001
    assert law['C']<0
    assert law['exponent_basis']=='declared_class_prior'
    check=next(c for c in r['engineering_audit']['checks'] if c['id']=='empty_mass_empirical_support')
    assert not check['passed']
