"""Empirical Adversarial Verification Runner for Milestone M3 (Challenger 2).

Scope:
1. Extreme mass scale: test MTOW from 10 kg (micro-UAV) to 500,000 kg (heavy transport).
2. Invariant check: verify that for 100 random parameter combinations across all 7 aircraft classes,
   the sum of breakdown components equals m_empty to within 1e-12 (mass conservation invariant).
3. Fuzz testing: test with empty dicts, missing geometry keys, None values, unusual string inputs.
   Ensure no unhandled exceptions crash the system and graceful fallback is used.

Author: challenger_m3_2
"""
import copy
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from calculations.mass import (
    ComponentBreakdown,
    MacroBreakdown,
    calculate_mass_sizing,
    estimate_component_masses,
)

AIRCRAFT_CLASSES = [
    "piston_ga",
    "turboprop_regional",
    "jet_business",
    "jet_transport",
    "glider",
    "motoglider",
    "uav",
]


def run_extreme_mass_scale():
    print("=" * 110)
    print("SECTION 1: EXTREME MASS SCALE STRESS TEST (MTOW 10 kg to 500,000 kg)")
    print("=" * 110)

    scales = [
        (10.0, "uav", "Micro-UAV (10 kg)"),
        (25.0, "uav", "Tactical UAV (25 kg)"),
        (100.0, "uav", "Heavy Cargo UAV (100 kg)"),
        (350.0, "glider", "Club Glider (350 kg)"),
        (450.0, "motoglider", "Touring Motoglider (450 kg)"),
        (750.0, "piston_ga", "Light Sport Trainer (750 kg)"),
        (1150.0, "piston_ga", "Standard GA 4-seat (1150 kg)"),
        (5000.0, "turboprop_regional", "Twin Commuter Turboprop (5000 kg)"),
        (18000.0, "jet_business", "Mid-size Business Jet (18000 kg)"),
        (75000.0, "jet_transport", "Narrowbody Airliner (75000 kg)"),
        (250000.0, "jet_transport", "Widebody Airliner (250000 kg)"),
        (500000.0, "jet_transport", "Ultra-Heavy Cargo Transport (500000 kg)"),
    ]

    print(f"{'Description':<35} | {'m0 [kg]':>10} | {'Method':<17} | {'m_empty [kg]':>12} | {'Rel Invariant Err':>18} | {'Status':>6}")
    print("-" * 110)

    all_passed = True

    for m0, ac_type, desc in scales:
        for use_geom in (False, True):
            method_label = "Raymer Parametric" if use_geom else "Statistical FB"

            ws = max(25.0, min(650.0, 30.0 * (m0 ** 0.25)))
            s_w = m0 / ws
            ar = 18.0 if ac_type == "glider" else 9.0 if ac_type in ("jet_transport", "jet_business") else 7.5
            b = math.sqrt(ar * s_w)
            l_f = max(2.0, 0.75 * b)
            d_f = max(0.5, 0.12 * l_f)

            params = {
                "aircraft_type": ac_type,
                "engine_type": "none" if ac_type == "glider" else "prop" if ac_type in ("piston_ga", "motoglider") else "jet",
                "wing_area_m2": s_w,
                "aspect_ratio": ar,
                "m_fuel": 0.25 * m0,
                "n_pax": 0 if ac_type == "uav" else 1 if ac_type in ("glider", "motoglider") else max(1, int(m0 / 1200.0)),
                "n_crew": 0 if ac_type == "uav" else 1 if m0 < 5000.0 else 2,
            }

            geom = None
            env = None
            if use_geom:
                geom = {
                    "wing": {
                        "S": s_w,
                        "b": b,
                        "AR": ar,
                        "sweep_25": 0.0 if m0 < 10000 else math.radians(28.0),
                        "taper_ratio": 0.5,
                        "thickness_ratio": 0.12,
                    },
                    "horizontal_tail": {
                        "S_h": 0.22 * s_w,
                        "AR_h": 4.0,
                        "sweep": 0.0,
                        "taper_ratio": 0.6,
                        "thickness_ratio": 0.11,
                        "arm": 0.55 * l_f,
                    },
                    "vertical_tail": {
                        "S_v": 0.12 * s_w,
                        "AR_v": 1.6,
                        "sweep": 0.0,
                        "taper_ratio": 0.6,
                        "thickness_ratio": 0.11,
                        "arm": 0.55 * l_f,
                    },
                    "fuselage": {
                        "length": l_f,
                        "diameter": d_f,
                        "S_wet": 0.75 * math.pi * d_f * l_f,
                    },
                    "gear": {
                        "length_main_m": max(0.4, 0.08 * l_f),
                        "length_nose_m": max(0.3, 0.06 * l_f),
                    },
                }
                env = {
                    "n_pos": 3.8 if m0 < 5000 else 2.5,
                    "n_ult": 1.5 * (3.8 if m0 < 5000 else 2.5),
                    "q_max_pa": min(25000.0, 1000.0 * (m0 ** 0.15)),
                }

            res = estimate_component_masses(m0, params, geom=geom, flight_envelope=env)
            bd = res["breakdown"]

            m_empty = res["m_empty"]
            comp_sum = math.fsum(bd.values())
            rel_err = abs(comp_sum - m_empty) / m_empty

            has_negative = any(v < 0.0 for v in bd.values())
            has_nan_inf = any(math.isnan(v) or math.isinf(v) for v in bd.values())
            is_valid = (m_empty > 0.0) and (not has_negative) and (not has_nan_inf) and (rel_err < 1e-12)

            if not is_valid:
                all_passed = False

            status = "PASS" if is_valid else "FAIL"
            print(f"{desc:<35} | {m0:10.1f} | {method_label:<17} | {m_empty:12.3f} | {rel_err:18.2e} | {status:>6}")

    print("-" * 110)
    print(f"Section 1 Extreme Mass Scale Overall Verdict: {'PASS' if all_passed else 'FAIL'}\n")
    return all_passed


def run_invariant_100_random_checks():
    print("=" * 110)
    print("SECTION 2: MASS CONSERVATION INVARIANT CHECK (100 Random Trials Across 7 Classes)")
    print("=" * 110)

    rng = random.Random(42)
    max_rel_err = 0.0
    max_abs_err = 0.0
    class_counts = {c: 0 for c in AIRCRAFT_CLASSES}
    all_passed = True

    for trial in range(100):
        ac_class = rng.choice(AIRCRAFT_CLASSES)
        class_counts[ac_class] += 1
        m0 = 10.0 ** rng.uniform(1.0, 5.6)  # 10 kg to 400,000 kg

        has_geom = rng.choice([True, False])
        is_glider = ac_class in ("glider", "motoglider") and rng.random() < 0.5
        engine_type = "none" if is_glider else rng.choice(["prop", "turboprop", "jet", "turbofan", "piston"])
        tech = rng.choice(["metallic", "advanced_composites", "composite", "wood", "steel_tube", "unknown"])
        wing_config = rng.choice(["low", "high", "mid", "braced_high"])

        params = {
            "aircraft_type": ac_class,
            "engine_type": engine_type,
            "technology": tech,
            "wing_config": wing_config,
            "wing_braced": wing_config == "braced_high",
            "is_pressurized": rng.choice([True, False]),
            "m0": m0,
        }

        if ac_class == "uav":
            params["n_pax"] = 0
            params["n_crew"] = 0
        elif is_glider:
            params["n_pax"] = 0
            params["n_crew"] = 1
        else:
            params["n_pax"] = rng.randint(0, max(1, int(m0 / 1000)))
            params["n_crew"] = 0 if params["n_pax"] == 0 else rng.randint(1, 4)

        geom = None
        env = None
        if has_geom:
            ws = rng.uniform(20.0, 500.0)
            s_w = max(0.5, m0 / ws)
            ar = rng.uniform(4.5, 22.0)
            b = math.sqrt(ar * s_w)
            l_f = max(1.5, rng.uniform(0.5, 1.2) * b)
            d_f = max(0.3, rng.uniform(0.05, 0.20) * l_f)
            geom = {
                "wing": {
                    "S": s_w, "b": b, "AR": ar, "sweep_25": math.radians(rng.uniform(0.0, 35.0)),
                    "taper_ratio": rng.uniform(0.3, 1.0), "thickness_ratio": rng.uniform(0.08, 0.20),
                },
                "horizontal_tail": {
                    "S_h": rng.uniform(0.12, 0.28) * s_w, "AR_h": rng.uniform(3.0, 5.5),
                    "sweep": 0.0, "taper_ratio": 0.6, "thickness_ratio": 0.11, "arm": 0.55 * l_f,
                },
                "vertical_tail": {
                    "S_v": rng.uniform(0.08, 0.18) * s_w, "AR_v": rng.uniform(1.1, 2.2),
                    "sweep": 0.0, "taper_ratio": 0.6, "thickness_ratio": 0.11, "arm": 0.55 * l_f,
                },
                "fuselage": {"length": l_f, "diameter": d_f, "S_wet": 0.75 * math.pi * d_f * l_f},
                "gear": {"length_main_m": 0.8, "length_nose_m": 0.6},
            }
            env = {"n_pos": rng.uniform(2.5, 5.0), "n_ult": rng.uniform(3.8, 7.5), "q_max_pa": rng.uniform(1000.0, 15000.0)}

        res = estimate_component_masses(m0, params, geom=geom, flight_envelope=env)
        m_empty = res["m_empty"]
        bd = res["breakdown"]
        comp_sum = math.fsum(bd.values())
        abs_err = abs(comp_sum - m_empty)
        rel_err = abs_err / m_empty

        if rel_err > max_rel_err:
            max_rel_err = rel_err
        if abs_err > max_abs_err:
            max_abs_err = abs_err

        if rel_err >= 1e-12:
            all_passed = False

    print(f"Trials Executed        : 100")
    print(f"Class Distribution     : {class_counts}")
    print(f"Maximum Absolute Error : {max_abs_err:.2e} kg")
    print(f"Maximum Relative Error : {max_rel_err:.2e} (Threshold: 1.00e-12)")
    print(f"Mass Conservation Check: {'PASS (IEEE-754 limit satisfied)' if all_passed else 'FAIL'}")
    print(f"Section 2 Invariant Check Overall Verdict: {'PASS' if all_passed else 'FAIL'}\n")
    return all_passed


def run_fuzz_testing():
    print("=" * 110)
    print("SECTION 3: ADVERSARIAL FUZZ TESTING & GRACEFUL FALLBACK AUDIT")
    print("=" * 110)

    fuzz_scenarios = [
        # Category A: Empty dicts and defaults
        ("Empty dict input params={}", lambda: estimate_component_masses({}), "Statistical fallback", True),
        ("None params input params=None", lambda: estimate_component_masses(1000.0, None), "Statistical fallback", True),
        ("calculate_mass_sizing({})", lambda: calculate_mass_sizing({}), "Normal sizing defaults", True),

        # Category B: Missing geometry keys
        ("geom={}", lambda: estimate_component_masses(1000.0, geom={}), "Statistical fallback", True),
        ("geom={'wing': {}}", lambda: estimate_component_masses(1000.0, geom={"wing": {}}), "Statistical fallback", True),
        ("geom={'wing': {'S': 15.0}} (missing tails/fus/gear)", lambda: estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}}), "Raymer with heuristics", True),
        ("geom empty sub-dicts", lambda: estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}, "horizontal_tail": {}, "vertical_tail": {}, "fuselage": {}, "gear": {}}), "Raymer with heuristics", True),

        # Category C: Unusual string inputs
        ("Unknown aircraft_type='alien_starship'", lambda: estimate_component_masses(1000.0, {"aircraft_type": "alien_starship"}), "Fallback to piston_ga shares", True),
        ("Unknown engine_type='dark_matter'", lambda: estimate_component_masses(1000.0, {"engine_type": "dark_matter"}), "Engine heuristics fallback", True),
        ("Unknown technology='unobtainium'", lambda: estimate_component_masses(1000.0, {"technology": "unobtainium"}), "1.0 technology factor fallback", True),

        # Category D: None values in parameters (Graceful fallback vs Unhandled crashes)
        ("params={'aircraft_type': None}", lambda: estimate_component_masses(1000.0, {"aircraft_type": None}), "Fallback to piston_ga", True),
        ("params={'engine_type': None}", lambda: estimate_component_masses(1000.0, {"engine_type": None}), "Engine fallback", True),
        ("params={'technology': None}", lambda: estimate_component_masses(1000.0, {"technology": None}), "Material fallback", True),
        ("params={'wing_config': None}", lambda: estimate_component_masses(1000.0, {"wing_config": None}), "Config fallback", True),
        ("params={'wing_braced': None}", lambda: estimate_component_masses(1000.0, {"wing_braced": None}), "Config fallback", True),
        ("params={'is_pressurized': None}", lambda: estimate_component_masses(1000.0, {"is_pressurized": None}), "Fuselage fallback", True),

        # Category E: Vulnerability triggers (None values that cause unhandled exceptions)
        ("geom={'wing': None}", lambda: estimate_component_masses(1000.0, geom={"wing": None}), "Should fall back gracefully", False),
        ("geom={'wing': {'S': None}}", lambda: estimate_component_masses(1000.0, geom={"wing": {"S": None}}), "Should fall back gracefully", False),
        ("geom={'wing': {'S': 15.0}, 'horizontal_tail': None}", lambda: estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}, "horizontal_tail": None}), "Should fall back gracefully", False),
        ("flight_envelope={'n_ult': None}", lambda: estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}}, flight_envelope={"n_ult": None}), "Should default n_ult", False),
        ("params={'n_pax': None}", lambda: estimate_component_masses(1000.0, {"n_pax": None}), "Should default n_pax", False),
        ("params={'n_crew': None}", lambda: estimate_component_masses(1000.0, {"n_crew": None}), "Should default n_crew", False),
    ]

    print(f"{'Scenario':<55} | {'Expected Behavior':<25} | {'Outcome':<23}")
    print("-" * 110)

    clean_fallbacks = 0
    unhandled_crashes = 0
    crash_details = []

    for name, fn, exp_behavior, should_succeed in fuzz_scenarios:
        try:
            res = fn()
            outcome = f"PASS (method={res.get('method', 'sizing')})"
            clean_fallbacks += 1
            print(f"{name:<55} | {exp_behavior:<25} | {outcome:<23}")
        except Exception as e:
            exc_desc = f"{type(e).__name__}: {str(e)[:30]}"
            if should_succeed:
                outcome = f"UNEXPECTED FAIL ({exc_desc})"
                print(f"{name:<55} | {exp_behavior:<25} | {outcome:<23}")
            else:
                unhandled_crashes += 1
                crash_details.append((name, type(e).__name__, str(e)))
                outcome = f"CRASH: {exc_desc}"
                print(f"{name:<55} | {exp_behavior:<25} | {outcome:<23}")

    print("-" * 110)
    print(f"Clean Graceful Fallbacks   : {clean_fallbacks}")
    print(f"Unhandled System Crashes   : {unhandled_crashes}")
    if unhandled_crashes > 0:
        print("\nDefect Findings (DEF-MASS-FUZZ-01):")
        for sc_name, exc_type, exc_msg in crash_details:
            print(f"  - Scenario: {sc_name}")
            print(f"    Exception: {exc_type}: {exc_msg}")
    print(f"\nSection 3 Fuzz Testing Verdict: {'REJECT (Robustness Defects Found)' if unhandled_crashes > 0 else 'APPROVE'}\n")
    return unhandled_crashes == 0


if __name__ == "__main__":
    t1 = run_extreme_mass_scale()
    t2 = run_invariant_100_random_checks()
    t3 = run_fuzz_testing()

    print("=" * 110)
    verdict = "APPROVE" if (t1 and t2 and t3) else "REJECT"
    print(f"FINAL ADVERSARIAL VERIFICATION VERDICT: {verdict}")
    print("=" * 110)
    sys.exit(0 if verdict == "APPROVE" else 1)
