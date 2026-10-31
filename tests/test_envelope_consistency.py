"""Independent CS-22 gust cases and outer-envelope geometry at key speeds."""
import math

import pytest

from app import app
from calculations import run_bipol_project
from calculations.atmosphere import G0, RHO0
from calculations.calc_sheet import build_sheet
from calculations.envelope import calculate_vn_envelope
from calculations.presets import AIRCRAFT_PRESETS


@pytest.mark.parametrize('model', ['amendment3','pratt'])
def test_cs22_gust_coefficients_and_asymmetric_caps_follow_the_selected_formula(model):
    mass, area, chord, slope = 500, 20, 1, 6
    geom={'wing':dict(S=area,b=20,mac=chord,AR=20)}
    aero=dict(cz_max_clean=.5,cz_max_lnd=1,cz_min_clean=-.8,a_w_rad=slope,cx0_clean=.005)
    perf={'speeds':dict(vs_clean_kmh=1,v_cruise_kmh=140,v_max_sl_kmh=0)}
    env=calculate_vn_envelope(mass,geom,aero,perf,dict(category='cs22_glider',engine_type='none',cs22_gust_model=model))
    mu=2*(mass/area)/(RHO0*chord*slope)
    reduced=mu/(12.17+.191*mu)
    expected_k=.96*reduced/(.475+reduced) if model=='amendment3' else .88*mu/(5.3+mu)
    assert env['gust_factors']['k_g']==pytest.approx(expected_k,rel=1e-12)
    vs=math.sqrt(2*mass*G0/(RHO0*area*.5))
    assert env['terms']['vs_clean_ms']==pytest.approx(vs,rel=1e-12)  # ignores rounded/wrong display speed
    for gust in env['gust_factors']['gusts']:
        speed=env['terms']['v_b_ms'] if gust['speed']=='VB' else env['terms']['v_d_ms']
        dn=.5*RHO0*speed*slope*expected_k*gust['u_ms']/(mass*G0/area)
        cap=1.25*(speed/vs)**2
        assert gust['n_positive']==pytest.approx(min(1+dn,cap),rel=1e-12)
        assert gust['n_negative']==pytest.approx(max(1-dn,-cap),rel=1e-12)
    vb=env['gust_factors']['gusts'][0]
    assert vb['delta_n_neg'] > vb['delta_n']  # positive cap must not erase a larger negative increment


@pytest.fixture(scope='module',params=list(AIRCRAFT_PRESETS))
def result(request):
    return run_bipol_project(AIRCRAFT_PRESETS[request.param])


def test_composite_contains_gust_and_manoeuvre_cases_at_dive_speed(result):
    env=result['envelope']
    half=len(env['composite_polygon'])//2
    upper,lower=env['composite_polygon'][:half],list(reversed(env['composite_polygon'][half:]))
    vd=env['speeds']['v_d_kmh']
    assert upper[-1]['v_kmh']==lower[-1]['v_kmh']==vd
    gust=next(g for g in env['gust_factors']['gusts'] if g['speed']=='VD')
    expected_upper=max(env['limits']['n_at_vd_pos'],gust['n_positive'])
    expected_lower=min(env['limits']['n_at_vd_neg'],gust['n_negative'])
    assert upper[-1]['n']==pytest.approx(expected_upper,abs=.006)
    assert lower[-1]['n']==pytest.approx(expected_lower,abs=.006)
    assert max(p['n'] for p in upper) <= env['limits']['n_dimensioning_pos']+.006
    assert min(p['n'] for p in lower) >= env['limits']['n_dimensioning_neg']-.006
    assert max(p['n'] for p in upper)==pytest.approx(env['limits']['n_dimensioning_pos'],abs=.006)
    assert min(p['n'] for p in lower)==pytest.approx(env['limits']['n_dimensioning_neg'],abs=.006)
    assert env['speed_basis']=='EAS'
    flap=env['flap']
    polygon=flap['maneuver_polygon']
    assert polygon[0]==polygon[-1]==dict(v_kmh=0.,n=0.)
    assert max(p['v_kmh'] for p in polygon)==flap['v_f_kmh']
    for point in polygon[1:18]:
        # Allow only the published 0.1 km/h and 0.01 g coordinate rounding.
        expected=(point['v_kmh']/3.6/env['terms']['vs_lnd_ms'])**2
        assert abs(point['n']-expected) < .02


@pytest.mark.parametrize('preset',['glider_pw5','motoglider_aos'])
@pytest.mark.parametrize('model',['amendment3','pratt'])
def test_both_cs22_methods_have_consistent_worked_reports(preset,model):
    result=run_bipol_project(dict(AIRCRAFT_PRESETS[preset],cs22_gust_model=model))
    sheet=build_sheet(result)
    assert not {k:(v['value'],v['computed']) for k,v in sheet.entries.items() if v['consistent'] is False}
    assert ('H_g' in sheet.entries)==(model=='amendment3')
    assert 'dn_neg_B' in sheet.entries and 'dn_neg_D' in sheet.entries


def test_api_rejects_unknown_gust_model():
    assert app.test_client().post('/api/calculate',json={**AIRCRAFT_PRESETS['glider_pw5'],
                                                       'cs22_gust_model':'unknown'}).status_code==400
