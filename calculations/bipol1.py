"""BIPOL_1, pp. 1–6: graph readings, empty-mass law and mission balance.

Graph samples are approximate readings of the supplied PDF, not empirical
equations with invented precision. Interpolation never extrapolates a graph.
Masses are kg; distances m; speeds TAS m/s; time s.
"""
import math
from collections import Counter

from calculations import aircraft_store
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
# Fig. 1, p. 2: S_wet/S_ref of the example aircraft — stored in the comparison-aircraft
# database (table wetted_area_examples), never in the code.
WETTED_EXAMPLES = {key: (row['label'], row['swet_ratio'])
                   for key, row in aircraft_store.wetted_area_examples().items()}
RAYMER_LABELS = {
    'glider': 'szybowce', 'military_supersonic': 'samoloty bojowe w locie naddźwiękowym',
    'military_subsonic': 'samoloty bojowe w locie poddźwiękowym', 'jet': 'cywilne samoloty odrzutowe',
    'prop_retractable': 'samoloty śmigłowe z podwoziem chowanym', 'prop_fixed': 'samoloty śmigłowe z podwoziem stałym',
}
CX0_RANGES = {
    'military': (.014,.020), 'transport': (.018,.024), 'small_twin': (.022,.028),
    'single_retractable': (.020,.030), 'single_fixed': (.025,.040),
    'agricultural': (.060,.080), 'motoglider': (.014,.020),
}
CX0_LABELS = {'military': 'samoloty bojowe', 'transport': 'duże samoloty transportowe',
              'small_twin': 'małe samoloty dwusilnikowe', 'single_retractable': 'jednosilnikowe z podwoziem chowanym',
              'single_fixed': 'jednosilnikowe z podwoziem stałym', 'agricultural': 'samoloty rolnicze',
              'motoglider': 'motoszybowce'}



def two_point_power_law(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """Wyznacza współczynniki A i C zależności m_e/m_0 = A * m_0^C z dwóch punktów (x1, y1) i (x2, y2)."""
    if x1 <= 0 or x2 <= 0 or y1 <= 0 or y2 <= 0:
        raise ValueError("Współrzędne punktów korelacji potęgowej muszą być dodatnie.")
    if x1 == x2:
        raise ValueError("Dwa punkty korelacji muszą mieć różne masy startowe.")
    c = math.log(y1 / y2) / math.log(x1 / x2)
    a = y1 / (x1 ** c)
    return a, c




def validate_bipol1(p):
    options = {
        'mass_method': ('auto','proportion','proportions','iterative'),
        'empty_mass_model': ('trend','two_point'),
        'preliminary_polar_mode': ('input','raymer','reading'),
        'raymer_family': tuple(RAYMER), 'cx0_reference_class': ('', *CX0_RANGES),
        'wetted_example': ('', 'sketch', *WETTED_EXAMPLES),
        'climb_fraction_mode': ('auto','corke','reading'),
        'trend_year_basis': ('production','certification'),
        'design_iteration_mode': ('preliminary', 'coupled'),
    }
    for key, allowed in options.items():
        if key in p and p[key] not in allowed:
            raise ValueError(f'Nieznana opcja {key}.')
    requirements = []
    mode = p.get('empty_mass_model')
    requirements += {'two_point':['mass_point_x1','mass_point_x2','mass_point_y1','mass_point_y2']}.get(mode,[])
    if p.get('preliminary_polar_mode') in ('raymer','reading') and p.get('wetted_example') == 'sketch':
        requirements += ['sketch_swet_ratio']
    if p.get('preliminary_polar_mode') == 'reading':
        requirements += ['raymer_kmax']
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


def wetted_example(p):
    """Fig. 1 example closest to the class sketch; the student may measure the sketch instead."""
    chosen = p.get('wetted_example')
    if chosen:
        return chosen
    ac_type = p.get('aircraft_type', 'piston_ga')
    if ac_type in ('glider', 'motoglider'):
        return 'glider'
    if ac_type == 'jet_transport':
        return 'jet_transport'
    if ac_type in ('turboprop_regional', 'jet_business') or int(p.get('n_engines', 1) or 1) >= 2:
        return 'twin_turboprop'
    return 'light_single'


def raymer_family(p):
    """Curve of Fig. 2 for the kind of aircraft (legend of the figure)."""
    if p.get('aircraft_type') in ('glider', 'motoglider') or p.get('engine_type') == 'none':
        return 'glider'
    if p.get('engine_type') == 'jet':
        return 'jet'
    from calculations.paturski_ml import default_retractable_gear
    return 'prop_retractable' if default_retractable_gear(p) else 'prop_fixed'


def read_raymer(family, wetted_aspect):
    """K_max from Fig. 2. Outside the printed curve K_max follows K ∝ √Λ_wet from its nearest
    end, the shape of Raymer's curves at a constant equivalent skin friction; such a reading is flagged."""
    points = RAYMER[family]
    (x_lo, y_lo), (x_hi, y_hi) = points[0], points[-1]
    if x_lo <= wetted_aspect <= x_hi:
        return interpolate(points, wetted_aspect), False
    x_end, y_end = (x_lo, y_lo) if wetted_aspect < x_lo else (x_hi, y_hi)
    return y_end * math.sqrt(wetted_aspect / x_end), True


def preliminary_polar(p):
    mode = p.get('preliminary_polar_mode', 'raymer')
    ar, e = p.get('aspect_ratio', 8), p.get('oswald_e', .8)
    example = family = None
    extrapolated = False
    if mode in ('raymer', 'reading'):
        example = wetted_example(p)
        ratio = p['sketch_swet_ratio'] if example == 'sketch' else WETTED_EXAMPLES[example][1]
        family = raymer_family(p)
        if mode == 'raymer':
            kmax, extrapolated = read_raymer(family, ar/ratio)
        else:
            kmax = p['raymer_kmax']
        cx0 = math.pi*ar*e/(4*kmax*kmax)
    else:
        # Next design iteration: C_x0 of the P4 polar replaces the graph estimate.
        ratio, cx0 = None, p.get('cx0', .025)
        if not p.get('preliminary_polar_includes_configuration'):
            cx0 += .002 if p.get('wing_config') == 'braced_high' else 0
            cx0 += .0025 if p.get('flap_type') == 'junkers' else 0
            cx0 += .003 if p.get('slat_type') == 'fixed_slot' else 0
        kmax = .5*math.sqrt(math.pi*ar*e/cx0)
    from calculations.preliminary import classify_bipol_cx0
    inferred_class = classify_bipol_cx0(p)
    inferred_class = {'combat':'military','large_transport':'transport'}.get(inferred_class,inferred_class)
    cx0_class = p.get('cx0_reference_class') or inferred_class
    bounds = CX0_RANGES[cx0_class]
    curve = RAYMER[family] if family else None
    return dict(mode=mode, kmax=kmax, cx0=cx0, swet_ratio=ratio, aspect_ratio=ar, oswald_e=e,
                wetted_aspect_ratio=ar/ratio if ratio else None,
                wetted_example=example, wetted_example_label=WETTED_EXAMPLES[example][0] if example in WETTED_EXAMPLES else None,
                raymer_family=family, raymer_family_label=RAYMER_LABELS.get(family),
                raymer_range=[curve[0][0], curve[-1][0]] if curve else None, extrapolated=extrapolated,
                cx0_class=cx0_class, cx0_bounds=list(bounds), cx0_in_range=bounds[0] <= cx0 <= bounds[1],
                cx0_deviation=(cx0 - bounds[0]) / bounds[0] if cx0 < bounds[0] else (cx0 - bounds[1]) / bounds[1] if cx0 > bounds[1] else 0.,
                source=(p.get('graph_source') or 'Podany C_D0 całego samolotu w konfiguracji gładkiej') if mode == 'input'
                       else 'BIPOL_1.pdf, s. 2–3, rys. 1–2 i wzór (3)',
                reading_note=('Odczyt poza narysowaną krzywą: K ∝ √Λ_wet od końca krzywej.' if extrapolated else
                              'Przybliżony odczyt graficzny; interpolacja odcinkowa.') if mode == 'raymer' else p.get('graph_source', ''))


def empty_mass_law(p):
    """BIPOL_1, wzór (1): mₑ/m₀ = A·m₀^C·K_vs. A i C wynikają z dwóch punktów linii trendu
    mₑ/m₀ = f(m₀) analizy trendów (odczyt programu) albo z dwóch punktów odczytanych przez autora."""
    mode = p.get('empty_mass_model', 'trend')
    kvs = 1.04 if p.get('variable_sweep', False) else 1.
    meta = dict(mode=mode, unit='kg', k_vs=kvs, source='BIPOL_1.pdf, s. 1, wzór (1)')
    if mode == 'two_point':
        x1, x2, y1, y2 = (p[k] for k in ('mass_point_x1','mass_point_x2','mass_point_y1','mass_point_y2'))
        a, c = two_point_power_law(x1, y1, x2, y2)
        meta['valid_range'] = sorted([x1,x2])
    else:
        from calculations.trends import empty_mass_trend
        rows, fit, points = empty_mass_trend(p)
        if not fit:
            raise ValueError('Równanie (1): linia trendu mₑ/m₀ = f(m₀) wymaga co najmniej 3 konstrukcji próby o różnych masach. '
                             'Poszerz próbę porównawczą albo odczytaj dwa punkty z wykresu.')
        a, c = points['A'], points['C']
        counts = Counter(r['family'] for r in rows)
        meta.update(mode='trend', n=len(rows), families=len(counts), aircraft_ids=[r['id'] for r in rows], points=points,
                    r2=fit['r2'], valid_range=[fit['x_min'], fit['x_max']],
                    definitions=sorted({r.get('empty_mass_definition') or 'nieokreślona' for r in rows}))
        constrained=bool(fit.get('physically_constrained'))
        meta.update(constrained=constrained,raw_exponent=fit.get('c_unconstrained',fit['C']),
                    unconstrained_r2=fit.get('r2_unconstrained',fit['r2']),
                    exponent_basis='declared_class_prior' if constrained else 'empirical_power_fit')
    meta.update(A=a, C=c, k_vs=kvs)

    def share(m):
        if m <= 0 or not math.isfinite(m):
            raise ValueError('Iteracja masy wymaga dodatniej, skończonej masy startowej.')
        try:
            return a*m**c*kvs
        except OverflowError:
            return math.inf
    return share, meta


def refined_cruise_ld(p):
    """K at the required cruise from the P4 polar, valid only for the speed and altitude it was found at."""
    ld = p.get('cruise_ld_p4')
    basis = (p.get('cruise_ld_p4_speed_kmh'), p.get('cruise_ld_p4_altitude_m'))
    if not ld or None in basis:
        return None
    same = (abs(basis[0] - p.get('cruise_speed_kmh', 250)) < .05
            and abs(basis[1] - p.get('cruise_altitude_m', 3000)) < .5)
    return float(ld) if same else None


def cruise_ld_from_range(p, range_km, m_start, m_end):
    """Mean L/D that makes Breguet's equation reproduce a cruise flown at constant speed and altitude."""
    speed = p.get('cruise_speed_kmh', 250)/3.6
    sfc = p.get('sfc', .62 if p.get('engine_type') == 'jet' else 265)
    per_ld = speed/(sfc/3600) if p.get('engine_type') == 'jet' else p.get('prop_efficiency', .82)/(sfc/3.6e9*G0)
    return range_km*1000/(per_ld*math.log(m_start/m_end))


def mission_model(p, kmax):
    engine = p.get('engine_type','prop')
    powered = engine != 'none' and p.get('aircraft_type') != 'glider'
    speed = p.get('cruise_speed_kmh',250)/3.6
    eta = p.get('prop_efficiency',.82)
    # First estimate per the course guideline; refined sizing uses the P4 polar at the required cruise.
    ld = refined_cruise_ld(p) or kmax*p.get('mission_ld_factor',.94)
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
        below = False
        if mode == 'reading':
            q0, q1 = p['corke_start_ordinate'], p['corke_end_ordinate']
        else:
            # Fig. 3 starts at M = 0,1 with W/W(M = 0,1) = 1: a slower state reads the start of the chart.
            below = min(mach0, mach1) < CORKE[0][0]
            q0, q1 = (interpolate(CORKE, max(m, CORKE[0][0]), True) for m in (mach0, mach1))
            mode = 'corke'
        if q1 > q0 + 1e-12:
            raise ValueError('Wykres Corke’a daje wzrost masy. Sprawdź prędkości, wysokości i odczyty wznoszenia.')
        climb = q1/q0
        corke = dict(mach_start=mach0,mach_end=mach1,ordinate_start=q0,ordinate_end=q1,
                     fraction=climb,source='BIPOL_1.pdf, s. 4–5, rys. 3 (oś M logarytmiczna)',
                     mode=mode, below_chart=below, provisional=False)
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
    warmup_frac = p.get('warmup_mass_fraction', 1.) if powered else 1.
    takeoff_frac = p.get('takeoff_mass_fraction', .975) if powered else 1.
    taxi_frac = p.get('taxi_mass_fraction')
    factors = {'warmup': warmup_frac, 'takeoff': takeoff_frac,
               'climb': climb, 'cruise': cruise(distance), 'descent': 1., 'loiter': loiter,
               'landing': p.get('landing_mass_fraction', .975) if powered else 1.}
    if taxi_frac is not None and powered:
        factors['taxi'] = float(taxi_frac)
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
        phase('warmup', 'Rozruch (uwzględniony w starcie)' if factors['warmup'] == 1. else 'Rozruch silnika', factors['warmup'])
        if 'taxi' in factors:
            phase('taxi', 'Kołowanie', factors['taxi'])
        phase('takeoff', 'Start i kołowanie' if 'taxi' not in factors else 'Start (oderwanie i wzniesienie)', factors['takeoff'])
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
            keys = ['warmup', 'takeoff', 'climb', 'cruise', 'descent', 'loiter', 'landing']
            if 'taxi' in factors:
                keys.insert(1, 'taxi')
            factors['total_mff'] = math.prod(factors[key] for key in keys if key in factors)
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
    # Numerical model domain, not an airworthiness limit: do not seek a new
    # aircraft class many orders of magnitude beyond the calibration sample.
    # Even one decade of extrapolation needs independent engineering evidence.
    maximum_search_mass = min(1e9, 10 * law['valid_range'][1])
    domain_error = ('Równanie (1) nie daje fizycznego rozwiązania bilansu w zakresie modelu; '
                    'poszukiwanie ograniczono do dziesięciokrotności górnej masy próby. '
                    'Zmień misję lub dobierz reprezentatywne konstrukcje; nie ekstrapoluj prawa masy do innej klasy samolotu.')
    if law['C'] >= 0:
        domain_error += ' Sprawdź również założenie malejącego udziału masy pustej (C < 0).'
    if useful >= maximum_search_mass:
        raise ValueError(domain_error)
    # First physical sign crossing: do not clamp invalid extrapolated mass laws.
    low = useful
    previous = evaluate(low)[0]
    high = low
    for _ in range(500):
        high = min(high * 1.08, maximum_search_mass)
        residual, me, inferred, flight = evaluate(high)
        if previous <= 0 <= residual and 0 < me < high and all(s['mass_end_kg'] > 0 for s in flight['phases']):
            break
        low, previous = high, residual
        if high >= maximum_search_mass:
            raise ValueError(domain_error)
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
                  empty_fraction=me/m0,fuel_fraction=flight['fuel']/m0,
                  payload_fraction=payload/m0,empty_mass_model=law['mode'],empty_mass_law=law,
                  ld_cruise_used=round(mission['ld'],2),iterations=history,mission_phases=flight['phases'],
                  fuel_burn_kg=flight['burn'],reserve_fuel_kg=flight['reserve'],preliminary_polar=polar,
                  fuel_fractions_detail=mission['factors'],mass_method=mission['method'],
                  mission_assumptions=dict(phase_model='galinski',reserve_factor=mission['reserve'],
                    cruise_model='constant_tas_altitude' if p.get('_mission_polar') else 'preliminary_ld',
                    cruise_route_margin=1.001 if p.get('_mission_polar') else 1.0,
                    ld_factor=p.get('mission_ld_factor',.94),k_max_preliminary=polar['kmax'],
                    ld_source='p4_integrated' if p.get('_mission_polar') else 'p4_cruise' if refined_cruise_ld(p) else 'guideline',
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
        law['mode'] == 'trend' or law['mode'] == 'two_point' and bool(p.get('mass_law_source')),
        f"Model: {law['mode']}; A={law['A']:.6g}, C={law['C']:.6g}, Kvs={law['k_vs']}; m₀ w kg. "+
        ('Wynik poza zakresem mas próby.' if law['extrapolated'] else 'Zapisz źródło współczynników i definicję masy pustej.'))
    add('sketch','Szkic odręczny uzgodniony z prowadzącym',bool(p.get('sketch_reference','').strip()),
        p.get('sketch_reference') or 'Podaj odniesienie do własnego szkicu; widok 3D go nie zastępuje.')
    add('mission','Uzgodniona misja i wymagania osiągowe',bool(p.get('mission_approval_reference','').strip()),
        p.get('mission_approval_reference') or 'Podaj odniesienie do uzgodnienia misji i wymagań.')
    add('raymer','Swet/S ze szkicu → Kmax z Raymera → Cx₀',
        polar['mode'] == 'raymer' and not polar['extrapolated'] or polar['mode'] == 'reading' and bool(p.get('graph_source','').strip()),
        f"Metoda: {polar['mode']}; Kmax={polar['kmax']:.3f}, Cx₀={polar['cx0']:.5f}. " +
        ('Λ_wet poza narysowaną krzywą: potwierdź odczyt z prowadzącym.' if polar['extrapolated'] else 'Odczyty wykresów mają dokładność graficzną.'))
    add('cx0','Cx₀ względem tabeli siedmiu klas',polar['cx0_in_range'],
        f"Cx₀={polar['cx0']:.5f}; przedział {polar['cx0_bounds'][0]}–{polar['cx0_bounds'][1]}. Odchylenie wymaga uzasadnienia, nie automatycznej korekty.")
    if p['engine_type']!='none':
        from calculations.engine_fuel import fuel_check
        fuel = fuel_check(result['engine_selection'])
        add('engine_fuel', fuel['parameter'], fuel['passed'],
            f"{fuel['actual']}. {fuel['note']}")
        corke=mass['mission_assumptions']['corke']
        add('corke','Wznoszenie: iloraz odczytów Corke’a',not corke.get('provisional') and
            (corke['mode']!='reading' or bool(p.get('graph_source','').strip())),
            f"Mₚ={corke['mach_start']:.4f}, Mₘ={corke['mach_end']:.4f}, m₂/m₁={corke['fraction']:.6f}. "+
            corke['source'] + ('; M < 0,1 odczytano na początku wykresu (W/W₀,₁ = 1).' if corke.get('below_chart') else ''))
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


def run_mission_mass_sizing(params: dict) -> dict:
    """M1 <-> M2 interface contract: mission profiling and mass sizing.

    Returns:
        dict with keys:
          - 'm0': float
          - 'm_empty': float
          - 'm_fuel': float
          - 'fuel_fractions': list of phase dicts
          - 'iterations': int
          plus full calculation fields.
    """
    from calculations.mass import calculate_mass_sizing
    res = calculate_mass_sizing(params)
    out = dict(res)
    out.update({
        'm0': float(res['m0']),
        'm_empty': float(res['m_empty']),
        'm_fuel': float(res['m_fuel']),
        'fuel_fractions': res.get('mission_phases', []),
        'iterations': len(res.get('iterations', [])),
    })
    return out

