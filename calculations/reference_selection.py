"""One real, best-performing variant per aircraft family in the comparison sample."""
from collections import defaultdict
import math
import re
import unicodedata


def _identity(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return re.sub(r'[^a-z0-9]', '', text)


def family_groups(rows):
    """Join catalogue family labels and identical models across sources.

    Resolve identities on the whole class before filtering, so a date/source
    filter cannot disconnect two aliases linked by a duplicate model.
    Missing family labels fall back to the full model, never its manufacturer.
    """
    parent, names, identities = {}, {}, {}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for row in rows:
        family = row.get('family') or row['model']
        key = _identity(family) or row['id']
        parent.setdefault(key, key)
        names.setdefault(key, set()).add(family)
        model = _identity(row['model'])
        if model in identities:
            a, b = root(key), root(identities[model])
            parent[max(a, b)] = min(a, b)
        identities[model] = key
    labels = defaultdict(list)
    for key, aliases in names.items():
        labels[root(key)].extend(aliases)
    result = {}
    for row in rows:
        key = root(_identity(row.get('family') or row['model']) or row['id'])
        result[row['id']] = key, min(labels[key], key=lambda label: (len(label), label))
    return result


def selection_criteria(aircraft_type):
    if aircraft_type in ('glider', 'motoglider'):
        return (('ld_max', 1), ('w_z_min_ms', -1), ('v_cruise_kmh', 1),
                ('range_km', 1), ('climb_rate_ms', 1))
    speeds = (('cruise_mach', 1), ('v_cruise_kmh', 1)) if aircraft_type in ('jet_business', 'jet_transport') else (('v_cruise_kmh', 1),)
    return (*speeds, ('range_km', 1), ('climb_rate_ms', 1))


def selection_description(aircraft_type):
    if aircraft_type in ('glider', 'motoglider'):
        criteria = 'większa doskonałość, mniejsze opadanie, większa prędkość przelotowa, zasięg i wznoszenie'
    else:
        speed = ('liczba Macha przelotu, prędkość przelotowa w km/h'
                 if aircraft_type in ('jet_business', 'jet_transport') else 'prędkość przelotowa')
        criteria = f'większa {speed}, następnie zasięg i wznoszenie'
    return (f'Jedna odmiana z każdej rodziny; kolejno: {criteria}. '
            'Porównuje się wyłącznie udokumentowane wartości. Przy remisie decydują '
            'kompletność danych, nowszy rok i identyfikator rekordu.')


def best_variants(rows, groups, aircraft_type):
    """Select one whole source record; do not assemble an imaginary best-of model."""
    families = defaultdict(list)
    for row in rows:
        families[groups[row['id']][0]].append(row)
    criteria = selection_criteria(aircraft_type)

    def documented(row, key, direction):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
            return value * direction
        return -math.inf

    def rank(row):
        performance = tuple(documented(row, key, direction) for key, direction in criteria)
        fields = ('me', 's', 'b', 'year', 'v_cruise_kmh', 'cruise_mach', 'range_km',
                  'climb_rate_ms', 'ld_max', 'w_z_min_ms', 'takeoff_distance_m', 'landing_distance_m')
        complete = sum(math.isfinite(documented(row, key, 1)) for key in fields)
        return (*performance, complete, documented(row, 'year', 1))

    result = []
    for key, variants in sorted(families.items()):
        # Sorted IDs give reproducible ties, independently of catalogue/source order.
        chosen = max(sorted(variants, key=lambda row: row['id']), key=rank)
        result.append({**chosen, 'catalog_family': chosen.get('family'), 'family': groups[chosen['id']][1],
                       'family_key': key, 'variant_selection': {
                           'policy': 'best_in_family', 'candidates_n': len(variants),
                           'criteria': [field for field, _ in criteria],
                           'values': {field: chosen.get(field) for field, _ in criteria},
                           'omitted_ids': sorted(row['id'] for row in variants if row['id'] != chosen['id'])}})
    return result
