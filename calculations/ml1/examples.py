"""Synthetic verification workbooks. These are explicitly not real aircraft data."""
import copy
import math


def example_workbook(kind='propeller',pitch='variable'):
    span=math.sqrt(120)
    root=1.8
    tip=30/span-root
    cl_values=[-.8,-.6,-.4,-.2,0,.02,.04,.06,.08,.1,.2,.4,.6,.8,1,1.2,1.4,1.5]
    def rows(re):return [dict(cl=c,alpha_deg=math.degrees(c/6.18)-2,
                              cd=.008*(3e6/re)**.11+.006*c*c) for c in cl_values]
    propeller=dict(name='Mapa demonstracyjna',source='Syntetyczne dane do nauki i testów, nie pomiar śmigła.',curves=[])
    for beta,base in [(10,.08),(50,.3)]:
        propeller['curves'].append(dict(beta_deg=beta,rows=[dict(j=j,cn=base-.012*j,
            eta=eta*(1 if beta==10 else .98)) for j,eta in [(0,0),(.5,.6),(1,.82),(1.5,.82),(2,.7),(3,.4),(4,.1),(5,0)]]))
    data=dict(example_basis='synthetic_educational_data',aircraft=dict(name='Przykład ML1 — dane syntetyczne',
        span_m=span,length_m=8,height_m=2.5,area_m2=15,empty_mass_kg=750,mtow_kg=1000,
        flight_mass_kg=1000,fuel_mass_kg=150,payload_mass_kg=100,propulsion=kind,
        sources=['Syntetyczny zestaw weryfikacyjny aplikacji. Nie jest opisem istniejącego samolotu.'],
        reported_performance={},notes='Wartości służą do prześledzenia metod ML1.',
        drawing=dict(reference_length_m=span,measured_length_mm=span*1000/75,target_denominator=75)),
        geometry=dict(stations=[dict(y_m=0,x_le_m=0,chord_m=root),dict(y_m=span/2,x_le_m=.3,chord_m=tip)]),
        profile=dict(name='Profil demonstracyjny',source='Syntetyczne trzy charakterystyki tunelowe.',
                     cm_ac=-.05,x_ac_mac=.25,z_ac_mac=-.05,data_kind='section',sweep_quarter_deg=0,
                     material='metal_composite',datasets=[dict(re=re,rows=rows(re)) for re in (1e6,3e6,6e6)]),
        aircraft_aerodynamics=dict(x_cg_mac=.28,zeta=6,interference=.04,
            tail=dict(area_m2=3,arm_m=4,span_m=3.5,oswald_e=.8,position='fuselage_axis',profile_cd_min=.008,gap_cd=.005),
            components=[dict(name='Kadłub',cd=.1,reference_area_m2=1.5,source='Dane syntetyczne'),
                        dict(name='Usterzenie pionowe',cd=.013,reference_area_m2=1.5,source='Dane syntetyczne'),
                        dict(name='Podwozie',cd=.15,reference_area_m2=.3,source='Dane syntetyczne')]),
        glide_cases=[dict(mass_kg=m,altitude_m=0) for m in (1000,900,800)],
        propulsion=dict(kind=kind,engine_count=1,pitch=pitch,diameter_m=2,rpm=1800,beta_deg=20,
                        propeller=propeller,engine=dict(model='piston_unboosted',power_sl_w=120000,lapse_k=.14),
                        engine_rpm_power=[[600,40000],[2400,160000]]),
        performance=dict(heights_m=[0,2000,4000,6000,8000,10000],cl_min=.1,samples=81,climb_steps=40),
        cruise=dict(altitude_m=0,sfc=.25,eta=.8,nominal_per_engine=120,cl_min=.2,cl_max=1.3,steps=160),
        propeller_design=dict(velocity_ms=60,altitude_m=0,power_w=120000,revolutions_s=30,
                              maximum_speed_ms=75,material='metal',min_diameter_m=1,max_diameter_m=3))
    if kind=='jet':
        data['aircraft'].update(name='Odrzutowiec ML1 — dane syntetyczne',empty_mass_kg=600,
                                fuel_mass_kg=300,payload_mass_kg=100)
        data['propulsion']=dict(kind='jet',engine_count=1,engine=dict(model='turbojet',static_thrust_n=2200))
        data['performance'].update(prandtl=True,heights_m=[0,3000,6000,9000,12000,15000,18000,20000],cl_min=.03)
        data['cruise'].update(altitude_m=8000,sfc=.8,nominal_per_engine=1800,cl_min=.2,cl_max=1.2)
        data.pop('propeller_design')
    elif kind=='glider':
        data['aircraft'].update(name='Szybowiec ML1 — dane syntetyczne',fuel_mass_kg=0,empty_mass_kg=700)
        data.pop('propeller_design')
        data['propulsion']={}
    return copy.deepcopy(data)
