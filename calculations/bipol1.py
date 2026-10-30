"""BIPOL_1, pp. 1–6: graph readings, empty-mass law and mission balance.

Graph samples are approximate readings of the supplied PDF, not empirical
equations with invented precision. Interpolation never extrapolates a graph.
Masses are kg; distances m; speeds TAS m/s; time s.
"""
import math
from collections import Counter

from calculations.atmosphere import G0, isa_atmosphere

# Fig. 2, p. 3. Points read from the printed axes (linear on both axes).
RAYMER = {
    'glider': [(4.1,27.5),(5,32),(6,36),(7,40),(8,44),(9,48),(10,51.5),(11.6,56.5)],
    'military_supersonic': [(.3,2.5),(.6,3.7),(.9,5),(1.2,6.3)],
    'military_subsonic': [(.3,7.5),(.7,11.2),(1.1,14.8),(1.5,17.5),(1.9,20),(2.3,21.5)],
    'jet': [(.8,14.5),(1.1,16.5),(1.45,18.5),(1.75,20.5)],
    'prop_retractable': [(1,11.5),(1.5,13.5),(2,15.5),(2.3,17)],
    'prop_fixed': [(1,8.5),(1.5,10.5),(2,12.5),(2.3,13.5)],
}
# Fig. 3, p. 5: logarithmic Mach axis, linear W/W_0.1 axis.
CORKE = [(.1,1),(.2,.997),(.3,.993),(.4,.989),(.5,.984),(.7,.975),
         (1,.960),(1.5,.935),(2,.905),(2.5,.873),(3,.839),(4,.770),
         (5,.699),(6,.638),(7,.587),(8,.542),(9,.505)]
CX0_RANGES = {
    'military': (.014,.020), 'transport': (.018,.024), 'small_twin': (.022,.028),
    'single_retractable': (.020,.030), 'single_fixed': (.025,.040),
    'agricultural': (.060,.080), 'motoglider': (.014,.020),
}


def validate_bipol1(p):
    options = {
        'mass_method': ('auto','proportion','proportions','iterative'),
        'empty_mass_model': ('class_correlation','fixed_fraction','trend','coefficients','two_point'),
        'preliminary_polar_mode': ('input','raymer','reading'),
        'raymer_family': tuple(RAYMER), 'cx0_reference_class': tuple(CX0_RANGES),
        'climb_fraction_mode': ('auto','corke','reading'),
        'trend_year_basis': ('production','certification'),
        'design_iteration_mode': ('preliminary', 'coupled'),
    }
    for key, allowed in options.items():
        if key in p and p[key] not in allowed:
            raise ValueError(f'Nieznana opcja {key}.')
    requirements = []
    mode = p.get('empty_mass_model')
    requirements += {'fixed_fraction':['empty_mass_fraction'], 'coefficients':['empty_mass_a','empty_mass_c'],
                     'two_point':['mass_point_x1','mass_point_x2','mass_point_y1','mass_point_y2']}.get(mode,[])
    if p.get('preliminary_polar_mode') in ('raymer','reading'):
        requirements += ['sketch_swet_ratio', 'raymer_family' if p['preliminary_polar_mode']=='raymer' else 'raymer_kmax']
    if p.get('climb_fraction_mode') == 'reading':
        requirements += ['corke_start_ordinate','corke_end_ordinate']
    if p.get('max_power_time_min',0):
        requirements += ['max_power_sfc', 'max_thrust_kn' if p['engine_type']=='jet' else 'max_power_kw']
        if p['engine_type'] == 'none':
            raise ValueError('Faza maksymalnej mocy wymaga napędu.')
    for key in requirements:
        if key not in p:
            raise ValueError(f'Uzupełnij parametr {key} dla wybranej metody.')
    if p.get('max_power_time_min',0) and p.get('max_thrust_kn' if p['engine_type']=='jet' else 'max_power_kw',0) <= 0:
        raise ValueError('Podaj dodatni maksymalny ciąg lub moc dla fazy zadania.')
    if p.get('max_power_time_min',0):
        low, high = (.15,4) if p['engine_type']=='jet' else (80,1000)
        if not low <= p['max_power_sfc'] <= high:
            raise ValueError(f'SFC fazy zadaniowej: dla tego napędu wymagany zakres {low}–{high} w jednostkach formularza.')
    for key in ('graph_source','mass_law_source','sketch_reference','mission_approval_reference'):
        if key in p and (not isinstance(p[key],str) or len(p[key])>4000):
            raise ValueError(f'{key}: wymagany tekst do 4000 znaków.')
    if p.get('outbound_range_km') is not None:
        p['range_km'] = p['outbound_range_km']+p.get('return_range_km',0)
    if p.get('return_range_km',0)>p['range_km']:
        raise ValueError('Powrót musi mieścić się w całkowitym zasięgu misji.')
    if p.get('climb_start_altitude_m',0)>p['cruise_altitude_m']:
        raise ValueError('Wysokość końcowa wznoszenia musi być nie mniejsza niż początkowa.')


def interpolate(points, x, logarithmic=False):
    if not math.isfinite(x) or not points[0][0] <= x <= points[-1][0]:
        raise ValueError(f'Odczyt poza zakresem wykresu: {x:.3g}; zakres {points[0][0]}–{points[-1][0]}. Podaj udokumentowany odczyt ręczny.')
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        if xa <= x <= xb:
            t = math.log(x/xa)/math.log(xb/xa) if logarithmic else (x-xa)/(xb-xa)
            return ya + t*(yb-ya)
    return points[-1][1]


def preliminary_polar(p):
    mode = p.get('preliminary_polar_mode', 'input')
    ar, e = p.get('aspect_ratio', 8), p.get('oswald_e', .8)
    if mode == 'raymer':
        ratio = p['sketch_swet_ratio']
        kmax = interpolate(RAYMER[p['raymer_family']], ar/ratio)
        cx0 = math.pi*ar*e/(4*kmax*kmax)
    elif mode == 'reading':
        ratio, kmax = p['sketch_swet_ratio'], p['raymer_kmax']
        cx0 = math.pi*ar*e/(4*kmax*kmax)
    else:
        ratio, cx0 = None, p.get('cx0', .025)
        # Existing aerodynamic input is a preliminary estimate, not a graph reading.
        if not p.get('preliminary_polar_includes_configuration'):
            cx0 += .002 if p.get('wing_config') == 'braced_high' else 0
            cx0 += .0025 if p.get('flap_type') == 'junkers' else 0
            cx0 += .003 if p.get('slat_type') == 'fixed_slot' else 0
        kmax = .5*math.sqrt(math.pi*ar*e/cx0)
    from calculations.preliminary import classify_bipol_cx0
    inferred_class = classify_bipol_cx0(p)
    inferred_class = {'combat':'military','large_transport':'transport'}.get(inferred_class,inferred_class)
    bounds = CX0_RANGES[p.get('cx0_reference_class', inferred_class)]
    return dict(mode=mode, kmax=kmax, cx0=cx0, swet_ratio=ratio, aspect_ratio=ar, oswald_e=e,
                wetted_aspect_ratio=ar/ratio if ratio else None,
                cx0_bounds=list(bounds), cx0_in_range=bounds[0] <= cx0 <= bounds[1],
                source='BIPOL_1.pdf, s. 2–3, rys. 1–2 i wzór (3)',
                reading_note='Przybliżony odczyt graficzny; interpolacja odcinkowa bez ekstrapolacji.' if mode == 'raymer' else p.get('graph_source', ''))


def empty_mass_law(p):
    mode = p.get('empty_mass_model', 'class_correlation')
    if p.get('empty_mass_fraction') is not None and mode == 'class_correlation' and p.get('empty_mass_trend_A') is None:
        mode = 'fixed_fraction'
    kvs = 1.04 if p.get('variable_sweep', False) else 1.
    meta = dict(mode=mode, unit='kg', k_vs=kvs, source='BIPOL_1.pdf, s. 1, wzór (1)')
    if p.get('empty_mass_trend_A') is not None and mode == 'class_correlation':
        a, c = p['empty_mass_trend_A'], p['empty_mass_trend_C']
        mode = 'bipol1_trend'
        meta['mode'] = mode
    elif mode == 'trend':
        from calculations.trends import select_references, fit_regression
        rows = select_references(p, p.get('mass_initial_guess', 5000))
        rows = [r for r in rows if r.get('empty_fraction') and .15 < r['empty_fraction'] < .95]
        counts = Counter(r['family'] for r in rows)
        weights = [1/counts[r['family']] if p.get('trend_weighting', 'family') == 'family' else 1 for r in rows]
        fit = fit_regression([(r['m0'], r['empty_fraction']/(1.04 if r.get('variable_sweep') else 1)) for r in rows], weights, power=True)
        if not fit:
            raise ValueError('Masa pusta z trendu: potrzeba co najmniej 3 kompletnych konstrukcji o różnych masach. Uzupełnij dobór samolotów.')
        a, c = fit['A'], fit['C']
        meta.update(n=len(rows), families=len(counts), aircraft_ids=[r['id'] for r in rows],
                    valid_range=[fit['x_min'], fit['x_max']], definitions=sorted({r.get('empty_mass_definition') or 'nieokreślona' for r in rows}))
    elif mode == 'two_point':
        x1, x2, y1, y2 = (p[k] for k in ('mass_point_x1','mass_point_x2','mass_point_y1','mass_point_y2'))
        if x1 == x2:
            raise ValueError('Dwa punkty korelacji muszą mieć różne masy startowe.')
        c = math.log(y1/y2)/math.log(x1/x2)
        a = y1/x1**c
        meta['valid_range'] = sorted([x1,x2])
    elif mode == 'coefficients':
        a, c = p['empty_mass_a'], p['empty_mass_c']
    elif mode == 'fixed_fraction':
        a, c, kvs = p['empty_mass_fraction'], 0., 1.
    else:
        # Retained for existing projects; explicitly marked provisional in review.
        a, c = {'glider':(.82,-.05),'motoglider':(.86,-.05),'piston_ga':(.92,-.06),
                'turboprop_regional':(.96,-.05),'jet_business':(1.02,-.06),
                'jet_transport':(.95,-.05),'uav':(.82,-.04)}[p.get('aircraft_type','piston_ga')]
        from calculations.polish_law import resolve_category, SUBCATEGORIES
        basis = SUBCATEGORIES[resolve_category(p.get('category','normal'))]['load_basis']
        mod = (.972 if p.get('wing_config') == 'braced_high' else 1)
        mod *= 1.045 if basis == 'cs23_aerobatic' else 1.018 if basis in ('cs23_utility','cs22_utility') else 1
        mod *= 1 + .006*max(0, p.get('aspect_ratio',8)-9)
        mod *= 1.012 if p.get('flap_type') in ('fowler','double_slotted') else 1
        meta.update(structural_modifier=mod, source='Korelacja klasy; do zastąpienia analizą własnej próby.')
    meta.update(A=a, C=c, k_vs=kvs)

    def share(m):
        if m <= 0 or not math.isfinite(m):
            raise ValueError('Iteracja masy wymaga dodatniej, skończonej masy startowej.')
        try:
            value = a*m**c*kvs
        except OverflowError:
            return math.inf
        if mode == 'class_correlation':
            value = min(.74, max(.38, value*meta['structural_modifier']))
        return value
    return share, meta


def mission_model(p, kmax):
    engine = p.get('engine_type','prop')
    powered = engine != 'none' and p.get('aircraft_type') != 'glider'
    speed = p.get('cruise_speed_kmh',250)/3.6
    eta = p.get('prop_efficiency',.82)
    ld = kmax*p.get('mission_ld_factor',.94)
    sfc = p.get('sfc', .62 if engine == 'jet' else 265)
    # Jet input 1/h is TSFC*g. Prop input g/kWh becomes kg/Ws.
    ct = sfc/3600 if engine == 'jet' else 0
    cp = sfc/3.6e9 if engine == 'prop' else 0
    reserve = p.get('fuel_reserve_factor',1.06)
    drop = p.get('payload_drop_kg',0)
    method = p.get('mass_method','auto')
    method = ('iterative' if drop else 'proportions') if method == 'auto' else method
    if method == 'proportion':
        method = 'proportions'
    if method == 'proportions' and drop:
        raise ValueError('Metoda proporcji dotyczy misji bez zrzutu. Wybierz metodę iteracyjną lub automatyczną.')
    corke = {}
    if powered:
        h0, h1 = p.get('climb_start_altitude_m',0), p.get('cruise_altitude_m',3000)
        v0 = p.get('climb_start_speed_kmh',p.get('cruise_speed_kmh',250))/3.6
        mach0, mach1 = v0/isa_atmosphere(h0)['a'], speed/isa_atmosphere(h1)['a']
        mode = p.get('climb_fraction_mode','auto')
        if mode == 'auto' and min(mach0,mach1)<CORKE[0][0]:
            # Existing slow aircraft remain calculable, but this is NOT Corke
            # and the coursework checklist explicitly rejects the fallback.
            q0,q1 = 1., .988 if engine=='prop' else .978
            mode = 'provisional'
        elif mode == 'reading':
            q0, q1 = p['corke_start_ordinate'], p['corke_end_ordinate']
        else:
            q0, q1 = interpolate(CORKE,mach0,True), interpolate(CORKE,mach1,True)
        if q1 > q0 + 1e-12:
            raise ValueError('Wykres Corke’a daje wzrost masy. Sprawdź prędkości, wysokości i odczyty wznoszenia.')
        climb = q1/q0
        corke = dict(mach_start=mach0,mach_end=mach1,ordinate_start=q0,ordinate_end=q1,
                     fraction=climb,source='BIPOL_1.pdf, s. 4–5, rys. 3 (oś M logarytmiczna)',
                     mode=mode, provisional=mode=='provisional')
    else:
        climb = 1.
    scale = (speed/ct if engine == 'jet' else eta/(cp*G0)) * ld if powered else math.inf
    distance = p.get('range_km',1200)
    back = p.get('return_range_km',0)
    if p.get('outbound_range_km') is not None:
        distance = p['outbound_range_km']+back
    if back > distance:
        raise ValueError('Odcinek powrotny nie może być dłuższy niż całkowity zasięg misji.')
    coupled = p.get('design_iteration_mode') == 'coupled' and bool(p.get('_mission_polar')) and powered
    def cruise(km, mass=None, takeoff_mass=None):
        if coupled and mass is not None:
            from calculations.mission_cruise import mass_after_cruise
            # A 0.1% explicit route margin avoids presenting rounding as compliance.
            polar = dict(p['_mission_polar'])
            if p.get('wing_input_mode') == 'loading':
                polar['S'] *= takeoff_mass / polar['reference_mass_kg']
            end = mass_after_cruise(mass, km * 1000 * 1.001, p, polar)
            return end / mass if end is not None else 0.0
        return math.exp(-km*1000/scale) if powered else 1.
    loiter_speed = p.get('loiter_speed_kmh',p.get('cruise_speed_kmh',250))/3.6
    # p. 6 is not superseded by the lecture's CRUISE-only factor .94.
    loiter = math.exp(-p.get('loiter_time_min',45)*60 * (ct if engine == 'jet' else loiter_speed*cp*G0/eta)/(.8*kmax)) if powered else 1.
    task_time = p.get('max_power_time_min',0)/60
    task_fuel = 0.
    if powered and task_time:
        max_sfc = p['max_power_sfc']
        task_fuel = (max_sfc/G0*1000*p['max_thrust_kn'] if engine == 'jet' else max_sfc/1000*p['max_power_kw'])*task_time
    factors = {'warmup':1.,'takeoff':p.get('takeoff_mass_fraction',.975) if powered else 1.,
               'climb':climb,'cruise':cruise(distance),'descent':1.,'loiter':loiter,
               'landing':p.get('landing_mass_fraction',.975) if powered else 1.}
    factors['total_mff'] = math.prod(factors.values())

    def simulate(m0):
        current, fuel_burn = m0, 0.
        phases = []
        def phase(key,label,fraction=1.,burn=0.,release=0.):
            nonlocal current, fuel_burn
            start = current
            fuel = start*(1-fraction) + burn
            current = start - fuel - release
            fuel_burn += fuel
            phases.append(dict(key=key,phase=label,mass_start_kg=start,mass_end_kg=current,
                               fuel_burn_kg=fuel,payload_drop_kg=release,
                               fraction=current/start if start > 0 else 0.,
                               fuel_fraction=1-fuel/start if start > 0 else 0.))
        phase('warmup','Rozruch (uwzględniony w starcie)')
        phase('takeoff','Start i kołowanie',factors['takeoff'])
        phase('climb','Wznoszenie i rozpędzanie',climb)
        phase('cruise','Lot do celu' if back or drop else 'Przelot',cruise(distance-back,current,m0))
        if task_time:
            phase('task','Zadanie przy maksymalnym ciągu / mocy',burn=task_fuel)
        if drop:
            phase('drop','Zrzut ładunku',release=drop)
        if back:
            phase('return','Lot powrotny',cruise(back,current,m0))
        phase('descent','Zniżanie (bez osobnego narzutu paliwa)')
        phase('loiter','Krążenie / patrol',loiter)
        phase('landing','Lądowanie i kołowanie',factors['landing'])
        if coupled:
            factors['cruise'] = math.prod(s['fuel_fraction'] for s in phases if s['key'] in ('cruise', 'return'))
            factors['total_mff'] = math.prod(factors[key] for key in ('warmup','takeoff','climb','cruise','descent','loiter','landing'))
        return dict(phases=phases,landing_mass=current,burn=fuel_burn,
                    fuel=reserve*fuel_burn,reserve=(reserve-1)*fuel_burn)
    return simulate, dict(method=method,corke=corke,factors=factors,range_scale=scale,
                         ld=ld,loiter_ld=.8*kmax,loiter_speed_kmh=loiter_speed*3.6,
                         task_fuel=task_fuel,reserve=reserve,drop=drop)


def solve_mass(p, payload, crew):
    polar = preliminary_polar(p)
    share, law = empty_mass_law(p)
    simulate, mission = mission_model(p,polar['kmax'])
    drop = mission['drop']
    if drop > p.get('m_cargo',0) or drop > payload:
        raise ValueError('Zrzut nie może przekraczać masy cargo; pasażerowie i załoga pozostają na pokładzie.')
    useful = payload+crew
    if useful <= 0:
        raise ValueError('Do wyznaczenia MTOW podaj dodatnią masę załogi lub ładunku.')
    def evaluate(m):
        flight = simulate(m)
        me = m*share(m)
        # Empty mass inferred at landing, with remaining load and fuel removed.
        inferred = flight['landing_mass']-(payload-drop)-crew-flight['reserve']
        residual = inferred-me if mission['method']=='iterative' else m-me-useful-flight['fuel']
        return residual, me, inferred, flight
    # First physical sign crossing: do not clamp invalid extrapolated mass laws.
    low = useful
    previous = evaluate(low)[0]
    high = low
    for _ in range(500):
        high *= 1.08
        residual, me, inferred, flight = evaluate(high)
        if previous <= 0 <= residual and 0 < me < high and all(s['mass_end_kg'] > 0 for s in flight['phases']):
            break
        low, previous = high, residual
        if high > 1e9:
            raise ValueError('Równanie (1) nie daje fizycznego rozwiązania bilansu; sprawdź dobór próby (oczekiwane C < 0), zakres mas i misję.')
    else:
        raise ValueError('Nie znaleziono przedziału rozwiązania bilansu masy.')
    history = []
    for i in range(100):
        # Safeguarded secant for the payload-drop iteration (p. 4 suggestion).
        a, b = evaluate(low)[0], evaluate(high)[0]
        candidate = low-a*(high-low)/(b-a) if mission['method']=='iterative' and b != a else (low+high)/2
        m0 = candidate if low+.1*(high-low) < candidate < high-.1*(high-low) else (low+high)/2
        residual, me, inferred, flight = evaluate(m0)
        relative = abs(inferred-me)/me
        history.append(dict(iter=i+1,m0=m0,empty_fraction=me/m0,diff=abs(residual),
                            m_empty_correlation=me,m_empty_from_mission=inferred,relative_error=relative))
        if i >= 4 and abs(residual) < .0001 and relative <= .001:
            break
        if residual > 0:
            high=m0
        else:
            low=m0
    else:
        raise ValueError('Bilans masy nie osiągnął zbieżności; wynik nie został przyjęty.')
    if not 0 < me < m0 or flight['fuel'] < 0 or flight['reserve'] < 0:
        raise ValueError('Niefizyczny bilans masy.')
    law['extrapolated'] = 'valid_range' in law and not law['valid_range'][0] <= m0 <= law['valid_range'][1]
    # Keep numerical mass precision between modules; round only in UI/reports.
    result = dict(m0=m0,m_empty=me,m_fuel=flight['fuel'],
                  m_payload=payload,m_crew=crew,m_zfw=me+useful,
                  m_payload_landing=payload-drop,m_payload_dropped=drop,
                  empty_fraction=round(me/m0,4),fuel_fraction=round(flight['fuel']/m0,4),
                  payload_fraction=round(payload/m0,4),empty_mass_model=law['mode'],empty_mass_law=law,
                  ld_cruise_used=round(mission['ld'],2),iterations=history,mission_phases=flight['phases'],
                  fuel_burn_kg=flight['burn'],reserve_fuel_kg=flight['reserve'],preliminary_polar=polar,
                  fuel_fractions_detail=mission['factors'],mass_method=mission['method'],
                  mission_assumptions=dict(phase_model='galinski',reserve_factor=mission['reserve'],
                    cruise_model='constant_tas_altitude' if p.get('_mission_polar') else 'preliminary_ld',
                    cruise_route_margin=1.001 if p.get('_mission_polar') else 1.0,
                    ld_factor=p.get('mission_ld_factor',.94),k_max_preliminary=polar['kmax'],
                    mass_residual_relative=abs(m0-me-useful-flight['fuel'])/m0,
                    empty_mass_residual_relative=relative,corke=mission['corke'],
                    loiter_ld=mission['loiter_ld'],loiter_speed_kmh=mission['loiter_speed_kmh'],
                    source='BIPOL_1.pdf, s. 1–6; notatka IMG20261021122751 (przelot 0,94 Kmax)',
                    note='Metoda iteracyjna: oddzielny bilans paliwa i zrzutu.' if mission['method']=='iterative' else 'Metoda proporcji: bez zrzutu ładunku.'))
    # Phase-dependent fractions exclude payload release from fuel consumption.
    if mission['task_fuel']:
        task = next(s for s in flight['phases'] if s['key']=='task')
        result['fuel_fractions_detail']['task'] = task['fuel_fraction']
        result['fuel_fractions_detail']['total_mff'] *= task['fuel_fraction']
    result['payload_range'] = []
    if p.get('_mission_polar'):
        used = dict(p['_mission_polar'])
        if p.get('wing_input_mode') == 'loading':
            used['S'] *= m0 / used['reference_mass_kg']
        result['mission_assumptions']['cruise_polar'] = used
        result['payload_range_note'] = 'Analiza ładunek–zasięg wymaga ponownego całkowania przy zachowanej pojemności paliwa; nie użyto uproszczenia stałego K.'
    n = int(p.get('n_pax',0))
    if n and math.isfinite(mission['range_scale']) and not drop and not mission['task_fuel'] and not p.get('_mission_polar'):
        other = mission['factors']['total_mff']/mission['factors']['cruise']
        for count in sorted({n,max(0,n-1),n//2,0},reverse=True):
            load = count*(p.get('m_pax',80)+p.get('m_bag',0))+p.get('m_cargo',0)
            fuel = m0-me-crew-load
            fraction = (1-fuel/(m0*mission['reserve']))/other
            distance = -mission['range_scale']*math.log(fraction)/1000 if 0 < fraction <= 1 else None
            result['payload_range'].append(dict(passengers=count,payload_kg=round(load,1),fuel_kg=round(fuel,1),range_km=round(distance,1) if distance is not None else None))
    return result


def review_bipol1(result):
    """Completeness of THIS project, separate from implemented capabilities."""
    p, mass = result['params'],result['mass']
    trends = result['bipol_projects']['p1']['trend_analysis']
    law, polar = mass['empty_mass_law'],mass['preliminary_polar']
    checks = []
    def add(key,label,passed,detail):
        checks.append(dict(key=key,label=label,passed=bool(passed),detail=detail))
    add('sample','Próba porównawcza: minimum 8 rodzin, cel PDF 20 konstrukcji',
        trends['families_n']>=8,
        f"{trends['families_n']} rodzin / {trends['selected_n']} wariantów. Notatki zmieniają minimum na 8; pokazujemy także cel 20 z PDF.")
    add('dates','Udokumentowane daty i prognozy +5 lat',
        any(t['fit'] and t['available_n']>=8 for t in trends['time_trends']),trends['year_basis'])
    from calculations.trends import BIPOL_1_AVERAGES
    missing = [k for k in BIPOL_1_AVERAGES if not trends['averages'][k]['n']]
    add('averages','Osiem średnich z analizy trendów',not missing,
        'Brak danych: '+', '.join(missing) if missing else 'Wszystkie osiem wielkości ma obserwacje.')
    add('mass_law','Masa pusta z równania (1) własnej próby',
        law['mode'] in ('trend','coefficients','two_point','bipol1_trend') and bool(p.get('mass_law_source') or law.get('aircraft_ids')),
        f"Model: {law['mode']}; A={law['A']:.6g}, C={law['C']:.6g}, Kvs={law['k_vs']}; m₀ w kg. "+
        ('Wynik poza zakresem mas próby.' if law['extrapolated'] else 'Zapisz źródło współczynników i definicję masy pustej.'))
    add('sketch','Szkic odręczny uzgodniony z prowadzącym',bool(p.get('sketch_reference','').strip()),
        p.get('sketch_reference') or 'Podaj odniesienie do własnego szkicu; widok 3D go nie zastępuje.')
    add('mission','Uzgodniona misja i wymagania osiągowe',bool(p.get('mission_approval_reference','').strip()),
        p.get('mission_approval_reference') or 'Podaj odniesienie do uzgodnienia misji i wymagań.')
    add('raymer','Swet/S ze szkicu → Kmax z Raymera → Cx₀',polar['mode'] in ('raymer','reading') and bool(p.get('graph_source','').strip()),
        f"Metoda: {polar['mode']}; Kmax={polar['kmax']:.3f}, Cx₀={polar['cx0']:.5f}. Odczyty wykresów mają dokładność graficzną.")
    add('cx0','Cx₀ względem tabeli siedmiu klas',polar['cx0_in_range'],
        f"Cx₀={polar['cx0']:.5f}; przedział {polar['cx0_bounds'][0]}–{polar['cx0_bounds'][1]}. Odchylenie wymaga uzasadnienia, nie automatycznej korekty.")
    if p['engine_type']!='none':
        corke=mass['mission_assumptions']['corke']
        add('corke','Wznoszenie: iloraz odczytów Corke’a',not corke.get('provisional') and
            (corke['mode']!='reading' or bool(p.get('graph_source','').strip())),
            f"Mₚ={corke['mach_start']:.4f}, Mₘ={corke['mach_end']:.4f}, m₂/m₁={corke['fraction']:.6f}. "+
            ('Poza wykresem: przybliżenie robocze wymaga odczytu źródłowego.' if corke.get('provisional') else corke['source']))
    add('mass','Obie oceny masy pustej zgodne do 0,1%',mass['mission_assumptions']['empty_mass_residual_relative']<=.001,
        f"Metoda: {mass['mass_method']}; {len(mass['iterations'])} iteracji; różnica {100*mass['mission_assumptions']['empty_mass_residual_relative']:.6f}%.")
    add('reserve','Rezerwa i paliwo nieużywalne według wzoru (4)',
        abs(mass['mission_assumptions']['reserve_factor']-1.06)<1e-12,
        f"Współczynnik {mass['mission_assumptions']['reserve_factor']}; PDF wymaga 1,06. Krążenie liczone osobno.")
    required = [c for c in result['instructor_review']['checks'] if c['key'] in ('charts','mass_trend','iteration','cruise','start_fraction')]
    add('notes','Komplet wykresów i wymagania obliczeniowe z notatek',all(c['passed'] for c in required),
        '; '.join(c['label'] for c in required if not c['passed']) or 'Kontrole prowadzącego spełnione.')
    return dict(checks=checks,passed=sum(c['passed'] for c in checks),total=len(checks),
                complete=all(c['passed'] for c in checks),
                basis='BIPOL_1.pdf + późniejsze notatki: przelot 0,94 Kmax; krążenie 0,8 Kmax; minimum 8 rodzin, cel PDF 20 konstrukcji.')
