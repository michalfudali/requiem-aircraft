"""
Testy jednostkowe modułu aeroelastyczności, rozbieżności i flatteru (calculations/aeroelastics.py).
"""
import pytest
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.aeroelastics import estimate_aeroelastics


def test_aeroelastics_basic_evaluation():
    preset = AIRCRAFT_PRESETS["pzl_kos"]
    res = run_bipol_project(preset)
    aeroel = estimate_aeroelastics(res["geometry"], res["aerodynamics"], res["mass"], res["envelope"], res["params"])

    assert aeroel["status"] == "success"
    assert aeroel["flutter_speed_kmh"] > aeroel["dive_speed_vd_kmh"]
    assert aeroel["divergence_speed_kmh"] > 0.0
    assert aeroel["aileron_reversal_speed_kmh"] is None
    assert aeroel["reversal_safe"] is None
    assert aeroel["certification_compliant"] is None
    assert aeroel["margin_flutter"] > 1.0
    assert aeroel["bending_frequency_hz"] > 0.5
    assert aeroel["torsion_frequency_hz"] > aeroel["bending_frequency_hz"]


def test_sweep_effect_on_divergence():
    """Skos do tyłu zwiększa prędkość rozbieżności w porównaniu ze skrzydłem prostym."""
    geom_straight = {"wing": {"S": 15.0, "b": 10.0, "AR": 6.67, "mac": 1.5, "tc_ratio": 0.12, "sweep_deg": 0.0}}
    geom_swept = {"wing": {"S": 15.0, "b": 10.0, "AR": 6.67, "mac": 1.5, "tc_ratio": 0.12, "sweep_deg": 25.0}}
    aero = {"a_w_rad": 4.8}
    mass = {"m0": 1200.0, "breakdown": {"m_wing": 150.0}}
    envelope = {"speeds": {"v_d_kmh": 350.0}}

    res_straight = estimate_aeroelastics(geom_straight, aero, mass, envelope)
    res_swept = estimate_aeroelastics(geom_swept, aero, mass, envelope)

    assert res_swept["divergence_speed_kmh"] > res_straight["divergence_speed_kmh"]


def test_forward_sweep_reduces_divergence():
    """Skos do przodu (ujemny) obniża prędkość rozbieżności skrętnej."""
    geom_straight = {"wing": {"S": 15.0, "b": 10.0, "AR": 6.67, "mac": 1.5, "tc_ratio": 0.12, "sweep_deg": 0.0}}
    geom_fwd = {"wing": {"S": 15.0, "b": 10.0, "AR": 6.67, "mac": 1.5, "tc_ratio": 0.12, "sweep_deg": -20.0}}
    aero = {"a_w_rad": 4.8}
    mass = {"m0": 1200.0, "breakdown": {"m_wing": 150.0}}
    envelope = {"speeds": {"v_d_kmh": 350.0}}

    res_straight = estimate_aeroelastics(geom_straight, aero, mass, envelope)
    res_fwd = estimate_aeroelastics(geom_fwd, aero, mass, envelope)

    assert res_fwd["divergence_speed_kmh"] < res_straight["divergence_speed_kmh"]


def test_straight_wing_divergence_matches_classical_strip_theory():
    """q_D = π²·GJ/(4·e·c·a·l²) dla prostego skrzydła wspornikowego (wcześniej w mianowniku było 8)."""
    import math
    from calculations.aeroelastics import estimate_aeroelastics
    geom = {'wing': {'S': 12.0, 'b': 10.0, 'AR': 8.33, 'mac': 1.2, 'tc_ratio': 0.12, 'sweep_deg': 0.0}}
    res = estimate_aeroelastics(geom, {'a_w_rad': 5.0}, {'m0': 1000.0, 'breakdown': {'m_wing': 150.0}},
                                {'speeds': {'v_d_kmh': 300.0}}, {'structure_material': 'metal'})
    mac, tc, t_skin = 1.2, 0.12, 0.0012
    area, perimeter = 0.6 * mac * tc * mac, 2 * (0.6 * mac + tc * mac)
    gj = 27e9 * 4 * area ** 2 * t_skin / perimeter
    q_d = math.pi ** 2 * gj / (4 * 0.15 * mac * mac * 5.0 * 5.0 ** 2)
    assert res['divergence_speed_kmh'] == pytest.approx(math.sqrt(2 * q_d / 1.225) * 3.6, rel=1e-3)


def _coalescence_speed_by_sweep(section, chord, lift_slope, rho=1.225):
    """Niezależnie: najmniejsza prędkość, przy której pierwiastki ω² z wyznacznika 2×2 przestają być rzeczywiste."""
    m, ia, sa, kh, ka, e = section['matrices']
    v = 1.0
    while v < 3000.0:
        lift = 0.5 * rho * v * v * chord * lift_slope
        a = m * ia - sa * sa
        b = -(m * (ka - lift * e) + ia * kh) + sa * lift
        c = kh * (ka - lift * e)
        if b * b - 4 * a * c < 0:
            return v
        v += 0.05
    return None


def test_typical_section_flutter_matches_eigenvalue_sweep():
    from calculations.aeroelastics import typical_section_flutter
    section = typical_section_flutter(15.0, 1.5, 1.57e6, 1.02e6, 5.0, 5.0)
    swept = _coalescence_speed_by_sweep(section, 1.5, 5.0)
    assert section['v_flutter_ms'] == pytest.approx(swept, abs=0.1)
    assert 4.0 < section['omega_h'] / (2 * 3.14159) < 8.0 and 30.0 < section['omega_alpha'] / (2 * 3.14159) < 60.0


def test_flutter_speed_rises_when_section_mass_moves_forward():
    """Wyważenie masowe: środek masy przekroju bliżej osi sprężystej podnosi prędkość flatteru."""
    from calculations.aeroelastics import typical_section_flutter
    speeds = [typical_section_flutter(15.0, 1.5, 1.57e6, 1.02e6, 5.0, 5.0, x_cg=x)['v_flutter_ms'] for x in (0.50, 0.45, 0.42)]
    assert speeds[0] < speeds[1] < speeds[2]


def test_presets_have_physically_plausible_flutter_speeds():
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    for name in ('ga_trainer', 'regional_turboprop', 'glider_pw5'):
        aeroel = run_bipol_project(dict(AIRCRAFT_PRESETS[name]))['aeroelastics']
        assert 1.2 < aeroel['margin_flutter'] < 6.0, (name, aeroel['margin_flutter'])  # dawniej nawet 89 V_D
        assert 1.0 < aeroel['bending_frequency_hz'] < 10.0 and aeroel['torsion_frequency_hz'] > aeroel['bending_frequency_hz']


def test_aeroelastics_respects_technology_parameter():
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    res_comp = run_bipol_project({**AIRCRAFT_PRESETS['motoglider_aos'], 'technology': 'composite'})
    res_metal = run_bipol_project({**AIRCRAFT_PRESETS['motoglider_aos'], 'technology': 'metallic'})
    assert 'Kompozyt' in res_comp['aeroelastics']['material']
    assert 'aluminium' in res_metal['aeroelastics']['material']

