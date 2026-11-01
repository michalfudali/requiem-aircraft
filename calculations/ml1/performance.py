"""ML1 P6 force/power methods, continuous intersections, offer chart and climb.

This is the published small-flight-path-angle method. Large power/thrust loading
or a climb angle over 20 degrees is explicitly outside its stated accuracy.
"""
import math

from ..atmosphere import G0
from .validation import finite,finite_result
from .numerics import pairs,interpolate,bracketed_root
from .propulsion import atmosphere_at,shaft_power,jet_thrust,variable_pitch,fixed_pitch
from .prandtl import prandtl_corrected_cd

SOURCE_URL='https://www.meil.pw.edu.pl/zm/content/download/23969/126700/file/Projekt%206.pdf'


def method_eligibility(mtow_kg,*,total_power_w=None,total_thrust_n=None):
    """P6 (6.1): choose accuracy based on maximum total installed power/thrust."""
    mass=finite(mtow_kg,'Maksymalna masa startowa',positive=True)
    if (total_power_w is None)==(total_thrust_n is None):
        raise ValueError('Podaj dokładnie jedną wielkość: sumaryczna moc maksymalna albo sumaryczny ciąg maksymalny.')
    if total_power_w is not None:
        loading=mass/(finite(total_power_w,'Sumaryczna moc maksymalna',positive=True)/1000)
        limit=6.;unit='kg/kW'
    else:
        loading=mass/(finite(total_thrust_n,'Sumaryczny ciąg maksymalny',positive=True)/1000)
        limit=300.;unit='kg/kN'
    return dict(method='ml1.p6.method_eligibility',source_url=SOURCE_URL,loading=loading,unit=unit,
                threshold=limit,within_course_power_method_loading=loading>limit,
                scope='Kryterium obciążenia według (6.1); nadal obowiązują ograniczenia kątów toru i ściśliwości.')


def polar_function(*,polar=None,cd0=None,k=None):
    if polar is not None:
        if not isinstance(polar,list) or not 2<=len(polar)<=1000:raise ValueError('Podaj 2–1000 punktów biegunowej.')
        data=pairs([(finite(r.get('cl'),'Cz'),finite(r.get('cd'),'Cx',positive=True)) for r in polar])
        def cd(cl):return interpolate(data,cl)
        return cd
    zero=finite(cd0,'Cx0',positive=True);induced=finite(k,'Nachylenie biegunowej',positive=True)
    return lambda cl:zero+induced*cl*cl


def availability_model(config):
    """Build total usable power [W] or total thrust [N], never mix per-engine values."""
    count=finite(config.get('engine_count',1),'Liczba silników',positive=True)
    if count!=int(count) or count>20:raise ValueError('Liczba silników musi być całkowita: 1–20.')
    kind=config.get('kind')
    if kind=='jet':
        engine=config.get('engine',{})
        return lambda v,h:count*jet_thrust(engine,v/atmosphere_at(h)['a'],h)['thrust_n']
    if kind!='propeller':raise ValueError('Rodzaj napędu: jet lub propeller.')
    if config.get('pitch')=='power_table':
        slices=config.get('altitude_slices',[])
        if not isinstance(slices,list) or not 2<=len(slices)<=100:raise ValueError('Podaj 2–100 wysokości charakterystyki mocy.')
        data=[(finite(s.get('altitude_m'),'Wysokość',nonnegative=True),pairs(s.get('velocity_power',[]),'Moc użyteczna na wale strugi w funkcji V')) for s in slices]
        pairs([(h,0) for h,_ in data])
        def available(v,h):
            # Use only the two neighboring height slices: irrelevant remote
            # slices may legitimately have a different measured speed domain.
            heights=sorted(data)
            if not heights[0][0]<=h<=heights[-1][0]:raise ValueError('Wysokość jest poza tabelą mocy.')
            exact=next((curve for height,curve in heights if h==height),None)
            if exact is not None:return count*interpolate(exact,v)
            a,b=next((a,b) for a,b in zip(heights,heights[1:]) if a[0]<h<b[0])
            return count*interpolate([(a[0],interpolate(a[1],v)),(b[0],interpolate(b[1],v))],h)
        return available
    engine=config.get('engine',{})
    propeller=config.get('propeller',{})
    diameter=finite(config.get('diameter_m'),'Średnica śmigła',positive=True)
    rpm=finite(config.get('rpm'),'Obroty śmigła',positive=True)
    if config.get('pitch')=='variable':
        def available(v,h):
            power=shaft_power(engine,h)['power_w']
            return count*variable_pitch(propeller,v,h,power,rpm/60,diameter)['available_power_w']
    elif config.get('pitch')=='fixed':
        external=pairs(config.get('engine_rpm_power',[]),'Moc w funkcji obr/min wału śmigła przy ziemi')
        beta=finite(config.get('beta_deg'),'Stały kąt śmigła')
        base=shaft_power(engine,0)['power_w']
        def available(v,h):
            factor=shaft_power(engine,h)['power_w']/base
            curve=[(n,p*factor) for n,p in external]
            return count*fixed_pitch(propeller,beta,v,h,diameter,curve,rpm_limit=rpm)['available_power_w']
    else:raise ValueError('Skok śmigła: fixed, variable lub power_table.')
    if engine.get('model')=='two_speed_supercharger':
        available.ml1_break_heights=[finite(engine.get('critical_1_m'),'Wysokość nominalna I',positive=True),
            finite(engine.get('shift_height_m'),'Wysokość przełączenia',positive=True),
            finite(engine.get('critical_2_m'),'Wysokość nominalna II',positive=True)]
    return available


def _maximum(function,left,right):
    """Bounded golden-section refinement, retaining both physical boundaries."""
    ratio=(math.sqrt(5)-1)/2
    lo,hi=left,right
    c=hi-ratio*(hi-lo);d=lo+ratio*(hi-lo)
    fc,fd=function(c),function(d)
    for _ in range(55):
        if fc<fd:
            lo,c,fc=c,d,fd;d=lo+ratio*(hi-lo);fd=function(d)
        else:
            hi,d,fd=d,c,fc;c=hi-ratio*(hi-lo);fc=function(c)
    candidates=[(left,function(left)),(right,function(right)),(c,fc),(d,fd)]
    return max(candidates,key=lambda p:p[1])[0]


def performance_at_height(mass_kg,area_m2,altitude_m,available,*,cl_min,cl_max,
                           polar=None,cd0=None,k=None,propulsion='propeller',prandtl=False,samples=121):
    mass=finite(mass_kg,'Masa obliczeniowa',positive=True)
    area=finite(area_m2,'Pole płata',positive=True)
    minimum=finite(cl_min,'Dolna granica Cz',positive=True)
    maximum=finite(cl_max,'Cz maksymalne',positive=True)
    if minimum>=maximum:raise ValueError('Cz minimalne musi być mniejsze od maksymalnego.')
    if isinstance(samples,bool) or not isinstance(samples,int) or not 21<=samples<=501:raise ValueError('Próbkowanie osiągów: 21–501 punktów.')
    if propulsion not in ('propeller','jet'):raise ValueError('Rodzaj napędu: propeller lub jet.')
    if prandtl and propulsion!='jet':raise ValueError('Suplement określa korektę Prandtla dla odrzutowców.')
    atm=atmosphere_at(altitude_m);rho=atm['rho'];weight=mass*G0
    cd=polar_function(polar=polar,cd0=cd0,k=k)
    slow=math.sqrt(2*weight/(rho*area*maximum))
    fast=math.sqrt(2*weight/(rho*area*minimum))
    def point(v):
        lift=2*weight/(rho*area*v*v)
        # Floating-point inversion at the exact data endpoints must not cause
        # false interpolation extrapolation.
        if abs(lift-minimum)<1e-12*minimum:lift=minimum
        if abs(lift-maximum)<1e-12*maximum:lift=maximum
        base=cd(lift);mach=v/atm['a']
        drag=prandtl_corrected_cd(base,mach) if prandtl else base
        force=weight*drag/lift
        useful=finite(available(v,atm['altitude']),'Moc lub ciąg rozporządzalny',nonnegative=True)
        thrust=useful/v if propulsion=='propeller' else useful
        power=thrust*v
        excess_force=thrust-force;excess_power=excess_force*v
        roc=excess_power/weight;sin_gamma=excess_force/weight
        gamma=math.degrees(math.asin(sin_gamma)) if abs(sin_gamma)<=1 else None
        finite_result(force,power,roc,excess_power)
        return dict(available=True,velocity_ms=v,cl=lift,cd_incompressible=base,cd=drag,mach=mach,
                    ld=lift/drag,energy_function=lift**1.5/drag,required_thrust_n=force,
                    available_thrust_n=thrust,required_power_w=force*v,available_power_w=power,
                    excess_power_w=excess_power,excess_thrust_n=excess_force,roc_ms=roc,
                    sin_gamma=sin_gamma,gamma_deg=gamma,
                    within_small_angle_scope=gamma is not None and abs(gamma)<=20,
                    compressibility_required=mach>.7,
                    compressibility_applied=prandtl)
    rows=[]
    for i in range(samples):
        v=slow+(fast-slow)*i/(samples-1)
        try:rows.append(point(v))
        except ValueError as error:rows.append(dict(available=False,velocity_ms=v,reason=str(error)))
    valid=[r for r in rows if r['available']]
    if not valid:raise ValueError('Brak wspólnego zakresu biegunowej i napędu na tej wysokości.')
    maxima={}
    for name,key in [('best_rate','roc_ms'),('best_gradient','sin_gamma')]:
        candidate=max(valid,key=lambda r:r[key])
        index=rows.index(candidate)
        if 0<index<len(rows)-1 and rows[index-1]['available'] and rows[index+1]['available']:
            try:
                optimum=_maximum(lambda v:point(v)[key],rows[index-1]['velocity_ms'],rows[index+1]['velocity_ms'])
                candidate=point(optimum)
            except ValueError:pass
        maxima[name]=candidate
    intersections=[]
    for a,b in zip(rows,rows[1:]):
        if not a['available'] or not b['available']:continue
        fa,fb=a['excess_power_w'],b['excess_power_w']
        if fa==0:intersections.append(a['velocity_ms'])
        if fa*fb<0:
            intersections.append(bracketed_root(lambda v:point(v)['excess_power_w'],a['velocity_ms'],b['velocity_ms']))
    if rows[-1]['available'] and rows[-1]['excess_power_w']==0:intersections.append(fast)
    feasible=[r['velocity_ms'] for r in valid if r['excess_power_w']>=0]+intersections
    level_min=min(feasible) if feasible else None
    level_max=max(feasible) if feasible else None
    stall_limited=rows[0]['available'] and rows[0]['excess_power_w']>=0
    upper_closed=bool(level_max is not None and any(r['available'] and r['velocity_ms']>level_max and r['excess_power_w']<0 for r in rows))
    if rows[-1]['available'] and rows[-1]['excess_power_w']==0:upper_closed=True
    return dict(method='ml1.p6.performance',source_url=SOURCE_URL,altitude_m=atm['altitude'],mass_kg=mass,
                propulsion=propulsion,prandtl=prandtl,rows=rows,intersections_ms=intersections,
                minimum_level_speed_ms=level_min,maximum_level_speed_ms=level_max if upper_closed else None,
                upper_speed_domain_limit_ms=level_max if not upper_closed else None,
                stall_limited=stall_limited,maximum_speed_bracketed=upper_closed,
                stall_speed_ms=slow,**maxima,
                scope='Metoda mocy/ciągu ML1, cos(gamma) ≈ 1; zakres małych kątów do 20 stopni.')


def linear_climb_time(height_m,theoretical_ceiling_m,sea_level_roc_ms):
    """Closed form (6.12); no finite climb time to the theoretical ceiling."""
    h=finite(height_m,'Wysokość docelowa',nonnegative=True)
    ceiling=finite(theoretical_ceiling_m,'Pułap teoretyczny',positive=True)
    rate=finite(sea_level_roc_ms,'Wznoszenie przy ziemi',positive=True)
    if h>=ceiling:raise ValueError('Dla h ≥ pułapowi teoretycznemu czas wznoszenia nie jest skończony.')
    return ceiling/rate*(-math.log1p(-h/ceiling))


def climb_time_from_chart(points,target_height_m):
    """(6.10) graphical area: integrate piecewise-linear 1/wmax exactly."""
    data=pairs(points,'Wykres odwrotności maksymalnego wznoszenia 1/w(h)')
    target=finite(target_height_m,'Wysokość docelowa',nonnegative=True)
    if data[0][0]!=0 or min(w for _,w in data)<=0 or not 0<=target<=data[-1][0]:
        raise ValueError('Wykres 1/w musi zaczynać się na ziemi, mieć dodatnie wartości i obejmować wysokość docelową.')
    nodes=[(h,value) for h,value in data if h<target]+[(target,interpolate(data,target))]
    return math.fsum((b[0]-a[0])*(a[1]+b[1])/2 for a,b in zip(nodes,nodes[1:]))


def offer_chart(mass_kg,area_m2,heights_m,available,*,climb_steps=80,**options):
    """Continuous wmax(h) ceiling roots, and Simpson integral to practical ceiling."""
    if not isinstance(heights_m,list) or not 3<=len(heights_m)<=51:
        raise ValueError('Wykres ofertowy wymaga 3–51 wysokości, zaczynając od ziemi.')
    heights=[finite(h,'Wysokość',nonnegative=True) for h in heights_m]
    if heights!=sorted(set(heights)) or heights[0]!=0 or heights[-1]>20000:
        raise ValueError('Wysokości muszą rosnąć od 0, bez powtórzeń, do maksymalnie 20 km.')
    # A gear shift may be discontinuous. Resolve both sides explicitly rather
    # than treating a jump over w=0 as an actual theoretical-ceiling root.
    breaks=[h for h in getattr(available,'ml1_break_heights',[]) if 0<h<heights[-1]]
    if breaks:
        heights=sorted(set(heights+[x for h in breaks for x in (math.nextafter(h,0),h)]))
    if isinstance(climb_steps,bool) or not isinstance(climb_steps,int) or not 20<=climb_steps<=400 or climb_steps%2:
        raise ValueError('Całkowanie wznoszenia: parzysta liczba przedziałów 20–400.')
    cache={}
    def at(h):
        if h not in cache:cache[h]=performance_at_height(mass_kg,area_m2,h,available,**options)
        return cache[h]
    tables=[at(h) for h in heights]
    def rate(h):return at(h)['best_rate']['roc_ms']
    ceilings={};discontinuities=[]
    for name,threshold in [('theoretical',0.),('practical',.5)]:
        roots=[]
        for low,high in zip(heights,heights[1:]):
            a,b=rate(low)-threshold,rate(high)-threshold
            if a==0:roots.append(low)
            if a*b<0:
                root=bracketed_root(lambda h:rate(h)-threshold,low,high,relative_tolerance=1e-8)
                if abs(rate(root)-threshold)<=1e-5:roots.append(root)
                else:discontinuities.append(dict(height_m=root,threshold_ms=threshold,
                    reason='Skok charakterystyki, nie miejsce zerowe wmax(h) − próg.'))
        if rate(heights[-1])==threshold:roots.append(heights[-1])
        # A two-speed supercharger can produce multiple operating intervals.
        # Expose all crossings instead of hiding the lower gap in a single root.
        ceilings[name+'_crossings_m']=roots
        ceilings[name+'_ceiling_m']=max(roots) if roots else None
    practical=ceilings['practical_ceiling_m']
    climb=None
    if practical is not None and rate(0)>0:
        dh=practical/climb_steps
        inverses=[]
        for i in range(climb_steps+1):
            roc=rate(i*dh)
            if roc<=0:break
            inverses.append(1/roc)
        if len(inverses)==climb_steps+1:
            climb=dh/3*math.fsum((1 if i in (0,climb_steps) else 4 if i%2 else 2)*v for i,v in enumerate(inverses))
    rows=[]
    elapsed=0.;previous=None
    for table in tables:
        best=table['best_rate'];gradient=table['best_gradient']
        inverse=1/best['roc_ms'] if best['roc_ms']>0 else None
        if inverse is None:elapsed=None
        elif previous is not None and elapsed is not None:
            elapsed+=(table['altitude_m']-previous['altitude_m'])*(inverse+previous['inverse_roc_s_m'])/2
        rows.append(dict(altitude_m=table['altitude_m'],minimum_speed_ms=table['minimum_level_speed_ms'],
                         maximum_speed_ms=table['maximum_level_speed_ms'],maximum_roc_ms=best['roc_ms'],
                         best_rate_speed_ms=best['velocity_ms'],maximum_gamma_deg=gradient['gamma_deg'],
                         best_gradient_speed_ms=gradient['velocity_ms'],
                         inverse_roc_s_m=inverse,climb_time_s=elapsed))
        previous=rows[-1]
    return dict(method='ml1.p6.offer_chart',source_url=SOURCE_URL,rows=rows,tables=tables,**ceilings,
                climb_to_practical_s=climb,climb_to_theoretical_s=None,
                theoretical_time_note='Przy wmax dążącym do zera całka czasu wznoszenia do pułapu teoretycznego jest rozbieżna.',
                table_climb_time_basis='Pole pod odcinkami wykresu 1/wmax(h), osobna całka Simpsona do pułapu praktycznego.',
                discontinuous_crossings=discontinuities,engine_break_heights_m=breaks,
                ceiling_scope='Wynik wymaga objęcia przecięcia w zadanej siatce wysokości; wszystkie przecięcia są zachowane.')
