"""
Moduł obliczeń dedykowanych dla poszczególnych projektów semestralnych BIPOL I (P1 do P6)
zgodnie z oficjalnym programem przedmiotu LK000-ISP-5003 BIPOL I (MEiL PW)
Autorzy metodyki: dr inż. Marcin Figat, dr inż. Tomasz Grabowski, prof. dr hab. inż. Cezary Galiński
"""
import math
from calculations.atmosphere import isa_atmosphere, G0
from calculations.official_topics import ALL_TOPICS
from calculations.paturski_ml import run_paturski_mechanika_lotu, aircraft_characteristics_for_cg
from calculations.trends import analyze_trends
from calculations.preliminary import preliminary_insights
from calculations.mass import calculate_mass_sizing
from calculations.high_lift import stall_requirement
from calculations.costs import calculate_costs
from calculations.polish_law import SUBCATEGORIES, K_CATEGORIES, resolve_category

def calculate_all_bipol_projects(mass_res: dict, sizing_res: dict, geom_res: dict, aero_res: dict, perf_res: dict, env_res: dict, bal_res: dict, params: dict) -> dict:
    """
    Integruje i wylicza kompletne pakiety danych dla 6 projektów semestralnych:
    P1: Projekt Koncepcyjny (5 pkt)
    P2: Studium Wykonalności (18 pkt)
    P3: Projekt Wstępny i Analiza Masowa (27 pkt)
    P4: Charakterystyki Aerodynamiczne Samolotu (15 pkt)
    P5: Osiągi Samolotu (15 pkt)
    P6: Obwiednia Obciążeń Dopuszczalnych (20 pkt)
    Łącznie: 100 pkt (60 pkt obowiązkowe + 40 pkt opcjonalne).
    Wzbogacone o pełną metodykę projektów Mechaniki Lotu wg dr. inż. Z. Paturskiego (Projekty nr 2, 3, 4, 5, 6).
    """
    paturski_res = run_paturski_mechanika_lotu(params, mass_res, sizing_res, geom_res, aero_res, perf_res)
    m0 = mass_res["m0"]
    m_empty = mass_res["m_empty"]
    m_fuel = mass_res["m_fuel"]
    m_payload = mass_res["m_payload"]
    m_crew = mass_res["m_crew"]
    
    S = geom_res["wing"]["S"]
    b = geom_res["wing"]["b"]
    AR = geom_res["wing"]["AR"]
    mac = geom_res["wing"]["mac"]
    eta = geom_res["wing"]["eta"]
    cr = geom_res["wing"]["cr"]
    ct = geom_res["wing"]["ct"]
    l_f = geom_res["fuselage"]["length"]
    d_f = geom_res["fuselage"]["diameter"]
    
    cx0 = aero_res["cx0_clean"]
    k_ind = aero_res["k_clean"]
    cz_max_clean = aero_res["cz_max_clean"]
    cz_max_lnd = aero_res["cz_max_lnd"]
    
    v_cr_kmh = float(params.get("cruise_speed_kmh", 240.0))
    v_cr_ms = v_cr_kmh / 3.6
    h_cr = float(params.get("cruise_altitude_m", 2500.0))
    engine_type = params.get("engine_type", "prop")
    ac_type = params.get("aircraft_type", "piston_ga")
    category = params.get("category", "normal")
    
    # =========================================================================
    # PROJEKT 1: PROJEKT KONCEPCYJNY (5 pkt)
    # =========================================================================
    # Temat projektu
    topic_id = int(params.get("topic_id", 0))
    selected_topic = next((dict(t, id=t['num'], catalog_id=t['id']) for t in ALL_TOPICS if t['num'] == topic_id), None)
    if not selected_topic:
        selected_topic = {
            "id": topic_id,
            "title": params.get("name", "Samolot szkolno-turystyczny"),
            "category_name": "Samoloty turystyczne i szkolne"
        }
    
    # 1.1 Szacunkowa biegunowa analityczna i doskonałość (Raymer / Galiński)
    # Powierzchnia omywana S_wet / S_w wyznaczona fizycznie z geometrii brył (skrzydło + kadłub + usterzenia)
    wetted_info = geom_res.get("wetted_area", {})
    swet_ratio = float(wetted_info.get("swet_over_s", 4.2 if ac_type == "piston_ga" else 5.2))
    s_wet = float(wetted_info.get("total_m2", round(swet_ratio * S, 2)))
    k_max_p1 = round(1 / (2 * math.sqrt(k_ind * cx0)), 2)
    # Wstępna moc / ciąg niezbędny dla założonej prędkości przelotowej na wysokości przelotu H_cr
    isa_cr_p1 = isa_atmosphere(h_cr)
    q_cr_p1 = max(10.0, 0.5 * isa_cr_p1["rho"] * (v_cr_ms ** 2))
    cz_cr_p1 = (m0 * G0) / (q_cr_p1 * S)
    drag_cr = q_cr_p1 * S * (cx0 + k_ind * (cz_cr_p1 ** 2))
    t_req_p1_kn = round(drag_cr / 1000.0, 2)
    if engine_type == "jet":
        p_req_p1_kw = round((drag_cr * v_cr_ms) / 1000.0, 1)
    else:
        p_req_p1_kw = round((drag_cr * v_cr_ms) / (float(params.get("prop_efficiency", 0.82)) * 1000.0), 1)
    
    # BIPOL_1, p. 1: actual reference cohort and fitted coefficients in kg.
    trend_analysis = analyze_trends(params, m0, m_empty, geom_res=geom_res)
    preliminary = preliminary_insights(params, mass_res, geom_res, aero_res)

    wing_cfg_pl = {
        "low": "dolnopłata wolnonośnego",
        "high": "górnopłata wolnonośnego",
        "braced_high": "górnopłata zastrzałowego",
        "mid": "średniopłata wolnonośnego"
    }.get(params.get("wing_config", "low"), "dolnopłata")
    law_sub = SUBCATEGORIES[resolve_category(category)]
    unmanned_ac = law_sub["unmanned"] or ac_type == "uav"
    k_cat = str(params.get("airworthiness_k") or law_sub["k_allowed"][0]).upper()
    cat_pl = (f"specyfikacji {law_sub['easa_spec']} ({law_sub['class_name']}, kategoria zdatności: {law_sub['design_code']}, "
              f"krajowy wpis: {law_sub['polish_code']} / {K_CATEGORIES.get(k_cat, k_cat)} wg rozporządzenia MI, t.j. Dz. U. z 2025 r. poz. 1137)")
    if engine_type == "jet":
        eng_pl = "turboodrzutowy dwuprzepływowy (Turbofan)"
    elif ac_type == "turboprop_regional":
        eng_pl = "turbośmigłowy (Turboprop)"
    elif engine_type == "none":
        eng_pl = "brak napędu"
    else:
        eng_pl = "tłokowy śmigłowy"

    raw_loc = params.get("engine_location", "rear" if engine_type == "jet" else "nose")
    if engine_type == "jet" and raw_loc == "nose":
        raw_loc = "wing" if ac_type == "jet_transport" else "rear"
    loc_pl = {
        "nose": "w nosie kadłuba (układ ciągnący ze śmigłem)",
        "wing": "w gondolach skrzydłowych",
        "rear": "w tylnej części kadłuba (gondole boczne / grzbietowe)" if engine_type == "jet" else "w tylnej części kadłuba (układ pchający)",
        "pusher": "w tylnej części kadłuba (układ pchający)",
        "pod": "w gondoli grzbietowej / podkadłubowej"
    }.get(raw_loc, "w gondolach skrzydłowych")

    if unmanned_ac:
        occupants_pl = (f"Bezzałogowy statek powietrzny – 0 osób na pokładzie (sterowanie ze stacji naziemnej GCS), "
                        f"wyposażenie zadaniowe {round(m_payload, 1)} kg")
    else:
        occupants_pl = (f"Załoga: {params.get('n_crew', 1)} os., pasażerowie: {params.get('n_pax', 1)} os. "
                        f"(masa płatna {round(m_payload, 1)} kg)")

    p1_data = {
        "topic": selected_topic,
        "concept_description": f"Projektowany samolot w układzie {wing_cfg_pl}, sklasyfikowany w {cat_pl}. {occupants_pl}, {('napęd ' + eng_pl + ' zabudowany ' + loc_pl) if engine_type != 'none' else 'lot bez napędu'}.",
        "engine_type": engine_type,
        "swet_over_s": swet_ratio,
        "s_wet_m2": s_wet,
        "k_max_est": k_max_p1,
        "p_req_est_kw": p_req_p1_kw,
        "t_req_est_kn": t_req_p1_kn,
        "trend_analysis": trend_analysis,
        "geometry_trends": trend_analysis.get("geometry_trends_analysis"),
        "preliminary": preliminary,
        "points_max": {"obligatory": 3, "optional": 2, "total": 5}
    }
    
    # =========================================================================
    # PROJEKT 2: STUDIUM WYKONALNOŚCI (18 pkt)
    # =========================================================================
    # 2.1 Profil misji i ułamki masowe
    fuel_detail = mass_res["fuel_fractions_detail"]
    mission_profile = mass_res['mission_phases']

    # 2.2 Dobór profilu skrzydła z katalogu (BIPOL_3_2010.pdf)
    isa_cr = isa_atmosphere(h_cr)
    mu_cr = 1.789e-5 * math.pow(isa_cr["T"] / 288.15, 1.5) * ((288.15 + 110.4) / (isa_cr["T"] + 110.4))
    re_proj = round((isa_cr["rho"] * v_cr_ms * mac) / max(1e-7, mu_cr))
    a_sound = math.sqrt(1.4 * 287.05 * isa_cr["T"])
    m_max_mach = round(max(v_cr_ms / a_sound, (float(perf_res["speeds"]["v_max_sl_kmh"]) / 3.6) / isa_atmosphere(0)["a"]), 3)
    
    if engine_type == "jet" or m_max_mach > 0.60:
        recommended_catalog = "Profile nadkrytyczne NASA SC(2) / NACA serii 64A–65 (wysokie Macha)"
    elif re_proj < 500000:
        recommended_catalog = "Katalog Seliga (małe liczby Reynoldsa, UAV / mikrosamoloty)"
    elif re_proj <= 3000000:
        recommended_catalog = "Katalog Wortmanna (szybowce, motoszybowce, samoloty lekkie)"
    else:
        recommended_catalog = "Katalog Abbota & Doenhoffa / Raport NACA Nr 824"
        
    cz_proj = round((2.0 * m0 * G0) / (isa_cr["rho"] * S * (v_cr_ms ** 2)), 3)
    
    if engine_type == "jet" or m_max_mach > 0.60:
        airfoil_candidates = [
            {"name": "NASA SC(2)-0412", "cx_min": 0.0054, "cx_cz_proj": 0.0066, "cz_max": 1.52, "k_max": 86, "stall": "Profil nadkrytyczny o wysokim M_kr > 0.78", "recommended": True},
            {"name": "NACA 64A212", "cx_min": 0.0056, "cx_cz_proj": 0.0069, "cz_max": 1.48, "k_max": 82, "stall": "Laminarny profil szybkościowy dla BizJet / VLJ", "recommended": False},
            {"name": "NACA 65-212", "cx_min": 0.0053, "cx_cz_proj": 0.0067, "cz_max": 1.45, "k_max": 84, "stall": "Niski opór falowy, wymaga przedskrzydeł", "recommended": False},
            {"name": "NACA 23012", "cx_min": 0.0062, "cx_cz_proj": 0.0078, "cz_max": 1.55, "k_max": 75, "stall": "Klasyczny profil porównawczy NACA", "recommended": False}
        ]
        selected_airfoil_name = "NASA SC(2)-0412"
    else:
        airfoil_candidates = [
            {"name": "NACA 23012", "cx_min": 0.0062, "cx_cz_proj": 0.0078, "cz_max": 1.55, "k_max": 75, "stall": "Umiarkowane, wczesne ostrzeżenie", "recommended": True},
            {"name": "NACA 2415", "cx_min": 0.0070, "cx_cz_proj": 0.0084, "cz_max": 1.50, "k_max": 70, "stall": "Bardzo łagodne, bezpieczne dla szkolnych", "recommended": False},
            {"name": "Wortmann FX 61-163", "cx_min": 0.0055, "cx_cz_proj": 0.0065, "cz_max": 1.62, "k_max": 92, "stall": "Ostre przeciągnięcie laminarnego profilu", "recommended": False},
            {"name": "Clark Y", "cx_min": 0.0080, "cx_cz_proj": 0.0092, "cz_max": 1.45, "k_max": 65, "stall": "Płaska dolna powierzchnia, łatwa budowa", "recommended": False}
        ]
        selected_airfoil_name = "NACA 23012"
    # Profil wybrany przez autora (pole w karcie P3) zastępuje roboczego kandydata.
    chosen_airfoil = " ".join(str(params.get("airfoil") or "").split())[:80]
    if chosen_airfoil:
        selected_airfoil_name = chosen_airfoil

    for candidate in airfoil_candidates:
        for key in ('cx_min', 'cx_cz_proj', 'cz_max', 'k_max'):
            candidate[key] = None
        candidate['stall'] = 'Wymaga biegunowej źródłowej dla właściwych Re i Macha.'

    # 2.3 Analiza wrażliwości MTOW
    # Pochodne cząstkowe m0 względem parametrów (Raymer / Roskam)
    # Re-solve the actual nonlinear mass balance for each perturbation.
    # A constant-fraction derivative is incorrect for me/m0 = A*m0**C.
    sens_d_payload = calculate_mass_sizing(dict(params, m_cargo=params.get('m_cargo', 0)+1))['m0'] - m0
    scenarios = [
        ('Masa płatna m_payload', '+10%', {k: params.get(k, 0)*1.1 for k in ('m_pax','m_bag','m_cargo')}),
        ('Masa płatna m_payload', '-10%', {k: params.get(k, 0)*.9 for k in ('m_pax','m_bag','m_cargo')}),
        ('Zasięg obliczeniowy R', '+10%', {'range_km': params['range_km']*1.1}),
        ('Doskonałość przelotowa K', '+10%', {'cruise_ld_p4': params['cruise_ld_p4']*1.1} if params.get('cruise_ld_p4')
                                             else {'mission_ld_factor': params['mission_ld_factor']*1.1}),
        ('Jednostkowe zużycie paliwa SFC', '+10%', {'sfc': params.get('sfc', 0)*1.1}),
    ]
    sensitivity_table = []
    for label, delta, change in scenarios:
        try:
            dm = calculate_mass_sizing({**params, **change})['m0'] - m0
            sensitivity_table.append(dict(var=label, delta=delta, d_mtow_kg=round(dm,1), pct_change=round(100*dm/m0,1)))
        except ValueError:
            sensitivity_table.append(dict(var=label, delta=delta, d_mtow_kg=None, pct_change=None))

    # 2.5 Analiza kosztów B+R i produkcji (BIPOL_2.pdf wzory 13-21, Tab. 5.9, wzór 5.10)
    # Szybowiec nie ma Vmax lotu poziomego; przyjęto VNE = 0,9·VD (CS 22.1505).
    dp = sizing_res["design_point"]
    v_max_cost = float(perf_res["speeds"]["v_max_sl_kmh"]) or 0.9 * float(env_res["speeds"]["v_d_kmh"])
    cost_analysis = calculate_costs(params, m_empty, v_max_cost,
                                    thrust_kn=dp.get("thrust_kn"), power_kw=dp.get("power_kw"), mach_max=m_max_mach)

    p2_data = {
        "mission_profile": mission_profile,
        "airfoil_selection": {
            "reynolds_cruise": re_proj,
            "mach_max": m_max_mach,
            "recommended_catalog": recommended_catalog,
            "cz_proj": cz_proj,
            "candidates": airfoil_candidates,
            "selected_airfoil": selected_airfoil_name
        },
        "sensitivity": {
            "d_mtow_d_payload": sens_d_payload,
            "table": sensitivity_table
        },
        "matching_chart_summary": {
            "engine_type": engine_type,
            "ws_design": sizing_res["design_point"]["ws"],
            "tw_design": sizing_res["design_point"]["tw"],
            "pw_design": sizing_res["design_point"]["pw"],
            "thrust_kn": sizing_res["design_point"].get("thrust_kn"),
            "power_kw": sizing_res["design_point"].get("power_kw"),
            "s_wing_m2": S
        },
        "cost_analysis": cost_analysis,
        "points_max": {"obligatory": 13, "optional": 5, "total": 18}
    }
    
    # =========================================================================
    # PROJEKT 3: PROJEKT WSTĘPNY I ANALIZA MASOWA (27 pkt)
    # =========================================================================
    # 3.1 Profile drawing requires independently verified coordinates.
    c_draw_mm = 200.0
    
    # 3.2 Tabela masowa 3.1 i warianty wyważenia 3.2 z momentami bezwładności (BIPOL_3_2010.pdf)
    x_lemac = bal_res["x_lemac_m"]
    arms = bal_res["arms"]
    bd = mass_res["breakdown"]
    
    # Szczegółowa tabela masowa 3.1 (30-40 pozycji wg programu BIPOL)
    prop_item_7 = "7. Zespół napędowy (silniki turboodrzutowe / dwuprzepływowe)" if engine_type == "jet" else "7. Silnik ze śmigłem i osprzętem"
    prop_item_8 = "8. Gondole silnikowe, pylony i układ wylotowy" if engine_type == "jet" else "8. Łoże silnika, osłony i chłodnice"
    table_3_1 = [
        {"item": "1. Skrzydło (dźwigary, żebra, poszycie)", "mass_kg": bd["m_wing"], "x_m": arms["wing"], "y_m": 0.0, "z_m": 0.15},
        {"item": "2. Kadłub (wręgi, podłużnice, pokrycie)", "mass_kg": bd["m_fuselage"], "x_m": arms["fuselage"], "y_m": 0.0, "z_m": 0.0},
        {"item": "3. Usterzenie poziome ze sterem wysokości", "mass_kg": bd["m_tail"] * 0.65, "x_m": arms["tail"], "y_m": 0.0, "z_m": 0.35},
        {"item": "4. Usterzenie pionowe ze sterem kierunku", "mass_kg": bd["m_tail"] * 0.35, "x_m": arms["tail"], "y_m": 0.0, "z_m": 0.75},
        {"item": "5. Podwozie główne z kołami i hamulcami", "mass_kg": bd["m_gear"] * 0.80, "x_m": arms["gear"], "y_m": 0.95, "z_m": -0.85},
        {"item": "6. Podwozie przednie / kółko ogonowe", "mass_kg": bd["m_gear"] * 0.20, "x_m": round(0.12 * l_f, 2), "y_m": 0.0, "z_m": -0.80},
        {"item": prop_item_7, "mass_kg": bd["m_propulsion"] * 0.85, "x_m": arms["propulsion"], "y_m": 0.0, "z_m": 0.05},
        {"item": prop_item_8, "mass_kg": bd["m_propulsion"] * 0.15, "x_m": round(arms["propulsion"] + 0.2, 2), "y_m": 0.0, "z_m": 0.0},
        {"item": "9. Instalacja paliwowa (zbiorniki, pompy, przewody)", "mass_kg": bd["m_systems"] * 0.25, "x_m": arms["fuel"], "y_m": 0.6, "z_m": 0.1},
        {"item": "10. Instalacja sterowania płatowcem", "mass_kg": bd["m_systems"] * 0.25, "x_m": round(x_lemac + 0.3 * mac, 2), "y_m": 0.0, "z_m": 0.0},
        {"item": "11. Przyrządy pokładowe i awionika" if not unmanned_ac else "11. Autopilot, awionika i łącze danych C2 (UAV)", "mass_kg": bd["m_systems"] * 0.25, "x_m": round(arms["crew"] + 0.3, 2), "y_m": 0.0, "z_m": 0.25},
        {"item": "12. Wyposażenie kabiny, fotele i pasy" if not unmanned_ac else "12. Instalacja elektryczna, zasilanie i okablowanie misji (UAV)", "mass_kg": bd["m_systems"] * 0.25, "x_m": arms["crew"], "y_m": 0.0, "z_m": -0.1},
    ]
    if unmanned_ac:
        table_3_1 += [
            {"item": "13. Głowica optoelektroniczna / sensory (60% ładunku)", "mass_kg": m_payload * 0.60, "x_m": arms.get("payload_sensor", arms["crew"]), "y_m": 0.0, "z_m": -0.35},
            {"item": "14. Wyposażenie zadaniowe w przedziale ładunkowym (40% ładunku)", "mass_kg": m_payload * 0.40, "x_m": arms.get("payload_bay", arms["pax_front"]), "y_m": 0.0, "z_m": 0.0},
        ]
    else:
        table_3_1 += [
            {"item": "13. Załoga (pilot + instruktor)", "mass_kg": m_crew, "x_m": arms["crew"], "y_m": 0.0, "z_m": 0.1},
            {"item": "14. Pasażerowie / Ładunek użyteczny", "mass_kg": m_payload, "x_m": arms["pax_front"], "y_m": 0.0, "z_m": 0.1},
        ]
    table_3_1 += [
        {"item": "15. Paliwo w zbiornikach skrzydłowych", "mass_kg": m_fuel, "x_m": arms["fuel"], "y_m": 1.2, "z_m": 0.15}
    ]
    
    group_indices = [([0], 'wing'), ([1], 'fuselage'), ([2,3], 'tail'),
                     ([4,5], 'gear'), ([6,7], 'propulsion'), ([8,9,10,11], 'systems')]
    for indices, key in group_indices:
        for index in indices:
            table_3_1[index]['x_m'] = arms[key]
        target = bd['m_' + key]
        table_3_1[indices[-1]]['mass_kg'] += target - sum(table_3_1[i]['mass_kg'] for i in indices)
    if not unmanned_ac:
        table_3_1[13]['x_m'] = arms['payload_equivalent']
    # Left and right components are represented by their common centroid.
    # Spread for inertia is separate from centroid position (symmetry yCG=0).
    for row in table_3_1:
        row['y_rms_m'] = abs(row['y_m'])
        row['y_m'] = 0.0

    # Obliczenie momentów bezwładności w środku ciężkości Jx, Jy, Jz i dewiacji Jxz (wzory 2.3 - 2.4 z BIPOL_3_2010.pdf)
    xcg_mtow = float(next(s for s in bal_res["loading_states"] if s["key"] == "mtow")["xcg_m"])
    ycg_mtow = 0.0
    zcg_mtow = sum(row["mass_kg"]*row["z_m"] for row in table_3_1) / sum(row["mass_kg"] for row in table_3_1)
    
    jx_cg = 0.0
    jy_cg = 0.0
    jz_cg = 0.0
    jxz_cg = 0.0
    for p in table_3_1:
        mi = p["mass_kg"]
        dx = p["x_m"] - xcg_mtow
        dy = p["y_rms_m"]
        dz = p["z_m"] - zcg_mtow
        jx_cg += mi * (dy**2 + dz**2)
        jy_cg += mi * (dx**2 + dz**2)
        jz_cg += mi * (dx**2 + dy**2)
        jxz_cg += mi * (dx * dz)
        
    jx_cg = round(jx_cg, 1)
    jy_cg = round(jy_cg, 1)
    jz_cg = round(jz_cg, 1)
    jxz_cg = round(jxz_cg, 1)
    
    # Przeliczenie twierdzeniem Steinera do punktu 1/4 SCA (wzór punktu 10 z BIPOL_3_2010.pdf)
    x_quarter_mac = round(x_lemac + 0.25 * mac, 3)
    dx_steiner = x_quarter_mac - xcg_mtow
    jy_quarter_mac = round(jy_cg + m0 * (dx_steiner ** 2 + zcg_mtow ** 2), 1)
    jz_quarter_mac = round(jz_cg + m0 * (dx_steiner ** 2), 1)
    
    prop_sel = paturski_res["p5_propulsion_characteristics"].get("propeller_selection", {})
    # Cz(α), Cm(α), Cx(Cz) płata (BIPOL I, opis Projektu 3): Tabela 2.2 Paturskiego,
    # Cm względem noska ŚCA: Cm = Cm_SA − x̄_SA·Cz (środek aerodynamiczny profilu).
    p2w = paturski_res["p2_wing_aero"]
    wing_alpha_table = [{"alpha_deg": r["alpha_p_deg"], "cz": r["cz_inf"], "cx": r["cx_p_prime"],
                         "cm_le": round(p2w["cm_sa_profile"] - p2w["x_sa_bar"] * r["cz_inf"], 4)}
                        for r in paturski_res["p3_aircraft_aero"]["table_2_2_complete"]]
    from calculations.airfoils import airfoil_200mm
    af_table, af_svg = [], ""
    af_note = (f"Profil {selected_airfoil_name} o cięciwie 200 mm: wyznacz rzędne poniżej (profile NACA 4- i 5-cyfrowe "
               "program liczy analitycznie) albo wklej rzędne wybranego profilu z katalogu.")
    # Profile NACA liczy się analitycznie (dokładna geometria, nie pomiar); dla innych rzędne wkleja autor.
    try:
        profile = airfoil_200mm(selected_airfoil_name, str(params.get("airfoil_coordinates") or ""))
        af_table, af_svg, af_note = profile["table"], profile["svg"], profile["note"]
    except ValueError as error:
        af_note = str(error)

    track_g = float(geom_res.get("gear", {}).get("track", 0.24 * b))
    wheelbase_g = max(0.8, bal_res.get("arms", {}).get("gear", 0.45 * l_f) - 0.12 * l_f)
    h_cg_g = max(0.4, zcg_mtow - (-0.80 * d_f))
    dn_g = (track_g / 2.0) / math.sqrt(1.0 + (track_g / (2.0 * wheelbase_g)) ** 2)
    turnover_angle_val = round(math.degrees(math.atan2(h_cg_g, dn_g)), 1)
    p3_data = {
        "geometry_trends": trend_analysis.get("geometry_trends_analysis"),
        "blueprint_checks": {
            "engine_type": engine_type,
            "pilot_vision_angle_deg": None,
            "propeller_tip_mach": prop_sel.get("ma_tip_kl", round((math.pi * 1.85 * (2400.0 / 60.0)) / a_sound, 2)) if engine_type == "prop" else None,
            "propeller_diameter_m": prop_sel.get("diameter_m", 1.85) if engine_type == "prop" else None,
            "propeller_cd": prop_sel.get("cd_dimensionless") if engine_type == "prop" else None,
            "prop_ground_clearance_m": None,
            "fan_intake_mach": None,
            "nacelle_ground_clearance_m": None,
            "gear_turnover_angle_deg": turnover_angle_val,
            "gear_cg_post_landing_mac_pct": None
        },
        "airfoil_200mm_table": af_table,
        "airfoil_200mm_svg": af_svg,
        "airfoil_coordinates_note": af_note,
        "table_3_1_components": table_3_1,
        "table_3_2_loading_states": bal_res["loading_states"],
        "inertia_moments": {
            "jx_cg_kgm2": jx_cg,
            "jy_cg_kgm2": jy_cg,
            "jz_cg_kgm2": jz_cg,
            "jxz_cg_kgm2": jxz_cg,
            "method": "Przybliżenie skupionych mas zespołów, bez własnych momentów bezwładności. Nie jest modelem konstrukcyjnym.",
            "zcg_m": zcg_mtow,
            "quarter_mac_x_m": x_quarter_mac,
            "jy_quarter_mac_kgm2": jy_quarter_mac,
            "jz_quarter_mac_kgm2": jz_quarter_mac
        },
        "isolated_wing_aero": {
            "cz_alpha_deg": round(aero_res["a_w_deg"], 3),
            "cz_alpha_paturski_deg": paturski_res["p2_wing_aero"]["a_wing_paturski_deg"],
            "cz_alpha_paturski_rad": paturski_res["p2_wing_aero"]["a_wing_paturski_rad"],
            "tau_glauert": paturski_res["p2_wing_aero"]["tau_glauert"],
            "delta_glauert": paturski_res["p2_wing_aero"]["delta_glauert"],
            "re_1_stall": paturski_res["p2_wing_aero"]["re_1_stall"],
            "cx_min_1_tunnel": paturski_res["p2_wing_aero"]["cx_min_1_tunnel"],
            "cx_min_2_corrected": paturski_res["p2_wing_aero"]["cx_min_2_corrected"],
            "delta_cx_tech": paturski_res["p2_wing_aero"]["delta_cx_tech"],
            "ca_paturski_m": paturski_res["p2_wing_aero"]["ca_paturski_m"],
            "xn_mac_m": paturski_res["p2_wing_aero"]["xn_mac_m"],
            "cm_0_wing": paturski_res["p2_wing_aero"]["cm_sa_profile"],
            "cx_0_wing": aero_res.get("component_drag_buildup", [{"cx0_i": round(cx0 * 0.44, 4)}])[0]["cx0_i"]
        },
        "wing_alpha_table": wing_alpha_table,
        "schrenk_summary": {
            "points": geom_res["schrenk"],
            "max_cz1": geom_res.get("schrenk_Pinpoint", {}).get("max_cz1", 1.08),
            "stall_eta_span": geom_res.get("schrenk_Pinpoint", {}).get("stall_eta_span", 0.55),
            "stall_y_m": geom_res.get("schrenk_Pinpoint", {}).get("stall_y_m", round(0.55 * 0.5 * b, 2)),
            "cz_max_wing_est": round((cz_max_clean * 1.06) / max(1.0, geom_res.get("schrenk_Pinpoint", {}).get("max_cz1", 1.08)), 3)
        },
        "control_surfaces": geom_res.get("control_surfaces", {}),
        "points_max": {"obligatory": 22, "optional": 5, "total": 27}
    }
    
    # =========================================================================
    # PROJEKT 4: CHARAKTERYSTYKI AERODYNAMICZNE SAMOLOTU (15 pkt)
    # =========================================================================
    # 4.1 Zestawienie oporów szkodliwych elementów płatowca metodą Component Buildup (Cf * FF * Q * Swet / Sref)
    parasite_drag_breakdown = aero_res.get("component_drag_buildup", [
        {"component": "Płat nośny (tarcie + kształt)", "re": 4500000, "cf": 0.0034, "ff": 1.22, "q": 1.0, "swet_m2": round(S * 1.75, 2), "cx0_i": round(cx0 * 0.44, 4), "share_pct": 44.0},
        {"component": "Kadłub (opływ i interferencja)", "re": 18000000, "cf": 0.0027, "ff": 1.18, "q": 1.0, "swet_m2": round(S * 1.45, 2), "cx0_i": round(cx0 * 0.32, 4), "share_pct": 32.0},
        {"component": "Usterzenie poziome i pionowe", "re": 3100000, "cf": 0.0036, "ff": 1.19, "q": 1.05, "swet_m2": round(S * 0.55, 2), "cx0_i": round(cx0 * 0.12, 4), "share_pct": 12.0},
        {"component": "Podwozie (stałe / gondole)", "re": 0, "cf": 0.0, "ff": 1.0, "q": 1.0, "swet_m2": 0.0, "cx0_i": round(cx0 * 0.08, 4), "share_pct": 8.0},
        {"component": "Chłodnice, wloty i wyposażenie", "re": 0, "cf": 0.0, "ff": 1.0, "q": 1.0, "swet_m2": 0.0, "cx0_i": round(cx0 * 0.04, 4), "share_pct": 4.0}
    ])
    
    # 4.1a Cz(α), Cm(α), K(α), E(α) i biegunowe wyważone dla skrajnych położeń ŚC
    # (BIPOL I, opis Projektu 4); metoda Tabeli 2.2 Paturskiego z obciążeniem usterzenia.
    glide = perf_res['glide']
    rho_glide = isa_atmosphere(glide.get('altitude_m', h_cr))['rho']
    cz_cruise = 2.0 * m0 * G0 / (isa_cr['rho'] * S * (v_cr_ms ** 2))
    cg_characteristics = aircraft_characteristics_for_cg(
        paturski_res["p3_aircraft_aero"],
        bal_res["cg_range"]["forward_pct"] / 100.0,
        bal_res["cg_range"]["aft_pct"] / 100.0,
        bal_res["neutral_point"]["x_n_mac_pct"] / 100.0,
        min(cz_cruise, 0.9 * cz_max_clean), m0, S, rho_glide)

    def sink_at(polar, v_kmh):
        pts = sorted(polar["points"], key=lambda q: q["v_kmh"])
        for lo, hi in zip(pts, pts[1:]):
            if lo["v_kmh"] <= v_kmh <= hi["v_kmh"]:
                t = (v_kmh - lo["v_kmh"]) / max(1e-9, hi["v_kmh"] - lo["v_kmh"])
                return round(lo["w_ms"] + t * (hi["w_ms"] - lo["w_ms"]), 3)
        return None

    # 4.2 Biegunowa prędkości w locie ślizgowym w(V) dla skrajnych położeń ŚC (BIPOL_4.pdf)
    polars_cg = cg_characteristics["speed_polars"]
    glide_polar_data = [dict(v_kmh=r['v_kmh'], w_sink_ms=r['sink_ms'],
                             w_sink_aft_ms=sink_at(polars_cg["aft"], r['v_kmh']),
                             w_sink_fwd_ms=sink_at(polars_cg["forward"], r['v_kmh']),
                             k_glide=r['ld']) for r in glide['points']]
    w_min_val = glide['minimum_sink']['sink_ms']
    v_ekon = glide['minimum_sink']['v_kmh']
    k_max_glide = glide['best_glide']['ld']
    v_opt = glide['best_glide']['v_kmh']

    # 4.3 Mechanizacja: project requirement, not a universal CS-23 speed limit.
    high_lift_summary = {
        "clean": {"cz_max": cz_max_clean, "vs_kmh": perf_res["speeds"]["vs_clean_kmh"], "cx0": aero_res["cx0_clean"]},
        "takeoff": {"cz_max": aero_res["cz_max_to"], "vs_kmh": perf_res["speeds"]["vs_to_kmh"], "cx0": aero_res["cx0_to"], "delta_cz": round(aero_res["cz_max_to"] - cz_max_clean, 2)},
        "landing": {"cz_max": cz_max_lnd, "vs_kmh": perf_res["speeds"]["vs_lnd_kmh"], "cx0": aero_res["cx0_lnd"], "delta_cz": round(cz_max_lnd - cz_max_clean, 2)},
        "stall_requirement": stall_requirement(params, perf_res),
        "control_surfaces": geom_res.get("control_surfaces", {})
    }
    for phase in ('clean', 'takeoff', 'landing'):
        high_lift_summary[phase]['flap_deflection_deg'] = aero_res['flap_configurations'][phase]['deflection_deg']
    
    p4_data = {
        "drag_breakdown": parasite_drag_breakdown,
        "aerodynamic_polars": aero_res["polar_points"],
        "glide_polar": {
            "points": glide_polar_data,
            "v_ekon_kmh": v_ekon,
            "w_min_ms": w_min_val,
            "v_opt_kmh": v_opt,
            "k_max": round(k_max_glide, 1),
            "table_4_1_paturski": paturski_res["p4_gliding_flight"]["table_4_1_glide"],
            "comparison_paturski": paturski_res["p4_gliding_flight"]["glide_comparison"],
            "cg_polars": polars_cg,
        },
        "cg_characteristics": cg_characteristics,
        "high_lift": high_lift_summary,
        "paturski_aero": paturski_res["p3_aircraft_aero"],
        "paturski_propulsion": paturski_res["p5_propulsion_characteristics"],
        "points_max": {"obligatory": 5, "optional": 10, "total": 15}
    }
    
    # =========================================================================
    # PROJEKT 5: OSIĄGI SAMOLOTU (15 pkt) — Tabela 6.2, 6.3 wg Z. Paturskiego
    # =========================================================================
    # 5.1 Wykres ofertowy samolotu z bezpośredniej metodyki dr. Paturskiego (Projekt nr 6, Tabela 6.2)
    p6_ml = paturski_res["p6_performance_paturski"]
    t6_2_ml = p6_ml.get("table_6_2_climb_and_ceilings", {})
    ceilings_ml = t6_2_ml.get("ceilings", {})
    alts_tbl_ml = t6_2_ml.get("altitudes_table", [])

    offer_chart_data = []
    for r in alts_tbl_ml:
        offer_chart_data.append({
            "h_m": r["h_m"],
            "wy_max_ms": r["w_max_ms"],
            "inv_wy_sm": r["inv_w_max_s_m"],
            "gamma_max_deg": r["gamma_max_deg"],
            "v_gamma_kmh": r["v_gamma_kmh"],
            "time_to_climb_s": r["th_s"],
            "time_to_climb_min": r["th_min"],
            "v_min_kmh": r["v_min_kmh"],
            "v_max_kmh": r["v_max_kmh"],
            "v_wy_kmh": r["v_w_kmh"]
        })

    # Ceilings use the propulsion-specific ROC threshold; time integrates dh/ROC.
    hp_service_m = ceilings_ml.get("h_p_practical_m", float(perf_res["ceiling"]["service_ceiling_m"]))
    ht_theoretical_m = ceilings_ml.get("h_t_theoretical_m", float(perf_res["ceiling"]["absolute_ceiling_m"]))
    thp_analytical_s = ceilings_ml.get("t_hp_climb_to_practical_ceiling_s", 0.0)
    thp_analytical_min = ceilings_ml.get("t_hp_climb_to_practical_ceiling_min", 0.0)
        
    # Compare real integrations of the same polar and cruise fuel allocation.
    # No synthetic percentage changes between methods or assumed glider range.
    ranges = paturski_res['p6_performance_paturski']['range_endurance_6_5']
    cruise_row = next((row for row in ranges['table_6_3'] if row['requested_speed']), None)
    range_km_m1 = endurance_h_m1 = range_km_m2 = endurance_h_m2 = None
    range_km_m3 = ranges['range_at_requested_speed_km']
    endurance_h_m3 = ranges['endurance_at_requested_speed_h']
    if cruise_row:
        range_km_m2, endurance_h_m2 = cruise_row['l_breguet_km_unrounded'], cruise_row['t_breguet_h_unrounded']
        if engine_type == 'jet':
            endurance_h_m1 = endurance_h_m2
            range_km_m1 = v_cr_kmh * endurance_h_m1
        else:
            range_km_m1 = range_km_m2
            endurance_h_m1 = range_km_m1 / v_cr_kmh
    range_endurance_methods = [
        dict(method='Stałe V i Cz, zmienna wysokość — idealny model Bregueta',
             range_km=range_km_m1, endurance_h=endurance_h_m1),
        dict(method='Stała wysokość i Cz, V zmienne z masą — idealny model Bregueta',
             range_km=range_km_m2, endurance_h=endurance_h_m2),
        dict(method='Stała wysokość i wymagana prędkość — całka arctan',
             range_km=range_km_m3, endurance_h=endurance_h_m3),
    ]

    # Compare against actual inputs; do not invent an earlier design iteration.
    powered = engine_type != 'none'
    cruise = perf_res['cruise_check']
    cruise_ok = powered and cruise['cl'] <= cruise['cl_max'] and cruise['climb_ms'] >= 0
    climb_ok = powered and perf_res['climb']['wy_max_ms'] >= params['climb_rate_ms']
    takeoff = perf_res['takeoff']['distance_to_15m']
    takeoff_req = params.get('takeoff_distance_m')
    takeoff_ok = powered and takeoff is not None and bool(takeoff_req) and takeoff <= takeoff_req
    mission_range_km = perf_res.get('mission_range', {}).get('total_available_km', range_km_m3)
    range_ok = powered and perf_res.get('mission_range', {}).get('passed', mission_range_km is not None and mission_range_km >= params['range_km'])
    verdict = lambda ok: 'Spełnione wymaganie projektu' if ok else 'Niespełnione wymaganie projektu'
    table_5_1_critical = [
        dict(param='Rozpiętość skrzydeł b [m]', project_assumed=params.get('wingspan_m')
             if params.get('wing_input_mode') in ('span_area', 'span_aspect') else None,
             actual_calc=b, comment='Wartość zadana tylko w trybie narzuconej rozpiętości.'),
        dict(param='Powierzchnia nośna S [m²]', project_assumed=params.get('wing_area_m2')
             if params.get('wing_input_mode') in ('span_area', 'area_aspect') else None,
             actual_calc=S, comment='Wartość zadana tylko w trybie narzuconej powierzchni.'),
        dict(param='Masa startowa MTOW [kg]', project_assumed=None, actual_calc=m0,
             comment='Wynik bilansu masowego; nie podano niezależnej masy wymaganej.'),
        dict(param='Vmax TAS na poziomie morza [km/h]', project_assumed=None,
             actual_calc=perf_res['speeds']['v_max_sl_kmh'] if perf_res['level_flight_available_sl'] else None,
             comment='Nie zadano osobnego wymagania Vmax; przelot sprawdzono na jego wysokości.'),
        dict(param='Prędkość przelotowa Vcr TAS [km/h]', project_assumed=v_cr_kmh,
             actual_calc=v_cr_kmh if cruise_ok else None, comment=verdict(cruise_ok) if powered else 'Lot ślizgowy; brak napędu.'),
        dict(param='Prędkość wznoszenia w_y,max [m/s]', project_assumed=params['climb_rate_ms'] if powered else None,
             actual_calc=perf_res['climb']['wy_max_ms'] if powered else None,
             comment=verdict(climb_ok) if powered else 'Nie dotyczy wznoszenia z napędem.'),
        dict(param='Całkowita długość startu do 15 m [m]', project_assumed=takeoff_req if powered else None,
             actual_calc=takeoff if powered else None, comment='Nie wyznaczono operacji na wodzie.' if params.get('operating_surface') == 'water' else verdict(takeoff_ok) if powered else 'Nie rozpatrywano samodzielnego startu.'),
        dict(param='Zasięg przy wymaganej prędkości [km]', project_assumed=params['range_km'] if powered else None,
             actual_calc=mission_range_km, comment=verdict(range_ok) if powered else 'Nie dotyczy zasięgu paliwowego.'),
    ]
    performance_recommendation = ('Sprawdź wyniki lotu ślizgowego i sposób startu.' if not powered else
        'Przyjęte wymagania przelotu, wznoszenia, startu i zasięgu spełniono w modelu wstępnym; sprawdź pozostałe kryteria.'
        if all((cruise_ok, climb_ok, takeoff_ok, range_ok)) else
        'Projekt nie spełnia wszystkich wymagań osiągów. Skoryguj założenia wskazane w tabeli i przelicz projekt.')

    # Krytyczna ocena (BIPOL I, Projekt 5): przyczyny rozbieżności między założeniami P2 a wynikami.
    performance_findings = []
    k_assumed = mass_res["mission_assumptions"].get("k_max_preliminary")
    ra_cr = next((row for row in paturski_res["p6_performance_paturski"]["range_endurance_6_5"].get("by_altitude", [])
                  if row["label"] == "wysokość przelotowa"), None)
    if powered and not cruise_ok:
        performance_findings.append(
            f"Na wysokości {h_cr:.0f} m potrzebna moc przelotowa {cruise['required_w'] / 1000:.0f} kW przekracza dostępną "
            f"{cruise['available_w'] / 1000:.0f} kW" + (f"; lot poziomy jest możliwy do około {ra_cr['v_max_kmh']:.0f} km/h" if ra_cr else "")
            + f". Biegunowa z P4 ma Cx0 = {aero_res['cx0_clean']:.4f}, a dobór napędu w P2 przyjął Cx0 = {params['cx0']:.4f}. "
            "Przyjmij w P2 wartości z P4 (bilans uściślony P2←P4) albo zmniejsz prędkość lub wysokość przelotu.")
    if powered and cruise_ok and not range_ok and k_assumed:
        m_mid = paturski_res["p6_performance_paturski"]["range_endurance_6_5"].get("m_obl_avg_kg", m0)
        cz_cr = 2.0 * m_mid * G0 / (isa_cr["rho"] * S * v_cr_ms ** 2)
        k_cr = cz_cr / (aero_res["cx0_clean"] + aero_res["k_clean"] * cz_cr ** 2)
        k_bilans = mass_res["mission_assumptions"]["ld_factor"] * k_assumed
        performance_findings.append(
            f"Bilans masy (P2) przyjął w przelocie K = 0,94·Kmax = {k_bilans:.1f}. Biegunowa z P4 przy {v_cr_kmh:.0f} km/h "
            f"na {h_cr:.0f} m daje K = {k_cr:.1f} (Cz = {cz_cr:.3f})"
            + (f"; największy zasięg odpowiada około {ra_cr['v_l_max_kmh']:.0f} km/h" if ra_cr else "")
            + ". Zmniejsz prędkość przelotową w stronę prędkości największego zasięgu albo utwórz wariant z bilansem uściślonym P2←P4, który dobiera paliwo przy tej doskonałości.")
    if powered and not climb_ok:
        performance_findings.append("Prędkość wznoszenia jest mniejsza od wymaganej: zwiększ moc (ciąg) albo zmniejsz obciążenie powierzchni.")
    if powered and not takeoff_ok and takeoff_req:
        performance_findings.append("Długość startu przekracza wymaganą: zwiększ Cz,max do startu, moc (ciąg) albo powierzchnię nośną.")

    p5_data = {
        "offer_chart": offer_chart_data,
        "ceiling_summary": {
            "hp_service_m": round(hp_service_m),
            "ht_theoretical_m": round(ht_theoretical_m),
            "thp_min": thp_analytical_min,
            "thp_s": round(thp_analytical_s),
        },
        "range_endurance_comparison": range_endurance_methods,
        "paturski_p6": paturski_res["p6_performance_paturski"],
        "takeoff_landing": {
            "ground_roll_m": perf_res["takeoff"]["ground_roll_m"],
            "transition_m": perf_res["takeoff"].get("transition_m", 0),
            "climb_to_15m_m": perf_res["takeoff"].get("climb_to_15m_m", 0),
            "air_distance_m": perf_res["takeoff"].get("air_distance_m", 0),
            "climb_angle_deg": perf_res["takeoff"].get("climb_angle_deg", 0),
            "takeoff_to_15m_m": perf_res["takeoff"].get("distance_to_15m", perf_res["takeoff"].get("takeoff_to_15m_m", 0)),
            "air_approach_m": perf_res["landing"].get("air_approach_m", 0),
            "free_roll_m": perf_res["landing"].get("free_roll_m", 0),
            "braking_roll_m": perf_res["landing"].get("braking_roll_m", 0),
            "landing_ground_roll_m": perf_res["landing"]["ground_roll_m"],
            "landing_from_15m_m": perf_res["landing"].get("distance_from_15m", perf_res["landing"].get("landing_from_15m_m", 0))
        },
        "critical_evaluation_table_5_1": table_5_1_critical,
        "recommendations": performance_recommendation,
        "performance_findings": performance_findings,
        "points_max": {"obligatory": 2, "optional": 13, "total": 15}
    }
    
    # =========================================================================
    # PROJEKT 6: OBWIEDNIA OBCIĄŻEŃ DOPUSZCZALNYCH (20 pkt)
    # =========================================================================
    # 6.1 Punkty charakterystyczne i 6.2 pętla klapowa z obwiedni: CS-23 Amdt 4 / CS-25 / CS-22 wg kategorii
    limits = env_res.get("limits", {})
    gusts = env_res.get("gust_factors", {})
    points_vn = env_res["key_points"]
    flap_loop = env_res["flap"]["loop"]
    v_f_kmh = env_res["flap"]["v_f_kmh"]

    p6_data = {
        "regulations_standard": f"{law_sub['design_code']} – podkategoria {law_sub['name']} (t.j. Dz. U. z 2025 r. poz. 1137); {limits.get('load_factor_reference', '')}",
        "points_table": points_vn,
        "flap_envelope_loop": flap_loop,
        "v_f_kmh": v_f_kmh,
        "n_flap": env_res["flap"]["n_flap"],
        "mass_ratio_mu_g": gusts.get("mu_g", 15.0),
        "alleviation_factor_kg": gusts.get("k_g", 0.70),
        "safety_factor_nu": limits.get("safety_factor_nu", 1.5),
        "ultimate_loads": {
            "n_ult_pos": limits.get("n_ult_pos", 5.7),
            "n_ult_neg": limits.get("n_ult_neg", -2.28)
        },
        "points_max": {"obligatory": 15, "optional": 5, "total": 20}
    }
    
    # =========================================================================
    # PODSUMOWANIE SEMESTRALNE BIPOL I (100 PKT)
    # =========================================================================
    semester_score_summary = {
        "p1": {"name": "Projekt 1: Projekt Koncepcyjny", "week": 3, "pts_max": 5, "pts_ob": 3, "pts_op": 2},
        "p2": {"name": "Projekt 2: Studium Wykonalności", "week": 5, "pts_max": 18, "pts_ob": 13, "pts_op": 5},
        "p3": {"name": "Projekt 3: Projekt Wstępny i Analiza Masowa", "week": 8, "pts_max": 27, "pts_ob": 22, "pts_op": 5},
        "p4": {"name": "Projekt 4: Charakterystyki Aerodynamiczne", "week": 10, "pts_max": 15, "pts_ob": 5, "pts_op": 10},
        "p5": {"name": "Projekt 5: Osiągi Samolotu", "week": 11, "pts_max": 15, "pts_ob": 2, "pts_op": 13},
        "p6": {"name": "Projekt 6: Obwiednia Obciążeń", "week": 14, "pts_max": 20, "pts_ob": 15, "pts_op": 5},
        "totals": {
            "obligatory_max": 60,
            "optional_max": 40,
            "projects_total_max": 100,
            "quizzes_total_max": 100,
            "course_total_max": 200,
            "passing_threshold_projects": 50,
            "passing_threshold_quizzes": 50
        }
    }
    
    return {
        "p1": p1_data,
        "p2": p2_data,
        "p3": p3_data,
        "p4": p4_data,
        "p5": p5_data,
        "p6": p6_data,
        "paturski_ml": paturski_res,
        "semester_summary": semester_score_summary
    }
