"""Real engine proposals and traceable fuel data. A catalogue point is not an engine map."""
from copy import deepcopy
from functools import lru_cache
import math

from calculations.atmosphere import G0

US_GALLON_L = 3.785411784


@lru_cache(maxsize=1)
def _catalog():
    # Engine proposals live in the comparison-aircraft database (table engines).
    from calculations import aircraft_store
    return aircraft_store.engines()


def catalog():
    return deepcopy(_catalog())


def normalized_sfc(point, density=.72, engine_type='prop'):
    """Return g/(kW h) for shaft engines and cT*g [1/h] for jets."""
    value, unit = float(point['value']), point['unit']
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Zużycie paliwa w punkcie pracy musi być dodatnie i skończone.')
    if engine_type == 'jet':
        if unit == 'kg/(N h)':
            return value * G0
        if unit == '1/h':
            return value
        raise ValueError('Dla silnika odrzutowego wymagane kg/(N h) albo cT·g w 1/h.')
    if unit == 'g/(kW h)':
        return value
    if unit == 'kg/(kW h)':
        return value * 1000
    if unit not in ('l/h', 'US gal/h'):
        raise ValueError('Nieznana jednostka zużycia paliwa silnika śmigłowego.')
    power = float(point.get('power_kw', 0))
    if not math.isfinite(power) or power <= 0 or not .5 <= density <= 1.0:
        raise ValueError('Przeliczenie przepływu wymaga dodatniej mocy punktu i gęstości paliwa 0,5–1 kg/l.')
    return value * (US_GALLON_L if unit == 'US gal/h' else 1) * density * 1000 / power


def _text(p, key, label, minimum=1):
    value = p.get(key, '')
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= 2000:
        raise ValueError(f'Dane silnika: uzupełnij {label} (do 2000 znaków).')
    return value.strip()


def apply_engine_inputs(p):
    """Rebuild evidence from independent choices; cached metadata never authenticates a number."""
    p.pop('_engine_fuel', None)
    mode = p.get('engine_fuel_mode', 'unselected')
    if mode not in ('unselected', 'catalog', 'custom'):
        raise ValueError('Nieznany sposób określenia danych paliwowych silnika.')
    engine = p.get('engine_type', 'prop')
    if engine == 'none':
        p['_engine_fuel'] = dict(status='not_applicable', supported=True, model='Bez napędu', notes=[])
        p.pop('engine_static_thrust_kn', None)
        return
    if mode == 'unselected':
        p['_engine_fuel'] = dict(status='missing', supported=False, model=None, notes=[
            'Nie wskazano rzeczywistego silnika i źródła zużycia paliwa. Wyniki paliwowe są założeniem roboczym, '
            'nie udokumentowanym projektem. Wybierz propozycję silnika lub podaj dane producenta.'])
        # A cached jet rating belonging to a removed proposal must not remain active.
        p.pop('engine_static_thrust_kn', None)
        return
    count = int(p['n_engines'])
    if mode == 'catalog':
        record = next((r for r in _catalog() if r['id'] == p.get('engine_model_id')), None)
        if record is None:
            raise ValueError('Wybierz rzeczywistą propozycję silnika z katalogu.')
        if record['engine_type'] != engine:
            raise ValueError('Wybrany silnik nie odpowiada rodzajowi napędu projektu.')
        point_id = p.get('engine_fuel_point') or record['points'][0]['id']
        point = next((x for x in record['points'] if x['id'] == point_id), None)
        if point is None:
            raise ValueError('Wybrany punkt zużycia paliwa nie należy do tego silnika.')
        evidence = dict(status='catalog', supported=True, model=record['model'], source=record['source_title'],
                        locator=record['source_locator'], source_url=record['source_url'],
                        rating_kw=record.get('rating_kw'), rating_kn=record.get('rating_kn'),
                        rating_note=record['rating_note'], rating_basis=record.get('rating_basis', 'continuous'), point=deepcopy(point),
                        checked_on=record['checked_on'])
    else:
        evidence = dict(status='author_source', supported=True,
                        model=_text(p, 'engine_custom_model', 'model i wariant silnika'),
                        source=_text(p, 'engine_fuel_source', 'dokument producenta i stronę', 5),
                        locator='', source_url='', rating_basis='continuous', rating_note='Dane i odniesienie do dokumentu podane przez autora.')
        if 'sfc' not in p:
            raise ValueError('Dane silnika: podaj SFC z dokumentacji producenta.')
        conditions = _text(p, 'engine_fuel_conditions', 'warunki punktu pracy (moc/ciąg, obroty, H/M)', 5)
        unit = '1/h' if engine == 'jet' else 'g/(kW h)'
        evidence['point'] = dict(id='custom', value=float(p['sfc']), unit=unit, conditions=conditions)
        key = 'engine_custom_thrust_kn' if engine == 'jet' else 'engine_custom_power_kw'
        rating = float(p.get(key, 0))
        if not math.isfinite(rating) or rating <= 0:
            raise ValueError('Dane silnika: podaj dodatnią moc ciągłą na silnik [kW] lub ciąg na silnik [kN].')
        evidence['rating_kn' if engine == 'jet' else 'rating_kw'] = rating
    density = float(p.get('fuel_density_kg_l', .72))
    sfc = normalized_sfc(evidence['point'], density, engine)
    evidence.update(sfc=sfc, unit='1/h' if engine == 'jet' else 'g/(kW h)', density_kg_l=density,
                    count=count, notes=[
                        'W równaniach przelotu, oczekiwania i osiągów przyjęto stałe SFC z wybranego punktu pracy rzeczywistego silnika. '
                        'Przeniesienie na inne moce, obroty, wysokości i prędkości jest przybliżeniem; '
                        'nie zastępuje pełnej mapy silnika. Fazy opisane w przewodniku ułamkiem masy '
                        '(np. start i lądowanie) pozostają oszacowaniem statystycznym, nie pomiarem spalania tego silnika.'])
    if evidence['point']['unit'] in ('l/h', 'US gal/h'):
        evidence['notes'].append('Gęstość paliwa jest jawnym założeniem przeliczenia objętości na masę, nie odczytem zużycia producenta.')
    if evidence.get('rating_basis') in ('maximum', 'measured'):
        evidence['notes'].append('Podana moc katalogowa nie jest potwierdzoną mocą ciągłą. '
                                 'Jej użycie w obliczeniu osiągów jest górnym oszacowaniem; '
                                 'trwała dostępność mocy wymaga instrukcji wybranego wariantu silnika.')
    p['sfc'] = sfc
    if engine == 'prop':
        p.update(power_input_mode='fixed', engine_power_kw=evidence['rating_kw'] * count)
        p.pop('engine_static_thrust_kn', None)
    else:
        p['power_input_mode'] = 'sized'
        if isinstance(p.get('locked_params'), list):
            p['locked_params'] = [key for key in p['locked_params'] if key != 'engine_power_kw']
        p['engine_static_thrust_kn'] = evidence['rating_kn'] * count
    if mode == 'custom' and float(p.get('max_power_time_min', 0)) > 0:
        max_source = _text(p, 'engine_max_fuel_source', 'źródło SFC maksymalnego ustawienia', 5) if p.get('engine_max_fuel_source') else ''
        max_conditions = _text(p, 'engine_max_fuel_conditions', 'warunki maksymalnego ustawienia', 5) if p.get('engine_max_fuel_conditions') else ''
        evidence['maximum_supported'] = bool(max_source and max_conditions)
        if evidence['maximum_supported']:
            evidence['maximum_source'] = max_source
            evidence['maximum_point'] = dict(value=p.get('max_power_sfc'), unit=evidence['unit'],
                conditions=max_conditions)
            evidence['maximum_sfc'] = p.get('max_power_sfc')
        else:
            evidence['notes'].append('Zadanie przy maksymalnym ustawieniu wymaga osobnego źródła i warunków SFC; '
                                     'punkt przelotowy tego nie dokumentuje.')
    if engine == 'jet' and float(p.get('max_power_time_min', 0)) > 0:
        if float(p.get('max_thrust_kn', 0)) > evidence['rating_kn'] * count + 1e-8:
            raise ValueError('Ciąg zadania przekracza ciąg wybranych rzeczywistych silników.')
    if mode == 'catalog' and float(p.get('max_power_time_min', 0)) > 0:
        requested = float(p.get('max_power_kw') or count * record.get('takeoff_kw', record.get('rating_kw', 0)))
        if engine == 'prop' and requested > count * record['takeoff_kw'] + 1e-8:
            raise ValueError('Moc zadania przekracza moc startową wybranego zespołu napędowego.')
        maximum = next((x for x in record['points'] if x['id'] == 'takeoff'), None)
        if engine == 'prop' and requested <= count * record['rating_kw']:
            maximum = next((x for x in record['points'] if x['id'] == 'continuous'), maximum)
        if maximum is None:
            evidence['notes'].append('Brak danych producenta dla zadania na maksymalnym ustawieniu; wymagane osobne źródło.')
            evidence['maximum_supported'] = False
        else:
            p['max_power_sfc'] = normalized_sfc(maximum, density, engine)
            evidence['maximum_sfc'] = p['max_power_sfc']
            evidence['maximum_point'] = deepcopy(maximum)
            evidence['maximum_supported'] = True
            if engine == 'prop':
                limit = record.get('takeoff_limit_min')
                if maximum['id'] == 'takeoff' and limit and float(p['max_power_time_min']) > limit:
                    raise ValueError(f"Moc startowa silnika {record['model']} może być użyta przez najwyżej {limit:g} minut.")
                p['max_power_kw'] = requested
    p['_engine_fuel'] = evidence


def engine_assessment(params, sizing):
    info = deepcopy(params.get('_engine_fuel') or dict(status='missing', supported=False, notes=[]))
    engine = params['engine_type']
    if engine == 'none':
        return dict(info, candidates=[])
    count = int(params['n_engines'])
    dp = sizing['design_point']
    required = (dp.get('required_thrust_kn') or dp['thrust_kn']) if engine == 'jet' else dp['required_power_kw']
    info['required_total'] = required
    info['rating_unit'] = 'kN' if engine == 'jet' else 'kW'
    info['candidates'] = []
    for row in catalog():
        if row['engine_type'] != engine or params['aircraft_type'] not in row['classes']:
            continue
        rating = row['rating_kn' if engine == 'jet' else 'rating_kw']
        info['candidates'].append(dict(row, total_rating=rating * count,
                                       adequate=rating * count >= required - 1e-6))
    info['candidates'].sort(key=lambda x: (not x['adequate'], abs(x['total_rating'] - required)))
    if info.get('supported'):
        rating = info['rating_kn' if engine == 'jet' else 'rating_kw'] * count
        info.update(installed_total=rating, adequate=rating >= required - 1e-6,
                    reference_load_pct=(100 * info['point']['power_kw'] / info['rating_kw'])
                    if info['point'].get('power_kw') else None)
    return info


def fuel_check(info):
    return dict(parameter='Źródło zużycia paliwa i rzeczywisty silnik',
                required='Model, dokument producenta i warunki punktu pracy',
                actual=(f"{info['model']}: {info['sfc']:.3f} {info['unit']}" if info.get('supported') else 'Brak danych źródłowych'),
                passed=bool(info.get('supported')) and info.get('maximum_supported', True),
                note='; '.join(info.get('notes', [])))
