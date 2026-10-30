# -*- coding: utf-8 -*-
"""
Moduł charakterystyk aerodynamicznych samolotu (BIPOL I).
Oparty w pierwszej kolejności na oficjalnej metodyce MEiL PW:
dr inż. Zbigniew Paturski — "Przewodnik po projektach z Mechaniki Lotu"
(Projekt nr 2: Płat, Projekt nr 3: Samolot).

Wyznacza:
- Geometrię i charakterystyki płata (ca, xN, Vs1, Re1, Glauert tau, delta, a_w)
- Opory komponentów samolotu (wzory 3.1 - 3.10, Tabela 3.1)
- Biegunową analityczną Cx = Cx0 + Cz^2 / (pi * Lambda * e) (wzór 3.11)
- Porównanie z zestawieniem statystycznym dr. Paturskiego (Tabele A, B, C)
- Punkty optymalne K_max, K_econ, E_max oraz konfiguracje ze skrzydełkami, klapami i podwoziem
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0
from calculations.paturski_ml import paturski_project_2_wing, paturski_project_3_aircraft_aero, default_retractable_gear
from calculations.high_lift import high_lift
from calculations.instructor import FLAP_TAKEOFF_DEFLECTION_DEG, FLAP_LANDING_DEFLECTION_DEG




def calculate_compressibility(mach: float, cz: float, tc: float = 0.12, sweep_deg: float = 0.0, airfoil_name: str = "") -> dict:
    """
    Oblicza efekty ściśliwości, liczbę Macha krytyczną (M_cr), rozbieżności oporu (M_dd)
    oraz przyrost oporu falowego wg korelacji Korna-Masona i Locka (Raymer rozdz. 12, Torenbeek 5.4).
    """
    m = max(0.0, float(mach))
    sweep_rad = math.radians(sweep_deg)
    cos_sweep = max(0.5, math.cos(sweep_rad))

    af_upper = (airfoil_name or "").upper()
    if "SC(" in af_upper or "SC2" in af_upper or "SUPERCRITICAL" in af_upper:
        kappa_a = 0.95
        profile_family = "Profil nadkrytyczny (supercritical)"
    elif "6" in af_upper and "NACA" in af_upper:
        kappa_a = 0.90
        profile_family = "Profil laminarny NACA serii 6"
    else:
        kappa_a = 0.87
        profile_family = "Profil klasyczny NACA / konwencjonalny"

    cz_pos = max(0.0, float(cz))
    tc_eff = max(0.06, min(0.24, float(tc)))
    m_dd_calc = (kappa_a / cos_sweep) - (tc_eff / (cos_sweep ** 2)) - (cz_pos / (10.0 * (cos_sweep ** 3)))
    m_dd = round(max(0.40, min(0.98, m_dd_calc)), 3)

    delta_m_cr = 0.10 / (1.0 + 2.0 * tc_eff)
    m_cr = round(max(0.35, m_dd - delta_m_cr), 3)

    beta = math.sqrt(max(0.05, 1.0 - min(0.90, m) ** 2)) if m < 1.0 else 0.316
    prandtl_glauert_factor = round(1.0 / beta, 3)

    if m <= m_cr:
        delta_cx_wave = 0.0
    elif m <= m_dd:
        ratio = (m - m_cr) / max(0.01, m_dd - m_cr)
        delta_cx_wave = round(0.0020 * (ratio ** 3), 5)
    else:
        delta_m = m - m_dd
        delta_cx_wave = round(0.0020 + 20.0 * (delta_m ** 4), 5)

    margin_to_divergence = round(m_dd - m, 3)
    is_safe = m < m_dd

    return {
        "mach": round(m, 3),
        "m_crit": m_cr,
        "m_dd": m_dd,
        "delta_cx_wave": delta_cx_wave,
        "prandtl_glauert_factor": prandtl_glauert_factor,
        "margin_to_divergence": margin_to_divergence,
        "drag_divergence_safe": is_safe,
        "profile_family": profile_family,
        "kappa_a": kappa_a,
        "is_transonic": m >= 0.70
    }


def calculate_aerodynamics(geom: dict, params: dict, m0: float = None):
    """
    Główna funkcja obliczeniowa aerodynamiki — uruchamia w pierwszej kolejności
    metodykę Paturskiego (Projekt nr 2 i Projekt nr 3).
    """
    wing = geom["wing"]
    S = float(wing["S"])
    AR = float(wing["AR"])
    mac = float(wing["mac"])
    sweep_deg = float(wing.get("sweep_deg", 0.0))
    tc_wing = float(wing.get("tc_ratio", 0.12))
    sweep_rad = math.radians(sweep_deg)

    # 1. METODYKA PATURSKIEGO JAKO PIERWSZA I NADRZĘDNA
    p2 = paturski_project_2_wing(geom, params, m0=m0)
    p3 = paturski_project_3_aircraft_aero(geom, params, m0=m0, p2_wing=p2)

    fit = p3["analytical_polar_fit"]
    cx0_clean = fit["cx0_approx"]
    oswald_e = fit["oswald_e_approx"]
    lambda_e = fit["lambda_e_approx"]
    k_clean = fit.get("k_ind_approx") or fit.get("slope_d_cx_d_cz2") or (1.0 / (math.pi * lambda_e))

    a_w_paturski_rad = p2["a_wing_paturski_rad"]
    a_w_paturski_deg = p2["a_wing_paturski_deg"]
    tau_glauert = p2["tau_glauert"]
    delta_glauert = p2["delta_glauert"]
    a_w_rad = a_w_paturski_rad
    a_w_deg = a_w_paturski_deg

    cz_max_clean = float(p2.get("cz_max_clean") or params.get("cz_max_clean", 1.40))

    # 2. Mechanizacja skrzydła (klapy i sloty) wg założeń BIPOL I / Paturskiego
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")
    wing_config = params.get("wing_config", "low")

    fd = high_lift(params, oswald_e, geometry=geom)
    # Section increments are scaled by the wing area equipped with each device.
    # They are preliminary estimates, not measured polars or percentages.
    flap_configurations = {
        'clean': {'deflection_deg': 0.0, 'delta_cz': 0.0, 'delta_cx0': 0.0},
        'takeoff': {'deflection_deg': FLAP_TAKEOFF_DEFLECTION_DEG,
                    'delta_cz': fd['delta_cz_to'], 'delta_cx0': fd['delta_cx0_to']},
        'landing': {'deflection_deg': FLAP_LANDING_DEFLECTION_DEG,
                    'delta_cz': fd['delta_cz_lnd'], 'delta_cx0': fd['delta_cx0_lnd']},
    }

    delta_cz_slat, delta_cx_slat = fd['slat_lift'], fd['slat_drag']

    cz_max_to = cz_max_clean + flap_configurations['takeoff']['delta_cz'] + delta_cz_slat * 0.5
    cz_max_lnd = cz_max_clean + flap_configurations['landing']['delta_cz'] + delta_cz_slat

    delta_cx0_to = flap_configurations['takeoff']['delta_cx0'] + delta_cx_slat * 0.5
    delta_cx0_lnd = flap_configurations['landing']['delta_cx0'] + delta_cx_slat

    ac_type = params.get("aircraft_type", "piston_ga")
    is_retractable = default_retractable_gear(params)
    delta_cx0_gear = 0.018 if (is_retractable and ac_type != "glider") else 0.000

    e_to = min(oswald_e, fd["e_to"])
    e_lnd = min(oswald_e, fd["e_lnd"])
    k_to = 1.0 / (math.pi * AR * e_to)
    k_lnd = 1.0 / (math.pi * AR * e_lnd)

    cx0_to = cx0_clean + delta_cx0_to
    cx0_lnd = cx0_clean + delta_cx0_lnd + delta_cx0_gear

    # 3. Punkty optymalne biegunowej Paturskiego (wzory 20, 27-28 i Projekt nr 4 wzory 4.8-4.12)
    cz_opt = math.sqrt(cx0_clean / k_clean)
    cx_opt = 2.0 * cx0_clean
    k_max = cz_opt / cx_opt

    cz_econ = math.sqrt(3.0 * cx0_clean / k_clean)
    cx_econ = 4.0 * cx0_clean
    k_econ = cz_econ / cx_econ

    cz_jet_range = math.sqrt(cx0_clean / (3.0 * k_clean))
    cx_jet_range = (4.0 / 3.0) * cx0_clean
    k_jet_range = cz_jet_range / cx_jet_range
    e_energy_max = (cz_econ ** 3) / (cx_econ ** 2)

    # 4. Zestawienie składowych oporu Component Drag Buildup z Tabeli 3.1 dr. Paturskiego
    # Mapujemy wiersze Tabeli 3.1 na format komponentów
    h_cr = float(params.get("cruise_altitude_m", 2500.0))
    v_cr_ms = max(20.0, float(params.get("cruise_speed_kmh", 220.0)) / 3.6)
    isa_cr = isa_atmosphere(h_cr)
    rho_cr = isa_cr["rho"]
    mu_cr = 1.789e-5 * math.pow(isa_cr["T"] / 288.15, 1.5) * ((288.15 + 110.4) / (isa_cr["T"] + 110.4))
    a_sound_cr = isa_cr.get("a", 340.0)
    mach_cruise = v_cr_ms / a_sound_cr
    compressibility_res = calculate_compressibility(
        mach=mach_cruise,
        cz=cz_opt,
        tc=tc_wing,
        sweep_deg=sweep_deg,
        airfoil_name=params.get("airfoil", "")
    )

    re_wing = round((rho_cr * v_cr_ms * mac) / mu_cr)
    cf_wing = round(p2["cx_min_2_corrected"], 5)
    ff_wing = round(1.0 + 2.0 * tc_wing + 60.0 * (tc_wing ** 4), 3)

    l_fus = float(geom["fuselage"]["length"])
    re_fus = round((rho_cr * v_cr_ms * l_fus) / mu_cr)
    f_fus = max(3.0, float(geom["fuselage"]["fineness"]))
    ff_fus = round(1.0 + 60.0 / (f_fus ** 3) + f_fus / 400.0, 3)

    swet_wing = float(geom["wing"].get("S_wet", 2.0 * S * 0.88))
    swet_fus = float(geom["fuselage"].get("S_wet", math.pi * geom["fuselage"]["diameter"] * l_fus * 0.78))
    swet_ht = float(geom["horizontal_tail"].get("S_wet", 2.0 * geom["horizontal_tail"]["S_h"] * 1.02))
    swet_vt = float(geom["vertical_tail"].get("S_wet", 2.0 * geom["vertical_tail"]["S_v"] * 1.02))

    component_drag_buildup = []
    for row in p3["table_3_1_parasite"]:
        comp_name = row["component"]
        cx0_i = row.get("cx_delta", round(row.get("cx_s_m2", 0.0) / max(0.1, S), 4))
        share = row.get("share_pct", round((cx0_i / max(1e-4, cx0_clean)) * 100.0, 1))

        if "Płat" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = re_wing, cf_wing, ff_wing, 1.0, swet_wing
        elif "Kadłub" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = re_fus, 0.0035, ff_fus, 1.0, swet_fus
        elif "poziome" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = round(re_wing * 0.6), 0.0040, 1.15, 1.04, swet_ht
        elif "pionowe" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = round(re_wing * 0.5), 0.0040, 1.15, 1.04, swet_vt
        else:
            c_re, c_cf, c_ff, c_q, c_swet = 0, 0.0, 1.0, 1.0, round(row.get("s_j_m2", 0.0), 2)

        component_drag_buildup.append({
            "component": comp_name,
            "re": c_re,
            "cf": c_cf,
            "ff": c_ff,
            "q": c_q,
            "swet_m2": round(c_swet, 2),
            "cx0_i": round(cx0_i, 4),
            "share_pct": round(share, 1),
            "source": row.get("source", "Paturski Tabela 3.1")
        })

    # 5. Generowanie punktów biegunowej (Tabela 2.2 Paturskiego z rozszerzeniem na klapy)
    polar_points = []
    n_pts = 40
    for i in range(n_pts + 1):
        cz = -0.2 + i * (cz_max_lnd - (-0.2)) / n_pts

        # Konfiguracja gładka
        if cz <= cz_max_clean:
            cx_c = cx0_clean + k_clean * (cz ** 2)
            ld_c = cz / cx_c if abs(cx_c) > 1e-4 else 0.0
            e_en_c = ((cz ** 3) / (cx_c ** 2)) if (abs(cx_c) > 1e-4 and cz > 0) else 0.0
        else:
            cx_c = None
            ld_c = None
            e_en_c = None

        # Konfiguracja startowa
        if cz <= cz_max_to:
            cx_t = cx0_to + k_to * (cz ** 2)
            ld_t = cz / cx_t if abs(cx_t) > 1e-4 else 0.0
        else:
            cx_t = None
            ld_t = None

        # Konfiguracja lądowania
        cx_l = cx0_lnd + k_lnd * (cz ** 2)
        ld_l = cz / cx_l if abs(cx_l) > 1e-4 else 0.0

        polar_points.append({
            "cz": round(cz, 3),
            "cx_clean": round(cx_c, 4) if cx_c is not None else None,
            "ld_clean": round(ld_c, 2) if ld_c is not None else None,
            "e_energy_clean": round(e_en_c, 1) if e_en_c is not None else None,
            "cx_to": round(cx_t, 4) if cx_t is not None else None,
            "cx_lnd": round(cx_l, 4) if cx_l is not None else None
        })

    return {
        "k_clean": k_clean,
        "cx0_clean": cx0_clean,
        "cx0_buildup_theoretical": cx0_clean,
        "component_drag_buildup": component_drag_buildup,
        "oswald_e": oswald_e,
        "lambda_e": lambda_e,
        "cx0_to": cx0_to,
        "cx0_lnd": cx0_lnd,
        "k_to": k_to,
        "k_lnd": k_lnd,
        "k_max": k_max,
        "k_econ": k_econ,
        "e_energy_max": e_energy_max,
        "k_jet_range": k_jet_range,
        "cz_opt": cz_opt,
        "cx_opt": cx_opt,
        "cz_econ": cz_econ,
        "cx_econ": cx_econ,
        "cz_jet_range": cz_jet_range,
        "cx_jet_range": cx_jet_range,
        "a_w_rad": a_w_rad,
        "a_w_deg": a_w_deg,
        "a_w_paturski_rad": a_w_paturski_rad,
        "a_w_paturski_deg": a_w_paturski_deg,
        "tau_glauert": tau_glauert,
        "delta_glauert": delta_glauert,
        "cz_max_clean": cz_max_clean,
        "cz_max_to": cz_max_to,
        "cz_max_lnd": cz_max_lnd,
        "flap_configurations": flap_configurations,
        "high_lift_model": dict(flap_area_fraction=fd['flap_area_fraction'],
            slat_area_fraction=fd['slat_area_fraction'],
            note='Przyrosty profilowe 20°/40° pomnożono przez udział powierzchni płata z mechanizacją (BIPOL_2, s. 4). Wartości wstępne; wymagają biegunowych wybranego profilu.'),
        "polar_points": polar_points,
        "control_surfaces": geom.get("control_surfaces", {}),
        "paturski_p2": p2,
        "paturski_p3": p3,
        "table_2_2_complete": p3.get("table_2_2_complete", []),
        "statistical_comparison": p3.get("statistical_benchmarks_abc", {}),
        "compressibility": compressibility_res
    }
