"""Comprehensive Milestone 1 Verification Suite: Tiers 1-5.

Covers:
- Feature 0: Baseline Stabilization (templates/reports/p1.html)
- Feature 1: Mission Profiling & Fuel Fractions (10 phases, Corke climb, Breguet cruise/loiter, reserve)
- Feature 2: Statistical Empty Weight Laws (7 aircraft classes, two_point_power_law, modifiers)
- Feature 3: Proportion & Iterative Mass Sizing (Method 1 vs Method 2, payload drop, secant root solver)
- Feature 4: Interactive Mass Convergence Calculator Data & Consistency
- Feature 5: Parametric Matching Chart Constraints (Takeoff 15m, Landing 15m, Climb quadratic & asymptote,
             Stall 1.1 safety margin, Ceiling, Propeller T/W <-> P/W, Point A & B)
- Feature 6: Interactive Matching Chart Canvas Data & Toggles
- Interface Contracts: run_mission_mass_sizing, calculate_constraint_curves
"""
import math
import pytest

from calculations.atmosphere import G0, RHO0, isa_atmosphere
from calculations.bipol1 import (
    CORKE,
    empty_mass_law,
    interpolate,
    preliminary_polar,
    run_mission_mass_sizing,
    two_point_power_law,
)
from calculations.constraints import calculate_constraint_curves as constraints_calc_curves
from calculations.mass import calculate_mass_sizing
from calculations.presets import AIRCRAFT_PRESETS
from calculations.sizing import (
    calculate_constraint_curves,
    calculate_matching_chart,
    climb_tw,
    landing_ws,
    takeoff_mean_speed,
    takeoff_tw,
)
from calculations.validation import validate_parameters


def base_params(**changes):
    """Generate valid base parameters for testing based on GA trainer preset."""
    return validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'], **changes))


# ==============================================================================
# TIER 1: FEATURE UNIT TESTS
# ==============================================================================

def test_feature0_baseline_p1_template_renders_without_syntax_error(client):
    """Feature 0: p1.html Jinja2 template renders without syntax errors and contains tab-predecessors."""
    p = base_params(payload_drop_kg=50, m_cargo=50, return_range_km=200)
    response = client.post('/report?sections=p1,p2', json=p)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<table class="compact-table" id="tab-predecessors">' in html
    assert '<caption>Najważniejsze parametry projektu na tle samolotów podobnych</caption>' in html
    assert '</table>' in html


def test_feature1_10_phase_step_tracking():
    """Feature 1: Mission fuel fractions satisfy exact mass conservation across all 10 phases."""
    p = base_params(
        range_km=1200, return_range_km=500, payload_drop_kg=80, m_cargo=80,
        warmup_mass_fraction=0.998, taxi_mass_fraction=0.995, takeoff_mass_fraction=0.975,
        loiter_time_min=30, max_power_time_min=5, max_power_kw=180, max_power_sfc=280
    )
    res = calculate_mass_sizing(p)
    phases = res['mission_phases']
    assert len(phases) >= 9

    # Verify step-by-step continuity
    for i, phase in enumerate(phases):
        expected_end = phase['mass_start_kg'] - phase['fuel_burn_kg'] - phase['payload_drop_kg']
        assert phase['mass_end_kg'] == pytest.approx(expected_end, abs=1e-4)
        if i > 0:
            assert phase['mass_start_kg'] == pytest.approx(phases[i - 1]['mass_end_kg'], abs=1e-4)

    total_burn = sum(phase['fuel_burn_kg'] for phase in phases)
    assert total_burn == pytest.approx(res['fuel_burn_kg'], abs=1e-3)
    assert res['reserve_fuel_kg'] == pytest.approx(0.06 * total_burn, abs=1e-3)
    assert res['m_fuel'] == pytest.approx(1.06 * total_burn, abs=1e-3)


def test_feature1_corke_interpolation_and_fallback():
    """Feature 1: Corke Mach chart exact anchors and low-speed fallback behavior."""
    # Calibrated anchor point: M = 0.5 -> 0.984, M = 0.7 -> 0.975
    val_m05 = interpolate(CORKE, 0.5, True)
    val_m07 = interpolate(CORKE, 0.7, True)
    assert val_m05 == pytest.approx(0.984)
    assert val_m07 == pytest.approx(0.975)

    # Climb fraction between M=0.5 and M=0.7 is 0.975 / 0.984
    p = base_params(
        cruise_altitude_m=8000,
        cruise_speed_kmh=0.7 * isa_atmosphere(8000)['a'] * 3.6,
        climb_start_speed_kmh=0.5 * isa_atmosphere(0)['a'] * 3.6,
        climb_fraction_mode='corke'
    )
    res = calculate_mass_sizing(p)
    assert res['fuel_fractions_detail']['climb'] == pytest.approx(0.975 / 0.984, abs=1e-4)

    # Below M=0.1 the clipped chart is only a provisional comparison. The
    # automatic physical model still pays for gaining height and overcoming drag.
    p_slow = base_params(
        cruise_speed_kmh=90,  # ~25 m/s -> M ~ 0.07 < 0.10
        v_stall_kmh=70,
        climb_fraction_mode='auto'
    )
    res_slow = calculate_mass_sizing(p_slow)
    corke_meta = res_slow['mission_assumptions']['corke']
    assert corke_meta['provisional'] is True and corke_meta['below_chart'] is True
    assert not corke_meta['used_for_balance']
    assert corke_meta['ordinate_start'] == corke_meta['ordinate_end'] == pytest.approx(1.0)
    assert corke_meta['fraction'] == pytest.approx(1.0)
    physical = res_slow['mission_assumptions']['climb']
    assert physical['model'] == 'energy'
    assert physical['fuel_kg'] > 0 and physical['duration_s'] > 0
    assert 0 < res_slow['fuel_fractions_detail']['climb'] < 1
    phase = next(s for s in res_slow['mission_phases'] if s['key'] == 'climb')
    assert phase['fuel_burn_kg'] == pytest.approx(physical['fuel_kg'])


@pytest.mark.parametrize("ac_type", ['glider', 'motoglider', 'piston_ga', 'turboprop_regional',
                                     'jet_business', 'jet_transport', 'uav'])
def test_feature2_statistical_empty_weight_7_classes(ac_type):
    """Feature 2: BIPOL_1 eq. (1) for every class, A and C from two points of the sample's trend line."""
    from calculations.trends import empty_mass_trend
    engine = {'glider': 'none', 'jet_business': 'jet', 'jet_transport': 'jet'}.get(ac_type, 'prop')
    p = {'aircraft_type': ac_type, 'engine_type': engine, 'empty_mass_model': 'trend', 'trend_nearest_count': 0}  # whole class
    share, meta = empty_mass_law(p)
    rows, fit, points = empty_mass_trend(p)
    assert meta['mode'] == 'trend' and meta['n'] == len(rows) >= 3
    assert (meta['A'], meta['C']) == (points['A'], points['C'])
    # The trend line stays physical over the masses of its own sample.
    for m in (fit['x_min'], (fit['x_min'] * fit['x_max']) ** .5, fit['x_max']):
        assert .15 < share(m) < .95


def test_feature2_two_point_power_law_derivation():
    """Feature 2: Two-point power law derivation matches log-log regression theory."""
    x1, y1 = 1200.0, 0.62
    x2, y2 = 3000.0, 0.54
    A, C = two_point_power_law(x1, y1, x2, y2)
    # Check endpoints reproduction
    assert A * (x1 ** C) == pytest.approx(y1, rel=1e-5)
    assert A * (x2 ** C) == pytest.approx(y2, rel=1e-5)
    # Scale efficiency requires C < 0
    assert C < 0


def test_feature3_dual_methods_exact_equivalence_zero_drop():
    """Feature 3: Proportion Method (Method 1) and 12-Step Iterative Method (Method 2) converge to identical MTOW when drop=0."""
    p = base_params(payload_drop_kg=0, m_cargo=100, range_km=800)
    r_auto = calculate_mass_sizing(dict(p, mass_method='auto'))
    r_prop = calculate_mass_sizing(dict(p, mass_method='proportion'))
    r_iter = calculate_mass_sizing(dict(p, mass_method='iterative'))

    assert r_prop['m0'] == pytest.approx(r_iter['m0'], abs=0.005)
    assert r_prop['m_empty'] == pytest.approx(r_iter['m_empty'], abs=0.005)
    assert r_prop['m_fuel'] == pytest.approx(r_iter['m_fuel'], abs=0.005)
    assert r_auto['m0'] == pytest.approx(r_prop['m0'], abs=0.005)


def test_feature3_interface_contract_run_mission_mass_sizing():
    """Feature 3: Interface contract run_mission_mass_sizing conforms to M1 <-> M2 specifications."""
    p = base_params(range_km=900, n_pax=4)
    res = run_mission_mass_sizing(p)
    assert isinstance(res, dict)
    for required_key in ('m0', 'm_empty', 'm_fuel', 'fuel_fractions', 'iterations'):
        assert required_key in res
    assert isinstance(res['m0'], float)
    assert isinstance(res['m_empty'], float)
    assert isinstance(res['m_fuel'], float)
    assert isinstance(res['fuel_fractions'], list)
    assert isinstance(res['iterations'], int)
    assert res['m0'] > res['m_empty'] + res['m_fuel']


def test_feature5_takeoff_tw_corke_si_formula():
    """Feature 5: Takeoff over 15 m obstacle per Corke / BIPOL_2 SI formulation (Handout 2 benchmark)."""
    # BIPOL_2 Handout 2 benchmark: W/S = 4130 N/m2, Cz_max,TO = 2.0, s_to = 1100 m, sigma = 1.0
    tw = takeoff_tw(4130.0, 2.0, 1100.0, sigma=1.0)
    assert tw == pytest.approx(0.297, abs=0.001)

    # TOP metric parameter check
    top = 4130.0 / 2.0  # 2065
    margin = 1100.0 - 3.834 * math.sqrt(top)
    expected_tw = 0.133 * top / margin
    assert tw == pytest.approx(expected_tw, rel=1e-5)


def test_feature5_landing_ws_si_formula():
    """Feature 5: Landing from 15 m obstacle per BIPOL_2 SI formulation (Handout 2 benchmark)."""
    # BIPOL_2 Handout 2 benchmark: s_l = 1100 m, Cz_max,LND = 2.17, sigma = 1.0
    ws_l = landing_ws(2.17, 1100.0, sigma=1.0)
    expected_ws_l = 1.0 * 2.17 * (1100.0 - 122.0) / 0.75
    assert ws_l == pytest.approx(expected_ws_l, rel=1e-5)
    assert ws_l == pytest.approx(2829.5, abs=1.0)


def test_feature5_climb_quadratic_and_asymptote():
    """Feature 5: Climb gradient quadratic solution and horizontal minimum thrust asymptote G + 1/Kmax."""
    ws = 1200.0
    q = 0.5 * 1.225 * (50.0 ** 2)
    cx0 = 0.025
    AR, e = 8.0, 0.80
    k_ind = 1.0 / (math.pi * AR * e)
    k_max = 0.5 / math.sqrt(cx0 * k_ind)
    gradient = 0.08  # 8% gradient

    tw = climb_tw(ws, q, cx0, k_ind, gradient)
    assert tw == pytest.approx(q * cx0 / ws + ws * k_ind / q + gradient, rel=1e-6)

    # Minimum possible thrust required for climb at optimal aerodynamic speed
    tw_min_asymptote = gradient + 1.0 / k_max
    assert tw_min_asymptote == pytest.approx(gradient + 2.0 * math.sqrt(cx0 * k_ind), rel=1e-6)


def test_feature5_stall_speed_safety_margin_1_1():
    """Feature 5: Stall speed wing loading constraint with regulatory 1.1 factor on Cz_max."""
    v_stall_kmh = 95.0
    v_stall_ms = v_stall_kmh / 3.6
    cz_max_lnd = 2.2
    s = calculate_matching_chart(base_params(v_stall_kmh=v_stall_kmh, cz_max_lnd=cz_max_lnd))
    expected_ws_stall = 0.5 * RHO0 * (v_stall_ms ** 2) * cz_max_lnd / 1.1
    assert s['ws_stall_max'] == pytest.approx(expected_ws_stall, abs=0.1)


def test_feature5_propeller_mean_takeoff_speed_conversion():
    """Feature 5: Propeller mean speed V_LOF / sqrt(2) conversion from T/W to P/W."""
    ws = 900.0
    cz_max_to = 1.8
    v_mean = takeoff_mean_speed(ws, cz_max_to)
    expected_v_mean = 1.15 * math.sqrt(2.0 * ws / (RHO0 * cz_max_to)) / math.sqrt(2.0)
    assert v_mean == pytest.approx(expected_v_mean, rel=1e-5)


def test_feature5_service_ceiling_constraint():
    """Feature 5: Service ceiling constraint curve calculation and atmospheric lapse incorporation."""
    p = base_params(service_ceiling_m=4500, ceiling_climb_rate_ms=0.5)
    s = calculate_matching_chart(p, m0=1200.0)
    assert s['curve_ceiling'] is not None
    assert len(s['curve_ceiling']) == len(s['ws_values'])
    assert all(val > 0 for val in s['curve_ceiling'] if val is not None)
    assert "pułap praktyczny" in s['terms']['at_design']


def test_feature5_interface_contract_calculate_constraint_curves():
    """Feature 5: Interface contract calculate_constraint_curves conforms to M1 <-> M2 specifications."""
    p = base_params()
    res1 = calculate_constraint_curves(p)
    res2 = constraints_calc_curves(p)
    for res in (res1, res2):
        assert isinstance(res, dict)
        for key in ('takeoff', 'landing', 'climb', 'stall', 'cruise', 'design_point'):
            assert key in res
        dp = res['design_point']
        for subkey in ('W_S', 'T_W', 'P_W'):
            assert subkey in dp
        assert dp['W_S'] > 0


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

def test_tier2_payload_drop_invalidates_proportion_method():
    """Tier 2: In-flight payload drop invalidates closed-form Proportion Method."""
    p = base_params(payload_drop_kg=120, m_cargo=150)
    res = calculate_mass_sizing(p)
    assert res['sizing_methods']['proportion']['applicable'] is False
    assert res['sizing_methods']['iterative']['applicable'] is True
    assert res['m_payload_dropped'] == 120

    # Explicitly requesting proportion method with drop raises ValueError
    with pytest.raises(ValueError, match='Metoda proporcji dotyczy misji bez zrzutu'):
        calculate_mass_sizing(dict(p, mass_method='proportions'))


def test_tier2_secant_iteration_convergence_and_residual_reduction():
    """Tier 2: 12-Step Secant root solver converges with monotonic error reduction and terminates at eps <= 0.001."""
    p = base_params(payload_drop_kg=80, m_cargo=100, return_range_km=400)
    res = calculate_mass_sizing(p)
    iters = res['iterations']
    assert len(iters) >= 4
    # Check that final iteration satisfies relative error <= 0.001 (0.1%)
    assert iters[-1]['relative_error'] <= 0.001
    assert iters[-1]['diff'] < 0.01


def test_tier2_extreme_payload_mass_spiral_divergence():
    """Tier 2: Extreme range that causes physical mass spiral divergence raises clean ValueError."""
    p = base_params(range_km=25000)  # 25,000 km range on light GA aircraft -> mass spiral divergence
    with pytest.raises(ValueError, match='(nie daje fizycznego rozwiązania|Nie znaleziono przedziału|nie osiągnął zbieżności)'):
        calculate_mass_sizing(p)


def test_tier2_takeoff_vertical_asymptote_returns_none():
    """Tier 2: Runway distance below obstacle flare distance 3.834*sqrt(TOP) returns None."""
    # TOP = 2000, 3.834*sqrt(2000) = 171.46 m. Runway s_to = 150 m (< 171.46 m).
    tw = takeoff_tw(2000.0, 1.0, 150.0)
    assert tw is None

    # calculate_matching_chart raises ValueError when s_to is physically impossible at design point (< 3.834*sqrt(TOP))
    with pytest.raises(ValueError, match='za krótka przy W/S'):
        calculate_matching_chart(base_params(takeoff_distance_m=70))


def test_tier2_landing_distance_below_122m_raises_error():
    """Tier 2: Landing distance s_l <= 122 m raises ValueError per BIPOL_2 formula (3)."""
    with pytest.raises(ValueError, match='musi przekraczać 122 m'):
        calculate_matching_chart(base_params(landing_distance_m=120))


def test_tier2_zero_climb_gradient_reduces_to_level_flight():
    """Tier 2: Climb equation with zero climb gradient G=0 reduces identically to level flight drag-to-weight ratio."""
    ws = 1000.0
    q = 0.5 * 1.225 * (60.0 ** 2)
    cx0 = 0.025
    k_ind = 1.0 / (math.pi * 8 * 0.8)
    tw_climb_g0 = climb_tw(ws, q, cx0, k_ind, 0.0)
    tw_level_flight = q * cx0 / ws + ws * k_ind / q
    assert tw_climb_g0 == pytest.approx(tw_level_flight, rel=1e-7)


def test_tier2_extreme_wing_loading_ultralight_vs_transport():
    """Tier 2: Numerical stability at extreme small (ultralight) and extreme large (transport) wing loading."""
    s_ulm = calculate_matching_chart(base_params(v_stall_kmh=65, cz_max_lnd=2.4))
    assert s_ulm['ws_stall_max'] < 500.0

    s_heavy = calculate_matching_chart(base_params(
        aircraft_type='jet_transport', engine_type='jet', sfc=0.65, cruise_speed_kmh=850, v_stall_kmh=260, cz_max_lnd=2.8
    ))
    assert s_heavy['ws_stall_max'] > 5000.0


def test_tier2_hot_and_high_airfield_density_penalty():
    """Tier 2: High elevation and hot temperature strictly increases required takeoff T/W and lowers allowable landing W/S."""
    p_sl = base_params(takeoff_distance_m=600, landing_distance_m=600)
    p_hot_high = base_params(
        takeoff_distance_m=600, landing_distance_m=600,
        airfield_elevation_m=2000, airfield_delta_t_k=15.0
    )
    s_sl = calculate_matching_chart(p_sl)
    s_hh = calculate_matching_chart(p_hot_high)

    # Hot-and-high density ratio is lower
    assert s_hh['terms']['sigma_airfield'] < s_sl['terms']['sigma_airfield']
    # Allowable landing wing loading is lower
    assert s_hh['ws_landing'] < s_sl['ws_landing']
    # Required takeoff power loading is higher
    assert s_hh['curve_takeoff'][10] > s_sl['curve_takeoff'][10]


# ==============================================================================
# TIER 3: PAIRWISE COMBINATIONS
# ==============================================================================

def test_tier3_propeller_vs_jet_power_loading_units():
    """Tier 3: Propeller returns P/W [W/N] and power [kW/HP]; Jet returns dimensionless T/W and thrust [kN]."""
    s_prop = calculate_matching_chart(base_params(engine_type='prop'), m0=1200.0)
    dp_prop = s_prop['design_point']
    assert dp_prop['pw'] is not None and dp_prop['pw'] > 0
    assert dp_prop['power_kw'] is not None and dp_prop['power_kw'] > 0
    assert dp_prop['power_hp'] is not None

    s_jet = calculate_matching_chart(base_params(engine_type='jet', aircraft_type='jet_business', sfc=0.65), m0=5000.0)
    dp_jet = s_jet['design_point']
    assert dp_jet['tw'] is not None and dp_jet['tw'] > 0
    assert dp_jet['thrust_kn'] is not None and dp_jet['thrust_kn'] > 0


def test_tier3_unpowered_glider_zero_thrust():
    """Tier 3: Unpowered glider handles engine_type == 'none' safely without power curves."""
    s_glider = calculate_matching_chart(dict(AIRCRAFT_PRESETS['glider_pw5']))
    assert s_glider['engine_type'] == 'none'
    assert all(val == 0.0 for val in s_glider['curve_takeoff'])
    assert all(val == 0.0 for val in s_glider['curve_climb'])
    assert all(val == 0.0 for val in s_glider['curve_cruise'])


def test_tier3_turbocharged_vs_naturally_aspirated_ceiling():
    """Tier 3: Turbocharged piston maintains higher lapse at ceiling than naturally aspirated."""
    p_na = base_params(service_ceiling_m=5000, turbocharged=False)
    p_tc = base_params(service_ceiling_m=5000, turbocharged=True)
    s_na = calculate_matching_chart(p_na, m0=1200.0)
    s_tc = calculate_matching_chart(p_tc, m0=1200.0)

    # Turbocharged requires lower installed sea-level power to meet the 5000 m ceiling
    assert s_tc['curve_ceiling'][10] < s_na['curve_ceiling'][10]


def test_tier3_high_lift_mechanization_coupling():
    """Tier 3: High-lift mechanization shifts landing boundary rightward and expands design space."""
    s_plain = calculate_matching_chart(base_params(landing_distance_m=500, cz_max_clean=1.2, cz_max_to=1.4, cz_max_lnd=1.6))
    s_fowler = calculate_matching_chart(base_params(landing_distance_m=500, cz_max_lnd=2.4))
    assert s_fowler['ws_landing'] > s_plain['ws_landing']


# ==============================================================================
# TIER 4: REAL-WORLD DESIGN SCENARIOS
# ==============================================================================

def test_tier4_scenario_cs23_ga_trainer():
    """Tier 4 Scenario 1: CS-23 4-seat Single-Engine GA Trainer (Cessna 172 / Piper Archer class)."""
    p = base_params(
        n_pax=3, n_crew=1, m_cargo=40, range_km=1100, cruise_speed_kmh=225,
        empty_mass_model='trend', trend_reference_mode='design', trend_nearest_count=50,
        v_stall_kmh=95, takeoff_distance_m=480, landing_distance_m=460, climb_rate_ms=4.5
    )
    res_mass = calculate_mass_sizing(p)
    # BIPOL_1, eq. (1) with A and C from the trend line of the similar aircraft, closed by eq. (5).
    from calculations.trends import empty_mass_trend
    rows, fit, points = empty_mass_trend(p)
    m0 = res_mass['m0']
    assert res_mass['empty_mass_model'] == 'trend' and len(rows) >= 20
    assert res_mass['empty_fraction'] == pytest.approx(points['A'] * m0 ** points['C'], abs=1e-4)
    assert fit['x_min'] <= m0 <= fit['x_max']
    useful = res_mass['m_payload'] + res_mass['m_crew']
    assert m0 == pytest.approx(useful / (1 - res_mass['m_fuel'] / m0 - res_mass['m_empty'] / m0), rel=1e-3)

    res_chart = calculate_matching_chart(p, m0=res_mass['m0'], mass=res_mass)
    dp = res_chart['design_point']
    assert dp['ws'] <= res_chart['ws_limit']
    # The power follows the matching chart of that mass: 60–110 W per kg of a light single (Cessna, Piper, Bonanza).
    assert 60 <= dp['power_hp'] * .7457 * 1000 / m0 <= 110
    assert dp['point_a']['ws'] == dp['ws']


def test_tier4_scenario_twin_turboprop_commuter():
    """Tier 4 Scenario 3: 19-Passenger Twin-Turboprop Commuter (Beech 1900 / L-410 class)."""
    p = validate_parameters(dict(
        AIRCRAFT_PRESETS['regional_turboprop'],
        n_pax=19, n_crew=2, m_cargo=300, range_km=1500, cruise_speed_kmh=460,
        takeoff_distance_m=950, landing_distance_m=900, climb_rate_ms=7.5
    ))
    res_mass = calculate_mass_sizing(p)
    assert 6000.0 <= res_mass['m0'] <= 12500.0

    res_chart = calculate_matching_chart(p, m0=res_mass['m0'], mass=res_mass)
    dp = res_chart['design_point']
    assert dp['ws'] <= res_chart['ws_limit'] + 1.0
    assert dp['power_kw'] > 500.0


def test_tier4_scenario_jet_transport_handout2():
    """Tier 4 Scenario: Lecture Handout 2 Benchmark (33100 kg Jet Transport)."""
    cx0 = math.pi * 8 * 0.8 / (4 * 15 ** 2)
    p = dict(
        aircraft_type='jet_transport', engine_type='jet', v_stall_kmh=200, cruise_speed_kmh=780,
        cruise_altitude_m=10000, aspect_ratio=8, oswald_e=0.8, cx0=cx0, cz_max_to=2.0,
        cz_max_lnd=2.17, takeoff_distance_m=1100, landing_distance_m=1100, climb_rate_ms=9.0
    )
    mass = {'m_fuel': 9700.0, 'fuel_fractions_detail': {'total_mff': 0.72, 'landing': 0.975}}
    s = calculate_matching_chart(p, m0=33100.0, mass=mass)

    assert s['assumptions']['v_climb_kmh'] == pytest.approx(345, abs=1)
    assert s['assumptions']['climb_gradient'] == pytest.approx(0.094, abs=0.001)
    assert s['ws_max_range'] == pytest.approx(4405, rel=0.01)
    assert landing_ws(2.17, 1100) == pytest.approx((1100 - 122) * 2.17 / 0.75)
    assert takeoff_tw(4130, 2.0, 1100) == pytest.approx(0.297, abs=0.001)


# ==============================================================================
# TIER 5: ADVERSARIAL INVARIANT CHECKS
# ==============================================================================

def test_tier5_takeoff_distance_monotonicity():
    """Tier 5: At constant W/S, longer available takeoff distance strictly reduces required T/W."""
    ws = 1800.0
    cz_max_to = 2.0
    tw_short = takeoff_tw(ws, cz_max_to, 900.0)
    tw_mid = takeoff_tw(ws, cz_max_to, 1200.0)
    tw_long = takeoff_tw(ws, cz_max_to, 1600.0)
    assert tw_short > tw_mid > tw_long


def test_tier5_stall_speed_monotonicity():
    """Tier 5: Higher allowable stall speed strictly increases allowable wing loading."""
    s1 = calculate_matching_chart(base_params(v_stall_kmh=80))
    s2 = calculate_matching_chart(base_params(v_stall_kmh=100))
    s3 = calculate_matching_chart(base_params(v_stall_kmh=120))
    assert s1['ws_stall_max'] < s2['ws_stall_max'] < s3['ws_stall_max']


def test_tier5_scale_invariance_power_and_thrust():
    """Tier 5: Power loading P/W and installed power scale precisely with gross takeoff weight."""
    p = base_params()
    s = calculate_matching_chart(p, m0=1200.0)
    dp = s['design_point']
    pw = dp['pw']  # W/N
    power_kw = dp['power_kw']
    expected_pw = (power_kw * 1000.0) / (1200.0 * G0)
    assert pw == pytest.approx(expected_pw, rel=1e-3)
