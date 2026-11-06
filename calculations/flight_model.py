"""Shared conventions for preliminary propulsion and mission bookkeeping."""
import math
from calculations.atmosphere import isa_atmosphere, G0


def climb_time_to_height(height, climb_rate, max_step=250):
    """Integrate dt = dh / ROC at constant mass, without a linear-ROC fiction.

    A nonpositive rate makes the height unreachable. The absolute ceiling is
    asymptotic and must be handled as unreachable by the caller.
    """
    if height <= 0:
        return 0.0
    steps = max(2, 2 * math.ceil(height / (2 * max_step)))
    dh = height / steps
    rates = [climb_rate(i * dh) for i in range(steps + 1)]
    if min(rates) <= 0:
        return None
    return dh/3 * (1/rates[0] + 1/rates[-1] +
        sum((4 if i % 2 else 2)/rates[i] for i in range(1, steps)))


def propulsion_lapse(params, altitude_m, speed_ms=0.0):
    """Available / sea-level installed thrust or shaft power (not prop efficiency).

    Jet: Paturski's turbofan approximation. Turboprop: density power law.
    Piston: normally aspirated approximation, or flat rated to 4500 m when
    explicitly turbocharged. These are estimates, not an engine deck.
    """
    atmosphere = isa_atmosphere(altitude_m)
    sigma = atmosphere['sigma']
    kind = params.get('engine_type', 'prop')
    if kind == 'none':
        return 0.0
    if kind == 'jet':
        kp = .45 if params.get('aircraft_type') == 'jet_business' else .55
        return sigma ** .85 * max(.35, 1 - kp * speed_ms / atmosphere['a'])
    if params.get('aircraft_type') == 'turboprop_regional':
        return sigma ** .85
    if params.get('turbocharged', False):
        rated = isa_atmosphere(4500)['sigma']
        return min(1.0, (sigma / rated) ** .9)
    return max(0.0, sigma - (1 - sigma) / 7.55)


def mission_masses(mass):
    """Masses from the actual fuel fractions, retaining reserve/unusable fuel."""
    if mass.get('mission_phases'):
        phases = {}
        for phase in mass['mission_phases']:
            phases[phase['key']+'_start'] = phase['mass_start_kg']
            phases[phase['key']+'_end'] = phase['mass_end_kg']
        phases['cruise_mean'] = (phases['cruise_start']+phases['cruise_end'])/2
        phases['fuel_after_landing'] = mass['reserve_fuel_kg']
        return phases
    fractions = mass['fuel_fractions_detail']
    current = mass['m0']
    phases = {}
    for key in ('warmup', 'takeoff', 'climb', 'cruise', 'descent', 'loiter', 'landing'):
        phases[key + '_start'] = current
        current *= fractions[key]
        phases[key + '_end'] = current
    phases['cruise_mean'] = (phases['cruise_start'] + phases['cruise_end']) / 2
    phases['fuel_after_landing'] = max(0.0, current - (mass['m0'] - mass['m_fuel']))
    return phases


def propeller_efficiency(params, speed_ms):
    """eta(V) of the P4 speed characteristic: variable-pitch propeller, Paturski, tab. 5.1.

    Maximum at the propeller design speed, 1,15 V_cr (not below 35 m/s); the same curve fills
    the P4 table, so P5 balances power with the efficiency that table shows at each speed.
    """
    design = max(35.0, float(params.get('cruise_speed_kmh', 220.0)) * 1.15 / 3.6)
    return float(params.get('prop_efficiency', .82)) * max(.45, 1 - .18 * (speed_ms / design - 1) ** 2)


def flight_point(params, sizing, mass, area, cd0, k, altitude, speed):
    """Force/power balance at one TAS, at the stated mass and altitude."""
    atmosphere = isa_atmosphere(altitude)
    weight = mass * G0
    q = .5 * atmosphere['rho'] * speed ** 2
    cl = weight / (q * area)
    drag = q * area * (cd0 + k * cl ** 2)
    dp = sizing['design_point']
    lapse = propulsion_lapse(params, altitude, speed)
    if params.get('engine_type') == 'jet':
        available = (dp.get('thrust_kn') or 0) * 1000 * lapse * speed
    else:
        available = (dp.get('power_kw') or 0) * 1000 * lapse * propeller_efficiency(params, speed)
    return {'cl': cl, 'drag_n': drag, 'required_w': drag * speed,
            'available_w': available, 'climb_ms': (available - drag * speed) / weight}


def level_flight_envelope(params, sizing, mass, area, cd0, k, cl_max, altitude):
    """Find maximum climb and both level-flight roots above stall; no fake roots."""
    rho = isa_atmosphere(altitude)['rho']
    stall = math.sqrt(2 * mass * G0 / (rho * area * cl_max))
    def climb(v):
        return flight_point(params, sizing, mass, area, cd0, k, altitude, v)['climb_ms']
    upper = max(stall * 8, params.get('cruise_speed_kmh', 250) / 3.6 * 2)
    left, right = stall, upper
    for _ in range(50):
        a, b = left + (right-left)/3, right - (right-left)/3
        if climb(a) < climb(b):
            left = a
        else:
            right = b
    best_v = (left + right) / 2
    best_w = climb(best_v)
    if climb(stall) > best_w:
        best_v, best_w = stall, climb(stall)
    if best_w < 0:
        return {'stall_ms': stall, 'best_speed_ms': best_v, 'climb_ms': best_w,
                'available': False, 'min_ms': None, 'max_ms': None}
    def root(lo, hi, rising):
        for _ in range(45):
            mid = (lo + hi) / 2
            if (climb(mid) < 0) == rising:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    minimum = stall if climb(stall) >= 0 else root(stall, best_v, True)
    while climb(upper) > 0:
        upper *= 2
    return {'stall_ms': stall, 'best_speed_ms': best_v, 'climb_ms': best_w,
            'available': True, 'min_ms': minimum, 'max_ms': root(best_v, upper, False)}
