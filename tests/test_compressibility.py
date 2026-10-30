"""
Testy modułu ściśliwości i oporu falowego (Korn-Mason & Lock) w calculations/aerodynamics.py.
"""
import pytest
from calculations.aerodynamics import calculate_compressibility
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS


def test_compressibility_subsonic_ga():
    """Dla małych prędkości (GA, M < 0.3) opór falowy musi być zerowy."""
    res = calculate_compressibility(mach=0.20, cz=0.45, tc=0.15, sweep_deg=0.0, airfoil_name="NACA 23012")
    assert res["delta_cx_wave"] == 0.0
    assert res["drag_divergence_safe"] is True
    assert res["m_dd"] > 0.65
    assert res["m_crit"] > 0.55
    assert res["prandtl_glauert_factor"] >= 1.0
    assert res["is_transonic"] is False


def test_supercritical_profile_advantage():
    """Profil nadkrytyczny NASA SC(2) ma wyższy współczynnik technologiczny kappa_A i wyższe M_dd."""
    res_conv = calculate_compressibility(mach=0.75, cz=0.40, tc=0.12, sweep_deg=20.0, airfoil_name="NACA 64-212")
    res_sc = calculate_compressibility(mach=0.75, cz=0.40, tc=0.12, sweep_deg=20.0, airfoil_name="NASA SC(2)-0412")

    assert res_sc["kappa_a"] > res_conv["kappa_a"]
    assert res_sc["m_dd"] > res_conv["m_dd"]
    assert res_sc["profile_family"] == "Profil nadkrytyczny (supercritical)"


def test_wave_drag_rise_past_mdd():
    """Powyżej liczby Macha rozbieżności oporu (M > M_dd) występuje stromy narost oporu falowego."""
    res_below = calculate_compressibility(mach=0.60, cz=0.40, tc=0.12, sweep_deg=0.0)
    res_divergence = calculate_compressibility(mach=0.75, cz=0.40, tc=0.12, sweep_deg=0.0)
    res_steep = calculate_compressibility(mach=0.85, cz=0.40, tc=0.12, sweep_deg=0.0)

    assert res_below["delta_cx_wave"] == 0.0
    assert res_steep["delta_cx_wave"] > res_divergence["delta_cx_wave"]
    assert res_steep["drag_divergence_safe"] is False


def test_aerodynamics_integration_has_compressibility():
    """calculate_aerodynamics zwraca słownik compressibility z pełnymi danymi."""
    preset = AIRCRAFT_PRESETS["pzl_kos"]
    full_res = run_bipol_project(preset)
    aero = full_res["aerodynamics"]

    assert "compressibility" in aero
    comp = aero["compressibility"]
    assert "mach" in comp
    assert "m_crit" in comp
    assert "m_dd" in comp
    assert "delta_cx_wave" in comp
    assert "drag_divergence_safe" in comp
