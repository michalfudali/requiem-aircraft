"""Automated unit and integration test suite for Milestone M3:
Parametric Component Mass Estimation Engine (`calculations/mass.py`).
Traceable to: MEiL PW `Analiza_masowa.pdf`, Raymer Chapter 15, and Audit DEF-MASS-01.
"""
import copy
import math
import pytest

from calculations import run_bipol_project
from calculations.mass import (
    ComponentBreakdown,
    MacroBreakdown,
    calculate_mass_sizing,
    estimate_component_masses,
)
from calculations.presets import AIRCRAFT_PRESETS


@pytest.fixture
def standard_ga_inputs():
    """Authoritative test baseline: Standard GA Trainer preset (Cessna/Koliber class).

    m0 = 1150 kg, S = 16.0 m², AR = 7.5, n_ult = 5.7 (1.5 * 3.8), t/c = 0.15, lambda = 0.65.
    """
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
            "b": math.sqrt(7.5 * 16.0),  # ~10.954 m
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
            "length_main_m": 0.71,  # ~28 inches
            "length_nose_m": 0.51,  # ~20 inches
        },
    }
    flight_envelope = {
        "n_pos": 3.8,
        "n_ult": 5.7,  # 1.5 * 3.8
        "q_max_pa": 1869.0,  # dynamic pressure at 225 km/h at 2500m
    }
    return {
        "m0": 1150.0,
        "params": params,
        "geom": geom,
        "flight_envelope": flight_envelope,
    }


class TestPhysicalSensitivity:
    """Verifies that structural component masses respond strictly and monotonically

    in accordance with underlying flight physics.
    """

    def test_wing_mass_aspect_ratio_sensitivity(self, standard_ga_inputs):
        """Under Raymer GA Class-II equation, wing weight scales as (A / cos^2 Lambda)^0.60.

        Doubling aspect ratio from 6 to 12 must increase wing mass by ratio ~2^0.60 = 1.516.
        """
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        geom_ar6 = copy.deepcopy(geom)
        geom_ar6["wing"]["AR"] = 6.0
        geom_ar6["wing"]["b"] = math.sqrt(6.0 * 16.0)

        geom_ar12 = copy.deepcopy(geom)
        geom_ar12["wing"]["AR"] = 12.0
        geom_ar12["wing"]["b"] = math.sqrt(12.0 * 16.0)

        res_ar6 = estimate_component_masses(
            1150.0, {**params, "aspect_ratio": 6.0}, geom_ar6, envelope
        )
        res_ar12 = estimate_component_masses(
            1150.0, {**params, "aspect_ratio": 12.0}, geom_ar12, envelope
        )

        m_wing_6 = res_ar6["breakdown"]["wing"]
        m_wing_12 = res_ar12["breakdown"]["wing"]

        assert m_wing_12 > m_wing_6, f"Wing mass failed to increase with aspect ratio: {m_wing_12} vs {m_wing_6}"
        ratio = m_wing_12 / m_wing_6
        assert ratio == pytest.approx(2.0 ** 0.60, rel=0.03), f"Aspect ratio exponent differs from 0.60: ratio={ratio}"
        assert res_ar12["percentages"]["wing"] > res_ar6["percentages"]["wing"]

    def test_structural_mass_load_factor_sensitivity(self, standard_ga_inputs):
        """Increasing ultimate load factor n_ult from 3.8 to 6.0 must scale structural masses:

        Wing ~ n_ult^0.49, H-tail ~ n_ult^0.414, V-tail ~ n_ult^0.376, Fuselage ~ n_ult^0.177.
        """
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]

        res_n38 = estimate_component_masses(
            1150.0, params, geom, {"n_ult": 3.8, "q_max_pa": 1869.0}
        )
        res_n60 = estimate_component_masses(
            1150.0, params, geom, {"n_ult": 6.0, "q_max_pa": 1869.0}
        )

        bd38, bd60 = res_n38["breakdown"], res_n60["breakdown"]
        assert bd60["wing"] > bd38["wing"]
        assert bd60["horizontal_tail"] > bd38["horizontal_tail"]
        assert bd60["vertical_tail"] > bd38["vertical_tail"]
        assert bd60["fuselage"] > bd38["fuselage"]

        # Check power law exponents
        assert (bd60["wing"] / bd38["wing"]) == pytest.approx((6.0 / 3.8) ** 0.49, rel=0.03)
        assert (bd60["horizontal_tail"] / bd38["horizontal_tail"]) == pytest.approx((6.0 / 3.8) ** 0.414, rel=0.03)
        assert (bd60["vertical_tail"] / bd38["vertical_tail"]) == pytest.approx((6.0 / 3.8) ** 0.376, rel=0.03)
        assert (bd60["fuselage"] / bd38["fuselage"]) == pytest.approx((6.0 / 3.8) ** 0.177, rel=0.03)

    def test_advanced_composites_technology_factor(self, standard_ga_inputs):
        """Table 15.4 technology correction factors for advanced carbon/epoxy composites:

        Wing 0.85, Tails 0.83, Fuselage 0.90, Gear 0.95.
        """
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        res_metal = estimate_component_masses(
            1150.0, {**params, "technology": "metallic"}, geom, envelope
        )
        res_comp = estimate_component_masses(
            1150.0, {**params, "technology": "advanced_composites"}, geom, envelope
        )

        assert res_comp["breakdown"]["wing"] == pytest.approx(0.85 * res_metal["breakdown"]["wing"], rel=1e-3)
        assert res_comp["breakdown"]["horizontal_tail"] == pytest.approx(0.83 * res_metal["breakdown"]["horizontal_tail"], rel=1e-3)
        assert res_comp["breakdown"]["vertical_tail"] == pytest.approx(0.83 * res_metal["breakdown"]["vertical_tail"], rel=1e-3)
        assert res_comp["breakdown"]["fuselage"] == pytest.approx(0.90 * res_metal["breakdown"]["fuselage"], rel=1e-3)
        assert res_comp["breakdown"]["landing_gear"] == pytest.approx(0.95 * res_metal["breakdown"]["landing_gear"], rel=1e-3)

    def test_braced_wing_factor(self, standard_ga_inputs):
        """Table 15.4 factor: strut-braced wing scales wing structural weight by 0.82."""
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        res_cantilever = estimate_component_masses(
            1150.0, {**params, "wing_braced": False, "wing_config": "low"}, geom, envelope
        )
        res_braced = estimate_component_masses(
            1150.0, {**params, "wing_braced": True, "wing_config": "braced_high"}, geom, envelope
        )

        assert res_braced["breakdown"]["wing"] == pytest.approx(0.82 * res_cantilever["breakdown"]["wing"], rel=1e-3)
        assert res_braced["breakdown"]["fuselage"] == pytest.approx(res_cantilever["breakdown"]["fuselage"], rel=1e-3)

    def test_airfoil_thickness_sensitivity(self, standard_ga_inputs):
        """Wing mass scales inversely with thickness ratio: (100 * t/c)^-0.30."""
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        geom_thin = copy.deepcopy(geom)
        geom_thin["wing"]["thickness_ratio"] = 0.12

        geom_thick = copy.deepcopy(geom)
        geom_thick["wing"]["thickness_ratio"] = 0.18

        res_thin = estimate_component_masses(1150.0, params, geom_thin, envelope)
        res_thick = estimate_component_masses(1150.0, params, geom_thick, envelope)

        assert res_thick["breakdown"]["wing"] < res_thin["breakdown"]["wing"]
        assert (res_thick["breakdown"]["wing"] / res_thin["breakdown"]["wing"]) == pytest.approx(
            (0.18 / 0.12) ** -0.30, rel=0.02
        )

    def test_wing_sweep_sensitivity(self, standard_ga_inputs):
        """Wing sweep adds structural mass due to increased torsional coupling and structural semi-span."""
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        geom_unswept = copy.deepcopy(geom)
        geom_unswept["wing"]["sweep_25"] = 0.0

        geom_swept = copy.deepcopy(geom)
        geom_swept["wing"]["sweep_25"] = math.radians(25.0)

        res_unswept = estimate_component_masses(1150.0, params, geom_unswept, envelope)
        res_swept = estimate_component_masses(1150.0, params, geom_swept, envelope)

        assert res_swept["breakdown"]["wing"] > res_unswept["breakdown"]["wing"]


class TestNumericalVectors:
    """Verifies numerical test vectors against analytical evaluations and real aircraft baselines."""

    def test_standard_ga_trainer_exact_numerical_vector(self, standard_ga_inputs):
        """Benchmark 1: Standard GA Trainer (m0=1150 kg, S=16 m2, AR=7.5, n_ult=5.7)."""
        res = estimate_component_masses(
            standard_ga_inputs["m0"],
            standard_ga_inputs["params"],
            standard_ga_inputs["geom"],
            standard_ga_inputs["flight_envelope"],
        )
        bd = res["breakdown"]

        assert bd["wing"] == pytest.approx(134.60, abs=3.0)
        assert bd["horizontal_tail"] == pytest.approx(13.44, abs=1.0)
        assert bd["vertical_tail"] == pytest.approx(7.66, abs=0.8)
        assert bd["fuselage"] == pytest.approx(86.46, abs=3.0)
        assert bd["landing_gear"] == pytest.approx(89.68, abs=3.0)
        assert bd["propulsion"] == pytest.approx(210.73, abs=5.0)
        assert bd["fuel_system"] == pytest.approx(16.20, abs=1.5)
        assert bd["flight_controls"] == pytest.approx(16.70, abs=1.5)
        assert bd["avionics"] == pytest.approx(36.94, abs=2.0)
        assert bd["electrical"] == pytest.approx(64.73, abs=3.0)
        assert bd["furnishings"] == pytest.approx(37.45, abs=2.0)

        assert res["m_empty"] == pytest.approx(715.73, abs=15.0)
        assert 0.58 <= (res["m_empty"] / 1150.0) <= 0.66

    def test_unpowered_glider_mass_vector(self):
        """Unpowered glider boundary test: propulsion and fuel systems must be exactly zero."""
        glider_params = {
            "aircraft_type": "glider",
            "engine_type": "none",
            "wing_area_m2": 10.0,
            "aspect_ratio": 18.0,
            "n_pax": 0,
            "n_crew": 1,
            "m_fuel": 0.0,
        }
        res = estimate_component_masses(350.0, glider_params)
        assert res["breakdown"]["propulsion"] == 0.0
        assert res["breakdown"]["fuel_system"] == 0.0
        assert res["percentages"]["propulsion"] == 0.0
        assert res["percentages"]["fuel_system"] == 0.0
        assert res["m_propulsion"] == 0.0
        assert math.isclose(res["m_structure"] + res["m_systems"], res["m_empty"], rel_tol=1e-9)

    def test_twin_engine_installation_scaling(self, standard_ga_inputs):
        """Twin-engine installation scales installed engine group weight by N_en."""
        p_single = {**standard_ga_inputs["params"], "n_engines": 1, "engine_dry_weight_lb": 250.0}
        p_twin = {**standard_ga_inputs["params"], "n_engines": 2, "engine_dry_weight_lb": 250.0}

        res_single = estimate_component_masses(
            1150.0, p_single, standard_ga_inputs["geom"], standard_ga_inputs["flight_envelope"]
        )
        res_twin = estimate_component_masses(
            1150.0, p_twin, standard_ga_inputs["geom"], standard_ga_inputs["flight_envelope"]
        )

        assert res_twin["breakdown"]["propulsion"] == pytest.approx(2.0 * res_single["breakdown"]["propulsion"], rel=1e-3)
        assert res_twin["breakdown"]["fuel_system"] > res_single["breakdown"]["fuel_system"]

    def test_cessna_172_empty_weight_validation(self):
        """Real aircraft validation: Cessna 172 empty weight prediction within 5% of 744 kg."""
        c172_params = {
            "aircraft_type": "piston_ga",
            "category": "cs23_level2",
            "engine_type": "prop",
            "engine_dry_weight_lb": 275.0,  # Lycoming O-320
            "m_fuel": 140.0,
            "fuel_capacity_gal": 56.0,  # 56 US gal standard long-range tanks
            "integral_tank_ratio": 0.0,  # Non-integral bay tanks
            "n_pax": 3,
            "n_crew": 1,
            "wing_braced": True,
            "wing_config": "braced_high",
            "technology": "metallic",
            "m_avionics_uninstalled_lb": 36.7,
        }
        c172_geom = {
            "wing": {
                "S": 16.2,
                "b": 11.0,
                "AR": 7.32,
                "sweep_25": 0.0,
                "taper_ratio": 0.69,
                "thickness_ratio": 0.12,
            },
            "horizontal_tail": {
                "S_h": 2.0,
                "AR_h": 4.0,
                "sweep": 0.0,
                "taper_ratio": 0.60,
                "thickness_ratio": 0.12,
                "arm": 4.55,
            },
            "vertical_tail": {
                "S_v": 1.5,
                "AR_v": 1.5,
                "sweep": math.radians(25.0),
                "taper_ratio": 0.60,
                "thickness_ratio": 0.12,
                "arm": 4.55,
            },
            "fuselage": {
                "length": 8.28,
                "diameter": 1.25,
                "S_wet": 0.78 * math.pi * 1.25 * 8.28,
            },
            "gear": {
                "length_main_m": 0.808,
                "length_nose_m": 0.668,
            },
        }
        c172_envelope = {
            "n_pos": 3.8,
            "n_ult": 5.7,
            "q_max_pa": 2250.0,
        }
        res = estimate_component_masses(1111.0, c172_params, c172_geom, c172_envelope)
        m_empty_pred = res["m_empty"]
        # Real Cessna 172 empty weight is ~744 kg; prediction must be within 5%
        assert 744.0 * 0.95 <= m_empty_pred <= 744.0 * 1.05


class TestBackwardCompatibility:
    """Verifies that legacy caller contracts and invariants are 100% preserved."""

    def test_estimate_component_masses_interface_contract(self, standard_ga_inputs):
        """Verifies schema conformance matching PROJECT.md Section 6 interface contract."""
        res = estimate_component_masses(
            standard_ga_inputs["m0"],
            standard_ga_inputs["params"],
            standard_ga_inputs["geom"],
            standard_ga_inputs["flight_envelope"],
        )
        for key in ["m_empty", "m_structure", "m_propulsion", "m_systems", "breakdown", "percentages", "method"]:
            assert key in res

        expected_components = {
            "wing", "fuselage", "horizontal_tail", "vertical_tail", "landing_gear",
            "propulsion", "fuel_system", "flight_controls", "avionics", "electrical", "furnishings",
        }
        assert set(res["breakdown"].keys()) == expected_components
        assert set(res["percentages"].keys()) == expected_components
        assert sum(res["percentages"].values()) == pytest.approx(100.0, abs=0.01)
        assert res["method"] in ("raymer_ga_parametric", "statistical_fallback")

        # Alias access check
        assert res["breakdown"]["m_wing"] == res["breakdown"]["wing"]
        assert res["breakdown"]["m_fuselage"] == res["breakdown"]["fuselage"]
        assert res["breakdown"]["m_tail"] == res["breakdown"]["horizontal_tail"] + res["breakdown"]["vertical_tail"]
        assert res["breakdown"]["m_gear"] == res["breakdown"]["landing_gear"]
        assert res["breakdown"]["m_propulsion"] == res["breakdown"]["propulsion"] + res["breakdown"]["fuel_system"]
        assert res["breakdown"]["m_systems"] == pytest.approx(
            res["breakdown"]["flight_controls"] + res["breakdown"]["avionics"] +
            res["breakdown"]["electrical"] + res["breakdown"]["furnishings"]
        )

    def test_legacy_sizing_breakdown_invariant(self, standard_ga_inputs):
        """In calculate_mass_sizing, legacy macro keys must exist and sum to m_empty within 1e-12."""
        result = calculate_mass_sizing(standard_ga_inputs["params"])
        bd = result["breakdown"]
        legacy_keys = {"m_wing", "m_fuselage", "m_tail", "m_gear", "m_propulsion", "m_systems"}
        assert legacy_keys.issubset(set(bd.keys()))
        assert math.fsum(bd.values()) == pytest.approx(result["m_empty"], rel=1e-12)

    def test_legacy_string_signature_polymorphism(self):
        """Calling estimate_component_masses(m_empty, ac_type) succeeds and preserves mass."""
        res = estimate_component_masses(600.0, "piston_ga")
        assert res["method"] == "statistical_fallback"
        assert res["m_empty"] == pytest.approx(600.0, rel=1e-12)
        assert "wing" in res["breakdown"]
        assert "m_wing" in res["breakdown"]

    @pytest.mark.parametrize("preset_name", AIRCRAFT_PRESETS.keys())
    def test_all_presets_parametric_mass_execution(self, preset_name):
        """Every preset executes through run_bipol_project and maintains valid mass breakdown."""
        p = AIRCRAFT_PRESETS[preset_name]
        r = run_bipol_project(p)
        assert "mass" in r
        assert "breakdown" in r["mass"]
        assert r["mass"]["m_empty"] > 0
        assert r["mass"]["m0"] > r["mass"]["m_empty"]
        assert math.fsum(r["mass"]["breakdown"].values()) == pytest.approx(r["mass"]["m_empty"], rel=1e-12)

    def test_balance_cg_coupling_with_parametric_mass(self):
        """Full end-to-end integration: run_bipol_project computes stable balance with parametric mass."""
        design = run_bipol_project(AIRCRAFT_PRESETS["ga_trainer"])
        assert "balance" in design
        bal = design["balance"]
        assert "cg_range" in bal
        assert "stability" in bal
        assert 5.0 <= bal["stability"]["static_margin_aft_pct"] <= 35.0


class TestEdgeCases:
    """Verifies robust boundary handling, guards, and fallback conditions."""

    def test_missing_geometry_graceful_fallback(self):
        """When geometry is absent, estimate_component_masses falls back gracefully."""
        res = estimate_component_masses(1150.0, {"aircraft_type": "piston_ga"}, geom=None, flight_envelope=None)
        assert res["method"] == "statistical_fallback"
        assert res["m_empty"] > 0
        assert res["breakdown"]["wing"] > 0
        assert res["breakdown"]["fuselage"] > 0
        assert math.fsum(res["breakdown"].values()) == pytest.approx(res["m_empty"], rel=1e-12)

    def test_uav_zero_furnishings(self):
        """Unmanned aircraft (UAV) must have exactly zero interior furnishings."""
        res = estimate_component_masses(150.0, {"aircraft_type": "uav", "n_pax": 0, "n_crew": 0})
        assert res["breakdown"]["furnishings"] == 0.0

    def test_pressurization_weight_penalty(self, standard_ga_inputs):
        """Cabin pressurization adds structural penalty to fuselage mass."""
        params = standard_ga_inputs["params"]
        geom = standard_ga_inputs["geom"]
        envelope = standard_ga_inputs["flight_envelope"]

        res_unpress = estimate_component_masses(1150.0, {**params, "is_pressurized": False}, geom, envelope)
        res_press = estimate_component_masses(
            1150.0, {**params, "is_pressurized": True, "cabin_pressure_diff_psi": 8.0}, geom, envelope
        )
        assert res_press["breakdown"]["fuselage"] > res_unpress["breakdown"]["fuselage"]

    def test_invalid_inputs_raise_value_error(self, standard_ga_inputs):
        """Non-positive mass or wing area must raise ValueError."""
        with pytest.raises(ValueError):
            estimate_component_masses(0.0, standard_ga_inputs["params"])
        with pytest.raises(ValueError):
            estimate_component_masses(-500.0, standard_ga_inputs["params"])
        with pytest.raises(ValueError):
            estimate_component_masses(1150.0, {**standard_ga_inputs["params"], "wing_area_m2": -10.0})

    def test_strict_mass_conservation_precision(self, standard_ga_inputs):
        """Sum of component masses strictly equals empty mass down to 1e-12."""
        res = estimate_component_masses(
            standard_ga_inputs["m0"],
            standard_ga_inputs["params"],
            standard_ga_inputs["geom"],
            standard_ga_inputs["flight_envelope"],
        )
        sum_components = math.fsum(res["breakdown"].values())
        assert sum_components == pytest.approx(res["m_empty"], rel=1e-12)
        assert (res["m_structure"] + res["m_propulsion"] + res["m_systems"]) == pytest.approx(res["m_empty"], rel=1e-12)
