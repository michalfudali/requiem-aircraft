"""Public, explicitly allow-listed ML1 methods and editable example inputs."""
import inspect

from . import reference,geometry,wing,aircraft,glide,propulsion,prandtl,performance
from . import range as flight_range
from .examples import example_workbook
from .workbook import run_workbook
from .exact_climb import exact_force_equilibrium


def performance_calculation(mass_kg,area_m2,altitude_m,propulsion_config,**options):
    return performance.performance_at_height(mass_kg,area_m2,altitude_m,
        performance.availability_model(propulsion_config),propulsion=propulsion_config.get('kind'),**options)


def offer_calculation(mass_kg,area_m2,heights_m,propulsion_config,**options):
    return performance.offer_chart(mass_kg,area_m2,heights_m,
        performance.availability_model(propulsion_config),propulsion=propulsion_config.get('kind'),**options)


def integrated_range_calculation(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,
                                 propulsion_config=None,**options):
    available=None if propulsion_config is None else performance.availability_model(propulsion_config)
    if propulsion_config is not None:options['propulsion']=propulsion_config.get('kind')
    return flight_range.integrate_range(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,available=available,**options)


def range_table_calculation(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,cl_values,
                           propulsion_config=None,**options):
    available=None if propulsion_config is None else performance.availability_model(propulsion_config)
    if propulsion_config is not None:options['propulsion']=propulsion_config.get('kind')
    return flight_range.range_sweep(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,cl_values,available=available,**options)


def _specs():
    demo=example_workbook();profile=demo['profile']['datasets'][1]['rows']
    converted=wing.wing_from_section(profile,8,.5)
    polar=[dict(cl=c,cd=.02+.05*c*c) for c in (0,.1,.2,.4,.6,.8,1,1.2,1.5)]
    prop=demo['propulsion']['propeller']
    p3=demo['aircraft_aerodynamics']
    power=dict(power_w=120000,revolutions_s=30,diameter_m=2)
    rargs=dict(mass_initial_kg=1000,mass_final_kg=850,area_m2=15,altitude_m=0,sfc=.25,cd0=.02,k=.05)
    performance_args=dict(mass_kg=1000,area_m2=15,cl_min=.08,cl_max=1.5,cd0=.02,k=.05,
                          propulsion_config=demo['propulsion'])
    return [
        (1,'known_aircraft','Dane znanego samolotu',reference.known_aircraft,dict(data=demo['aircraft'])),
        (1,'drawing_scale','Podziałka trzech rzutów',reference.drawing_scale,demo['aircraft']['drawing']),
        (2,'planform_integrals','Całki obrysu: S, MAC i położenie',geometry.integrate_planform,dict(stations=demo['geometry']['stations'])),
        (2,'ellipse','Płat eliptyczny z prostą linią połówek cięciw',geometry.elliptical_planform,dict(span_m=10,root_chord_m=2)),
        (2,'tunnel_data_assembly','Scalenie pomiarów i uzupełnienie Cx przy kątach krytycznych',wing.assemble_tunnel_polar,
            dict(lift_rows=[dict(cl=r['cl'],alpha_deg=r['alpha_deg']) for r in profile],drag_rows=profile,allow_critical_extrapolation=False)),
        (2,'reynolds_selection','Dobór danych spośród trzech liczb Re',wing.select_reynolds_data,dict(datasets=demo['profile']['datasets'],mass_kg=1000,area_m2=15,mac_m=1.4)),
        (2,'lift_sampling','Niejednorodna siatka Cz — tabela 2.0',wing.sample_lift_coefficients,dict(cl_max=1.5)),
        (2,'lift_slope_fit','Regresja dCz/dα w zakresie liniowym',wing.fit_lift_slope,dict(rows=profile)),
        (2,'glauert','Poprawki Glauerta τ i δ',wing.glauert_coefficients,dict(aspect_ratio=8,taper_ratio=.5,a_inf_rad=6.18)),
        (2,'reynolds_correction','Korekta oporu profilowego od Re',wing.reynolds_drag_correction,
            dict(cl=.5,cd=.01,cl_critical_positive=1.5,cl_critical_negative=-.8,cd_min_reference=.008,re_from=3e6)),
        (2,'section_to_wing','Profil → płat: kąt indukowany i składniki oporu',wing.wing_from_section,dict(rows=profile,aspect_ratio=8,taper_ratio=.5)),
        (2,'finite_wing_transfer','Tunelowy płat → inne wydłużenie i Re',wing.transfer_finite_wing,
            dict(rows=[dict(cl=r['cl'],cd=r['cd_wing'],alpha_deg=r['alpha_wing_deg']) for r in converted['rows']],source_aspect_ratio=8,target_aspect_ratio=10,a_inf_rad=6.18)),
        (2,'inverse_section_slope','Odtworzenie pochodnej profilu z pochodnej płata',wing.infer_section_slope,dict(a_wing_rad=4.5,aspect_ratio=8)),
        (2,'wing_slope_check','Porównanie pochodnej płata z równaniem 2.27',wing.compare_wing_slope,
            dict(rows=[dict(cl=r['cl'],cd=r['cd_wing'],alpha_deg=r['alpha_wing_deg']) for r in converted['rows']],theoretical_a_rad=converted['a_wing_rad'])),
        (3,'chart_reading','Odczyty wykresów i tablic podzespołów',aircraft.chart_reading,dict(points=[[1e6,.004],[1e7,.003],[1e8,.002]],argument=5e6,logarithmic_x=True)),
        (3,'chart_surface','Interpolacja między krzywymi wykresu (np. ηMa)',aircraft.chart_surface,
            dict(curves=[dict(parameter=2,points=[[0,1],[.8,1.2]]),dict(parameter=4,points=[[0,1],[.8,1.1]])],argument=.4,parameter=3)),
        (3,'drag_statistics','Porównanie oporów z tabelami A, B i C',aircraft.drag_statistics,dict(cd_min=.03,cd_parasite_min=.015)),
        (3,'fuselage','Kadłub opływowy — wzór Ostosławskiego',aircraft.fuselage_drag,
            dict(length_m=8,frontal_area_m2=1.5,nose_length_m=2,velocity_ms=60,altitude_m=0,cf=.003,eta_shape=1.2,eta_mach=1)),
        (3,'component_drag','Opór podzespołu: Cx·S lub siła z tunelu / q',aircraft.component_drag_area,dict(component=p3['components'][0])),
        (3,'vertical_tail','Opór usterzenia pionowego',aircraft.vertical_tail_drag,dict(profile_cd_min=.008,gap_cd=.005,area_m2=1.5)),
        (3,'aircraft_polar','Biegunowa całego samolotu i równowaga usterzenia',aircraft.aircraft_polar,
            dict(wing_rows=converted['rows'],area_m2=15,mac_m=1.4,tail=p3['tail'],components=p3['components'],cm_ac=-.05,x_cg_mac=.28,x_ac_mac=.25)),
        (3,'parabolic_fit','Biegunowa analityczna — najmniejsze kwadraty',wing.fit_parabolic_polar,dict(rows=polar,aspect_ratio=8)),
        (3,'graphical_fit','Biegunowa analityczna — metoda wykreślno-rachunkowa',wing.parabolic_polar_from_chart,
            dict(point_a=dict(cl_squared=0,cd=.02),point_b=dict(cl_squared=1,cd=.07),aspect_ratio=8)),
        (4,'exact_glide','Dokładna biegunowa prędkości dla trzech mas / wysokości',glide.glide_polar,dict(polar=polar,area_m2=15,cases=demo['glide_cases'])),
        (4,'approximate_glide','Przybliżone warunki optymalne i ekonomiczne',glide.approximate_glide,dict(cd0=.02,k=.05,mass_kg=1000,area_m2=15,altitude_m=0,cl_max=1.5)),
        (5,'shaft_power','Moc silnika z wysokością: modele i tabela',propulsion.shaft_power,dict(engine=demo['propulsion']['engine'],altitude_m=2000)),
        (5,'jet_thrust','Ciąg silnika jedno-/dwuprzepływowego lub tabela',propulsion.jet_thrust,dict(engine=dict(model='turbojet',static_thrust_n=10000),mach=.6,altitude_m=8000)),
        (5,'propeller_selection','Dobór śmigła i średnicy z mapy',propulsion.select_propeller,
            dict(candidates=[prop],velocity_ms=60,altitude_m=0,power_w=120000,revolutions_s=30,maximum_speed_ms=75)),
        (5,'variable_pitch','Śmigło przestawialne: rozwiązanie kąta łopaty',propulsion.variable_pitch,dict(propeller=prop,velocity_ms=60,altitude_m=0,**power)),
        (5,'fixed_pitch','Śmigło stałe: równowaga z charakterystyką obrotową',propulsion.fixed_pitch,
            dict(propeller=prop,beta_deg=20,velocity_ms=50,altitude_m=0,diameter_m=2,engine_curve=[[600,40000],[2400,160000]],rpm_limit=1800)),
        (5,'constant_torque','Śmigło stałe: metoda N/n=const i ogranicznik obrotów',propulsion.fixed_pitch_constant_torque,
            dict(propeller=prop,beta_deg=20,j_values=[0,.5,1,1.5,2,3],altitude_m=0,diameter_m=2,power_at_max_w=120000,rpm_max=1800)),
        (6,'prandtl','Korekta całego Cx — suplement ML1',prandtl.prandtl_corrected_cd,dict(cd_incompressible=.03,mach=.6)),
        (6,'method_eligibility','Dobór dokładności metody z obciążenia mocy / ciągu',performance.method_eligibility,dict(mtow_kg=1000,total_power_w=120000)),
        (6,'altitude_polars','Biegunowe odrzutowca dla różnych wysokości',prandtl.altitude_polars,
            dict(mass_kg=6000,area_m2=20,polar=polar,altitudes_m=[0,4000,8000])),
        (6,'performance','Metoda mocy / ciągu: przecięcia i najlepsze wznoszenie',performance_calculation,dict(altitude_m=0,**performance_args)),
        (6,'exact_force_equilibrium','Dokładna równowaga sił przy dużym kącie wznoszenia',exact_force_equilibrium,
            dict(mass_kg=1000,area_m2=15,altitude_m=0,velocities_ms=[35,45,55,65],polar=polar,propulsion_config=demo['propulsion'])),
        (6,'offer_chart','Wykres ofertowy, pułapy i czas wznoszenia',offer_calculation,dict(heights_m=[0,2000,4000,6000,8000,10000],**performance_args)),
        (6,'linear_climb','Analityczny czas dla liniowego wmax(h)',performance.linear_climb_time,dict(height_m=4000,theoretical_ceiling_m=8000,sea_level_roc_ms=5)),
        (6,'chart_climb','Czas wznoszenia jako pole pod wykresem 1/wmax',performance.climb_time_from_chart,dict(points=[[0,.2],[2000,.3],[4000,.5]],target_height_m=3000)),
        (6,'fuel_budget','Paliwo na przelot po odjęciu manewrów i rezerwy',flight_range.fuel_budget,dict(fuel_kg=150,engine_count=1,nominal_per_engine=120,sfc=.25)),
        (6,'analytical_range','Cztery wzory analityczne zasięgu i długotrwałości',flight_range.analytical_range,dict(**rargs,cl=.6)),
        (6,'integrated_range','Całki masy: biegunowa, zmienne V/Ma, opcjonalnie Prandtl',integrated_range_calculation,dict(**rargs,cl=.6)),
        (6,'range_table','Tabela 6.3: oba programy lotu i ich ekstrema',range_table_calculation,dict(**rargs,cl_values=[.3,.5,.7,.9,1.1])),
    ]


# Construct once: all examples are cheap deterministic data, without network or DB.
SPECS={entry[1]:entry for entry in _specs()}


def calculate(method,inputs):
    if not isinstance(inputs,dict):raise ValueError('Parametry metody muszą być obiektem JSON.')
    if method=='workbook':return run_workbook(inputs)
    if method not in SPECS:raise ValueError('Nieznana metoda ML1.')
    function=SPECS[method][3]
    try:inspect.signature(function).bind(**inputs)
    except TypeError as error:raise ValueError('Parametry metody: '+str(error)) from None
    return function(**inputs)


def catalog():
    methods=[]
    for project,identifier,title,function,example in SPECS.values():
        defaults={name:p.default for name,p in inspect.signature(function).parameters.items()
                  if p.default is not inspect.Parameter.empty and p.kind not in (p.VAR_KEYWORD,p.VAR_POSITIONAL)}
        # Wrapper kwargs expose the same explicit options as the numerical method.
        underlying={'performance':performance.performance_at_height,'offer_chart':performance.performance_at_height,
                    'integrated_range':flight_range.integrate_range,'range_table':flight_range.integrate_range}.get(identifier)
        if underlying:
            defaults.update({name:p.default for name,p in inspect.signature(underlying).parameters.items()
                if p.default is not inspect.Parameter.empty and name not in ('available','samples' if identifier=='offer_chart' else '')})
        values=dict(defaults,**example)
        if identifier=='range_table':
            values.pop('cl',None);values.pop('velocity_ms',None);values.pop('schedule',None)
        if identifier in ('performance','offer_chart'):values.pop('propulsion',None)
        methods.append(dict(project=project,id=identifier,title=title,inputs=values,
                            description=inspect.getdoc(function) or '',
                            source_url={1:reference.SOURCE_URL,2:geometry.SOURCE_URL,3:aircraft.SOURCE_URL,
                                        4:glide.SOURCE_URL,5:propulsion.SOURCE_URL,6:performance.SOURCE_URL}[project]))
    return methods
