"""
Testy jednostkowe modułu akustyki i hałasu ICAO Annex 16 / CS-36 (calculations/acoustics.py).
"""
import pytest
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.acoustics import estimate_aircraft_noise


def test_glider_noise_is_minimal():
    preset = AIRCRAFT_PRESETS["glider_pw5"]
    res = run_bipol_project(preset)
    ac = estimate_aircraft_noise(res["params"], res["sizing"], res["performance"], res["geometry"], res["mass"])

    assert ac["status"] == "success"
    assert ac["noise_flyover"] < 55.0
    assert ac["compliant"] is True
    assert ac["propeller_tip_mach"] is None


def test_propeller_aircraft_noise_and_tip_mach():
    preset = AIRCRAFT_PRESETS["pzl_kos"]
    res = run_bipol_project(preset)
    ac = estimate_aircraft_noise(res["params"], res["sizing"], res["performance"], res["geometry"], res["mass"])

    assert ac["status"] == "success"
    assert ac["metric_unit"] == "dBA"
    assert ac["noise_flyover"] > 50.0
    assert ac["limit_flyover"] >= 68.0
    assert ac["propeller_tip_mach"] is not None
    assert ac["propeller_tip_mach"] > 0.40


def test_jet_aircraft_noise_and_bpr():
    preset = AIRCRAFT_PRESETS["vlj_jet"]
    res = run_bipol_project(preset)
    ac = estimate_aircraft_noise(res["params"], res["sizing"], res["performance"], res["geometry"], res["mass"])

    assert ac["status"] == "success"
    assert ac["metric_unit"] == "EPNdB"
    assert "Rozdział 14" in ac["icao_standard"]
    assert ac["bypass_ratio"] is not None
