"""Known hardware cannot shrink to make the preliminary empty-mass budget close."""
from copy import deepcopy
import json

import pytest

from calculations import run_bipol_project,aircraft_store
from calculations.engine_mass import validate_hardware
from calculations.engine_fuel import catalog
from calculations.presets import AIRCRAFT_PRESETS
from calculations.validation import validate_parameters
from tools.import_engine_hardware import MANIFEST,apply_manifest


def proposal(**changes):
    return dict(AIRCRAFT_PRESETS['motoglider_aos'],engine_fuel_mode='catalog',
                engine_model_id='rotax_912_ul',engine_fuel_point='continuous',**changes)


def installation(**changes):
    return proposal(engine_installed_mass_kg=95,
        engine_mass_source='Próbne zestawienie mas instalacji do testu regresyjnego',
        engine_mass_conditions='Silnik, przekładnia, śmigło, chłodzenie z płynami, mocowanie i wydech; bez paliwa i układu paliwowego',**changes)


def test_rotax_source_mass_is_distinct_from_the_power_mass_correlation():
    r=run_bipol_project(proposal())
    observed=r['engine_selection']['mass']
    assert observed['hardware']['source_url']=='https://www.flyrotax.com/products/912-ul-a-f'
    assert observed['base_mass_each_kg']==55.4
    raw=r['mass']['component_masses']
    assert raw['engine_mass']['basis']=='manufacturer_base_mass'
    assert raw['engine_mass']['base_mass_each_kg']==pytest.approx(55.4)
    assert raw['breakdown']['propulsion']==pytest.approx(2.575*(55.4/.45359237)**.922*.45359237)
    allocated=r['mass']['component_allocation']
    assert allocated['fixed_masses_kg']['propulsion']==55.4
    assert allocated['assigned_masses_kg']['propulsion']>=55.4
    assert sum(allocated['assigned_masses_kg'].values())==pytest.approx(r['mass']['m_empty'],abs=1e-10)
    check=next(c for c in r['engineering_audit']['checks'] if c['id']=='engine_installation_mass')
    assert not check['passed']  # A dry-engine datum does not document the whole installation.


@pytest.mark.parametrize('count',[1,2,4,8])
def test_hardware_counts_once_per_engine_without_changing_specific_fuel_consumption(count):
    p=validate_parameters(proposal(n_engines=count))
    assert p['_engine_fuel']['mass']['fixed_mass_total_kg']==pytest.approx(55.4*count)
    assert p['sfc']==285


def test_documented_installed_assembly_is_fixed_in_raw_estimate_balance_and_report(client):
    r=run_bipol_project(installation())
    m=r['mass'];allocation=m['component_allocation']
    assert m['component_masses']['breakdown']['propulsion']==95
    assert allocation['assigned_masses_kg']['propulsion']==95
    assert r['params']['engine_mass_owner']=='catalog:rotax_912_ul'
    table=r['bipol_projects']['p3']['table_3_1_components']
    plant=next(v for v in table if 'Zabudowany zespół napędowy' in v['item'])
    assert plant['mass_kg']==95
    assert sum(m['breakdown'].values())==pytest.approx(m['m_empty'],abs=1e-10)
    replay=run_bipol_project(r['params'])
    assert replay['mass']['m0']==pytest.approx(m['m0'],rel=1e-8)
    check=next(c for c in r['engineering_audit']['checks'] if c['id']=='engine_installation_mass')
    assert check['passed']
    html=client.post('/report/project/p3',json=r['params']).get_data(as_text=True)
    assert r['params']['engine_mass_source'] in html and 'pozostaje bez skalowania' in html


@pytest.mark.parametrize('change',[dict(engine_installed_mass_kg=55.399),dict(engine_mass_source=''),
    dict(engine_mass_conditions=''),dict(engine_mass_owner='catalog:other'),
    dict(engine_installed_mass_kg=float('nan')),dict(engine_installed_mass_kg=True),dict(engine_installed_mass_kg=-1)])
def test_unsubstantiated_or_physically_impossible_installed_mass_is_rejected(change):
    with pytest.raises(ValueError):validate_parameters(dict(installation(),**change))


def test_installed_assembly_alone_cannot_exceed_p1_empty_mass(client):
    p=dict(installation(),engine_installed_mass_kg=1000)
    response=client.post('/api/calculate',json=p)
    assert response.status_code==400
    assert 'Masa pusta P1' in response.get_json()['message']


def test_cached_hardware_cannot_authenticate_forged_data_and_other_engines_have_no_invented_mass():
    p=validate_parameters(dict(proposal(),_engine_fuel={'mass':{'fixed_mass_total_kg':1}}))
    assert p['_engine_fuel']['mass']['fixed_mass_total_kg']==55.4
    other=validate_parameters(dict(proposal(),engine_model_id='rotax_912_uls'))
    assert other['_engine_fuel']['mass']['hardware'] is None


def test_atomic_import_is_idempotent_and_preserves_other_engine_fields():
    data=json.loads(MANIFEST.read_text(encoding='utf8'))
    data['records'][0]['hardware']['checked_on']='2026-11-05'
    before=aircraft_store.engines();path=aircraft_store.database_path()
    assert apply_manifest(data,path)['changed']==1
    assert apply_manifest(data,path)['changed']==0
    after=aircraft_store.engines()
    for old,new in zip(before,after):
        assert {k:v for k,v in old.items() if k!='hardware'}=={k:v for k,v in new.items() if k!='hardware'}
    invalid=deepcopy(data)
    invalid['records'][0]['hardware']['mass_kg']=56
    invalid['records'].append(dict(engine_id='nonexistent',hardware=data['records'][0]['hardware']))
    with pytest.raises(ValueError):apply_manifest(invalid,path)
    assert aircraft_store.engines()==after


@pytest.mark.parametrize('value',[0,-1,True,float('nan'),float('inf')])
def test_source_hardware_mass_must_be_positive_and_finite(value):
    record=deepcopy(next(e for e in catalog() if e['id']=='rotax_912_ul')['hardware'])
    record['mass_kg']=value
    with pytest.raises(ValueError):validate_hardware(record)
