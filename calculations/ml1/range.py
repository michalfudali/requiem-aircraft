"""ML1 P6 §6.5: four flight schedules, fuel accounting and mass integrals.

Propeller SFC is kg/(kW h), jet SFC is kg/(daN h). Public results use seconds,
metres and kilograms, with hours/km additionally provided for the course table.
"""
import math

from ..atmosphere import G0
from .propulsion import atmosphere_at
from .validation import finite, finite_result
from .numerics import pairs,interpolate
from .prandtl import prandtl_corrected_cd

SOURCE_URL='https://www.meil.pw.edu.pl/zm/content/download/23969/126700/file/Projekt%206.pdf'


def fuel_budget(fuel_kg,engine_count,nominal_per_engine, sfc,*,propulsion='propeller',
                maneuver_minutes=30.,reserve_minutes=45.,reserve_fuel_flow_kgh=None):
    """(6.13) course shortcut: both allowances at the stated nominal setting."""
    fuel=finite(fuel_kg,'Zapas paliwa',positive=True)
    count=finite(engine_count,'Liczba silników',positive=True)
    if count!=int(count):raise ValueError('Liczba silników musi być całkowita.')
    nominal=finite(nominal_per_engine,'Moc [kW] lub ciąg [N] nominalny jednego silnika',positive=True)
    qe=finite(sfc,'Jednostkowe zużycie paliwa',positive=True)
    maneuver=finite(maneuver_minutes,'Czas startu i lądowania [min]',nonnegative=True)
    reserve=finite(reserve_minutes,'Rezerwa nawigacyjna [min]',nonnegative=True)
    if propulsion not in ('propeller','jet'):raise ValueError('Rodzaj napędu: propeller lub jet.')
    hourly=count*nominal*qe/(10 if propulsion=='jet' else 1)
    reserve_flow=hourly if reserve_fuel_flow_kgh is None else finite(reserve_fuel_flow_kgh,'Zużycie godzinowe na ekonomicznym locie rezerwowym',positive=True)
    allowance=(hourly*maneuver+reserve_flow*reserve)/60
    cruise=fuel-allowance
    if cruise<=0:raise ValueError('Zapas paliwa nie pokrywa zadanych rezerw przy mocy lub ciągu nominalnym.')
    return dict(method='ml1.p6.fuel_budget',source_url=SOURCE_URL,total_fuel_kg=fuel,
                maneuver_fuel_kg=hourly*maneuver/60,reserve_fuel_kg=reserve_flow*reserve/60,
                cruise_fuel_kg=cruise,nominal_fuel_flow_kgh=hourly,
                reserve_fuel_flow_kgh=reserve_flow,
                convention=('(6.13): oba przedziały przy nastawie nominalnej; rezerwy są odejmowane tylko raz.'
                            if reserve_fuel_flow_kgh is None else 'Manewry przy nastawie nominalnej, rezerwa przy podanym ekonomicznym zużyciu paliwa.'))


def _inputs(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,propulsion,eta):
    m0=finite(mass_initial_kg,'Początkowa masa przelotu',positive=True)
    mf=finite(mass_final_kg,'Końcowa masa przelotu',positive=True)
    if mf>=m0:raise ValueError('Masa końcowa przelotu musi być mniejsza od początkowej.')
    area=finite(area_m2,'Pole płata',positive=True)
    atm=atmosphere_at(altitude_m)
    qe=finite(sfc,'Jednostkowe zużycie paliwa',positive=True)
    if propulsion not in ('propeller','jet'):raise ValueError('Napęd: propeller lub jet.')
    efficiency=finite(eta,'Sprawność śmigła',positive=True)
    if efficiency>1:raise ValueError('Sprawność śmigła nie może przekraczać 1.')
    return m0,mf,area,atm,qe,efficiency


def analytical_range(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,*,
                     cd0,k,propulsion='propeller',schedule='constant_cl',cl=None,
                     velocity_ms=None,eta=.8):
    """Closed forms (6.29)–(6.38), incompressible parabolic polar, constant eta/SFC."""
    m0,mf,area,atm,qe,efficiency=_inputs(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,propulsion,eta)
    zero=finite(cd0,'Cx0',positive=True)
    induced=finite(k,'Nachylenie biegunowej k',positive=True)
    rho=atm['rho']
    if schedule=='constant_cl':
        lift=finite(cl,'Stały Cz',positive=True)
        drag=zero+induced*lift*lift
        v0=math.sqrt(2*m0*G0/(rho*area*lift))
        vf=math.sqrt(2*mf*G0/(rho*area*lift))
        if propulsion=='propeller':
            hours=1000*lift**1.5/drag*2*efficiency/(qe*G0)*math.sqrt(rho*area/(2*G0))*(1/math.sqrt(mf)-1/math.sqrt(m0))
            km=3600*lift/drag*efficiency/(G0*qe)*math.log(m0/mf)
        else:
            hours=10/(G0*qe)*lift/drag*math.log(m0/mf)
            km=72/qe*math.sqrt(2/(G0*rho*area))*math.sqrt(lift)/drag*(math.sqrt(m0)-math.sqrt(mf))
    elif schedule=='constant_speed':
        v0=vf=finite(velocity_ms,'Stała prędkość',positive=True)
        # Integral of 1/(A+B m²); atan difference evaluated with atan2 to
        # preserve accuracy for a small fuel fraction at a large argument.
        factor=2*G0/(rho*area*v0*v0)*math.sqrt(induced/zero)
        a,b=factor*m0,factor*mf
        angle=math.atan2(a-b,1+a*b)
        common=angle/math.sqrt(zero*induced)
        hours=(1000*efficiency/(G0*v0*qe) if propulsion=='propeller' else 10/(G0*qe))*common
        km=3.6*v0*hours
    else:raise ValueError('Program lotu: constant_cl lub constant_speed.')
    finite_result(hours,km,v0,vf)
    return dict(method='ml1.p6.analytical_range',source_url=SOURCE_URL,
                propulsion=propulsion,schedule=schedule,time_h=hours,range_km=km,
                time_s=hours*3600,range_m=km*1000,initial_velocity_ms=v0,final_velocity_ms=vf,
                fuel_burn_kg=m0-mf,compressibility='incompressible',
                assumptions='Biegunowa paraboliczna, stałe qe i eta, stała wysokość; masy wyłącznie odcinka przelotowego.')


def integrate_range(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,*,
                    polar=None,cd0=None,k=None,propulsion='propeller',schedule='constant_cl',
                    cl=None,velocity_ms=None,eta=.8,prandtl=False,steps=400,
                    efficiency_curve=None,sfc_curve=None,available=None,cl_max=None):
    """(6.25)–(6.28)/(6.33): Simpson integration, recomputing V, Mach and CD.

    Optional measured eta(V), SFC(V) and available(V,h) permit checking the
    actual propulsion characteristic instead of assuming constant efficiency.
    Returns all quadrature nodes for an auditable ML1 calculation table.
    """
    m0,mf,area,atm,qe,efficiency=_inputs(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,propulsion,eta)
    if isinstance(steps,bool) or not isinstance(steps,int) or not 20<=steps<=4000 or steps%2:
        raise ValueError('Liczba przedziałów Simpsona musi być parzysta: 20–4000.')
    if prandtl and propulsion!='jet':raise ValueError('Suplement ML1 określa tę korektę Prandtla dla odrzutowców.')
    if polar is not None:
        data=pairs([(finite(r.get('cl'),'Cz'),finite(r.get('cd'),'Cx',positive=True)) for r in polar],'Biegunowa')
        def get_cd(lift):return interpolate(data,lift)
    else:
        zero=finite(cd0,'Cx0',positive=True);induced=finite(k,'Nachylenie biegunowej',positive=True)
        def get_cd(lift):return zero+induced*lift*lift
    eta_data=None if efficiency_curve is None else pairs(efficiency_curve,'Sprawność w funkcji V')
    sfc_data=None if sfc_curve is None else pairs(sfc_curve,'Zużycie jednostkowe w funkcji V')
    if schedule=='constant_cl':fixed_cl=finite(cl,'Stały Cz',positive=True)
    elif schedule=='constant_speed':fixed_v=finite(velocity_ms,'Stała prędkość',positive=True)
    else:raise ValueError('Program lotu: constant_cl lub constant_speed.')
    maximum=None if cl_max is None else finite(cl_max,'Cz maksymalne',positive=True)
    dm=(m0-mf)/steps
    time_sum=distance_sum=0.
    rows=[]
    for i in range(steps+1):
        mass=mf+dm*i
        if schedule=='constant_cl':
            lift=fixed_cl;v=math.sqrt(2*mass*G0/(atm['rho']*area*lift))
        else:
            v=fixed_v;lift=2*mass*G0/(atm['rho']*area*v*v)
        if maximum is not None and lift>maximum:raise ValueError('Program lotu przekracza Cz maksymalne.')
        mach=v/atm['a']
        drag=get_cd(lift)
        corrected=prandtl_corrected_cd(drag,mach) if prandtl else drag
        force=mass*G0*corrected/lift
        local_qe=qe if sfc_data is None else finite(interpolate(sfc_data,v),'Odczyt qe',positive=True)
        if propulsion=='propeller':
            local_eta=efficiency if eta_data is None else finite(interpolate(eta_data,v),'Sprawność',positive=True)
            if local_eta>1:raise ValueError('Sprawność przekracza 1.')
            shaft=force*v/local_eta
            flow=local_qe*shaft/(1000*3600)
            required=force*v
        else:
            local_eta=None;shaft=None;flow=local_qe*force/(10*3600);required=force
        margin=None
        if available is not None:
            margin=finite(available(v,atm['altitude']),'Dostępna moc lub ciąg',nonnegative=True)-required
            if margin<0:raise ValueError('Napęd nie zapewnia lotu poziomego dla całego programu przelotu.')
        weight=1 if i in (0,steps) else (4 if i%2 else 2)
        time_sum+=weight/flow;distance_sum+=weight*v/flow
        rows.append(dict(mass_kg=mass,cl=lift,cd_incompressible=drag,cd=corrected,mach=mach,
                         velocity_ms=v,required_thrust_n=force,required_shaft_power_w=shaft,
                         fuel_flow_kgs=flow,sfc=local_qe,eta=local_eta,available_margin=margin))
    seconds=time_sum*dm/3;metres=distance_sum*dm/3
    finite_result(seconds,metres)
    return dict(method='ml1.p6.integrated_range',source_url=SOURCE_URL,propulsion=propulsion,
                schedule=schedule,prandtl=prandtl,time_s=seconds,time_h=seconds/3600,
                range_m=metres,range_km=metres/1000,fuel_burn_kg=m0-mf,rows=rows,
                initial_velocity_ms=rows[-1]['velocity_ms'],final_velocity_ms=rows[0]['velocity_ms'],
                quadrature='composite_simpson_mass',steps=steps)


def range_sweep(mass_initial_kg,mass_final_kg,area_m2,altitude_m,sfc,cl_values,**options):
    """Table 6.3 for both schedules; V parameterized at the mean cruise mass."""
    if not isinstance(cl_values,list) or not 3<=len(cl_values)<=300:
        raise ValueError('Tabela zasięgu wymaga 3–300 wartości Cz.')
    atm=atmosphere_at(altitude_m)
    area=finite(area_m2,'Pole płata',positive=True)
    mean=(finite(mass_initial_kg,'Masa początkowa',positive=True)+finite(mass_final_kg,'Masa końcowa',positive=True))/2
    schedules=[]
    for schedule in ('constant_cl','constant_speed'):
        results=[]
        for lift in cl_values:
            lift=finite(lift,'Cz tabeli',positive=True)
            v=math.sqrt(2*mean*G0/(atm['rho']*area*lift))
            try:
                result=integrate_range(mass_initial_kg,mass_final_kg,area,altitude_m,sfc,
                                       schedule=schedule,cl=lift,velocity_ms=v,**options)
                result.pop('rows')
                result['available']=True
            except ValueError as error:
                result=dict(available=False,reason=str(error),schedule=schedule)
            result.update(reference_cl=lift,reference_velocity_ms=v)
            results.append(result)
        feasible=[r for r in results if r['available']]
        schedules.append(dict(schedule=schedule,rows=results,
                              maximum_range=max(feasible,key=lambda r:r['range_m']) if feasible else None,
                              maximum_endurance=max(feasible,key=lambda r:r['time_s']) if feasible else None))
    return dict(method='ml1.p6.range_table',source_url=SOURCE_URL,mean_cruise_mass_kg=mean,
                schedules=schedules,extrema_basis='supplied_cl_grid')
