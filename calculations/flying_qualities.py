"""
Moduł analizy dynamiki lotu i kryteriów oceny własności lotnych (Flying Qualities)
zgodnie z programem przedmiotu BIPOL I (MEiL Politechniki Warszawskiej),
materiałami wykładowymi (okBIPOL_1_handout_11_1.pdf oraz 11_2.pdf),
normami wojskowymi MIL-STD-1797 oraz przepisami certyfikacyjnymi CS-23.181 / CS-25.181.

Główne wyznaczane parametry i kryteria:
1. Ruch krótkookresowy (Short Period):
   - Częstość drgań nietłumionych omega_n_sp [rad/s]
   - Współczynnik tłumienia zeta_sp [-]
   - Przyspieszenie normalne na jednostkę kąta natarcia n_z_alpha [g/rad]
   - Parametr oczekiwanej sterowności CAP = omega_n_sp^2 / n_z_alpha [rad/s^2/g]
   - Poziomy akceptowalności (Level 1, 2, 3) dla faz lotu A, B, C
2. Fugoida (Phugoid / ruch długookresowy):
   - Częstość omega_n_ph [rad/s] i okres T_ph [s]
   - Współczynnik tłumienia zeta_ph [-] (Level 1: zeta_ph >= 0.04)
3. Ruch przechylania (Roll Mode):
   - Stała czasowa przechylania T_R = -1/L_p [s] (Level 1: T_R <= 1.0 - 1.4 s)
   - Czas osiągnięcia kąta przechylenia 60 deg (lub 30 deg w fazie C)
4. Stateczność spiralna (Spiral Mode):
   - Wartość własna lambda_s, czas podwojenia T_2 [s] oraz stała czasowa T_S [s]
   - Wymóg minimalnego czasu podwojenia (Faza B: T_2 >= 20 s / T_S >= 28.9 s)
5. Oscylacje holendrowania (Dutch Roll):
   - Częstość omega_n_dr [rad/s] i współczynnik tłumienia zeta_dr [-]
   - Kryterium tłumienia JAR/CS-23: -xi/eta >= 0.0523 (tłumienie do 1/10 amplitudy w <= 7 cyklach)
"""

import math
from calculations.atmosphere import G0, isa_atmosphere


def evaluate_flying_qualities(params: dict, geom: dict, aero: dict, mass: dict, balance: dict, perf: dict) -> dict:
    """
    Wyznacza charakterystyki dynamiczne i ocenia własności lotne (Flying Qualities)
    dla samolotu w przelocie według kryteriów BIPOL I (Handout 11_1 i 11_2).
    """
    # 1. Warunki lotu i gęstość powietrza
    h_m = float(params.get("cruise_altitude_m", 0.0))
    v_kmh = float(params.get("cruise_speed_kmh", 250.0))
    v_ms = max(15.0, v_kmh / 3.6)
    
    # Parametry atmosfery
    atm = isa_atmosphere(h_m)
    rho = atm["rho"]
    a_sound = atm["a"]
    mach = v_ms / max(100.0, a_sound)
    q_inf = 0.5 * rho * v_ms ** 2

    m0 = max(10.0, float(mass.get("m0", 1000.0)))
    weight_n = m0 * G0

    # 2. Geometria
    wing = geom.get("wing", {})
    S = max(0.1, float(wing.get("S", 15.0)))
    b = max(0.5, float(wing.get("b", 10.0)))
    AR = max(1.0, float(wing.get("AR", 7.0)))
    mac = max(0.1, float(wing.get("mac", 1.5)))
    sweep_deg = float(params.get("sweep_quarter_deg", params.get("sweep_le_deg", 0.0)))
    dihedral_deg = float(params.get("dihedral_deg", 3.0))

    fus = geom.get("fuselage", {})
    l_fus = max(1.0, float(fus.get("length", 8.0)))
    d_fus = max(0.3, float(fus.get("diameter", 1.2)))

    ht = geom.get("horizontal_tail", {})
    S_h = float(ht.get("S_h", 0.2 * S))
    l_h = float(ht.get("l_h", 0.45 * l_fus))
    AR_h = float(ht.get("AR_h", 4.0))

    vt = geom.get("vertical_tail", {})
    S_v = float(vt.get("S_v", 0.12 * S))
    l_v = float(vt.get("l_v", 0.45 * l_fus))
    AR_v = float(vt.get("AR_v", 1.5))

    # Objętościowe współczynniki usterzeń (Handout 6)
    vh = (S_h * l_h) / (S * mac)
    vv = (S_v * l_v) / (S * b)

    # 3. Aerodynamika
    # Pochodne siły nośnej płata i usterzeń (wg Helmbolda / Diedericha)
    beta_comp = math.sqrt(max(0.01, 1.0 - mach ** 2))
    a_w = float(aero.get("cl_alpha", 2.0 * math.pi * AR / (2.0 + math.sqrt(4.0 + (AR * beta_comp) ** 2))))
    a_h = 2.0 * math.pi * AR_h / (2.0 + math.sqrt(4.0 + (AR_h * beta_comp) ** 2))
    a_v = 2.0 * math.pi * AR_v / (2.0 + math.sqrt(4.0 + (AR_v * beta_comp) ** 2))

    # Kąt natarcia i współczynnik siły nośnej w przelocie
    cz_cruise = weight_n / (q_inf * S)
    cd_cruise = float(aero.get("cx0_clean", 0.025)) + float(aero.get("k_clean", 0.05)) * (cz_cruise ** 2)
    ld_cruise = cz_cruise / max(1e-4, cd_cruise)

    # 4. Masowe momenty bezwładności (promienie bezwładności wg Raymer / Roskam)
    ac_type = params.get("aircraft_type", "piston_ga")
    if "glider" in ac_type or params.get("engine_type") == "none":
        rx, ry, rz = 0.32 * b, 0.24 * l_fus, 0.36 * math.sqrt(b**2 + l_fus**2)
    elif "twin" in ac_type or "regional" in ac_type or params.get("n_engines", 1) > 1:
        rx, ry, rz = 0.28 * b, 0.34 * l_fus, 0.40 * math.sqrt(b**2 + l_fus**2)
    elif "jet" in ac_type or "business" in ac_type:
        rx, ry, rz = 0.26 * b, 0.36 * l_fus, 0.42 * math.sqrt(b**2 + l_fus**2)
    else:  # jednosilnikowy tłokowy GA
        rx, ry, rz = 0.24 * b, 0.36 * l_fus, 0.38 * math.sqrt(b**2 + l_fus**2)

    I_xx = m0 * (rx ** 2)
    I_yy = m0 * (ry ** 2)
    I_zz = m0 * (rz ** 2)

    # 5. Zapas stateczności podłużnej K_n (z modułu balance)
    stab_info = balance.get("stability", {})
    kn_pct = float(stab_info.get("static_margin_aft_pct", 10.0))
    kn = kn_pct / 100.0  # (x_N - x_CG) / MAC

    # -------------------------------------------------------------
    # 6. Ruch krótkookresowy (Short Period) & CAP (Handout 11_1)
    # -------------------------------------------------------------
    # Cm_alpha = -a_w * K_n
    cm_alpha = -a_w * kn

    # Tłumienie pochylenia C_mq i C_m_alphadot
    eta_h = 0.90
    de_da = 2.0 * a_w / (math.pi * AR)  # gradient znoszenia strumienia za skrzydłem
    cm_q = -2.0 * eta_h * vh * (l_h / mac) * a_h
    cm_alphadot = -2.0 * eta_h * vh * (l_h / mac) * a_h * de_da

    # Częstość nietłumiona omega_n_sp [rad/s]
    # Wzór: omega_n_sp^2 = (-C_m_alpha * q * S * mac) / I_yy
    omega_n_sq = max(1e-4, (-cm_alpha * q_inf * S * mac) / I_yy)
    omega_n_sp = math.sqrt(omega_n_sq)

    # Współczynnik tłumienia drgań krótkookresowych zeta_sp [-]
    # 2 * zeta_sp * omega_n_sp = - (q * S * mac^2 / (2 * V * I_yy)) * (C_mq + C_m_alphadot) + (rho * V * S * a_w) / (2 * m0)
    damping_tail = - (q_inf * S * (mac ** 2) / (2.0 * v_ms * I_yy)) * (cm_q + cm_alphadot)
    damping_wing = (rho * v_ms * S * a_w) / (2.0 * m0)
    zeta_sp = max(0.01, (damping_tail + damping_wing) / (2.0 * omega_n_sp))

    # Częstość tłumiona i czas stłumienia do połowy amplitudy (Handout 11_1, slajd 2 i 4)
    xi_sp = -zeta_sp * omega_n_sp  # część rzeczywista wartości własnej
    eta_sp = omega_n_sp * math.sqrt(max(0.001, abs(1.0 - zeta_sp ** 2))) if zeta_sp < 1.0 else 0.0
    t_half_sp = math.log(2.0) / abs(xi_sp) if xi_sp < 0 else math.inf

    # Przyspieszenie normalne na jednostkę kąta natarcia n_z_alpha [g/rad] (slajd 3 i 5)
    # n_z_alpha = (q * S * a_w) / (m0 * G0)
    n_z_alpha = (q_inf * S * a_w) / (m0 * G0)

    # Parametr oczekiwanej sterowności CAP (Control Anticipation Parameter) [rad/s^2 / g]
    # CAP = omega_n_sp^2 / n_z_alpha = (K_n * mac * m0 * G0) / I_yy
    cap = omega_n_sq / max(0.1, n_z_alpha)

    # Ocena poziomów akceptowalności CAP i tłumienia krótkookresowego (Faza B - Przelot, Handout 11_1)
    # Level 1: 0.085 <= CAP <= 3.6  oraz  0.30 <= zeta_sp <= 2.00
    # Level 2: 0.038 <= CAP <= 10.0 oraz  0.20 <= zeta_sp <= 2.00
    # Level 3: CAP >= 0.02          oraz  zeta_sp >= 0.10
    if (0.085 <= cap <= 3.6) and (0.30 <= zeta_sp <= 2.00):
        cap_level = 1
        cap_comment = "Poziom 1 (Satisfactory): optymalna zwinność i precyzja pilotażu bez tendencji do PIO."
    elif (0.038 <= cap <= 10.0) and (0.20 <= zeta_sp <= 2.00):
        cap_level = 2
        cap_comment = "Poziom 2 (Acceptable): właściwości akceptowalne, nieco obniżony komfort lub wrażliwość sterowania."
    elif cap >= 0.02 and zeta_sp >= 0.10:
        cap_level = 3
        cap_comment = "Poziom 3 (Controllable): sterowalny, lecz wymaga wzmożonej uwagi pilota (Poor)."
    else:
        cap_level = 4
        cap_comment = "Nieakceptowalny: groźba oscylacji wzbudzanych przez pilota (PIO) lub powolna reakcja na drążek."

    # -------------------------------------------------------------
    # 7. Fugoida (Phugoid / ruch długookresowy) (Handout 11_1 slajd 3-4)
    # -------------------------------------------------------------
    # Przybliżenie Lanchestera
    omega_n_ph = math.sqrt(2.0) * G0 / v_ms
    t_period_ph = 2.0 * math.pi / max(1e-4, omega_n_ph)
    zeta_ph = 1.0 / (math.sqrt(2.0) * max(1.0, ld_cruise))

    # Level 1: zeta_ph >= 0.04; Level 2: zeta_ph >= 0.00; Level 3: T >= 55 s jeśli niestabilny
    if zeta_ph >= 0.04:
        phugoid_level = 1
    elif zeta_ph >= 0.00:
        phugoid_level = 2
    elif t_period_ph >= 55.0:
        phugoid_level = 3
    else:
        phugoid_level = 4

    # -------------------------------------------------------------
    # 8. Ruch przechylania (Roll Mode) (Handout 11_2 slajd 2-3)
    # -------------------------------------------------------------
    # Pochodna tłumienia przechylania C_lp (Roskam / Raymer)
    taper = float(params.get("taper_ratio", 0.6))
    c_lp = - (a_w / 12.0) * ((1.0 + 3.0 * taper) / (1.0 + taper))
    l_p = (q_inf * S * (b ** 2) / (2.0 * v_ms * I_xx)) * c_lp

    # Stała czasowa przechylania T_R = -1/L_p [s]
    t_roll = -1.0 / l_p if l_p < -1e-6 else 10.0

    # Skuteczność lotek C_l_delta_a i czas wykonania przechylenia 60 deg (lub 30 deg)
    c_l_delta_a = 0.18  # typowa wartość dla lotek o cięciwie 22% i rozpiętości 30% b
    delta_a_rad = math.radians(20.0)  # pełne wychylenie lotek
    p_steady = - (c_l_delta_a * delta_a_rad / c_lp) * (2.0 * v_ms / b)

    # Obliczenie czasu do przechylenia o 60 deg (pi/3 rad) metodą Newtona
    target_bank_rad = math.radians(60.0)
    # phi(t) = p_steady * [t - t_roll * (1 - exp(-t / t_roll))]
    t_bank_60 = 0.5
    for _ in range(8):
        f_val = p_steady * (t_bank_60 - t_roll * (1.0 - math.exp(-t_bank_60 / t_roll))) - target_bank_rad
        df_val = p_steady * (1.0 - math.exp(-t_bank_60 / t_roll))
        if abs(df_val) < 1e-6:
            break
        t_bank_60 -= f_val / df_val
        t_bank_60 = max(0.1, t_bank_60)

    # Wymóg Handout 11_2 Slajd 3: Klasa I Faza B: 60 deg w 1.7 s (Level 1), 2.5 s (Level 2), 3.4 s (Level 3)
    if t_roll <= 1.4 and t_bank_60 <= 1.7:
        roll_level = 1
    elif t_roll <= 3.0 and t_bank_60 <= 2.5:
        roll_level = 2
    elif t_roll <= 10.0 and t_bank_60 <= 3.4:
        roll_level = 3
    else:
        roll_level = 4

    # -------------------------------------------------------------
    # 9. Oscylacje holendrowania (Dutch Roll) (Handout 11_2 slajd 4-6)
    # -------------------------------------------------------------
    # Pochodne kierunkowe: C_n_beta (stateczność kierunkowa) i C_n_r (tłumienie odchylania)
    # Wpływ usterzenia pionowego i destabilizacji kadłuba
    c_n_beta_vt = vv * a_v * 0.95
    c_n_beta_fus = -0.0010 * (l_fus * (d_fus ** 2)) / (S * b)
    c_n_beta = max(0.02, c_n_beta_vt + c_n_beta_fus)

    # C_nr (tłumienie odchylania głównie od usterzenia pionowego)
    c_nr = -2.0 * vv * (l_v / b) * a_v

    # Pochodna siły bocznej C_y_beta
    c_y_beta = - (S_v / S) * a_v

    # Częstość drgań nietłumionych holendrowania omega_n_dr [rad/s]
    omega_n_dr = math.sqrt(max(1e-4, (q_inf * S * b * c_n_beta) / I_zz))

    # Współczynnik tłumienia drgań holendrowania zeta_dr [-]
    damping_dr = - (q_inf * S * (b ** 2) / (2.0 * v_ms * I_zz)) * c_nr - (q_inf * S / (m0 * v_ms)) * c_y_beta
    zeta_dr = max(0.005, damping_dr / (2.0 * omega_n_dr))

    # Sprawdzenie kryterium JAR/CS-23: -xi/eta >= 0.0523 (Handout 11_2 slajd 5-6)
    # -xi/eta = zeta_dr / sqrt(1 - zeta_dr^2)
    damping_criterion_ratio = zeta_dr / math.sqrt(max(0.001, abs(1.0 - zeta_dr ** 2)))
    cs23_dutch_roll_ok = damping_criterion_ratio >= 0.0523

    # Poziomy akceptowalności Dutch Roll (Handout 11_2 slajd 4):
    # Faza B (przelot): Level 1: zeta_dr >= 0.08, omega_n_dr >= 0.4 rad/s; Level 2: zeta_dr >= 0.02
    if zeta_dr >= 0.08 and omega_n_dr >= 0.4 and cs23_dutch_roll_ok:
        dutch_roll_level = 1
    elif zeta_dr >= 0.02 and omega_n_dr >= 0.4:
        dutch_roll_level = 2
    else:
        dutch_roll_level = 3

    # -------------------------------------------------------------
    # 10. Stateczność spiralna (Spiral Mode) (Handout 11_2 slajd 3-4)
    # -------------------------------------------------------------
    # Pochodna efektu wzniosu C_l_beta (efekt wzniosu skrzydła + skosu + usterzenia pionowego)
    # Wznios z teorii pasowej dla płata trapezowego (Etkin, Reid): C_lβ,Γ = −(a·Γ/6)·(1 + 2λ)/(1 + λ).
    # Położenie płata działa jak dodatkowy wznios: górnopłat ok. +1,5°, dolnopłat ok. −1,5° (Raymer).
    z_v_arm = 0.25 * (geom.get("vertical_tail", {}).get("b_v", 1.5))
    wing_position_deg = {"high": 1.5, "braced_high": 1.5, "low": -1.5}.get(params.get("wing_config", "low"), 0.0)
    gamma_eff = math.radians(dihedral_deg + wing_position_deg)
    c_l_beta = (- a_w * gamma_eff / 6.0 * (1.0 + 2.0 * taper) / (1.0 + taper)
                - 0.05 * cz_cruise * math.sin(math.radians(sweep_deg)) - (S_v / S) * a_v * (z_v_arm / b))
    
    # C_l_r (moment przechylający od prędkości odchylania)
    c_l_r = cz_cruise / 4.0

    # Wartość własna ruchu spiralnego (aproksymacja klasyczna):
    # lambda_s ~= −(g / V) * (C_l_beta * C_n_r − C_l_r * C_n_beta) / (C_l_beta * C_n_p − C_l_p * C_n_beta)
    # (Cook, Nelson): spirala stateczna, gdy C_lβ·C_nr > C_lr·C_nβ, czyli λ_s < 0.
    # Mianownik zdominowany przez −C_lp·C_nβ (> 0); C_np pominięto.
    denom = max(1e-4, - c_lp * c_n_beta)
    numer = c_l_beta * c_nr - c_l_r * c_n_beta
    lambda_s = -(G0 / v_ms) * (numer / denom)

    # Czas podwojenia (jeśli niestabilny) lub połowienia (jeśli stabilny)
    is_spiral_stable = lambda_s <= 0
    if is_spiral_stable:
        t_double_spiral = math.inf
        t_spiral_s = math.log(2.0) / abs(lambda_s) if abs(lambda_s) > 1e-6 else math.inf
        spiral_desc = "Stabilny aperiodycznie (samoczynny powrót z przechyłu)."
        spiral_level = 1
    else:
        t_double_spiral = math.log(2.0) / lambda_s
        t_spiral_s = 1.0 / lambda_s
        # Kryteria Handout 11_2 Slajd 3: Faza B: Level 1: T2 >= 20 s (T_S >= 28.9 s); Level 2: T2 >= 8 s; Level 3: T2 >= 5 s
        if t_double_spiral >= 20.0:
            spiral_level = 1
            spiral_desc = f"Dopuszczalna wolna niestabilność: T2 = {t_double_spiral:.1f} s >= 20 s (Level 1)."
        elif t_double_spiral >= 8.0:
            spiral_level = 2
            spiral_desc = f"Niestabilność spiralna Level 2: T2 = {t_double_spiral:.1f} s (wymaga korekt pilota)."
        elif t_double_spiral >= 5.0:
            spiral_level = 3
            spiral_desc = f"Niestabilność spiralna Level 3: T2 = {t_double_spiral:.1f} s."
        else:
            spiral_level = 4
            spiral_desc = f"Niedopuszczalnie szybka spirala: T2 = {t_double_spiral:.1f} s < 5 s!"

    overall_level = max(cap_level, dutch_roll_level, roll_level, spiral_level)

    return {
        "flight_condition": {
            "altitude_m": round(h_m, 0),
            "tas_kmh": round(v_kmh, 1),
            "tas_ms": round(v_ms, 2),
            "mach": round(mach, 3),
            "q_pa": round(q_inf, 1),
            "cz_cruise": round(cz_cruise, 3),
            "ld_cruise": round(ld_cruise, 2)
        },
        "inertias": {
            "I_xx_kgm2": round(I_xx, 1),
            "I_yy_kgm2": round(I_yy, 1),
            "I_zz_kgm2": round(I_zz, 1)
        },
        "short_period": {
            "omega_n_rad_s": round(omega_n_sp, 3),
            "damping_ratio_zeta": round(zeta_sp, 3),
            "t_half_amplitude_s": round(t_half_sp, 3) if t_half_sp != math.inf else None,
            "n_z_alpha_g_rad": round(n_z_alpha, 2),
            "cap_rad_s2_per_g": round(cap, 4),
            "cap_level": cap_level,
            "evaluation": cap_comment,
            "references": "BIPOL I Handout 11_1 (slajdy 1-5), MIL-STD-1797"
        },
        "phugoid": {
            "omega_n_rad_s": round(omega_n_ph, 4),
            "period_s": round(t_period_ph, 1),
            "damping_ratio_zeta": round(zeta_ph, 3),
            "level": phugoid_level,
            "is_stable": zeta_ph >= 0.0
        },
        "roll_mode": {
            "time_constant_T_R_s": round(t_roll, 3),
            "time_to_bank_60deg_s": round(t_bank_60, 2),
            "steady_roll_rate_deg_s": round(math.degrees(p_steady), 1),
            "level": roll_level,
            "references": "BIPOL I Handout 11_2 (slajdy 2-3)"
        },
        "dutch_roll": {
            "omega_n_rad_s": round(omega_n_dr, 3),
            "damping_ratio_zeta": round(zeta_dr, 3),
            "damping_criterion_ratio": round(damping_criterion_ratio, 4),
            "cs23_criterion_passed": cs23_dutch_roll_ok,
            "cs23_required_ratio": 0.0523,
            "level": dutch_roll_level,
            "references": "BIPOL I Handout 11_2 (slajd 5), CS-23.181 / JAR-23"
        },
        "spiral_mode": {
            "lambda_s": round(lambda_s, 5),
            "is_stable": is_spiral_stable,
            "t_double_s": round(t_double_spiral, 1) if not is_spiral_stable and t_double_spiral != math.inf else None,
            "t_spiral_constant_s": round(t_spiral_s, 1),
            "level": spiral_level,
            "evaluation": spiral_desc,
            "references": "BIPOL I Handout 11_2 (slajd 3)"
        },
        "overall_summary": {
            "mil_std_overall_level": overall_level,
            "status": "Zadowalające (Level 1)" if overall_level == 1 else (
                "Akceptowalne (Level 2)" if overall_level == 2 else "Wymaga uwagi / Level 3"
            ),
            "description": f"Własności pilotażowe w przelocie: Poziom {overall_level} wg MIL-STD-1797 / BIPOL I Handout 11."
        }
    }
