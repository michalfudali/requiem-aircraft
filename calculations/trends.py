"""Source-backed reference aircraft and descriptive regressions for BIPOL P1.

All masses use kg. Regressions are exploratory and never silently replace sizing.
Missing observations stay missing; each fit reports its own sample size.
"""
from collections import Counter
from datetime import date
import math
import threading

from calculations import aircraft_store
from calculations.aircraft_store import CLASSES, DATA
from calculations.atmosphere import G0
from calculations.instructor import MIN_AIRCRAFT
from calculations.reference_selection import best_variants, family_groups, selection_description

# Provenance and licence of each data set, stored with the records.
SOURCES = aircraft_store.load_sources()

# BIPOL_1, s. 1: trends are extrapolated five years ahead of the design date.
FORECAST_HORIZON_YEARS = 5
BIPOL_1_SAMPLE = 20
ENGINE_LABELS = {'prop': 'napęd śmigłowy', 'jet': 'napęd odrzutowy', 'none': 'bez napędu'}
DEFAULT_ENGINE = {'glider': 'none', 'jet_business': 'jet', 'jet_transport': 'jet'}



def two_point_power_law(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """Wyznacza współczynniki A i C zależności m_e/m_0 = A * m_0^C z dwóch punktów (x1, y1) i (x2, y2)."""
    if x1 <= 0 or x2 <= 0 or y1 <= 0 or y2 <= 0:
        raise ValueError("Współrzędne punktów korelacji potęgowej muszą być dodatnie.")
    if x1 == x2:
        raise ValueError("Dwa punkty korelacji muszą mieć różne masy startowe.")
    c = math.log(y1 / y2) / math.log(x1 / x2)
    a = y1 / (x1 ** c)
    return a, c

# BIPOL_1, s. 1: the eight averages listed in the handout, in its order.
BIPOL_1_AVERAGES = ('v_h', 'v_v', 'empty_fraction', 'aileron_span_fraction', 'aileron_chord_ratio',
                    'elevator_chord_ratio', 'rudder_chord_ratio', 'dihedral_deg')


def derived(row):
    r = dict(row)
    r['year'] = r.get('year')
    mass, area, span = r['m0'], r.get('s'), r.get('b')
    r['ar'] = span * span / area if span and area else None
    r['empty_fraction'] = r['me'] / mass if r.get('me') else None
    r['wing_loading_kg_m2'] = mass / area if area else None
    r['wing_loading_n_m2'] = G0 * mass / area if area else None
    r['power_loading_kg_kw'] = mass / r['p_kw'] if r.get('p_kw') else None
    r['specific_power_kw_kg'] = r['p_kw'] / mass if r.get('p_kw') else None
    r['thrust_to_weight'] = r['t_kn'] * 1000 / (mass * G0) if r.get('t_kn') else None
    r['prop_diameter_m'] = r.get('prop_diameter_m')
    r['prop_type'] = r.get('prop_type')
    r['ld_max'] = r.get('ld_max')
    r['w_z_min_ms'] = r.get('w_z_min_ms')
    r['v_h'] = r.get('v_h')
    r['aileron_span_fraction'] = r.get('aileron_span_fraction')
    r['aileron_chord_ratio'] = r.get('aileron_chord_ratio')
    r['elevator_chord_ratio'] = r.get('elevator_chord_ratio')
    r['rudder_chord_ratio'] = r.get('rudder_chord_ratio')
    r['dihedral_deg'] = r.get('dihedral_deg')
    # A catalogue's unlabeled take-off number may be ground roll. Do not
    # silently promote it to obstacle distance (the lecture explicitly forbids it).
    r['takeoff_distance_m'] = r.get('takeoff_m') if r.get('takeoff_basis') in ('15m', '50ft', 'field_length') else None
    r['landing_distance_m'] = r.get('landing_m') if r.get('landing_basis') in ('15m', '50ft', 'field_length') else None
    r['climb_rate_ms'] = r.get('climb_rate_ms')
    r['quality_notes'] = []
    if r['empty_fraction'] is not None and not .15 < r['empty_fraction'] < .95:
        r['quality_notes'].append('Nietypowy udział OEW/MTOW — pominięto w regresji masowej.')
    if r['ar'] is not None and not 2 <= r['ar'] <= 60:
        r['quality_notes'].append('Nietypowe wydłużenie — sprawdź źródło geometrii.')
    return r


_catalog = {'revision': None, 'rows': ()}
_catalog_lock = threading.Lock()


def load_aircraft():
    """All reference aircraft with derived values, reloaded only when the database revision changes."""
    with _catalog_lock:
        revision, records = aircraft_store.read_catalog(_catalog['revision'])
        if records is not None:
            _catalog.update(revision=revision, rows=tuple(derived(r) for r in records))
        return _catalog['rows']


def _clear_catalog_cache():
    with _catalog_lock:
        _catalog.update(revision=None, rows=())


load_aircraft.cache_clear = _clear_catalog_cache


def sources_in_use(rows):
    """Sources with at least one record; an empty user source is neither listed nor cited."""
    used = {r['source_id'] for r in rows}
    return {key: meta for key, meta in SOURCES.items() if key in used}


def reference_catalog():
    rows = load_aircraft()
    return {'schema': 1, 'total': len(rows), 'classes': CLASSES, 'sources': sources_in_use(rows),
            'counts': dict(Counter(r['aircraft_type'] for r in rows)), 'aircraft': rows}


# One comparison sample per project. The wizard, the input panel, the P1 trend
# analysis and the empty-mass law select aircraft from these settings only.
SAMPLE_KEYS = ('trend_source', 'trend_nearest_count', 'trend_engine_count', 'trend_year_min', 'trend_year_max',
               'trend_weighting', 'trend_year_basis', 'trend_aircraft_ids', 'trend_observations',
               'variable_sweep')
SAMPLE_CHOICES = {'trend_source': ('all', 'fast', 'cado', 'motogliders', 'geometry_trends', 'user'),
                  'trend_weighting': ('family', 'variant'), 'trend_year_basis': ('production', 'certification')}


def sample_settings(data):
    """Validated comparison-sample settings of a project; other keys are ignored."""
    settings = {}
    for key in ('trend_nearest_count', 'trend_engine_count', 'trend_year_min', 'trend_year_max'):
        if data.get(key) not in (None, ''):
            value = float(data[key])
            if not value.is_integer() or value < 0:
                raise ValueError(f'Pole {key}: wymagana nieujemna liczba całkowita.')
            settings[key] = int(value)
    for key, allowed in SAMPLE_CHOICES.items():
        if data.get(key) not in (None, ''):
            if data[key] not in allowed:
                raise ValueError(f'Pole {key}: nieznana wartość.')
            settings[key] = data[key]
    ids = data.get('trend_aircraft_ids')
    if ids not in (None, ''):
        ids = [i for i in ids.split(',') if i] if isinstance(ids, str) else ids
        if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
            raise ValueError('Dobór konstrukcji: wymagana lista identyfikatorów.')
        settings['trend_aircraft_ids'] = ids
    if data.get('trend_observations'):
        from calculations.trend_observations import validate_observations
        settings['trend_observations'] = validate_observations(data['trend_observations'])
    if data.get('variable_sweep') not in (None, ''):
        settings['variable_sweep'] = data['variable_sweep'] in (True, 'true', '1')
    return settings


def sample_reference_mass(params):
    """MTOW for narrowing: an initial assumption, or an explicitly chosen design fixed point."""
    if not int(params.get('trend_nearest_count', SIMILAR_COUNT) or 0) or params.get('trend_aircraft_ids') is not None:
        return None
    return sample_size(params)[1]


SIMILAR_COUNT = 50


EQ1_UNSOLVABLE = 'Równanie (1)'
PAYLOAD_MARGIN = 1.1  # P2 sensitivity analysis: payload +10%


def similar_counts(params):
    """Sizes of the sample of similar aircraft: the chosen one, widened by a quarter at a time,
    up to the whole matching class (0)."""
    start = int(params.get('trend_nearest_count', SIMILAR_COUNT) or 0)
    pool = len(select_references({**params, '_similar_count': 0, '_reference_mass': None}))
    sizes, count = [], start
    while count and count < pool:
        sizes.append(count)
        count = math.ceil(count * 1.25)
    return sizes + [0]


def design_reference(params, count):
    """MTOW of the design around which the `count` aircraft nearest in mass are chosen.

    The design MTOW follows from the P1 mass balance with eq. (1) of that very sample, so the
    choice is repeated from the whole class until the sample stops changing. When it alternates
    between two samples, the mean of their masses is the reference. `unsolvable` marks a sample
    whose eq. (1) leaves the BIPOL_1 mass iteration without a solution, also for the payload
    increased by 10% of the sensitivity analysis (opis projektu 2)."""
    from calculations.bipol1 import solve_mass
    from calculations.mass import mission_loads
    base = {k: v for k, v in params.items() if k not in ('_mission_polar', '_reference_mass', '_reference')}
    base.update(design_iteration_mode='preliminary', _similar_count=count)
    base, payload, crew = mission_loads(base)
    reference, seen, path = None, [], []
    for _ in range(15):
        sample = tuple(r['id'] for r in select_references({**base, '_reference_mass': reference}))
        if sample in seen:
            cycle = path[seen.index(sample):]
            if len(cycle) > 1:
                reference = sum(cycle) / len(cycle)
            try:
                solve_mass({**base, '_reference_mass': reference}, payload * PAYLOAD_MARGIN, crew)
            except ValueError as error:
                if not str(error).startswith(EQ1_UNSOLVABLE):
                    raise
                return dict(mass=reference, path=path, cycle=len(cycle) > 1, unsolvable=True)
            return dict(mass=reference, path=path, cycle=len(cycle) > 1, unsolvable=False)
        try:
            mass = solve_mass({**base, '_reference_mass': reference}, payload, crew)['m0']
        except ValueError as error:
            if not str(error).startswith(EQ1_UNSOLVABLE):
                raise
            return dict(mass=reference, path=path, cycle=False, unsolvable=True)
        seen.append(sample)
        path.append(mass)
        reference = mass
    return dict(mass=reference, path=path, cycle=False, unsolvable=False)


def similar_sample(params, first=0):
    """BIPOL_1, s. 1 and 4: the aircraft similar to the design are those nearest to it in MTOW;
    their eq. (1) must let the mass iteration close. The smallest such sample, starting from the
    chosen size (sizes[first]), is the comparison sample; the whole class is the last resort."""
    sizes = similar_counts(params)
    for index in range(first, len(sizes)):
        count = sizes[index]
        reference = design_reference(params, count) if count else dict(mass=None, path=[], cycle=False, unsolvable=False)
        if not reference['unsolvable']:
            return dict(reference, count=count, start=sizes[0], index=index, widened=index > 0)
    raise ValueError('Równanie (1) nie daje fizycznego rozwiązania bilansu nawet dla całej klasy samolotów; '
                     'sprawdź misję i masę ładunku.')


def sample_size(params):
    """(number of nearest aircraft or 0 for all, reference MTOW) of the project's sample."""
    if params.get('trend_aircraft_ids') is not None or not int(params.get('trend_nearest_count', SIMILAR_COUNT) or 0):
        return 0, None
    if '_similar_count' in params:
        return int(params['_similar_count'] or 0), params.get('_reference_mass')
    if '_reference_mass' in params:
        # Reference given by the caller (the design mass, or None for the whole class).
        reference = params['_reference_mass']
        return (int(params.get('trend_nearest_count', SIMILAR_COUNT) or 0) if reference is not None else 0), reference
    sample = similar_sample(params)
    return sample['count'], sample['mass']



def select_references(params):
    cls, engine = params.get('aircraft_type', 'piston_ga'), params.get('engine_type', 'prop')
    pool = [r for r in load_aircraft() if r['aircraft_type'] == cls and r['engine_type'] == engine]
    groups = family_groups(pool)
    overrides = {r['id']: r for r in params.get('trend_observations', [])}
    pool = [{**r, **{k: v for k, v in overrides.get(r['id'], {}).items() if k != 'source'},
             'source_references': r['source_references'] + ('; Uzupełnienie autora: ' + overrides[r['id']]['source'] if r['id'] in overrides else '')}
            for r in pool]
    source = params.get('trend_source', 'all')
    if source != 'all':
        pool = [r for r in pool if r['source_id'] == source]
    engines = int(params.get('trend_engine_count', 0))
    if engines:
        pool = [r for r in pool if r['n_engines'] == engines]
    ymin, ymax = int(params.get('trend_year_min', 0)), int(params.get('trend_year_max', 0))
    if ymin or ymax:
        pool = [r for r in pool if r.get('year') is not None and (not ymin or r.get('year') >= ymin) and (not ymax or r.get('year') <= ymax)]
    ids = params.get('trend_aircraft_ids')
    if ids is not None:
        selected_families = {groups[aid][0] for aid in ids if aid in groups}
        pool = [r for r in pool if groups[r['id']][0] in selected_families]
    pool = best_variants(pool, groups, cls)
    reference = sample_reference_mass(params)
    if reference is None:
        return sorted(pool, key=lambda r: r['id'])
    pool = sorted(pool, key=lambda r: (abs(math.log(r['m0'] / reference)), r['id']))
    count = sample_size(params)[0]
    return pool[:count] if count else pool


def valid_value(key, row):
    """Observation usable in a fit or average; outliers are excluded consistently."""
    value = row.get(key)
    if value is None:
        return False
    if key == 'empty_fraction':
        return .15 < value < .95
    if key == 'ar':
        return 2 <= value <= 60
    return True


def sample_weights(weighting):
    def weights(subset):
        # Recount within each fit: missing data must not reduce a family's total weight.
        families = Counter(r['family'] for r in subset)
        return [1/families[r['family']] if weighting == 'family' else 1. for r in subset]
    return weights


def mass_trend(params, rows=None):
    """The same mass law for P1, suggestions, and the nonlinear mass balance."""
    rows = select_references(params) if rows is None else rows
    subset = [r for r in rows if valid_value('empty_fraction', r)]
    weights = sample_weights(params.get('trend_weighting', 'family'))(subset)
    fit = fit_regression([(r['m0'], r['empty_fraction']) for r in subset], weights, power=True)
    return subset, fit


def forecast_years(today=None):
    reference = (today or date.today()).year
    return reference, reference + FORECAST_HORIZON_YEARS


def dated_rows(rows):
    """Aircraft on the time axis. BIPOL_1 asks for the production year; the basis with more dated
    aircraft in the sample gives the better trend (production on a tie). Returns (basis, rows)."""
    counts = Counter(r.get('year_basis') or 'certification' for r in rows if r.get('year') is not None)
    basis = 'production' if counts['production'] and counts['production'] >= counts['certification'] else 'certification'
    return basis, [r for r in rows if r.get('year') is not None and (r.get('year_basis') or 'certification') == basis]


def time_trend(rows, key, weights, forecast_year):
    subset = [r for r in rows if r.get('year') is not None and valid_value(key, r)]
    fit = fit_regression([(r['year'], r[key]) for r in subset], weights(subset))
    # Do not pretend to extrapolate a single generation of aircraft.
    if fit and fit['x_max'] - fit['x_min'] < 5:
        fit = None
    return subset, fit, predict(fit, forecast_year) if fit else None


def forecast_rejection(fit, forecast, metric, forecast_year):
    """Common acceptance rule for a design forecast, separate from merely plotting a fit.

    R² = 0.2 is a declared screening choice, not an airworthiness requirement.
    Exceeding the observed y range alone cannot reject an extrapolation.
    """
    if not fit:
        return 'mniej niż 3 kompletne obserwacje lub rozpiętość dat poniżej 5 lat'
    lo, hi = PHYSICAL_BOUNDS.get(metric, (0, math.inf))
    if forecast is None or not lo < forecast < hi:
        return 'prognoza poza zakresem fizycznym'
    if fit['r2'] is None or fit['r2'] < .2:
        return 'słaba zależność od roku (R² < 0,2)'
    if forecast_year - fit['x_max'] > max(5, fit['x_max'] - fit['x_min']):
        return 'ekstrapolacja dłuższa niż okres objęty obserwacjami'
    return None


def two_point_coefficients(fit):
    """BIPOL_1, eq. (1): C and A from two points read off the fitted mass line."""
    x1, x2 = fit['x_min'], fit['x_max']
    y1, y2 = predict(fit, x1), predict(fit, x2)
    c = math.log(y1 / y2) / math.log(x1 / x2)
    return {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'C': c, 'A': y1 / x1 ** c}


def empty_mass_trend(params, rows=None):
    rows, fit = mass_trend(params, rows)
    return rows, fit, two_point_coefficients(fit) if fit else None


def describe_sample(params, rows):
    engine = params.get('engine_type', 'prop')
    parts = [f"klasa „{CLASSES[params.get('aircraft_type', 'piston_ga')]}”, {ENGINE_LABELS.get(engine, engine)}"]
    reference = sample_reference_mass(params)
    if params.get('trend_aircraft_ids') is not None:
        parts.append('konstrukcje zaznaczone ręcznie')
    elif reference:
        parts.append(f"{len(rows)} konstrukcji o masie startowej najbliższej masie projektu {_pl(reference, 0)} kg")
    else:
        parts.append('wszystkie pasujące konstrukcje')
    if params.get('trend_source', 'all') != 'all':
        parts.append(f"źródło: {SOURCES.get(params['trend_source'], {}).get('name', params['trend_source'])}")
    if int(params.get('trend_engine_count', 0)):
        parts.append(f"liczba silników: {int(params['trend_engine_count'])}")
    ymin, ymax = int(params.get('trend_year_min', 0)), int(params.get('trend_year_max', 0))
    if ymin or ymax:
        parts.append(f"certyfikacja {ymin or '…'}–{ymax or '…'}")
    weighting = params.get('trend_weighting', 'family')
    parts.append('jedna najlepsza odmiana na rodzinę; równa waga konstrukcji')
    return {'description': '; '.join(parts), 'selected_n': len(rows), 'reference_mass': reference,
            'families_n': len({r['family'] for r in rows}), 'weighting': weighting,
            'variant_policy': 'best_in_family',
            'variant_selection_rule': selection_description(params.get('aircraft_type', 'piston_ga')),
            'omitted_variants_n': sum(r.get('variant_selection', {}).get('candidates_n', 1) - 1 for r in rows)}


def _pl(value, digits=3, significant=False):
    text = f'{value:.{digits}g}' if significant else f'{value:.{digits}f}'
    return text.replace('-', '−').replace('.', ',')


def fit_regression(points, weights=None, power=False):
    """Weighted OLS with centered sums; reject constant x and insufficient data."""
    points = [(x, y, w) for (x, y), w in zip(points, weights or [1.] * len(points))
              if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)
              and w > 0 and (not power or x > 0 and y > 0)]
    if len(points) < 3:
        return None
    tx = [math.log(x) if power else x for x, _, _ in points]
    ty = [math.log(y) if power else y for _, y, _ in points]
    ws = [w for _, _, w in points]
    total = sum(ws)
    xm, ym = sum(x*w for x, w in zip(tx, ws))/total, sum(y*w for y, w in zip(ty, ws))/total
    sxx = sum(w * (x-xm)**2 for x, w in zip(tx, ws))
    syy = sum(w * (y-ym)**2 for y, w in zip(ty, ws))
    if sxx <= 1e-16:
        return None
    slope = sum(w*(x-xm)*(y-ym) for x, y, w in zip(tx, ty, ws)) / sxx
    intercept = ym - slope*xm
    if power and not -700 < intercept < 700:
        return None  # Ill-conditioned near-constant mass cohort, not a usable law.
    residual = sum(w*(y-intercept-slope*x)**2 for x, y, w in zip(tx, ty, ws))
    return {'kind': 'power' if power else 'linear', 'n': len(points), 'slope': slope,
            'intercept': intercept, 'A': math.exp(intercept) if power else None,
            'C': slope if power else None, 'r2': 1-residual/syy if syy > 1e-16 else None,
            'rmse': math.sqrt(residual/total), 'x_min': min(x for x, _, _ in points),
            'x_max': max(x for x, _, _ in points), 'y_min': min(y for _, y, _ in points),
            'y_max': max(y for _, y, _ in points)}


def predict(fit, x):
    if not fit:
        return None
    try:
        value = math.exp(fit['intercept'] + fit['C']*math.log(x)) if fit['kind'] == 'power' else fit['intercept'] + fit['slope']*x
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


METRICS = {
    'm0': ('MTOW', 'kg'), 'empty_fraction': ('OEW / MTOW', '−'), 'ar': ('Wydłużenie AR', '−'),
    'wing_loading_kg_m2': ('Obciążenie powierzchni', 'kg/m²'),
    'prop_diameter_m': ('Średnica / rozpiętość śmigła', 'm'),
    'v_cruise_kmh': ('Prędkość przelotowa', 'km/h'), 'cruise_mach': ('Liczba Macha przelotu', 'Ma'),
    'range_km': ('Zasięg katalogowy', 'km'), 'takeoff_m': ('Długość startu katalogowa', 'm'),
    'takeoff_distance_m': ('Całkowita długość startu (wg źródła)', 'm'),
    'landing_distance_m': ('Całkowita długość lądowania (wg źródła)', 'm'),
    'climb_rate_ms': ('Prędkość wznoszenia', 'm/s'),
    'power_loading_kg_kw': ('Obciążenie mocy m₀/P', 'kg/kW'),
    'specific_power_kw_kg': ('Moc jednostkowa P/m₀', 'kW/kg'),
    'thrust_to_weight': ('Obciążenie ciągu T/W', '−'),
    'ld_max': ('Doskonałość maksymalna', '−'),
    'w_z_min_ms': ('Najmniejsze opadanie', 'm/s'),
    'v_h': ('Cecha objętościowa usterzenia poziomego V_H', '−'),
    'v_v': ('Cecha objętościowa usterzenia pionowego V_V', '−'),
    'aileron_span_fraction': ('Część rozpiętości objęta lotkami b_ail/(b/2)', '−'),
    'aileron_chord_ratio': ('Względna cięciwa lotek c_ail/c', '−'),
    'elevator_chord_ratio': ('Względna cięciwa steru wysokości c_e/c_H', '−'),
    'rudder_chord_ratio': ('Względna cięciwa steru kierunku c_r/c_V', '−'),
    'dihedral_deg': ('Kąt wzniosu skrzydła Γ', '°'),
}

GEOMETRY_METRICS_INFO = {
    'v_h': {
        'label': 'Cecha objętościowa usterzenia poziomego',
        'symbol': 'V_H',
        'formula_latex': r'\bar{V}_H = \frac{S_H \cdot l_H}{S \cdot c_a}',
        'unit': '−',
        'desc': 'Współczynnik objętościowy usterzenia poziomego decydujący o statycznej stateczności podłużnej i zapasie stateczności.',
        'typical_ranges': {
            'piston_ga': (0.50, 0.85, '0.50 – 0.85 (Raymer Tab. 6.4: ~0.70)'),
            'turboprop_regional': (0.75, 1.05, '0.75 – 1.05 (Roskam Tab. 2.1: ~0.90)'),
            'jet_business': (0.65, 1.00, '0.65 – 1.00 (Raymer Tab. 6.4: ~0.80)'),
            'jet_transport': (0.80, 1.15, '0.80 – 1.15 (Roskam Tab. 2.1: ~1.00)'),
            'glider': (0.45, 0.60, '0.45 – 0.60 (MEiL PW / Thomas: ~0.50)'),
            'motoglider': (0.50, 0.65, '0.50 – 0.65 (EASA CS-22: ~0.58)'),
            'uav': (0.45, 0.75, '0.45 – 0.75 (Gudmundsson: ~0.60)')
        }
    },
    'aileron_span_fraction': {
        'label': 'Część rozpiętości objęta lotkami',
        'symbol': 'b_{ail} / (b/2)',
        'formula_latex': r'\frac{b_{ail,1}}{b/2}=\frac{2b_{ail,1}}{b}',
        'unit': '−',
        'desc': 'Udział rozpiętości skrzydła zajęty przez lotkę; determinuje skuteczność przechylania pb/(2V).',
        'typical_ranges': {
            'piston_ga': (0.30, 0.55, '0.30 – 0.55 (typowo ~0.40; Raymer/Roskam)'),
            'turboprop_regional': (0.25, 0.40, '0.25 – 0.40 (typowo ~0.32)'),
            'jet_business': (0.24, 0.35, '0.24 – 0.35 (typowo ~0.30)'),
            'jet_transport': (0.20, 0.30, '0.20 – 0.30 (typowo ~0.24 + spoilery)'),
            'glider': (0.40, 0.55, '0.40 – 0.55 (typowo ~0.48)'),
            'motoglider': (0.40, 0.70, '0.40 – 0.70 (klapolotki do ~0.75)'),
            'uav': (0.35, 0.60, '0.35 – 0.60 (typowo ~0.45)')
        }
    },
    'aileron_chord_ratio': {
        'label': 'Względna cięciwa lotek',
        'symbol': 'c_{ail} / c',
        'formula_latex': r'\frac{c_{ail}}{c}',
        'unit': '−',
        'desc': 'Stosunek cięciwy lotki do lokalnej cięciwy skrzydła w rejonie krawędzi spływu.',
        'typical_ranges': {
            'piston_ga': (0.18, 0.28, '0.18 – 0.28 (Raymer rozdz. 12: ~0.22)'),
            'turboprop_regional': (0.18, 0.25, '0.18 – 0.25 (typowo ~0.21)'),
            'jet_business': (0.17, 0.24, '0.17 – 0.24 (typowo ~0.20)'),
            'jet_transport': (0.15, 0.22, '0.15 – 0.22 (typowo ~0.18)'),
            'glider': (0.15, 0.22, '0.15 – 0.22 (typowo ~0.17)'),
            'motoglider': (0.16, 0.24, '0.16 – 0.24 (typowo ~0.19)'),
            'uav': (0.18, 0.28, '0.18 – 0.28 (typowo ~0.23)')
        }
    },
    'elevator_chord_ratio': {
        'label': 'Względna cięciwa steru wysokości',
        'symbol': 'c_e / c_H',
        'formula_latex': r'\frac{c_e}{c_H}',
        'unit': '−',
        'desc': 'Stosunek cięciwy steru wysokości do cięciwy statecznika poziomego (lub 1.00 dla płytowego).',
        'typical_ranges': {
            'piston_ga': (0.28, 0.45, '0.28 – 0.45 (lub 1.00 stabilator; Raymer ~0.35)'),
            'turboprop_regional': (0.28, 0.38, '0.28 – 0.38 (typowo ~0.33)'),
            'jet_business': (0.26, 0.35, '0.26 – 0.35 (typowo ~0.30)'),
            'jet_transport': (0.25, 0.35, '0.25 – 0.35 (typowo ~0.28)'),
            'glider': (0.30, 0.45, '0.30 – 0.45 (typowo ~0.36)'),
            'motoglider': (0.30, 0.42, '0.30 – 0.42 (typowo ~0.36)'),
            'uav': (0.25, 0.40, '0.25 – 0.40 (typowo ~0.34)')
        }
    },
    'rudder_chord_ratio': {
        'label': 'Względna cięciwa steru kierunku',
        'symbol': 'c_r / c_V',
        'formula_latex': r'\frac{c_r}{c_V}',
        'unit': '−',
        'desc': 'Stosunek cięciwy steru kierunku do cięciwy statecznika pionowego.',
        'typical_ranges': {
            'piston_ga': (0.30, 0.48, '0.30 – 0.48 (Raymer rozdz. 12: ~0.38)'),
            'turboprop_regional': (0.30, 0.42, '0.30 – 0.42 (typowo ~0.35)'),
            'jet_business': (0.28, 0.38, '0.28 – 0.38 (typowo ~0.31)'),
            'jet_transport': (0.25, 0.35, '0.25 – 0.35 (typowo ~0.28)'),
            'glider': (0.38, 0.52, '0.38 – 0.52 (typowo ~0.45; adverse yaw)'),
            'motoglider': (0.36, 0.48, '0.36 – 0.48 (typowo ~0.42)'),
            'uav': (0.28, 0.42, '0.28 – 0.42 (typowo ~0.35)')
        }
    },
    'dihedral_deg': {
        'label': 'Kąt wzniosu skrzydła',
        'symbol': r'\Gamma',
        'formula_latex': r'\Gamma \; [^\circ]',
        'unit': '°',
        'desc': 'Kąt wzniosu geometrycznego skrzydła wpływający na poprzeczną stateczność statyczną.',
        'typical_ranges': {
            'piston_ga': (0.0, 7.0, 'Dolnopłat: 4°–7°; Górnopłat: 0°–2° (Roskam Tab. 3.1)'),
            'turboprop_regional': (0.0, 7.0, 'Dolnopłat: 4°–6°; Górnopłat: 0°–3°'),
            'jet_business': (2.0, 6.0, '2°–6° (skos skrzydeł obniża wymagany wznios)'),
            'jet_transport': (3.0, 7.0, '4°–7° (skrzydła skośne ze skręceniem ujemnym)'),
            'glider': (1.5, 4.5, '2°–4° (typowo ~3.3°; stateczność spiralna)'),
            'motoglider': (1.5, 4.0, '2°–3.5° (typowo ~3.0°)'),
            'uav': (0.0, 6.0, '0°–5° (zależnie od położenia skrzydła i usterzenia V)')
        }
    }
}


def compute_vector_stats(values):
    if not values:
        return None
    n = len(values)
    mean = sum(values) / n
    s_vals = sorted(values)
    med = s_vals[n // 2] if n % 2 != 0 else (s_vals[n // 2 - 1] + s_vals[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(var)
    return {'n': n, 'mean': mean, 'median': med, 'std': std, 'min': min(values), 'max': max(values)}


def analyze_geometry_trends(params, geom_res=None, rows=None):
    """Geometry diagnostics of the project's selected sample, using the P1 weights."""
    all_aircraft = select_references(params) if rows is None else rows
    sample = all_aircraft
    weights = sample_weights(params.get('trend_weighting', 'family'))
    ac_type = params.get('aircraft_type', 'piston_ga')
    wing_cfg = params.get('wing_configuration', params.get('wing_config', 'low'))

    # Extract project values
    ctrl = geom_res.get('control_surfaces', {}) if geom_res else {}
    htail = geom_res.get('horizontal_tail', {}) if geom_res else {}
    wing = geom_res.get('wing', {}) if geom_res else {}
    ailerons = ctrl.get('ailerons', {})

    proj_vals = {
        'v_h': htail.get('vh_coeff', float(params.get('v_h', 0.70))),
        'aileron_span_fraction': ailerons.get('ba_over_b', float(params.get('aileron_span_ratio', 0.35))),
        'aileron_chord_ratio': ailerons.get('ca_over_c', float(params.get('aileron_chord_ratio', 0.20))),
        'elevator_chord_ratio': float(params.get('elevator_chord_ratio', params.get('ce_ch', 0.35))),
        'rudder_chord_ratio': float(params.get('rudder_chord_ratio', params.get('cr_cv', 0.35))),
        'dihedral_deg': wing.get('dihedral_deg', float(params.get('dihedral_deg', 3.0))),
    }

    metrics_analysis = []
    for key, info in GEOMETRY_METRICS_INFO.items():
        all_subset = [r for r in all_aircraft if r.get(key) is not None]
        class_subset = [r for r in sample if r.get(key) is not None]

        all_vals = [r[key] for r in all_subset]
        class_vals = [r[key] for r in class_subset]

        all_stats = compute_vector_stats(all_vals)
        class_stats = compute_vector_stats(class_vals)
        for stats, subset in ((all_stats, all_subset), (class_stats, class_subset)):
            if stats:
                sw = weights(subset)
                stats['mean'] = sum(r[key] * w for r, w in zip(subset, sw)) / sum(sw)

        proj_val = proj_vals.get(key)

        # Do not mix classes to conceal missing data in the selected class.
        reg_source = class_subset
        mass_rows = [r for r in reg_source if r.get('m0')]
        span_rows = [r for r in reg_source if r.get('b')]
        fit_m0 = fit_regression([(r['m0'], r[key]) for r in mass_rows], weights(mass_rows))
        fit_b = fit_regression([(r['b'], r[key]) for r in span_rows], weights(span_rows))

        # Evaluation against typical literature range
        typ_min, typ_max, lit_note = info['typical_ranges'][ac_type]
        if key == 'dihedral_deg' and ac_type in ('piston_ga', 'turboprop_regional'):
            if wing_cfg in ('high', 'braced_high'):
                typ_min, typ_max = 0.0, 2.5
                lit_note = 'Górnopłat: 0°–2.5° (efekt wahadła kadłuba)'
            else:
                typ_min, typ_max = 3.5, 7.0
                lit_note = 'Dolnopłat: 3.5°–7.0° (wymagany zapas Cl_beta < 0)'

        diff_pct = ((proj_val - class_stats['mean']) / class_stats['mean'] * 100.0) if (proj_val is not None and class_stats and class_stats['mean'] != 0) else None

        is_in_range = (typ_min <= proj_val <= typ_max) if proj_val is not None else None

        if is_in_range:
            status = 'ok'
            verdict = f'W typowym zakresie literaturowym ({lit_note}); skuteczność wymaga osobnego sprawdzenia.'
        elif proj_val is not None and proj_val < typ_min:
            status = 'warning'
            verdict = f'Poniżej typowego zakresu ({lit_note}); zweryfikuj zapas stateczności lub skuteczność.'
        elif proj_val is not None and proj_val > typ_max:
            status = 'info' if key in ('aileron_span_fraction', 'aileron_chord_ratio') else 'warning'
            verdict = f'Powyżej typowego zakresu ({lit_note}); sprawdź skuteczność i opór.'
        else:
            status = 'unknown'
            verdict = 'Brak danych do weryfikacji.'

        # Samples for inspection
        samples = sorted(class_subset, key=lambda r: abs(r[key] - (proj_val if proj_val is not None else class_stats['mean'])))[:3]

        metrics_analysis.append({
            'key': key,
            'label': info['label'],
            'symbol': info['symbol'],
            'formula_latex': info['formula_latex'],
            'unit': info['unit'],
            'desc': info['desc'],
            'project_value': proj_val,
            'class_stats': class_stats,
            'all_stats': all_stats,
            'fit_m0': fit_m0,
            'fit_b': fit_b,
            'diff_pct': diff_pct,
            'typical_range_str': lit_note,
            'status': status,
            'verdict': verdict,
            'samples': [{'model': s['model'], 'm0': s.get('m0'), 'b': s.get('b'), 'val': s[key], 'source': s.get('source_locator', s.get('source_id'))} for s in samples]
        })

    # Cross-class comparison table
    cross_class_matrix = []
    for c_id, c_name in CLASSES.items():
        row_stats = {'class_id': c_id, 'class_name': c_name, 'is_active': (c_id == ac_type)}
        c_models = [r for r in all_aircraft if r.get('aircraft_type') == c_id]
        row_stats['n_models'] = len(c_models)
        for k in GEOMETRY_METRICS_INFO:
            k_vals = [r[k] for r in c_models if r.get(k) is not None]
            st = compute_vector_stats(k_vals)
            row_stats[k] = st
        cross_class_matrix.append(row_stats)

    return {
        'metrics': metrics_analysis,
        'cross_class_matrix': cross_class_matrix,
        'active_class': ac_type,
        'active_class_name': CLASSES.get(ac_type, ac_type),
        'total_geometry_models': len([r for r in all_aircraft if any(r.get(k) is not None for k in GEOMETRY_METRICS_INFO)]),
    }


def analyze_trends(params, m0, m_empty, geom_res=None):
    rows = select_references(params)
    counts = Counter(r['family'] for r in rows)
    weighting = params.get('trend_weighting', 'family')
    weights = sample_weights(weighting)
    reference_year, forecast_year = forecast_years()
    valid_mass, mass_fit = mass_trend(params, rows)
    two_point = two_point_coefficients(mass_fit) if mass_fit else None
    k_vs = 1.04 if params.get('variable_sweep', False) else 1.
    prediction = predict(mass_fit, m0)
    trend_value = prediction * k_vs if prediction is not None else None
    warnings = []
    if len(counts) < MIN_AIRCRAFT:
        warnings.append(f'Wymaganie prowadzącego: minimum 8 podobnych konstrukcji. Wybrano {len(counts)} rodzin; uzupełnij próbę.')
    if mass_fit and mass_fit['C'] >= 0:
        warnings.append('Trend OEW/MTOW nie jest malejący (C ≥ 0). Sprawdź dobór podobnych konstrukcji, definicje mas i źródła; nie odwracaj sztucznie regresji.')
    if len(rows) < BIPOL_1_SAMPLE:
        warnings.append(f'Wybrano {len(rows)} konstrukcji. Materiał BIPOL_1 zaleca co najmniej 20 podobnych samolotów; poszerz dobór lub uzupełnij źródła.')
    if len(valid_mass) < BIPOL_1_SAMPLE:
        warnings.append(f'Regresja masowa ma {len(valid_mass)} kompletnych obserwacji; wynik jest poglądowy.')
    if mass_fit and not mass_fit['x_min'] <= m0 <= mass_fit['x_max']:
        warnings.append('Masa projektu leży poza zakresem próby — porównanie masowe jest ekstrapolacją.')
    if trend_value is not None and not 0 < trend_value < 1:
        warnings.append('Ekstrapolacja daje niefizyczny udział masy. Nie używaj jej do bilansu mas.')
    time_trends = []
    year_basis, time_rows = dated_rows(rows)
    for key, (label, unit) in METRICS.items():
        subset, fit, forecast = time_trend(time_rows, key, weights, forecast_year)
        rejection = forecast_rejection(fit, forecast, key, forecast_year)
        time_trends.append({'key': key, 'label': label, 'unit': unit, 'fit': fit,
            'available_n': len(subset), 'points': [{'x': r['year'], 'y': r[key], 'model': r['model']} for r in subset],
            'forecast_year': forecast_year if fit else None, 'forecast': forecast,
            'extrapolation_years': forecast_year - fit['x_max'] if fit else None,
            'forecast_physical': forecast is not None and forecast > 0 and (key != 'empty_fraction' or forecast < 1),
            'forecast_accepted': rejection is None, 'forecast_rejection': rejection,
            'provisional': len(subset) < BIPOL_1_SAMPLE})
    if max((t['available_n'] for t in time_trends), default=0) < BIPOL_1_SAMPLE:
        warnings.append('Za mało udokumentowanych dat dla pełnej analizy czasowej. Dat certyfikacji nie zastępujemy domyślnym rokiem produkcji.')
    relationships = []
    x_keys = ['ar', 'wing_loading_kg_m2']
    if params.get('engine_type') == 'jet':
        x_keys.append('thrust_to_weight')
    elif params.get('engine_type', 'prop') == 'prop':
        x_keys.extend(['power_loading_kg_kw', 'specific_power_kw_kg'])
    x_labels = {'ar': ('Wydłużenie AR', '−'), 'wing_loading_kg_m2': ('Obciążenie powierzchni', 'kg/m²'),
                'thrust_to_weight': ('T / W', '−'), 'power_loading_kg_kw': ('Obciążenie mocy m₀ / P', 'kg/kW'),
                'specific_power_kw_kg': ('Moc jednostkowa P / m₀', 'kW/kg')}
    if any(r.get('prop_diameter_m') is not None for r in rows):
        x_keys.append('prop_diameter_m')
        x_labels['prop_diameter_m'] = ('Średnica śmigła d_prop', 'm')
    y_keys = ['v_cruise_kmh', 'cruise_mach', 'range_km', 'takeoff_distance_m', 'landing_distance_m', 'climb_rate_ms', 'ld_max', 'w_z_min_ms',
              'v_h', 'aileron_span_fraction', 'aileron_chord_ratio', 'dihedral_deg']
    if any(r.get('prop_diameter_m') is not None for r in rows):
        y_keys.append('prop_diameter_m')
    for x_key in x_keys:
        for key in y_keys:
            if x_key == key:
                continue
            subset = [r for r in rows if r.get(x_key) is not None and r.get(key) is not None
                      and not (x_key == 'ar' and not 2 <= r['ar'] <= 60)]
            fit = fit_regression([(r[x_key], r[key]) for r in subset], weights(subset))
            relationships.append({'x_key': x_key, 'x_label': x_labels[x_key][0], 'x_unit': x_labels[x_key][1],
                'y_key': key, 'y_label': METRICS[key][0], 'y_unit': METRICS[key][1], 'fit': fit,
                'points': [{'x': r[x_key], 'y': r[key], 'model': r['model']} for r in subset]})
    averages = {}
    for key in (*BIPOL_1_AVERAGES, 'ar', 'wing_loading_kg_m2', 'prop_diameter_m', 'h_tail_area', 'v_tail_area'):
        subset = [r for r in rows if valid_value(key, r)]
        ws = weights(subset)
        averages[key] = {'mean': sum(r[key]*w for r,w in zip(subset,ws))/sum(ws) if subset else None, 'n': len(subset)}
    sample = describe_sample(params, rows)
    suggestions = trend_suggestions(rows, params, m0, weights, mass_fit, forecast_year, sample)

    geometry_trends_analysis = analyze_geometry_trends(params, geom_res, rows)

    # A fixed report structure: one mass plot, two plots against year and
    # three physical relationships. Missing observations remain explicit.
    def time_chart(key):
        t = next(t for t in time_trends if t['key'] == key)
        return {'mode': key, 'kind': 'time', 'label': f"{t['label']} w funkcji roku",
                'parameter': key, 'n': t['available_n'], 'fit': t['fit'],
                'forecast_accepted': t['forecast_accepted'], 'forecast_rejection': t['forecast_rejection']}

    def relation_chart(x, y):
        r = next(r for r in relationships if r['x_key'] == x and r['y_key'] == y)
        return {'mode': f'{x}:{y}', 'kind': 'relation', 'label': f"{r['y_label']} a {r['x_label']}",
                'parameter': y, 'n': len(r['points']), 'fit': r['fit']}

    propulsion_key = 'thrust_to_weight' if params.get('engine_type') == 'jet' else 'power_loading_kg_kw'
    performance_key = ('cruise_mach' if sum(r.get('cruise_mach') is not None for r in rows) >
                       sum(r.get('v_cruise_kmh') is not None for r in rows) else 'v_cruise_kmh')
    time_keys = [performance_key, 'ar', 'wing_loading_kg_m2']
    if params.get('engine_type') != 'none':
        time_keys.append(propulsion_key)
    time_options = [time_chart(key) for key in time_keys]
    # Prefer complete observations instead of a blank speed/year plot when
    # speed and certification dates belong to different source records.
    def chart_rank(chart):
        fit = chart['fit']
        return (not (chart['n'] >= MIN_AIRCRAFT and fit),
                -(fit['r2'] if fit and fit['r2'] is not None else 0), -chart['n'])

    time_options.sort(key=chart_rank)
    report_charts = [{'mode': 'mass', 'kind': 'mass', 'label': 'Udział masy pustej w funkcji masy startowej',
                      'n': len(valid_mass), 'fit': mass_fit}, *time_options[:2]]
    if params.get('engine_type') == 'none':
        choices = [('ar','ld_max'), ('wing_loading_kg_m2','v_cruise_kmh'),
                   ('ar','w_z_min_ms'), ('wing_loading_kg_m2','w_z_min_ms'),
                   ('wing_loading_kg_m2','ld_max'), ('ar','v_cruise_kmh'), ('ar','range_km')]
        required_axes = ['ar', 'wing_loading_kg_m2', 'ar']
    else:
        climb_chart = relation_chart(propulsion_key, 'climb_rate_ms')
        choices = [('ar','range_km'), (propulsion_key,'climb_rate_ms'),
                   ('wing_loading_kg_m2','takeoff_distance_m'), (propulsion_key,performance_key),
                   ('ar','ld_max'), ('wing_loading_kg_m2','landing_distance_m'),
                   ('ar',performance_key), ('wing_loading_kg_m2',performance_key), (propulsion_key,'range_km')]
        required_axes = ['ar', 'wing_loading_kg_m2', propulsion_key]
        if climb_chart['n'] < MIN_AIRCRAFT:
            warnings.append('Wznoszenie a obciążenie napędu: uzupełnij katalogowe prędkości wznoszenia. Braku danych osiągowych nie zastępuje się proporcjami geometrycznymi.')
    candidates = [relation_chart(x, y) for x, y in choices]
    candidates.sort(key=chart_rank)
    used_parameters = {c['parameter'] for c in report_charts if c['kind'] != 'mass'}
    for axis in required_axes:
        candidate = next(c for c in candidates if c['mode'].split(':')[0] == axis and c['parameter'] not in used_parameters)
        report_charts.append(candidate)
        used_parameters.add(candidate['parameter'])
    if any(c['n'] < MIN_AIRCRAFT for c in report_charts):
        warnings.append('Część sześciu wymaganych wykresów ma mniej niż 8 par danych. Uzupełnij dane źródłowe; nie zastępuj pełnego startu rozbiegiem ani wznoszenia opadaniem.')

    return {'database_total': len(load_aircraft()), 'selected_n': len(rows), 'families_n': len(counts),
        'class_label': CLASSES[params.get('aircraft_type', 'piston_ga')], 'weighting': weighting,
        'reg_A': mass_fit['A'] if mass_fit else None, 'reg_C': mass_fit['C'] if mass_fit else None,
        'mass_fit': mass_fit, 'two_point': two_point, 'k_vs': k_vs, 'we_wo_trend': trend_value,
        'we_wo_actual': m_empty/m0 if m0 else None,
        'similar_aircraft': rows, 'averages': averages, 'warnings': warnings,
        'time_trends': time_trends, 'relationships': relationships, 'sources': sources_in_use(rows),
        'report_charts': report_charts, 'sample': sample, 'suggestions': suggestions,
        'reference_year': reference_year, 'forecast_year': forecast_year,
        'mass_trend_decreasing': mass_fit['C'] < 0 if mass_fit else None,
        'year_basis': 'Rok produkcji' if year_basis=='production' else 'Rok certyfikacji wariantu (nie rok produkcji)',
        'method': 'Linia trendu log(OEW/MTOW) = log(A) + C·log(m₀ [kg]) z regresji; A i C odczytano z dwóch punktów tej linii wzorami BIPOL_1. Każdą rodzinę reprezentuje jedna najlepsza odmiana o wadze 1.',
        'limitations': 'OEW obejmuje wyposażenie operacyjne i nie jest tożsama z masą własną każdego projektu. Cechy geometryczne i sterów (V_H, lotki, stery, wznios) oparto na 82 certyfikowanych konstrukcjach (Raymer, Roskam, Corke, TCDS, MEiL PW). Rodziny są grupowane heurystycznie. Korelacja nie dowodzi przyczynowości.',
        'geometry_trends_analysis': geometry_trends_analysis}


SUGGESTION_TYPICAL_RANGES = {
    'ws': {
        'piston_ga': [60.0, 130.0],
        'turboprop_regional': [180.0, 360.0],
        'jet_business': [220.0, 500.0],
        'jet_transport': [400.0, 750.0],
        'glider': [28.0, 52.0],
        'motoglider': [30.0, 55.0],
        'uav': [15.0, 120.0],
    },
    'ar': {
        'piston_ga': [6.0, 9.5],
        'turboprop_regional': [8.5, 13.0],
        'jet_business': [6.5, 10.0],
        'jet_transport': [7.0, 11.5],
        'glider': [16.0, 32.0],
        'motoglider': [14.0, 28.0],
        'uav': [8.0, 20.0],
    },
    'me_m0': {
        'piston_ga': [0.55, 0.72],
        'turboprop_regional': [0.52, 0.68],
        'jet_business': [0.50, 0.68],
        'jet_transport': [0.44, 0.62],
        'glider': [0.45, 0.70],
        'motoglider': [0.52, 0.74],
        'uav': [0.45, 0.65],
    },
    'pw': {
        'piston_ga': [5.5, 10.5],
        'turboprop_regional': [3.8, 7.5],
        'motoglider': [8.0, 25.0],
    },
    'tw': {
        'jet_business': [0.25, 0.48],
        'jet_transport': [0.22, 0.40],
    },
    # Raymer, Aircraft Design, Tab. 6.4 (c_VT): szybowiec 0,02; GA 0,04–0,07; turbośmigłowy 0,08; odrzutowy 0,09.
    'v_v': {
        'piston_ga': [0.03, 0.07],
        'turboprop_regional': [0.06, 0.10],
        'jet_business': [0.06, 0.10],
        'jet_transport': [0.07, 0.11],
        'glider': [0.015, 0.03],
        'motoglider': [0.02, 0.035],
        'uav': [0.02, 0.06],
    },
}

# key, metric, label, symbol, unit, rule, decimals. Rules follow BIPOL_1, s. 1–2:
# "time" — trend in time extrapolated five years ahead, "mass" — eq. (1), "mean" — sample average.
SUGGESTION_SPECS = (
    ('ws', 'wing_loading_kg_m2', 'Obciążenie powierzchni', 'm₀/S', 'kg/m²', 'time', 1),
    ('ar', 'ar', 'Wydłużenie skrzydła', 'AR', '−', 'time', 2),
    ('me_m0', 'empty_fraction', 'Udział masy pustej', 'mₑ/m₀', '−', 'mass', 3),
    ('pw', 'power_loading_kg_kw', 'Obciążenie mocy', 'm₀/P', 'kg/kW', 'time', 2),
    ('tw', 'thrust_to_weight', 'Stosunek ciągu do ciężaru', 'T/W', '−', 'time', 3),
    ('vh', 'v_h', 'Cecha objętościowa usterzenia poziomego', 'V_H', '−', 'mean', 3),
    ('v_v', 'v_v', 'Cecha objętościowa usterzenia pionowego', 'V_V', '−', 'mean', 4),
    ('b_ail_ratio', 'aileron_span_fraction', 'Część rozpiętości objęta lotkami', 'b_ail/(b/2)', '−', 'mean', 3),
    ('c_ail_ratio', 'aileron_chord_ratio', 'Względna cięciwa lotki', 'c_ail/c', '−', 'mean', 3),
    ('c_e_ratio', 'elevator_chord_ratio', 'Względna cięciwa steru wysokości', 'c_e/c_H', '−', 'mean', 3),
    ('c_r_ratio', 'rudder_chord_ratio', 'Względna cięciwa steru kierunku', 'c_r/c_V', '−', 'mean', 3),
    ('dihedral_deg', 'dihedral_deg', 'Wznios', 'Γ', '°', 'mean', 1),
)
PHYSICAL_BOUNDS = {'wing_loading_kg_m2': (1, 2000), 'ar': (2, 60), 'empty_fraction': (.15, .95),
                   'power_loading_kg_kw': (.5, 100), 'thrust_to_weight': (.01, 2)}
BIPOL_1_BASIS = {
    'time': 'BIPOL_1.pdf, s. 1: zależność od roku produkcji ekstrapolowana na 5 lat naprzód',
    'mass': 'BIPOL_1.pdf, s. 1, równanie (1) ze wzorami na A i C; s. 4: równanie (1) wstawia się do równania (5)',
    'mean': 'BIPOL_1.pdf, s. 1: „Obliczyć średnie parametry”',
}


def suggestion_range(key, metric, aircraft_type, wing_configuration):
    """Literature range shown for comparison only; it never replaces the sample result."""
    if key == 'dihedral_deg':
        high = wing_configuration in ('high', 'braced_high', 'strut_braced')
        if aircraft_type in ('piston_ga', 'turboprop_regional'):
            return [0.0, 2.5] if high else [3.5, 7.0]
        if high:
            return [0.0, 3.0]
    if key in SUGGESTION_TYPICAL_RANGES:
        return SUGGESTION_TYPICAL_RANGES[key].get(aircraft_type)
    if metric in GEOMETRY_METRICS_INFO:
        return list(GEOMETRY_METRICS_INFO[metric]['typical_ranges'][aircraft_type][:2])
    return None


def trend_suggestions(rows, params, m0, weights, mass_fit, forecast_year, sample):
    """Design values proposed by the BIPOL_1 trend analysis of one comparison sample, with provenance."""
    engine = params.get('engine_type', 'prop')
    aircraft_type = params.get('aircraft_type', 'piston_ga')
    wing_cfg = params.get('wing_configuration', params.get('wing_config'))
    k_vs = 1.04 if params.get('variable_sweep', False) else 1.
    result = {}
    for key, metric, label, symbol, unit, rule, digits in SUGGESTION_SPECS:
        item = {'key': key, 'name': label, 'symbol': symbol, 'unit': unit, 'suggested_value': None,
                'model_type': None, 'equation': None, 'equation_latex': None, 'r2': None, 'n': 0,
                'available_n': 0, 'stats': None, 'typical_range': None, 'provenance': None}
        result[key] = item
        if key == 'pw' and engine != 'prop' or key == 'tw' and engine != 'jet':
            continue
        item['typical_range'] = suggestion_range(key, metric, aircraft_type, wing_cfg)
        basis = BIPOL_1_BASIS[rule] + ('; s. 2: wydłużenie skrzydła założyć na podstawie analizy trendów' if key == 'ar' else '')
        prov = {'basis': basis, 'sample': sample, 'method': None, 'formula': None, 'steps': [],
                'observations': [], 'x_label': None, 'fit': None, 'alternatives': [], 'warnings': []}
        item['provenance'] = prov
        subset = [r for r in rows if valid_value(metric, r)]
        item['available_n'] = len(subset)
        if not subset:
            prov['method'] = 'Brak obserwacji w próbie'
            prov['warnings'].append('Żadna konstrukcja w próbie nie ma tej wielkości w bazie. Poszerz dobór lub uzupełnij dane; program nie podstawia wartości domyślnej.')
            continue
        values = [r[metric] for r in subset]
        stats = compute_vector_stats(values)
        item['stats'] = {k: round(stats[k], 4) for k in ('min', 'max', 'mean', 'median')}
        sw = weights(subset)
        weighted_sum = sum(v * w for v, w in zip(values, sw))
        mean = weighted_sum / sum(sw)
        mean_label = 'Średnia ważona z próby — każda rodzina ma łączną wagę 1' if any(w != 1 for w in sw) else 'Średnia arytmetyczna z próby'
        unit_text = '' if unit == '−' else ' ' + unit
        mean_steps = [f'Σ wᵢ·xᵢ = {_pl(weighted_sum, 4)}; Σ wᵢ = {_pl(sum(sw), 3)}',
                      f'x̄ = Σ wᵢ·xᵢ / Σ wᵢ = {_pl(mean, digits + 1)}']
        mean_obs = [{'model': r['model'], 'x': None, 'value': r[metric], 'weight': w, 'source': r['source_id']}
                    for r, w in zip(subset, sw)]
        alternative = {'label': f'{mean_label} (n = {len(subset)})', 'value': round(mean, digits)}

        def use_mean(method):
            formula = 'x̄ = Σ wᵢ·xᵢ / Σ wᵢ'
            prov.update(method=method, formula=f"{prov['formula']};  {formula}" if prov['formula'] else formula,
                        observations=prov['observations'] or mean_obs)
            prov['steps'].extend(mean_steps)
            item['equation'] = f'{symbol} = x̄ = {_pl(mean, digits)}'
            item['equation_latex'] = rf'\bar{{x}} = {mean:.{digits}f}'
            return mean, 'mean', len(subset)

        lo, hi = PHYSICAL_BOUNDS.get(metric, (-math.inf, math.inf))
        if rule == 'time':
            date_basis = params.get('trend_year_basis','certification')
            dated_rows = [r for r in rows if (r.get('year_basis') or 'certification')==date_basis]
            dated, fit, forecast = time_trend(dated_rows, metric, weights, forecast_year)
            rejection = forecast_rejection(fit, forecast, metric, forecast_year)
            supported = rejection is None
            if supported:
                value, model, n = forecast, 'time_trend', len(dated)
                date_label = 'Rok produkcji' if date_basis=='production' else 'Rok certyfikacji'
                prov.update(method=f'Trend: {date_label.lower()}, ekstrapolowany na {forecast_year} r.',
                            formula=f'{symbol}(rok) = a·rok + b', x_label=date_label, fit=dict(fit),
                            observations=[{'model': r['model'], 'x': r['year'], 'value': r[metric], 'weight': w,
                                           'source': r['source_id']} for r, w in zip(dated, weights(dated))])
                prov['steps'] += [f"a = {_pl(fit['slope'], 4, True)}{unit_text}/rok; b = {_pl(fit['intercept'], 6, True)}{unit_text}",
                                  f"R² = {_pl(fit['r2'], 3) if fit['r2'] is not None else '—'}; n = {fit['n']}; lata {fit['x_min']:.0f}–{fit['x_max']:.0f}",
                                  f'{symbol}({forecast_year}) = a·{forecast_year} + b = {_pl(forecast, digits + 1)}']
                item['equation'] = f"{symbol} = {_pl(fit['slope'], 4, True)}·rok {'+' if fit['intercept'] >= 0 else '−'} {_pl(abs(fit['intercept']), 6, True)} → {_pl(forecast, digits)} ({forecast_year})"
                item['equation_latex'] = rf"{symbol}({forecast_year}) = {fit['slope']:.4g}\cdot{forecast_year} {'+' if fit['intercept'] >= 0 else '-'} {abs(fit['intercept']):.6g}"
                item['r2'] = round(fit['r2'], 4) if fit['r2'] is not None else None
                gap = forecast_year - fit['x_max']
                if gap > 2 * FORECAST_HORIZON_YEARS:
                    prov['warnings'].append(f"Ekstrapolacja o {gap:.0f} lat poza najnowszą obserwację ({fit['x_max']:.0f} r.). Zweryfikuj aktualność próby.")
            else:
                outside = fit and forecast is not None and lo < forecast < hi
                reason = rejection
                value, model, n = use_mean(f'{mean_label}; prognoza trendu w czasie nie została przyjęta')
                if fit:
                    prov['fit'] = dict(fit)
                    prov['steps'].insert(0, f"Trend: {symbol} = {_pl(fit['slope'], 4, True)}·rok {'+' if fit['intercept'] >= 0 else '−'} {_pl(abs(fit['intercept']), 6, True)}; "
                                            f"R² = {_pl(fit['r2'], 3) if fit['r2'] is not None else '—'}; n = {fit['n']}; {symbol}({forecast_year}) = {_pl(forecast, digits + 1)}")
                if outside:
                    prov['alternatives'].append({'label': f'Prognoza trendu na {forecast_year} r.', 'value': round(forecast, digits)})
                prov['warnings'].append(f'Nie przyjęto prognozy w funkcji roku: {reason}. Zaproponowano średnią z próby.')
        elif rule == 'mass':
            if mass_fit:
                tp = two_point_coefficients(mass_fit)
                prov.update(formula='mₑ/m₀ = A·m₀^C·K_vs;  C = log(y₁/y₂) / log(x₁/x₂);  A = y₁ / x₁^C', x_label='m₀ [kg]', fit={**mass_fit, 'A': tp['A'], 'C': tp['C'], 'k_vs': k_vs},
                            observations=[{'model': r['model'], 'x': r['m0'], 'value': r['empty_fraction'], 'weight': w,
                                           'source': r['source_id']} for r, w in zip(subset, sw)])
                prov['steps'] += [
                    f"Dwa punkty linii trendu: x₁ = {_pl(tp['x1'], 0)} kg, y₁ = {_pl(tp['y1'], 4)}; x₂ = {_pl(tp['x2'], 0)} kg, y₂ = {_pl(tp['y2'], 4)}",
                    f"C = log({_pl(tp['y1'], 4)}/{_pl(tp['y2'], 4)}) / log({_pl(tp['x1'], 0)}/{_pl(tp['x2'], 0)}) = {_pl(tp['C'], 5)}",
                    f"A = y₁ / x₁^C = {_pl(tp['A'], 5)}",
                    f"K_vs = {_pl(k_vs, 2)} ({'skos zmienny wzdłuż rozpiętości' if k_vs != 1 else 'skos stały'})"]
                item['apply'] = {'empty_mass_model': 'trend', 'empty_mass_trend_A': tp['A'],
                                 'empty_mass_trend_C': tp['C'], 'empty_mass_fraction': None}
                item['r2'] = round(mass_fit['r2'], 4) if mass_fit['r2'] is not None else None
                item['equation'] = f"mₑ/m₀ = {_pl(tp['A'], 4, True)}·m₀^{_pl(tp['C'], 4, True)}·{_pl(k_vs, 2)}"
                item['equation_latex'] = rf"m_e/m_0 = {tp['A']:.4g}\cdot m_0^{{{tp['C']:.4g}}}\cdot{k_vs:.2f}"
                prediction = predict(mass_fit, m0) if m0 else None
                equation_value = prediction * k_vs if prediction is not None else None
                if equation_value is not None and lo < equation_value < hi:
                    value, model, n = equation_value, 'power', mass_fit['n']
                    prov['method'] = 'Równanie (1): linia trendu mₑ/m₀ = f(m₀) z próby'
                    prov['steps'].append(f"mₑ/m₀ = {_pl(tp['A'], 5)}·{_pl(m0, 0)}^{_pl(tp['C'], 5)}·{_pl(k_vs, 2)} = {_pl(equation_value, 4)}")
                    item['equation'] += f' = {_pl(equation_value, 3)}'
                    if not mass_fit['x_min'] <= m0 <= mass_fit['x_max']:
                        prov['warnings'].append(f"Masa projektu {_pl(m0, 0)} kg leży poza zakresem próby ({_pl(mass_fit['x_min'], 0)}–{_pl(mass_fit['x_max'], 0)} kg); wynik jest ekstrapolacją.")
                else:
                    value, model, n = use_mean(f'{mean_label}; równanie (1) wymaga masy projektu' if not m0 else
                                               f'{mean_label}; równanie (1) daje wartość niefizyczną')
                    if m0:
                        prov['warnings'].append('Dla masy projektu równanie (1) daje udział spoza zakresu 0,15–0,95. Zaproponowano średnią z próby.')
                    else:
                        prov['warnings'].append('Masa projektu nie jest jeszcze znana. „Zastosuj” wstawia równanie (1) do bilansu masy; jako liczbę pokazano średnią z próby.')
                if mass_fit['C'] >= 0:
                    prov['warnings'].append('C ≥ 0: udział masy pustej nie maleje z masą startową. Sprawdź dobór próby i definicje mas.')
            else:
                value, model, n = use_mean(f'{mean_label}; za mało zróżnicowanych mas do linii trendu')
                item['apply'] = {'empty_mass_model': 'trend'}
                prov['warnings'].append('Linia trendu wymaga co najmniej 3 konstrukcji o różnych masach.')
        else:
            value, model, n = use_mean(mean_label)
        item.update(suggested_value=round(value, digits), model_type=model, n=n)
        if n < 3:
            prov['warnings'].append('Mniej niż 3 obserwacje: wartość orientacyjna. Poszerz próbę, np. „Wszystkie pasujące”.')
        elif n < BIPOL_1_SAMPLE:
            prov['warnings'].append(f'n = {n}: mniej niż 20 samolotów zalecanych w BIPOL_1.')
        rng = item['typical_range']
        if rng and not rng[0] <= value <= rng[1]:
            prov['warnings'].append(
                f"Wartość poza orientacyjnym zakresem literaturowym {_pl(rng[0], 2)}–{_pl(rng[1], 2)}{'' if unit == '−' else ' ' + unit}." +
                (' Baza nie rozróżnia dolno- i górnopłatów, więc średnia może mieszać układy skrzydła.' if key == 'dihedral_deg' else ''))
    return result


def get_trend_suggestions(aircraft_type, m0=None, wing_configuration=None, engine_type=None, settings=None, project=None):
    """BIPOL_1 suggestions before a project is calculated (wizard, input panel).

    The sample is the project's own comparison sample (settings), so the values
    match the P1 trend analysis; m0 only evaluates equation (1), it never selects aircraft.
    """
    if aircraft_type not in CLASSES:
        raise ValueError(f"Unknown aircraft_type: '{aircraft_type}'")
    if m0 is not None:
        try:
            m0 = float(m0)
            if not math.isfinite(m0) or m0 <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("m0 must be a positive finite number") from None
    engine = engine_type or DEFAULT_ENGINE.get(aircraft_type, 'prop')
    if engine not in ENGINE_LABELS:
        raise ValueError(f"Unknown engine_type: '{engine_type}'")
    # The sample around the design mass needs the whole project (its mission); the wizard and the
    # input panel send it and get the very analysis of the calculated project.
    settings = settings if settings is not None else project
    if project is not None:
        from calculations import run_bipol_project
        result = run_bipol_project({**project, 'aircraft_type': aircraft_type, 'engine_type': engine,
                                   **({'wing_config': wing_configuration} if wing_configuration else {})})
        ta, params = result['bipol_projects']['p1']['trend_analysis'], result['params']
        weights = sample_weights(params.get('trend_weighting', 'family'))
        return {'status': 'ok', 'aircraft_type': aircraft_type, 'class_name': CLASSES[aircraft_type],
                'engine_type': engine, 'm0': result['mass']['m0'], 'sample': ta['sample'],
                'reference_year': ta['reference_year'], 'forecast_year': ta['forecast_year'],
                'suggestions': ta['suggestions'],
                'charts': wizard_trend_charts(ta['similar_aircraft'], params, weights, ta['mass_fit'],
                                              ta['forecast_year'], ta['suggestions'])}
    # Without the project m0 (if given) is the design mass; otherwise the whole class is the sample.
    params = {**sample_settings(settings or {}), 'aircraft_type': aircraft_type, 'engine_type': engine,
              'wing_configuration': wing_configuration, '_reference_mass': m0,
              '_similar_count': int((settings or {}).get('trend_nearest_count', SIMILAR_COUNT) or 0) if m0 else 0}
    rows = select_references(params)
    weights = sample_weights(params.get('trend_weighting', 'family'))
    valid_mass, mass_fit = mass_trend(params, rows)
    reference_year, forecast_year = forecast_years()
    sample = describe_sample(params, rows)
    return {'status': 'ok', 'aircraft_type': aircraft_type, 'class_name': CLASSES[aircraft_type],
            'engine_type': engine, 'm0': m0, 'sample': sample,
            'reference_year': reference_year, 'forecast_year': forecast_year,
            'suggestions': (sugg := trend_suggestions(rows, params, m0, weights, mass_fit, forecast_year, sample)),
            'charts': wizard_trend_charts(rows, params, weights, mass_fit, forecast_year, sugg)}


def wizard_trend_charts(rows, params, weights, mass_fit, forecast_year, suggestions):
    """Compact plot series for interactive BIPOL_1 trend charts inside the project wizard."""
    engine = params.get('engine_type', 'prop')
    date_basis, time_rows = dated_rows(rows)
    date_label = 'Rok produkcji' if date_basis == 'production' else 'Rok certyfikacji'
    charts = {}

    def add_time(sugg_key, metric, title, y_label, unit, symbol):
        subset, fit, forecast = time_trend(time_rows, metric, weights, forecast_year)
        s = suggestions.get(sugg_key)
        lo, hi = PHYSICAL_BOUNDS.get(metric, (0.0, math.inf))
        forecast_ok = bool(fit and forecast is not None and lo < forecast < hi)
        accepted = bool(s and s.get('model_type') == 'time_trend')
        charts[sugg_key] = {
            'key': sugg_key, 'kind': 'time', 'title': title, 'symbol': symbol, 'unit': unit,
            'x_label': date_label, 'y_label': y_label, 'n': len(subset),
            'points': [{'x': r['year'], 'y': round(r[metric], 4), 'model': r['model']} for r in subset],
            'fit': fit,
            'forecast': {'x': forecast_year, 'y': round(forecast, 4), 'accepted': accepted} if forecast_ok else None,
            'suggested_value': s['suggested_value'] if s else None,
            'typical_range': s['typical_range'] if s else None,
            'equation': s['equation'] if s else None,
        }

    add_time('ar', 'ar', 'Wydłużenie skrzydła AR w funkcji roku', 'Wydłużenie AR [−]', '−', 'AR')
    add_time('ws', 'wing_loading_kg_m2', 'Obciążenie powierzchni m₀/S w funkcji roku', 'm₀/S [kg/m²]', 'kg/m²', 'm₀/S')
    if engine == 'prop':
        add_time('pw', 'power_loading_kg_kw', 'Obciążenie mocy m₀/P w funkcji roku', 'm₀/P [kg/kW]', 'kg/kW', 'm₀/P')
    elif engine == 'jet':
        add_time('tw', 'thrust_to_weight', 'Stosunek ciągu do ciężaru T/W w funkcji roku', 'T/W [−]', '−', 'T/W')

    valid_mass = [r for r in rows if valid_value('empty_fraction', r)]
    me_s = suggestions.get('me_m0', {})
    charts['me_m0'] = {
        'key': 'me_m0', 'kind': 'mass', 'title': 'Udział masy pustej mₑ/m₀ w funkcji MTOW',
        'symbol': 'mₑ/m₀', 'unit': '−', 'x_label': 'Masa startowa MTOW m₀ [kg]', 'y_label': 'OEW / MTOW mₑ/m₀ [−]',
        'n': len(valid_mass),
        'points': [{'x': round(r['m0'], 1), 'y': round(r['empty_fraction'], 4), 'model': r['model']} for r in valid_mass],
        'fit': mass_fit, 'forecast': None,
        'suggested_value': me_s.get('suggested_value'), 'typical_range': me_s.get('typical_range'),
        'equation': me_s.get('equation'),
    }

    speed_key = ('cruise_mach' if sum(r.get('cruise_mach') is not None for r in rows) >
                 sum(r.get('v_cruise_kmh') is not None for r in rows) else 'v_cruise_kmh')
    speed_sub = [r for r in rows if r.get('wing_loading_kg_m2') is not None and r.get(speed_key) is not None]
    speed_fit = fit_regression([(r['wing_loading_kg_m2'], r[speed_key]) for r in speed_sub], weights(speed_sub))
    is_mach = speed_key == 'cruise_mach'
    charts['ws_speed'] = {
        'key': 'ws_speed', 'kind': 'relation', 'speed_metric': speed_key,
        'title': 'Liczba Macha przelotu a obciążenie powierzchni' if is_mach else 'Prędkość przelotowa a obciążenie powierzchni',
        'symbol': 'Ma' if is_mach else 'V_cr', 'unit': 'Ma' if is_mach else 'km/h',
        'x_label': 'Obciążenie powierzchni m₀/S [kg/m²]',
        'y_label': 'Liczba Macha Ma [−]' if is_mach else 'Prędkość przelotowa V_cr [km/h]',
        'n': len(speed_sub),
        'points': [{'x': round(r['wing_loading_kg_m2'], 2), 'y': round(r[speed_key], 3), 'model': r['model']} for r in speed_sub],
        'fit': speed_fit, 'forecast': None, 'suggested_value': None, 'typical_range': None, 'equation': None,
    }

    rng_sub = [r for r in rows if valid_value('ar', r) and r.get('range_km') is not None]
    rng_fit = fit_regression([(r['ar'], r['range_km']) for r in rng_sub], weights(rng_sub))
    charts['rng_ar'] = {
        'key': 'rng_ar', 'kind': 'relation',
        'title': 'Zasięg katalogowy R w funkcji wydłużenia AR',
        'symbol': 'R', 'unit': 'km', 'x_label': 'Wydłużenie skrzydła AR [−]', 'y_label': 'Zasięg R [km]',
        'n': len(rng_sub),
        'points': [{'x': round(r['ar'], 2), 'y': round(r['range_km'], 1), 'model': r['model']} for r in rng_sub],
        'fit': rng_fit, 'forecast': None, 'suggested_value': None, 'typical_range': None, 'equation': None,
    }

    for sugg_key, metric, label, symbol, unit in (
        ('vh', 'v_h', 'Cecha objętościowa usterzenia poziomego V_H', 'V_H', '−'),
        ('dihedral_deg', 'dihedral_deg', 'Kąt wzniosu skrzydła Γ', 'Γ', '°'),
        ('b_ail_ratio', 'aileron_span_fraction', 'Część rozpiętości objęta lotkami b_ail/(b/2)', 'b_ail/(b/2)', '−'),
        ('c_ail_ratio', 'aileron_chord_ratio', 'Względna cięciwa lotki c_ail/c', 'c_ail/c', '−'),
        ('c_e_ratio', 'elevator_chord_ratio', 'Względna cięciwa steru wysokości c_e/c_H', 'c_e/c_H', '−'),
        ('c_r_ratio', 'rudder_chord_ratio', 'Względna cięciwa steru kierunku c_r/c_V', 'c_r/c_V', '−'),
        ('v_v', 'v_v', 'Cecha objętościowa usterzenia pionowego V_V', 'V_V', '−'),
    ):
        sub = [r for r in rows if r.get('m0') is not None and valid_value(metric, r)]
        s = suggestions.get(sugg_key, {})
        charts[sugg_key] = {
            'key': sugg_key, 'kind': 'mean', 'title': f'{label} względem MTOW',
            'symbol': symbol, 'unit': unit, 'x_label': 'Masa startowa MTOW m₀ [kg]',
            'y_label': f'{symbol} [{unit}]', 'n': len(sub),
            'points': [{'x': round(r['m0'], 1), 'y': round(r[metric], 4), 'model': r['model']} for r in sub],
            'fit': None, 'forecast': None,
            'suggested_value': s.get('suggested_value'), 'typical_range': s.get('typical_range'),
            'equation': s.get('equation'),
        }

    return charts
