"""ML1 general geometry integrals and the P6 supplement, with independent examples."""
import math

import pytest

from calculations.atmosphere import G0, isa_atmosphere
from calculations.ml1 import integrate_planform, elliptical_planform, prandtl_corrected_cd, altitude_polars


def test_rectangular_wing_has_exact_area_mac_and_weighted_position():
    r = integrate_planform([dict(y_m=0, x_le_m=0, chord_m=2), dict(y_m=5, x_le_m=1, chord_m=2)])
    assert r['area_m2'] == 20
    assert r['span_m'] == 10
    assert r['aspect_ratio'] == 5
    assert r['mac_m'] == 2
    assert r['x_n_mac_m'] == .5
    assert r['y_mac_m'] == 2.5


def test_trapezoid_integrals_equal_the_closed_form_course_relations():
    b, cr, ct, leading_sweep = 12., 3., 1.2, math.radians(17)
    r = integrate_planform([dict(y_m=0, x_le_m=0, chord_m=cr),
                            dict(y_m=b/2, x_le_m=b/2*math.tan(leading_sweep), chord_m=ct)])
    taper = ct/cr
    assert r['area_m2'] == b*(cr+ct)/2
    assert r['mac_m'] == pytest.approx(2*cr*(1+taper+taper*taper)/(3*(1+taper)), rel=1e-13)
    assert r['x_n_mac_m'] == pytest.approx(b*math.tan(leading_sweep)*(1+2*taper)/(6*(1+taper)), rel=1e-13)


def test_arbitrary_broken_planform_keeps_each_geometry_segment():
    r = integrate_planform([dict(y_m=0, x_le_m=0, chord_m=3),
                            dict(y_m=1, x_le_m=.5, chord_m=3),
                            dict(y_m=2, x_le_m=2, chord_m=1)])
    # Independent segment integration gives Ic=5, Ic²=40/3, Icx=3, Iyc=13/3.
    assert r['area_m2'] == 10
    assert r['mac_m'] == pytest.approx(8/3, rel=1e-13)
    assert r['x_n_mac_m'] == pytest.approx(.6, rel=1e-13)
    assert r['y_mac_m'] == pytest.approx(13/15, rel=1e-13)
    assert len(r['segments']) == 2


def test_root_translation_changes_the_coordinate_but_preserves_relative_mac_position():
    first = integrate_planform([dict(y_m=0, x_le_m=0, chord_m=3), dict(y_m=2, x_le_m=2, chord_m=1)])
    shifted = integrate_planform([dict(y_m=0, x_le_m=10, chord_m=3), dict(y_m=2, x_le_m=12, chord_m=1)])
    assert shifted['x_le_mac_m'] == pytest.approx(first['x_le_mac_m']+10)
    assert shifted['x_n_mac_m'] == pytest.approx(first['x_n_mac_m'])
    assert shifted['area_m2'] == first['area_m2'] and shifted['mac_m'] == first['mac_m']


def test_ellipse_uses_the_straight_half_chord_convention_in_ml1():
    r = elliptical_planform(12, 3)
    assert r['area_m2'] == 9*math.pi
    assert r['mac_m'] == 8/math.pi
    assert r['x_n_mac_m'] == pytest.approx(1.5-4/math.pi)
    assert r['y_mac_m'] == 8/math.pi
    swept = elliptical_planform(12, 3, 20)
    assert swept['x_n_mac_m'] == pytest.approx(r['x_n_mac_m'] + r['y_mac_m']*math.tan(math.radians(20)))


@pytest.mark.parametrize('stations', [[], [dict(y_m=0, x_le_m=0, chord_m=2)],
    [dict(y_m=1, x_le_m=0, chord_m=2), dict(y_m=2, x_le_m=0, chord_m=2)],
    [dict(y_m=0, x_le_m=0, chord_m=2), dict(y_m=0, x_le_m=0, chord_m=2)],
    [dict(y_m=0, x_le_m=0, chord_m=-2), dict(y_m=2, x_le_m=0, chord_m=2)],
    [dict(y_m=0, x_le_m=0, chord_m=0), dict(y_m=2, x_le_m=0, chord_m=0)],
    [dict(y_m=0, x_le_m=0, chord_m=2), dict(y_m=2, x_le_m=float('nan'), chord_m=2)]])
def test_invalid_planform_data_are_rejected(stations):
    with pytest.raises(ValueError):
        integrate_planform(stations)


def test_prandtl_corrects_the_whole_drag_coefficient_without_clamping():
    assert prandtl_corrected_cd(.02, 0) == .02
    assert prandtl_corrected_cd(.02, .6) == pytest.approx(.025, abs=1e-15)
    assert prandtl_corrected_cd(.02, .8) == pytest.approx(1/30, abs=1e-15)
    assert prandtl_corrected_cd(.02, .99) > prandtl_corrected_cd(.02, .9)


def test_supplement_height_polars_use_the_point_lift_and_isa_sound_speed():
    polar = [dict(cl=1.0, cd=.04), dict(cl=.5, cd=.025), dict(cl=.01, cd=.02), dict(cl=0, cd=.02)]
    r = altitude_polars(4500, 25, polar, [0, 3000, 6000, 9000])
    for table in r['tables']:
        atm = isa_atmosphere(table['altitude_m'])
        for row in table['rows'][:2]:
            velocity = math.sqrt(2*4500*G0/(atm['rho']*25*row['cl']))
            mach = velocity/atm['a']
            assert row['available']
            assert row['speed_ms'] == pytest.approx(velocity, rel=1e-13)
            assert row['mach'] == pytest.approx(mach, rel=1e-13)
            assert row['cd_corrected'] == pytest.approx(row['cd_incompressible']/math.sqrt(1-mach*mach), rel=1e-13)
        assert not table['rows'][2]['available'] and table['rows'][2]['cd_corrected'] is None
        assert table['rows'][2]['mach'] >= 1
        assert not table['rows'][3]['available'] and table['rows'][3]['speed_ms'] is None
    assert r['tables'][-1]['rows'][0]['cd_corrected'] > r['tables'][0]['rows'][0]['cd_corrected']


@pytest.mark.parametrize('cd,mach', [(.02,1),(.02,1.1),(.02,-.1),(-.01,.2),(.02,float('nan'))])
def test_prandtl_does_not_return_a_fabricated_value_outside_its_domain(cd, mach):
    with pytest.raises(ValueError):
        prandtl_corrected_cd(cd,mach)
