"""
Moduł audytu inżynierskiego i weryfikatora pułapek konstrukcyjnych (BiPOL Requiem).
Ocenia projekt pod kątem krytycznych kryteriów bezpieczeństwa, geometrii,
stateczności oraz typowych pytań zadawanych na obronach projektów (MEiL PW).

Autor metodyki i kryteriów:
- J. Danilecki: "Konstruowanie samolotów",
- D. Raymer: "Aircraft Design: A Conceptual Approach",
- E. Torenbeek: "Synthesis of Subsonic Airplane Design",
- Z. Paturski: "Przewodnik po projektach z Mechaniki Lotu",
- Wymagania przepisów zdatności CS-23, CS-25, CS-22, LTF-UL.
"""
import math
from calculations.atmosphere import G0, RHO0
from calculations.paturski_ml import wing_alpha_deg


def perform_engineering_audit(result: dict) -> dict:
    """
    Wykonuje pełny audyt inżyniersko-dydaktyczny projektu.
    Zwraca zestaw weryfikacji (checks), wskaźniki liczbowe (metrics)
    oraz spersonalizowany symulator pytań na obronę / zejściówkę (defense_questions).
    """
    params = result.get("params", {})
    geom = result.get("geometry", {})
    mass = result.get("mass", {})
    aero = result.get("aerodynamics", {})
    perf = result.get("performance", {})
    balance = result.get("balance", {})
    sizing = result.get("sizing", {})

    wing = geom.get("wing", {})
    fuse = geom.get("fuselage", {})
    ht = geom.get("horizontal_tail", {})
    vt = geom.get("vertical_tail", {})
    gear = geom.get("gear", {})

    b = float(wing.get("b", 10.0))
    S = float(wing.get("S", 14.0))
    AR = float(wing.get("AR", 8.0))
    mac = float(wing.get("mac", 1.4))
    l_f = float(fuse.get("length", 8.0))
    d_f = float(fuse.get("diameter", 1.2))
    m0 = float(mass.get("m0", 1000.0))
    engine_type = params.get("engine_type", "prop")
    n_engines = max(1, int(params.get("n_engines", 1) or 1))

    checks = []
    metrics = {}

    # =========================================================================
    # 1. KĄT PRZEWROTKI BOCZNEJ PODWOZIA (Tipover Angle) - Raymer §11.2 / Torenbeek
    # =========================================================================
    track = float(gear.get("track", 0.24 * b))
    x_gear = float(balance.get("arms", {}).get("gear", 0.45 * l_f))
    x_nose = max(0.5, 0.12 * l_f)
    wheelbase = max(0.8, x_gear - x_nose)

    wing_config = params.get("wing_config", "low")
    if wing_config in ("high", "braced_high"):
        z_cg_fuse = 0.18 * d_f
    elif wing_config == "mid":
        z_cg_fuse = 0.02 * d_f
    else:
        z_cg_fuse = -0.10 * d_f

    z_ground = -0.80 * d_f
    h_cg_ground = max(0.4, z_cg_fuse - z_ground)

    # Odległość prostopadła od punktu styku do linii koło przednie - koło główne
    d_n = (track / 2.0) / math.sqrt(1.0 + (track / (2.0 * wheelbase)) ** 2)
    tipover_angle_deg = math.degrees(math.atan2(h_cg_ground, d_n))
    metrics["tipover_angle_deg"] = round(tipover_angle_deg, 1)
    metrics["track_m"] = round(track, 2)
    metrics["wheelbase_m"] = round(wheelbase, 2)
    metrics["h_cg_ground_m"] = round(h_cg_ground, 2)

    # Wykład 4 (podwozia): kąt przewrócenia na bok mniejszy niż 60°; Torenbeek zaleca ≤ 55°, Raymer dopuszcza 63°.
    tipover_ok = tipover_angle_deg < 60.0
    checks.append({
        "id": "tipover_angle",
        "category": "Podwozie i bezpieczeństwo naziemne",
        "title": "Kąt przewrócenia na bok (Tipover angle)",
        "value": f"{tipover_angle_deg:.1f}°".replace(".", ","),
        "required": "< 60° (wykład 4 BIPOL I; zalecane ≤ 55°)",
        "passed": tipover_ok,
        "severity": "ok" if tipover_angle_deg <= 55.0 else "warning",
        "didactic_simple": (
            "Gdy lądujesz z bocznym wiatrem lub gwałtownie skręcasz na drodze kołowania, "
            "samolot nie może przewrócić się na skrzydło. Kąt wywrotki zależy od szerokości "
            "rozstawu kół i wysokości środka ciężkości."
        ),
        "engineering_note": (
            f"Kąt przewrócenia wynosi {tipover_angle_deg:.1f}°. ".replace(".", ",", 1)
            + ("Spełnia wymaganie wykładu (< 60°) i zalecenie Torenbeeka (≤ 55°)." if tipover_angle_deg <= 55.0 else
               "Spełnia wymaganie wykładu (< 60°), ale przekracza zalecane 55° — sprawdź rozstaw kół." if tipover_ok else
               "Przekracza 60°: zbyt wąski rozstaw kół lub zbyt wysoko położony środek masy. "
               "Zwiększ rozstaw podwozia głównego lub rozważ mocowanie goleni do skrzydła.")
        )
    })

    # =========================================================================
    # 2. KĄT OCHRONY OGONA PRZED UDERZENIEM O PAS (Tailstrike Clearance)
    # =========================================================================
    # Wykład 7 (przykład projektu, slajd 17): kąt od koła głównego do ogona ≥ α przy Cz_max,
    # kąt między pionem przez ŚC a prostą ŚC–koło główne ≥ α przy 0,9·Cz_max + 3°.
    # Kąty natarcia płata z tabeli 2.2 (względem cięciwy, bez kąta zaklinowania).
    deg = lambda v: f"{v:.1f}°".replace(".", ",")  # noqa: E731
    metres = lambda v: f"{v:.2f} m".replace(".", ",")  # noqa: E731
    sailplane = params.get("aircraft_type") == "glider"  # szybowiec stoi na kole głównym i płozie ogonowej
    trim_model = result.get("bipol_projects", {}).get("p4", {}).get("paturski_aero", {}).get("trim_model")
    if trim_model:
        alpha_09 = wing_alpha_deg(trim_model, 0.9 * trim_model["cz_max_clean"])
        alpha_max = wing_alpha_deg(trim_model, trim_model["cz_max_clean"])
    else:
        alpha_09 = alpha_max = None
    tail_required = alpha_max if alpha_max is not None else 12.0
    tipback_required = alpha_09 + 3.0 if alpha_09 is not None else 15.0

    z_tail_bumper = -0.20 * d_f
    h_tail_clearance = z_tail_bumper - z_ground
    tail_angle = lambda x: math.degrees(math.atan2(h_tail_clearance, max(0.5, l_f - x)))  # noqa: E731
    tailstrike_angle_deg = tail_angle(x_gear)
    metrics["tailstrike_angle_deg"] = round(tailstrike_angle_deg, 1)
    metrics["tailstrike_required_deg"] = round(tail_required, 1)

    tailstrike_ok = tailstrike_angle_deg >= tail_required
    checks.extend([] if sailplane else [{
        "id": "tailstrike_clearance",
        "category": "Geometria kadłuba i lądowanie",
        "title": "Kąt ochrony ogona (Tailstrike clearance angle)",
        "value": deg(tailstrike_angle_deg),
        "required": (f"≥ α przy Cz_max = {deg(tail_required)} (wykład 7)" if alpha_max is not None
                     else "≥ 12,0° (ochrona przed tail-strike)"),
        "passed": tailstrike_ok,
        "severity": "ok" if tailstrike_ok else "warning",
        "didactic_simple": (
            "Gdy pilot podczas lądowania zadziera nos do góry (wyrównanie ze spłaszczeniem), "
            "ogon samolotu opada w dół. Kąt z tyłu kadłuba musi być wystarczająco stromy, "
            "by ogon nie przytarł o beton nawet przy kącie natarcia maksymalnej siły nośnej."
        ),
        "engineering_note": (
            f"Kąt między ziemią a prostą od koła głównego do ogona wynosi {deg(tailstrike_angle_deg)} "
            f"(wysokość ogona nad ziemią oszacowana na {metres(h_tail_clearance)}). "
            + ("Ogon nie dotknie ziemi przy kącie natarcia Cz_max." if tailstrike_ok else
               f"To mniej niż {deg(tail_required)}: ryzyko uderzenia ogonem w pas przy lądowaniu na dużym kącie natarcia. "
               "Zwiększ podcięcie tyłu kadłuba (upsweep), przesuń podwozie główne ku tyłowi albo wydłuż goleń.")
        )
    }])

    # =========================================================================
    # 2a. KĄT MIĘDZY PIONEM PRZEZ ŚC A KOŁEM GŁÓWNYM (wykład 7, slajd 17)
    # =========================================================================
    x_lemac = balance.get("x_lemac_m")
    if not sailplane and x_lemac is not None:
        # BIPOL_3, krok 10: przy rysowaniu podwozia przyjąć ŚC w 35% SCA (albo dalej, jeśli tak wynika z wyważenia).
        cg_ref_pct = max(35.0, float(balance.get("cg_range", {}).get("aft_pct", 30.0)))
        x_cg_aft = float(x_lemac) + cg_ref_pct / 100.0 * mac
        tipback_deg = math.degrees(math.atan2(x_gear - x_cg_aft, h_cg_ground))
        x_gear_required = x_cg_aft + h_cg_ground * math.tan(math.radians(tipback_required))
        gear_pct = 100.0 * (x_gear - x_lemac) / mac
        gear_required_pct = 100.0 * (x_gear_required - x_lemac) / mac
        metrics.update(tipback_angle_deg=round(tipback_deg, 1), tipback_required_deg=round(tipback_required, 1),
                       tipback_cg_mac_pct=round(cg_ref_pct, 1),
                       main_gear_x_required_m=round(x_gear_required, 3), main_gear_required_mac_pct=round(gear_required_pct, 1))
        tipback_ok = tipback_deg >= tipback_required
        pct = lambda v: f"{v:.0f}% SCA"  # noqa: E731
        checks.append({
            "id": "main_gear_tipback",
            "category": "Podwozie i bezpieczeństwo naziemne",
            "title": "Położenie kół głównych za środkiem ciężkości",
            "value": deg(tipback_deg),
            "required": (f"≥ α przy 0,9·Cz_max + 3° = {deg(tipback_required)} (wykład 7)" if alpha_09 is not None
                         else "≥ 15,0° (kąt zadarcia przy starcie)"),
            "passed": tipback_ok,
            "severity": "ok" if tipback_ok else "warning",
            "didactic_simple": (
                "Przy rotacji do startu samolot obraca się wokół kół głównych. Jeśli środek ciężkości "
                "znajdzie się za nimi, samolot usiądzie na ogonie. Dlatego koła główne stoją wyraźnie za "
                "najdalszym tylnym położeniem środka ciężkości."
            ),
            "engineering_note": (
                f"Kąt między pionem przez ŚC w {pct(cg_ref_pct)} (tylne położenie, nie mniej niż 35% SCA wg BIPOL_3) a prostą "
                f"do punktu styku koła głównego wynosi {deg(tipback_deg)} (koła w {pct(gear_pct)}, ŚC na wysokości ok. "
                f"{metres(h_cg_ground)}). "
                + ("Samolot zadarty do kąta startowego nie usiądzie na ogonie." if tipback_ok else
                   f"Wymaganie spełnią koła główne w x ≥ {metres(x_gear_required)} ({pct(gear_required_pct)}); "
                   f"kąt ochrony ogona wyniósłby wtedy {deg(tail_angle(x_gear_required))}. "
                   "Przesunięcie kół do tyłu zwiększa obciążenie kółka przedniego i siłę potrzebną do rotacji.")
            )
        })

    # =========================================================================
    # 3. MIEJSCE POCZĄTKU PRZECIĄGNIĘCIA WG ROZKŁADU SCHRENKA
    # =========================================================================
    schrenk_pin = geom.get("schrenk_Pinpoint", {})
    stall_eta = float(schrenk_pin.get("stall_eta_span", 0.0))
    max_cz1 = float(schrenk_pin.get("max_cz1", 1.0))
    metrics["stall_eta_span"] = stall_eta
    metrics["max_cz1_ratio"] = max_cz1

    # Oderwanie ma się zacząć przed wewnętrzną krawędzią lotki (η_oderwania < η_lotki); bez danych lotki — 0,65.
    partition = geom.get("control_surfaces", {}).get("trailing_edge_partition", {})
    eta_aileron = (1.0 - (partition.get("tip_clearance_pct", 0.0) + partition.get("aileron_span_pct", 0.0)) / 100.0
                   if partition.get("aileron_span_pct") else 0.65)
    eta_aileron = geom.get("control_surfaces", {}).get("ailerons", {}).get("eta_in", eta_aileron)
    metrics["aileron_inner_eta"] = round(eta_aileron, 3)
    stall_safe = stall_eta < eta_aileron
    eta_txt = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    checks.append({
        "id": "stall_progression",
        "category": "Aerodynamika i bezpieczeństwo przeciągnięcia",
        "title": "Lokalizacja początku przeciągnięcia (Stall origin wg Schrenka)",
        "value": f"η = {eta_txt(stall_eta)} ({stall_eta * 100:.0f}% półrozpiętości)",
        "required": f"η < {eta_txt(eta_aileron)} — przed wewnętrzną krawędzią lotki",
        "passed": stall_safe,
        "severity": "ok" if stall_safe else "warning",
        "didactic_simple": (
            "Gdy samolot zwalnia i zaczyna przepadać, skrzydło nie powinno tracić siły nośnej "
            "na końcach, bo tam są lotki! Bezpieczne skrzydło przeciąga się najpierw bliżej kadłuba, "
            "dzięki czemu pilot wciąż może sterować przechyleniem i czuje drgania ostrzegawcze (bufetowanie)."
        ),
        "engineering_note": (
            f"Maksimum lokalnego współczynnika obciążenia Cz,loc/Cz = {max_cz1:.2f} przypada na η = {eta_txt(stall_eta)}, "
            f"a lotki zaczynają się w η = {eta_txt(eta_aileron)}. "
            + ("Przeciągnięcie zaczyna się przed lotkami, więc sterowność poprzeczna zostaje zachowana." if stall_safe else
               "Przeciągnięcie rozpocznie się w strefie lotek — grozi utratą sterowności poprzecznej i wejściem w korkociąg. "
               "Wprowadź zwichrzenie końcówki (skręcenie o −2°…−3°), zwiększ λ (skrzydło mniej zbieżne) "
               "albo dodaj przerywacze na krawędzi natarcia przy kadłubie.")
        )
    })

    # =========================================================================
    # 4. KRYTERIUM ASYMETRII CIĄGU DLA SAMOLOTÓW WIELOSILNIKOWYCH (OEI)
    # =========================================================================
    if n_engines >= 2 and engine_type != "none":
        y_engine = float(params.get("engine_span_y", 0.35 * (b / 2.0)))
        t_single = float(sizing.get("design_point", {}).get("thrust_kn", 0.0) or 0.0) * 1000.0 / n_engines
        if t_single <= 0.0 and engine_type == "prop":
            p_single_kw = float(sizing.get("design_point", {}).get("power_kw", 0.0) or 0.0) / n_engines
            v_lof = float(perf.get("speeds", {}).get("v_lof_kmh", 120.0)) / 3.6
            t_single = (p_single_kw * 1000.0 * 0.70) / max(10.0, v_lof)

        n_yaw_asym = t_single * y_engine
        l_v = float(vt.get("l_v", 0.45 * l_f))
        s_v = float(vt.get("S_v", 0.12 * S))
        v_mc = 1.20 * (float(perf.get("speeds", {}).get("vs_lnd_kmh", 100.0)) / 3.6)
        q_mc = 0.5 * RHO0 * (v_mc ** 2)

        # Maksymalny współczynnik siły bocznej usterzenia przy wychyleniu steru kierunku
        cy_v_max = 0.65
        y_v_avail = q_mc * s_v * cy_v_max
        n_yaw_restore = y_v_avail * l_v
        oei_margin = n_yaw_restore / max(1.0, n_yaw_asym)

        metrics["oei_yaw_margin"] = round(oei_margin, 2)
        metrics["y_engine_m"] = round(y_engine, 2)
        oei_ok = oei_margin >= 1.05

        checks.append({
            "id": "oei_directional_control",
            "category": "Stateczność kierunkowa i bezpieczeństwo napędu",
            "title": "Sterowność kierunkowa przy awarii jednego silnika (OEI / Vmc)",
            "value": f"Zapas momentu: {oei_margin * 100:.0f}%",
            "required": "≥ 105% (statecznik pionowy równoważy asymetrię ciągu)",
            "passed": oei_ok,
            "severity": "ok" if oei_ok else "warning",
            "didactic_simple": (
                "W samolocie wielosilnikowym, gdy jeden silnik zgaśnie, drugi pcha samolot niesymetrycznie "
                "i obraca go w bok. Statecznik pionowy ze sterem kierunku musi być na tyle duży, by pilot "
                "mógł utrzymać prosty tor lotu."
            ),
            "engineering_note": (
                f"Stosunek dostępnego momentu odchylającego usterzenia pionowego do momentu asymetrii ciągu wynosi {oei_margin:.2f}. "
                + ("Usterzenie pionowe zapewnia wymaganą sterowność powyżej Vmc zgodnie z CS-23/25." if oei_ok else
                   "Niewystarczający moment usterzenia pionowego po awarii silnika skrajnego! Zwiększ powierzchnię Sv lub wydłuż ramię lv.")
            )
        })
    else:
        metrics["oei_yaw_margin"] = None

    # =========================================================================
    # 5. EFEKTYWNOŚĆ PRZELOTOWA: PUNKT PRACY SKRZYDŁA (Cz_cruise vs Cz_opt)
    # =========================================================================
    cx0 = float(aero.get("cx0_clean", 0.025))
    e = float(aero.get("oswald_e", 0.80))
    k_ind = 1.0 / (math.pi * AR * e)
    cz_opt = math.sqrt(cx0 / k_ind)

    v_cr_ms = float(params.get("cruise_speed_kmh", 250.0)) / 3.6
    h_cr = float(params.get("cruise_altitude_m", 3000.0))
    rho_cr = RHO0 * math.exp(-h_cr / 9000.0)
    q_cr = 0.5 * rho_cr * (v_cr_ms ** 2)
    cz_cr = (m0 * G0) / max(100.0, q_cr * S)
    ratio_cr = cz_cr / max(0.01, cz_opt)

    metrics["cz_cruise"] = round(cz_cr, 3)
    metrics["cz_opt_kmax"] = round(cz_opt, 3)
    metrics["cruise_matching_ratio"] = round(ratio_cr, 2)

    cruise_match_ok = 0.65 <= ratio_cr <= 1.35
    checks.append({
        "id": "cruise_aerodynamic_matching",
        "category": "Osiągi i ekonomia przelotu",
        "title": "Dopasowanie aerodynamiczne skrzydła w przelocie (Cz,przelot / Cz,opt)",
        "value": f"{cz_cr:.2f} / {cz_opt:.2f} ({ratio_cr:.2f} Cz,opt)",
        "required": "0.65 – 1.35 Cz,opt (przelot blisko Kmax)",
        "passed": cruise_match_ok,
        "severity": "ok" if cruise_match_ok else "warning",
        "didactic_simple": (
            "Samolot lata najtaniej i najdalej, gdy leci z prędkością, przy której skrzydło ma "
            "największą doskonałość (Kmax). Jeśli lecisz ze zbyt małym lub za dużym Cz, marnujesz paliwo "
            "na niepotrzebny opór."
        ),
        "engineering_note": (
            f"W przelocie Cz = {cz_cr:.3f}, podczas gdy optymalny współczynnik wynosi Cz,opt = {cz_opt:.3f} (stosunek: {ratio_cr:.2f}). "
            + ("Skrzydło pracuje w reżimie wysokiej doskonałości aerodynamicznej." if cruise_match_ok else
               ("Zbyt małe obciążenie powierzchni W/S lub za duża prędkość: skrzydło leci na zbyt niskim Cz. "
                "Zmniejszenie powierzchni skrzydła S zredukowałoby opór tarcia." if ratio_cr < 0.65 else
                "Zbyt duże obciążenie powierzchni lub za mała prędkość: skrzydło pracuje w reżimie wysokiego oporu indukcyjnego."))
        )
    })

    # =========================================================================
    # 6. GĘSTOŚĆ ŁADOWNI I POJEMNOŚĆ KUBATUROWA
    # =========================================================================
    m_cargo = float(params.get("m_cargo", 0.0) or 0.0)
    n_pax = int(params.get("n_pax", 0) or 0)
    v_fus_total = math.pi * ((d_f / 2.0) ** 2) * l_f * 0.65  # Użyteczna kubatura kadłuba

    if m_cargo > 0:
        vol_cargo_est = max(0.1, 0.25 * v_fus_total)
        rho_cargo_est = m_cargo / vol_cargo_est
        cargo_ok = 60.0 <= rho_cargo_est <= 450.0
        checks.append({
            "id": "cargo_density",
            "category": "Kadłub i masa płatna",
            "title": "Gęstość ładunku w ładowni",
            "value": f"{rho_cargo_est:.0f} kg/m³",
            "required": "60 – 450 kg/m³ (realistyczna gęstość cargo)",
            "passed": cargo_ok,
            "severity": "ok" if cargo_ok else "warning",
            "didactic_simple": (
                "Ładunek nie może być ani za lekki (wtedy kadłub musiałby być wielki jak balon), "
                "ani gęsty jak ołów (chyba że wieziesz złoto). Standardowe paczki lotnicze mają gęstość ok. 150–250 kg/m³."
            ),
            "engineering_note": (
                f"Szacowana gęstość cargo wynosi {rho_cargo_est:.0f} kg/m³. "
                + ("Mieści się w standardach lotnictwa transportowego." if cargo_ok else
                   "Nietypowa gęstość ładunku! Sprawdź kubaturę ładowni w założeniach projektu.")
            )
        })

    # =========================================================================
    # 7. ZAGADNIENIA ŚCIŚLIWOŚCI I LICZBA MACHA (Raymer rozdz. 12)
    # =========================================================================
    comp = aero.get("compressibility", {})
    raw_comp = comp.get('terms', comp)
    mach_cr = float(raw_comp.get("mach", 0.0))
    m_dd = float(raw_comp.get("m_dd", 0.75))
    m_crit = float(raw_comp.get("m_crit", 0.68))
    delta_cx_w = raw_comp.get("delta_cx_wave")

    mach_ok = comp.get("drag_divergence_safe", True)
    metrics["mach_cruise"] = mach_cr
    metrics["m_dd"] = m_dd
    metrics["delta_cx_wave"] = delta_cx_w

    if mach_cr >= 0.30 or engine_type == "jet":
        checks.append({
            "id": "compressibility_drag_divergence",
            "category": "Aerodynamika dużych prędkości i ściśliwość",
            "title": "Margines liczby Macha rozbieżności oporu (M vs M_dd)",
            "value": f"M = {mach_cr:.2f} (M_dd = {m_dd:.2f})",
            "required": "Punkt w zakresie korelacji oraz M < M_dd; dodatkowo sprawdź zakres biegunowej",
            "passed": mach_ok,
            "severity": "ok" if mach_ok else "warning",
            "didactic_simple": (
                "Gdy samolot zbliża się do prędkości dźwięku, na skrzydle powstają fale uderzeniowe, "
                "które zwiększają opór powietrza. Początek oporu falowego M_kr występuje wcześniej niż "
                "rozbieżność oporu M_dd; dodatni margines do M_dd nie dowodzi poprawności biegunowej bez oporu falowego."
            ),
            "engineering_note": (
                f"Przelot przy MTOW: M = {mach_cr:.3f}, M_kr = {m_crit:.3f}, M_dd = {m_dd:.3f}; "
                f"margines korelacji ΔM = {m_dd - mach_cr:.3f}. "
                + (f"Diagnostyczny ΔCx,wave = {delta_cx_w:.5f}. " if delta_cx_w is not None else
                   "Przyrost oporu jest niedostępny poza zakresem korelacji. ")
                + comp.get('note', '')
            )
        })

    # =========================================================================
    # 8. OBCIĄŻENIE POWIERZCHNI NOŚNEJ W/S A KATEGORIA SAMOLOTU
    # =========================================================================
    ws_n_m2 = (m0 * G0) / max(0.1, S)
    ac_cat = params.get("category", "cs23_level2")
    ac_type = params.get("aircraft_type", "piston_ga")

    if ac_type in ("glider", "motoglider"):
        ws_min, ws_max = 200.0, 600.0
        ws_desc = "Szybowiec / motoszybowiec (20–60 kg/m²)"
    elif ac_type in ("ultralight", "vla"):
        ws_min, ws_max = 250.0, 750.0
        ws_desc = "Samolot ultralekki / VLA (25–75 kg/m²)"
    elif ac_type in ("jet_business", "vlj_jet"):
        ws_min, ws_max = 1500.0, 5000.0
        ws_desc = "Odrzutowiec dyspozycyjny / VLJ (150–500 kg/m²)"
    elif ac_type == "turboprop_regional":
        ws_min, ws_max = 1800.0, 4000.0
        ws_desc = "Regionalny samolot komunikacyjny (180–400 kg/m²)"
    else:
        ws_min, ws_max = 450.0, 1600.0
        ws_desc = "Samolot lotnictwa ogólnego GA (45–160 kg/m²)"

    ws_ok = ws_min <= ws_n_m2 <= ws_max
    metrics["ws_n_m2"] = round(ws_n_m2, 1)
    metrics["ws_kg_m2"] = round(m0 / max(0.1, S), 1)

    checks.append({
        "id": "wing_loading_benchmark",
        "category": "Wymiarowanie i parametry wstępne",
        "title": "Obciążenie powierzchni skrzydła (W/S vs standardy)",
        "value": f"{ws_n_m2:.0f} N/m² ({m0/S:.1f} kg/m²)",
        "required": f"{ws_min:.0f} – {ws_max:.0f} N/m² ({ws_desc})",
        "passed": ws_ok,
        "severity": "ok" if ws_ok else "warning",
        "didactic_simple": (
            "Obciążenie skrzydła mówi, ile kilogramów samolotu musi unieść każdy metr kwadratowy skrzydła. "
            "Małe skrzydło (duże W/S) jest szybsze i lżejsze, ale wymaga długiego pasa i wysokiej prędkości lądowania. "
            "Duże skrzydło (małe W/S) pozwala lądować powoli, lecz mocniej trzęsie w turbulencji."
        ),
        "engineering_note": (
            f"Wartość W/S = {ws_n_m2:.1f} N/m² ({m0/S:.1f} kg/m²). "
            + ("Mieści się w statystycznym przedziale dla tej klasy statku powietrznego." if ws_ok else
               ("Zbyt małe obciążenie skrzydła: płat jest przewymiarowany pod kątem powierzchni, co zwiększa opór tarcia i masę struktury." if ws_n_m2 < ws_min else
                "Zbyt duże obciążenie skrzydła: wysoka prędkość przeciągnięcia wymaga zaawansowanej mechanizacji płata (sloty, klapy szczelinowe)."))
        )
    })

    # =========================================================================
    # 9. MARGINES BEZPIECZEŃSTWA PRZED FLATTEREM (CS-23.629 / CS-25.629)
    # =========================================================================
    aeroel = result.get("aeroelastics") or {}
    v_flutter = float(aeroel.get("flutter_speed_kmh", 0.0) or 0.0)
    v_d_val = float(aeroel.get("dive_speed_vd_kmh", 0.0) or 0.0)
    flutter_margin = float(aeroel.get("margin_flutter", 1.5) or 1.5)
    flutter_ok = aeroel.get("flutter_safe", True)

    metrics["flutter_speed_kmh"] = v_flutter
    metrics["flutter_margin"] = flutter_margin
    metrics["divergence_speed_kmh"] = aeroel.get("divergence_speed_kmh")
    metrics["aileron_reversal_speed_kmh"] = aeroel.get("aileron_reversal_speed_kmh")
    metrics["dive_speed_vd_kmh"] = v_d_val

    if v_flutter > 0.0 and v_d_val > 0.0:
        checks.append({
            "id": "flutter_safety_margin",
            "category": "Aeroelastyczność i sztywność konstrukcji",
            "title": "Margines bezpieczeństwa flatteru (V_flater vs 1.20 VD)",
            "value": f"V_flater = {v_flutter:.0f} km/h ({flutter_margin:.2f} VD)",
            "required": "≥ 1.20 VD (wymóg CS-23.629 / CS-25.629)",
            "passed": flutter_ok,
            "severity": "ok" if flutter_ok else "warning",
            "didactic_simple": (
                "Flater to gwałtowne, samowzbudne trzepotanie skrzydła, które potrafi urwać skrzydło w ułamku sekundy. "
                "Skrzydło musi być na tyle sztywne na skręcanie i zginanie, by flater pojawił się dopiero daleko powyżej "
                "największej dopuszczalnej prędkości nurkowania (co najmniej 20% powyżej VD)."
            ),
            "engineering_note": (
                f"Szacowana prędkość flatteru giętno-skrętnego wynosi V_flater = {v_flutter:.0f} km/h (VD = {v_d_val:.0f} km/h, zapas: {flutter_margin:.2f} VD); "
                "to szacunek wstępny z modelu przekroju typowego z aerodynamiką quasi-stacjonarną. "
                + ("Szacunek mieści się w marginesie 1,20 VD; CS-23.629 wymaga potwierdzenia analizą drgań lub próbami." if flutter_ok else
                   "Szacunek nie daje marginesu 1,20 VD: przesuń środek masy przekrojów do przodu (wyważenie masowe lotek, "
                   "masy przed osią sprężystą) i zwiększ sztywność skrętną kesonu.")
            )
        })

    # =========================================================================
    # 10. ZDATNOŚĆ AKUSTYCZNA I HAŁAS ZEWNĘTRZNY (ICAO Annex 16 / CS-36)
    # =========================================================================
    acoustics = result.get("acoustics") or {}
    noise_flyover = float(acoustics.get("noise_flyover", 0.0) or 0.0)
    noise_limit = float(acoustics.get("limit_flyover", 0.0) or 0.0)
    noise_margin = float(acoustics.get("margin_flyover", 0.0) or 0.0)
    cumulative = acoustics.get("cumulative_margin_epndb")
    noise_unit = acoustics.get("metric_unit", "dBA")
    noise_compliant = acoustics.get("compliant", True)
    m_tip_val = acoustics.get("propeller_tip_mach")

    metrics["noise_flyover"] = noise_flyover
    metrics["noise_limit"] = noise_limit
    metrics["noise_margin"] = noise_margin
    metrics["noise_unit"] = noise_unit
    metrics["propeller_tip_mach"] = m_tip_val

    if noise_flyover > 0.0 and acoustics.get("limit_flyover") is not None:
        checks.append({
            "id": "noise_compliance_check",
            "category": "Ochrona środowiska i zdatność akustyczna",
            "title": f"Certyfikacja hałasu ({acoustics.get('icao_standard', 'ICAO Annex 16')})",
            "value": f"{noise_flyover:.1f} {noise_unit} (zapas: {noise_margin:+.1f} {noise_unit})",
            "required": (f"Rozdz. 14.4: suma zapasów w 3 punktach ≥ 17 EPNdB (jest {cumulative:.1f}), w każdym ≥ 1; przelot ≤ {noise_limit:.1f} EPNdB"
                         if cumulative is not None else f"≤ {noise_limit:.1f} {noise_unit} (limit przy starcie)" if noise_limit
                         else acoustics.get("icao_standard", "nie dotyczy")),
            "passed": noise_compliant,
            "severity": "ok" if noise_compliant else "warning",
            "didactic_simple": (
                "Samolot nie może być zbyt głośny dla ludzi mieszkających wokół lotniska. "
                "W samolotach śmigłowych głównym źródłem ryku jest końcówka śmigła tnąca powietrze (zwłaszcza gdy M_tip > 0.75), "
                "a w odrzutowcach — gwałtowny strumień gorących gazów wylotowych."
            ),
            "engineering_note": (
                f"Szacowany poziom hałasu wynosi {noise_flyover:.1f} {noise_unit} przy limicie {noise_limit:.1f} {noise_unit}. "
                "Model jest zgrubny (moc, M_tip, odległość; bez widma i kierunkowości), więc służy do porównania wariantów, "
                "a nie do oceny certyfikacyjnej. "
                + (f"Szacunek mieści się w limicie z zapasem {noise_margin:.1f} {noise_unit}. {acoustics.get('didactic_advice', '')}" if noise_compliant else
                   f"Szacunek przekracza limit o {abs(noise_margin):.1f} {noise_unit} — sprawdź M_tip, liczbę łopat i obroty śmigła. "
                   f"{acoustics.get('didactic_advice', '')}")
            )
        })

    # =========================================================================
    # 11. DYNAMIKA LOTU: KRYTERIUM OCENY WŁASNOŚCI LOTNYCH (CAP & Dutch Roll)
    # =========================================================================
    fq = result.get("flying_qualities", {})
    if fq:
        sp = fq.get("short_period", {})
        dr = fq.get("dutch_roll", {})
        cap_val = sp.get("cap_rad_s2_per_g", 0.0)
        cap_lvl = sp.get("cap_level", 1)
        dr_passed = dr.get("cs23_criterion_passed", True)
        fq_passed = (cap_lvl <= 2) and dr_passed

        metrics["cap_rad_s2_per_g"] = cap_val
        metrics["flying_qualities_level"] = cap_lvl
        metrics["dutch_roll_cs23_passed"] = dr_passed

        checks.append({
            "id": "flying_qualities_cap_check",
            "category": "Dynamika lotu i pilotaż (Flying Qualities)",
            "title": "Sterowność podłużna CAP i tłumienie holendrowania (Handout 11)",
            "value": f"CAP = {cap_val:.3f} rad/(s²·g) (Level {cap_lvl}), Dutch Roll: {'Zgodny z CS-23' if dr_passed else 'Niewystarczające tłumienie'}",
            "required": ("Faza B wg MIL-F-8785C/MIL-STD-1797 (wykład 11): CAP 0,085–3,6 rad/(s²·g) na poziom 1, "
                         "0,038–10 na poziom 2; holendrowanie −ξ/η ≥ 0,0523 (JAR/CS-23)"),
            "passed": fq_passed,
            "severity": "ok" if fq_passed else "warning",
            "didactic_simple": (
                "Samolot musi reagować na stery płynnie i przewidywalnie dla pilota. "
                "Jeśli parametr CAP jest za wysoki, samolot jest 'nadsterowny' i pilot może wpaść w niebezpieczne "
                "oscylacje PIO. Jeśli jest za niski — samolot reaguje jak kloc lodu."
            ),
            "engineering_note": (
                f"Krótkookresowy parametr CAP = {cap_val:.4f} rad/(s²·g) kwalifikuje samolot do Poziomu {cap_lvl} (Handout 11_1). "
                f"Tłumienie holendrowania -ξ/η = {dr.get('damping_criterion_ratio', 0.0):.4f} (wymagane ≥ 0.0523 wg JAR/CS-23.181). "
                + ("Płatowiec wykazuje prawidłowe właściwości dynamiczne i pilotażowe." if fq_passed else
                   "Właściwości dynamiczne wymagają optymalizacji: skoryguj zapas stateczności statycznej lub powierzchnię usterzeń.")
            )
        })

    # =========================================================================
    # 12. SYMULATOR PYTAŃ NA ZEJSZCIÓWKĘ / OBRONĘ (Defense Quiz Simulator)
    # =========================================================================
    defense_questions = generate_defense_questions(result, metrics)

    total_checks = len(checks)
    passed_checks = sum(1 for c in checks if c["passed"])

    return {
        "status": "success",
        "passed_count": passed_checks,
        "total_count": total_checks,
        "quality_score_pct": round((passed_checks / max(1, total_checks)) * 100, 1),
        "checks": checks,
        "metrics": metrics,
        "defense_questions": defense_questions
    }


def generate_defense_questions(result: dict, metrics: dict) -> list:
    """
    Generuje spersonalizowane pytania problemowe na zejściówkę / obronę projektu
    w oparciu o konkretne liczby bieżącego samolotu.
    """
    p = result.get("params", {})
    mass = result.get("mass", {})
    sizing = result.get("sizing", {})
    perf = result.get("performance", {})
    balance = result.get("balance", {})

    dp = sizing.get("design_point", {})
    ws_val = round(float(dp.get("ws", 0.0)), 1)
    power_kw = round(float(dp.get("power_kw", 0.0) or 0.0), 1)
    thrust_kn = round(float(dp.get("thrust_kn", 0.0) or 0.0), 2)
    m0 = round(float(mass.get("m0", 1000.0)), 1)
    wy_max = round(float(perf.get("climb", {}).get("wy_max_ms", 5.0) or 5.0), 1)
    sm_aft = round(float(balance.get("stability", {}).get("static_margin_aft_pct", 5.0)), 1)
    vs0 = round(float(perf.get("speeds", {}).get("vs_lnd_kmh", 90.0) or 90.0), 1)
    limit_by, governing = dp.get("limit_by"), dp.get("governing")
    powered = p.get("engine_type", "prop") != "none" and (dp.get("power_kw") or dp.get("thrust_kn"))
    comma = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    drive = f"mocy P = {power_kw} kW" if dp.get("power_kw") else f"ciągu T = {thrust_kn} kN"
    # Początek przeciągnięcia wg Schrenka a wewnętrzna krawędź lotki (BIPOL: η_oderwania < η_lotki).
    stall_eta = float(metrics.get("stall_eta_span", 0.5))
    partition = result.get("geometry", {}).get("control_surfaces", {}).get("trailing_edge_partition", {})
    eta_aileron = (1.0 - (partition.get("tip_clearance_pct", 0.0) + partition.get("aileron_span_pct", 0.0)) / 100.0
                   if partition.get("aileron_span_pct") else None)
    eta_aileron = result.get("geometry", {}).get("control_surfaces", {}).get("ailerons", {}).get("eta_in", eta_aileron)
    if eta_aileron is None:
        stall_verdict = "Porównaj to miejsce z wewnętrzną krawędzią lotki na rysunku."
    elif stall_eta < eta_aileron:
        stall_verdict = (f"Lotki zaczynają się w η ≈ {comma(eta_aileron)}, więc oderwanie zaczyna się przed nimi i na początku "
                         "przeciągnięcia sterowanie poprzeczne pozostaje skuteczne.")
    else:
        stall_verdict = (f"Lotki zaczynają się w η ≈ {comma(eta_aileron)}, a oderwanie zaczyna się już na nich — "
                         "przy przeciągnięciu samolot może gwałtownie przechylić się i stracić sterowność poprzeczną.")

    questions = [
        {
            "id": "q_matching_chart",
            "topic": "Studium Wykonalności (P2)",
            "question": f"Dlaczego obciążenie powierzchni Twojego szybowca wynosi W/S = {ws_val} N/m²?",
            "expected_answer": (
                f"Bez napędu W/S ogranicza prędkość minimalna (V_S0 = {vs0} km/h) i wymagana prędkość krążenia w kominie. "
                "Większe W/S przesuwa biegunową prędkości ku większym prędkościom przy tej samej doskonałości — szybszy "
                "przelot między kominami — ale zwiększa promień krążenia i opadanie; dlatego szybowce wyczynowe zabierają "
                "zrzucany balast wodny."
            ),
            "faculty_tip": "Prowadzący sprawdza, czy rozumiesz, jak W/S przesuwa biegunową prędkości szybowca."
        } if not powered else {
            "id": "q_matching_chart",
            "topic": "Studium Wykonalności (P2)",
            "question": f"Dlaczego punkt projektowy Twojego samolotu wybrano na poziomie W/S = {ws_val} N/m² i {drive}?",
            "expected_answer": (
                f"Największe dopuszczalne W/S wyznacza ograniczenie: {limit_by or 'prędkość minimalna'} (dla V_S0 = {vs0} km/h "
                f"pionowa granica na wykresie). Przy tym W/S wymagany {'stosunek mocy' if dp.get('power_kw') else 'ciąg'} "
                f"wynika z ograniczenia {governing or 'najwyższej krzywej wymagań'}; punkt leży w obszarze dopuszczalnym, "
                "najbliżej najmniejszego napędu. Większe W/S dałoby mniejsze i lżejsze skrzydło, ale nie spełniłoby warunku "
                "prędkości minimalnej (lądowania) bez mocniejszej mechanizacji."
            ),
            "faculty_tip": "Prowadzący sprawdza, czy rozumiesz fizyczny sens krzywych na wykresie dopasowania (Matching Chart)."
        },
        {
            "id": "q_climb_speed",
            "topic": "Osiągi szybowca (P5)",
            "question": "Czym różni się prędkość najmniejszego opadania od prędkości największej doskonałości Twojego szybowca?",
            "expected_answer": (
                "Największa doskonałość K_max (najdłuższy lot ślizgowy) występuje przy C_z = √(π·A·e·C_x0), "
                "a najmniejsze opadanie przy największej funkcji energetycznej C_z^1,5/C_x, czyli C_z = √(3·π·A·e·C_x0). "
                "Prędkość najmniejszego opadania jest więc mniejsza, ok. 0,76 prędkości największej doskonałości: "
                "pierwszą stosuje się przy krążeniu w kominie, drugą (z poprawką na wiatr i noszenia) w przelocie."
            ),
            "faculty_tip": "Prowadzący sprawdza, czy łączysz biegunową prędkości z funkcją energetyczną profilu i płata."
        } if not powered else {
            "id": "q_climb_speed",
            "topic": "Osiągi i biegunowa wznoszenia (P5)",
            "question": f"Przy jakiej prędkości Twój samolot osiąga maksymalne wznoszenie wy,max = {wy_max} m/s i czym różni się Vx od Vy?",
            "expected_answer": (
                "Prędkość największego kąta wznoszenia Vx odpowiada największej nadwyżce ciągu (T - D), natomiast prędkość "
                "największej prędkości wznoszenia Vy odpowiada największej nadwyżce mocy (N_dost - N_niezb). Dla napędu śmigłowego Vx < Vy."
            ),
            "faculty_tip": "Klasyczne pytanie pułapka z Mechaniki Lotu I: student musi odróżnić metodę ciągu od metody mocy."
        },
        {
            "id": "q_stability_margin",
            "topic": "Wyważenie i stateczność (P3)",
            "question": f"Twój zapas stateczności statycznej wynosi Kn = {sm_aft}% ŚDA w tylnym położeniu ŚC. Co stanie się po przekroczeniu punktu neutralnego?",
            "expected_answer": (
                "Gdy środek ciężkości przesunie się za punkt neutralny xN (Kn < 0), samolot stanie się statycznie niestabilny: "
                "każde zaburzenie kąta natarcia wywoła moment pochylający pogłębiający to zaburzenie, co uniemożliwi pilotowanie bez układu FBW."
            ),
            "faculty_tip": ("Program wymaga Kn ≥ 5% ŚDA przy tylnym ŚC (praktyka projektowa); materiał BIPOL_3 "
                            "wymaga ŚC w locie w zakresie 25–35% ŚDA.")
        },
        {
            "id": "q_stall_origin",
            "topic": "Aerodynamika skrzydła wg Schrenka (P3)",
            "question": f"W którym miejscu rozpiętości rozpoczyna się przeciągnięcie na Twoim skrzydle (η = {comma(stall_eta)}) i dlaczego?",
            "expected_answer": (
                "Przeciągnięcie zaczyna się tam, gdzie lokalne c_z/C_z z rozkładu Schrenka (średnia rozkładu cięciw "
                f"i eliptycznego) jest największe — u Ciebie w {stall_eta:.0%} półrozpiętości. Płat prostokątny przeciąga się "
                "przy kadłubie, a im mniejsza zbieżność λ, tym dalej ku końcówce leży to maksimum. "
                f"{stall_verdict} Miejsce oderwania przesuwa się do kadłuba zwichrzeniem geometrycznym lub aerodynamicznym, "
                "większym λ (skrzydłem mniej zbieżnym) albo przerywaczami na krawędzi natarcia przy kadłubie."
            ),
            "faculty_tip": "Prowadzący sprawdza, czy student wie, jak zbieżność i zwichrzenie wpływają na bezpieczeństwo lotu."
        },
        {
            "id": "q_aeroelastics",
            "topic": "Aeroelastyczność i sztywność (P4/P6)",
            "question": f"Prędkość nurkowania Twojego samolotu wynosi VD = {metrics.get('dive_speed_vd_kmh', 300):.0f} km/h. Dlaczego przepisy CS-23 wymagają, by prędkość flatteru przekraczała 1.20 VD i czym grozi rewers lotek?",
            "expected_answer": (
                "Współczynnik 1.20 (20% margines w prędkości) zabezpiecza samolot przed nieprzewidzianym przekroczeniem VD w turbulencji i niedokładnościami obliczeniowymi. "
                "Rewers lotek grozi utratą sterowania poprzecznego: przy dużej prędkości ugięcie lotki skręca całe skrzydło przeciwnie do zamierzonego przechylenia."
            ),
            "faculty_tip": "Klasyczne pytanie na 5.0 z Mechaniki Lotu i Konstruowania Samolotów: student musi powiązać aerodynamikę z odkształceniami sprężystymi struktury."
        },
        {
            "id": "q_flying_qualities",
            "topic": "Dynamika lotu i sterowność (Handout 11)",
            "question": f"Parametr oczekiwanej sterowności Twojego samolotu wynosi CAP = {metrics.get('cap_rad_s2_per_g', 0.5):.3f} rad/(s²·g). Od czego zależy CAP i dlaczego zbyt wysoka wartość grozi PIO?",
            "expected_answer": (
                "CAP = omega_n_sp² / n_z_alpha = (Kn · MAC · m · g) / Iyy. Oznacza to, że CAP zależy wprost proporcjonalnie od zapasu stateczności statycznej Kn i cięciwy średniej MAC, "
                "a odwrotnie proporcjonalnie od masowego momentu bezwładności pochylenia Iyy. Zbyt wysoki CAP powoduje nadmierną 'sztywność' kątową i zbyt szybką reakcję w pochyleniu "
                "w stosunku do przyrostu przeciążenia nz, co prowokuje pilota do przesterowywania drążka i wzbudzenia oscylacji indukowanych przez pilota (PIO)."
            ),
            "faculty_tip": "Główne kryterium dynamiczne z wykładów BIPOL I (Handout 11_1): pilot ocenia samolot po parametrze CAP, a nie po samej statyce."
        }
    ]
    if metrics.get("tipback_angle_deg") is not None:
        deg = lambda v: f"{v:.1f}°".replace(".", ",")  # noqa: E731
        questions.append({
            "id": "q_main_gear",
            "topic": "Rysunek samolotu — podwozie (P3, wykład 7)",
            "question": (f"Koła główne stoją pod kątem {deg(metrics['tipback_angle_deg'])} za tylnym położeniem ŚC, a kąt od koła "
                         f"do ogona wynosi {deg(metrics['tailstrike_angle_deg'])}. Skąd biorą się wymagane wartości tych kątów?"),
            "expected_answer": (
                "Z kątów natarcia płata. Kąt między pionem przez ŚC a prostą do koła głównego ma być nie mniejszy niż kąt natarcia "
                f"przy 0,9·Cz_max plus 3° (u Ciebie {deg(metrics['tipback_required_deg'])}), żeby zadarty do startu samolot nie usiadł "
                "na ogonie. Kąt od koła głównego do ogona ma być nie mniejszy niż kąt natarcia przy Cz_max (u Ciebie "
                f"{deg(metrics['tailstrike_required_deg'])}), żeby ogon nie uderzył o pas. Kąt przewrócenia na bok ma być mniejszy niż 60°."
            ),
            "faculty_tip": "Prowadzący sprawdza na arkuszu, czy położenie kół wynika z kątów natarcia, a nie z wyglądu rysunku."
        })

    return questions
