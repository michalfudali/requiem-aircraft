import math

import pytest

from calculations.atmosphere import G0,isa_atmosphere
from calculations.ml1.performance import (performance_at_height,availability_model,
    linear_climb_time,climb_time_from_chart,offer_chart,method_eligibility)
from calculations.ml1.exact_climb import exact_force_equilibrium


def test_force_and_power_methods_close_the_same_balance_and_find_both_level_roots():
    thrust=1200.
    args=(1000,15,0)
    kw=dict(cl_min=.025,cl_max=1.5,cd0=.02,k=.05)
    force=performance_at_height(*args,lambda v,h:thrust,propulsion='jet',**kw)
    power=performance_at_height(*args,lambda v,h:thrust*v,propulsion='propeller',**kw)
    for a,b in zip(force['rows'],power['rows']):
        assert a['roc_ms']==pytest.approx(b['roc_ms'],rel=1e-13)
        assert a['required_power_w']==pytest.approx(a['required_thrust_n']*a['velocity_ms'])
        expected=(thrust-a['required_thrust_n'])*a['velocity_ms']/(1000*G0)
        assert a['roc_ms']==pytest.approx(expected)
        assert a['energy_function']==pytest.approx(a['cl']**1.5/a['cd'])
    # Parabolic drag: A*V² + B/V² = T -> quadratic in V².
    rho=isa_atmosphere(0)['rho'];a=.5*rho*15*.02;b=2*.05*(1000*G0)**2/(rho*15)
    roots=[math.sqrt((thrust+s*math.sqrt(thrust**2-4*a*b))/(2*a)) for s in (-1,1)]
    # CLmax imposes stall before the lower thrust-limited intersection.
    assert force['minimum_level_speed_ms']==pytest.approx(force['stall_speed_ms'])
    assert force['maximum_level_speed_ms']==pytest.approx(roots[1],rel=1e-9)
    assert force['best_rate']['velocity_ms']!=pytest.approx(force['best_gradient']['velocity_ms'],rel=.01)


def test_level_speed_is_not_fabricated_when_the_polar_domain_ends_before_the_root():
    r=performance_at_height(1000,15,0,lambda v,h:5000,
                            propulsion='jet',cl_min=.3,cl_max=1.5,cd0=.02,k=.05)
    assert r['maximum_level_speed_ms'] is None
    assert not r['maximum_speed_bracketed']
    assert r['upper_speed_domain_limit_ms']>0
    assert not r['best_rate']['within_small_angle_scope']


def test_prandtl_changes_drag_excess_and_actual_level_intersection_together():
    kw=dict(propulsion='jet',cl_min=.04,cl_max=1.5,cd0=.02,k=.05)
    base=performance_at_height(6000,20,8000,lambda v,h:16000,**kw)
    corrected=performance_at_height(6000,20,8000,lambda v,h:16000,**kw,prandtl=True)
    assert corrected['maximum_level_speed_ms']<base['maximum_level_speed_ms']
    assert corrected['best_rate']['roc_ms']<base['best_rate']['roc_ms']
    for r in corrected['rows']:
        if not r['available']:continue
        assert r['cd']==pytest.approx(r['cd_incompressible']/math.sqrt(1-r['mach']**2))


def test_graphical_and_linear_climb_methods_have_independent_exact_cases():
    assert climb_time_from_chart([[0,.1],[1000,.2],[2000,.3]],1500)==pytest.approx(262.5)
    assert linear_climb_time(5000,10000,10)==pytest.approx(1000*math.log(2))
    with pytest.raises(ValueError):linear_climb_time(10000,10000,10)


def test_availability_uses_total_engine_count_and_only_neighboring_measured_slices():
    config=dict(kind='propeller',engine_count=2,pitch='power_table',altitude_slices=[
        dict(altitude_m=0,velocity_power=[[20,100000],[100,100000]]),
        dict(altitude_m=2000,velocity_power=[[20,80000],[100,80000]]),
        dict(altitude_m=4000,velocity_power=[[40,60000],[80,60000]])])
    available=availability_model(config)
    assert available(30,1000)==pytest.approx(180000)
    with pytest.raises(ValueError):available(30,3000)


def test_offer_chart_ceiling_is_a_root_not_the_nearest_height_sample():
    # Configure total useful power so best ROC decreases linearly with h.
    # At each altitude minimum required power occurs at CL=sqrt(3*CD0/k).
    mass=1000;area=15;zero=.02;k=.05
    cl=math.sqrt(3*zero/k);cd=zero+k*cl*cl
    def power(v,h):
        rho=isa_atmosphere(h)['rho']
        min_v=math.sqrt(2*mass*G0/(rho*area*cl))
        min_required=mass*G0*cd/cl*min_v
        return min_required+mass*G0*(5-h/1000)
    result=offer_chart(mass,area,[0,2000,4000,6000],power,
                       cl_min=.05,cl_max=1.5,cd0=zero,k=k,samples=81,climb_steps=40)
    assert result['theoretical_ceiling_m']==pytest.approx(5000,abs=.001)
    assert result['practical_ceiling_m']==pytest.approx(4500,abs=.001)
    expected=1000*math.log(10)
    assert result['climb_to_practical_s']==pytest.approx(expected,rel=1e-4)
    assert result['climb_to_theoretical_s'] is None
    assert result['rows'][1]['climb_time_s']==pytest.approx(2000*(.2+1/3)/2)


def test_exact_force_equilibrium_closes_a_known_40_degree_climb_with_inclined_thrust():
    weight=1000*G0;area=15;lift=.8;drag=.02+.05*lift*lift
    gamma=math.radians(40);epsilon=math.radians(20)
    qarea=weight*(math.cos(gamma)-math.tan(epsilon)*math.sin(gamma))/(lift+drag*math.tan(epsilon))
    thrust=(qarea*drag+weight*math.sin(gamma))/math.cos(epsilon)
    v=math.sqrt(2*qarea/(isa_atmosphere(0)['rho']*area))
    polar=[dict(cl=c,cd=.02+.05*c*c,alpha_deg=5) for c in (0,.2,.4,.6,.8,1,1.2,1.5)]
    # At Ma=0 table selects static T directly; use a constant measured thrust table.
    config=dict(kind='jet',engine_count=1,engine=dict(model='table',altitude_slices=[
        dict(altitude_m=h,mach_thrust=[[0,thrust],[1,thrust]]) for h in (0,1000)]))
    result=exact_force_equilibrium(1000,area,0,[v],polar,config,thrust_axis_deg=15)
    root=min(result['rows'][0]['equilibria'],key=lambda r:abs(r['cl']-.8))
    assert root['cl']==pytest.approx(.8,abs=1e-9)
    assert root['gamma_deg']==pytest.approx(40,abs=1e-8)
    assert abs(root['tangential_residual_n'])<1e-6
    assert abs(root['normal_residual_n'])<1e-6
    assert root['lift_n']<weight*math.cos(gamma)


def test_method_eligibility_uses_maximum_total_installed_power_or_thrust():
    assert method_eligibility(1000,total_power_w=120000)['within_course_power_method_loading']
    assert not method_eligibility(1000,total_power_w=200000)['within_course_power_method_loading']
    assert not method_eligibility(1000,total_thrust_n=10000)['within_course_power_method_loading']
    with pytest.raises(ValueError):method_eligibility(1000,total_power_w=1e5,total_thrust_n=1000)
