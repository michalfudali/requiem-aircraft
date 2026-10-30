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

    tipover_ok = tipover_angle_deg <= 55.0
    checks.append({
        "id": "tipover_angle",
        "category": "Podwozie i bezpieczeństwo naziemne",
        "title": "Kąt przewrotki bocznej podwozia (Tipover angle)",
        "value": f"{tipover_angle_deg:.1f}°",
        "required": "≤ 55.0° (zalecane 40°–53°)",
        "passed": tipover_ok,
        "severity": "ok" if tipover_ok else "warning",
        "didactic_simple": (
            "Gdy lądujesz z bocznym wiatrem lub gwałtownie skręcasz na drodze kołowania, "
            "samolot nie może przewrócić się na skrzydło. Kąt wywrotki zależy od szerokości "
            "rozstawu kół i wysokości środka ciężkości."
        ),
        "engineering_note": (
            f"Kąt przewrotki wynosi {tipover_angle_deg:.1f}°. "
            + ("Spełnia kryterium stabilności naziemnej Raymera (≤55°)." if tipover_ok else
               "Przekracza limit 55°! Samolot ma zbyt wąski rozstaw kół lub zbyt wysoko położony środek masy. "
               "Zwiększ rozstaw podwozia głównego lub rozważ mocowanie goleni do skrzydła.")
        )
    })

    # =========================================================================
    # 2. KĄT OCHRONY OGONA PRZED UDERZENIEM O PAS (Tailstrike Clearance)
    # =========================================================================
    l_tail_overhang = max(0.5, l_f - x_gear)
    z_tail_bumper = -0.20 * d_f
    h_tail_clearance = z_tail_bumper - z_ground
    tailstrike_angle_deg = math.degrees(math.atan2(h_tail_clearance, l_tail_overhang))
    metrics["tailstrike_angle_deg"] = round(tailstrike_angle_deg, 1)

    tailstrike_ok = tailstrike_angle_deg >= 12.0
    checks.append({
        "id": "tailstrike_clearance",
        "category": "Geometria kadłuba i lądowanie",
        "title": "Kąt ochrony ogona (Tailstrike clearance angle)",
        "value": f"{tailstrike_angle_deg:.1f}°",
        "required": "≥ 12.0° (ochrona przed tail-strike)",
        "passed": tailstrike_ok,
        "severity": "ok" if tailstrike_ok else "warning",
        "didactic_simple": (
            "Gdy pilot podczas lądowania zadziera nos do góry (wyrównanie ze spłaszczeniem), "
            "ogon samolotu opada w dół. Kąt z tyłu kadłuba musi być wystarczająco stromy, "
            "by ogon nie przytarł o beton."
        ),
        "engineering_note": (
            f"Dostępny kąt geometryczny ochrony ogona wynosi {tailstrike_angle_deg:.1f}°. "
            + ("Zapewnia bezpieczny margines podczas rotacji do startu (VR) i przyziemienia." if tailstrike_ok else
               "Zbyt mały kąt (<12°)! Ryzyko uderzenia ogonem w pas (tail strike) przy lądowaniu na dużym kącie natarcia. "
               "Zwiększ podcięcie tyłu kadłuba (upsweep) lub przesuń podwozie główne ku tyłowi.")
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

    # Strefa lotek: zwykle powyżej 65% półrozpiętości
    stall_safe = stall_eta < 0.65
    checks.append({
        "id": "stall_progression",
        "category": "Aerodynamika i bezpieczeństwo przeciągnięcia",
        "title": "Lokalizacja początku przeciągnięcia (Stall origin wg Schrenka)",
        "value": f"η = {stall_eta:.2f} ({stall_eta * 100:.0f}% półrozpiętości)",
        "required": "η < 0.65 (początek przy kadłubie, lotki bezpieczne)",
        "passed": stall_safe,
        "severity": "ok" if stall_safe else "warning",
        "didactic_simple": (
            "Gdy samolot zwalnia i zaczyna przepadać, skrzydło nie powinno tracić siły nośnej "
            "na końcach, bo tam są lotki! Bezpieczne skrzydło przeciąga się najpierw przy kadłubie, "
            "dzięki czemu pilot wciąż może sterować przechyleniem i czuje drgania ostrzegawcze (bufetowanie)."
        ),
        "engineering_note": (
            f"Maksimum lokalnego współczynnika obciążenia Cz,loc/Cz = {max_cz1:.2f} przypada na η = {stall_eta:.2f}. "
            + ("Prawidłowa kolejność: przeciągnięcie zaczyna się w części przykadłubowej, chroniąc sterowność lotkami." if stall_safe else
               "Przeciągnięcie rozpocznie się w strefie lotek (η ≥ 0.65)! Grozi utratą sterowności poprzecznej i wejściem w korkociąg. "
               "Wprowadź ujemne zwichrzenie aerodynamiczne końcówki (skręcenie o -2°…-3°) lub zmniejsz zbieżność skrzydła.")
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
    mach_cr = float(comp.get("mach", 0.0) or 0.0)
    m_dd = float(comp.get("m_dd", 0.75) or 0.75)
    m_crit = float(comp.get("m_crit", 0.68) or 0.68)
    delta_cx_w = float(comp.get("delta_cx_wave", 0.0) or 0.0)

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
            "required": "M < M_dd (przelot poniżej stromej rozbieżności oporu)",
            "passed": mach_ok,
            "severity": "ok" if mach_ok else "warning",
            "didactic_simple": (
                "Gdy samolot zbliża się do prędkości dźwięku, na skrzydle powstają fale uderzeniowe, "
                "które gwałtownie zwiększają opór powietrza (ściana oporu falowego). Przelot powinien "
                "odbywać się poniżej liczby Macha M_dd."
            ),
            "engineering_note": (
                f"Liczba Macha w przelocie wynosi M = {mach_cr:.3f}, a liczba Macha rozbieżności oporu wg Korna-Masona M_dd = {m_dd:.3f}. "
                + (f"Margines bezpieczeństwa ΔM = {m_dd - mach_cr:.2f} jest zachowany (ΔCx,wave = {delta_cx_w:.4f})." if mach_ok else
                   f"Przelot powyżej rozbieżności oporu! Przyrost oporu falowego wynosi ΔCx,wave = {delta_cx_w:.4f}. "
                   "Rozważ profil nadkrytyczny, zmniejszenie grubości względnej t/c skrzydła lub zwiększenie skosu krawędzi natarcia.")
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
                f"Szacowana prędkość flatteru giętno-skrętnego wynosi V_flater = {v_flutter:.0f} km/h (VD = {v_d_val:.0f} km/h, zapas: {flutter_margin:.2f} VD). "
                + ("Skrzydło spełnia wymóg przepisów zdatności CS-23/25 (margines ≥ 1.20 VD)." if flutter_ok else
                   "Niewystarczający margines flatteru (< 1.20 VD)! Zwiększ grubość poszycia kesonu skrzydła (t_skin) lub zastosuj sztywniejszy dźwigar.")
            )
        })

    # =========================================================================
    # 10. ZDATNOŚĆ AKUSTYCZNA I HAŁAS ZEWNĘTRZNY (ICAO Annex 16 / CS-36)
    # =========================================================================
    acoustics = result.get("acoustics") or {}
    noise_flyover = float(acoustics.get("noise_flyover", 0.0) or 0.0)
    noise_limit = float(acoustics.get("limit_flyover", 0.0) or 0.0)
    noise_margin = float(acoustics.get("margin_flyover", 0.0) or 0.0)
    noise_unit = acoustics.get("metric_unit", "dBA")
    noise_compliant = acoustics.get("compliant", True)
    m_tip_val = acoustics.get("propeller_tip_mach")

    metrics["noise_flyover"] = noise_flyover
    metrics["noise_limit"] = noise_limit
    metrics["noise_margin"] = noise_margin
    metrics["noise_unit"] = noise_unit
    metrics["propeller_tip_mach"] = m_tip_val

    if noise_flyover > 0.0:
        checks.append({
            "id": "noise_compliance_check",
            "category": "Ochrona środowiska i zdatność akustyczna",
            "title": f"Certyfikacja hałasu ({acoustics.get('icao_standard', 'ICAO Annex 16')})",
            "value": f"{noise_flyover:.1f} {noise_unit} (zapas: {noise_margin:+.1f} {noise_unit})",
            "required": f"≤ {noise_limit:.1f} {noise_unit} (limit przelotu)",
            "passed": noise_compliant,
            "severity": "ok" if noise_compliant else "warning",
            "didactic_simple": (
                "Samolot nie może być zbyt głośny dla ludzi mieszkających wokół lotniska. "
                "W samolotach śmigłowych głównym źródłem ryku jest końcówka śmigła tnąca powietrze (zwłaszcza gdy M_tip > 0.75), "
                "a w odrzutowcach — gwałtowny strumień gorących gazów wylotowych."
            ),
            "engineering_note": (
                f"Obliczony poziom hałasu przelotu wynosi {noise_flyover:.1f} {noise_unit} przy limicie {noise_limit:.1f} {noise_unit}. "
                + (f"Spełnia normy hałasowe ICAO/EASA z marginesem {noise_margin:.1f} {noise_unit}. {acoustics.get('didactic_advice', '')}" if noise_compliant else
                   f"Przekroczenie limitu hałasu o {abs(noise_margin):.1f} {noise_unit}! {acoustics.get('didactic_advice', '')}")
            )
        })

    # =========================================================================
    # 11. SYMULATOR PYTAŃ NA ZEJSZCIÓWKĘ / OBRONĘ (Defense Quiz Simulator)
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

    questions = [
        {
            "id": "q_matching_chart",
            "topic": "Studium Wykonalności (P2)",
            "question": f"Dlaczego punkt projektowy Twojego samolotu wybrano na poziomie W/S = {ws_val} N/m² i mocy P = {power_kw} kW?",
            "expected_answer": (
                f"Punkt projektowy leży w obszarze dopuszczalnym ograniczonym prędkością przeciągnięcia VS0 = {vs0} km/h "
                f"(pionowa granica W/S) oraz wymaganiami startu na 15 m i wznoszenia. Zwiększenie W/S zmniejszyłoby masę skrzydła, "
                f"ale uniemożliwiłoby spełnienie warunku lądowania bez zaawansowanej mechanizacji."
            ),
            "faculty_tip": "Prowadzący sprawdza, czy rozumiesz fizyczny sens krzywych na wykresie dopasowania (Matching Chart)."
        },
        {
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
            "faculty_tip": "Wymóg regulaminu: Kn ≥ 5% ŚDA dla skrajnego tylnego wyważenia."
        },
        {
            "id": "q_stall_origin",
            "topic": "Aerodynamika skrzydła wg Schrenka (P4)",
            "question": f"W którym miejscu rozpiętości rozpoczyna się przeciągnięcie na Twoim skrzydle (η = {metrics.get('stall_eta_span', 0.5):.2f}) i dlaczego?",
            "expected_answer": (
                f"Rozkład Schrenka wyznacza punkt krytyczny tam, gdzie stosunek c_Schrenk(y)/c_geom(y) osiąga maksimum. "
                "Dla skrzydła o umiarkowanej zbieżności maksimum wypada w części przykadłubowej, co chroni lotki przed wczesnym oderwaniem strug."
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
        }
    ]

    return questions
