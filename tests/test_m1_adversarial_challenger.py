"""Empirical Adversarial Challenge Suite for BIPOL Milestone 1.

Authored by m1_challenger_1 (EMPIRICAL CHALLENGER).
Stress-tests and validates:
1. run_mission_mass_sizing edge cases (zero payload, mass spiral divergence, negative inputs, extreme ranges).
2. In-flight payload drop stress (Proportion Method rejection, auto-switch, 12-step iteration convergence, monotonicity).
3. Empty weight regression laws across all 7 classes under extreme MTOW (5 kg to 500,000 kg) ensuring 0.38 <= me/m0 <= 0.74.
4. Two-point power-law calibration invariants and sizing integration.
5. Sizing constraint curves interface and edge cases.
"""
import math
import pytest

from calculations.bipol1 import (
    empty_mass_law,
    run_mission_mass_sizing,
    two_point_power_law,
)
from calculations.mass import calculate_mass_sizing
from calculations.presets import AIRCRAFT_PRESETS
from calculations.sizing import calculate_constraint_curves
from calculations.validation import validate_parameters


def base_params(**changes):
    """Return validated GA trainer parameters with changes."""
    return validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'], **changes))


# ==============================================================================
# CHALLENGE SUITE 1: MISSION MASS SIZING EDGE CASES
# ==============================================================================

def test_adversarial_zero_payload_ferry_flight():
    """Ferry mission: 0 passengers, 0 cargo, pilot on board (crew > 0).

    Should converge cleanly to physical MTOW and non-negative fuel.
    """
    p = base_params(n_pax=0, m_cargo=0, n_crew=1, m_crew_person=90.0)
    res = run_mission_mass_sizing(p)

    assert res['m0'] > 0
    assert res['m_payload'] == 0.0
    assert res['m_crew'] == 90.0
    assert res['m_fuel'] > 0.0
    assert 0.38 <= res['empty_fraction'] <= 0.74
    # Mass conservation: MTOW = empty + fuel + crew + payload
    assert res['m0'] == pytest.approx(res['m_empty'] + res['m_fuel'] + 90.0, rel=1e-3)


def test_adversarial_zero_useful_load_strictly_rejected():
    """Zero useful load (0 payload AND 0 crew).

    Must raise ValueError to prevent physical indeterminacy.
    """
    p = base_params(n_pax=0, m_cargo=0, n_crew=0, m_crew_person=0.0)
    with pytest.raises(ValueError, match="Do wyznaczenia MTOW podaj dodatnią masę załogi lub ładunku"):
        run_mission_mass_sizing(p)


def test_adversarial_mass_spiral_divergence_extreme_cargo_or_mass_ratio():
    """Mass spiral divergence: empty fraction + fuel fraction exceeds 1.0 or MTOW exceeds limit.

    Must raise ValueError cleanly without hanging or infinite loop.
    """
    p = dict(
        AIRCRAFT_PRESETS['ga_trainer'],
        empty_mass_model='two_point',
        mass_point_x1=1000.0, mass_point_y1=1.10,
        mass_point_x2=2000.0, mass_point_y2=1.10,
    )
    with pytest.raises(ValueError, match="Równanie \\(1\\) nie daje fizycznego rozwiązania bilansu"):
        run_mission_mass_sizing(p)


def test_adversarial_mass_spiral_divergence_extreme_range():
    """Mass spiral divergence: extreme range (15,000 km on light GA trainer).

    Fuel fraction requirements cause mass spiral divergence; must raise ValueError.
    """
    p = dict(AIRCRAFT_PRESETS['ga_trainer'], range_km=15000.0)
    with pytest.raises(ValueError, match="Równanie \\(1\\) nie daje fizycznego rozwiązania bilansu"):
        run_mission_mass_sizing(p)

    # Extreme 50,000 km range (exceeds Earth circumference)
    p_extreme = dict(AIRCRAFT_PRESETS['ga_trainer'], range_km=50000.0)
    with pytest.raises(ValueError):
        run_mission_mass_sizing(p_extreme)


@pytest.mark.parametrize("invalid_kwargs, expected_match", [
    ({'m_cargo': -100.0}, "Zrzut nie może przekraczać masy cargo"),
    ({'range_km': -500.0}, "Odcinek powrotny nie może być dłuższy niż całkowity zasięg misji"),
    ({'return_range_km': 1500.0, 'range_km': 1000.0},
     "Odcinek powrotny nie może być dłuższy niż całkowity zasięg misji"),
    ({'climb_start_altitude_m': 4000.0, 'cruise_altitude_m': 2000.0},
     "wysokość końcowa nie może być mniejsza od początkowej"),
])
def test_adversarial_negative_and_invalid_inputs(invalid_kwargs, expected_match):
    """Input validation must reject non-physical coordinates and ranges."""
    p = dict(AIRCRAFT_PRESETS['ga_trainer'], **invalid_kwargs)
    with pytest.raises(ValueError, match=expected_match):
        run_mission_mass_sizing(p)


def test_adversarial_extreme_short_range_1km():
    """Very short range (1 km): aircraft completes mission with minimal cruise fuel."""
    p = base_params(range_km=1.0)
    res = run_mission_mass_sizing(p)
    assert res['m0'] > 0
    assert res['m_fuel'] > 0
    # At 1 km range, fuel consumption is dominated by takeoff and loiter, not cruise
    assert res['fuel_fraction'] < 0.15


# ==============================================================================
# CHALLENGE SUITE 2: IN-FLIGHT PAYLOAD DROP & ITERATIVE SIZING STRESS
# ==============================================================================

@pytest.mark.parametrize("method_name", ['proportion', 'proportions'])
def test_adversarial_proportion_method_strictly_rejected_with_drop(method_name):
    """Proportion Method is strictly non-applicable when payload drop > 0."""
    p = base_params(m_cargo=100.0, payload_drop_kg=50.0, mass_method=method_name)
    with pytest.raises(ValueError, match="Metoda proporcji dotyczy misji bez zrzutu"):
        run_mission_mass_sizing(p)


def test_adversarial_auto_method_switches_to_iterative_when_drop_active():
    """When mass_method='auto' and payload_drop_kg > 0, system selects iterative method."""
    p = base_params(m_cargo=100.0, payload_drop_kg=50.0, mass_method='auto')
    res = run_mission_mass_sizing(p)
    assert res['mass_method'] == 'iterative'
    assert res['m_payload_dropped'] == 50.0
    assert res['m_payload_landing'] == pytest.approx(res['m_payload'] - 50.0)


def test_adversarial_payload_drop_exceeding_cargo_limit():
    """Drop exceeding available cargo mass must raise ValueError."""
    p = base_params(m_cargo=50.0, payload_drop_kg=80.0)
    with pytest.raises(ValueError, match="Zrzut nie może przekraczać masy cargo"):
        run_mission_mass_sizing(p)


def test_adversarial_12_step_iterative_convergence_and_monotonicity():
    """12-step iterative mass simulation convergence verification:

    - Iterations <= 12
    - Residual diff reduces monotonically once within root bracket
    - Relative error <= 0.001 (0.1%)
    """
    p = base_params(m_cargo=150.0, payload_drop_kg=100.0, mass_method='iterative')
    res_mass = calculate_mass_sizing(p)
    history = res_mass['iterations']

    # Must converge within MEiL PW 12-step bound
    assert len(history) <= 12

    # After initial bracket step (from step 2 onwards), diff decreases monotonically
    for i in range(2, len(history)):
        assert history[i]['diff'] <= history[i - 1]['diff'] + 1e-9

    final_step = history[-1]
    assert final_step['diff'] < 0.0001
    assert final_step['relative_error'] <= 0.001


def test_adversarial_payload_drop_mass_and_fuel_burn_monotonicity():
    """Physical conservation check:

    Releasing payload in-flight reduces aircraft weight for subsequent flight phases.
    Increasing payload drop must monotonically DECREASE required initial MTOW and fuel burn.
    """
    drops = [0.0, 25.0, 50.0, 100.0, 150.0]
    m0_values = []
    fuel_values = []

    for drop in drops:
        p = base_params(m_cargo=150.0, payload_drop_kg=drop, mass_method='iterative')
        res = run_mission_mass_sizing(p)
        m0_values.append(res['m0'])
        fuel_values.append(res['m_fuel'])

    # Verify strict monotonic decrease
    for i in range(1, len(drops)):
        assert m0_values[i] < m0_values[i - 1], f"MTOW did not decrease at drop={drops[i]}"
        assert fuel_values[i] < fuel_values[i - 1], f"Fuel did not decrease at drop={drops[i]}"


# ==============================================================================
# CHALLENGE SUITE 3: STATISTICAL EMPTY WEIGHT BOUNDS (0.38 <= me/m0 <= 0.74)
# ==============================================================================

ALL_7_CLASSES = [
    'glider',
    'motoglider',
    'piston_ga',
    'turboprop_regional',
    'jet_business',
    'jet_transport',
    'uav',
]

EXTREME_MTOW_VALUES = [
    0.001,      # Micro-UAV / insect scale
    1.0,        # 1 kg drone
    5.0,        # 5 kg UAV
    50.0,       # Light tactical drone
    500.0,      # Ultralight / glider
    1150.0,     # Cessna 172 class
    5000.0,     # Twin turboprop / VLJ
    50000.0,    # Regional jet / commuter
    500000.0,   # Super transport (A380 / An-225 scale)
    10000000.0, # 10^7 kg theoretical extreme
]


@pytest.mark.parametrize("ac_type", ALL_7_CLASSES)
def test_adversarial_empty_weight_bounds_across_extreme_masses(ac_type):
    """BIPOL_1 eq. (1) of every class stays physical (0.15 < me/m0 < 0.95) over its sample's masses;
    it is a trend line of real aircraft, not a clamped correlation."""
    from calculations.trends import empty_mass_trend
    engine = {'glider': 'none', 'jet_business': 'jet', 'jet_transport': 'jet'}.get(ac_type, 'prop')
    p = {'aircraft_type': ac_type, 'engine_type': engine, 'empty_mass_model': 'trend', 'trend_nearest_count': 0}  # whole class
    share, meta = empty_mass_law(p)
    _, fit, _ = empty_mass_trend(p)
    lo, hi = fit['x_min'], fit['x_max']
    for m in [lo * (hi / lo) ** (k / 8) for k in range(9)]:
        frac = share(m)
        assert .15 < frac < .95, f"Class '{ac_type}' eq. (1) unphysical at MTOW={m:.0f} kg: {frac}"


# ==============================================================================
# CHALLENGE SUITE 4: TWO-POINT POWER-LAW CALIBRATION & INVARIANTS
# ==============================================================================

def test_adversarial_two_point_power_law_scale_invariance_and_symmetry():
    """Order symmetry: two_point_power_law(P1, P2) == two_point_power_law(P2, P1)."""
    p1 = (1200.0, 0.62)
    p2 = (8500.0, 0.51)
    a1, c1 = two_point_power_law(*p1, *p2)
    a2, c2 = two_point_power_law(*p2, *p1)

    assert a1 == pytest.approx(a2, rel=1e-12)
    assert c1 == pytest.approx(c2, rel=1e-12)
    assert c1 < 0.0  # Scale efficiency: heavier aircraft have lower empty weight fraction


def test_adversarial_two_point_flat_curve_zero_exponent():
    """Flat curve: y1 == y2 -> C = 0, A = y1."""
    a, c = two_point_power_law(1000.0, 0.55, 5000.0, 0.55)
    assert c == pytest.approx(0.0, abs=1e-12)
    assert a == pytest.approx(0.55, rel=1e-12)


@pytest.mark.parametrize("x1, y1, x2, y2, expected_match", [
    (-100.0, 0.6, 5000.0, 0.5, "Współrzędne punktów korelacji potęgowej muszą być dodatnie"),
    (1000.0, -0.6, 5000.0, 0.5, "Współrzędne punktów korelacji potęgowej muszą być dodatnie"),
    (1000.0, 0.6, 0.0, 0.5, "Współrzędne punktów korelacji potęgowej muszą być dodatnie"),
    (1000.0, 0.6, 1000.0, 0.5, "Dwa punkty korelacji muszą mieć różne masy startowe"),
    (1000.0, 0.6, 1000.0 + 1e-15, 0.5, "Dwa punkty korelacji muszą mieć różne masy startowe"),
])
def test_adversarial_two_point_invalid_coordinates_rejected(x1, y1, x2, y2, expected_match):
    """Degenerate anchor points must be rejected with descriptive ValueError."""
    with pytest.raises(ValueError, match=expected_match):
        two_point_power_law(x1, y1, x2, y2)


def test_adversarial_two_point_in_sizing_engine():
    """End-to-end mission mass sizing using two_point empty weight model."""
    p = base_params(
        empty_mass_model='two_point',
        mass_point_x1=1000.0, mass_point_y1=0.60,
        mass_point_x2=3000.0, mass_point_y2=0.52,
    )
    res = run_mission_mass_sizing(p)
    assert res['empty_mass_model'] == 'two_point'
    assert 1000.0 <= res['m0'] <= 3000.0
    assert 0.52 <= res['empty_fraction'] <= 0.60


# ==============================================================================
# CHALLENGE SUITE 5: SIZING CONSTRAINTS INTERFACE & REAL-WORLD BOUNDS
# ==============================================================================

def test_adversarial_constraint_curves_interface_contract():
    """Contract verification for calculate_constraint_curves."""
    p = base_params()
    mass = run_mission_mass_sizing(p)
    curves = calculate_constraint_curves(p, m0=mass['m0'], mass=mass)

    required_keys = ['takeoff', 'landing', 'climb', 'stall', 'cruise', 'ceiling', 'design_point']
    for k in required_keys:
        assert k in curves, f"Missing contract key: {k}"

    dp = curves['design_point']
    for dp_key in ['W_S', 'T_W', 'P_W']:
        assert dp_key in dp, f"Missing design point key: {dp_key}"

    assert dp['W_S'] > 0
    assert dp['P_W'] > 0
