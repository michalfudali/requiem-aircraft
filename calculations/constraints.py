"""Independent design assumptions, dependent outputs and suggested constraints.

The wing uses one independent pair from (span, area, aspect ratio), or automatic
area sizing from the stall requirement. Payload includes passenger baggage;
known engine power is used by both sizing and subsequent performance checks.
"""
import math

LOCKABLE_PARAMETERS = {
    'wingspan_m': {'label': 'Rozpiętość skrzydła b', 'unit': 'm', 'stage': 'P3', 'triad': 'wing_geom'},
    'aspect_ratio': {'label': 'Wydłużenie skrzydła Λ (AR)', 'unit': '−', 'stage': 'P3', 'triad': 'wing_geom'},
    'wing_area_m2': {'label': 'Powierzchnia skrzydła S', 'unit': 'm²', 'stage': 'P3', 'triad': 'wing_geom'},
    'n_pax': {'label': 'Liczba pasażerów', 'unit': 'os.', 'stage': 'P1', 'triad': 'payload'},
    'n_crew': {'label': 'Liczba załogi (pilotów)', 'unit': 'os.', 'stage': 'P1', 'triad': 'payload'},
    'm_cargo': {'label': 'Ładunek cargo / wyposażenie', 'unit': 'kg', 'stage': 'P1', 'triad': 'payload'},
    'm_payload': {'label': 'Masa płatna łączna', 'unit': 'kg', 'stage': 'P1', 'triad': 'payload'},
    'engine_power_kw': {'label': 'Maksymalna moc silnika P_max', 'unit': 'kW', 'stage': 'P5', 'triad': 'propulsion'},
    'range_km': {'label': 'Maksymalny zasięg obliczeniowy R', 'unit': 'km', 'stage': 'P1', 'triad': 'mission'},
    'cruise_speed_kmh': {'label': 'Prędkość przelotowa V_cr', 'unit': 'km/h', 'stage': 'P1', 'triad': 'mission'},
    'v_stall_kmh': {'label': 'Prędkość przeciągnięcia Vs0', 'unit': 'km/h', 'stage': 'P1', 'triad': 'stall'},
    'wing_planform': {'label': 'Obrys skrzydła', 'unit': 'typ', 'stage': 'P3', 'triad': 'planform'},
}

WING_PLANFORMS = {
    'trapezoidal': {
        'id': 'trapezoidal',
        'name_pl': 'Trapezowy (zbieżny klasyczny)',
        'description': 'Optymalny kompromis aerodynamiczno-wytrzymałościowy. Zbieżność redukuje masę dźwigarów i moment gnący w nasadzie.',
        'stall_behavior': 'Sam obrys nie przesądza o przeciągnięciu. Sprawdź profile, zwichrzenie, mechanizację i rozkład lokalnego Cz.'
    },
    'rectangular': {
        'id': 'rectangular',
        'name_pl': 'Prostokątny (stała cięciwa)',
        'description': 'Maksymalna prostota technologiczna (jednakowe żebra i poszycie wzdłuż całej rozpiętości). Wyższy opór indukowany niż w skrzydle trapezowym.',
        'stall_behavior': 'Sam obrys nie przesądza o przeciągnięciu. Sprawdź profile, zwichrzenie, mechanizację i rozkład lokalnego Cz.'
    },
    'compound_trapezoid': {
        'id': 'compound_trapezoid',
        'name_pl': 'Prostokątno-trapezowy',
        'description': 'Centropłat prostokątny ułatwia montaż klap, podwozia i zbiorników; końcówki trapezowe redukują indukowany opór (układ Piper Cherokee/Archer, Cessna 172, Wilga).',
        'stall_behavior': 'Sam obrys nie przesądza o przeciągnięciu. Sprawdź profile, zwichrzenie, mechanizację i rozkład lokalnego Cz.'
    },
    'elliptical': {
        'id': 'elliptical',
        'name_pl': 'Eliptyczny (minimalny opór indukowany)',
        'description': 'Teoretycznie optymalny rozkład siły nośnej wg Prandtla (współczynnik e = 1.0). Bardzo wysoki koszt produkcji i trudna technologia wykonania żeber (układ Supermarine Spitfire).',
        'stall_behavior': 'Sam obrys nie przesądza o przeciągnięciu. Sprawdź profile, zwichrzenie, mechanizację i rozkład lokalnego Cz.'
    },
    'swept_trapezoidal': {
        'id': 'swept_trapezoidal',
        'name_pl': 'Skośny trapezowy',
        'description': 'Skos krawędzi natarcia przesuwa krytyczną liczbę Macha ku wyższym prędkościom. Stosowany w odrzutowcach dyspozycyjnych i komunikacyjnych.',
        'stall_behavior': 'Sam obrys nie przesądza o przeciągnięciu. Sprawdź profile, zwichrzenie, mechanizację i rozkład lokalnego Cz.'
    }
}


def get_initial_constraint_suggestions(category: str, aircraft_type: str) -> list[dict]:
    """Working design choices, without inventing universal certification limits."""
    from calculations.presets import AIRCRAFT_PRESETS
    name = {'piston_ga':'ga_trainer', 'glider':'glider_pw5', 'motoglider':'motoglider_aos',
            'turboprop_regional':'regional_turboprop', 'jet_business':'vlj_jet',
            'jet_transport':'vlj_jet', 'uav':'uav_male'}.get(aircraft_type, 'ga_trainer')
    base = AIRCRAFT_PRESETS[name]
    values = [('aspect_ratio','Wydłużenie skrzydła — wartość startowa',base['aspect_ratio'],'−'),
              ('v_stall_kmh','VS0 — robocze wymaganie projektu',base['v_stall_kmh'],'km/h'),
              ('m_pax','Pasażer z bagażem według wytycznych zajęć',115.,'kg')]
    if base['engine_type'] != 'none':
        values.append(('takeoff_distance_m','Długość startu do wysokości 15 m',base['takeoff_distance_m'],'m'))
    return [dict(id='sugg_'+key,param=key,title=title,value=value,unit=unit,
        description='Założenie robocze do sprawdzenia względem misji i wybranej kategorii. Nie stanowi uniwersalnego limitu zdatności.',
        standard='Profil klasy / wytyczne BIPOL',icon='📐') for key,title,value,unit in values]


def resolve_and_lock_parameters(params: dict, locked_keys: list = None) -> tuple[dict, dict, list]:
    """Resolve independent inputs before any mass, sizing or performance calculation.

    VS0 is a maximum requirement. With a specified wing area it remains a check,
    rather than a second, conflicting prescription for that same area.
    """
    p = dict(params)
    locked = set(locked_keys if locked_keys is not None else p.get('locked_params', []))
    if 'm0' in locked or 'wing_loading_kg_m2' in locked:
        raise ValueError('Masa startowa i obciążenie powierzchni są wynikami bilansu. '
                         'Jako założenia wybierz masę płatną i niezależne wymiary skrzydła.')
    states = {}
    warnings = []

    def state(key, value, formula=None, sources=()):
        p[key] = value
        states[key] = {'state': 'derived' if formula else ('locked' if key in locked else 'input'),
                       'value': value}
        if formula:
            states[key].update(formula=formula, sources=list(sources))
            locked.discard(key)

    span = float(p.get('wingspan_m') or p.get('span_limit') or 0)
    area = float(p.get('wing_area_m2') or 0)
    aspect = float(p['aspect_ratio'])
    if not p.get('wing_input_mode') and {'wingspan_m','wing_area_m2','aspect_ratio'} <= locked:
        raise ValueError('Wybierz dwa niezależne wymiary skrzydła; trzeci musi wynikać z b² = S · Λ.')
    mode = p.get('wing_input_mode')
    if not mode:
        mode = ('span_area' if span and area and 'wing_area_m2' in locked else
                'span_aspect' if span else 'area_aspect' if area else 'loading')
    p['wing_input_mode'] = mode
    if mode in ('span_aspect', 'span_area') and span <= .5:
        raise ValueError('Pole wingspan_m: podaj dodatnią rozpiętość dla wybranych założeń skrzydła.')
    if mode in ('span_area', 'area_aspect') and area < .5:
        raise ValueError('Pole wing_area_m2: podaj powierzchnię co najmniej 0,5 m².')
    if mode == 'span_aspect':
        state('wingspan_m', span)
        state('aspect_ratio', aspect)
        state('wing_area_m2', span ** 2 / aspect, 'S = b² / Λ', ('wingspan_m','aspect_ratio'))
    elif mode == 'span_area':
        aspect = span ** 2 / area
        if not 2 <= aspect <= 35:
            raise ValueError('Podana rozpiętość i powierzchnia dają Λ poza zakresem 2–35. '
                             'Zwiększ powierzchnię lub wybierz założenia „rozpiętość i wydłużenie”.')
        state('wingspan_m', span)
        state('wing_area_m2', area)
        state('aspect_ratio', aspect, 'Λ = b² / S', ('wingspan_m','wing_area_m2'))
    elif mode == 'area_aspect':
        state('wing_area_m2', area)
        state('aspect_ratio', aspect)
        state('wingspan_m', math.sqrt(area * aspect), 'b = √(S · Λ)', ('wing_area_m2','aspect_ratio'))
    else:
        # Discard cached outputs from a previous calculation or a different basis.
        p['wingspan_m'] = p['wing_area_m2'] = 0.0
        state('aspect_ratio', aspect)
    p['span_limit'] = 0.0  # The resolved mode, rather than this legacy alias, controls geometry.

    unmanned = p.get('aircraft_type') == 'uav' or str(p.get('category', '')).startswith('easa_uas_')
    if unmanned:
        state('n_pax', 0, 'Statek bezzałogowy: 0 pasażerów', ('aircraft_type',))
        state('n_crew', 0, 'Statek bezzałogowy: 0 osób załogi na pokładzie', ('aircraft_type',))
    per_person = float(p.get('m_pax', 80)) + float(p.get('m_bag', 0))
    passengers_mass = int(p['n_pax']) * per_person
    payload_mode = p.get('payload_input_mode') or ('total' if 'm_payload' in locked else 'seats')
    p['payload_input_mode'] = payload_mode
    if payload_mode == 'total':
        payload = float(p.get('m_payload', 0))
        cargo = payload - passengers_mass
        if cargo < -1e-8:
            raise ValueError('Masa płatna jest mniejsza od masy pasażerów z bagażem. '
                             'Zwiększ masę płatną albo zmniejsz liczbę pasażerów.')
        state('m_payload', payload)
        state('m_cargo', max(0.0, cargo), 'm_cargo = m_payload − n_pax · (m_pax + m_bag)',
              ('m_payload','n_pax','m_pax','m_bag'))
    else:
        state('m_cargo', float(p.get('m_cargo', 0)))
        state('m_payload', passengers_mass + p['m_cargo'],
              'm_payload = n_pax · (m_pax + m_bag) + m_cargo', ('n_pax','m_pax','m_bag','m_cargo'))
    state('n_pax', p['n_pax'], states.get('n_pax', {}).get('formula'), ('aircraft_type',))

    power_mode = p.get('power_input_mode') or ('fixed' if 'engine_power_kw' in locked else 'sized')
    p['power_input_mode'] = power_mode
    if power_mode == 'fixed':
        locked.add('engine_power_kw')
    else:
        locked.discard('engine_power_kw')
    if p['engine_type'] == 'none':
        for key in ('sfc','engine_power_kw','takeoff_run_m','takeoff_distance_m','climb_rate_ms'):
            state(key, 0.0, 'Nie dotyczy lotu bez napędu', ('engine_type',))
        p['engine_location'] = 'none'
        p['power_input_mode'] = 'sized'
        locked.discard('engine_power_kw')
    elif 'engine_power_kw' in locked:
        if p['engine_type'] != 'prop' or float(p.get('engine_power_kw', 0)) <= 0:
            raise ValueError('Stała moc silnika wymaga napędu śmigłowego i dodatniej mocy w kW.')
        state('engine_power_kw', float(p['engine_power_kw']))
    elif p['engine_type'] == 'prop':
        # A saved project also contains the last automatically sized rating.
        # It is an output, not an installed-engine assumption for the next mass
        # breakdown. A known rating is used only in explicit fixed-power mode.
        state('engine_power_kw', 0.0, 'Automatyczny dobór mocy po bilansie masy', ('power_input_mode',))

    planform = p.get('wing_planform', 'trapezoidal')
    state('wing_planform', planform)
    if planform in ('rectangular', 'elliptical'):
        state('taper_ratio', 1.0 if planform == 'rectangular' else 0.0,
              'Zbieżność wynika z wybranego obrysu skrzydła', ('wing_planform',))
    for key in sorted(locked):
        if key in p and key not in states:
            state(key, p[key])
    p['locked_params'] = sorted(locked)
    return p, states, warnings


def finalize_parameter_states(params, states, mass, sizing, geometry):
    """Expose computed quantities as outputs, including the automatic sizing mode."""
    wing = geometry['wing']
    mode = params['wing_input_mode']
    values = {'wing_area_m2': wing['S'], 'wingspan_m': wing['b'], 'aspect_ratio': wing['AR'],
              'm_payload': mass['m_payload'], 'wing_loading_kg_m2': mass['m0'] / wing['S']}
    derived = {'wing_loading_kg_m2': ('m₀ / S', ['m0','wing_area_m2'])}
    for key in ('flap_takeoff_deg', 'flap_landing_deg'):
        values[key] = params[key]
        derived[key] = ('Wychylenie klap w stopniach według wytycznych prowadzącego', ['flap_type'])
    if mode == 'loading':
        derived.update(wing_area_m2=('S = m₀g / (W/S)', ['m0','v_stall_kmh']),
                       wingspan_m=('b = √(S · Λ)', ['wing_area_m2','aspect_ratio']))
    if params['engine_type'] == 'prop' and 'engine_power_kw' not in params['locked_params']:
        values['engine_power_kw'] = sizing['design_point']['power_kw']
        derived['engine_power_kw'] = ('Moc wyznaczona z diagramu doboru', ['range_km','cruise_speed_kmh','climb_rate_ms'])
    if params.get('_engine_fuel', {}).get('supported') and params['engine_type'] != 'none':
        values['sfc'] = params['sfc']
        derived['sfc'] = ('Zużycie z dokumentacji rzeczywistego silnika; przeliczenie jednostek punktu pracy',
                          ['engine_model_id', 'engine_fuel_point', 'fuel_density_kg_l'])
    for key, value in values.items():
        if key in states and states[key]['state'] != 'derived' and key not in derived:
            value = params[key]
        else:
            params[key] = value
        if key in derived:
            formula, sources = derived[key]
            states[key] = {'state': 'derived', 'value': value, 'formula': formula, 'sources': sources}
        elif key in states:
            states[key]['value'] = value
    params['locked_params'] = sorted(set(params['locked_params']) -
                                    {key for key, info in states.items() if info['state'] == 'derived'})


def calculate_constraint_curves(params: dict, m0: float = None, mass: dict = None) -> dict:
    """Interface contract function M1 <-> M2: matching chart constraint curves."""
    from calculations.sizing import calculate_constraint_curves as _calc
    return _calc(params, m0=m0, mass=mass)

