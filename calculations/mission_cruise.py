"""Fuel integration at constant TAS and altitude with a parabolic drag polar.

L = mg; D = q S CD0 + k (mg)^2 / (q S) = a + b m^2.
Propeller: dm/dx = -BSFC D/eta; jet: dm/dx = -TSFC D/(g V).
BSFC is converted from g/kWh to kg/(W s); input jet TSFC is weight/force/h.
The arctangent integral retains changing weight; no assumed L/D is substituted.
"""
import math

from calculations.atmosphere import G0, isa_atmosphere


def coefficients(params, polar):
    speed = params['cruise_speed_kmh'] / 3.6
    q_area = .5 * isa_atmosphere(params['cruise_altitude_m'])['rho'] * speed**2 * polar['S']
    a, b = q_area * polar['cx0'], polar['k'] * G0**2 / q_area
    consumption = (params['sfc'] / (3600 * G0 * speed) if params['engine_type'] == 'jet'
                   else params['sfc'] / (3.6e9 * params['prop_efficiency']))
    return a, b, consumption


def mass_after_cruise(mass, distance_m, params, polar):
    """Return None if the requested leg would exhaust even the total aircraft mass."""
    a, b, consumption = coefficients(params, polar)
    angle = math.atan(mass * math.sqrt(b/a)) - distance_m * consumption * math.sqrt(a*b)
    return math.sqrt(a/b) * math.tan(angle) if angle > 0 else None


def cruise_distance(start_mass, end_mass, params, polar):
    if not 0 < end_mass <= start_mass:
        return None
    a, b, consumption = coefficients(params, polar)
    return (math.atan(start_mass * math.sqrt(b/a)) - math.atan(end_mass * math.sqrt(b/a))) / (consumption * math.sqrt(a*b))


def assess_mission_range(params, mass, geometry, aero, sizing):
    """Check each allocated cruise leg separately; reserves and task fuel are retained."""
    from calculations.flight_model import flight_point
    if params['engine_type'] == 'none':
        return dict(legs=[], total_available_km=None, passed=False)
    polar = dict(S=geometry['wing']['S'], cx0=aero['cx0_clean'], k=aero['k_clean'])
    back = params.get('return_range_km', 0)
    requirements = dict(cruise=params['range_km']-back, return_leg=back)
    legs = []
    for phase in mass['mission_phases']:
        if phase['key'] not in ('cruise', 'return'):
            continue
        required = requirements['cruise' if phase['key']=='cruise' else 'return_leg']
        point = flight_point(params, sizing, phase['mass_start_kg'], polar['S'], polar['cx0'], polar['k'],
                             params['cruise_altitude_m'], params['cruise_speed_kmh']/3.6)
        reachable = point['cl'] <= aero['cz_max_clean'] and point['climb_ms'] >= -1e-7
        distance = cruise_distance(phase['mass_start_kg'], phase['mass_end_kg'], params, polar) if reachable else None
        available = distance/1000 if distance is not None else None
        legs.append(dict(key=phase['key'], label=phase['phase'], required_km=required,
                         available_km=round(available, 1) if available is not None else None,
                         passed=available is not None and available >= required-1e-6))
    complete = bool(legs) and all(leg['available_km'] is not None for leg in legs)
    return dict(legs=legs, total_available_km=round(sum(leg['available_km'] for leg in legs), 1) if complete else None,
                passed=bool(legs) and all(leg['passed'] for leg in legs))
