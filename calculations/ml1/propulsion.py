"""ML1 project 5: chart-driven propeller matching and engine characteristics.

Propeller maps use CN=P/(rho n³D⁵), J=V/(nD), n in revolutions/second.
Each map has curves [{beta_deg, rows:[{j,cn,eta}]}] and a source citation.
Only interpolation within the supplied chart domain is permitted.
"""
import math

from ..atmosphere import isa_atmosphere
from .validation import finite, finite_result
from .numerics import pairs, interpolate, bracketed_root

SOURCE_URL='https://www.meil.pw.edu.pl/zm/content/download/23968/126696/file/Projekt%205.pdf'


def atmosphere_at(height):
    h=finite(height,'Wysokość',nonnegative=True)
    if h>20000:raise ValueError('Wysokość musi mieścić się w zakresie 0–20 km.')
    return isa_atmosphere(h)


def shaft_power(engine, altitude_m):
    """(5.6)–(5.8), or the manufacturer's measured altitude curve, per engine."""
    atm=atmosphere_at(altitude_m)
    h=atm['altitude']
    model=engine.get('model')
    if model=='table':
        power=interpolate(pairs(engine.get('altitude_power',[]),'Moc na wysokości'),h)
        stage='manufacturer_data'
    else:
        p0=finite(engine.get('power_sl_w'),'Moc przy ziemi',positive=True)
        k=finite(engine.get('lapse_k',.14),'Współczynnik k')
        if not .08<=k<=.25:raise ValueError('Współczynnik k silnika tłokowego: 0,08–0,25.')
        def lapse(power,reference_height):
            sigma=atm['rho']/atmosphere_at(reference_height)['rho']
            return power*(sigma-k)/(1-k)
        if model=='piston_unboosted':
            power=lapse(p0,0)
            stage='unboosted'
        elif model=='turboprop':
            power=p0*(atm['rho']/atmosphere_at(0)['rho'])**.6
            stage='density_exponent_0.6'
        elif model=='turbocharged':
            critical=finite(engine.get('critical_height_m'),'Wysokość krytyczna',positive=True)
            atmosphere_at(critical)
            power=p0 if h<=critical else lapse(p0,critical)
            stage='regulated' if h<=critical else 'above_critical'
        elif model=='two_speed_supercharger':
            h1=finite(engine.get('critical_1_m'),'Wysokość nominalna I biegu',positive=True)
            hs=finite(engine.get('shift_height_m'),'Wysokość przełączenia',positive=True)
            h2=finite(engine.get('critical_2_m'),'Wysokość nominalna II biegu',positive=True)
            p1=finite(engine.get('power_critical_1_w'),'Moc nominalna I biegu',positive=True)
            ps=finite(engine.get('power_shift_2_w'),'Moc II biegu po przełączeniu',positive=True)
            p2=finite(engine.get('power_critical_2_w'),'Moc nominalna II biegu',positive=True)
            if not 0<h1<hs<h2<=20000:
                raise ValueError('Wysokości sprężarki muszą spełniać 0 < hn1 < hprzeł < hn2 ≤ 20 km.')
            if h<=h1:
                power=p0+(p1-p0)*h/h1;stage='first_regulated'
            elif h<hs:
                power=lapse(p1,h1);stage='first_unregulated'
            elif h<=h2:
                power=ps+(p2-ps)*(h-hs)/(h2-hs);stage='second_regulated'
            else:
                power=lapse(p2,h2);stage='second_unregulated'
        else:raise ValueError('Wybierz model wysokościowy silnika lub tabelę producenta.')
    finite_result(power)
    if power<=0:
        raise ValueError('Model nie daje dodatniej mocy na tej wysokości; osiągnięto granicę jego zakresu.')
    return dict(method='ml1.p5.shaft_power',source_url=SOURCE_URL,power_w=power,stage=stage,altitude_m=h)


def jet_thrust(engine,mach,altitude_m):
    """Single-/two-stream equations (5.18)–(5.20), or 2-D manufacturer data."""
    m=finite(mach,'Liczba Macha',nonnegative=True)
    atm=atmosphere_at(altitude_m)
    if engine.get('model')=='table':
        slices=engine.get('altitude_slices',[])
        if not isinstance(slices,list) or not 2<=len(slices)<=100:
            raise ValueError('Tabela ciągu wymaga 2–100 charakterystyk wysokościowych.')
        data=sorted((finite(s.get('altitude_m'),'Wysokość charakterystyki',nonnegative=True),
                     pairs(s.get('mach_thrust',[]),'Ciąg w funkcji Ma')) for s in slices)
        pairs([(h,0) for h,_ in data])
        h=atm['altitude']
        if not data[0][0]<=h<=data[-1][0]:raise ValueError('Wysokość jest poza tabelą ciągu.')
        exact=next((curve for height,curve in data if height==h),None)
        if exact is not None:thrust=interpolate(exact,m)
        else:
            a,b=next((a,b) for a,b in zip(data,data[1:]) if a[0]<h<b[0])
            thrust=interpolate([(a[0],interpolate(a[1],m)),(b[0],interpolate(b[1],m))],h)
    else:
        if m>1.6:raise ValueError('Charakterystyka przybliżona ML1 jest ograniczona do Ma ≤ 1,6.')
        static=finite(engine.get('static_thrust_n'),'Ciąg statyczny przy ziemi',positive=True)
        base=static*(atm['rho']/atmosphere_at(0)['rho'])**.85
        if engine.get('model')=='turbojet':factor=1-.605*m+.725*m*m
        elif engine.get('model')=='turbofan':
            kp=finite(engine.get('kp'),'Współczynnik Kp',positive=True)
            if not .3<=kp<=.65:raise ValueError('Współczynnik Kp: 0,3–0,65.')
            factor=1-kp*m
        else:raise ValueError('Wybierz model turbojet, turbofan lub table.')
        thrust=base*factor
    finite(thrust,'Ciąg rozporządzalny',nonnegative=True)
    return dict(method='ml1.p5.jet_thrust',source_url=SOURCE_URL,thrust_n=thrust,mach=m,altitude_m=atm['altitude'])


def normalize_propeller(propeller):
    if not isinstance(propeller,dict) or not str(propeller.get('source','')).strip():
        raise ValueError('Podaj źródło charakterystyki śmigła, numer rysunku i typ łopaty.')
    curves=propeller.get('curves')
    if not isinstance(curves,list) or not 1<=len(curves)<=100:
        raise ValueError('Mapa śmigła musi zawierać 1–100 krzywych kąta ustawienia.')
    out=[]
    for curve in curves:
        beta=finite(curve.get('beta_deg'),'Kąt ustawienia łopaty')
        rows=curve.get('rows')
        if not isinstance(rows,list) or not 2<=len(rows)<=1000:
            raise ValueError('Krzywa śmigła musi zawierać 2–1000 odczytów.')
        normalized=[]
        for row in rows:
            j=finite(row.get('j'),'Posuw J',nonnegative=True)
            cn=finite(row.get('cn'),'Współczynnik mocy CN',nonnegative=True)
            eta=finite(row.get('eta'),'Sprawność śmigła',nonnegative=True)
            if eta>1 or (j==0 and eta!=0):raise ValueError('Sprawność musi wynosić 0–1, a przy J=0 jest równa zero.')
            normalized.append(dict(j=j,cn=cn,eta=eta))
        normalized.sort(key=lambda r:r['j'])
        pairs([(r['j'],r['cn']) for r in normalized])
        out.append(dict(beta_deg=beta,rows=normalized))
    out.sort(key=lambda c:c['beta_deg'])
    if any(a['beta_deg']==b['beta_deg'] for a,b in zip(out,out[1:])):
        raise ValueError('Kąty ustawienia krzywych muszą być różne.')
    return out


def _curve_at(curve,j):
    return {key:interpolate([(r['j'],r[key]) for r in curve['rows']],j) for key in ('cn','eta')}


def propeller_at(curves,j,beta_deg):
    """Bilinear between J-readings and neighboring pitch curves; no extrapolation."""
    beta=finite(beta_deg,'Kąt ustawienia łopaty')
    if not curves[0]['beta_deg']<=beta<=curves[-1]['beta_deg']:
        raise ValueError('Kąt łopaty jest poza zakresem mapy śmigła.')
    for curve in curves:
        if beta==curve['beta_deg']:return _curve_at(curve,j)
    a,b=next((a,b) for a,b in zip(curves,curves[1:]) if a['beta_deg']<beta<b['beta_deg'])
    va,vb=_curve_at(a,j),_curve_at(b,j)
    ratio=(beta-a['beta_deg'])/(b['beta_deg']-a['beta_deg'])
    return {key:va[key]+ratio*(vb[key]-va[key]) for key in ('cn','eta')}


def variable_pitch(propeller,velocity_ms,altitude_m,power_w,revolutions_s,diameter_m):
    curves=normalize_propeller(propeller)
    v=finite(velocity_ms,'Prędkość lotu',nonnegative=True)
    p=finite(power_w,'Moc na wale śmigła',positive=True)
    n=finite(revolutions_s,'Obroty śmigła [1/s]',positive=True)
    d=finite(diameter_m,'Średnica śmigła',positive=True)
    atm=atmosphere_at(altitude_m)
    j=v/(n*d)
    cn=p/(atm['rho']*n**3*d**5)
    readings=[]
    for index,curve in enumerate(curves):
        if curve['rows'][0]['j']<=j<=curve['rows'][-1]['j']:
            readings.append((curve['beta_deg'],_curve_at(curve,j),index))
    if not readings:raise ValueError('Posuw jest poza zakresem mapy śmigła.')
    matches=[]
    for beta,reading,_ in readings:
        if abs(reading['cn']-cn)<=1e-12*max(1,cn):matches.append((beta,reading['eta']))
    for (ba,a,ia),(bb,b,ib) in zip(readings,readings[1:]):
        if ib==ia+1 and (a['cn']-cn)*(b['cn']-cn)<0:
            fraction=(cn-a['cn'])/(b['cn']-a['cn'])
            matches.append((ba+fraction*(bb-ba),a['eta']+fraction*(b['eta']-a['eta'])))
    if len(matches)!=1:raise ValueError('Mapa nie daje jednoznacznego kąta ustawienia dla podanych J i CN.')
    beta,eta=matches[0]
    return dict(method='ml1.p5.variable_pitch',source_url=SOURCE_URL,j=j,cn=cn,beta_deg=beta,eta=eta,
                revolutions_s=n,diameter_m=d,shaft_power_w=p,available_power_w=p*eta,
                velocity_ms=v,altitude_m=atm['altitude'])


def _roots_on_grid(function,grid):
    result=[]
    for lo,hi in zip(grid,grid[1:]):
        fl,fh=function(lo),function(hi)
        if fl==0:result.append(lo)
        if fl*fh<0:result.append(bracketed_root(function,lo,hi))
    if function(grid[-1])==0:result.append(grid[-1])
    unique=[]
    for root in result:
        if not unique or abs(root-unique[-1])>1e-8*max(1,root):unique.append(root)
    return unique


def fixed_pitch(propeller,beta_deg,velocity_ms,altitude_m,diameter_m,engine_curve,*,rpm_limit):
    """Solve (5.9) using measured external engine power versus propeller RPM.

    If absorbed power at nmax is below full-throttle power, throttle the engine
    to the absorbed power at nmax, as (5.15)–(5.17) require. The engine curve
    must already refer to the selected altitude and the propeller shaft.
    """
    curves=normalize_propeller(propeller)
    beta=finite(beta_deg,'Stały kąt ustawienia')
    v=finite(velocity_ms,'Prędkość',nonnegative=True)
    d=finite(diameter_m,'Średnica',positive=True)
    limit=finite(rpm_limit,'Maksymalne obroty śmigła [obr/min]',positive=True)/60
    engine=pairs(engine_curve,'Moc silnika w funkcji obr/min śmigła')
    if engine[0][0]<=0 or min(p for _,p in engine)<=0:
        raise ValueError('Zewnętrzna charakterystyka silnika musi mieć dodatnie obroty i moc.')
    atm=atmosphere_at(altitude_m)
    active=[c for c in curves if c['beta_deg']==beta]
    if not active:
        active=list(next((a,b) for a,b in zip(curves,curves[1:]) if a['beta_deg']<beta<b['beta_deg'])) if curves[0]['beta_deg']<beta<curves[-1]['beta_deg'] else []
    if not active:raise ValueError('Kąt ustawienia poza mapą.')
    jlo=max(c['rows'][0]['j'] for c in active)
    jhi=min(c['rows'][-1]['j'] for c in active)
    low=engine[0][0]/60
    high=min(engine[-1][0]/60,limit)
    if v>0:
        low=max(low,v/(d*jhi))
        if jlo>0:high=min(high,v/(d*jlo))
    elif jlo>0:raise ValueError('Mapa nie zawiera charakterystyki statycznej J=0.')
    if low>=high:raise ValueError('Brak wspólnego zakresu obrotów silnika i mapy śmigła.')
    def absorbed(n):
        return propeller_at(curves,v/(n*d),beta)['cn']*atm['rho']*n**3*d**5
    def residual(n):return interpolate(engine,n*60)-absorbed(n)
    # On each map/engine segment CN=a+b/n and engine power is linear in n.
    # Their residual is cubic. Include its derivative roots to isolate every
    # intersection exactly, avoiding hundreds of trial RPMs per flight point.
    grid=sorted(set([low,high]+[rpm/60 for rpm,_ in engine if low<rpm/60<high]+
        [v/(d*r['j']) for c in active for r in c['rows']
         if r['j']>0 and low<v/(d*r['j'])<high]))
    critical=[]
    for lo,hi in zip(grid,grid[1:]):
        n1=lo+(hi-lo)*.25;n2=lo+(hi-lo)*.75
        c1=propeller_at(curves,v/(n1*d),beta)['cn']
        c2=propeller_at(curves,v/(n2*d),beta)['cn']
        b=(c1-c2)/(1/n1-1/n2)
        a=c1-b/n1
        engine_slope=(interpolate(engine,n2*60)-interpolate(engine,n1*60))/(n2-n1)
        qa=3*atm['rho']*d**5*a;qb=2*atm['rho']*d**5*b;qc=-engine_slope
        if abs(qa)<1e-20:
            if abs(qb)>1e-20:
                root=-qc/qb
                if lo<root<hi:critical.append(root)
        else:
            discriminant=qb*qb-4*qa*qc
            if discriminant>=0:
                for root in ((-qb-math.sqrt(discriminant))/(2*qa),(-qb+math.sqrt(discriminant))/(2*qa)):
                    if lo<root<hi:critical.append(root)
    grid=sorted(set(grid+critical))
    roots=_roots_on_grid(residual,grid)
    throttled=False
    if len(roots)==1:n=roots[0]
    elif not roots and high==limit and residual(high)>0:
        n=limit;throttled=True
    else:raise ValueError('Brak jednoznacznej równowagi silnika i śmigła w podanym zakresie.')
    point=propeller_at(curves,v/(n*d),beta)
    power=absorbed(n)
    max_power=interpolate(engine,n*60)
    return dict(method='ml1.p5.fixed_pitch',source_url=SOURCE_URL,j=v/(n*d),cn=point['cn'],
                eta=point['eta'],beta_deg=beta,rpm=n*60,shaft_power_w=power,
                full_throttle_power_w=max_power,available_power_w=power*point['eta'],
                throttle_fraction=power/max_power,rpm_limited=throttled,
                balance_residual_w=power-(power if throttled else max_power),
                velocity_ms=v,altitude_m=atm['altitude'])


def fixed_pitch_constant_torque(propeller,beta_deg,j_values,altitude_m,diameter_m,
                                power_at_max_w,rpm_max):
    """Published parametric shortcut (5.10)–(5.17), with the RPM limiter."""
    curves=normalize_propeller(propeller)
    atm=atmosphere_at(altitude_m)
    d=finite(diameter_m,'Średnica śmigła',positive=True)
    nmax=finite(rpm_max,'Obroty maksymalne',positive=True)/60
    pmax=finite(power_at_max_w,'Moc przy obrotach maksymalnych',positive=True)
    torque_power=pmax/nmax
    rows=[]
    if not isinstance(j_values,list) or not 2<=len(j_values)<=1000:raise ValueError('Podaj 2–1000 wartości J.')
    for j in j_values:
        j=finite(j,'Posuw',nonnegative=True)
        point=propeller_at(curves,j,beta_deg)
        cn=point['cn']
        if cn<=0:
            rows.append(dict(j=j,available_power_w=0.,shaft_power_w=0.,rpm=nmax*60,
                             velocity_ms=j*nmax*d,rpm_limited=True,eta=point['eta']))
            continue
        unrestricted=math.sqrt(torque_power/(atm['rho']*d**5*cn))
        n=min(nmax,unrestricted)
        absorbed=cn*atm['rho']*n**3*d**5
        rows.append(dict(j=j,cn=cn,eta=point['eta'],rpm=n*60,velocity_ms=j*n*d,
                         shaft_power_w=absorbed,available_power_w=absorbed*point['eta'],
                         rpm_limited=unrestricted>nmax,unrestricted_rpm=unrestricted*60,
                         throttle_fraction=absorbed/(torque_power*n)))
    return dict(method='ml1.p5.constant_torque_fixed_pitch',source_url=SOURCE_URL,
                cn_limit=pmax/(atm['rho']*nmax**3*d**5),rows=rows)


def select_propeller(candidates,velocity_ms,altitude_m,power_w,revolutions_s,*,maximum_speed_ms,
                     material='metal',min_diameter_m=None,max_diameter_m=None):
    """Diameter-free coefficient and map optimum (5.1)–(5.3), discrete pitch curves.

    Candidate J is solved from J^5/CN(J,beta)=rho V^5/(P n²), not assumed.
    Geometrical installation limits are supplied by the user, never arbitrary.
    """
    v=finite(velocity_ms,'Prędkość doboru',positive=True)
    vmax=finite(maximum_speed_ms,'Maksymalna prędkość pozioma',positive=True)
    p=finite(power_w,'Moc doboru na wale',positive=True)
    n=finite(revolutions_s,'Obroty śmigła [1/s]',positive=True)
    atm=atmosphere_at(altitude_m)
    if material not in ('metal','wood_composite'):raise ValueError('Materiał śmigła: metal lub wood_composite.')
    tip_limit=.9 if material=='metal' else .8
    target=atm['rho']*v**5/(p*n*n)
    choices=[]
    if not isinstance(candidates,list) or not 1<=len(candidates)<=100:raise ValueError('Podaj 1–100 map śmigieł.')
    dmin=None if min_diameter_m is None else finite(min_diameter_m,'Minimalna średnica zabudowy',positive=True)
    dmax=None if max_diameter_m is None else finite(max_diameter_m,'Maksymalna średnica zabudowy',positive=True)
    if dmin is not None and dmax is not None and dmin>dmax:raise ValueError('Granice średnicy są odwrócone.')
    for candidate in candidates:
        for curve in normalize_propeller(candidate):
            # J^5-target*CN avoids division at the zero-power boundary.
            def equation(j):return j**5-target*_curve_at(curve,j)['cn']
            roots=_roots_on_grid(equation,[r['j'] for r in curve['rows']])
            for j in roots:
                if j<=0:continue
                point=_curve_at(curve,j)
                d=v/(j*n)
                tip_mach=math.hypot(1.2*vmax,math.pi*n*d)/atm['a']
                fits=(dmin is None or d>=dmin) and (dmax is None or d<=dmax)
                choices.append(dict(name=str(candidate.get('name','Śmigło')),source=candidate['source'],
                                    beta_deg=curve['beta_deg'],j=j,cn=point['cn'],eta=point['eta'],
                                    diameter_m=d,tip_mach=tip_mach,tip_mach_limit=tip_limit,
                                    tip_mach_ok=tip_mach<=tip_limit,installation_ok=fits,
                                    eligible=tip_mach<=tip_limit and fits))
    feasible=[c for c in choices if c['eligible']]
    return dict(method='ml1.p5.select_propeller',source_url=SOURCE_URL,
                diameter_free_coefficient=target**.2,candidates=choices,
                selected=max(feasible,key=lambda c:c['eta']) if feasible else None,
                optimum_basis='maximum_over_supplied_pitch_curves')
