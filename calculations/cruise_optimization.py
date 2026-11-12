"""Continuous range/endurance optima at constant TAS and altitude.

The parabolic polar, constant SFC and propeller efficiency give unimodal
objectives. Search the feasible interval at cruise-entry mass, including its
endpoints; integrate only the fuel allocated to the first cruise leg.
"""
import math

from calculations.flight_model import flight_point, level_flight_envelope
from calculations.mission_cruise import cruise_distance


def _maximum(evaluate, key, low, high):
    ratio = (math.sqrt(5) - 1) / 2
    a, b = low, high
    c, d = b - ratio*(b-a), a + ratio*(b-a)
    fc, fd = evaluate(c), evaluate(d)
    for _ in range(64):
        if fc[key] < fd[key]:
            a, c, fc = c, d, fd
            d = a + ratio*(b-a)
            fd = evaluate(d)
        else:
            b, d, fd = d, c, fc
            c = b - ratio*(b-a)
            fc = evaluate(c)
    return max((evaluate(low), evaluate(high), fc, fd), key=lambda p: p[key])


def optimize_cruise(params, sizing, start_mass, end_mass, area, cd0, k, cl_max, altitude):
    result = dict(available=False, status='unreachable', altitude_m=altitude,
                  start_mass_kg=start_mass, end_mass_kg=end_mass,
                  fuel_kg=start_mass-end_mass, min_speed_kmh=None, max_speed_kmh=None,
                  max_range=None, max_endurance=None,
                  method='Stałe TAS i wysokość; całka zmiennej masy; optymalizacja ciągła.',
                  basis='Paliwo pierwszego odcinka przelotu, bez paliwa powrotu i rezerwy. '
                        'Granice lotu poziomego z modelu napędu i biegunowej, bez ograniczeń VMO/VNE. '
                        'Stałe SFC i sprawność śmigła, biegunowa paraboliczna bez oporu falowego.')
    if params['engine_type'] == 'none':
        result['status'] = 'unpowered'
        return result
    if not 0 < end_mass <= start_mass:
        result['status'] = 'invalid_masses'
        return result
    if end_mass == start_mass:
        result['status'] = 'no_cruise_fuel'
        return result
    envelope = level_flight_envelope(params, sizing, start_mass, area, cd0, k, cl_max, altitude)
    if not envelope['available']:
        return result
    polar = dict(S=area, cx0=cd0, k=k)
    p = dict(params, cruise_altitude_m=altitude)

    def evaluate(speed):
        p['cruise_speed_kmh'] = 3.6 * speed
        distance = cruise_distance(start_mass, end_mass, p, polar)
        start = flight_point(params, sizing, start_mass, area, cd0, k, altitude, speed)
        return dict(speed_kmh=3.6*speed, range_km=distance/1000,
                    endurance_h=distance/(speed*3600), cl_start=start['cl'],
                    cl_end=start['cl']*end_mass/start_mass,
                    excess_power_start_w=start['available_w']-start['required_w'])

    low, high = envelope['min_ms'], envelope['max_ms']
    result.update(available=True, status='available', min_speed_kmh=low*3.6, max_speed_kmh=high*3.6,
                  max_range=_maximum(evaluate, 'range_km', low, high),
                  max_endurance=_maximum(evaluate, 'endurance_h', low, high))
    return result
