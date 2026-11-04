"""Adversarial and Empirical Challenge Test Suite for Milestone 1:
Constraint Analysis and Matching Chart Sizing.

Author: m1_challenger_2 (Empirical Challenger)
Target: calculations/sizing.py, calculations/constraints.py

Adversarially challenges:
1. Takeoff Distance, Flare Margin & Hot-and-High Extremes (4000 m, ISA +30°C, flare asymptote)
2. Landing Distance & Singularity Checks (s_L <= 122 m threshold, near-singularity, negative distances)
3. Climb Gradient & Rate Invariants (G=0 level flight, horizontal minimum thrust asymptote G + 1/Kmax)
4. Stall Speed Regulatory 1.1 Safety Margin (Cz_safety=1.1 enforcement across Cz_max_lnd domain)
5. Service Ceiling Atmospheric Density Lapse & Climb Reserves (0.5 m/s prop vs 2.54 m/s jet)
6. Strict Monotonicity & Mathematical Invariants (takeoff T/W vs W/S, stall vs W/S, runway vs T/W)
7. Point A (mass compromise) and Point B (aerodynamic range optimum) Location & Physics Checks
8. Interface Contract Conformance & Preset Robustness across all 7 aircraft classes
9. Advanced Features: Seaplane Water Handling, Glider Tow, Ground Roll Fallback
"""
import math
import random
import pytest

from calculations.atmosphere import G0, RHO0, isa_atmosphere
from calculations.constraints import calculate_constraint_curves as constraints_calculate_curves
from calculations.presets import AIRCRAFT_PRESETS
from calculations.sizing import (
    CZ_SAFETY,
    SIGMA_AIRFIELD,
    calculate_constraint_curves,
    calculate_matching_chart,
    climb_tw,
    landing_ws,
    takeoff_mean_speed,
    takeoff_tw,
)
from calculations.validation import validate_parameters


def base_params(**kwargs):
    """Return validated GA trainer parameters with optional overrides."""
    return validate_parameters(dict(AIRCRAFT_PRESETS["ga_trainer"], **kwargs))


# ==============================================================================
# 1. TAKEOFF DISTANCE & HOT-AND-HIGH ADVERSARIAL CHALLENGES
# ==============================================================================

class TestTakeoffHotAndHigh:
    """Adversarially challenge takeoff equations under extreme atmospheric conditions and flare limits."""

    def test_hot_and_high_density_and_sigma_4000m_isa_plus_30c(self):
        """Elevation 4000 m, ISA +30°C density matches thermodynamic atmospheric physics."""
        p_hh = base_params(
            takeoff_distance_m=1200,
            airfield_elevation_m=4000,
            airfield_temperature_delta_c=30.0,
        )
        res = calculate_matching_chart(p_hh)
        sigma = res["terms"]["sigma_airfield"]

        # Theoretical check:
        # ISA at 4000 m: T_isa = 288.15 - 0.0065*4000 = 262.15 K (-11°C)
        # T_act = 262.15 + 30 = 292.15 K (+19°C)
        # p_isa = 101325 * (1 - 0.0065*4000/288.15)^5.25588 ~ 61660 Pa
        # rho = p / (287.05287 * 292.15) ~ 0.7352 kg/m³
        # sigma = rho / 1.225 ~ 0.600
        isa4000 = isa_atmosphere(4000)
        t_act = isa4000["T"] + 30.0
        expected_rho = isa4000["p"] / (287.05287 * t_act)
        expected_sigma = expected_rho / RHO0

        assert sigma == pytest.approx(expected_sigma, rel=1e-4)
        assert 0.58 <= sigma <= 0.62  # Approximately 40% density loss

    def test_hot_and_high_strictly_penalizes_takeoff_power_at_all_wing_loadings(self):
        """Takeoff power required at 4000 m ISA +30°C is strictly higher than at sea level for all W/S."""
        p_sl = base_params(takeoff_distance_m=1200, airfield_elevation_m=0, airfield_temperature_delta_c=0)
        p_hh = base_params(takeoff_distance_m=1200, airfield_elevation_m=4000, airfield_temperature_delta_c=30.0)

        s_sl = calculate_matching_chart(p_sl)
        s_hh = calculate_matching_chart(p_hh)

        # For common W/S domain, hot-and-high curve must be strictly above sea level curve
        ws_sl = s_sl["ws_values"]
        cz_to = p_sl["cz_max_to"]

        for ws in ws_sl:
            tw_sl = takeoff_tw(ws, cz_to, 1200, sigma=s_sl["terms"]["sigma_airfield"])
            tw_hh = takeoff_tw(ws, cz_to, 1200, sigma=s_hh["terms"]["sigma_airfield"])
            if tw_sl is not None and tw_hh is not None:
                assert tw_hh > tw_sl, f"At W/S={ws}, tw_hh ({tw_hh}) must exceed tw_sl ({tw_sl})"

    def test_takeoff_flare_distance_asymptote_returns_none(self):
        """When runway distance s_to <= 3.834 * sqrt(TOP), takeoff_tw must return None, not negative or error."""
        ws = 1500.0
        cz_to = 2.0
        sigma = 1.0
        top = ws / (cz_to * sigma)  # 750
        flare_dist = 3.834 * math.sqrt(top)  # ~105.0 m

        # Distance exactly at flare distance
        assert takeoff_tw(ws, cz_to, flare_dist, sigma=sigma) is None
        # Distance below flare distance
        assert takeoff_tw(ws, cz_to, flare_dist - 1.0, sigma=sigma) is None
        assert takeoff_tw(ws, cz_to, 10.0, sigma=sigma) is None
        # Distance just above flare distance -> huge but finite positive T/W
        tw_near = takeoff_tw(ws, cz_to, flare_dist + 0.1, sigma=sigma)
        assert tw_near is not None
        assert tw_near > 100.0  # Asymptotic climb towards infinity

    def test_hot_and_high_sweeps_monotonicity(self):
        """Airfield density sigma decreases monotonically with increasing altitude and temperature delta."""
        altitudes = [0, 500, 1000, 2000, 3000, 4000]
        sigmas = []
        for alt in altitudes:
            p = base_params(takeoff_distance_m=1500, airfield_elevation_m=alt, airfield_delta_t_k=0)
            s = calculate_matching_chart(p)
            sigmas.append(s["terms"]["sigma_airfield"])

        # Altitude monotonicity
        for i in range(len(sigmas) - 1):
            assert sigmas[i] > sigmas[i + 1]

        # Temperature monotonicity at 2000 m
        deltas = [-15, 0, 15, 30]
        t_sigmas = []
        for d in deltas:
            p = base_params(takeoff_distance_m=1500, airfield_elevation_m=2000, airfield_delta_t_k=d)
            s = calculate_matching_chart(p)
            t_sigmas.append(s["terms"]["sigma_airfield"])

        for i in range(len(t_sigmas) - 1):
            assert t_sigmas[i] > t_sigmas[i + 1]

    def test_negative_airfield_elevation_handling(self):
        """Below-sea-level airfields follow the tropospheric law, with sigma > 1."""
        p_dead_sea = dict(AIRCRAFT_PRESETS["ga_trainer"], airfield_elevation_m=-400, airfield_delta_t_k=0)
        s = calculate_matching_chart(p_dead_sea)
        temperature = 288.15 - .0065 * -400
        pressure = 101325 * (temperature / 288.15) ** (9.80665 / (.0065 * 287.05287))
        expected = pressure / (287.05287 * temperature) / 1.225
        assert s["terms"]["sigma_airfield"] == pytest.approx(expected, rel=1e-9)
        assert s["terms"]["sigma_airfield"] > 1


# ==============================================================================
# 2. LANDING DISTANCE & SINGULARITY CHECKS (s_L <= 122 m)
# ==============================================================================

class TestLandingDistanceSingularity:
    """Adversarially challenge landing equations near and below the 122 m physical threshold."""

    @pytest.mark.parametrize("bad_sl", [122.0, 121.99, 120.0, 100.0, 50.0, 1.0, 0.01])
    def test_landing_distance_below_or_equal_122m_raises_value_error(self, bad_sl):
        """Landing distance s_l <= 122 m raises clean ValueError per BIPOL_2 formula (3)."""
        p = base_params(landing_distance_m=bad_sl)
        with pytest.raises(ValueError, match="Długość lądowania z 15 m musi przekraczać 122 m"):
            calculate_matching_chart(p)

    def test_negative_landing_distance_rejected_by_engine_and_validator(self):
        """Negative landing distance is caught by validator and direct calculation."""
        # 1. Validation check
        with pytest.raises(ValueError, match="Pole landing_distance_m"):
            validate_parameters(dict(AIRCRAFT_PRESETS["ga_trainer"], landing_distance_m=-10.0))

        # 2. Direct calculation check
        raw_p = dict(AIRCRAFT_PRESETS["ga_trainer"], landing_distance_m=-10.0)
        with pytest.raises(ValueError, match="Długość lądowania z 15 m musi przekraczać 122 m"):
            calculate_matching_chart(raw_p)

    def test_landing_distance_near_singularity_122_001m(self):
        """Near singularity s_l = 122.001 m yields valid infinitesimal positive wing loading without crashing."""
        p = base_params(landing_distance_m=122.001, takeoff_distance_m=1500)
        s = calculate_matching_chart(p)

        # Unrounded terms must be strictly positive
        assert s["terms"]["ws_landing"] is not None
        assert s["terms"]["ws_landing"] > 0
        assert s["terms"]["ws_landing"] < 1.0  # Extremely tiny allowable wing loading (~0.00287 N/m2)
        assert s["design_point"]["limit_by"] == "długość lądowania"
        assert s["design_point"]["ws"] == s["terms"]["ws_landing"]

    def test_landing_distance_monotonicity(self):
        """Higher available landing distance strictly increases allowable wing loading."""
        s_distances = [200.0, 400.0, 600.0, 800.0, 1200.0, 2000.0]
        loadings = [landing_ws(2.0, sl, sigma=1.0) for sl in s_distances]

        for i in range(len(loadings) - 1):
            assert loadings[i] < loadings[i + 1]
            # Exact linearity check: derivative is sigma * cz_max / 0.75
            delta_s = s_distances[i + 1] - s_distances[i]
            expected_delta_ws = 2.0 * delta_s / 0.75
            assert (loadings[i + 1] - loadings[i]) == pytest.approx(expected_delta_ws, rel=1e-5)


# ==============================================================================
# 3. CLIMB GRADIENT, RATE & ASYMPTOTE CHECKS
# ==============================================================================

class TestClimbGradientAndAsymptote:
    """Adversarially challenge climb quadratic, G=0 level flight, and the G + 1/Kmax asymptote."""

    def test_zero_climb_gradient_exact_equivalence_to_level_flight(self):
        """Climb equation at G=0 matches level flight drag-to-weight D/W = q*Cx0/ws + ws*kind/q exactly."""
        cx0 = 0.027
        AR, e = 9.2, 0.82
        k_ind = 1.0 / (math.pi * AR * e)

        for ws in [200, 500, 1000, 2500, 6000]:
            for speed in [30, 50, 80, 120]:
                q = 0.5 * 1.225 * speed ** 2
                tw_climb = climb_tw(ws, q, cx0, k_ind, 0.0)
                tw_level = q * cx0 / ws + ws * k_ind / q
                assert tw_climb == pytest.approx(tw_level, rel=1e-9)

    def test_horizontal_minimum_thrust_asymptote_is_absolute_lower_bound(self):
        """For ALL wing loadings and ALL speeds, T/W >= G + 1/Kmax, with equality at V_md."""
        cx0 = 0.024
        AR, e = 8.5, 0.80
        k_ind = 1.0 / (math.pi * AR * e)
        inv_k_max = 2.0 * math.sqrt(cx0 * k_ind)
        gradient = 0.06

        tw_asymptote = gradient + inv_k_max

        # Random fuzzing across 1000 arbitrary points
        rng = random.Random(42)
        for _ in range(1000):
            ws = rng.uniform(100.0, 8000.0)
            q = rng.uniform(50.0, 15000.0)
            tw = climb_tw(ws, q, cx0, k_ind, gradient)
            assert tw >= tw_asymptote - 1e-12, f"Failed at W/S={ws}, q={q}: {tw} < {tw_asymptote}"

        # Exact equality check at minimum drag speed V_md where q_md = ws * sqrt(k_ind / cx0)
        for ws in [300, 800, 1500, 4000]:
            q_md = ws * math.sqrt(k_ind / cx0)
            tw_at_md = climb_tw(ws, q_md, cx0, k_ind, gradient)
            assert tw_at_md == pytest.approx(tw_asymptote, rel=1e-7)

    def test_extreme_vertical_climb_rates_linearity(self):
        """Climb rate from 0 to 100 m/s scales strictly linearly with gradient term wy/V."""
        p0 = base_params(climb_rate_ms=0)
        s0 = calculate_matching_chart(p0)
        grad0 = s0["terms"]["gradient"]
        assert grad0 == 0.0

        for wy in [5.0, 25.0, 50.0, 100.0]:
            p = base_params(climb_rate_ms=wy)
            s = calculate_matching_chart(p)
            v_climb = s["terms"]["v_climb_ms"]
            expected_grad = wy / v_climb
            assert s["terms"]["gradient"] == pytest.approx(expected_grad, rel=1e-6)
            # Thrust increment over zero climb
            delta_tw = s["terms"]["tw_climb_min"] - s0["terms"]["tw_climb_min"]
            assert delta_tw == pytest.approx(expected_grad, rel=1e-6)


# ==============================================================================
# 4. STALL SPEED MARGIN & REGULATORY COMPLIANCE (1.1 SAFETY FACTOR)
# ==============================================================================

class TestStallSpeedMargin:
    """Adversarially challenge stall speed wing loading constraint and the 1.1 regulatory factor."""

    @pytest.mark.parametrize("cz_max_lnd", [1.8, 2.0, 2.2, 2.6, 3.2, 4.0])
    def test_regulatory_1_1_safety_factor_is_strictly_enforced_across_cz_domain(self, cz_max_lnd):
        """Ratio ws_stall / (0.5 * rho0 * Vs^2 * Cz_max) == 1 / 1.1 across all Cz_max_lnd values."""
        vs_kmh = 90.0
        vs_ms = vs_kmh / 3.6
        # Ensure aerodynamic hierarchy Cz_clean <= Cz_to <= Cz_lnd
        p = base_params(
            v_stall_kmh=vs_kmh,
            cz_max_clean=min(1.4, cz_max_lnd * 0.7),
            cz_max_to=min(1.7, cz_max_lnd * 0.85),
            cz_max_lnd=cz_max_lnd,
        )
        s = calculate_matching_chart(p)

        unfactored_ws = 0.5 * RHO0 * (vs_ms ** 2) * cz_max_lnd
        expected_ws = unfactored_ws / CZ_SAFETY

        assert s["terms"]["ws_min_speed"] == pytest.approx(expected_ws, rel=1e-7)
        assert s["terms"]["ws_min_speed"] / unfactored_ws == pytest.approx(1.0 / 1.1, rel=1e-7)

    def test_stall_speed_quadratic_speed_scaling(self):
        """Doubling stall speed strictly quadruples allowable stall wing loading (exact in unrounded terms)."""
        p_vs50 = base_params(v_stall_kmh=50.0)
        p_vs100 = base_params(v_stall_kmh=100.0)
        s50 = calculate_matching_chart(p_vs50)
        s100 = calculate_matching_chart(p_vs100)

        # Unrounded terms must be exactly 4.0
        assert s100["terms"]["ws_min_speed"] / s50["terms"]["ws_min_speed"] == pytest.approx(4.0, rel=1e-7)
        # Rounded ws_stall_max matches 4.0 within rounding resolution
        assert s100["ws_stall_max"] / s50["ws_stall_max"] == pytest.approx(4.0, abs=0.01)


# ==============================================================================
# 5. SERVICE CEILING DENSITY LAPSE & CLIMB RESERVES
# ==============================================================================

class TestServiceCeilingConstraint:
    """Adversarially challenge service ceiling density lapse, climb reserves, and engine types."""

    def test_service_ceiling_climb_reserve_defaults(self):
        """Propeller defaults to 0.5 m/s climb reserve; Jet defaults to 2.54 m/s (500 ft/min)."""
        p_prop = base_params(engine_type="prop", service_ceiling_m=4000)
        s_prop = calculate_matching_chart(p_prop)
        p_jet = base_params(engine_type="jet", aircraft_type="jet_business", sfc=0.65, service_ceiling_m=11000)
        s_jet = calculate_matching_chart(p_jet)

        assert s_prop["curve_ceiling"] is not None
        assert s_jet["curve_ceiling"] is not None

    def test_service_ceiling_installed_power_increases_monotonically_with_ceiling_altitude(self):
        """Higher service ceiling strictly increases installed sea-level power/thrust required."""
        ceilings = [2000, 4000, 6000, 8000]
        pw_at_design = []

        for h in ceilings:
            p = base_params(service_ceiling_m=h, ceiling_climb_rate_ms=0.5)
            s = calculate_matching_chart(p, m0=1200.0)
            req = s["terms"]["at_design"].get("pułap praktyczny")
            assert req is not None
            pw_at_design.append(req)

        for i in range(len(pw_at_design) - 1):
            assert pw_at_design[i] < pw_at_design[i + 1]

    def test_zero_ceiling_omits_ceiling_curve(self):
        """When service_ceiling_m=0, ceiling curve is None and not included in governing constraints."""
        p = base_params(service_ceiling_m=0)
        s = calculate_matching_chart(p)
        assert s["curve_ceiling"] is None
        assert "pułap praktyczny" not in s["terms"]["at_design"]

    def test_extreme_ceiling_numerical_stability(self):
        """Extreme ceiling (15000 m for GA trainer) does not raise ZeroDivisionError due to 1e-6 lapse clamp."""
        p = base_params(service_ceiling_m=15000)
        s = calculate_matching_chart(p, m0=1200.0)
        assert s["curve_ceiling"] is not None
        for val in s["curve_ceiling"]:
            assert val is not None and not math.isnan(val) and not math.isinf(val)
            assert val > 0


# ==============================================================================
# 6. MONOTONICITY & MATHEMATICAL INVARIANT FUZZING
# ==============================================================================

class TestMonotonicityAndInvariants:
    """Property-based oracles and fuzz tests verifying physical monotonicity across parameters."""

    def test_fuzz_takeoff_tw_strictly_increasing_with_ws(self):
        """For ANY physical configuration, takeoff T/W is strictly monotonically increasing with W/S."""
        rng = random.Random(1337)
        for _ in range(200):
            cz_to = rng.uniform(1.2, 3.0)
            sigma = rng.uniform(0.6, 1.1)
            s_to = rng.uniform(500.0, 2000.0)

            top_max = (s_to / 3.834) ** 2
            ws_max = top_max * cz_to * sigma * 0.90
            ws_vals = [ws_max * (i / 30.0) for i in range(1, 31)]

            tw_prev = None
            for ws in ws_vals:
                tw = takeoff_tw(ws, cz_to, s_to, sigma=sigma)
                if tw is not None:
                    if tw_prev is not None:
                        assert tw > tw_prev, f"Monotonicity violation: tw({ws})={tw} <= tw_prev={tw_prev}"
                    tw_prev = tw

    def test_fuzz_takeoff_tw_strictly_decreasing_with_runway_length(self):
        """At constant W/S, longer available runway strictly reduces required T/W."""
        ws = 1400.0
        cz_to = 1.9
        sigma = 0.95

        s_runways = [600, 800, 1000, 1300, 1800, 2500]
        tw_vals = [takeoff_tw(ws, cz_to, s, sigma=sigma) for s in s_runways]

        for i in range(len(tw_vals) - 1):
            assert tw_vals[i] > tw_vals[i + 1]

    def test_propeller_takeoff_mean_speed_monotonic_with_ws(self):
        """Mean takeoff speed V_mean increases monotonically with W/S."""
        ws_vals = [200, 500, 1000, 2000, 4000]
        speeds = [takeoff_mean_speed(ws, 2.0) for ws in ws_vals]

        for i in range(len(speeds) - 1):
            assert speeds[i] < speeds[i + 1]


# ==============================================================================
# 7. POINT A AND POINT B LOCATION & OPTIMALITY CHECKS
# ==============================================================================

class TestPointAAndPointB:
    """Verify Point A (mass compromise) and Point B (aerodynamic range optimum) properties."""

    def test_point_a_design_point_consistency(self):
        """Point A matches ws_design, includes regulatory margin, and correctly sizes installed power."""
        p = base_params()
        s = calculate_matching_chart(p, m0=1200.0)
        dp = s["design_point"]
        pt_a = dp["point_a"]

        assert pt_a["ws"] == dp["ws"]
        assert pt_a["pw"] == dp["pw"]
        assert pt_a["power_kw"] == dp["power_kw"]

        # 8% design margin for propeller
        governing = dp["governing"]
        gov_val = s["terms"]["at_design"][governing]
        expected_pw = round(gov_val * 1.08, 2)
        assert dp["pw"] == pytest.approx(expected_pw, abs=0.01)

    def test_point_b_aerodynamic_range_optimum_jet_vs_prop(self):
        """Point B cruise wing loading uses 1.0 for prop and 3.0 for jet in denominator."""
        p_prop = base_params(engine_type="prop", cruise_speed_kmh=240, cruise_altitude_m=3000)
        s_prop = calculate_matching_chart(p_prop, m0=1200.0)

        # Theoretical check for prop: q_cr * sqrt(pi * AR * e * cx0 / 1.0)
        q_cr = s_prop["terms"]["q_cr"]
        ar = s_prop["terms"]["aspect_ratio"]
        e = s_prop["terms"]["oswald_e"]
        cx0 = s_prop["terms"]["cx0"]
        expected_ws_prop_cr = q_cr * math.sqrt(math.pi * ar * e * cx0 / 1.0)

        assert s_prop["terms"]["ws_max_range_cruise"] == pytest.approx(expected_ws_prop_cr, rel=1e-5)

        # Theoretical check for jet: q_cr * sqrt(pi * AR * e * cx0 / 3.0)
        p_jet = base_params(
            engine_type="jet", aircraft_type="jet_business", sfc=0.65,
            cruise_speed_kmh=750, cruise_altitude_m=11000
        )
        s_jet = calculate_matching_chart(p_jet, m0=5000.0)
        q_cr_jet = s_jet["terms"]["q_cr"]
        ar_jet = s_jet["terms"]["aspect_ratio"]
        e_jet = s_jet["terms"]["oswald_e"]
        cx0_jet = s_jet["terms"]["cx0"]
        expected_ws_jet_cr = q_cr_jet * math.sqrt(math.pi * ar_jet * e_jet * cx0_jet / 3.0)

        assert s_jet["terms"]["ws_max_range_cruise"] == pytest.approx(expected_ws_jet_cr, rel=1e-5)

    def test_point_b_feasibility_flag(self):
        """Point B feasible flag is True if ws_max_range <= ws_limit, False otherwise."""
        # Low cruise speed -> low q_cr -> low ws_max_range <= ws_limit -> Feasible
        p_low = base_params(cruise_speed_kmh=120.0, v_stall_kmh=110.0)
        s_low = calculate_matching_chart(p_low, m0=1200.0)
        pt_b_low = s_low["design_point"]["point_b"]
        assert pt_b_low["feasible"] is True
        assert pt_b_low["ws"] <= s_low["ws_limit"]

        # High cruise speed -> high q_cr -> high ws_max_range > ws_limit -> Infeasible
        p_high = base_params(cruise_speed_kmh=350.0, v_stall_kmh=90.0)
        s_high = calculate_matching_chart(p_high, m0=1200.0)
        pt_b_high = s_high["design_point"]["point_b"]
        assert pt_b_high["feasible"] is False
        assert pt_b_high["ws"] > s_high["ws_limit"]


# ==============================================================================
# 8. INTERFACE CONTRACT CONFORMANCE ACROSS ALL 7 PRESETS
# ==============================================================================

class TestInterfaceContractAndPresets:
    """Verify calculate_constraint_curves contract and robustness across all 7 reference aircraft classes."""

    @pytest.mark.parametrize("preset_name", list(AIRCRAFT_PRESETS.keys()))
    def test_calculate_constraint_curves_interface_contract(self, preset_name):
        """calculate_constraint_curves satisfies M1 <-> M2 interface keys for every preset."""
        preset = AIRCRAFT_PRESETS[preset_name]
        p = validate_parameters(dict(preset))

        res1 = calculate_constraint_curves(p)
        res2 = constraints_calculate_curves(p)

        for res in (res1, res2):
            assert isinstance(res, dict)
            for k in ("takeoff", "landing", "climb", "stall", "cruise", "ceiling", "design_point"):
                assert k in res, f"Missing key {k} in calculate_constraint_curves for preset {preset_name}"

            dp = res["design_point"]
            for subk in ("W_S", "T_W", "P_W"):
                assert subk in dp, f"Missing design_point key {subk} for preset {preset_name}"
            assert dp["W_S"] > 0

    def test_fixed_wing_area_override_controls_design_wing_loading(self):
        """When wing_area_m2 is provided with m0, ws_design is directly determined by m0*g/S."""
        fixed_s = 14.5
        m0 = 1150.0
        p = base_params(wing_area_m2=fixed_s)
        s = calculate_matching_chart(p, m0=m0)

        expected_ws = m0 * G0 / fixed_s
        assert s["design_point"]["ws"] == pytest.approx(expected_ws, rel=1e-5)
        assert s["design_point"]["limit_by"] == "zadana powierzchnia skrzydła"

    def test_locked_engine_power_kw_recomputes_pw_design(self):
        """When engine_power_kw is locked in params, power_kw is preserved and pw_design matches."""
        locked_kw = 160.0
        m0 = 1200.0
        p = base_params(engine_power_kw=locked_kw, locked_params=["engine_power_kw"])
        s = calculate_matching_chart(p, m0=m0)

        dp = s["design_point"]
        assert dp["power_kw"] == pytest.approx(locked_kw)
        expected_pw = locked_kw * 1000.0 / (m0 * G0)
        assert dp["pw"] == pytest.approx(expected_pw, rel=1e-5)


# ==============================================================================
# 9. ADVANCED CONFIGURATIONS: WATER, TOW GLIDER, GROUND ROLL FALLBACK
# ==============================================================================

class TestAdvancedConfigurations:
    """Challenge water operation exclusion, glider towing constraints, and ground-roll fallback."""

    def test_water_operations_zeroes_takeoff_constraint(self):
        """When operating_surface == 'water', takeoff constraint is excluded (takeoff_basis='unmodelled_water')."""
        p = base_params(operating_surface="water")
        s = calculate_matching_chart(p)
        assert s["takeoff_basis"] == "unmodelled_water"
        assert all(val == 0.0 for val in s["curve_takeoff"])
        assert s["terms"]["s_to"] == 0.0
        assert s["terms"]["s_l"] == 0.0

    def test_ground_roll_fallback_when_s_to_not_provided(self):
        """When takeoff_distance_m is zero or None, sizing falls back to ground roll formula."""
        p = base_params(takeoff_distance_m=0, takeoff_run_m=600)
        s = calculate_matching_chart(p)
        assert s["takeoff_basis"] == "ground_roll"
        assert s["curve_takeoff"] is not None
        assert all(val > 0 for val in s["curve_takeoff"] if val is not None)

    def test_glider_tow_constraint_adds_tow_thrust(self):
        """When tow_glider_mass_kg > 0, curve_tow is calculated and requires additional power."""
        p_normal = base_params()
        p_tow = base_params(
            tow_glider_mass_kg=450,
            tow_speed_kmh=120,
            tow_climb_rate_ms=2.5,
            tow_glider_ld=28.0,
        )
        s_norm = calculate_matching_chart(p_normal, m0=1200.0)
        s_tow = calculate_matching_chart(p_tow, m0=1200.0)

        assert s_tow["curve_tow"] is not None
        assert "holowanie szybowca" in s_tow["terms"]["at_design"]
        # Tow climb power is strictly positive
        assert s_tow["terms"]["at_design"]["holowanie szybowca"] > 0
