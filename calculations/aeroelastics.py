"""
Moduł aeroelastyczności, rozbieżności skrętnej i flatteru (BiPOL Requiem).
Zgodny z wytycznymi MEiL PW:
- J. Danilecki: "Konstruowanie samolotów",
- Bisplinghoff, Ashley, Halfman: "Aeroelasticity",
- D. Raymer: "Aircraft Design: A Conceptual Approach" (rozdz. 14.8),
- Wymagania przepisów zdatności CS-23.629 / CS-25.629 / CS-22.629 (margines flatteru 1.20 VD).
"""
import math
from calculations.atmosphere import RHO0


def estimate_aeroelastics(geom: dict, aero: dict, mass: dict, envelope: dict, params: dict = None) -> dict:
    """
    Szacuje sztywności, prędkość rozbieżności skrętnej (divergence),
    prędkość rewersu lotek (aileron reversal) oraz prędkość flatteru giętno-skrętnego (flutter).
    """
    params = params or {}
    wing = geom.get("wing", {})
    S = float(wing.get("S", 14.0))
    b = float(wing.get("b", 10.0))
    AR = float(wing.get("AR", 8.0))
    mac = float(wing.get("mac", 1.4))
    tc = float(wing.get("tc_ratio", 0.12))
    sweep_deg = float(wing.get("sweep_deg", 0.0))
    sweep_rad = math.radians(sweep_deg)

    # Obliczeniowa prędkość nurkowania VD [m/s]
    env_speeds = envelope.get("speeds", {})
    v_d_kmh = float(env_speeds.get("v_d_kmh", 0.0) or 0.0)
    if v_d_kmh <= 0.0:
        v_c_kmh = float(env_speeds.get("v_c_kmh", 250.0) or 250.0)
        v_d_kmh = 1.25 * v_c_kmh
    v_d_ms = v_d_kmh / 3.6

    # Masa skrzydła
    m_wing = float(mass.get("breakdown", {}).get("m_wing", 0.12 * mass.get("m0", 1000.0)))

    # Nachylenie krzywej siły nośnej profilu / płata [1/rad]
    a_w_rad = float(aero.get("a_w_rad", 4.8))

    # Położenie osi sprężystej (EA) i środka aerodynamicznego (AC)
    e_ratio = 0.15  # ramie e = x_EA - x_AC = 15% cięciwy
    e_arm = e_ratio * mac

    # Przybliżona sztywność skrętna kesonu skrzydła (GJ)
    material = params.get("structure_material", "metal")
    if material in ("composite", "carbon"):
        G_mod = 25.0e9  # Pa
        mat_label = "Kompozyt węglowo-epoksydowy (CFRP)"
    elif material == "wood":
        G_mod = 1.2e9
        mat_label = "Drewno lotnicze / sklejka"
    else:
        G_mod = 27.0e9  # Pa dural 2024-T3
        mat_label = "Stop aluminium (Dural 2024-T3)"

    t_skin = max(0.0008, 0.0012 * math.sqrt(m_wing / 150.0))
    A_m = 0.60 * mac * (tc * mac)
    perimeter = 2.0 * (0.60 * mac + (tc * mac))
    J_torsion = (4.0 * (A_m ** 2) * t_skin) / max(0.01, perimeter)
    GJ = G_mod * J_torsion

    # 1. CIŚNIENIE DYNAMICZNE I PRĘDKOŚĆ ROZBIEŻNOŚCI SKRĘTNEJ (DIVERGENCE)
    l_semi = b / 2.0
    q_div_straight = (math.pi ** 2 * GJ) / (8.0 * e_arm * mac * a_w_rad * (l_semi ** 2))
    q_div_straight = max(100.0, q_div_straight)

    # Wpływ skosu (Diederich & Foss, NACA TN 2761):
    # - Skos dodatni (do tyłu, sweep > 0) odciąża uginające się skrzydło -> q_div rośnie
    # - Skos ujemny (do przodu, sweep < 0) dociąża uginające się skrzydło -> q_div drastycznie maleje!
    aspect_half = l_semi / max(0.2, mac)
    if sweep_deg > 0:
        q_div = q_div_straight * (1.0 + 1.8 * math.sin(sweep_rad))
    elif sweep_deg < 0:
        sin_fwd = math.sin(abs(sweep_rad))
        q_div = q_div_straight / (1.0 + 2.0 * sin_fwd * aspect_half)
    else:
        q_div = q_div_straight

    v_div_ms = math.sqrt(2.0 * q_div / RHO0)
    v_div_kmh = v_div_ms * 3.6

    # 2. PRĘDKOŚĆ REWERSU LOTEK (AILERON REVERSAL SPEED)
    v_rev_ms = 0.82 * v_div_ms
    v_rev_kmh = v_rev_ms * 3.6

    # 3. PRĘDKOŚĆ FLATTERU GIĘTNO-SKRĘTNEGO (THEODORSEN / RAYMER)
    omega_h = 2.0 * math.pi * max(1.5, 3.5 * math.sqrt(10.0 / max(1.0, b)))
    omega_alpha = 2.0 * math.pi * max(4.0, 10.0 * math.sqrt(GJ / max(1.0, 50000.0)))

    b_half = mac / 2.0
    mu_mass = m_wing / max(1.0, math.pi * RHO0 * (b_half ** 2) * b)
    v_flutter_ms = 0.88 * b_half * omega_alpha * math.sqrt(max(1.0, mu_mass)) * (1.0 + 0.15 * (omega_h / max(0.1, omega_alpha)))
    v_flutter_kmh = v_flutter_ms * 3.6

    # 4. MARGINESY BEZPIECZEŃSTWA WG PRZEPISÓW ZDATNOŚCI (CS-23.629 / CS-25.629)
    v_req_flutter_kmh = 1.20 * v_d_kmh
    v_req_rev_kmh = 1.15 * v_d_kmh

    margin_flutter = round(v_flutter_kmh / max(1.0, v_d_kmh), 2)
    margin_divergence = round(v_div_kmh / max(1.0, v_d_kmh), 2)
    margin_reversal = round(v_rev_kmh / max(1.0, v_d_kmh), 2)

    flutter_safe = v_flutter_kmh >= v_req_flutter_kmh
    reversal_safe = v_rev_kmh >= v_req_rev_kmh
    divergence_safe = v_div_kmh >= v_req_flutter_kmh

    return {
        "status": "success",
        "material": mat_label,
        "dive_speed_vd_kmh": round(v_d_kmh, 1),
        "divergence_speed_kmh": round(v_div_kmh, 1),
        "aileron_reversal_speed_kmh": round(v_rev_kmh, 1),
        "flutter_speed_kmh": round(v_flutter_kmh, 1),
        "required_flutter_speed_kmh": round(v_req_flutter_kmh, 1),
        "margin_flutter": margin_flutter,
        "margin_divergence": margin_divergence,
        "margin_reversal": margin_reversal,
        "flutter_safe": flutter_safe,
        "reversal_safe": reversal_safe,
        "divergence_safe": divergence_safe,
        "torsional_stiffness_gj": round(GJ, 1),
        "bending_frequency_hz": round(omega_h / (2.0 * math.pi), 1),
        "torsion_frequency_hz": round(omega_alpha / (2.0 * math.pi), 1),
        "explanation": {
            "flutter": (
                "Flater to gwałtowne, samowzbudne drgania giętno-skrętne skrzydła pod wpływem sił aerodynamicznych. "
                "Przepisy CS-23.629 wymagają, by prędkość flatteru przewyższała obliczeniową prędkość nurkowania VD o co najmniej 20% (margines 1.20 VD)."
            ),
            "reversal": (
                "Rewers lotek to niebezpieczne zjawisko, w którym przy dużej prędkości moment pochylający od wychylenia lotki "
                "skręca całe skrzydło w przeciwną stronę, powodując odwrócenie działania steru (pilot chce przechylić w prawo, a samolot leci w lewo!)."
            ),
            "divergence": (
                "Rozbieżność skrętna (divergence) to utrata stateczności sprężystej skrzydła przy dużej prędkości. "
                "Skos ujemny (do przodu) drastycznie sprzyja rozbieżności, podczas gdy skos dodatni (do tyłu) ją wygasza."
            )
        }
    }
