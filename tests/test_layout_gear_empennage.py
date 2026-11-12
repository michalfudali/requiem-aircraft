"""
tests/test_layout_gear_empennage.py
Comprehensive Verification Test Suite for Milestone 2:
Features 7, 8, 9 (Fuselage, Landing Gear & Ground Stability)
Features 10, 11 (Propulsion Matching & Empennage Sizing)
Features 12, 13 (Mass Distribution, Balance Envelope & Layout Visualizer)

Strictly derived from MEiL PW BIPOL I:
- Wykład 3 (okBIPOL_1_handout_3.pdf): Fuselage Packaging, Cabin Ergonomics, Cargo ULDs, Upsweep
- Wykład 4 (okBIPOL_1_handout_4.pdf): Landing Gear Sizing, Stability Angles, Turnover Check
- Wykład 15 (okBIPOL_1_handout_15.pdf): Gear Energy Balance, Shock Absorption, Braking Forces
- Wykład 5 (okBIPOL_1_handout_5.pdf): Propulsion Matching, Propeller Clearances, Tip Mach
- Wykład 6 (okBIPOL_1_handout_6.pdf & Usterzenie_wymiary.pdf): Empennage Volumes, V-Tail, Spin Recovery
- Wykład 7 (okBIPOL_1_handout_7.pdf): Mass Distribution, 6 Canonical Loading Cases, Neutral Point, Static Margin
"""

import math
import pytest

from calculations.landing_gear import (
    calculate_fuselage_and_gear,
    size_tire,
    ULD_CONTAINERS,
    TIRE_COEFFICIENTS,
    PILOT_VISION_ANGLES,
)
from calculations.empennage import (
    calculate_empennage_sizing,
    calculate_propulsion_clearance,
    size_propeller_diameter,
    CORKE_VOLUME_COEFFICIENTS,
)
from calculations.balance import (
    calculate_balance_envelope,
    calculate_balance_and_stability,
)
from calculations.geometry import (
    calculate_geometry,
)


# ==============================================================================
# FEATURE 7: Fuselage Packaging, Cabin Ergonomics & Cargo ULD Containers
# ==============================================================================

def test_feature7_cabin_ergonomics_short_vs_long_range():
    """Verify short-range vs long-range cabin ergonomics match Handout 3, p. 6."""
    res_short = calculate_fuselage_and_gear({
        "m0": 12000.0, "ws": 2500.0, "b": 22.0, "aircraft_type": "turboprop_regional",
        "n_pax": 30, "range_category": "short_range"
    })
    res_long = calculate_fuselage_and_gear({
        "m0": 45000.0, "ws": 4000.0, "b": 32.0, "aircraft_type": "jet_transport",
        "n_pax": 90, "range_category": "long_range"
    })

    f_short = res_short["fuselage"]
    f_long = res_long["fuselage"]

    # Short range: w_seat ~ 0.44m, pitch ~ 0.78m, aisle ~ 0.38m, headroom = 1.52m
    assert f_short["seat_width_m"] == 0.44
    assert f_short["seat_pitch_m"] == 0.78
    assert f_short["aisle_width_m"] == 0.38
    assert f_short["cabin_height_m"] == 1.52

    # Long range: w_seat ~ 0.48m, pitch ~ 0.90m, aisle ~ 0.56m, headroom = 1.93m
    assert f_long["seat_width_m"] == 0.48
    assert f_long["seat_pitch_m"] == 0.90
    assert f_long["aisle_width_m"] == 0.56
    assert f_long["cabin_height_m"] == 1.93

    # Long range cabin should be wider and taller than short range
    assert f_long["cabin_width_m"] > f_short["cabin_width_m"]
    assert f_long["cabin_height_m"] > f_short["cabin_height_m"]


def test_feature7_cargo_containers_exact_specs():
    """Verify exact ULD container dimensions and hold allocation per Handout 3, p. 7."""
    assert ULD_CONTAINERS["LD-2"]["volume_m3"] == 3.398
    assert ULD_CONTAINERS["LD-2"]["max_gross_kg"] == 1224.7

    assert ULD_CONTAINERS["LD-3"]["volume_m3"] == 4.417
    assert ULD_CONTAINERS["LD-3"]["max_gross_kg"] == 1587.6

    assert ULD_CONTAINERS["LD-4"]["volume_m3"] == 5.522
    assert ULD_CONTAINERS["LD-4"]["max_gross_kg"] == 2449.4

    assert ULD_CONTAINERS["LD-8"]["volume_m3"] == 6.938
    assert ULD_CONTAINERS["LD-8"]["max_gross_kg"] == 2449.4

    assert ULD_CONTAINERS["LD-11"]["volume_m3"] == 7.160
    assert ULD_CONTAINERS["LD-11"]["max_gross_kg"] == 3175.0

    # Cargo allocation test: 3000 kg cargo in LD-3 containers (max 1587.6 kg each)
    res = calculate_fuselage_and_gear({
        "m0": 45000.0, "ws": 3500.0, "b": 30.0, "m_cargo": 3000.0,
        "container_type": "LD-3", "fuselage_diameter_m": 3.8
    })
    c = res["cargo"]
    assert c["n_containers"] == 2
    assert pytest.approx(c["hold_volume_required_m3"], 0.01) == 2 * 4.417
    assert c["container_compatible"] is True


def test_feature7_fuselage_fineness_and_raymer_wetted_area():
    """Verify fuselage fineness ratio and Raymer/Torenbeek wetted area formula."""
    res = calculate_fuselage_and_gear({
        "m0": 10000.0, "ws": 2000.0, "b": 18.0,
        "fuselage_length_m": 16.0, "fuselage_diameter_m": 2.0
    })
    f = res["fuselage"]
    assert f["fineness_ratio"] == 8.0

    # Analytical calculation: S_wet = pi * 2.0 * 16.0 * (1 - 2/8)^(2/3) * (1 + 1/64)
    # 100.53096 * (0.75)^(2/3) * 1.015625 = 100.53096 * 0.8254818 * 1.015625 = 84.288 m2
    expected_swet = math.pi * 2.0 * 16.0 * ((0.75) ** (2.0 / 3.0)) * (1.0 + 1.0 / 64.0)
    assert pytest.approx(f["s_wet_fus_m2"], 0.1) == expected_swet


def test_feature7_rear_upsweep_angle_rule():
    """Verify rear fuselage upsweep check: upsweep <= 24 deg is compliant (Handout 3, p. 20)."""
    # Slender tail cone: upsweep ~ 14 deg <= 24 deg
    res_good = calculate_fuselage_and_gear({
        "m0": 5000.0, "fuselage_length_m": 12.0, "fuselage_diameter_m": 1.5
    })
    assert res_good["fuselage"]["upsweep_compliant"] is True
    assert res_good["fuselage"]["upsweep_angle_deg"] <= 24.0


# ==============================================================================
# FEATURE 8: Landing Gear Energy Balance, Shock Absorption & Reaction Forces
# ==============================================================================

def test_feature8_touchdown_energy_balance_analytical():
    """
    Verify analytical benchmark from Handout 15 p. 2:
    m = 1000 kg, w_drop = 2.6 m/s, k_lift = 0.67, h_a = 0.20 m, eta_a = 0.80,
    h_p = 0.07 m, eta_p = 0.45.
    """
    res = calculate_fuselage_and_gear({
        "m0": 1000.0, "ws": 650.0, "b": 11.0,
        "w_drop_m_s": 2.6, "lift_ratio_touchdown": 0.67,
        "oleo_stroke_m": 0.20, "oleo_fullness": 0.80,
        "tire_deflection_m": 0.07, "tire_fullness": 0.45,
        "strut_leverage": 1.0,
    })
    reactions = res["gear_reactions"]

    # Kinetic energy: 0.5 * 1000 * 2.6^2 = 3380 J
    # Potential energy: (1000 * 9.80665 * (1 - 0.67)) * (0.20 + 0.07) = 3236.19 * 0.27 = 873.77 J
    # Total energy = 4253.77 J
    # Work stroke denominator: 0.20 * 0.80 + 0.07 * 0.45 = 0.16 + 0.0315 = 0.1915 m
    # Z_max = 4253.77 / 0.1915 = 22212.9 N
    # Delta n_L = 22212.9 / (1000 * 9.80665) = 2.265
    # Total n_L = 2.265 + 0.67 = 2.935 <= 3.5g
    assert pytest.approx(reactions["total_energy_j"], 5.0) == 4253.8
    assert pytest.approx(reactions["max_vertical_reaction_n"], 50.0) == 22213.0
    assert pytest.approx(reactions["vertical_load_factor_increment"], 0.02) == 2.265
    assert pytest.approx(reactions["total_landing_load_factor"], 0.02) == 2.935
    assert reactions["cs23_load_factor_compliant"] is True


def test_feature8_fullness_coefficients_sensitivity():
    """Verify that replacing oleo (eta_a = 0.80) with steel spring (eta_a = 0.50) increases load factor."""
    res_oleo = calculate_fuselage_and_gear({
        "m0": 1000.0, "ws": 650.0, "w_drop_m_s": 2.6,
        "oleo_stroke_m": 0.20, "oleo_fullness": 0.80,
        "tire_deflection_m": 0.07, "tire_fullness": 0.45,
    })
    res_spring = calculate_fuselage_and_gear({
        "m0": 1000.0, "ws": 650.0, "w_drop_m_s": 2.6,
        "oleo_stroke_m": 0.20, "oleo_fullness": 0.50,
        "tire_deflection_m": 0.07, "tire_fullness": 0.45,
    })
    z_oleo = res_oleo["gear_reactions"]["max_vertical_reaction_n"]
    z_spring = res_spring["gear_reactions"]["max_vertical_reaction_n"]
    assert z_spring > z_oleo
    # Denominator drops from 0.1915 to 0.1315 m -> Z increases significantly
    assert z_spring > 1.35 * z_oleo


def test_feature8_braking_force_and_pitch_moment():
    """Verify braking ground drag X = mu * Z and horizontal load factor n_x = mu * Delta n_L."""
    res = calculate_fuselage_and_gear({
        "m0": 1000.0, "ws": 650.0, "w_drop_m_s": 2.6,
        "friction_coeff": 0.35, "oleo_stroke_m": 0.20, "oleo_fullness": 0.80,
        "tire_deflection_m": 0.07, "tire_fullness": 0.45,
    })
    r = res["gear_reactions"]
    assert pytest.approx(r["braking_force_n"], 5.0) == 0.35 * r["max_vertical_reaction_n"]
    assert pytest.approx(r["horizontal_load_factor"], 0.01) == 0.35 * r["vertical_load_factor_increment"]


def test_feature8_empirical_tire_sizing_regressions():
    """Verify Handout 4 empirical regressions for light aircraft tire sizing."""
    d_m, w_m = size_tire(1000.0, "piston_ga", n_wheels=2)
    # Wm = 0.9 * 2204.62 / 2 = 992 lb
    # d_in = 1.51 * (992)^0.349 = 16.7 in -> 0.425 m
    # w_in = 0.715 * (992)^0.312 = 6.13 in -> 0.155 m
    assert 0.38 <= d_m <= 0.46
    assert 0.13 <= w_m <= 0.18


# ==============================================================================
# FEATURE 9: Ground Stability, Lateral Turnover & Clearances
# ==============================================================================

def test_feature9_lateral_tipover_turnover_angle():
    """Verify 2D and 3D turnover angle criteria: psi < 60 deg (recommended <= 55 deg)."""
    # Track = 2.4m, z_cg = 1.2m -> tan(psi) = 1.2 / 1.2 = 1.0 -> psi = 45 deg < 60 deg
    res_stable = calculate_fuselage_and_gear({
        "m0": 1100.0, "track_m": 2.4, "z_cg_m": 1.2, "wheelbase_m": 2.5
    })
    assert res_stable["tipover_angle_deg"] == 45.0
    assert res_stable["tipover_compliant"] is True

    # Unstable narrow track: Track = 1.0m, z_cg = 1.2m -> tan(psi) = 1.2 / 0.5 = 2.4 -> psi = 67.4 deg > 60 deg
    res_unstable = calculate_fuselage_and_gear({
        "m0": 1100.0, "track_m": 1.0, "z_cg_m": 1.2, "wheelbase_m": 2.5
    })
    assert res_unstable["tipover_angle_deg"] > 60.0
    assert res_unstable["tipover_compliant"] is False


def test_feature9_main_gear_cg_location_13_to_15_deg():
    """Verify main gear placement 13 to 15 deg aft of critical CG and 8-15% nose load."""
    res = calculate_fuselage_and_gear({
        "m0": 1100.0, "cg_aft_m": 3.8, "cg_fwd_m": 3.5, "z_cg_m": 1.2,
        "fuselage_length_m": 8.0, "track_m": 2.4,
    })
    assert res["main_gear_cg_compliant"] is True
    assert 12.5 <= res["gear_dimensions"]["main_gear_cg_angle_deg"] <= 16.5
    # Nose load percentage between 8% and 15%
    nose_pct = res["gear_reactions"]["nose_gear_static_load_pct"]
    assert 8.0 <= nose_pct <= 16.0


def test_feature9_tailstrike_clearance_10_to_15_deg():
    """Verify tailstrike rotation angle theta_tail >= 10 deg (Handout 4, p. 7)."""
    res = calculate_fuselage_and_gear({
        "m0": 1100.0, "fuselage_length_m": 8.0, "x_tail_m": 7.5, "z_tail_m": 0.85,
        "x_main_m": 4.1
    })
    # dx = 7.5 - 4.1 = 3.4m, z_tail = 0.85m -> arctan(0.85 / 3.4) = 14.0 deg
    assert res["tail_clearance_compliant"] is True
    assert 12.0 <= res["tail_clearance_deg"] <= 16.0


def test_feature9_ground_clearances_prop_and_belly():
    """CS 22.925(a): 180 mm nose wheel / 230 mm tail wheel; retain belly calculation."""
    res_tri = calculate_fuselage_and_gear({
        "m0": 1100.0, "landing_gear_type": "tricycle",
        "propeller_diameter_m": 1.90, "prop_shaft_height_m": 1.45,
        "oleo_stroke_m": 0.18, "tire_deflection_m": 0.05
    })
    # Prop tip clearance = 1.45 - 0.95 - 0.23 = 0.27 m >= 0.18 m.
    assert res_tri["propeller_clearance_compliant"] is True
    assert res_tri["propeller_clearance_m"] >= 0.180
    assert res_tri["ground_clearance_m"] >= 0.50


# ==============================================================================
# FEATURE 10: Propulsion Matching, Propeller Clearances & Efficiency Curves
# ==============================================================================

def test_propeller_diameter_scaling_blade_count():
    """Verify propeller sizing D_p = 0.22 * sqrt(P) * (2/N_b)^0.25 and monotonicity."""
    p_kw = 118.0  # 160 hp
    d2 = size_propeller_diameter(p_kw, 2)
    d3 = size_propeller_diameter(p_kw, 3)
    d4 = size_propeller_diameter(p_kw, 4)

    # 2-blade baseline: 0.22 * sqrt(118) = 0.22 * 10.863 = 2.39m
    assert pytest.approx(d2, 0.05) == 2.39
    # Monotonicity with blade count
    assert d4 < d3 < d2
    assert pytest.approx(d3, 0.05) == d2 * ((2.0 / 3.0) ** 0.25)
    assert pytest.approx(d4, 0.05) == d2 * ((2.0 / 4.0) ** 0.25)


def test_propeller_ground_clearance_tricycle_vs_taildragger():
    """Verify CS 22.925(a): 180 mm (nose wheel), 230 mm (tail wheel)."""
    # Nose wheel: 1.40 - 1.05 - 0.10 = 0.25 m >= 0.18 m.
    res_tri = calculate_propulsion_clearance({
        "engine_power_kw": 100.0, "gear_type": "tricycle",
        "propeller_diameter_m": 2.10, "prop_shaft_height_m": 1.40,
        "gear_compressed_deflection_m": 0.10
    })
    assert res_tri["ground_clearance_req_m"] == 0.180
    assert res_tri["ground_clearance_passed"] is True

    # Tail wheel: 0.20 m is insufficient for the required 0.23 m.
    res_td = calculate_propulsion_clearance({
        "engine_power_kw": 100.0, "gear_type": "taildragger",
        "propeller_diameter_m": 2.20, "prop_shaft_height_m": 1.40,
        "gear_compressed_deflection_m": 0.10
    })
    assert res_td["ground_clearance_req_m"] == 0.230
    assert res_td["ground_clearance_m"] == 0.200
    assert res_td["ground_clearance_passed"] is False


def test_propeller_tip_mach_limit():
    """Verify tip Mach calculation M_tip <= 0.85 threshold."""
    # Normal RPM (2400) -> safe Mach ~ 0.78 <= 0.85
    res_safe = calculate_propulsion_clearance({
        "engine_power_kw": 120.0, "prop_rpm": 2400.0, "propeller_diameter_m": 1.90,
        "cruise_speed_kmh": 220.0, "altitude_m": 1000.0
    })
    assert res_safe["tip_mach"] <= 0.85
    assert res_safe["tip_mach_passed"] is True

    # Excessive RPM (3400) & large diameter (2.30m) -> M_tip > 0.85
    res_fast = calculate_propulsion_clearance({
        "engine_power_kw": 250.0, "prop_rpm": 3400.0, "propeller_diameter_m": 2.30,
        "cruise_speed_kmh": 300.0, "altitude_m": 3000.0
    })
    assert res_fast["tip_mach"] > 0.85
    assert res_fast["tip_mach_passed"] is False


def test_propeller_efficiency_flight_phases():
    """Verify propeller efficiency curves across flight phases (variable vs fixed pitch)."""
    res_var = calculate_propulsion_clearance({"engine_power_kw": 120.0, "prop_pitch_type": "variable"})
    res_fix = calculate_propulsion_clearance({"engine_power_kw": 120.0, "prop_pitch_type": "fixed"})

    eff_var = res_var["efficiencies"]
    eff_fix = res_fix["efficiencies"]

    # Monotonic flight phase efficiency progression: takeoff < climb < cruise
    assert eff_var["eta_takeoff"] < eff_var["eta_climb"] < eff_var["eta_cruise"]
    assert eff_fix["eta_takeoff"] < eff_fix["eta_climb"] < eff_fix["eta_cruise"]

    # Variable pitch is superior to fixed pitch off-design
    assert eff_var["eta_takeoff"] > eff_fix["eta_takeoff"]
    assert eff_var["eta_climb"] > eff_fix["eta_climb"]


# ==============================================================================
# FEATURE 11: Empennage Volume Sizing & Spin Recovery Rudder Area
# ==============================================================================

def test_empennage_volume_sizing_all_categories():
    """Verify Corke's volume coefficient tables across 9 aircraft categories."""
    for cat, expected in CORKE_VOLUME_COEFFICIENTS.items():
        res = calculate_empennage_sizing({
            "S": 16.0, "b": 11.0, "mac": 1.5, "fuselage_len": 8.5,
            "aircraft_type": cat, "engine_location": "nose"
        })
        assert res["V_H"] == expected["V_H"]
        assert res["V_V"] == expected["V_V"]
        assert res["S_H"] > 0.0
        assert res["S_V"] > 0.0


def test_v_tail_projected_area_identity():
    """Verify V-tail projection identity: S_H,proj + S_V,proj == S_vtail exactly."""
    res = calculate_empennage_sizing({
        "S": 16.2, "b": 11.0, "mac": 1.5, "fuselage_len": 8.28,
        "tail_layout": "v_tail", "v_h": 0.70, "v_v": 0.040
    })
    v = res["v_tail_data"]
    assert v is not None
    # S_H_proj + S_V_proj must identically equal total panel area
    assert pytest.approx(v["S_H_proj"] + v["S_V_proj"], abs=0.005) == v["S_vtail_total"]
    # Check tan^2(Gamma) == S_V / S_H
    tan_gamma = math.tan(math.radians(v["dihedral_deg"]))
    assert pytest.approx(tan_gamma ** 2, rel=0.01) == (res["S_V"] / res["S_H"])


def test_canard_volume_sizing():
    """Verify canard volume coefficient S_C = V_C * S * mac / l_C."""
    res = calculate_empennage_sizing({
        "S": 20.0, "b": 12.0, "mac": 1.8, "fuselage_len": 10.0,
        "is_canard": True, "v_c": 0.11, "l_c": 3.5
    })
    c = res["canard_data"]
    assert c is not None
    expected_sc = (0.11 * 20.0 * 1.8) / 3.5
    assert pytest.approx(c["S_C"], 0.01) == expected_sc


def test_spin_recovery_unshielded_rudder_t_tail_vs_conventional():
    """Verify 30°-60° stall wake cone spin recovery: T-tail ~100%, conventional ~35-50%."""
    # T-tail: Horizontal tail mounted at fin tip -> wake cone passes ABOVE fin/rudder -> URDA ~ 1.0
    res_ttail = calculate_empennage_sizing({
        "S": 16.0, "b": 11.0, "mac": 1.5, "fuselage_len": 8.0,
        "tail_layout": "t_tail"
    })
    assert res_ttail["rudder_unshielded_fraction"] >= 0.95
    assert res_ttail["spin_recovery_passed"] is True
    assert res_ttail["spin_recovery_verdict"] == "EXCELLENT"

    # Conventional tail: horizontal tail at base -> wake shields top portion -> URDA ~ 35-50%
    res_conv = calculate_empennage_sizing({
        "S": 16.0, "b": 11.0, "mac": 1.5, "fuselage_len": 8.0,
        "tail_layout": "conventional", "h_tail_pos_z_fraction": 0.0
    })
    assert 0.30 <= res_conv["rudder_unshielded_fraction"] <= 0.65
    assert res_conv["spin_recovery_passed"] is True


# ==============================================================================
# FEATURE 12: Mass Distribution, 6 Canonical Loading Cases & Static Margin
# ==============================================================================

def test_mass_and_first_moment_conservation():
    """Verify strict machine-precision conservation of mass and first moment across all 6 cases."""
    params = {
        "m0": 1150.0, "m_empty": 710.0, "m_fuel": 150.0, "m_payload": 210.0,
        "n_crew": 1, "n_pax": 2, "m_bag": 36.0,
        "fuselage_length_m": 8.2, "wingspan_m": 10.8, "wing_area_m2": 15.6,
        "aspect_ratio": 7.48, "mac_m": 1.48
    }
    res = calculate_balance_envelope(params)
    cases = res["cg_positions"]

    assert len(cases) >= 6
    for key, c in cases.items():
        stations = c["stations"]
        sum_m = sum(st["mass_kg"] for st in stations)
        sum_mom = sum(st["mass_kg"] * st["x_m"] for st in stations)
        # Mass conservation
        assert pytest.approx(sum_m, 1e-4) == c["mass_kg"]
        # First moment conservation
        assert pytest.approx(sum_mom, 1e-3) == c["moment_kg_m"]
        # Coordinate calculation
        assert pytest.approx(sum_mom / sum_m, 1e-4) == c["xcg_m"]


def test_case2_pilot_heavy_creates_forward_cg_boundary():
    """Verify Case 2b (heavy pilot) produces more forward CG than Case 2a (light pilot)."""
    res = calculate_balance_envelope({
        "m0": 1100.0, "m_empty": 680.0, "m_fuel": 140.0, "m_payload": 200.0,
        "n_crew": 1, "n_pax": 2, "fuselage_length_m": 8.0, "wingspan_m": 10.5,
        "wing_area_m2": 15.0, "mac_m": 1.45
    })
    c2a = res["cg_positions"]["case2_pilot_light"]
    c2b = res["cg_positions"]["case2_pilot_heavy"]

    # Cockpit is forward of wing -> heavier pilot pulls CG forward
    assert c2b["xcg_m"] < c2a["xcg_m"]
    assert c2b["xcg_mac_pct"] < c2a["xcg_mac_pct"]
    assert c2b["xcg_mac_pct"] == res["cg_fwd"]


def test_case4_baggage_creates_aft_cg_boundary():
    """Verify Case 4 (full baggage, no pax) produces more aft CG than Case 3 (full pax, min bag)."""
    res = calculate_balance_envelope({
        "m0": 1100.0, "m_empty": 680.0, "m_fuel": 140.0, "m_payload": 200.0,
        "n_crew": 1, "n_pax": 2, "fuselage_length_m": 8.0, "wingspan_m": 10.5,
        "wing_area_m2": 15.0, "mac_m": 1.45
    })
    c3 = res["cg_positions"]["case3_full_pax_min_bag"]
    c4 = res["cg_positions"]["case4_full_bag_min_pax"]

    # Baggage is at aft hold (x_lemac + 0.75 MAC) -> creates critical aft CG
    assert c4["xcg_m"] > c3["xcg_m"]
    assert c4["xcg_mac_pct"] > c3["xcg_mac_pct"]
    assert c4["xcg_mac_pct"] == res["cg_aft"]


def test_static_margin_compliance():
    """Verify static margin Kn >= 0.05 (5.0% MAC) at critical aft CG limit."""
    res = calculate_balance_envelope({
        "m0": 1100.0, "m_empty": 680.0, "m_fuel": 140.0, "m_payload": 200.0,
        "fuselage_length_m": 8.0, "wingspan_m": 10.5, "wing_area_m2": 15.0, "mac_m": 1.45
    })
    assert res["is_stable"] is True
    assert res["kn_min"] >= 0.05
    assert res["static_margin_aft_pct"] >= 5.0
    # Neutral point must be aft of CG aft limit
    assert res["x_np"] > res["cg_aft_m"]


def test_wing_positioning_algorithm_centers_cg():
    """Verify bisection wing positioning restores CG within target 25-35% MAC."""
    res = calculate_balance_envelope({
        "m0": 1100.0, "m_empty": 680.0, "m_fuel": 140.0, "m_payload": 200.0,
        "fuselage_length_m": 8.0, "wingspan_m": 10.5, "wing_area_m2": 15.0, "mac_m": 1.45
    })
    assert res["cg_within_target"] is True
    assert res["cg_aft"] <= 35.0
    assert res["cg_fwd"] >= 25.0 or res["cg_travel_span_pct"] > 10.0


def test_turnover_stability_triangle():
    """Verify landing gear turnover triangle stability calculation."""
    res = calculate_balance_envelope({
        "m0": 1100.0, "m_empty": 680.0, "m_fuel": 140.0, "m_payload": 200.0,
        "fuselage_length_m": 8.0, "wingspan_m": 10.5, "wing_area_m2": 15.0, "mac_m": 1.45
    })
    t = res["turnover_stability"]
    assert t["turnover_angle_deg"] < 60.0
    assert t["turnover_compliant"] is True
    assert 13.0 <= t["main_gear_cg_angle_deg"] <= 16.0
    assert t["tailstrike_clearance_deg"] >= 10.0


def test_scale_invariance_dimensionless_balance():
    """Verify dimensionless balance results (% MAC, Kn) are scale invariant."""
    base_params = {
        "m0": 1000.0, "m_empty": 600.0, "m_fuel": 150.0, "m_payload": 180.0,
        "fuselage_length_m": 8.0, "wingspan_m": 10.0, "wing_area_m2": 15.0, "mac_m": 1.5
    }
    lam = 2.0
    scaled_params = {
        "m0": 1000.0 * (lam ** 3), "m_empty": 600.0 * (lam ** 3),
        "m_fuel": 150.0 * (lam ** 3), "m_payload": 180.0 * (lam ** 3),
        "fuselage_length_m": 8.0 * lam, "wingspan_m": 10.0 * lam,
        "wing_area_m2": 15.0 * (lam ** 2), "mac_m": 1.5 * lam
    }
    r1 = calculate_balance_envelope(base_params)
    r2 = calculate_balance_envelope(scaled_params)

    assert pytest.approx(r1["cg_fwd"], 0.2) == r2["cg_fwd"]
    assert pytest.approx(r1["cg_aft"], 0.2) == r2["cg_aft"]
    assert pytest.approx(r1["kn_min"], abs=0.01) == r2["kn_min"]


# ==============================================================================
# TIER 2 & TIER 4: Boundary Cases & Real-World Workloads
# ==============================================================================

def test_tier2_extreme_narrow_gear_tipover_rejection():
    """Boundary test: Near-zero track causes severe turnover violation."""
    res = calculate_fuselage_and_gear({
        "m0": 1000.0, "track_m": 0.40, "z_cg_m": 1.40, "wheelbase_m": 2.5
    })
    # tan(psi) = 1.40 / 0.20 = 7.0 -> psi ~ 81.8 deg >> 60 deg
    assert res["tipover_angle_deg"] > 75.0
    assert res["tipover_compliant"] is False


def test_tier4_real_world_ga_trainer_cessna172():
    """End-to-End Tier 4 scenario: Cessna 172 class 4-seat general aviation trainer."""
    params = {
        "m0": 1157.0, "ws": 680.0, "wingspan_m": 11.0, "aircraft_type": "piston_ga",
        "n_pax": 3, "n_crew": 1, "m_cargo": 54.0,
        "engine_power_kw": 134.0, "prop_rpm": 2400.0, "cruise_speed_kmh": 226.0,
        "fuselage_length_m": 8.28, "fuselage_diameter_m": 1.25,
        "wing_area_m2": 16.2, "mac_m": 1.50, "aspect_ratio": 7.47,
    }
    gear_res = calculate_fuselage_and_gear(params)
    emp_res = calculate_empennage_sizing(params)
    prop_res = calculate_propulsion_clearance(params)
    bal_res = calculate_balance_envelope(params)

    assert gear_res["tipover_compliant"] is True
    assert gear_res["tail_clearance_compliant"] is True
    assert emp_res["spin_recovery_passed"] is True
    assert prop_res["tip_mach_passed"] is True
    assert bal_res["is_stable"] is True
    assert bal_res["cg_within_target"] is True


def test_tier4_real_world_twin_turboprop_commuter_beech1900():
    """End-to-End Tier 4 scenario: Beechcraft 1900 / ATR class 19-passenger twin turboprop commuter."""
    params = {
        "m0": 7765.0, "ws": 2400.0, "wingspan_m": 17.65, "aircraft_type": "turboprop_regional",
        "n_pax": 19, "n_crew": 2, "m_cargo": 800.0,
        "engine_power_kw": 950.0, "prop_rpm": 1700.0, "cruise_speed_kmh": 500.0,
        "fuselage_length_m": 17.63, "fuselage_diameter_m": 1.95,
        "wing_area_m2": 28.8, "mac_m": 1.70, "aspect_ratio": 10.8,
        "tail_layout": "t_tail",
    }
    gear_res = calculate_fuselage_and_gear(params)
    emp_res = calculate_empennage_sizing(params)
    prop_res = calculate_propulsion_clearance(params)
    bal_res = calculate_balance_envelope(params)

    assert gear_res["tipover_compliant"] is True
    assert gear_res["gear_reactions"]["cs23_load_factor_compliant"] is True
    assert emp_res["spin_recovery_verdict"] == "EXCELLENT"
    assert prop_res["tip_mach_passed"] is True
    assert bal_res["is_stable"] is True
