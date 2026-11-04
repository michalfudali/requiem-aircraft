"""Official BIPOL I topics of the designed aircraft.

The catalogue — titles, categories, starting parameters and requirements of all topics —
is stored in the projects database (data/projects/projects.sqlite3); this module keeps
only the checks of a project against the requirements of its topic.
"""
from calculations.project_store import load_categories, load_topics

OFFICIAL_CATEGORIES = load_categories()
ALL_TOPICS = load_topics()


def _topic(params):
    return next((t for t in ALL_TOPICS if str(t['num']) == str(params.get('topic_id'))), None)


def validate_topic_geometry(params, geometry):
    if params.get('topic_origin') != 'official':
        return
    topic = _topic(params)
    required = topic['requirements'] if topic else {}
    span = float(params.get('wingspan_m') or geometry['wing']['b'])
    if 'span_above_m' in required and span <= required['span_above_m']:
        raise ValueError(f"Wybrany temat wymaga rozpiętości większej niż {required['span_above_m']:g} m. "
                         'Zmień niezależne założenia skrzydła albo wybierz własny temat.')
    prescribed = required.get('span_exact_m')
    if prescribed and abs(span - prescribed) > .005:
        raise ValueError(f'Wybrany temat wymaga rozpiętości {prescribed:g} m. '
                         'Zachowaj tę rozpiętość albo wybierz własny temat.')


def check_topic_requirements(params, sizing):
    if params.get('topic_origin') != 'official':
        return []
    topic = _topic(params)
    if topic is None:
        return [dict(parameter='[Temat] Numer oficjalnego tematu', required='Temat z katalogu',
                     actual=str(params.get('topic_id')), passed=False,
                     note='Wybierz istniejący temat albo oznacz projekt jako własny.')]
    requirements = topic['requirements']
    labels = dict(n_pax='Liczba pasażerów', n_engines='Liczba silników', engine_type='Rodzaj napędu',
                  operating_surface='Środowisko startu i lądowania', category='Przeznaczenie akrobacyjne',
                  wing_config='Układ skrzydła', seats_config='Rozmieszczenie miejsc')
    checks = [dict(parameter=f"[Temat {topic['num']}] {labels[key]}", required=str(expected),
                   actual=str(params.get(key)), passed=params.get(key) == expected,
                   note='Wymaganie oficjalnego tematu. Odstępstwo wymaga zmiany tematu lub projektu własnego.')
              for key, expected in requirements.items() if key in labels]
    if 'power_per_engine_max_kw' in requirements:
        power = sizing['design_point'].get('power_kw')
        limit = requirements['power_per_engine_max_kw'] * requirements['n_engines']
        checks.append(dict(parameter=f"[Temat {topic['num']}] Maksymalna moc zainstalowana",
                           required=f'≤ {limit:g} kW', actual=f'{power:g} kW' if power is not None else 'Nie wyznaczono',
                           passed=power is not None and power <= limit + 1e-6,
                           note='Limit mocy jednego silnika z treści tematu × wymagana liczba silników.'))
    if 'cargo_min_kg' in requirements:
        cargo = params.get('m_cargo', 0)
        checks.append(dict(parameter=f"[Temat {topic['num']}] Ładunek zadaniowy",
                           required=f"≥ {requirements['cargo_min_kg']:g} kg", actual=f'{cargo:g} kg',
                           passed=cargo >= requirements['cargo_min_kg'],
                           note='Sprawdzenie masy ładunku nie potwierdza wymiarów, mocowania ani przestrzeni ładunkowej.'))
    return checks
