"""
Moduł obwiedni obciążeń dopuszczalnych V-n (BIPOL I)
Samoloty: metoda wg CS-23 Amdt 4 (§23.333–23.345) i Danileckiego „Konstruowanie samolotów”, rozdz. 2.
CS-23 Amdt 5 usunęła te paragrafy (wymagania celu CS 23.2xxx, środki spełnienia w AMC/ASTM),
dlatego program stosuje je jako metodę dydaktyczną, a nie obowiązujący przepis.
Dla CS-25 linie podmuchu Pratta są uproszczeniem: CS-25.341 stosuje podmuch dyskretny 1-cos.
Szybowce i motoszybowce: CS-22 Amdt 3, §22.333–22.345; opcjonalnie starszy model Pratta z Amdt 2.
Wszystkie prędkości obwiedni są prędkościami równoważnymi (EAS), poziom morza.
"""
import math
from calculations.atmosphere import G0, RHO0, isa_atmosphere
from calculations.polish_law import resolve_category, limit_load_factors, envelope_speed_family, SUBCATEGORIES

# CS 22.337: n1 (przy VA), n2 (przy VD), n3 (przy VD), n4 (przy VG); kategoria U i A.
CS22_LOAD_FACTORS = {'cs22_utility': (5.3, 4.0, -1.5, -2.65), 'cs22_aerobatic': (7.0, 7.0, -5.0, -5.0)}


def cs23_speed_factors(category, ws_psf):
    """CS-23 Amdt 4 §23.335(a)(1) i (b)(2): współczynnik VC,min [kt/√psf] i VD/VC,min.

    Dla W/S > 20 psf oba maleją liniowo: do 28,6 i do 1,35 przy W/S = 100 psf
    (§23.335(a)(1)(iv) i (b)(4)).
    """
    aerobatic = category in ("aerobatic", "acrobatic")
    vc0 = 36.0 if aerobatic else 33.0
    vd0 = 1.55 if aerobatic else (1.50 if category == "utility" else 1.40)
    share = min(1.0, max(0.0, (ws_psf - 20.0) / 80.0))
    return vc0 - (vc0 - 28.6) * share, vd0 - (vd0 - 1.35) * share


def calculate_vn_envelope(m0: float, geom: dict, aero: dict, perf: dict, params: dict):
    """
    Parametry:
      - m0: masa startowa [kg]
      - geom: geometria skrzydła (S, b, MAC, AR)
      - aero: cz_max_clean, cx0
      - perf: prędkości vs_clean
      - params: kategoria samolotu (normal, utility, aerobatic, transport)
    """
    S = float(geom["wing"]["S"])
    b = float(geom["wing"]["b"])
    mac = float(geom["wing"]["mac"])
    AR = float(geom["wing"]["AR"])
    W = m0 * G0
    ws = W / S

    vs_clean_ms = math.sqrt(2 * ws / (RHO0 * float(aero['cz_max_clean'])))
    vs_lnd_ms = (math.sqrt(2 * ws / (RHO0 * float(aero['cz_max_lnd']))) if aero.get('cz_max_lnd')
                 else float(perf['speeds'].get('vs_lnd_kmh', vs_clean_ms * 3.6 * .82)) / 3.6)
    # V-n and sea-level stall branches use EAS, whereas mission cruise is TAS.
    v_cr_ms = float(params.get('cruise_speed_kmh', perf['speeds']['v_cruise_kmh'])) / 3.6 * math.sqrt(isa_atmosphere(params.get('cruise_altitude_m', 0))['sigma'])
    v_h_ms = float(perf.get('terms', {}).get('v_max_sl', (perf['speeds'].get('v_max_sl_kmh') or 0) / 3.6))
    powered = params.get("engine_type", "prop") != "none" and v_h_ms > 0

    # 1. Określenie dopuszczalnych współczynników przeciążeń wg podstawy projektowej podkategorii
    #    (klasyfikacja wg rozporządzenia MI, t.j. Dz. U. z 2025 r. poz. 1137 -> CS-25 / CS-23 / CS-VLA / CS-LSA / CS-22 / LTF-UL / STANAG 4671)
    category_key = resolve_category(params.get("category", "normal"))
    n_max, n_min, load_factor_ref = limit_load_factors(category_key, m0)
    category = envelope_speed_family(category_key)
    load_basis = SUBCATEGORIES[category_key]["load_basis"]
    sailplane = load_basis in CS22_LOAD_FACTORS
    cz_max = float(aero["cz_max_clean"])
    cz_min = float(aero.get("cz_min_clean", -0.85))  # Współczynnik siły nośnej ujemnego przeciągnięcia

    # 2. Parametry podmuchów wg Danilecki "Konstruowanie samolotów" wzory (2.13)-(2.14) oraz CS-23 Amdt 4 §23.341
    # Pochodna współczynnika siły nośnej skończonego płata a_w = dCz/dalpha [1/rad] (wzór Helmbolda-Diedericha ze skosem)
    a_w = float(aero.get("a_w_rad", (2.0 * math.pi * AR) / (AR + 2.0 * ((AR + 4.0) / (AR + 2.0)))))

    # Cecha masowa mu_g = 2 (m/S) / (rho c a). Danilecki (wzór 2.14) używa ŚCA;
    # CS 22.341 wymaga średniej cięciwy geometrycznej S/b.
    chord = S / b if sailplane else mac
    mu_g = (2.0 * (m0 / S)) / (RHO0 * chord * a_w)

    # Współczynnik łagodzenia podmuchu Kg wg Danilecki wzór (2.13) / CS-23 Amdt 4 §23.341(b) / CS 22.341
    k_g = (0.88 * mu_g) / (5.3 + mu_g)
    cs22_model = params.get('cs22_gust_model', 'amendment3') if sailplane else None
    gust_length_ratio = None
    if cs22_model == 'amendment3':
        gust_length_ratio = 12.17 + .191 * mu_g
        reduced_mass = mu_g / gust_length_ratio
        k_g = .96 * reduced_mass / (.475 + reduced_mass)

    def gust_dn(v_ms, u_ms):
        return (0.5 * RHO0 * v_ms * a_w * k_g * u_ms) / ws

    # 3. Prędkości charakterystyczne obwiedni
    # Prędkość manewrowa dodatnia VA = Vs1 * sqrt(n_max); ujemna VG = Vs1 * sqrt(|n_min| * (Cz_max / |Cz_min|))
    v_a_ms = vs_clean_ms * math.sqrt(n_max)
    v_g_ms = vs_clean_ms * math.sqrt(abs(n_min) * (cz_max / abs(cz_min)))

    if sailplane:
        n1, n2, n3, n4 = CS22_LOAD_FACTORS[load_basis]
        # CS 22.335(f): VD >= 18 * cbrt((W/S)/Cd_min) km/h (kat. U, W/S w daN/m²) lub 3,5 W/S + 200 (kat. A);
        # dla motoszybowca także VD >= 1,35 VH.
        cd_min = max(0.004, float(aero.get("cx0_clean") or aero.get("cx0") or 0.012))
        ws_dan = ws / 10.0
        vd_rule_kmh = (18.0 * (ws_dan / cd_min) ** (1.0 / 3.0) if load_basis == 'cs22_utility'
                       else 3.5 * ws_dan + 200.0)
        v_d_ms = max(vd_rule_kmh / 3.6, 1.35 * v_h_ms if powered else 0.0, v_a_ms)
        rule_terms = dict(cd_min=cd_min, ws_dan=ws_dan, vd_rule_kmh=vd_rule_kmh)
        v_b_ms = v_a_ms               # CS 22.335(c): VB nie mniejsza niż VA
        v_c_ms = None                 # CS-22 nie definiuje VC
        v_f_ms = max(1.4 * vs_clean_ms, 2.0 * vs_lnd_ms)   # CS 22.335(b)(1)
        n_flap, u_flap = 4.0, 7.5                           # CS 22.345(b)(1)
        gusts = [("VB", v_b_ms, 15.0), ("VD", v_d_ms, 7.5)]  # CS 22.333(c)
        vb_gust = True
        gust_basis = (f"CS-22 Amdt {'3 (podmuch 1-cos)' if cs22_model == 'amendment3' else '2 (Pratt)'} §22.333(c), §22.341: "
                      "15 m/s przy VB i 7,5 m/s przy VD; μ z cięciwy S/b; osobne ograniczenia n dodatniego i ujemnego do ±1,25 (V/VS1)².")
        speed_rule = (f"CS 22.335: VB ≥ VA, VD ≥ {'18·∛((W/S)/Cd,min)' if load_basis == 'cs22_utility' else '3,5·W/S + 200'}"
                      f" = {vd_rule_kmh:.0f} km/h (Cd,min = {cd_min:.4f})" + (", VD ≥ 1,35 VH" if powered else "")
                      + "; VF ≥ max(1,4 VS1; 2,0 VSF).")
    else:
        # Obliczeniowa prędkość przelotowa VC (EAS)
        ws_psf = ws / 47.88026   # 1 lbf/ft² = 47.88026 N/m²; siła ciężkości, nie masa
        vc_factor_kts, vd_factor = cs23_speed_factors(category, ws_psf)
        v_c_min_ms = (vc_factor_kts * math.sqrt(max(1.0, ws_psf))) * 0.514444
        if category == "transport":
            # CS-25.335: reguła 33·√(W/S) dotyczy CS-23; VD >= VC/0,8.
            v_c_ms = max(v_cr_ms, v_a_ms * 1.02)
            v_d_ms = 1.25 * v_c_ms
            speed_rule = "CS-25.335(b): VD ≥ VC/0,8; VC nie mniejsza niż przelotowa EAS i VA (uproszczenie bez kryterium VB + 1,32 Uref)."
        else:
            # CS-23 Amdt 4 §23.335(a)(2): VC nie musi przekraczać 0.9 VH, ale musi być >= VA
            v_c_ms = max(v_cr_ms, v_a_ms * 1.02, min(v_c_min_ms, 0.9 * v_h_ms) if v_h_ms > 0 else v_c_min_ms)
            # §23.335(b): VD >= 1,25 VC oraz VD >= k·VC,min (1,40 / 1,50 / 1,55, malejące powyżej 20 psf)
            v_d_ms = max(1.25 * v_c_ms, vd_factor * v_c_min_ms)
            speed_rule = (f"CS-23 Amdt 4 §23.335: VC,min = {vc_factor_kts:.1f}·√(W/S) kt, VD ≥ max(1,25 VC; "
                          f"{vd_factor:.3f} VC,min); W/S = {ws_psf:.1f} lbf/ft².")
        rule_terms = dict(ws_psf=ws_psf, vc_factor_kts=vc_factor_kts, vd_factor=vd_factor,
                          v_c_min_ms=v_c_min_ms)
        n1, n4 = n_max, n_min
        # CS-23 Amdt 4 / JAR-23.333(b)(3): ujemna gałąź maleje liniowo od VC do n = 0 przy VD
        # (normal, commuter; także CS-25.333(b)), a do n = −1 dla kategorii akrobacyjnej i użytkowej.
        n2, n3 = n_max, (-1.0 if load_basis in ("cs23_aerobatic", "cs23_utility") else 0.0)
        # Podmuch przy V_B był wymagany tylko dla kategorii commuter (§23.333(c)(1)(iii));
        # dla CS-25 odpowiada uproszczonemu modelowi Pratta (dawny FAR 25.341).
        vb_gust = load_basis in ("cs23_commuter", "cs25")
        # Prędkość VB: przecięcie linii przeciągnięcia n = (V/Vs1)^2 z linią podmuchu 66 fps (20.12 m/s)
        a_quad = 1.0 / max(1.0, vs_clean_ms ** 2)
        b_quad = gust_dn(1.0, 20.12)
        v_b_intersect_ms = (b_quad + math.sqrt((b_quad ** 2) + 4.0 * a_quad)) / (2.0 * a_quad)
        v_b_ms = min(v_c_ms, max(v_a_ms * 0.85, v_b_intersect_ms))
        rule_terms.update(v_b_intersect_ms=v_b_intersect_ms)
        # CS-23 Amdt 4 §23.345: VF = max(1.4 Vs1, 1.8 Vs0), n = +2,0
        v_f_ms = max(1.4 * vs_clean_ms, 1.8 * vs_lnd_ms)
        n_flap, u_flap = 2.0, 7.62
        gusts = ([("VB", v_b_ms, 20.12)] if vb_gust else []) + [("VC", v_c_ms, 15.24), ("VD", v_d_ms, 7.62)]
        if load_basis == "cs25":
            gust_basis = ("Uproszczony model Pratta (dawny FAR 25.341: 66/50/25 ft/s przy VB/VC/VD). "
                          "Obowiązujący CS-25.341 stosuje podmuch dyskretny 1-cos i turbulencję ciągłą.")
        elif vb_gust:
            gust_basis = "Metoda wg CS-23 Amdt 4 §23.333(c) / Danilecki: 66/50/25 ft/s przy VB/VC/VD (commuter)."
        else:
            gust_basis = ("Metoda wg CS-23 Amdt 4 §23.333(c) / Danilecki: 50/25 ft/s przy VC/VD; "
                          "podmuch 66 ft/s przy VB dotyczył tylko kategorii commuter.")

    # Współczynnik bezpieczeństwa konstrukcji nu = 1.5 wg CS-23 Amdt 4 §23.303 / CS 22.303 / Danilecki wzór (1.1)
    safety_factor_nu = 1.5

    # 4. Generowanie krzywych obwiedni manewrowej do wykresu
    # A. Krzywa przeciągnięcia dodatniego n = (V / Vs1)^2 od V=0 do VA
    stall_pos = []
    n_pts_stall = 18
    for i in range(n_pts_stall + 1):
        v = i * v_a_ms / n_pts_stall
        n = (0.5 * RHO0 * (v ** 2) * cz_max) / ws
        stall_pos.append({"v_kmh": round(v * 3.6, 1), "n": round(min(n, n_max), 2)})

    # B. Krzywa przeciągnięcia ujemnego od V=0 do VG
    stall_neg = []
    for i in range(n_pts_stall + 1):
        v = i * v_g_ms / n_pts_stall
        n = (0.5 * RHO0 * (v ** 2) * cz_min) / ws
        stall_neg.append({"v_kmh": round(v * 3.6, 1), "n": round(max(n, n_min), 2)})

    # C. Pełny wielokąt obwiedni manewrowej z paraboliczną granicą przeciągnięcia n(V) ~ V^2
    upper = ([] if sailplane else [{"v_kmh": round(v_c_ms * 3.6, 1), "n": n1}]) + [
        {"v_kmh": round(v_d_ms * 3.6, 1), "n": n2},
        {"v_kmh": round(v_d_ms * 3.6, 1), "n": n3},
    ]
    lower = [] if sailplane else [{"v_kmh": round(v_c_ms * 3.6, 1), "n": n4}]
    maneuver_polygon = list(stall_pos) + upper + lower + list(reversed(stall_neg))

    # D. Linie podmuchów Pratta: Delta_n = (0.5 * rho0 * V * a_w * K_g * U) / (W/S) (Danilecki wzory 2.10-2.13)
    def gust_loads(v_ms, u_ms):
        dn = gust_dn(v_ms, u_ms)
        cap = 1.25 * (v_ms / vs_clean_ms) ** 2
        return (min(1 + dn, cap), max(1 - dn, -cap)) if sailplane else (1 + dn, 1 - dn)

    gust_points = [(label, v, u, *gust_loads(v, u)) for label, v, u in gusts]
    def interpolate(v, points):
        if v >= points[-1][0]:
            return points[-1][1]
        for (v0, n0), (v1, n1_) in zip(points, points[1:]):
            if v <= v1 and v1 > v0:
                return n0 + (n1_ - n0) * (v - v0) / (v1 - v0)
        return points[0][1]

    gust_upper = [(0., 1.)] + [(v, pos) for _, v, _, pos, _ in gust_points]
    gust_lower = [(0., 1.)] + [(v, neg) for _, v, _, _, neg in gust_points]
    def gust_at(v):
        if sailplane and v <= v_b_ms:
            return gust_loads(v, 15.)
        return interpolate(v, gust_upper), interpolate(v, gust_lower)

    gust_plot_speeds = ([vs_clean_ms + (v_b_ms - vs_clean_ms) * i/40 for i in range(41)]
                        if sailplane else [0.]) + [v for _, v, *_ in gust_points]
    gust_plot_speeds = sorted(set(gust_plot_speeds))
    gust_pos = [{'v_kmh': round(v*3.6, 1), 'n': round(gust_at(v)[0], 2)} for v in gust_plot_speeds]
    gust_neg = [{'v_kmh': round(v*3.6, 1), 'n': round(gust_at(v)[1], 2)} for v in gust_plot_speeds]

    n_gust_max = round(max(pos for _, _, _, pos, _ in gust_points), 2)
    n_gust_min = round(min(neg for _, _, _, _, neg in gust_points), 2)
    n_dimensioning_pos = round(max(n_max, n_gust_max), 2)
    n_dimensioning_neg = round(min(n_min, n_gust_min), 2)
    n_ult_pos = round(n_dimensioning_pos * safety_factor_nu, 2)
    n_ult_neg = round(n_dimensioning_neg * safety_factor_nu, 2)

    # E. Punkty charakterystyczne (tabela P6) i pętla obciążeń z klapami
    kmh = lambda v: round(v * 3.6, 1)  # noqa: E731
    by_label = {label: (v, pos-1) for label, v, _, pos, _ in gust_points}
    key_points = [
        {"point": "S (początek przeciągnięcia dodatniego Vs1)", "v_kmh": kmh(vs_clean_ms), "n": 1.0, "type": "Przeciągnięcie n=+1"},
        {"point": "A (prędkość manewrowa dodatnia VA)", "v_kmh": kmh(v_a_ms), "n": n1, "type": "Krzywa manewrowa n_max"},
    ]
    if "VB" in by_label:
        u_b = next(u for label, _, u, *_ in gust_points if label == "VB")
        key_points.append({"point": f"B (prędkość podmuchu VB, U={u_b:g} m/s)", "v_kmh": kmh(v_b_ms),
                           "n": round(1.0 + by_label["VB"][1], 2), "type": "Podmuch"})
    if v_c_ms is not None:
        key_points.append({"point": "C (obliczeniowa prędkość przelotowa VC)", "v_kmh": kmh(v_c_ms), "n": n1,
                           "type": "Przelot VC (U=15,24 m/s)"})
    key_points += [
        {"point": "D (obliczeniowa prędkość nurkowania VD)", "v_kmh": kmh(v_d_ms), "n": n2, "type": "Nurkowanie VD"},
        {"point": "E (dolny punkt przy VD)", "v_kmh": kmh(v_d_ms), "n": n3, "type": "Nurkowanie, gałąź ujemna"},
    ]
    if v_c_ms is not None:
        key_points.append({"point": "F (dolny punkt przy VC z n_min)", "v_kmh": kmh(v_c_ms), "n": n4, "type": "Krzywa manewrowa n_min"})
    key_points.append({"point": "G (prędkość manewrowa ujemna VG)", "v_kmh": kmh(v_g_ms), "n": n4, "type": "Przeciągnięcie ujemne"})

    flap_loop = [
        {"point": "Sf (początek przeciągnięcia z klapami Vs0)", "v_kmh": kmh(vs_lnd_ms), "n": 1.0},
        {"point": f"Af (wejście na n=+{n_flap:g} z klapami)", "v_kmh": kmh(vs_lnd_ms * math.sqrt(n_flap)), "n": n_flap},
        {"point": "Ff (prędkość obliczeniowa klap VF)", "v_kmh": kmh(v_f_ms), "n": n_flap},
        {"point": "Df (dolny punkt przy VF)", "v_kmh": kmh(v_f_ms), "n": 0.0},
    ]
    # The four table points do not describe the stall parabola or its origin.
    v_af_ms = vs_lnd_ms * math.sqrt(n_flap)
    flap_polygon = [{"v_kmh": kmh(v_af_ms * i / n_pts_stall),
                     "n": round(n_flap * (i / n_pts_stall) ** 2, 2)}
                    for i in range(n_pts_stall + 1)]
    flap_polygon += [{"v_kmh": kmh(v_f_ms), "n": n_flap},
                     {"v_kmh": kmh(v_f_ms), "n": 0.0}, {"v_kmh": 0.0, "n": 0.0}]

    # F. Wypadkowa obwiednia konstrukcyjna (CS-23.333(c) / Danilecki rys. 2.1)
    composite_pts_pos = []
    composite_pts_neg = []
    sample_speeds = {i * v_d_ms / 60 for i in range(61)} | {
        0., vs_clean_ms, v_a_ms, v_g_ms, v_b_ms, v_d_ms, *[v for _, v, *_ in gust_points]}
    if v_c_ms is not None:
        sample_speeds.add(v_c_ms)
    sample_speeds.add(vs_clean_ms * (1 - 1e-9))
    for v in sorted(x for x in sample_speeds if 0 <= x <= v_d_ms):
        n_st_pos = (0.5 * RHO0 * (v ** 2) * cz_max) / ws
        n_st_neg = (0.5 * RHO0 * (v ** 2) * cz_min) / ws
        if sailplane:
            n_man_p = n1 if v <= v_a_ms else interpolate(v, [(v_a_ms, n1), (v_d_ms, n2)])
            n_man_n = n4 if v <= v_g_ms else interpolate(v, [(v_g_ms, n4), (v_d_ms, n3)])
        elif v_c_ms is None or v <= v_c_ms:
            n_man_p = n1
            n_man_n = n4
        else:
            ratio = (v - v_c_ms) / max(0.1, v_d_ms - v_c_ms)
            n_man_p = n1 + (n2 - n1) * ratio
            n_man_n = n4 + (n3 - n4) * ratio
        n_man_p, n_man_n = min(n_st_pos, n_man_p), max(n_st_neg, n_man_n)
        # Gust and manoeuvre cases are separate; take their outer boundary.
        # Applying the static stall curve again would erase permitted gust loads.
        if v >= vs_clean_ms:
            gust_p, gust_n = gust_at(v)
            n_comp_p, n_comp_n = max(n_man_p, gust_p), min(n_man_n, gust_n)
        else:
            n_comp_p, n_comp_n = n_man_p, n_man_n
        composite_pts_pos.append({"v_kmh": round(v * 3.6, 1), "n": round(n_comp_p, 2)})
        composite_pts_neg.append({"v_kmh": round(v * 3.6, 1), "n": round(n_comp_n, 2)})
    composite_polygon = composite_pts_pos + list(reversed(composite_pts_neg))

    from calculations.polish_law import LB_PER_KG
    terms = dict(W=W, ws=ws, m0=m0, S=S, b=b, mac=mac, vs_clean_ms=vs_clean_ms, vs_lnd_ms=vs_lnd_ms,
                 v_cr_eas_ms=v_cr_ms, v_h_ms=v_h_ms, cz_max=cz_max, cz_min=cz_min, a_w=a_w, chord=chord,
                 mu_g=mu_g, k_g=k_g, v_a_ms=v_a_ms, v_g_ms=v_g_ms, v_c_ms=v_c_ms, v_d_ms=v_d_ms,
                 v_b_ms=v_b_ms, v_f_ms=v_f_ms, w_lb=max(1.0, m0) * LB_PER_KG, load_basis=load_basis,
                 sigma_cr=isa_atmosphere(params.get('cruise_altitude_m', 0))['sigma'], **rule_terms)
    return {
        "speed_basis": "EAS",
        "composite_basis": "Zewnętrzna granica osobnych przypadków manewru i podmuchu, bez sumowania ich przeciążeń.",
        "terms": terms,
        "limits": {
            "n_max": n_max,
            "n_min": n_min,
            "n_at_vd_pos": n2,
            "n_at_vd_neg": n3,
            "safety_factor_nu": safety_factor_nu,
            "n_ult_pos": n_ult_pos,
            "n_ult_neg": n_ult_neg,
            "n_gust_max": n_gust_max,
            "n_gust_min": n_gust_min,
            "n_dimensioning_pos": n_dimensioning_pos,
            "n_dimensioning_neg": n_dimensioning_neg,
            "category": category_key,
            "category_code": SUBCATEGORIES[category_key]["code"],
            "design_code": SUBCATEGORIES[category_key]["design_code"],
            "load_factor_reference": load_factor_ref,
            "speed_rule": speed_rule,
            "basis": "CS-22" if sailplane else ("CS-25" if category == "transport" else "CS-23"),
            "cs22_gust_model": cs22_model,
        },
        "speeds": {
            "v_s_kmh": kmh(vs_clean_ms),
            "v_s0_kmh": kmh(vs_lnd_ms),
            "v_a_kmh": kmh(v_a_ms),
            "v_b_kmh": kmh(v_b_ms) if vb_gust else None,
            "v_g_kmh": kmh(v_g_ms),
            "v_c_kmh": kmh(v_c_ms) if v_c_ms is not None else None,
            "v_d_kmh": kmh(v_d_ms),
            "v_f_kmh": kmh(v_f_ms)
        },
        "gust_factors": {
            "a_w": a_w,
            "mu_g": mu_g,
            "k_g": k_g,
            "gust_length_ratio": gust_length_ratio,
            "gust_length_m": gust_length_ratio * chord if gust_length_ratio is not None else None,
            "chord_m": chord,
            "chord_basis": "średnia cięciwa geometryczna S/b (CS 22.341)" if sailplane else "średnia cięciwa aerodynamiczna (Danilecki, wzór 2.14)",
            "vb_gust": vb_gust,
            "gust_basis": gust_basis,
            "gusts": [{"speed": label, "v_kmh": kmh(v), "u_ms": u, "delta_n": pos-1,
                       "delta_n_neg": 1-neg, "n_positive": pos, "n_negative": neg}
                      for label, v, u, pos, neg in gust_points],
            "u_b_ms": next((u for label, _, u, *_ in gust_points if label == "VB"), None),
            "u_c_ms": 15.24 if v_c_ms is not None else None,
            "u_d_ms": next(u for label, _, u, *_ in gust_points if label == "VD"),
            "delta_n_b": round(by_label["VB"][1], 3) if "VB" in by_label else None,
            "delta_n_c": round(by_label["VC"][1], 3) if "VC" in by_label else None,
            "delta_n_d": round(by_label["VD"][1], 3)
        },
        "key_points": key_points,
        "flap": {"n_flap": n_flap, "u_flap_ms": u_flap, "v_f_kmh": kmh(v_f_ms),
                 "loop": flap_loop, "maneuver_polygon": flap_polygon},
        "stall_pos": stall_pos,
        "stall_neg": stall_neg,
        "maneuver_polygon": maneuver_polygon,
        "composite_polygon": composite_polygon,
        "gust_pos": gust_pos,
        "gust_neg": gust_neg
    }
