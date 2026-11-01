"""Standalone Empirical Verification Runner for Milestone M3.
Prints comprehensive empirical tables for AR sweep, load factor sweep,
technology factor scaling, and class robustness.
"""
import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from calculations.mass import estimate_component_masses


def run_ar_sweep():
    print("=" * 80)
    print("TEST 1: ASPECT RATIO MONOTONICITY SWEEP (AR 4.0 to 18.0, step 0.5)")
    print("=" * 80)

    m0 = 1150.0
    s_w = 16.0
    p = {
        "aircraft_type": "piston_ga",
        "category": "cs23_level2",
        "engine_type": "prop",
        "m_fuel": 120.0,
        "n_pax": 3,
        "n_crew": 1,
        "technology": "metallic",
        "wing_braced": False,
    }
    g_base = {
        "wing": {
            "S": s_w,
            "mac": 16.0 / math.sqrt(7.5 * 16.0),
            "sweep_25": 0.0,
            "taper_ratio": 0.65,
            "thickness_ratio": 0.15,
        },
        "horizontal_tail": {"S_h": 3.20, "AR_h": 4.0, "sweep": 0.0, "taper_ratio": 0.60, "thickness_ratio": 0.12, "arm": 4.50},
        "vertical_tail": {"S_v": 1.60, "AR_v": 1.5, "sweep": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.12, "arm": 4.50},
        "fuselage": {"length": 7.50, "diameter": 1.20, "S_wet": 0.75 * math.pi * 1.20 * 7.50},
        "gear": {"length_main_m": 0.71, "length_nose_m": 0.51},
    }
    env = {"n_ult": 5.7, "q_max_pa": 1869.0}

    ar_steps = [round(4.0 + 0.5 * i, 1) for i in range(29)]
    print(f"{'AR':>5} | {'b [m]':>7} | {'m_wing [kg]':>11} | {'Delta [kg]':>10} | {'Act Ratio':>9} | {'Exp Ratio':>9} | {'Strict Monotonic?':>17}")
    print("-" * 80)

    prev_w = None
    all_monotonic = True
    for i, ar in enumerate(ar_steps):
        p_curr = dict(p, aspect_ratio=ar)
        g_curr = copy.deepcopy(g_base)
        b = math.sqrt(s_w * ar)
        g_curr["wing"]["AR"] = ar
        g_curr["wing"]["b"] = b

        res = estimate_component_masses(m0, p_curr, g_curr, env)
        w_curr = res["breakdown"]["wing"]

        if prev_w is None:
            delta_str = "    -     "
            act_ratio_str = "   -    "
            exp_ratio_str = "   -    "
            status = "BASELINE"
        else:
            delta = w_curr - prev_w
            act_ratio = w_curr / prev_w
            exp_ratio = (ar / ar_steps[i - 1]) ** 0.60
            delta_str = f"{delta:+10.4f}"
            act_ratio_str = f"{act_ratio:9.5f}"
            exp_ratio_str = f"{exp_ratio:9.5f}"
            is_mono = delta > 0 and math.isclose(act_ratio, exp_ratio, rel_tol=1e-5)
            status = "PASS (STRICT)" if is_mono else "FAIL"
            if not is_mono:
                all_monotonic = False

        print(f"{ar:5.1f} | {b:7.3f} | {w_curr:11.4f} | {delta_str} | {act_ratio_str} | {exp_ratio_str} | {status:>17}")
        prev_w = w_curr

    print("-" * 80)
    print(f"Aspect Ratio Sweep Overall Verdict: {'PASS' if all_monotonic else 'FAIL'}\n")
    return all_monotonic


def run_load_factor_sweep():
    print("=" * 95)
    print("TEST 2: LOAD FACTOR MONOTONICITY SWEEP (n_ult 2.5 to 9.0, step 0.5)")
    print("=" * 95)

    m0 = 1150.0
    s_w = 16.0
    p = {
        "aircraft_type": "piston_ga",
        "category": "cs23_level2",
        "engine_type": "prop",
        "m_fuel": 120.0,
        "n_pax": 3,
        "n_crew": 1,
        "technology": "metallic",
        "wing_braced": False,
        "aspect_ratio": 7.5,
    }
    g = {
        "wing": {"S": s_w, "AR": 7.5, "b": math.sqrt(7.5 * s_w), "mac": 16.0 / math.sqrt(7.5 * s_w), "sweep_25": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.15},
        "horizontal_tail": {"S_h": 3.20, "AR_h": 4.0, "sweep": 0.0, "taper_ratio": 0.60, "thickness_ratio": 0.12, "arm": 4.50},
        "vertical_tail": {"S_v": 1.60, "AR_v": 1.5, "sweep": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.12, "arm": 4.50},
        "fuselage": {"length": 7.50, "diameter": 1.20, "S_wet": 0.75 * math.pi * 1.20 * 7.50},
        "gear": {"length_main_m": 0.71, "length_nose_m": 0.51},
    }

    n_steps = [round(2.5 + 0.5 * i, 1) for i in range(14)]
    print(f"{'n_ult':>5} | {'m_wing':>9} | {'m_ht':>8} | {'m_vt':>7} | {'m_fus':>8} | {'m_fc':>7} | {'m_struct':>9} | {'m_empty':>9} | {'Status':>8}")
    print("-" * 95)

    prev_struct = None
    all_monotonic = True
    for n in n_steps:
        env = {"n_ult": n, "q_max_pa": 1869.0}
        res = estimate_component_masses(m0, p, g, env)
        bd = res["breakdown"]

        w = bd["wing"]
        ht = bd["horizontal_tail"]
        vt = bd["vertical_tail"]
        fus = bd["fuselage"]
        fc = bd["flight_controls"]
        struct = res["m_structure"]
        empty = res["m_empty"]

        if prev_struct is None:
            status = "BASELINE"
        else:
            is_mono = (struct > prev_struct) and (w > prev_w) and (ht > prev_ht) and (vt > prev_vt) and (fus > prev_fus) and (fc > prev_fc)
            status = "PASS" if is_mono else "FAIL"
            if not is_mono:
                all_monotonic = False

        print(f"{n:5.1f} | {w:9.3f} | {ht:8.3f} | {vt:7.3f} | {fus:8.3f} | {fc:7.3f} | {struct:9.3f} | {empty:9.3f} | {status:>8}")
        prev_struct = struct
        prev_w = w
        prev_ht = ht
        prev_vt = vt
        prev_fus = fus
        prev_fc = fc

    print("-" * 95)
    print(f"Load Factor Sweep Overall Verdict: {'PASS' if all_monotonic else 'FAIL'}\n")
    return all_monotonic


def run_tech_factor_verification():
    print("=" * 95)
    print("TEST 3: TECHNOLOGY FACTOR EXACT SCALING")
    print("=" * 95)

    m0 = 1150.0
    p_metal = {
        "aircraft_type": "piston_ga",
        "category": "cs23_level2",
        "engine_type": "prop",
        "m_fuel": 120.0,
        "n_pax": 3,
        "n_crew": 1,
        "technology": "metallic",
        "wing_braced": False,
        "aspect_ratio": 7.5,
    }
    g = {
        "wing": {"S": 16.0, "AR": 7.5, "b": math.sqrt(7.5 * 16.0), "mac": 16.0 / math.sqrt(7.5 * 16.0), "sweep_25": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.15},
        "horizontal_tail": {"S_h": 3.20, "AR_h": 4.0, "sweep": 0.0, "taper_ratio": 0.60, "thickness_ratio": 0.12, "arm": 4.50},
        "vertical_tail": {"S_v": 1.60, "AR_v": 1.5, "sweep": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.12, "arm": 4.50},
        "fuselage": {"length": 7.50, "diameter": 1.20, "S_wet": 0.75 * math.pi * 1.20 * 7.50},
        "gear": {"length_main_m": 0.71, "length_nose_m": 0.51},
    }
    env = {"n_ult": 5.7, "q_max_pa": 1869.0}

    res_metal = estimate_component_masses(m0, p_metal, g, env)["breakdown"]

    p_comp = dict(p_metal, technology="advanced_composites")
    res_comp = estimate_component_masses(m0, p_comp, g, env)["breakdown"]

    p_braced = dict(p_metal, wing_braced=True, wing_config="braced_high")
    res_braced = estimate_component_masses(m0, p_braced, g, env)["breakdown"]

    p_combo = dict(p_metal, technology="advanced_composites", wing_braced=True, wing_config="braced_high")
    res_combo = estimate_component_masses(m0, p_combo, g, env)["breakdown"]

    print(f"{'Component':<16} | {'Metallic':>9} | {'Composite':>9} | {'Comp Ratio':>10} | {'Exp Ratio':>9} | {'Braced':>9} | {'Braced Ratio':>12} | {'Exp':>4}")
    print("-" * 95)

    comps = [
        ("wing", 0.85, 0.82),
        ("horizontal_tail", 0.83, 1.00),
        ("vertical_tail", 0.83, 1.00),
        ("fuselage", 0.90, 1.00),
        ("landing_gear", 0.95, 1.00),
        ("propulsion", 1.00, 1.00),
        ("fuel_system", 1.00, 1.00),
        ("flight_controls", 1.00, 1.00),
        ("avionics", 1.00, 1.00),
        ("electrical", 1.00, 1.00),
        ("furnishings", 1.00, 1.00),
    ]

    all_passed = True
    for c, exp_comp, exp_braced in comps:
        m_m = res_metal[c]
        m_c = res_comp[c]
        m_b = res_braced[c]

        ratio_c = m_c / m_m if m_m > 0 else 1.0
        ratio_b = m_b / m_m if m_m > 0 else 1.0

        ok_c = math.isclose(ratio_c, exp_comp, rel_tol=1e-6)
        ok_b = math.isclose(ratio_b, exp_braced, rel_tol=1e-6)

        if not (ok_c and ok_b):
            all_passed = False

        print(f"{c:<16} | {m_m:9.3f} | {m_c:9.3f} | {ratio_c:10.5f} | {exp_comp:9.2f} | {m_b:9.3f} | {ratio_b:12.5f} | {exp_braced:4.2f}")

    print("-" * 95)
    # Check combo wing
    combo_ratio = res_combo["wing"] / res_metal["wing"]
    exp_combo = 0.85 * 0.82
    print(f"Combined Advanced Composites + Braced Wing Ratio: {combo_ratio:.6f} (Expected: {exp_combo:.6f}) -> {'PASS' if math.isclose(combo_ratio, exp_combo, rel_tol=1e-6) else 'FAIL'}")
    print(f"Technology Factors Overall Verdict: {'PASS' if all_passed else 'FAIL'}\n")
    return all_passed


def run_robustness_verification():
    print("=" * 115)
    print("TEST 4: NUMERICAL ROBUSTNESS, NON-ZERO/NON-NEGATIVITY, AND MASS CONSERVATION ACROSS CLASSES")
    print("=" * 115)

    classes = [
        ("piston_ga", 1150.0, "prop", 3, 1, 120.0),
        ("turboprop_regional", 22000.0, "turboprop", 50, 2, 2500.0),
        ("jet_business", 10500.0, "jet", 8, 2, 3000.0),
        ("jet_transport", 75000.0, "jet", 160, 2, 15000.0),
        ("uav", 150.0, "prop", 0, 0, 30.0),
        ("glider", 450.0, "none", 0, 1, 0.0),
        ("motoglider", 650.0, "prop", 1, 1, 30.0),
    ]

    g = {
        "wing": {"S": 16.0, "AR": 7.5, "b": math.sqrt(7.5 * 16.0), "mac": 16.0 / math.sqrt(7.5 * 16.0), "sweep_25": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.15},
        "horizontal_tail": {"S_h": 3.20, "AR_h": 4.0, "sweep": 0.0, "taper_ratio": 0.60, "thickness_ratio": 0.12, "arm": 4.50},
        "vertical_tail": {"S_v": 1.60, "AR_v": 1.5, "sweep": 0.0, "taper_ratio": 0.65, "thickness_ratio": 0.12, "arm": 4.50},
        "fuselage": {"length": 7.50, "diameter": 1.20, "S_wet": 0.75 * math.pi * 1.20 * 7.50},
        "gear": {"length_main_m": 0.71, "length_nose_m": 0.51},
    }
    env = {"n_ult": 5.7, "q_max_pa": 1869.0}

    print(f"{'Class':<20} | {'Geom?':<5} | {'m0 [kg]':>8} | {'m_empty [kg]':>12} | {'NaN/Inf':>7} | {'Negatives':>9} | {'Zeros':>5} | {'Residual [kg]':>14} | {'Status':>6}")
    print("-" * 115)

    all_passed = True
    for ac, m0, eng, pax, crew, fuel in classes:
        for has_g in (True, False):
            p = {
                "aircraft_type": ac,
                "engine_type": eng,
                "n_pax": pax,
                "n_crew": crew,
                "m_fuel": fuel,
                "technology": "metallic",
                "aspect_ratio": 7.5,
            }
            res = estimate_component_masses(m0, p, g if has_g else None, env if has_g else None)
            bd = res["breakdown"]

            nan_inf = any(math.isnan(v) or math.isinf(v) for v in bd.values()) or math.isnan(res["m_empty"])
            negatives = [k for k, v in bd.items() if v < 0.0]

            zeros = []
            for k, v in bd.items():
                if v == 0.0:
                    if ac == "glider" and k in ("propulsion", "fuel_system"):
                        pass  # allowed
                    elif ac == "uav" and k == "furnishings":
                        pass  # allowed
                    else:
                        zeros.append(k)

            res_diff = abs(math.fsum(bd.values()) - res["m_empty"])
            ok = (not nan_inf) and (len(negatives) == 0) and (len(zeros) == 0) and (res_diff < 1e-11)
            if not ok:
                all_passed = False

            print(f"{ac:<20} | {'YES' if has_g else 'NO':<5} | {m0:8.1f} | {res['m_empty']:12.4f} | {'0' if not nan_inf else 'FAIL':>7} | {len(negatives):9d} | {len(zeros):5d} | {res_diff:14.2e} | {'PASS' if ok else 'FAIL':>6}")

    print("-" * 115)
    print(f"Robustness Verification Overall Verdict: {'PASS' if all_passed else 'FAIL'}\n")
    return all_passed


if __name__ == "__main__":
    t1 = run_ar_sweep()
    t2 = run_load_factor_sweep()
    t3 = run_tech_factor_verification()
    t4 = run_robustness_verification()
    print("=" * 80)
    print(f"OVERALL EMPIRICAL VERIFICATION VERDICT: {'APPROVE' if (t1 and t2 and t3 and t4) else 'REJECT'}")
    print("=" * 80)
