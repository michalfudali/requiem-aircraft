"""Prescribed climb: constant vertical speed and TAS linear in altitude.

Point-mass force balance with thrust tangent to the flight path:
T = D + m g sin(gamma) + m dV/dt; L = m(g cos(gamma) + V dgamma/dt).
Fuel uses the selected engine's constant SFC, as in the cruise model. This is
an engineering estimate, not an engine deck or a validated flight schedule.
"""
import math
from functools import lru_cache

from calculations.atmosphere import G0, isa_atmosphere
from calculations.flight_model import propeller_efficiency, propulsion_lapse

SOURCE = 'Bilans sił i energii wznoszenia; NASA Glenn, Forces in a Climb'
SOURCE_URL = 'https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/forces-in-a-climb/'


@lru_cache(maxsize=64)
def _grid(h0, h1, v0, v1, roc, eta_max, jet, max_step):
    steps = math.ceil((h1-h0)/max_step) if h1 > h0 else 0
    dh = (h1-h0)/steps if steps else 0.
    slope = (v1-v0)/(h1-h0) if h1 > h0 else 0.
    points = []
    for i in range(2*steps+1):
        h = h0+i*dh/2
        v = v0+slope*(h-h0)
        cosine = math.sqrt(1-(roc/v)**2)
        acceleration = slope*roc
        lift_per_mass = G0*cosine-roc*acceleration/(v*cosine)
        efficiency = 1. if jet else propeller_efficiency(dict(cruise_speed_kmh=v1*3.6, prop_efficiency=eta_max), v)
        points.append((h, v, lift_per_mass, .5*isa_atmosphere(h)['rho']*v*v,
                       G0*roc/v+acceleration, efficiency))
    return steps, dh, slope, tuple(points)


def climb_segment(start_mass, params, polar=None, ld=None, max_step_m=100., *, detailed=True):
    """Integrate mass, work and thrust impulse with RK4 in altitude [SI].

    P4 supplies the parabolic polar after design closure. Preliminary iterations
    use an explicitly identified constant L/D, never a zero-fuel chart clamp.
    Installed propulsion is assessed afterwards, at the actual final sizing.
    """
    h0 = float(params.get('climb_start_altitude_m', 0))
    h1 = float(params.get('cruise_altitude_m', 3000))
    v1 = float(params['cruise_speed_kmh'])/3.6
    v0 = float(params.get('climb_start_speed_kmh') or params['cruise_speed_kmh'])/3.6
    roc = float(params.get('mission_climb_rate_ms', 3.))
    sfc = float(params['sfc'])
    if not all(math.isfinite(v) for v in (h0, h1, v0, v1, roc, start_mass, sfc, max_step_m)):
        raise ValueError('Wznoszenie wymaga skończonych danych wejściowych.')
    if h1 < h0 or min(start_mass, sfc, max_step_m) <= 0:
        raise ValueError('Wznoszenie: wysokość końcowa nie może być mniejsza od początkowej; masa i SFC muszą być dodatnie.')
    if roc <= 0 or min(v0, v1) <= roc:
        raise ValueError('Prędkość wznoszenia musi być dodatnia i mniejsza od TAS w całym profilu.')
    if h1 == h0 and v0 != v1:
        raise ValueError('Rozpędzanie bez przyrostu wysokości wymaga osobnego czasu i profilu fazy.')
    if polar is None and (ld is None or not math.isfinite(ld) or ld <= 0):
        raise ValueError('Brak biegunowej lub dodatniej doskonałości do bilansu wznoszenia.')
    if polar and (not all(math.isfinite(polar[k]) and polar[k] > 0 for k in ('S', 'cx0', 'k'))):
        raise ValueError('Biegunowa wznoszenia wymaga dodatnich S, C_D0 i k.')
    jet = params.get('engine_type') == 'jet'
    steps, dh, slope, grid = _grid(h0, h1, v0, v1, roc, float(params.get('prop_efficiency', .82)), jet, max_step_m)
    coefficients = []
    for h, v, lift_per_mass, q, acceleration_force, efficiency in grid:
        if lift_per_mass <= 0:
            raise ValueError('Zadany profil rozpędzania wymaga niedodatniej siły nośnej; zmień TAS lub tempo wznoszenia.')
        if not 0 < efficiency <= 1:
            raise ValueError('Sprawność śmigła wznoszenia musi należeć do (0, 1].')
        qs = q*polar['S'] if polar else None
        a, b, c = ((qs*polar['cx0'], polar['k']*lift_per_mass**2/qs, 0.) if polar else
                   (0., 0., lift_per_mass/ld))
        consumption = sfc/(3600*G0*roc) if jet else sfc/3.6e9*v/(efficiency*roc)
        coefficients.append((a, b, c, consumption))

    def point(index, mass):
        h, v, lift_per_mass, q, acceleration_force, efficiency = grid[index]
        a, b, c, consumption = coefficients[index]
        lift = mass*lift_per_mass
        drag = a+b*mass*mass+c*mass
        thrust = drag+mass*acceleration_force
        if thrust <= 0:
            raise ValueError('Profil wznoszenia wymaga niedodatniego ciągu; brak danych pracy silnika dla takiego hamowania.')
        power = thrust*v/efficiency
        burn_rate = sfc/(3600*G0)*thrust if jet else sfc/3.6e9*power
        return dict(altitude_m=h, mass_kg=mass, tas_ms=v, lift_n=lift, drag_n=drag,
                    cl=lift/(q*polar['S']) if polar else None, thrust_n=thrust, shaft_power_w=None if jet else power,
                    useful_power_w=thrust*v, efficiency=efficiency, burn_rate_kg_s=burn_rate)

    def derivative(index, state):
        if not detailed:
            a, b, c, consumption = coefficients[index]
            thrust = a+b*state[0]*state[0]+(c+grid[index][4])*state[0]
            if thrust <= 0:
                raise ValueError('Profil wznoszenia wymaga niedodatniego ciągu; brak danych pracy silnika dla takiego hamowania.')
            return [-consumption*thrust]
        p = point(index, state[0])
        return [-p['burn_rate_kg_s']/roc, p['drag_n']*p['tas_ms']/roc,
                state[0]*G0, state[0]*p['tas_ms']*slope,
                (p['shaft_power_w'] or 0)/roc, p['thrust_n']/roc]

    state = [float(start_mass)] + ([0., 0., 0., 0., 0.] if detailed else [])
    nodes = [point(0, state[0])] if detailed else []
    for i in range(steps):
        k1 = derivative(2*i, state)
        k2 = derivative(2*i+1, [v+dh*k/2 for v, k in zip(state, k1)])
        k3 = derivative(2*i+1, [v+dh*k/2 for v, k in zip(state, k2)])
        k4 = derivative(2*i+2, [v+dh*k for v, k in zip(state, k3)])
        state = [v+dh*(a+2*b+2*c+d)/6 for v, a, b, c, d in zip(state, k1, k2, k3, k4)]
        if not 0 < state[0] <= start_mass:
            raise ValueError('Zadany profil wznoszenia zużywa całą masę samolotu.')
        if detailed:
            nodes.append(point(2*i+2, state[0]))
    end_mass = state[0]
    if not detailed:
        return dict(end_mass_kg=end_mass, fuel_kg=start_mass-end_mass, fraction=end_mass/start_mass)
    return dict(model='energy', drag_model='p4_polar' if polar else 'preliminary_ld',
                polar=dict(polar) if polar else None, preliminary_ld=ld if not polar else None,
                start_mass_kg=start_mass, end_mass_kg=state[0], fuel_kg=start_mass-state[0],
                fraction=state[0]/start_mass, altitude_start_m=h0, altitude_end_m=h1,
                tas_start_ms=v0, tas_end_ms=v1, roc_ms=roc, duration_s=(h1-h0)/roc,
                integrator='RK4', step_m=dh,
                drag_work_j=state[1], potential_work_j=state[2], kinetic_work_j=state[3],
                shaft_work_j=None if jet else state[4], thrust_impulse_ns=state[5],
                source=SOURCE, source_url=SOURCE_URL, nodes=nodes,
                note='Stałe tempo wznoszenia i TAS liniowa z wysokością. '+
                     ('SFC z wybranego punktu rzeczywistego silnika. ' if params.get('_engine_fuel', {}).get('supported')
                      else 'Robocze SFC bez udokumentowanego punktu rzeczywistego silnika. ')+
                     'Przeniesienie stałego SFC na inne moce i wysokości jest przybliżeniem, wymagającym mapy silnika.')


def assess_climb(segment, params, sizing, cl_max):
    """Check the commanded profile against the same lapse/eta model as P4/P5."""
    if segment['duration_s'] == 0:
        return dict(passed=True, minimum_rating_margin=None, peak_cl=None, cl_max=cl_max, nodes=0,
                    scope='Faza wznoszenia nie występuje: nie zadano zmiany wysokości ani TAS.')
    jet = params['engine_type'] == 'jet'
    rating = sizing['design_point']['thrust_kn' if jet else 'power_kw']*1000
    margins = []
    for point in segment['nodes']:
        available = rating*propulsion_lapse(params, point['altitude_m'], point['tas_ms'])
        required = point['thrust_n'] if jet else point['shaft_power_w']
        margins.append(available-required)
    cls = [p['cl'] for p in segment['nodes'] if p['cl'] is not None]
    peak_cl = max(cls) if cls else None
    margin = min(margins)
    return dict(passed=margin >= -1e-6 and peak_cl is not None and peak_cl <= cl_max,
                minimum_rating_margin=margin, margin_unit='N' if jet else 'W',
                peak_cl=peak_cl, cl_max=cl_max, nodes=len(margins),
                scope='Dyskretny profil punktowy z modelem spadku mocy/ciągu P4/P5; wymaga potwierdzenia mapą silnika.')
