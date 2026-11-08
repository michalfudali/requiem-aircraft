"""Official BIPOL I topics of the designed aircraft.

The catalogue — titles, categories, starting parameters and requirements of all topics —
is stored in the projects database (data/projects/projects.sqlite3); this module keeps
only the checks of a project against the requirements of its topic.
"""
from calculations.polish_law import resolve_category
from calculations.project_store import load_categories, load_topics


def explicit_topic_requirements(topic):
    """Include configuration constraints stated in the official topic title.

    Older course databases omit some constraints from the requirements object,
    while retaining both the official wording and its configuration in defaults.
    Normalize the read model, without rewriting anyone's saved project inputs.
    """
    required = dict(topic['requirements'])
    title = topic['title'].casefold()
    if 'jednomiejscow' in title:
        required['occupants_exact'] = 1
    elif 'dwumiejscow' in title:
        required['occupants_exact'] = 2
    if 'zespół napędowy' in title and any(word in title for word in ('ciągnący', 'pchający', 'chowany')):
        required['engine_location'] = ('nose' if 'ciągnący' in title else
                                       'rear' if 'pchający' in title else 'retractable')
    return required


OFFICIAL_CATEGORIES = load_categories()
ALL_TOPICS = [dict(topic, requirements=explicit_topic_requirements(topic)) for topic in load_topics()]


def _topic(params):
    return next((t for t in ALL_TOPICS if str(t['num']) == str(params.get('topic_id'))), None)


def fixed_occupants(params):
    """Number of people the title of an official topic prescribes, otherwise None."""
    topic = _topic(params) if params.get('topic_origin') == 'official' else None
    return topic['requirements'].get('occupants_exact') if topic else None


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
                  wing_config='Układ skrzydła', seats_config='Rozmieszczenie miejsc',
                  engine_location='Zabudowa zespołu napędowego')
    names = {'prop': 'śmigłowy', 'jet': 'odrzutowy', 'none': 'bez napędu', 'land': 'ląd', 'water': 'woda',
             'amphibian': 'ląd i woda', 'nose': 'w nosie kadłuba', 'rear': 'z tyłu kadłuba', 'retractable': 'chowany',
             'wing': 'na skrzydle'}

    def shown(value):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return names.get(value, str(value)) if isinstance(value, str) else str(value)
    def same(key, expected):
        if key == 'category':  # stored topics may keep the former level keys
            return resolve_category(params.get(key)) == resolve_category(expected)
        return params.get(key) == expected
    checks = [dict(parameter=f"[Temat {topic['num']}] {labels[key]}",
                   required=resolve_category(expected) if key == 'category' else shown(expected),
                   actual=resolve_category(params.get(key)) if key == 'category' else shown(params.get(key)),
                   passed=same(key, expected),
                   note='Wymaganie oficjalnego tematu. Odstępstwo wymaga zmiany tematu lub projektu własnego.')
              for key, expected in requirements.items() if key in labels]
    if 'occupants_exact' in requirements:
        occupants = int(params.get('n_crew', 0)) + int(params.get('n_pax', 0))
        checks.append(dict(parameter=f"[Temat {topic['num']}] Liczba osób na pokładzie",
                           required=str(requirements['occupants_exact']), actual=str(occupants),
                           passed=occupants == requirements['occupants_exact'],
                           note='Liczba miejsc z treści tematu obejmuje załogę i pasażerów.'))
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
