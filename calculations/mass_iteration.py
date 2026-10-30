"""BIPOL_1, s. 4: masa startowa wyznaczana krok po kroku, jak w opracowaniu ręcznym.

Moduł odtwarza obie metody z materiału C. Galińskiego:
  * iteracyjną — punkty 1)–12): masy po kolejnych fazach, masa pustego z misji (9),
    masa pustego z równania (1) (10), różnica (11) i korekta masy startowej (12);
    od trzeciej iteracji korekta z liniowej zależności m0(Δ) wyznaczonej z dwóch
    poprzednich iteracji (metoda siecznych, zalecana w materiale);
  * proporcji — stosunki mas faz, ich iloczyn, wzór (4) i iteracyjne rozwiązanie
    wzoru (5) z równaniem (1).
Wynik bilansu przyjmowany w projekcie pochodzi z solve_mass(); ten ślad służy do
sprawozdania i używa tych samych funkcji faz misji i masy pustej.
"""
import math

from calculations.bipol1 import empty_mass_law, mission_model, preliminary_polar

TOLERANCE = 1e-3       # BIPOL_1, s. 4: zgodność mas na poziomie 0,1 %
MASS_RESOLUTION = .05  # kg; dalsze iteracje, aż m0 ustali się z dokładnością zapisu 0,1 kg
MAX_ITERATIONS = 60

# Punkty 2)–8) BIPOL_1: klucz fazy modelu → numer masy m_i po danej fazie.
GUIDELINE_PHASES = (
    (1, 'takeoff', 'po starcie'),
    (2, 'climb', 'po wznoszeniu i rozpędzaniu'),
    (3, 'cruise', 'po dolocie do celu'),
    (4, ('task', 'drop'), 'po wykonaniu zadania'),
    (5, 'return', 'po powrocie'),
    (6, 'loiter', 'po oczekiwaniu w kolejce do lądowania'),
    (7, 'landing', 'po lądowaniu i kołowaniu'),
)


def auto_start(useful):
    """Pierwsze założenie: masa użyteczna stanowi około 1/3 masy startowej."""
    return math.ceil(3 * useful / 10) * 10


def guideline_masses(phases):
    """Masy m1…m7 po punktach 2)–8) BIPOL_1; brakująca faza nie zmienia masy."""
    by_key = {phase['key']: phase for phase in phases}
    masses, current = {}, phases[0]['mass_start_kg']
    for index, keys, _label in GUIDELINE_PHASES:
        for key in (keys if isinstance(keys, tuple) else (keys,)):
            if key in by_key:
                current = by_key[key]['mass_end_kg']
        masses[f'm{index}'] = current
    return masses


def _phase_rows(phases):
    return [dict(key=s['key'], label=s['phase'], m_start=s['mass_start_kg'], m_end=s['mass_end_kg'],
                 ratio=s['fraction'], fuel=s['fuel_burn_kg'], release=s['payload_drop_kg'])
            for s in phases if s['key'] not in ('warmup', 'descent')]


def guideline_trace(p, payload, crew, method, start=None):
    """Kolejne iteracje wybranej metody BIPOL_1 dla danych projektu."""
    polar = preliminary_polar(p)
    share, law = empty_mass_law(p)
    method = 'proportions' if method in ('proportion', 'proportions') else 'iterative'
    simulate, mission = mission_model(dict(p, mass_method=method), polar['kmax'])
    drop = mission['drop']
    useful = payload + crew
    chosen = float(start) if start else auto_start(useful)
    base = dict(method='proportion' if method == 'proportions' else 'iterative', start=chosen,
                start_rule=p.get('_mass_trace_start_rule') or ('założenie autora' if start else '3·(m_zał + m_ład), zaokrąglone w górę do 10 kg'),
                payload=payload, crew=crew, useful=useful, drop=drop, reserve_factor=mission['reserve'],
                tolerance=TOLERANCE, law=dict(mode=law['mode'], A=law['A'], C=law['C'], k_vs=law['k_vs'],
                                               modifier=law.get('structural_modifier')),
                factors={k: v for k, v in mission['factors'].items()}, kmax=polar['kmax'],
                cruise_ld=mission['ld'], task_fuel=mission['task_fuel'])
    rows = []
    try:
        if method == 'iterative':
            _iterate_mission(rows, simulate, share, chosen, payload, crew, drop)
        else:
            _iterate_proportion(rows, simulate, share, chosen, useful)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        return dict(base, rows=rows, converged=False, error=str(error))
    reached = next((row['k'] for row in rows if row['relative'] <= TOLERANCE), None)
    final = rows[-1]
    return dict(base, rows=rows, converged=reached is not None, converged_at=reached,
                final_k=final['k'], m0=final['m0'] if method == 'iterative' else final['next_m0'],
                final=final)


def _iterate_mission(rows, simulate, share, m0, payload, crew, drop):
    """Punkty 1)–12): różnica mas pustego i korekta masy startowej."""
    previous = None
    for k in range(1, MAX_ITERATIONS + 1):
        flight = simulate(m0)
        if any(s['mass_end_kg'] <= 0 for s in flight['phases']):
            raise ValueError('Założona masa startowa daje ujemną masę w trakcie misji.')
        landing = flight['landing_mass']
        reserve = flight['reserve']
        # 9) od masy po lądowaniu odjąć ładunek pozostały na pokładzie, załogę oraz rezerwę i paliwo niezużywalne.
        me_mission = landing - (payload - drop) - crew - reserve
        fraction = share(m0)
        me_trend = m0 * fraction             # 10) zakładana masa startowa · (1)
        delta = me_mission - me_trend         # 11)
        relative = abs(delta) / me_trend
        row = dict(k=k, m0=m0, phases=_phase_rows(flight['phases']), masses=guideline_masses(flight['phases']),
                   m_landing=landing, fuel_burn=flight['burn'], reserve=reserve, empty_fraction=fraction,
                   me_mission=me_mission, me_trend=me_trend, delta=delta, relative=relative)
        # 12) korekta: w 1. iteracji o różnicę mas, dalej z prostej przez dwa ostatnie punkty (m0, Δ).
        if previous is None or delta == previous['delta']:
            row.update(rule='correction', next_m0=m0 - delta)
        else:
            slope = (m0 - previous['m0']) / (delta - previous['delta'])
            row.update(rule='secant', slope=slope, next_m0=m0 - delta * slope)
        rows.append(row)
        if relative <= TOLERANCE and abs(row['next_m0'] - m0) < MASS_RESOLUTION:
            return
        if row['next_m0'] <= 0:
            raise ValueError('Korekta daje niedodatnią masę startową; zmień założenie początkowe.')
        previous, m0 = row, row['next_m0']
    raise ValueError('Iteracje BIPOL_1 nie osiągnęły zbieżności.')


def _iterate_proportion(rows, simulate, share, m0, useful):
    """Wzór (5) z (1): m0 = (m_zał + m_ład) / (1 − m_f/m0 − m_e/m0), rozwiązywany iteracyjnie."""
    accelerated = False
    for k in range(1, MAX_ITERATIONS + 1):
        flight = simulate(m0)
        fuel_fraction = flight['fuel'] / m0
        fraction = share(m0)
        denominator = 1 - fuel_fraction - fraction
        if denominator <= 0:
            raise ValueError('Suma udziałów paliwa i masy pustej przekracza 1 dla założonej masy startowej.')
        nxt = useful / denominator
        relative = abs(nxt - m0) / m0
        row = dict(k=k, m0=m0, fuel_fraction=fuel_fraction, fuel=flight['fuel'], empty_fraction=fraction,
                   denominator=denominator, next_m0=nxt, relative=relative, rule='fixed_point',
                   mff=flight['landing_mass'] / m0)
        if len(rows) >= 2 and relative > .9 * rows[-1]['relative'] and not accelerated:
            # Słaba zbieżność podstawienia: przyspieszenie sieczną na h(m0) = g(m0) − m0.
            accelerated = True
        if accelerated and rows:
            prev = rows[-1]
            h1, h0 = nxt - m0, prev['next_m0'] - prev['m0']
            if h1 != h0:
                row.update(rule='secant', next_m0=m0 - h1 * (m0 - prev['m0']) / (h1 - h0))
        rows.append(row)
        if relative <= TOLERANCE and abs(nxt - m0) < MASS_RESOLUTION:
            return
        m0 = row['next_m0']
    raise ValueError('Iteracje wzoru (5) nie osiągnęły zbieżności.')
