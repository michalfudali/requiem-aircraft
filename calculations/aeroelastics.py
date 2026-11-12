"""
Moduł aeroelastyczności, rozbieżności skrętnej i flatteru (BiPOL Requiem).
Zgodny z wytycznymi MEiL PW:
- J. Danilecki: "Konstruowanie samolotów",
- Bisplinghoff, Ashley, Halfman: "Aeroelasticity",
- D. Raymer: "Aircraft Design: A Conceptual Approach" (rozdz. 14.8),
- Wymagania przepisów zdatności JAR 23.629(c) / JAR-VLA 629(b) / JAR 22.629 / JAR 25.629(b)(1) (margines flatteru 1.20 VD).
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
    material = params.get("structure_material") or params.get("technology") or "metal"
    if material in ("composite", "composites", "advanced_composites", "carbon"):
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
    # Skrzydło wspornikowe, teoria pasowa: GJ·θ'' + q·c·e·a·θ = −q·c·e·a·α₀; rozbieżność przy λ·l = π/2,
    # λ² = q·c·e·a/GJ, czyli q_D = π²·GJ / (4·e·c·a·l²) (Bisplinghoff, Ashley, Halfman; Hodges, Pierce).
    q_div_straight = (math.pi ** 2 * GJ) / (4.0 * e_arm * mac * a_w_rad * (l_semi ** 2))
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

    # 3. FLATTER GIĘTNO-SKRĘTNY: przekrój typowy o dwóch stopniach swobody (h, α), aerodynamika
    # quasi-stacjonarna, flatter przy zbiegnięciu się częstości (Hodges, Pierce „Introduction to Structural
    # Dynamics and Aeroelasticity”, rozdz. 5; Bisplinghoff, Ashley, Halfman). Częstości własne z belki
    # wspornikowej o sztywności kesonu: giętna ω_h = 1,875²·√(EI/(m′l⁴)), skrętna ω_α = π/(2l)·√(GJ/I_α).
    E_mod = {"composite": 60.0e9, "composites": 60.0e9, "advanced_composites": 60.0e9, "carbon": 60.0e9, "wood": 10.0e9}.get(material, 72.0e9)
    box_height = 0.9 * tc * mac
    EI = E_mod * 2.0 * (0.60 * mac) * t_skin * (box_height / 2.0) ** 2   # pokrycia kesonu jako pasy
    m_line = m_wing / max(0.5, b)                                       # masa skrzydła na metr rozpiętości
    x_ea, x_cg, r_alpha = 0.40, 0.45, 0.50                              # oś sprężysta, środek masy, promień bezwładności
    section = typical_section_flutter(m_line, mac, GJ, EI, l_semi, a_w_rad, x_ea, x_cg, r_alpha)
    omega_h, omega_alpha, mu_mass = section["omega_h"], section["omega_alpha"], section["mu"]
    v_flutter_ms = section["v_flutter_ms"]
    v_flutter_kmh = v_flutter_ms * 3.6

    # 4. MARGINESY BEZPIECZEŃSTWA WG PRZEPISÓW ZDATNOŚCI (JAR 23.629(c) / JAR 25.629(b)(1))
    v_req_flutter_kmh = 1.20 * v_d_kmh
    v_req_rev_kmh = 1.15 * v_d_kmh

    coalescence = math.isfinite(v_flutter_kmh)
    margin_flutter = round(v_flutter_kmh / max(1.0, v_d_kmh), 2) if coalescence else None
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
        "flutter_speed_kmh": round(v_flutter_kmh, 1) if coalescence else None,
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
        "bending_stiffness_ei": round(EI, 1),
        "flutter_model": {
            "method": ("Przekrój typowy 2 st. swobody, aerodynamika quasi-stacjonarna, flatter przy zbiegnięciu częstości "
                       "(Hodges, Pierce, rozdz. 5). Szacunek wstępny: rzeczywista prędkość flatteru wymaga analizy "
                       "z aerodynamiką niestacjonarną lub badań drgań (JAR 23.629)."),
            "mass_ratio_mu": round(mu_mass, 2),
            "elastic_axis_chord": x_ea, "section_cg_chord": x_cg, "radius_of_gyration": r_alpha,
            "coalescence": coalescence,
        },
        "explanation": {
            "flutter": (
                "Flater to gwałtowne, samowzbudne drgania giętno-skrętne skrzydła pod wpływem sił aerodynamicznych. "
                "Przepisy JAR 23.629(c) wymagają, by prędkość flatteru przewyższała obliczeniową prędkość nurkowania VD o co najmniej 20% (margines 1.20 VD)."
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


def typical_section_flutter(m_line, chord, GJ, EI, l_semi, lift_slope, x_ea=0.40, x_cg=0.45, r_alpha=0.50, rho=RHO0):
    """Prędkość flatteru przekroju typowego (h, α) z aerodynamiką quasi-stacjonarną.

    det[[k_h − mω², L − S_α ω²], [−S_α ω², k_α − L·e − I_α ω²]] = 0, L = q·c·a (siła nośna na radian i metr),
    e — odległość 1/4 cięciwy przed osią sprężystą. Wyróżnik równania na ω² jest kwadratowy względem L;
    flatter występuje przy najmniejszym dodatnim L, dla którego znika (zbiegnięcie częstości).
    """
    b_s = chord / 2.0
    a_ea, x_alpha = (x_ea - 0.5) / 0.5, (x_cg - x_ea) / 0.5
    I_alpha = m_line * (r_alpha * b_s) ** 2
    omega_h = 1.875 ** 2 * math.sqrt(EI / (m_line * l_semi ** 4))
    omega_alpha = math.pi / (2.0 * l_semi) * math.sqrt(GJ / I_alpha)
    k_h, k_a, s_a = m_line * omega_h ** 2, I_alpha * omega_alpha ** 2, m_line * x_alpha * b_s
    e_ac = (0.5 + a_ea) * b_s
    A = m_line * I_alpha - s_a ** 2
    B0, B1 = -(m_line * k_a + I_alpha * k_h), m_line * e_ac + s_a
    C0, C1 = k_h * k_a, -k_h * e_ac
    qa, qb, qc = B1 ** 2, 2.0 * B0 * B1 - 4.0 * A * C1, B0 ** 2 - 4.0 * A * C0
    disc = qb ** 2 - 4.0 * qa * qc
    lifts = [(-qb + sgn * math.sqrt(disc)) / (2.0 * qa) for sgn in (-1.0, 1.0)] if disc >= 0 and qa > 0 else []
    lifts = [lift for lift in lifts if lift > 0]
    v_flutter = math.sqrt(2.0 * min(lifts) / (rho * chord * lift_slope)) if lifts else math.inf
    return dict(v_flutter_ms=v_flutter, omega_h=omega_h, omega_alpha=omega_alpha,
                mu=m_line / (math.pi * rho * b_s ** 2), matrices=(m_line, I_alpha, s_a, k_h, k_a, e_ac))
