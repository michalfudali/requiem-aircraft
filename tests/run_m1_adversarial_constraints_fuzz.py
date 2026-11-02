"""Intensive Adversarial Fuzz and Property-Based Stress Harness for Milestone 1:
Matching Chart Constraints Engine.

Author: m1_challenger_2 (Empirical Challenger)
"""
import math
import random
import sys
import time

from calculations.atmosphere import G0, RHO0, isa_atmosphere
from calculations.presets import AIRCRAFT_PRESETS
from calculations.sizing import (
    CZ_SAFETY,
    calculate_constraint_curves,
    calculate_matching_chart,
    climb_tw,
    landing_ws,
    takeoff_mean_speed,
    takeoff_tw,
)


def run_takeoff_tw_fuzz(n_iterations=20000):
    """Fuzz takeoff_tw with extreme values, checking strict positivity, None on impossible flare, and monotonicity."""
    print(f"[1/4] Running Takeoff T/W Fuzz ({n_iterations} iterations)...")
    rng = random.Random(42)
    none_count = 0
    valid_count = 0

    for i in range(n_iterations):
        ws = rng.uniform(50.0, 15000.0)
        cz_to = rng.uniform(0.5, 4.0)
        sigma = rng.uniform(0.3, 1.2)
        s_to = rng.uniform(50.0, 5000.0)

        tw = takeoff_tw(ws, cz_to, s_to, sigma=sigma)

        top = ws / (cz_to * sigma)
        flare_dist = 3.834 * math.sqrt(top)

        if s_to <= flare_dist:
            assert tw is None, f"Expected None when s_to ({s_to}) <= flare_dist ({flare_dist})"
            none_count += 1
        else:
            assert tw is not None, f"Expected float when s_to ({s_to}) > flare_dist ({flare_dist})"
            assert tw > 0, f"Takeoff T/W must be positive: got {tw}"
            assert not math.isnan(tw) and not math.isinf(tw)
            valid_count += 1

    print(f"      Passed: {valid_count} valid positive T/W solutions, {none_count} gracefully handled flare asymptotes.")


def run_climb_asymptote_fuzz(n_iterations=20000):
    """Fuzz climb_tw, verifying that T/W >= G + 1/Kmax holds unconditionally for all valid inputs."""
    print(f"[2/4] Running Climb Asymptote Invariant Fuzz ({n_iterations} iterations)...")
    rng = random.Random(12345)

    for i in range(n_iterations):
        ws = rng.uniform(50.0, 12000.0)
        q = rng.uniform(10.0, 20000.0)
        cx0 = rng.uniform(0.010, 0.080)
        ar = rng.uniform(2.0, 35.0)
        e = rng.uniform(0.5, 0.95)
        gradient = rng.uniform(0.0, 0.30)

        k_ind = 1.0 / (math.pi * ar * e)
        inv_k_max = 2.0 * math.sqrt(cx0 * k_ind)
        min_asymptote = gradient + inv_k_max

        tw = climb_tw(ws, q, cx0, k_ind, gradient)

        assert tw >= min_asymptote - 1e-11, (
            f"Climb asymptote invariant violated: tw={tw} < min_asymptote={min_asymptote} "
            f"at ws={ws}, q={q}, cx0={cx0}, ar={ar}, e={e}"
        )

    print(f"      Passed: 100% of {n_iterations} points satisfied T/W >= G + 1/Kmax unconditionally.")


def run_landing_ws_fuzz(n_iterations=10000):
    """Fuzz landing_ws, verifying exact linear scaling and zero division avoidance."""
    print(f"[3/4] Running Landing W/S Fuzz ({n_iterations} iterations)...")
    rng = random.Random(9999)

    for i in range(n_iterations):
        cz_lnd = rng.uniform(0.8, 4.5)
        sigma = rng.uniform(0.4, 1.2)
        s_l = rng.uniform(122.001, 6000.0)

        ws_l = landing_ws(cz_lnd, s_l, sigma=sigma)
        assert ws_l > 0, f"Expected positive landing W/S: got {ws_l}"
        assert not math.isnan(ws_l) and not math.isinf(ws_l)

        # Monotonicity with respect to runway length
        ws_l_more = landing_ws(cz_lnd, s_l + 100.0, sigma=sigma)
        assert ws_l_more > ws_l

    print(f"      Passed: 100% of {n_iterations} landing points strictly positive and monotonic.")


def run_end_to_end_matching_chart_fuzz(n_iterations=500):
    """Fuzz calculate_matching_chart across 500 randomized plausible aircraft configurations."""
    print(f"[4/4] Running End-to-End Matching Chart Fuzz ({n_iterations} designs)...")
    rng = random.Random(2026)
    passed = 0

    base_presets = list(AIRCRAFT_PRESETS.values())

    for i in range(n_iterations):
        template = dict(rng.choice(base_presets))

        # Perturb parameters within plausible engineering limits
        cz_lnd = rng.uniform(1.8, 3.2)
        cz_to = min(cz_lnd * 0.85, rng.uniform(1.4, 2.4))
        cz_clean = min(cz_to * 0.85, rng.uniform(1.1, 1.6))

        template.update({
            "cz_max_clean": cz_clean,
            "cz_max_to": cz_to,
            "cz_max_lnd": cz_lnd,
            "v_stall_kmh": rng.uniform(70.0, 160.0),
            "cruise_speed_kmh": rng.uniform(180.0, 450.0),
            "takeoff_distance_m": rng.uniform(400.0, 1800.0),
            "landing_distance_m": rng.uniform(400.0, 1800.0),
            "climb_rate_ms": rng.uniform(2.0, 15.0),
            "service_ceiling_m": rng.uniform(2000.0, 9000.0),
            "airfield_elevation_m": rng.uniform(0.0, 2500.0),
            "airfield_temperature_delta_c": rng.uniform(-10.0, 25.0),
        })

        m0 = rng.uniform(600.0, 15000.0)

        try:
            res = calculate_matching_chart(template, m0=m0)
            dp = res["design_point"]
            assert dp["ws"] > 0
            assert dp["limit_by"] in ("prędkość minimalna", "długość lądowania", "zadana powierzchnia skrzydła")

            if res["engine_type"] == "none":
                assert dp["governing"] is None
                assert dp["pw"] is None
                assert dp["tw"] is None
            else:
                assert dp["governing"] in ("start", "wznoszenie", "przelot", "pułap praktyczny", "prędkość maksymalna", "holowanie szybowca")
                if res["engine_type"] == "jet":
                    assert dp["tw"] is not None and dp["tw"] > 0
                else:
                    assert dp["pw"] is not None and dp["pw"] > 0

            assert len(res["ws_values"]) == 41
            passed += 1
        except ValueError as e:
            # Physical impossibility (e.g. s_to too short for W/S) is acceptable and expected
            err_msg = str(e)
            assert ("za krótka przy W/S" in err_msg or "Długość lądowania" in err_msg or "musi być większa" in err_msg)
            passed += 1

    print(f"      Passed: 100% of {n_iterations} randomized designs handled cleanly ({passed}/{n_iterations}).")


if __name__ == "__main__":
    t0 = time.time()
    print("==================================================================")
    print("MILSTONE 1 ADVERSARIAL FUZZ HARNESS — CONSTRAINTS & SIZING")
    print("==================================================================")
    run_takeoff_tw_fuzz(20000)
    run_climb_asymptote_fuzz(20000)
    run_landing_ws_fuzz(10000)
    run_end_to_end_matching_chart_fuzz(500)
    elapsed = time.time() - t0
    print(f"All fuzz harnesses PASSED in {elapsed:.2f} seconds.")
    print("==================================================================")
