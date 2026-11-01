"""Independent force/power/fuel balances for ML1 projects 3–6."""
import math

import pytest

from calculations.atmosphere import G0,isa_atmosphere
from calculations.ml1.aircraft import (chart_reading,fuselage_drag,component_drag_area,
                                      vertical_tail_drag,aircraft_polar,chart_surface,drag_statistics)
from calculations.ml1.glide import glide_polar,approximate_glide
from calculations.ml1.propulsion import (shaft_power,jet_thrust,variable_pitch,fixed_pitch,
    fixed_pitch_constant_torque,select_propeller,normalize_propeller,propeller_at)
from calculations.ml1.range import analytical_range,integrate_range,fuel_budget


# Synthetic test chart with known bilinear solution, not aircraft/propeller data.
MAP=dict(name='Test chart',source='Synthetic verification chart',curves=[
    dict(beta_deg=10,rows=[dict(j=j,cn=.05-.01*j,eta=.6*j) for j in (0,.5,1,1.5)]),
    dict(beta_deg=30,rows=[dict(j=j,cn=.15-.01*j,eta=.5*j) for j in (0,.5,1,1.5)])])


def test_chart_interpolation_respects_linear_and_logarithmic_axes():
    assert chart_reading([[1e6,.004],[1e8,.002]],1e7,logarithmic_x=True)==pytest.approx(.003)
    assert chart_reading([[0,1],[2,3]],1)==2
    with pytest.raises(ValueError):chart_reading([[0,1],[2,3]],3)


def test_two_dimensional_chart_reading_and_source_statistics_do_not_calibrate_inputs():
    curves=[dict(parameter=p,points=[[0,1],[1,1+p/10]]) for p in (2,4)]
    assert chart_surface(curves,.5,3)==pytest.approx(1.15)
    with pytest.raises(ValueError):chart_surface(curves,.5,5)
    check=drag_statistics(.03,.015)
    assert all(r['computed_cd_min']==.03 for r in check['table_a'])
    assert all(r['computed_cd_parasite_min']==.015 for r in check['table_b'])


def test_fuselage_reference_area_and_wetted_area_are_not_confused():
    r=fuselage_drag(10,2,2,50,1000,cf=.003,eta_shape=1.2,eta_mach=1)
    wetted=2.85*10*math.sqrt(2)
    assert r['cd']==pytest.approx(.003*1.2*wetted/2)
    assert r['drag_area_m2']==pytest.approx(.003*1.2*wetted)
    explicit=fuselage_drag(10,2,2,50,1000,cf=.003,eta_shape=1.2,eta_mach=1,wetted_area_m2=40)
    assert explicit['drag_area_m2']==pytest.approx(.144)
    assert explicit['wetted_basis']=='measured'


def test_coefficient_and_tunnel_force_formats_produce_the_same_drag_area():
    a=component_drag_area(dict(name='Gear',cd=.5,reference_area_m2=.2,source='test'))
    b=component_drag_area(dict(name='Gear',drag_n=50,dynamic_pressure_pa=500,source='test'))
    c=component_drag_area(dict(name='Gear',drag_n=50,rho_kgm3=1,velocity_ms=math.sqrt(1000),source='test'))
    assert a['drag_area_m2']==pytest.approx(b['drag_area_m2'])
    assert b['drag_area_m2']==pytest.approx(c['drag_area_m2'])
    assert vertical_tail_drag(.008,.004,2)['drag_area_m2']==pytest.approx(.024)


def test_aircraft_polar_closes_trim_and_uses_all_component_reference_areas():
    rows=[dict(cl=c,cd=.01+.04*c*c,alpha_deg=10*c) for c in (-.5,0,.5,1)]
    tail=dict(area_m2=2,arm_m=4,span_m=3,oswald_e=.8,position='t_tail',profile_cd_min=.008,gap_cd=.005)
    r=aircraft_polar(rows,10,1.5,tail,[dict(cd=.1,reference_area_m2=1,source='test')],
                     cm_ac=-.05,x_cg_mac=.3,x_ac_mac=.25,zeta=5,interference=.04)
    assert r['tail_volume_effective']==pytest.approx(2*4/(10*1.5)*.98)
    for wing,out in zip(rows,r['rows']):
        assert out['trim_moment_residual']==pytest.approx(0,abs=1e-15)
        assert out['cl']==pytest.approx(wing['cl']+.2*out['cl_tail'])
        assert out['cd']==pytest.approx((wing['cd']+.01*(1+abs(wing['cl'])/5)+.2*out['cd_tail'])*1.04)


def test_exact_glide_closes_both_force_components_including_vertical_dive():
    polar=[dict(cl=c,cd=.02+.04*c*c) for c in (0,.2,.5,1)]
    cases=[dict(mass_kg=500,altitude_m=h) for h in (0,1000,2000)]
    result=glide_polar(polar,10,cases)
    for case in result['cases']:
        for row in case['rows']:
            gamma=math.radians(row['gamma_down_deg'])
            q=.5*case['rho']*row['velocity_ms']**2
            assert q*10*row['cl']==pytest.approx(500*G0*math.cos(gamma),abs=1e-10)
            assert q*10*row['cd']==pytest.approx(500*G0*math.sin(gamma),rel=1e-12)
        assert case['rows'][0]['gamma_down_deg']==90


def test_glide_approximation_reproduces_published_characteristic_ratios():
    r=approximate_glide(.02,.04,500,10,0,cl_max=1.5)
    assert r['speed_ratio']==pytest.approx(3**.25,rel=1e-13)
    assert r['sink_ratio']==pytest.approx(3**.75/2,rel=1e-13)


def test_glide_polar_reaches_exactly_120_percent_of_reported_maximum_speed():
    rows=[dict(cl=c,cd=.02+.04*c*c) for c in (.01,.1,.3,.6,1,1.5)]
    r=glide_polar(rows,10,[dict(mass_kg=m,altitude_m=0) for m in (500,600,700)],maximum_level_speed_ms=50)
    for case in r['cases']:
        assert case['terminal_speed_covered']
        assert max(p['velocity_ms'] for p in case['rows'])==pytest.approx(60)
        assert max(abs(p['force_residual_n']) for p in case['rows'])<1e-6


def test_engine_height_models_are_exact_at_each_defined_branch_point():
    p0=100000
    unboosted=shaft_power(dict(model='piston_unboosted',power_sl_w=p0,lapse_k=.14),2000)
    expected=p0*(isa_atmosphere(2000)['rho']/isa_atmosphere(0)['rho']-.14)/.86
    assert unboosted['power_w']==pytest.approx(expected)
    e=dict(model='two_speed_supercharger',power_sl_w=100000,critical_1_m=2000,
           shift_height_m=3000,critical_2_m=4000,power_critical_1_w=110000,
           power_shift_2_w=105000,power_critical_2_w=115000)
    for h,p in [(0,100000),(1000,105000),(2000,110000),(3000,105000),(3500,110000),(4000,115000)]:
        assert shaft_power(e,h)['power_w']==pytest.approx(p)
    assert shaft_power(e,5000)['stage']=='second_unregulated'
    turbo=dict(model='turbocharged',power_sl_w=p0,critical_height_m=6000)
    assert shaft_power(turbo,6000)['power_w']==p0
    assert shaft_power(turbo,7000)['power_w']<p0
    tp=shaft_power(dict(model='turboprop',power_sl_w=p0),4000)
    assert tp['power_w']==pytest.approx(p0*(isa_atmosphere(4000)['rho']/isa_atmosphere(0)['rho'])**.6)


def test_jet_characteristics_keep_single_and_two_stream_mach_relations_distinct():
    e=dict(model='turbojet',static_thrust_n=10000)
    assert jet_thrust(e,0,0)['thrust_n']==pytest.approx(10000)
    assert jet_thrust(e,1,0)['thrust_n']==pytest.approx(11200)
    e.update(model='turbofan',kp=.5)
    assert jet_thrust(e,1,0)['thrust_n']==pytest.approx(5000)
    table=dict(model='table',altitude_slices=[
        dict(altitude_m=0,mach_thrust=[[0,10000],[1,8000]]),
        dict(altitude_m=4000,mach_thrust=[[0,6000],[1,4000]])])
    assert jet_thrust(table,.5,2000)['thrust_n']==pytest.approx(7000)


def test_variable_pitch_matching_solves_map_power_instead_of_assuming_beta_or_efficiency():
    rho=isa_atmosphere(0)['rho'];n=30;d=2;v=30
    power=.095*rho*n**3*d**5
    r=variable_pitch(MAP,v,0,power,n,d)
    assert r['j']==.5
    assert r['beta_deg']==pytest.approx(20)
    assert r['eta']==pytest.approx(.275)
    assert r['available_power_w']==pytest.approx(power*.275)
    with pytest.raises(ValueError):variable_pitch(MAP,300,0,power,n,d)


def test_propeller_selection_recovers_a_known_diameter_from_the_dimensionless_map():
    rho=isa_atmosphere(0)['rho'];n=30;d=2;v=30;power=.045*rho*n**3*d**5
    only=dict(MAP,curves=[MAP['curves'][0]])
    r=select_propeller([only],v,0,power,n,maximum_speed_ms=40,min_diameter_m=1,max_diameter_m=3)
    assert r['selected']['diameter_m']==pytest.approx(d,rel=1e-9)
    assert r['selected']['j']==pytest.approx(.5,rel=1e-9)
    assert r['diameter_free_coefficient']==pytest.approx((.5**5/.045)**.2)


def test_fixed_pitch_numerical_and_constant_torque_solutions_close_the_same_balance():
    n=30;d=2;rho=isa_atmosphere(0)['rho'];v=30
    power=.045*rho*n**3*d**5
    curve=[[900,power*.5],[2700,power*1.5]]
    exact=fixed_pitch(MAP,10,v,0,d,curve,rpm_limit=2700)
    shortcut=fixed_pitch_constant_torque(MAP,10,[0,.5,1],0,d,power*1.5,2700)['rows'][1]
    assert exact['rpm']==pytest.approx(1800,rel=1e-9)
    assert exact['balance_residual_w']==pytest.approx(0,abs=1e-4)
    assert shortcut['rpm']==pytest.approx(exact['rpm'],rel=1e-9)
    assert shortcut['available_power_w']==pytest.approx(exact['available_power_w'],rel=1e-9)
    # More engine torque than the propeller can absorb at nmax: throttle down.
    limited=fixed_pitch(MAP,10,30,0,d,[[900,4*power],[2700,12*power]],rpm_limit=1800)
    assert limited['rpm_limited'] and limited['rpm']==1800
    assert 0<limited['throttle_fraction']<1


@pytest.mark.parametrize('propulsion,sfc',[('propeller',.25),('jet',.8)])
@pytest.mark.parametrize('schedule',['constant_cl','constant_speed'])
def test_each_mass_integral_matches_its_independent_closed_form(propulsion,sfc,schedule):
    args=(1000,800,15,2000,sfc)
    kw=dict(cd0=.02,k=.045,propulsion=propulsion,schedule=schedule,cl=.6,velocity_ms=60,eta=.82)
    analytic=analytical_range(*args,**kw)
    numerical=integrate_range(*args,**kw,steps=400)
    assert numerical['time_s']==pytest.approx(analytic['time_s'],rel=1e-11)
    assert numerical['range_m']==pytest.approx(analytic['range_m'],rel=1e-11)


def test_jet_prandtl_is_recomputed_for_each_mass_and_reduces_range_and_endurance():
    kw=dict(cd0=.02,k=.045,propulsion='jet',schedule='constant_cl',cl=.3)
    base=integrate_range(6000,4000,20,8000,.8,**kw)
    corrected=integrate_range(6000,4000,20,8000,.8,**kw,prandtl=True)
    assert corrected['range_m']<base['range_m']
    assert corrected['time_s']<base['time_s']
    ratios=[]
    for row in corrected['rows']:
        ratios.append(row['cd']/row['cd_incompressible'])
        assert ratios[-1]==pytest.approx(1/math.sqrt(1-row['mach']**2),rel=1e-13)
        assert row['fuel_flow_kgs']==pytest.approx(.8*row['required_thrust_n']/(10*3600))
    assert ratios[-1]>ratios[0]
    finer=integrate_range(6000,4000,20,8000,.8,**kw,prandtl=True,steps=800)
    assert finer['range_m']==pytest.approx(corrected['range_m'],rel=1e-10)


def test_fuel_allowance_uses_engine_count_and_daN_conversion_once():
    r=fuel_budget(200,2,100,.25)
    assert r['cruise_fuel_kg']==pytest.approx(137.5)
    assert r['reserve_fuel_kg']==pytest.approx(37.5)
    j=fuel_budget(3000,2,10000,.8,propulsion='jet')
    assert j['cruise_fuel_kg']==pytest.approx(1000)
    economical=fuel_budget(200,2,100,.25,reserve_fuel_flow_kgh=20)
    assert economical['reserve_fuel_kg']==15
    assert economical['cruise_fuel_kg']==160


@pytest.mark.parametrize('case',[lambda:integrate_range(1000,1100,15,0,.25,cd0=.02,k=.04),
    lambda:integrate_range(1000,800,15,0,.25,cd0=.02,k=.04,cl=.5,steps=21),
    lambda:integrate_range(6000,4000,20,15000,.8,cd0=.02,k=.04,cl=.01,propulsion='jet',prandtl=True),
    lambda:normalize_propeller(dict(MAP,curves=[dict(beta_deg=0,rows=[dict(j=0,cn=.1,eta=.5),dict(j=1,cn=.1,eta=.5)])])),
    lambda:component_drag_area(dict(cd=.1,reference_area_m2=1))])
def test_invalid_inputs_are_rejected_without_fabricated_values(case):
    with pytest.raises(ValueError):case()
