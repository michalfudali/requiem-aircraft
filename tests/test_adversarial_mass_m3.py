"""Adversarial Empirical Verification Suite for Milestone M3:
Parametric Component Mass Estimation Engine (`calculations/mass.py`).

Tests boundary conditions, extreme mass scales, mathematical invariants,
and adversarial fuzz testing to assess robustness.
"""
import copy
import math
import random
import sys
import pytest

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


class TestExtremeMassScale:
    """Stress tests boundary conditions from micro-UAV (10 kg) to heavy transport (500,000 kg)."""

    MASS_SCALES = [
        (10.0, "uav", "micro_uav_10kg"),
        (25.0, "uav", "tactical_uav_25kg"),
        (100.0, "uav", "heavy_uav_100kg"),
        (350.0, "glider", "club_glider_350kg"),
        (450.0, "motoglider", "motoglider_450kg"),
        (750.0, "piston_ga", "light_trainer_750kg"),
        (1150.0, "piston_ga", "standard_ga_1150kg"),
        (5000.0, "turboprop_regional", "commuter_5000kg"),
        (18000.0, "jet_business", "business_jet_18000kg"),
        (75000.0, "jet_transport", "narrowbody_75000kg"),
        (250000.0, "jet_transport", "widebody_250000kg"),
        (500000.0, "jet_transport", "heavy_transport_500000kg"),
    ]

    @pytest.mark.parametrize("m0,ac_type,desc", MASS_SCALES)
    def test_statistical_fallback_extreme_scale(self, m0, ac_type, desc):
        """Statistical fallback must produce non-negative masses and conserve mass at all scales."""
        params = {
            "aircraft_type": ac_type,
            "engine_type": "none" if ac_type == "glider" else "prop" if ac_type in ("piston_ga", "motoglider") else "jet",
        }
        res = estimate_component_masses(m0, params, geom=None, flight_envelope=None)

        assert res["m_empty"] > 0.0, f"[{desc}] m_empty must be positive: {res['m_empty']}"
        assert res["m_structure"] > 0.0, f"[{desc}] m_structure must be positive"
        assert res["m_systems"] > 0.0, f"[{desc}] m_systems must be positive"
        if ac_type == "glider":
            assert res["m_propulsion"] == 0.0, f"[{desc}] Glider propulsion must be 0"
        else:
            assert res["m_propulsion"] > 0.0, f"[{desc}] Propulsion group must be positive"

        bd = res["breakdown"]
        # All individual breakdown components must be non-negative
        for k, v in bd.items():
            assert v >= 0.0, f"[{desc}] Component '{k}' is negative: {v}"

        # Strict mass conservation check: sum(breakdown) == m_empty down to rel=1e-12
        total_comp = math.fsum(bd.values())
        rel_diff = abs(total_comp - res["m_empty"]) / res["m_empty"]
        assert rel_diff < 1e-12, f"[{desc}] Mass conservation violated: diff={abs(total_comp - res['m_empty'])}, rel={rel_diff}"

        # Macro groups conservation check
        macro_sum = res["m_structure"] + res["m_propulsion"] + res["m_systems"]
        rel_macro_diff = abs(macro_sum - res["m_empty"]) / res["m_empty"]
        assert rel_macro_diff < 1e-12, f"[{desc}] Macro sum mismatch: rel={rel_macro_diff}"

        # Percentages sum to 100%
        pct_sum = math.fsum(res["percentages"].values())
        assert abs(pct_sum - 100.0) < 1e-6, f"[{desc}] Percentages do not sum to 100%: {pct_sum}"

    @pytest.mark.parametrize("m0,ac_type,desc", MASS_SCALES)
    def test_parametric_raymer_extreme_scale(self, m0, ac_type, desc):
        """Raymer parametric estimation with scaled geometry must produce valid non-negative components."""
        # Scale wing loading and geometry realistically with mass
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
        envelope = {
            "n_pos": 3.8 if m0 < 5000 else 2.5,
            "n_ult": 1.5 * (3.8 if m0 < 5000 else 2.5),
            "q_max_pa": min(25000.0, 1000.0 * (m0 ** 0.15)),
        }

        res = estimate_component_masses(m0, params, geom, envelope)

        assert res["method"] == "raymer_ga_parametric"
        assert res["m_empty"] > 0.0
        bd = res["breakdown"]

        for k, v in bd.items():
            assert v >= 0.0, f"[{desc}] Raymer component '{k}' is negative: {v}"

        # Mass conservation
        total_comp = math.fsum(bd.values())
        rel_diff = abs(total_comp - res["m_empty"]) / res["m_empty"]
        assert rel_diff < 1e-12, f"[{desc}] Raymer mass conservation violated: diff={abs(total_comp - res['m_empty'])}, rel={rel_diff}"

        # Structural, propulsion, systems sum
        macro_sum = res["m_structure"] + res["m_propulsion"] + res["m_systems"]
        rel_macro_diff = abs(macro_sum - res["m_empty"]) / res["m_empty"]
        assert rel_macro_diff < 1e-12, f"[{desc}] Raymer macro sum mismatch: rel={rel_macro_diff}"


class TestMassConservationInvariant100Random:
    """Stress tests mass conservation invariant across 100 random parameter combinations

    spanning all 7 aircraft classes: sum(breakdown) == m_empty within 1e-12.
    """

    def test_100_random_parameter_combinations_invariant(self):
        rng = random.Random(42)  # Fixed seed for determinism

        for trial in range(100):
            ac_class = rng.choice(AIRCRAFT_CLASSES)
            m0 = 10.0 ** rng.uniform(1.0, 5.6)  # 10 kg to ~400,000 kg

            has_geometry = rng.choice([True, False])
            is_glider = ac_class in ("glider", "motoglider") and rng.random() < 0.5

            engine_types = ["none"] if is_glider else ["prop", "turboprop", "jet", "turbofan", "piston"]
            engine_type = rng.choice(engine_types)

            tech = rng.choice(["metallic", "advanced_composites", "composite", "wood", "steel_tube", "unknown"])
            wing_config = rng.choice(["low", "high", "mid", "braced_high"])
            pressurized = rng.choice([True, False])

            params = {
                "aircraft_type": ac_class,
                "engine_type": engine_type,
                "technology": tech,
                "wing_config": wing_config,
                "wing_braced": wing_config == "braced_high",
                "is_pressurized": pressurized,
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
            envelope = None

            if has_geometry:
                ws = rng.uniform(20.0, 500.0)
                s_w = max(0.5, m0 / ws)
                ar = rng.uniform(4.5, 22.0)
                b = math.sqrt(ar * s_w)
                taper = rng.uniform(0.3, 1.0)
                tc = rng.uniform(0.08, 0.20)
                sweep = math.radians(rng.uniform(0.0, 35.0))
                l_f = max(1.5, rng.uniform(0.5, 1.2) * b)
                d_f = max(0.3, rng.uniform(0.05, 0.20) * l_f)

                geom = {
                    "wing": {
                        "S": s_w,
                        "b": b,
                        "AR": ar,
                        "sweep_25": sweep,
                        "taper_ratio": taper,
                        "thickness_ratio": tc,
                    },
                    "horizontal_tail": {
                        "S_h": rng.uniform(0.12, 0.28) * s_w,
                        "AR_h": rng.uniform(3.0, 5.5),
                        "sweep": math.radians(rng.uniform(0.0, 30.0)),
                        "taper_ratio": rng.uniform(0.4, 0.8),
                        "thickness_ratio": rng.uniform(0.09, 0.14),
                        "arm": rng.uniform(0.4, 0.7) * l_f,
                    },
                    "vertical_tail": {
                        "S_v": rng.uniform(0.08, 0.18) * s_w,
                        "AR_v": rng.uniform(1.1, 2.2),
                        "sweep": math.radians(rng.uniform(10.0, 40.0)),
                        "taper_ratio": rng.uniform(0.4, 0.8),
                        "thickness_ratio": rng.uniform(0.09, 0.14),
                        "arm": rng.uniform(0.4, 0.7) * l_f,
                    },
                    "fuselage": {
                        "length": l_f,
                        "diameter": d_f,
                        "S_wet": rng.uniform(0.65, 0.85) * math.pi * d_f * l_f,
                    },
                    "gear": {
                        "length_main_m": rng.uniform(0.3, 2.5),
                        "length_nose_m": rng.uniform(0.2, 2.0),
                    },
                }
                envelope = {
                    "n_pos": rng.uniform(2.5, 6.0),
                    "n_ult": rng.uniform(3.8, 9.0),
                    "q_max_pa": rng.uniform(800.0, 20000.0),
                }

            res = estimate_component_masses(m0, params, geom=geom, flight_envelope=envelope)

            m_empty = res["m_empty"]
            assert m_empty > 0.0, f"Trial {trial}: m_empty <= 0"

            bd = res["breakdown"]
            comp_sum = math.fsum(bd.values())

            # Mass conservation invariant check
            diff = abs(comp_sum - m_empty)
            rel_diff = diff / m_empty
            assert rel_diff < 1e-12, (
                f"Trial {trial} ({ac_class}, m0={m0:.1f}kg, method={res['method']}): "
                f"Mass conservation broken! comp_sum={comp_sum:.12f}, m_empty={m_empty:.12f}, "
                f"diff={diff:.2e}, rel_diff={rel_diff:.2e}"
            )

            # Invariant: Macro groups sum
            macro_sum = res["m_structure"] + res["m_propulsion"] + res["m_systems"]
            macro_diff = abs(macro_sum - m_empty)
            rel_macro_diff = macro_diff / m_empty
            assert rel_macro_diff < 1e-12, (
                f"Trial {trial}: Macro group sum broken! macro_sum={macro_sum:.12f}, "
                f"m_empty={m_empty:.12f}, rel_diff={rel_macro_diff:.2e}"
            )

            # Invariant: Component alias access
            assert bd["m_wing"] == bd["wing"]
            assert bd["m_fuselage"] == bd["fuselage"]
            assert bd["m_tail"] == bd["horizontal_tail"] + bd["vertical_tail"]
            assert bd["m_gear"] == bd["landing_gear"]
            assert bd["m_propulsion"] == bd["propulsion"] + bd["fuel_system"]
            assert bd["m_systems"] == pytest.approx(
                bd["flight_controls"] + bd["avionics"] + bd["electrical"] + bd["furnishings"],
                rel=1e-12,
            )


class TestAdversarialFuzzTesting:
    """Stress tests fuzz inputs: empty dicts, missing geometry keys, None values, unusual string inputs.

    System must not crash with unhandled exceptions and must provide graceful fallback.
    """

    def test_empty_dict_input(self):
        """Calling estimate_component_masses with empty dict must default gracefully."""
        res = estimate_component_masses({})
        assert res["m_empty"] > 0.0
        assert res["method"] == "statistical_fallback"
        assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_none_parameter_dict(self):
        """estimate_component_masses(1000.0, None) must default to statistical fallback."""
        res = estimate_component_masses(1000.0, None)
        assert res["m_empty"] > 0.0
        assert res["method"] == "statistical_fallback"
        assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_missing_geom_keys_fallback(self):
        """Various partial or missing geometry keys must not raise unhandled exceptions."""
        partial_geoms = [
            {},
            {"wing": {}},
            {"wing": {"S": 15.0}},  # Missing tails, fuselage, gear
            {"horizontal_tail": {"S_h": 2.5}},  # Missing wing
            {"vertical_tail": {}},
            {"fuselage": {}},
            {"gear": {}},
            {"wing": {"S": 15.0}, "fuselage": {"length": 7.0}},
        ]
        for idx, g in enumerate(partial_geoms):
            res = estimate_component_masses(1150.0, {"aircraft_type": "piston_ga"}, geom=g)
            assert res["m_empty"] > 0.0
            assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_none_values_in_parameters(self):
        """Parameters containing None for optional/numeric fields must not crash."""
        none_param_cases = [
            {"aircraft_type": None},
            {"engine_type": None},
            {"technology": None},
            {"wing_config": None},
            {"wing_braced": None},
            {"is_pressurized": None},
            {"fuselage_material": None},
            {"fuselage_type": None},
            {"geometry": None},
            {"flight_envelope": None},
            {"wing_area_m2": None},
            {"S": None},
        ]
        for p in none_param_cases:
            res = estimate_component_masses(1150.0, p)
            assert res["m_empty"] > 0.0
            assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_unusual_string_inputs(self):
        """Unknown string inputs for categorical fields must fall back gracefully to defaults."""
        weird_params = {
            "aircraft_type": "hypersonic_interceptor_v99",
            "engine_type": "antimatter_warp_drive",
            "technology": "vibranium_adamantium_matrix",
            "wing_config": "oblique_variable_forward_sweep",
            "fuselage_material": "aerogel_nanotube_composite",
            "fuselage_type": "blended_lifting_body",
            "category": "cs_experimental_alien",
        }
        res = estimate_component_masses(2500.0, weird_params)
        assert res["m_empty"] > 0.0
        assert res["method"] == "statistical_fallback"
        assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_corrupted_nested_geom_dictionaries(self):
        """Nested geometry with empty sub-dicts or missing dimension fields."""
        corrupted_geom = {
            "wing": {"S": 14.0},  # has S, but no AR, sweep, taper, thickness
            "horizontal_tail": {},  # completely empty
            "vertical_tail": {},    # completely empty
            "fuselage": {},         # completely empty
            "gear": {},             # completely empty
        }
        res = estimate_component_masses(1000.0, {"aircraft_type": "piston_ga"}, geom=corrupted_geom)
        assert res["m_empty"] > 0.0
        assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_zero_or_negative_mass_validation(self):
        """Invalid physical boundary inputs (<= 0 mass) must strictly raise ValueError."""
        with pytest.raises(ValueError, match="Aircraft mass"):
            estimate_component_masses(0.0)
        with pytest.raises(ValueError, match="Aircraft mass"):
            estimate_component_masses(-100.0)
        with pytest.raises(ValueError, match="Aircraft mass"):
            estimate_component_masses({"m0": -50.0})
        with pytest.raises(ValueError, match="Aircraft mass"):
            estimate_component_masses(-500.0, "piston_ga")
        with pytest.raises(ValueError, match="Wing area"):
            estimate_component_masses(1000.0, {"wing_area_m2": -5.0})
        with pytest.raises(ValueError, match="Wing area"):
            estimate_component_masses(1000.0, geom={"wing": {"S": 0.0}})
        with pytest.raises(ValueError, match="Wing area"):
            estimate_component_masses(1000.0, geom={"wing": {"S": -15.0}})


class TestDiscoveredFuzzVulnerabilities:
    """Documents and empirically reproduces unhandled exceptions when malformed/None inputs are supplied.

    These test cases prove that when None values are explicitly present in nested dicts or params,
    calculations/mass.py crashes with unhandled TypeError/AttributeError instead of falling back gracefully.
    """

    def test_repro_geom_wing_none_unhandled_type_error(self):
        """Passing geom={'wing': None} crashes with TypeError on line 194 instead of falling back."""
        with pytest.raises(TypeError, match="argument of type 'NoneType' is not iterable"):
            estimate_component_masses(1000.0, geom={"wing": None})

    def test_repro_geom_wing_s_none_unhandled_type_error(self):
        """Passing geom={'wing': {'S': None}} crashes with TypeError on line 195 instead of falling back."""
        with pytest.raises(TypeError, match="float\\(\\) argument must be a string or a real number, not 'NoneType'"):
            estimate_component_masses(1000.0, geom={"wing": {"S": None}})

    def test_repro_geom_ht_none_unhandled_attribute_error(self):
        """Passing geom={'wing': {'S': 15.0}, 'horizontal_tail': None} crashes with AttributeError on line 411."""
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'get'"):
            estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}, "horizontal_tail": None})

    def test_repro_flight_envelope_n_ult_none_unhandled_type_error(self):
        """Passing flight_envelope={'n_ult': None} crashes with TypeError on line 332 instead of defaulting."""
        with pytest.raises(TypeError, match="float\\(\\) argument must be a string or a real number, not 'NoneType'"):
            estimate_component_masses(1000.0, geom={"wing": {"S": 15.0}}, flight_envelope={"n_ult": None})

    def test_repro_params_n_pax_none_unhandled_type_error(self):
        """Passing params={'n_pax': None} crashes with TypeError on line 224/567 instead of defaulting."""
        with pytest.raises(TypeError, match="int\\(\\) argument must be a string, a bytes-like object or a real number, not 'NoneType'"):
            estimate_component_masses(1000.0, {"n_pax": None})

    def test_repro_params_n_crew_none_unhandled_type_error(self):
        """Passing params={'n_crew': None} crashes with TypeError on line 224/568 instead of defaulting."""
        with pytest.raises(TypeError, match="int\\(\\) argument must be a string, a bytes-like object or a real number, not 'NoneType'"):
            estimate_component_masses(1000.0, {"n_crew": None})



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
