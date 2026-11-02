"""
tests/test_m2_adversarial_challenger.py
Empirical Adversarial Challenge Suite for BIPOL Milestone 2:
Features 7, 8, 9 (Fuselage, Landing Gear Kinematics & Ground Stability)
Features 10 (Propulsion Matching & Propeller Clearances)

Authored by m2_challenger_1 (EMPIRICAL CHALLENGER / Critic / Specialist).
Strictly derived from MEiL PW BIPOL I course materials:
- Wykład 3 (Handout 3): Fuselage Packaging, Cabin Ergonomics, ULD Cargo, Upsweep
- Wykład 4 (Handout 4): Landing Gear Sizing, 2D/3D Tipover & Turnover Angles, Tailstrike
- Wykład 15 (Handout 15): Touchdown Energy Balance, Shock Absorption, Braking & Moments
- Wykład 5 (Handout 5): Propulsion Integration, Propeller Sizing, Clearances & Tip Mach
- Wykład 7 (Handout 7): Static Gear Load Distribution & Ground Clearances
"""

import math
import random
import pytest

from calculations.landing_gear import (
    calculate_fuselage_and_gear,
    size_tire,
    ULD_CONTAINERS,
    TIRE_COEFFICIENTS,
    PILOT_VISION_ANGLES,
)
from calculations.empennage import (
    calculate_propulsion_clearance,
    size_propeller_diameter,
)


# ==============================================================================
# SUITE 1: TOUCHDOWN ENERGY BALANCE & SHOCK ABSORPTION (Wykład 4, 15)
# ==============================================================================

def test_adversarial_energy_conservation_fuzzing():
    """
    Fuzzing test over 200 randomized landing configurations:
    Verify exact mechanical work-energy conservation:
    E_kin + E_pot == Z_max * (i * h_a * eta_a + h_p * eta_p)
    """
    rng = random.Random(20261101)
    for idx in range(200):
        m0 = rng.uniform(300.0, 45000.0)
        ws = rng.uniform(300.0, 5500.0)
        w_drop = rng.uniform(1.8, 3.8)
        oleo_s = rng.uniform(0.10, 0.45)
        eta_a = rng.uniform(0.60, 0.90)
        tire_def = rng.uniform(0.03, 0.15)
        eta_p = rng.uniform(0.40, 0.55)
        i_strut = rng.uniform(0.85, 1.15)
        k_lift = rng.uniform(0.50, 0.75)
        mu = rng.uniform(0.20, 0.50)

        res = calculate_fuselage_and_gear({
            "m0": m0, "ws": ws, "w_drop_m_s": w_drop,
            "oleo_stroke_m": oleo_s, "oleo_fullness": eta_a,
            "tire_deflection_m": tire_def, "tire_fullness": eta_p,
            "strut_leverage": i_strut, "lift_ratio_touchdown": k_lift,
            "friction_coeff": mu
        })
        r = res["gear_reactions"]
        z_max = r["max_vertical_reaction_n"]
        e_total = r["total_energy_j"]

        delta_s_eff = (i_strut * oleo_s * eta_a) + (tire_def * eta_p)
        work_absorbed = z_max * delta_s_eff

        # Conservation holds within numerical rounding of reported z_max (1 decimal place)
        assert abs(work_absorbed - e_total) <= 0.20, (
            f"Energy conservation violation in case {idx}: work={work_absorbed}, E_tot={e_total}"
        )


def test_adversarial_load_factor_extreme_masses_and_wing_loadings():
    """
    Stress-test touchdown load factors across extreme masses (200 kg to 80,000 kg)
    and wing loadings (250 N/m² to 6,000 N/m²).
    Verify that well-sized oleo stroke keeps Delta n_L <= 3.5g and n_L <= 3.5g.
    """
    matrix = [
        # (m0, ws, oleo_stroke, expected_compliant)
        (250.0, 280.0, 0.15, True),     # Light sport aircraft
        (1150.0, 680.0, 0.20, True),    # Cessna 172 class
        (3500.0, 1400.0, 0.22, True),   # High-perf utility / aerobatic
        (8500.0, 2500.0, 0.28, True),   # Regional turboprop
        (65000.0, 5500.0, 0.36, True),  # Jet airliner
    ]
    for m0, ws, oleo_s, expected in matrix:
        res = calculate_fuselage_and_gear({
            "m0": m0, "ws": ws, "oleo_stroke_m": oleo_s
        })
        r = res["gear_reactions"]
        delta_nl = r["vertical_load_factor_increment"]
        nl = r["total_landing_load_factor"]
        compliant = r["cs23_load_factor_compliant"]

        assert compliant is expected
        assert delta_nl <= 3.50, f"Delta n_L exceeded 3.5g at m0={m0}: {delta_nl}"
        assert nl <= 3.50, f"Total n_L exceeded 3.5g at m0={m0}: {nl}"


def test_adversarial_inadequate_oleo_stroke_load_factor_rejection():
    """
    Adversarial under-stroke test:
    When oleo stroke is severely inadequate (e.g. 0.04m on a 1500kg aircraft),
    peak reaction force Z must surge, forcing Delta n_L > 3.5g and cs23_load_factor_compliant=False.
    """
    res = calculate_fuselage_and_gear({
        "m0": 1500.0, "ws": 800.0, "oleo_stroke_m": 0.04, "tire_deflection_m": 0.04
    })
    r = res["gear_reactions"]
    assert r["vertical_load_factor_increment"] > 4.5
    assert r["cs23_load_factor_compliant"] is False


def test_adversarial_braking_force_and_pitch_moment_equilibrium():
    """
    Verify ground braking equilibrium per Handout 15, p. 4-5:
    - Braking friction force X = mu * Z
    - Pitching moment M = Z * x_p + X * z_p
    - Horizontal load factor n_x = mu * Delta n_L
    """
    rng = random.Random(42)
    for _ in range(50):
        m0 = rng.uniform(800.0, 5000.0)
        mu = rng.uniform(0.15, 0.55)
        x_p = rng.uniform(0.15, 0.60)
        z_p = rng.uniform(0.60, 2.00)

        res = calculate_fuselage_and_gear({
            "m0": m0, "friction_coeff": mu,
            "main_gear_offset_m": x_p, "gear_height_m": z_p
        })
        r = res["gear_reactions"]
        z_max = r["max_vertical_reaction_n"]
        x_braking = r["braking_force_n"]
        m_pitch = r["pitch_moment_nm"]
        n_x = r["horizontal_load_factor"]
        delta_nl = r["vertical_load_factor_increment"]

        # X = mu * Z
        assert pytest.approx(x_braking, rel=0.01) == mu * z_max
        # M = Z * x_p + X * z_p
        expected_m = z_max * x_p + x_braking * z_p
        assert pytest.approx(m_pitch, rel=0.01) == expected_m
        # n_x = mu * Delta n_L
        assert pytest.approx(n_x, rel=0.01) == mu * delta_nl


def test_adversarial_touchdown_sink_rate_clamping():
    """
    Verify CS-23.723 touchdown sink rate clamping:
    w_drop = min(3.05, max(2.13, 0.51 * (W/S)^0.25))
    """
    # Low wing loading (ws = 100 N/m² -> 0.51 * 100^0.25 = 1.61 m/s -> clamped to 2.13 m/s)
    res_low = calculate_fuselage_and_gear({"ws": 100.0})
    assert res_low["gear_reactions"]["sink_rate_drop_m_s"] == 2.13

    # High wing loading (ws = 5000 N/m² -> 0.51 * 5000^0.25 = 4.29 m/s -> clamped to 3.05 m/s)
    res_high = calculate_fuselage_and_gear({"ws": 5000.0})
    assert res_high["gear_reactions"]["sink_rate_drop_m_s"] == 3.05


# ==============================================================================
# SUITE 2: GROUND STABILITY & TIPOVER TRIANGLE (Wykład 4, Handout 4)
# ==============================================================================

def test_adversarial_2d_tipover_angle_geometry():
    """
    Verify 2D transverse tipover formula: tan(psi) = z_cg / (T / 2).
    """
    res = calculate_fuselage_and_gear({
        "track_m": 2.40, "z_cg_m": 1.20, "wheelbase_m": 2.50
    })
    # tan(psi) = 1.20 / 1.20 = 1.0 -> psi = 45.0 deg
    assert res["tipover_angle_deg"] == 45.0
    assert res["tipover_compliant"] is True


def test_adversarial_3d_turnover_distance_and_angle_ordering():
    """
    Verify geometric invariant:
    Perpendicular turnover distance d_n = (T/2 * l_n) / sqrt(B^2 + (T/2)^2) is STRICTLY less than T/2.
    Therefore, the 3D turnover angle theta_3D = atan(z_cg / d_n) is STRICTLY GREATER than 2D angle psi_2D.
    """
    rng = random.Random(999)
    for _ in range(50):
        t = rng.uniform(1.5, 3.5)
        z_cg = rng.uniform(0.9, 1.8)
        # Ensure physical tricycle layout: nose < cg < main
        x_nose = rng.uniform(0.5, 1.2)
        l_n = rng.uniform(1.5, 3.0)
        cg_aft = x_nose + l_n
        wb = l_n + rng.uniform(0.3, 1.5)  # B > l_n

        res = calculate_fuselage_and_gear({
            "track_m": t, "z_cg_m": z_cg, "wheelbase_m": wb,
            "cg_aft_m": cg_aft, "x_nose_m": x_nose
        })
        psi_2d = res["tipover_angle_deg"]
        theta_3d = res["tipover_angle_3d_deg"]

        # Invariant: 3D turnover angle is always strictly greater than 2D tipover angle
        assert theta_3d > psi_2d, f"Ordering failed: theta_3d={theta_3d} <= psi_2d={psi_2d}"


def test_adversarial_3d_turnover_compliance_rejection_gap():
    """
    Defect reproduction test:
    When 2D tipover angle < 60 deg (e.g. 50.2 deg) but 3D turnover angle >= 60 deg (e.g. 62.2 deg),
    the configuration violates BIPOL Wykład 4 safety limits ('Mniej niż 60°').
    The system MUST reject this configuration (tipover_compliant = False).
    """
    res = calculate_fuselage_and_gear({
        "track_m": 2.0, "z_cg_m": 1.2, "wheelbase_m": 3.0,
        "cg_aft_m": 3.0, "x_nose_m": 1.0,
    })
    assert res["tipover_angle_deg"] < 60.0, "2D angle should be ~50.2 deg"
    assert res["tipover_angle_3d_deg"] >= 60.0, "3D turnover angle is 62.2 deg >= 60 deg"
    # Defect: currently evaluates to True because it only checks 2D angle
    assert res["tipover_compliant"] is False, "3D turnover angle >= 60 deg must be rejected!"


def test_adversarial_wheelbase_desynchronization_with_explicit_stations():
    """
    Defect reproduction test:
    When x_main_m=7.0 and x_nose_m=1.0 are provided on a 10m fuselage, actual wheelbase is 6.0m.
    `gear_dimensions['wheelbase_m']` and line 357 `d_tip` must use 6.0m, not default 0.38*10 = 3.8m.
    """
    res = calculate_fuselage_and_gear({
        "fuselage_length_m": 10.0,
        "x_nose_m": 1.0,
        "x_main_m": 7.0,
        "track_m": 2.4,
    })
    assert res["gear_dimensions"]["wheelbase_m"] == 6.0


def test_adversarial_zero_track_rejection():
    """
    Boundary test: Zero track width must not silently fall back to default track fraction.
    A track width of 0m must be rejected as an unphysical rollover hazard.
    """
    res = calculate_fuselage_and_gear({"track_m": 0.0, "z_cg_m": 1.2})
    assert res["tipover_compliant"] is False


def test_adversarial_main_gear_placement_13_to_15_deg_and_nose_load():
    """
    Verify main gear placement 13°-15° aft of CG and static nose gear load 8%-15% per Handout 4 & 7.
    - Angle ~14° -> main_gear_cg_compliant = True, nose load ~8-15%.
    - Angle < 12.5° or > 16.5° -> main_gear_cg_compliant = False.
    """
    z_cg = 1.20
    cg_aft = 4.00
    fus_len = 8.50
    x_nose = 1.00

    # 1. Compliant placement (14.0 deg)
    dx_compliant = z_cg * math.tan(math.radians(14.0))
    res_comp = calculate_fuselage_and_gear({
        "z_cg_m": z_cg, "cg_aft_m": cg_aft, "fuselage_length_m": fus_len,
        "x_nose_m": x_nose, "x_main_m": cg_aft + dx_compliant
    })
    assert res_comp["main_gear_cg_compliant"] is True
    assert 13.0 <= res_comp["gear_dimensions"]["main_gear_cg_angle_deg"] <= 15.0
    nose_load = res_comp["gear_reactions"]["nose_gear_static_load_pct"]
    assert 8.0 <= nose_load <= 15.0

    # 2. Too forward placement (7.0 deg -> nose load too small, risk of tipback)
    dx_fwd = z_cg * math.tan(math.radians(7.0))
    res_fwd = calculate_fuselage_and_gear({
        "z_cg_m": z_cg, "cg_aft_m": cg_aft, "fuselage_length_m": fus_len,
        "x_nose_m": x_nose, "x_main_m": cg_aft + dx_fwd
    })
    assert res_fwd["main_gear_cg_compliant"] is False
    assert res_fwd["gear_reactions"]["nose_gear_static_load_pct"] < 8.0

    # 3. Too aft placement (25.0 deg -> nose load too high > 15%)
    dx_aft = z_cg * math.tan(math.radians(25.0))
    res_aft = calculate_fuselage_and_gear({
        "z_cg_m": z_cg, "cg_aft_m": cg_aft, "fuselage_length_m": fus_len,
        "x_nose_m": x_nose, "x_main_m": cg_aft + dx_aft
    })
    assert res_aft["main_gear_cg_compliant"] is False
    assert res_aft["gear_reactions"]["nose_gear_static_load_pct"] > 15.0


def test_adversarial_tailstrike_rotation_clearance():
    """
    Verify tailstrike rotation angle theta_tail >= 10° per Handout 4, p. 7.
    """
    # Compliant: tail at 7.5m, main gear at 4.1m, z_tail = 0.85m -> 14.0 deg >= 10 deg
    res_ok = calculate_fuselage_and_gear({
        "x_main_m": 4.1, "x_tail_m": 7.5, "z_tail_m": 0.85
    })
    assert res_ok["tail_clearance_deg"] >= 10.0
    assert res_ok["tail_clearance_compliant"] is True

    # Non-compliant: tail too low (z_tail = 0.40m) -> 6.7 deg < 10 deg
    res_bad = calculate_fuselage_and_gear({
        "x_main_m": 4.1, "x_tail_m": 7.5, "z_tail_m": 0.40
    })
    assert res_bad["tail_clearance_deg"] < 10.0
    assert res_bad["tail_clearance_compliant"] is False


# ==============================================================================
# SUITE 3: PROPULSION MATCHING & PROPELLER CLEARANCES (Wykład 5)
# ==============================================================================

def test_adversarial_propeller_diameter_scaling_formula():
    """
    Verify propeller diameter sizing formula:
    D_p = 0.22 * sqrt(P_kW) * (2 / blade_count)^0.25
    """
    powers = [30.0, 75.0, 120.0, 300.0, 800.0]
    for p in powers:
        d2 = size_propeller_diameter(p, 2)
        d3 = size_propeller_diameter(p, 3)
        d4 = size_propeller_diameter(p, 4)

        expected_d2 = round(0.22 * math.sqrt(p), 3)
        expected_d3 = round(expected_d2 * ((2.0 / 3.0) ** 0.25), 3)
        expected_d4 = round(expected_d2 * ((2.0 / 4.0) ** 0.25), 3)

        assert abs(d2 - expected_d2) <= 0.002
        assert abs(d3 - expected_d3) <= 0.002
        assert abs(d4 - expected_d4) <= 0.002


def test_adversarial_propeller_diameter_blade_count_monotonicity():
    """
    Verify strict diameter reduction with increasing blade count:
    D_6 < D_5 < D_4 < D_3 < D_2.
    """
    for p in [50.0, 118.0, 250.0, 750.0]:
        diameters = [size_propeller_diameter(p, nb) for nb in [2, 3, 4, 5, 6]]
        for i in range(1, len(diameters)):
            assert diameters[i] < diameters[i - 1], (
                f"Monotonicity failed at power {p}: {diameters[i]} >= {diameters[i-1]}"
            )


def test_adversarial_multi_engine_power_partitioning():
    """
    Defect reproduction test:
    Twin piston aircraft with 2 engines (total 300 kW, n_engines=2) must size propeller
    based on per-engine power 150 kW (D_p ~ 2.69m for 2 blades), not all 300 kW (D_p ~ 3.81m).
    """
    res = calculate_propulsion_clearance({
        "engine_power_kw": 300.0,
        "n_engines": 2,
        "aircraft_type": "twin_piston",
        "blade_count": 2,
        "prop_rpm": 1200,  # Keep this sizing test below the helical tip-Mach limit.
    })
    expected_dp_150kw = round(0.22 * math.sqrt(150.0), 3)
    assert pytest.approx(res["propeller_diameter_m"], abs=0.05) == expected_dp_150kw


def test_adversarial_propeller_ground_clearance_boundaries():
    """
    Verify propeller ground clearances under compressed deflection:
    - Tricycle gear: >= 230 mm (0.230 m)
    - Taildragger gear: >= 180 mm (0.180 m)
    """
    # Tricycle passing at 240 mm
    res_tri_pass = calculate_propulsion_clearance({
        "engine_power_kw": 120.0, "gear_type": "tricycle",
        "propeller_diameter_m": 2.00, "prop_shaft_height_m": 1.32,
        "gear_compressed_deflection_m": 0.08
    })
    # Clearance: 1.32 - 1.00 - 0.08 = 0.240 m >= 0.230 m
    assert res_tri_pass["ground_clearance_req_m"] == 0.230
    assert res_tri_pass["ground_clearance_m"] == 0.240
    assert res_tri_pass["ground_clearance_passed"] is True

    # Tricycle failing at 210 mm
    res_tri_fail = calculate_propulsion_clearance({
        "engine_power_kw": 120.0, "gear_type": "tricycle",
        "propeller_diameter_m": 2.00, "prop_shaft_height_m": 1.29,
        "gear_compressed_deflection_m": 0.08
    })
    # Clearance: 1.29 - 1.00 - 0.08 = 0.210 m < 0.230 m
    assert res_tri_fail["ground_clearance_passed"] is False

    # Taildragger passing with the same 210 mm (req is only 180 mm)
    res_td_pass = calculate_propulsion_clearance({
        "engine_power_kw": 120.0, "gear_type": "taildragger",
        "propeller_diameter_m": 2.00, "prop_shaft_height_m": 1.29,
        "gear_compressed_deflection_m": 0.08
    })
    assert res_td_pass["ground_clearance_req_m"] == 0.180
    assert res_td_pass["ground_clearance_m"] == 0.210
    assert res_td_pass["ground_clearance_passed"] is True


def test_adversarial_helical_tip_mach_envelope():
    """
    Verify helical tip Mach limit M_tip <= 0.85 across speeds and altitudes.
    V_tip,helical = sqrt(V_cr^2 + (pi * n * D_p)^2), M_tip = V_tip,helical / a(h).
    """
    # Safe GA condition: 200 km/h, 2400 RPM, D_p = 1.90m at 1000m -> M_tip ~ 0.73 <= 0.85
    res_safe = calculate_propulsion_clearance({
        "engine_power_kw": 120.0, "prop_rpm": 2400.0, "propeller_diameter_m": 1.90,
        "cruise_speed_kmh": 200.0, "altitude_m": 1000.0
    })
    assert res_safe["tip_mach"] <= 0.85
    assert res_safe["tip_mach_passed"] is True

    # Overspeed / high altitude condition: 450 km/h, 2800 RPM, D_p = 2.20m at 8000m
    # Speed of sound drops with altitude -> Mach rises significantly -> M_tip > 0.85
    res_transonic = calculate_propulsion_clearance({
        "engine_power_kw": 300.0, "prop_rpm": 2800.0, "propeller_diameter_m": 2.20,
        "cruise_speed_kmh": 450.0, "altitude_m": 8000.0
    })
    assert res_transonic["tip_mach"] > 0.85
    assert res_transonic["tip_mach_passed"] is False


def test_adversarial_fuselage_clearance_rule():
    """
    Verify propeller-to-fuselage clearance rule:
    Clearance >= max(0.025m, 0.10 * D_p).
    """
    # D_p = 2.0m -> req clearance = max(0.025, 0.20) = 0.20m
    # Twin engine nacelle at y = 1.80m, fuselage radius = 0.70m -> clearance = 1.80 - 0.70 - 1.00 = 0.10m < 0.20m -> fail!
    res_tight = calculate_propulsion_clearance({
        "engine_power_kw": 150.0, "propeller_diameter_m": 2.0,
        "prop_axis_lateral_y_m": 1.80, "fuselage_radius_at_prop_m": 0.70
    })
    assert res_tight["fuselage_clearance_m"] == 0.100
    assert res_tight["fuselage_clearance_req_m"] == 0.200
    assert res_tight["fuselage_clearance_passed"] is False

    # Nacelle moved outward to y = 2.00m -> clearance = 2.00 - 0.70 - 1.00 = 0.30m >= 0.20m -> pass!
    res_wide = calculate_propulsion_clearance({
        "engine_power_kw": 150.0, "propeller_diameter_m": 2.0,
        "prop_axis_lateral_y_m": 2.00, "fuselage_radius_at_prop_m": 0.70
    })
    assert res_wide["fuselage_clearance_m"] == 0.300
    assert res_wide["fuselage_clearance_passed"] is True
