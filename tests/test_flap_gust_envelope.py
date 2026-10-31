"""Independent landing-gust calculations, configurations and report closure."""
import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.atmosphere import G0, RHO0
from calculations.calc_sheet import build_sheet
from calculations.envelope import calculate_vn_envelope
from calculations.presets import AIRCRAFT_PRESETS


def example(category='cs22_glider', model='amendment3', cz=.5):
    geom={'wing':dict(S=20.,b=20.,mac=2.,AR=20.)}  # deliberately different MAC and S/b
    aero=dict(cz_max_clean=cz,cz_max_lnd=cz*2,cz_min_clean=-.8,a_w_rad=6.,cx0_clean=.005)
    perf={'speeds':dict(vs_clean_kmh=1.,v_cruise_kmh=140.,v_max_sl_kmh=0.)}
    params=dict(category=category,engine_type='none',cs22_gust_model=model,flap_type='plain')
    return calculate_vn_envelope(500.,geom,aero,perf,params)


@pytest.mark.parametrize('category,model,man,u', [
    ('cs22_glider','amendment3',4.,7.5),('cs22_glider','pratt',4.,7.5),
    ('cs23_level1','amendment3',2.,7.62),('cs25_transport','amendment3',2.,7.62)])
def test_flap_gust_has_independent_signed_cases_and_full_precision_ultimate_loads(category,model,man,u):
    env=example(category,model)
    flap=env['flap']
    mu=2*(500/20)/(RHO0*1.*6.)
    reduced=mu/(12.17+.191*mu)
    k=.96*reduced/(.475+reduced) if category=='cs22_glider' and model=='amendment3' else .88*mu/(5.3+mu)
    assert env['gust_factors']['chord_m']==1.
    assert env['gust_factors']['mu_g']==pytest.approx(mu,rel=1e-12)
    assert env['gust_factors']['k_g']==pytest.approx(k,rel=1e-12)
    vs=math.sqrt(2*500*G0/(RHO0*20*1.))
    vs1=math.sqrt(2*500*G0/(RHO0*20*.5))
    vf=max(1.4*vs1,(2. if category=='cs22_glider' else 1.8)*vs)
    dn=.5*RHO0*vf*6.*k*u/(500*G0/20)
    assert flap['gust_at_vf']['delta_n']==pytest.approx(dn,rel=1e-12)
    assert flap['gust_at_vf']['n_positive']==pytest.approx(1+dn,rel=1e-12)
    assert flap['gust_at_vf']['n_negative']==pytest.approx(1-dn,rel=1e-12)
    limits=flap['limits']
    assert limits['n_dimensioning_pos']==pytest.approx(max(man,1+dn),rel=1e-12)
    assert limits['n_dimensioning_neg']==pytest.approx(min(0,1-dn),rel=1e-12)
    assert limits['n_ult_pos']==pytest.approx(1.5*max(man,1+dn),rel=1e-12)
    assert limits['n_ult_neg']==pytest.approx(1.5*min(0,1-dn),rel=1e-12)
    half=len(flap['composite_polygon'])//2
    assert flap['composite_polygon'][half-1]['n']==pytest.approx(limits['n_dimensioning_pos'],abs=.006)
    assert flap['composite_polygon'][half]['n']==pytest.approx(limits['n_dimensioning_neg'],abs=.006)
    assert max(p['v_kmh'] for p in flap['composite_polygon'])==flap['v_f_kmh']
    if category=='cs25_transport':
        assert 'analizy dynamicznej' in flap['basis']


def test_uncapped_flap_gust_can_govern_configuration_summary():
    env=example(cz=.01)
    fl=env['flap']['limits']
    combined=env['configuration_limits']
    assert fl['n_dimensioning_pos']>env['limits']['n_dimensioning_pos']
    assert fl['n_dimensioning_neg']<env['limits']['n_dimensioning_neg']
    assert combined['n_dimensioning_pos']==fl['n_dimensioning_pos']
    assert combined['n_dimensioning_neg']==fl['n_dimensioning_neg']
    assert combined['governing_positive']==combined['governing_negative']=='landing_high_lift'
    assert combined['n_ult_pos']==pytest.approx(1.5*combined['n_dimensioning_pos'],rel=1e-12)


@pytest.fixture(scope='module',params=list(AIRCRAFT_PRESETS))
def result(request):
    return run_bipol_project(AIRCRAFT_PRESETS[request.param])


def test_all_presets_close_the_flap_and_combined_worked_reports(result):
    env=result['envelope']
    fl=env['flap']['limits']
    all_=env['configuration_limits']
    assert all_['n_dimensioning_pos']==max(env['limits']['n_dimensioning_pos'],fl['n_dimensioning_pos'])
    assert all_['n_dimensioning_neg']==min(env['limits']['n_dimensioning_neg'],fl['n_dimensioning_neg'])
    sheet=build_sheet(result)
    assert not {k:(e['value'],e['computed']) for k,e in sheet.entries.items() if e['consistent'] is False}
    for key in ('dn_F','n_fg_p','n_fg_m','n_fd_p','n_fd_m','n_fu_p','n_fu_m','n_all_p','n_all_m'):
        assert key in sheet.entries


@pytest.mark.parametrize('slats,applicable',[('none',False),('fixed_slot',False),('slats_auto',True),('krueger',True)])
def test_moving_high_lift_devices_control_applicability(slats,applicable):
    r=run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'],flap_type='none',slat_type=slats))
    env=r['envelope']
    flap=env['flap']
    assert flap['applicable'] is applicable
    geometry=r['geometry']['control_surfaces']
    assert geometry['layout']=='ailerons_only'
    assert geometry['flaps']['b_f_m']==geometry['flaps']['S_flap_surface_m2']==geometry['flaps']['S_flapped_m2']==0.
    sheet=build_sheet(r)
    assert ('V_F' in sheet.entries) is applicable
    assert ('dn_F' in sheet.entries) is applicable
    assert not {k for k,e in sheet.entries.items() if e['consistent'] is False}
    if not applicable:
        assert flap['maneuver_polygon']==flap['composite_polygon']==flap['gust_pos']==flap['gust_neg']==[]
        assert flap['v_f_kmh'] is flap['n_flap'] is flap['gust_at_vf'] is flap['limits'] is None
        assert env['speeds']['v_f_kmh'] is None
        assert env['configuration_limits']['n_dimensioning_pos']==env['limits']['n_dimensioning_pos']


@pytest.mark.parametrize('preset,extra',[('glider_pw5',{}),('ga_trainer',{}),('ga_trainer',dict(flap_type='none',slat_type='none'))])
def test_p6_html_has_explicit_flap_cases_or_nonapplicability(preset,extra):
    response=app.test_client().post('/report/project/p6',json=dict(AIRCRAFT_PRESETS[preset],**extra))
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert 'p6.design_all' in html
    assert ('id="repFlapEnvelope"' in html) is not bool(extra)
    assert 'nie zostały wyznaczone dla konfiguracji klapowej' not in html
