"""Physical planform invariants and invalid data are independent of the SDK."""
import math

import pytest

from calculations.geometry import calculate_geometry
from calculations.presets import AIRCRAFT_PRESETS
from calculations.vsp_wing import projected_wing_stations


def geometry(planform='trapezoidal', **extra):
    p = dict(AIRCRAFT_PRESETS['ga_trainer'], wing_planform=planform, wingspan_m=13.73,
             wing_area_m2=23.13, break_span_ratio=.371, dihedral_deg=12., **extra)
    return calculate_geometry(850, 400, p)['wing'], p


@pytest.mark.parametrize('planform', ['trapezoidal', 'rectangular', 'compound_trapezoid', 'elliptical', 'swept_trapezoidal'])
def test_projected_dimensions_area_and_mac_close_independently(planform):
    wing, params = geometry(planform)
    stations, info = projected_wing_stations(wing, params)
    area = sum((r[0]-l[0])*(l[1]+r[1]) for l, r in zip(stations, stations[1:]))
    moment = 2*sum((r[0]-l[0])*(l[1]**2+l[1]*r[1]+r[1]**2)/3 for l, r in zip(stations, stations[1:]))
    assert area == pytest.approx(wing['S'], abs=1e-10)
    assert moment/area == pytest.approx(wing['mac'], rel=.001 if planform == 'elliptical' else 1e-12)
    assert stations[0] == [0., wing['cr']] and stations[-1] == [wing['b']/2, wing['ct']]
    assert info['unprojected_span_m']*math.cos(math.radians(12)) == pytest.approx(wing['b'])
    assert info['unprojected_area_m2']*math.cos(math.radians(12)) == pytest.approx(wing['S'])
    if planform == 'elliptical':
        assert 1 < info['ellipse_interior_chord_factor'] < 1.00042
        assert all(l[1] > r[1] for l, r in zip(stations, stations[1:]))
    elif planform == 'compound_trapezoid':
        assert stations[1][0] == .371*wing['b']/2  # no centimetre rounding


@pytest.mark.parametrize('key,value', [('b',0), ('S',float('inf')), ('cr',-1), ('ct',-.1),
                                       ('dihedral_deg',89), ('sweep_deg',-89)])
def test_invalid_dimensions_cannot_be_passed_to_the_native_model(key, value):
    wing, params = geometry()
    wing[key] = value
    with pytest.raises(ValueError, match='OpenVSP'):
        projected_wing_stations(wing, params)


@pytest.mark.parametrize('planform', ['elliptical', 'trapezoidal'])
def test_stale_planform_geometry_requires_recalculation(planform):
    wing, params = geometry(planform)
    wing['S'] *= 1.01
    with pytest.raises(ValueError, match='Przelicz'):
        projected_wing_stations(wing, params)


def test_break_outside_half_span_and_unknown_planform_are_rejected():
    wing, params = geometry('compound_trapezoid')
    wing['break_station_m'] = wing['b']/2
    with pytest.raises(ValueError, match='załamanie'):
        projected_wing_stations(wing, params)
    with pytest.raises(ValueError, match='nieobsługiwany'):
        projected_wing_stations(wing, dict(params, wing_planform='unknown'))


def test_missing_break_uses_the_explicit_ratio():
    wing, params = geometry('compound_trapezoid')
    wing.pop('break_station_m')
    assert projected_wing_stations(wing, params)[0][1][0] == .371*wing['b']/2
