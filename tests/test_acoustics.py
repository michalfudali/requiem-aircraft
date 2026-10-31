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


def test_chapter10_limits_follow_annex16():
    """ICAO Załącznik 16, t. I, 10.4: a) 76 dB(A) do 600 kg → 88 dB(A) przy 1400 kg; b) 70 → 85 dB(A) (570–1500 kg)."""
    from calculations.acoustics import chapter10_limit
    assert chapter10_limit(500, False) == 76.0 and chapter10_limit(1400, False) == 88.0 and chapter10_limit(5000, False) == 88.0
    assert chapter10_limit(1000, False) == pytest.approx(83.23, abs=0.01)  # 83,23 + 32,67·log(M/1000)
    assert chapter10_limit(570, True) == 70.0 and chapter10_limit(1500, True) == 85.0
    assert chapter10_limit(800, True) < chapter10_limit(1200, True)


def test_chapter14_limits_follow_annex16():
    """Rozdz. 14.4.1: boczny 88,6–94, przelot 80,6–89 (−4 EPNdB na połowienie masy), podejście 93,1–98 EPNdB."""
    from calculations.acoustics import chapter14_limits
    small, mid = chapter14_limits(1500), chapter14_limits(8618)
    assert small['lateral'] == 88.6 and small['approach'] == 93.1 and small['flyover'] == pytest.approx(80.57, abs=0.01)
    assert mid == {'lateral': 94.0, 'flyover': 89.0, 'approach': 98.0}
    assert chapter14_limits(400000)['lateral'] == 103.0 and chapter14_limits(385000, 4)['flyover'] == 106.0
    assert chapter14_limits(4309)['flyover'] == pytest.approx(85.0, abs=0.01)  # połowa 8618 kg → 4 EPNdB mniej


def test_noise_rules_outside_chapter10_are_not_applied():
    for name in ('regional_turboprop', 'f6f_hellcat'):
        res = run_bipol_project(dict(AIRCRAFT_PRESETS[name]))
        assert res['acoustics']['limit_flyover'] is None
        assert all(c['id'] != 'noise_compliance_check' for c in res['engineering_audit']['checks'])
    jet = run_bipol_project(dict(AIRCRAFT_PRESETS['vlj_jet']))['acoustics']
    assert jet['cumulative_margin_epndb'] == pytest.approx(sum(jet['margins_epndb'].values()), abs=0.15)
