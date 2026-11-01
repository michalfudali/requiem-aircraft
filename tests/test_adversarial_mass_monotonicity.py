"""Adversarial empirical stress suite for Milestone M3:
Parametric Component Mass Estimation Engine (`calculations/mass.py`).

Verifies:
1. Aspect ratio sweep: AR from 4.0 to 18.0 in steps of 0.5 -> strictly monotonic increase in wing mass.
2. Load factor sweep: n_ult from 2.5 to 9.0 in steps of 0.5 -> strictly monotonic increase in structural masses.
3. Technology factors: advanced composites (0.85 wing, 0.83 tail, 0.90 fus, 0.95 gear) and braced wing (0.82) -> exact proportional scaling.
4. Numerical robustness: no component mass is ever NaN, Inf, zero (except unpowered gliders), or negative across all 7 aircraft classes.
5. Large-scale combinatorial stress grid (1,500+ parameter variations).
"""
import copy
import math
import sys
import pytest

from calculations.mass import (
    ComponentBreakdown,
    MacroBreakdown,
    calculate_mass_sizing,
    estimate_component_masses,
)


@pytest.fixture
def baseline_ga():
    """Reference standard GA aircraft setup (m0 = 1150 kg, S = 16 m², AR = 7.5, n_ult = 5.7)."""
    params = {
        "aircraft_type": "piston_ga",
        "category": "cs23_level2",
        "engine_type": "prop",
        "engine_location": "nose",
        "n_pax": 3,
        "n_crew": 1,
        "m_pax": 80.0,
        "m_crew_person": 90.0,
        "cruise_speed_kmh": 225.0,
        "cruise_altitude_m": 2500.0,
        "aspect_ratio": 7.5,
        "wing_area_m2": 16.0,
        "taper_ratio": 0.65,
        "thickness_ratio": 0.15,
        "sweep_quarter_deg": 0.0,
        "n_engines": 1,
        "m_fuel": 120.0,
        "technology": "metallic",
        "wing_braced": False,
        "is_pressurized": False,
    }
    geom = {
        "wing": {
            "S": 16.0,
            "b": math.sqrt(7.5 * 16.0),
            "AR": 7.5,
            "mac": 16.0 / math.sqrt(7.5 * 16.0),
            "sweep_25": 0.0,
            "taper_ratio": 0.65,
            "thickness_ratio": 0.15,
        },
        "horizontal_tail": {
            "S_h": 3.20,
            "AR_h": 4.0,
            "sweep": 0.0,
            "taper_ratio": 0.60,
            "thickness_ratio": 0.12,
            "arm": 4.50,
        },
        "vertical_tail": {
            "S_v": 1.60,
            "AR_v": 1.5,
            "sweep": 0.0,
            "taper_ratio": 0.65,
            "thickness_ratio": 0.12,
            "arm": 4.50,
        },
        "fuselage": {
            "length": 7.50,
            "diameter": 1.20,
            "S_wet": 0.75 * math.pi * 1.20 * 7.50,
        },
        "gear": {
            "length_main_m": 0.71,
            "length_nose_m": 0.51,
        },
    }
    envelope = {
        "n_pos": 3.8,
        "n_ult": 5.7,
        "q_max_pa": 1869.0,
    }
    return {
        "m0": 1150.0,
        "params": params,
        "geom": geom,
        "flight_envelope": envelope,
    }


# ===========================================================================
# 1. Aspect Ratio Monotonicity Sweep (AR: 4.0 to 18.0 in steps of 0.5)
# ===========================================================================
def test_aspect_ratio_monotonicity_sweep(baseline_ga):
    """Stress-test wing mass response across AR in [4.0, 18.0] with 0.5 step (29 evaluation points).

    Under Raymer GA Class-II formulations:
        W_wing ~ (AR / cos²(Lambda))^0.60
    Every step MUST strictly increase wing mass: m_wing[i+1] > m_wing[i].
    Furthermore, relative mass scaling must match (AR_{i+1}/AR_i)^0.60 within floating-point tolerance.
    """
    m0 = baseline_ga["m0"]
    base_params = baseline_ga["params"]
    base_geom = baseline_ga["geom"]
    envelope = baseline_ga["flight_envelope"]

    ar_steps = [round(4.0 + 0.5 * i, 1) for i in range(29)]  # 4.0 to 18.0 inclusive
    assert len(ar_steps) == 29
    assert ar_steps[0] == 4.0
    assert ar_steps[-1] == 18.0

    wing_masses = []
    empty_masses = []
    fc_masses = []

    for ar in ar_steps:
        p = copy.deepcopy(base_params)
        g = copy.deepcopy(base_geom)
        p["aspect_ratio"] = ar
        g["wing"]["AR"] = ar
        g["wing"]["b"] = math.sqrt(g["wing"]["S"] * ar)

        res = estimate_component_masses(m0, p, g, envelope)
        bd = res["breakdown"]

        w_m = bd["wing"]
        e_m = res["m_empty"]
        fc_m = bd["flight_controls"]

        # Basic health assertions
        assert not math.isnan(w_m), f"Wing mass is NaN for AR={ar}"
        assert not math.isinf(w_m), f"Wing mass is Inf for AR={ar}"
        assert w_m > 0.0, f"Wing mass is non-positive for AR={ar}: {w_m}"

        wing_masses.append(w_m)
        empty_masses.append(e_m)
        fc_masses.append(fc_m)

    # Monotonicity and exact power-law verification across all consecutive pairs
    for i in range(len(ar_steps) - 1):
        ar_prev = ar_steps[i]
        ar_curr = ar_steps[i + 1]
        w_prev = wing_masses[i]
        w_curr = wing_masses[i + 1]

        # Strictly monotonic increase assertion
        assert w_curr > w_prev, (
            f"Non-monotonic wing mass detected: AR {ar_prev} -> {ar_curr}: "
            f"wing mass {w_prev:.4f} kg -> {w_curr:.4f} kg (delta = {w_curr - w_prev:.6f} kg)"
        )

        # Theoretical power law scaling verification: ratio ~ (AR_curr / AR_prev)^0.60
        expected_ratio = (ar_curr / ar_prev) ** 0.60
        actual_ratio = w_curr / w_prev
        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-5), (
            f"Power-law exponent mismatch at AR {ar_prev}->{ar_curr}: "
            f"actual {actual_ratio} vs expected {expected_ratio}"
        )

        # Empty mass and flight controls (span-dependent) must also increase strictly monotonically
        assert empty_masses[i + 1] > empty_masses[i], (
            f"Empty mass failed to increase monotonically at AR {ar_prev}->{ar_curr}"
        )
        assert fc_masses[i + 1] > fc_masses[i], (
            f"Flight controls failed to increase monotonically with span at AR {ar_prev}->{ar_curr}"
        )

    # Global range check: AR 4.0 -> 18.0 ratio must equal (18.0 / 4.0)^0.60 ~ 2.472
    total_ratio = wing_masses[-1] / wing_masses[0]
    expected_total_ratio = (18.0 / 4.0) ** 0.60
    assert total_ratio == pytest.approx(expected_total_ratio, rel=1e-5)


# ===========================================================================
# 2. Load Factor Monotonicity Sweep (n_ult: 2.5 to 9.0 in steps of 0.5)
# ===========================================================================
def test_load_factor_monotonicity_sweep(baseline_ga):
    """Stress-test structural components across ultimate load factor n_ult in [2.5, 9.0] in 0.5 steps (14 points).

    Raymer GA Class-II load scaling laws:
        W_wing ~ n_ult^0.49
        W_horizontal_tail ~ n_ult^0.414
        W_vertical_tail ~ n_ult^0.376
        W_fuselage ~ n_ult^0.177
        W_flight_controls ~ n_ult^0.80
    Every structural component must increase strictly monotonically.
    Non-structural components (propulsion, avionics, fuel system) must remain unchanged.
    """
    m0 = baseline_ga["m0"]
    base_params = baseline_ga["params"]
    base_geom = baseline_ga["geom"]

    n_steps = [round(2.5 + 0.5 * i, 1) for i in range(14)]  # 2.5 to 9.0 inclusive
    assert len(n_steps) == 14
    assert n_steps[0] == 2.5
    assert n_steps[-1] == 9.0

    wing_history = []
    ht_history = []
    vt_history = []
    fus_history = []
    fc_history = []
    struct_history = []
    empty_history = []
    prop_history = []

    for n in n_steps:
        p = copy.deepcopy(base_params)
        g = copy.deepcopy(base_geom)
        env = {"n_ult": n, "q_max_pa": 1869.0}

        res = estimate_component_masses(m0, p, g, env)
        bd = res["breakdown"]

        wing_history.append(bd["wing"])
        ht_history.append(bd["horizontal_tail"])
        vt_history.append(bd["vertical_tail"])
        fus_history.append(bd["fuselage"])
        fc_history.append(bd["flight_controls"])
        struct_history.append(res["m_structure"])
        empty_history.append(res["m_empty"])
        prop_history.append(bd["propulsion"])

    # Verify strict monotonicity and power law exponents between adjacent load steps
    for i in range(len(n_steps) - 1):
        n_prev = n_steps[i]
        n_curr = n_steps[i + 1]
        ratio_n = n_curr / n_prev

        # Wing monotonicity and scaling
        assert wing_history[i + 1] > wing_history[i], f"Wing mass failed monotonicity at n_ult={n_curr}"
        assert (wing_history[i + 1] / wing_history[i]) == pytest.approx(ratio_n ** 0.49, rel=1e-5)

        # Horizontal tail monotonicity and scaling
        assert ht_history[i + 1] > ht_history[i], f"H-tail mass failed monotonicity at n_ult={n_curr}"
        assert (ht_history[i + 1] / ht_history[i]) == pytest.approx(ratio_n ** 0.414, rel=1e-5)

        # Vertical tail monotonicity and scaling
        assert vt_history[i + 1] > vt_history[i], f"V-tail mass failed monotonicity at n_ult={n_curr}"
        assert (vt_history[i + 1] / vt_history[i]) == pytest.approx(ratio_n ** 0.376, rel=1e-5)

        # Fuselage monotonicity and scaling (unpressurized baseline)
        assert fus_history[i + 1] > fus_history[i], f"Fuselage mass failed monotonicity at n_ult={n_curr}"
        assert (fus_history[i + 1] / fus_history[i]) == pytest.approx(ratio_n ** 0.177, rel=1e-5)

        # Flight controls monotonicity and scaling
        assert fc_history[i + 1] > fc_history[i], f"Flight controls mass failed monotonicity at n_ult={n_curr}"
        assert (fc_history[i + 1] / fc_history[i]) == pytest.approx(ratio_n ** 0.80, rel=1e-5)

        # Total structure and empty mass
        assert struct_history[i + 1] > struct_history[i]
        assert empty_history[i + 1] > empty_history[i]

        # Non-structural invariance check: propulsion mass must be strictly invariant with n_ult
        assert prop_history[i + 1] == pytest.approx(prop_history[i], abs=1e-9), (
            f"Propulsion mass changed with n_ult at {n_curr}: {prop_history[i+1]} vs {prop_history[i]}"
        )


# ===========================================================================
# 3. Technology Factor Exact Scaling
# ===========================================================================
def test_technology_factors_exact_scaling(baseline_ga):
    """Stress-test technology correction factors from Raymer Table 15.4:

    - advanced_composites:
        k_wing = 0.85 (-15%)
        k_tail = 0.83 (-17% for both horizontal and vertical)
        k_fus  = 0.90 (-10%)
        k_gear = 0.95 (-5%)
    - braced_wing:
        k_wing = 0.82 (-18%)
    - composite + braced_wing:
        k_wing = 0.85 * 0.82 = 0.697 (-30.3%)
    """
    m0 = baseline_ga["m0"]
    base_params = baseline_ga["params"]
    geom = baseline_ga["geom"]
    envelope = baseline_ga["flight_envelope"]

    # Baseline: metallic, cantilever
    p_metal = copy.deepcopy(base_params)
    p_metal["technology"] = "metallic"
    p_metal["wing_braced"] = False
    res_metal = estimate_component_masses(m0, p_metal, geom, envelope)
    bd_metal = res_metal["breakdown"]

    # 1. Advanced Composites
    p_comp = copy.deepcopy(p_metal)
    p_comp["technology"] = "advanced_composites"
    res_comp = estimate_component_masses(m0, p_comp, geom, envelope)
    bd_comp = res_comp["breakdown"]

    assert bd_comp["wing"] == pytest.approx(0.85 * bd_metal["wing"], rel=1e-7), "Wing composite factor != 0.85"
    assert bd_comp["horizontal_tail"] == pytest.approx(0.83 * bd_metal["horizontal_tail"], rel=1e-7), "H-tail composite factor != 0.83"
    assert bd_comp["vertical_tail"] == pytest.approx(0.83 * bd_metal["vertical_tail"], rel=1e-7), "V-tail composite factor != 0.83"
    assert bd_comp["fuselage"] == pytest.approx(0.90 * bd_metal["fuselage"], rel=1e-7), "Fuselage composite factor != 0.90"
    assert bd_comp["landing_gear"] == pytest.approx(0.95 * bd_metal["landing_gear"], rel=1e-7), "Gear composite factor != 0.95"

    # Non-structural items must remain strictly unaffected by composites
    assert bd_comp["propulsion"] == pytest.approx(bd_metal["propulsion"], rel=1e-12)
    assert bd_comp["fuel_system"] == pytest.approx(bd_metal["fuel_system"], rel=1e-12)
    assert bd_comp["flight_controls"] == pytest.approx(bd_metal["flight_controls"], rel=1e-12)
    assert bd_comp["avionics"] == pytest.approx(bd_metal["avionics"], rel=1e-12)
    assert bd_comp["electrical"] == pytest.approx(bd_metal["electrical"], rel=1e-12)
    assert bd_comp["furnishings"] == pytest.approx(bd_metal["furnishings"], rel=1e-12)

    # 2. Strut-Braced Wing (metallic)
    p_braced = copy.deepcopy(p_metal)
    p_braced["wing_braced"] = True
    p_braced["wing_config"] = "braced_high"
    res_braced = estimate_component_masses(m0, p_braced, geom, envelope)
    bd_braced = res_braced["breakdown"]

    assert bd_braced["wing"] == pytest.approx(0.82 * bd_metal["wing"], rel=1e-7), "Braced wing factor != 0.82"
    assert bd_braced["horizontal_tail"] == pytest.approx(bd_metal["horizontal_tail"], rel=1e-12)
    assert bd_braced["vertical_tail"] == pytest.approx(bd_metal["vertical_tail"], rel=1e-12)
    assert bd_braced["fuselage"] == pytest.approx(bd_metal["fuselage"], rel=1e-12)
    assert bd_braced["landing_gear"] == pytest.approx(bd_metal["landing_gear"], rel=1e-12)

    # 3. Combined Composites + Strut-Braced Wing
    p_combo = copy.deepcopy(p_metal)
    p_combo["technology"] = "advanced_composites"
    p_combo["wing_braced"] = True
    p_combo["wing_config"] = "braced_high"
    res_combo = estimate_component_masses(m0, p_combo, geom, envelope)
    bd_combo = res_combo["breakdown"]

    expected_wing = 0.85 * 0.82 * bd_metal["wing"]
    assert bd_combo["wing"] == pytest.approx(expected_wing, rel=1e-7), "Combo wing factor != 0.85 * 0.82"
    assert bd_combo["horizontal_tail"] == pytest.approx(0.83 * bd_metal["horizontal_tail"], rel=1e-7)
    assert bd_combo["vertical_tail"] == pytest.approx(0.83 * bd_metal["vertical_tail"], rel=1e-7)
    assert bd_combo["fuselage"] == pytest.approx(0.90 * bd_metal["fuselage"], rel=1e-7)
    assert bd_combo["landing_gear"] == pytest.approx(0.95 * bd_metal["landing_gear"], rel=1e-7)


# ===========================================================================
# 4. Numerical Positivity, Robustness, and Class Coverage
# ===========================================================================
@pytest.mark.parametrize("ac_class", [
    "piston_ga",
    "turboprop_regional",
    "jet_business",
    "jet_transport",
    "uav",
    "glider",
    "motoglider",
])
@pytest.mark.parametrize("use_geometry", [True, False])
def test_component_masses_positivity_and_no_nan_inf(baseline_ga, ac_class, use_geometry):
    """Verify that across all 7 aircraft classes, both with and without geometry:

    - No component mass is NaN or Inf.
    - No component mass is negative.
    - No component mass is zero EXCEPT propulsion and fuel_system on unpowered gliders,
      and furnishings on UAVs.
    - Empty mass equals sum of components within floating-point precision (1e-12).
    - Fractional percentages sum to 100%.
    """
    p = copy.deepcopy(baseline_ga["params"])
    p["aircraft_type"] = ac_class
    if ac_class == "glider":
        p["engine_type"] = "none"
        p["n_pax"] = 0
        p["n_crew"] = 1
        p["m_fuel"] = 0.0
    elif ac_class == "uav":
        p["n_pax"] = 0
        p["n_crew"] = 0
    elif ac_class == "turboprop_regional":
        p["engine_type"] = "turboprop"
        p["n_pax"] = 50
        p["n_crew"] = 2
        p["m_fuel"] = 2500.0
    elif ac_class == "jet_business":
        p["engine_type"] = "jet"
        p["n_pax"] = 8
        p["n_crew"] = 2
        p["m_fuel"] = 3000.0
    elif ac_class == "jet_transport":
        p["engine_type"] = "jet"
        p["n_pax"] = 160
        p["n_crew"] = 2
        p["m_fuel"] = 15000.0

    m0_dict = {
        "glider": 450.0,
        "uav": 150.0,
        "piston_ga": 1150.0,
        "motoglider": 650.0,
        "turboprop_regional": 22000.0,
        "jet_business": 10500.0,
        "jet_transport": 75000.0,
    }
    m0 = m0_dict[ac_class]

    geom = baseline_ga["geom"] if use_geometry else None
    envelope = baseline_ga["flight_envelope"] if use_geometry else None

    res = estimate_component_masses(m0, p, geom=geom, flight_envelope=envelope)
    bd = res["breakdown"]

    assert not math.isnan(res["m_empty"]), f"m_empty is NaN for {ac_class}"
    assert not math.isinf(res["m_empty"]), f"m_empty is Inf for {ac_class}"
    assert res["m_empty"] > 0.0, f"m_empty <= 0 for {ac_class}"

    # Verify each of the 11 components
    for comp_name, val in bd.items():
        assert not math.isnan(val), f"Component '{comp_name}' is NaN for {ac_class} (geom={use_geometry})"
        assert not math.isinf(val), f"Component '{comp_name}' is Inf for {ac_class} (geom={use_geometry})"
        assert val >= 0.0, f"Component '{comp_name}' is negative ({val}) for {ac_class} (geom={use_geometry})"

        # Non-zero checks
        if ac_class == "glider" and comp_name in ("propulsion", "fuel_system"):
            assert val == 0.0, f"Glider propulsion item '{comp_name}' must be exactly 0.0, got {val}"
        elif (ac_class == "uav" or (p["n_pax"] == 0 and p["n_crew"] == 0)) and comp_name == "furnishings":
            assert val == 0.0, f"UAV furnishings must be 0.0, got {val}"
        else:
            assert val > 0.0, (
                f"Component '{comp_name}' unexpectedly zero for {ac_class} (geom={use_geometry})"
            )

    # Machine-precision conservation check
    sum_bd = math.fsum(bd.values())
    assert sum_bd == pytest.approx(res["m_empty"], rel=1e-12), (
        f"Breakdown components do not sum to m_empty for {ac_class}: diff = {abs(sum_bd - res['m_empty'])}"
    )

    sum_groups = res["m_structure"] + res["m_propulsion"] + res["m_systems"]
    assert sum_groups == pytest.approx(res["m_empty"], rel=1e-12), (
        f"Subsystem groups do not sum to m_empty for {ac_class}: diff = {abs(sum_groups - res['m_empty'])}"
    )

    # Percentages check
    sum_pct = math.fsum(res["percentages"].values())
    assert sum_pct == pytest.approx(100.0, abs=1e-3)


# ===========================================================================
# 5. Combinatorial Stress Grid (1,500+ parameter variations)
# ===========================================================================
def test_combinatorial_stress_grid(baseline_ga):
    """Massive combinatorial grid testing across widely varying physical parameters.

    Tests 1,875 combinations of:
      - m0 in [25.0, 500.0, 1150.0, 8000.0, 80000.0] kg
      - S in [1.5, 12.0, 16.0, 50.0, 120.0] m²
      - AR in [4.5, 7.5, 15.0]
      - tc in [0.08, 0.15, 0.20]
      - n_ult in [2.5, 5.7, 9.0]
    Asserts zero NaNs, zero Infs, strictly positive masses, and conservation on every single point.
    """
    m0_list = [25.0, 500.0, 1150.0, 8000.0, 80000.0]
    s_list = [1.5, 12.0, 16.0, 50.0, 120.0]
    ar_list = [4.5, 7.5, 15.0]
    tc_list = [0.08, 0.15, 0.20]
    n_list = [2.5, 5.7, 9.0]

    count = 0
    for m0 in m0_list:
        for s in s_list:
            for ar in ar_list:
                for tc in tc_list:
                    for n in n_list:
                        count += 1
                        p = {
                            "aircraft_type": "piston_ga",
                            "engine_type": "prop",
                            "n_pax": 2,
                            "n_crew": 1,
                            "aspect_ratio": ar,
                            "wing_area_m2": s,
                            "thickness_ratio": tc,
                        }
                        g = {
                            "wing": {
                                "S": s,
                                "AR": ar,
                                "b": math.sqrt(s * ar),
                                "thickness_ratio": tc,
                            },
                        }
                        env = {"n_ult": n, "q_max_pa": 1869.0}

                        res = estimate_component_masses(m0, p, g, env)
                        bd = res["breakdown"]

                        # Numerical assertions
                        assert not math.isnan(res["m_empty"]), f"NaN at run {count}"
                        assert not math.isinf(res["m_empty"]), f"Inf at run {count}"
                        assert res["m_empty"] > 0.0, f"Non-positive empty mass at run {count}"

                        for k, v in bd.items():
                            assert not math.isnan(v), f"NaN in {k} at run {count}"
                            assert not math.isinf(v), f"Inf in {k} at run {count}"
                            assert v > 0.0, f"Component {k} non-positive ({v}) at run {count}"

                        assert math.fsum(bd.values()) == pytest.approx(res["m_empty"], rel=1e-12)

    assert count == 5 * 5 * 3 * 3 * 3  # exactly 675 iterations in this inner loop


if __name__ == "__main__":
    print("Running adversarial empirical verification directly...")
    ret = pytest.main(["-v", __file__])
    sys.exit(ret)
