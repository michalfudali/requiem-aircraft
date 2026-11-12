"""Ground-clearance dimensions from CS-22.925(a) and legacy CS-23.925(a).

CS-22 Amendment 3, p.80: 180 mm nose wheel, 230 mm tail wheel, with statically
deflected gear. Meeting this one dimension does not verify all required attitudes
or the tyre/strut failure cases.
"""
import math

CS22_SOURCE = 'https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf'
REFERENCE = 'CS-22.925(a); CS-23.925(a), wydanie klasyczne'


def landing_gear_layout(params):
    # gear_type in the main project means fixed/retractable, but older standalone
    # clearance requests used it for tricycle/taildragger.
    layout = params.get('landing_gear_type')
    if not layout:
        legacy = params.get('gear_type')
        layout = legacy if legacy in ('tricycle', 'tailwheel', 'taildragger') else 'tricycle'
    if layout == 'taildragger':
        return 'tailwheel'
    if layout not in ('tricycle', 'tailwheel'):
        raise ValueError('Nieznany układ podwozia do oceny prześwitu śmigła.')
    return layout


def minimum_ground_clearance_m(params):
    return .230 if landing_gear_layout(params) == 'tailwheel' else .180


def meets_minimum(actual, required):
    # Ignore machine round-off only, never round a deficient dimension to a pass.
    return actual >= required or math.isclose(actual, required, abs_tol=1e-12, rel_tol=0.)


def nominal_ground_assessment(params, shaft_height, diameter):
    """Screen the final project's one nose-mounted propeller in level attitude."""
    applicable = params.get('engine_type') == 'prop'
    info = dict(applicable=applicable, shaft_height_m=None, diameter_m=diameter if applicable else None,
                clearance_m=None, required_m=minimum_ground_clearance_m(params) if applicable else None,
                nominal_passed=None, certification_compliant=None, reference=REFERENCE, source_url=CS22_SOURCE,
                scope='level_attitude_statically_deflected_gear')
    if not applicable:
        info['note'] = 'Brak śmigła — ocena nie dotyczy.'
    elif params.get('operating_surface') == 'water':
        info.update(required_m=None, scope='waterline_not_defined')
        info['note'] = 'Do oceny prześwitu nad wodą wymagane są statyczna linia wodna i wymiary zabudowy.'
    elif params.get('engine_location', 'nose') != 'nose' or int(params.get('n_engines', 1)) != 1:
        info['note'] = 'Wymagane wysokości osi i położenia wszystkich śmigieł dla przyjętej zabudowy.'
    else:
        try:
            shaft_height, diameter = float(shaft_height), float(diameter)
        except (TypeError, ValueError) as exc:
            raise ValueError('Wysokość osi i średnica śmigła muszą być dodatnie i skończone.') from exc
        if not all(math.isfinite(v) and v > 0 for v in (shaft_height, diameter)):
            raise ValueError('Wysokość osi i średnica śmigła muszą być dodatnie i skończone.')
        clearance = shaft_height-diameter/2
        info.update(shaft_height_m=shaft_height, diameter_m=diameter, clearance_m=clearance,
                    nominal_passed=meets_minimum(clearance, info['required_m']))
        info['note'] = ('Obliczenie w położeniu poziomym, przy przyjętej wysokości osi na podwoziu ugiętym statycznie. '
                        'Do pełnej oceny: najbardziej niekorzystna masa i ŚC, kąt łopat, położenia podczas startu '
                        'i kołowania oraz przypadki uszkodzenia opony i dobicia goleni.')
    return info
