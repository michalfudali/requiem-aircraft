"""A linked, fixed-aircraft ML1 P1–P6 workbook, separate from BIPOL numbering."""
import math

from .reference import known_aircraft,drawing_scale
from .geometry import integrate_planform,elliptical_planform
from .wing import (select_reynolds_data,wing_from_section,transfer_finite_wing,
                   fit_parabolic_polar,parabolic_polar_from_chart,fit_lift_slope)
from .aircraft import aircraft_polar,drag_statistics
from .glide import glide_polar,approximate_glide
from .propulsion import atmosphere_at,shaft_power,jet_thrust,select_propeller
from .performance import availability_model,offer_chart,method_eligibility
from .range import fuel_budget,range_sweep,analytical_range
from .exact_climb import exact_force_equilibrium
from .validation import finite


def run_workbook(inputs):
    if not isinstance(inputs,dict):raise ValueError('Zeszyt ML1 musi być obiektem z danymi P1–P6.')
    reference=known_aircraft(inputs.get('aircraft'))
    geometry_input=inputs.get('geometry',{})
    geometry=(elliptical_planform(**geometry_input['ellipse']) if 'ellipse' in geometry_input else
              integrate_planform(geometry_input.get('stations')))
    area=geometry['area_m2'];span=geometry['span_m'];mac=geometry['mac_m'];ar=geometry['aspect_ratio']
    geometry_differences=dict(area_percent=100*(area/reference['area_m2']-1),
                              span_percent=100*(span/reference['span_m']-1))
    mass=reference['flight_mass_kg']
    profile=inputs.get('profile',{})
    if not str(profile.get('source','')).strip() or not str(profile.get('name','')).strip():
        raise ValueError('P2: podaj profil i źródło jego badań tunelowych.')
    selection=select_reynolds_data(profile.get('datasets'),mass,area,mac,profile.get('stall_speed_ms'),
                                   finite_wing_data=profile.get('data_kind')=='finite_wing')
    rows=selection['selected']['rows'];re=selection['selected']['re']
    material=profile.get('material','metal_composite')
    target_re=finite(profile.get('target_re',1e7),'Docelowa liczba Re',positive=True)
    taper=(geometry['stations'][-1]['chord_m']/geometry['stations'][0]['chord_m']
           if 'ellipse' not in geometry_input else 0.)
    common=dict(a_inf_rad=profile.get('a_inf_rad'),re_from=re,re_to=target_re,material=material)
    if profile.get('data_kind','section')=='finite_wing':
        wing=transfer_finite_wing(rows,profile.get('source_aspect_ratio'),ar,
                                  source_taper=profile.get('source_taper',1),target_taper=taper,
                                  source_sweep_quarter_deg=profile.get('source_sweep_quarter_deg',0),
                                  target_sweep_quarter_deg=profile.get('sweep_quarter_deg',0),
                                  target_elliptical='ellipse' in geometry_input,**common)
    elif profile.get('data_kind','section')=='section':
        wing=wing_from_section(rows,ar,taper,sweep_quarter_deg=profile.get('sweep_quarter_deg',0),
                               elliptical='ellipse' in geometry_input,**common)
    else:raise ValueError('P2: rodzaj danych musi być section lub finite_wing.')
    p3=inputs.get('aircraft_aerodynamics',{})
    polar=aircraft_polar(wing['rows'],area,mac,p3.get('tail',{}),p3.get('components',[]),
                         cm_ac=profile.get('cm_ac'),x_cg_mac=p3.get('x_cg_mac'),
                         x_ac_mac=profile.get('x_ac_mac'),zeta=p3.get('zeta',6),interference=p3.get('interference',.04))
    fit=fit_parabolic_polar(polar['rows'],ar,cl_fit_min=p3.get('cl_fit_min',0),cl_fit_max=p3.get('cl_fit_max'))
    fit_points=[r for r in polar['rows'] if fit['cl_fit_min']<=r['cl']<=fit['cl_fit_max']]
    endpoints=[dict(cl_squared=r['cl']**2,cd=r['cd']) for r in (fit_points[0],fit_points[-1])]
    graphical=parabolic_polar_from_chart(*endpoints,ar)
    graphical['point_basis']='endpoints_of_computed_table; user may supply independent chart readings in method calculator'
    positive=[dict(cl=r['cl'],cd=r['cd']) for r in polar['rows'] if r['cl']>0]
    cases=inputs.get('glide_cases')
    if cases is None:cases=[dict(mass_kg=mass*f,altitude_m=0) for f in (1,.9,.8)]
    glide=glide_polar(positive,area,cases,maximum_level_speed_ms=inputs.get('glide_maximum_level_speed_ms'))
    for case in glide['cases']:
        case['approximation']=approximate_glide(fit['cd0'],fit['k'],case['mass_kg'],area,case['altitude_m'],cl_max=positive[-1]['cl'])
        case['approximation_comparison']={name:dict(
            velocity_percent=100*(case['approximation'][name]['velocity_ms']/case[name]['velocity_ms']-1),
            sink_percent=100*(case['approximation'][name]['sink_ms']/case[name]['sink_ms']-1)) for name in ('economic','optimum')}
    result=dict(method='ml1.workbook',version=1,p1=reference,p2=dict(geometry=geometry,
        geometry_differences=geometry_differences,profile_name=profile['name'],profile_source=profile['source'],
        profile_cm_ac=profile['cm_ac'],profile_x_ac_mac=profile['x_ac_mac'],
        profile_z_ac_mac=finite(profile.get('z_ac_mac'),'Pionowe położenie środka aerodynamicznego / MAC'),
        reynolds_selection=selection,wing=wing),p3=dict(polar=polar,least_squares=fit,
        graphical_approximation=graphical),p4=glide,p5=None,p6=None,
        example_basis=inputs.get('example_basis','user_data'))
    result['p3']['drag_statistics']=drag_statistics(min(r['cd'] for r in polar['rows']),polar['cd_parasite_min'])
    if reference.get('drawing',{}).get('reference_length_m') is not None:
        result['p1']['drawing_scale']=drawing_scale(**reference['drawing'])
    if reference['propulsion']=='glider':
        result['propulsion_scope']='Szybowiec bez napędu: P5 i silnikowa część P6 nie mają zastosowania.'
        return result
    config=inputs.get('propulsion',{})
    kind=config.get('kind')
    if kind!=reference['propulsion']:raise ValueError('P1 i P5 podają różne rodzaje napędu.')
    available=availability_model(config)
    settings=inputs.get('performance',{})
    heights=settings.get('heights_m',[0,2000,4000,6000,8000,10000])
    minimum=finite(settings.get('cl_min',positive[0]['cl']),'Dolna granica Cz obliczeń',positive=True)
    maximum=positive[-1]['cl']
    if minimum<positive[0]['cl'] or minimum>=maximum:raise ValueError('Zakres P6 musi należeć do dodatniej części biegunowej P3.')
    # P5 table uses the same speed/height domain as P6, preserving missing chart
    # coverage explicitly rather than replacing it by a guessed efficiency.
    propulsion_tables=[]
    for h in heights:
        atm=atmosphere_at(h)
        speeds=[math.sqrt(2*mass*9.80665/(atm['rho']*area*(minimum+(maximum-minimum)*i/30))) for i in range(31)]
        table=[]
        for v in sorted(speeds):
            try:table.append(dict(velocity_ms=v,mach=v/atm['a'],available=True,
                                 **({'thrust_n':available(v,h)} if kind=='jet' else {'useful_power_w':available(v,h)})))
            except ValueError as error:table.append(dict(velocity_ms=v,available=False,reason=str(error)))
        propulsion_tables.append(dict(altitude_m=h,rows=table))
    result['p5']=dict(tables=propulsion_tables,config=config,propeller_selection=None)
    if kind=='propeller' and inputs.get('propeller_design'):
        design=inputs['propeller_design']
        result['p5']['propeller_selection']=select_propeller([config.get('propeller')],
            design.get('velocity_ms'),design.get('altitude_m'),design.get('power_w'),design.get('revolutions_s'),
            maximum_speed_ms=design.get('maximum_speed_ms'),material=design.get('material','metal'),
            min_diameter_m=design.get('min_diameter_m'),max_diameter_m=design.get('max_diameter_m'))
    prandtl=settings.get('prandtl',kind=='jet')
    if not isinstance(prandtl,bool):raise ValueError('Prandtl musi być wartością logiczną.')
    offer=offer_chart(mass,area,heights,available,cl_min=minimum,cl_max=maximum,polar=positive,
                      propulsion=kind,prandtl=prandtl,samples=settings.get('samples',81),
                      climb_steps=settings.get('climb_steps',40))
    cruise=inputs.get('cruise',{})
    budget=fuel_budget(reference['fuel_mass_kg'],config.get('engine_count',1),
                       cruise.get('nominal_per_engine'),cruise.get('sfc'),propulsion=kind,
                       maneuver_minutes=cruise.get('maneuver_minutes',30),reserve_minutes=cruise.get('reserve_minutes',45),
                       reserve_fuel_flow_kgh=cruise.get('reserve_fuel_flow_kgh'))
    initial=mass-budget['maneuver_fuel_kg']
    final=initial-budget['cruise_fuel_kg']
    if final<reference['empty_mass_kg']+reference['payload_mass_kg']:
        raise ValueError('Bilans paliwa P6 daje masę końcową mniejszą od pustego samolotu z ładunkiem.')
    hcruise=finite(cruise.get('altitude_m',0),'Wysokość przelotu',nonnegative=True)
    low=finite(cruise.get('cl_min',.2),'Cz minimalne tabeli zasięgu',positive=True)
    high=finite(cruise.get('cl_max',.9*maximum),'Cz maksymalne tabeli zasięgu',positive=True)
    if low>=high:raise ValueError('Zakres Cz tabeli zasięgu jest odwrócony.')
    grid=[low+(high-low)*i/12 for i in range(13)]
    ranges=range_sweep(initial,final,area,hcruise,cruise.get('sfc'),grid,
                       polar=positive,propulsion=kind,prandtl=prandtl,eta=cruise.get('eta',.8),
                       steps=cruise.get('steps',160),available=available,cl_max=maximum)
    comparison=[]
    for schedule in ranges['schedules']:
        for row in schedule['rows']:
            if not row['available']:continue
            comparison.append(analytical_range(initial,final,area,hcruise,cruise.get('sfc'),
                cd0=fit['cd0'],k=fit['k'],propulsion=kind,schedule=schedule['schedule'],
                cl=row['reference_cl'],velocity_ms=row['reference_velocity_ms'],eta=cruise.get('eta',.8)))
    result['p6']=dict(offer=offer,fuel_budget=budget,ranges=ranges,
                      incompressible_parabolic_comparison=comparison,
                      cruise_initial_mass_kg=initial,cruise_final_mass_kg=final,
                      comparison_scope='Wzory analityczne: biegunowa paraboliczna bez Prandtla; całki: biegunowa P3 i wybrana korekta.')
    result['p6']['exact_force_tables']=[dict(altitude_m=table['altitude_m'],
        **exact_force_equilibrium(mass,area,table['altitude_m'],
            [r['velocity_ms'] for r in table['rows'] if r['available']],polar['rows'],config,
            prandtl=prandtl,thrust_axis_deg=settings.get('thrust_axis_deg')))
        for table in offer['tables'] if any(r['available'] for r in table['rows'])]
    engine=config.get('engine',{})
    count=finite(config.get('engine_count',1),'Liczba silników',positive=True)
    if kind=='jet' and engine.get('static_thrust_n') is not None:
        result['p6']['method_eligibility']=method_eligibility(reference['mtow_kg'],total_thrust_n=count*engine['static_thrust_n'])
    elif kind=='propeller' and engine.get('power_sl_w') is not None:
        result['p6']['method_eligibility']=method_eligibility(reference['mtow_kg'],total_power_w=count*engine['power_sl_w'])
    else:
        result['p6']['method_eligibility']=dict(available=False,reason='Dane tabelaryczne nie deklarują maksymalnej sumarycznej mocy / ciągu.')
    return result
