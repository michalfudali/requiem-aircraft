"""Ground support geometry and identical-engine scaling are physical invariants."""
import pytest
from calculations.empennage import calculate_propulsion_clearance
from calculations.landing_gear import calculate_fuselage_and_gear


def test_forward_cg_can_govern_lateral_turnover_even_when_aft_cg_is_stable():
    params = dict(x_nose_m=1., x_main_m=4., track_m=2.4, z_cg_m=1.2,
                  cg_fwd_m=2., cg_aft_m=3.7)
    aft_only = calculate_fuselage_and_gear({**params, 'cg_fwd_m': 3.7})
    complete = calculate_fuselage_and_gear(params)
    assert aft_only['tipover_compliant']
    assert complete['main_gear_cg_compliant']
    assert not complete['tipover_compliant']
    assert complete['tipover_reference_cg_m'] == 2.
    assert complete['tipover_angle_3d_deg'] > 60


@pytest.mark.parametrize('gear_type, main', [('tricycle', 4.), ('tailwheel', -2.)])
def test_supplied_wheelbase_and_station_determine_the_other_contact(gear_type, main):
    result = calculate_fuselage_and_gear(dict(landing_gear_type=gear_type,
        x_nose_m=1., wheelbase_m=3., cg_fwd_m=0., cg_aft_m=.5))
    dims = result['gear_dimensions']
    assert dims['wheelbase_m'] == 3.
    assert dims['x_main_m'] == main
    assert dims['x_nose_m'] == 1.


@pytest.mark.parametrize('count', [1, 2, 4])
def test_identical_propellers_retain_diameter_loading_and_total_thrust(count):
    one = calculate_propulsion_clearance(dict(engine_power_kw=150., n_engines=1, prop_rpm=1200))
    several = calculate_propulsion_clearance(dict(engine_power_kw=150.*count, n_engines=count, prop_rpm=1200))
    assert several['propeller_diameter_m'] == one['propeller_diameter_m']
    assert several['disk_loading_kw_m2'] == one['disk_loading_kw_m2']
    assert several['power_per_engine_kw'] == 150.
    assert several['static_thrust_n'] == pytest.approx(count * one['static_thrust_n'], abs=.21)


@pytest.mark.parametrize('engine', ['none', 'jet'])
def test_aircraft_without_propellers_does_not_receive_a_propeller_check(engine):
    result = calculate_propulsion_clearance(dict(engine_type=engine, engine_power_kw=300., n_engines=2))
    assert not result['applicable']
    assert result['propeller_diameter_m'] == 0
    assert result['blade_count'] == 0


@pytest.mark.parametrize('count', [0, -1, 1.5, True, float('nan'), float('inf')])
def test_invalid_engine_count_is_rejected(count):
    with pytest.raises(ValueError, match='Liczba silników'):
        calculate_propulsion_clearance(dict(n_engines=count))
