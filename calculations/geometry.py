"""
Moduł wymiarowania geometrycznego zespołów płatowca (Projekt P3).
Implementuje:
- 5 obrysów skrzydła: trapezowy, prostokątny, prostokątno-trapezowy, eliptyczny, skośny trapezowy
- Rozkład obciążenia aerodynamicznego Schrenka wzdłuż półrozpiętości (Danilecki rozdz. 7)
- Wymiarowanie usterzeń poziomego i pionowego metodą współczynników objętościowych VH i VV
- Powierzchnie omywane (Raymer rozdz. 12 / Torenbeek)
- Mechanizację krawędzi spływu: klapy i lotki (prof. C. Galiński rozdz. 16, Danilecki rozdz. 8)
- Kąt wzniosu, skos, podwozie i wyznaczenie przekroju krytycznego przeciągnięcia
"""
import math
from calculations.atmosphere import G0

def calculate_geometry(m0: float, ws: float, params: dict):
    """
    Wymiarowanie geometryczne zespołów płatowca na podstawie obciążenia powierzchni i masy startowej.
    """
    AR = float(params.get("aspect_ratio", 8.0))
    eta = float(params.get("taper_ratio", 0.55))
    sweep_deg = float(params.get("sweep_quarter_deg", 0.0))
    dihedral_deg = float(params.get("dihedral_deg", 3.0))
    n_pax = int(params.get("n_pax", 4))
    ac_type = params.get("aircraft_type", "piston_ga")
    
    # 1. Geometria skrzydła i wybór obrysu płata
    weight_n = m0 * G0
    S = float(params.get("wing_area_m2")) if params.get("wing_area_m2") else (weight_n / ws)
    AR = max(2.0, min(35.0, float(params.get("aspect_ratio", 8.0))))

    req_span = params.get("wingspan_m") or params.get("span_limit")
    try:
        req_span_val = float(req_span) if req_span is not None else 0.0
    except (ValueError, TypeError):
        req_span_val = 0.0

    if req_span_val > 0.5:
        b = req_span_val
        AR = (b ** 2) / S
    else:
        b = max(1.0, math.sqrt(S * AR))

    half_span = b / 2.0
    wing_config = params.get("wing_config", "low") # 'low', 'high', 'mid'
    planform = params.get("wing_planform", "trapezoidal")
    if planform not in ("trapezoidal", "rectangular", "compound_trapezoid", "elliptical", "swept_trapezoidal"):
        planform = "trapezoidal"

    sweep_rad = math.radians(sweep_deg)
    y_brk_m = None
    break_span_ratio = float(params.get("break_span_ratio", 0.40))

    if planform == "rectangular":
        eta = 1.0
        cr = S / b
        ct = cr
        mac = cr
        y_mac = b / 4.0
        x_le_mac = y_mac * math.tan(sweep_rad)
        planform_name_pl = "Prostokątny (stała cięciwa)"
        def chord_at_y(y_val):
            return cr
        def int_y_c(y_val):
            return cr * (y_val ** 2) / 2.0

    elif planform == "elliptical":
        eta = 0.0
        c0 = (4.0 * S) / (math.pi * b)
        cr = c0
        ct = 0.0
        mac = (8.0 / (3.0 * math.pi)) * c0
        y_mac = (2.0 * b) / (3.0 * math.pi)
        x_le_mac = y_mac * math.tan(sweep_rad) + .25 * (cr - mac)
        planform_name_pl = "Eliptyczny (wg Prandtla)"
        def chord_at_y(y_val):
            eta_loc = max(0.0, min(1.0, y_val / half_span))
            return cr * math.sqrt(max(0.0, 1.0 - eta_loc ** 2))
        def int_y_c(y_val):
            eta_loc = max(0.0, min(1.0, y_val / half_span))
            return ((half_span ** 2) * cr / 3.0) * (1.0 - (max(0.0, 1.0 - eta_loc ** 2) ** 1.5))

    elif planform == "compound_trapezoid":
        planform_name_pl = "Prostokątno-trapezowy (centropłat prostokątny + końcówki trapezowe)"
        xi_brk = break_span_ratio
        y_brk = xi_brk * half_span
        y_brk_m = round(y_brk, 2)
        eta_tip = float(params.get("taper_ratio", 0.60))
        eta = eta_tip
        w = half_span - y_brk
        denom = 2.0 * (y_brk + ((1.0 + eta_tip) / 2.0) * w)
        cr = S / max(0.01, denom)
        ct = eta_tip * cr
        mac = (2.0 / S) * (cr ** 2 * y_brk + (w / 3.0) * (cr ** 2 + cr * ct + ct ** 2))
        i1 = cr * (y_brk ** 2) / 2.0
        delta_c = cr - ct
        i2 = y_brk * ((cr + ct) / 2.0) * w + (w ** 2) * ((cr / 2.0) - (delta_c / 3.0))
        y_mac = (2.0 / S) * (i1 + i2)
        x_le_mac = y_mac * math.tan(sweep_rad) + .25 * (cr - mac)
        def chord_at_y(y_val):
            if y_val <= y_brk:
                return cr
            eta_out = max(0.0, min(1.0, (y_val - y_brk) / max(0.01, w)))
            return cr - (cr - ct) * eta_out
        def int_y_c(y_val):
            if y_val <= y_brk:
                return cr * (y_val ** 2) / 2.0
            part1 = cr * (y_brk ** 2) / 2.0
            u = y_val - y_brk
            part2 = y_brk * (cr * u - delta_c * (u ** 2) / (2.0 * w)) + cr * (u ** 2) / 2.0 - delta_c * (u ** 3) / (3.0 * w)
            return part1 + part2

    else: # trapezoidal or swept_trapezoidal
        eta = float(params.get("taper_ratio", 0.55))
        cr = (2.0 * S) / (b * (1.0 + eta))
        ct = eta * cr
        mac = (2.0 / 3.0) * cr * ((1.0 + eta + eta ** 2) / (1.0 + eta))
        y_mac = (b / 6.0) * ((1.0 + 2.0 * eta) / (1.0 + eta))
        tan_chi0 = math.tan(sweep_rad) + (cr * (1.0 - eta)) / (2.0 * b)
        x_le_mac = y_mac * tan_chi0
        planform_name_pl = "Skośny trapezowy" if (planform == "swept_trapezoidal" or sweep_deg > 5.0) else "Trapezowy (zbieżny prosty)"
        def chord_at_y(y_val):
            eta_loc = max(0.0, min(1.0, y_val / half_span))
            return cr * (1.0 - (1.0 - eta) * eta_loc)
        def int_y_c(y_val):
            return cr * (y_val ** 2) / 2.0 - ((cr - ct) / half_span) * (y_val ** 3) / 3.0

    # 2. Geometria kadłuba (wstępne oszacowanie z liczby pasażerów i rozpiętości)
    # Freighters: the hold volume follows from the payload density (C-295 ≈ 140, C-130 ≈ 180 kg/m³),
    # with height 0.9·width, length 4·width and room for an LD-3 container (2.0 m wide).
    hold = None
    hold_density = float(params.get('cargo_hold_density_kg_m3') or 0)
    cargo_mass = float(params.get('m_cargo') or 0)
    cargo_dimensions = [float(params.get(key, 0)) for key in
                        ('cargo_bay_length_m', 'cargo_bay_width_m', 'cargo_bay_height_m')]
    if all(cargo_dimensions):
        length, width, height = cargo_dimensions
        volume = length*width*height
        hold = dict(volume_m3=volume, width=width, height=height, length=length,
                    density_kg_m3=cargo_mass/volume, basis='explicit_dimensions')
    elif hold_density and cargo_mass and ac_type in ('turboprop_regional', 'jet_business', 'jet_transport'):
        volume = cargo_mass / hold_density
        width = max(2.0, (volume / 3.6) ** (1 / 3))
        hold = dict(volume_m3=volume, width=width, height=.9*width,
                    length=volume/(.9*width**2), density_kg_m3=hold_density,
                    basis='assumed_payload_density')
    if ac_type in ("glider", "motoglider"):
        fuselage_len = max(5.5, 0.45 * b)
        # Średnica zastępcza przekroju czołowego kabiny (z owiewką): jednomiejscowy
        # ~0,60×0,85 m, tandem ~0,65×1,0 m, miejsca obok siebie ~1,10×1,0 m.
        seats = int(params.get("n_crew", 1)) + n_pax
        layout = params.get("seats_config") or ("tandem" if ac_type == "glider" else "side")
        if seats <= 1:
            fuselage_diam = 0.72
        elif layout == "tandem":
            fuselage_diam = 0.82
        else:
            fuselage_diam = 1.10
    elif ac_type == "uav":
        # Bez kabiny: przekrój wynika z ładunku i paliwa, rośnie z masą
        # (taktyczny ~150 kg: ~0,43 m; MALE ~900 kg: ~0,77 m; ~4700 kg: ~1,34 m).
        fuselage_len = max(1.5, 0.55 * b)
        fuselage_diam = max(0.25, min(1.4, 0.08 * m0 ** (1.0 / 3.0)))
    elif ac_type == "piston_ga":
        fuselage_len = max(5.5, 0.72 * b)
        fuselage_diam = 1.25 if n_pax <= 4 else 1.50
    elif ac_type in ('turboprop_regional', 'jet_business'):
        # Explicit cabin-layout assumptions: seats + aisle + shell allowance.
        seats_abreast = 4 if n_pax > 19 else 2
        fuselage_diam = seats_abreast * .48 + .45 + .30
        cabin_length = max(2, math.ceil(n_pax / seats_abreast)) * .80
        fuselage_len = cabin_length + 4 * fuselage_diam
    else: # jet_transport
        seats_abreast = 6 if n_pax > 120 else 4
        fuselage_diam = seats_abreast * .48 + .50 + .35
        cabin_length = max(2, math.ceil(n_pax / seats_abreast)) * .80
        fuselage_len = cabin_length + 4 * fuselage_diam
        
    cargo_bay = None
    if hold:
        cargo_length, cargo_width, cargo_height = hold['length'], hold['width'], hold['height']
        layout_length, layout_diameter = fuselage_len, fuselage_diam
        # Circular outer envelope of the rectangular usable cross section.
        # 0.30 m is an explicit diametral allowance, not a structural sizing.
        fuselage_diam = max(fuselage_diam, math.hypot(cargo_width, cargo_height) + .30)
        fuselage_len = max(fuselage_len, cargo_length + 4*fuselage_diam)
        cargo_bay = dict(length_m=cargo_length, width_m=cargo_width, height_m=cargo_height,
                         volume_m3=cargo_length*cargo_width*cargo_height,
                         layout_length_m=layout_length, layout_diameter_m=layout_diameter,
                         basis=hold['basis'],
                         shell_diametral_allowance_m=.30)
    fuselage_fineness = fuselage_len / fuselage_diam
    
    # 3. Geometria usterzenia poziomego (UP) metodą współczynnika objętościowego VH
    # V_H = (S_H * L_H) / (S * MAC) (wg Usterzenie_wymiary.pdf str. 2-7 / T. Corke)
    engine_loc = params.get("engine_location", "nose")
    if engine_loc == "nose":
        lh_ratio = 0.58
        lv_ratio = 0.55
    elif engine_loc == "rear":
        lh_ratio = 0.47
        lv_ratio = 0.45
    else: # wing
        lh_ratio = 0.53
        lv_ratio = 0.50

    vh_coeff = float(params.get("v_h", 0.70))
    l_h = float(params.get('_tail_arm_h', lh_ratio * fuselage_len))
    S_h = (vh_coeff * S * mac) / l_h
    ar_h = float(params.get("ar_h", 4.0))
    eta_h = 0.60
    b_h = math.sqrt(S_h * ar_h)
    cr_h = (2.0 * S_h) / (b_h * (1.0 + eta_h))
    ct_h = eta_h * cr_h
    mac_h = (2.0 / 3.0) * cr_h * ((1.0 + eta_h + eta_h**2) / (1.0 + eta_h))
    
    # 4. Geometria usterzenia pionowego (UV) metodą współczynnika objętościowego VV
    # V_V = (S_V * L_V) / (S * b)
    vv_coeff = float(params.get("v_v", 0.050))
    l_v = float(params.get('_tail_arm_v', lv_ratio * fuselage_len))
    S_v = (vv_coeff * S * b) / l_v
    ar_v = float(params.get("ar_v", 1.6))
    eta_v = 0.65
    h_v = math.sqrt(S_v * ar_v) # Wysokość usterzenia pionowego
    cr_v = (2.0 * S_v) / (h_v * (1.0 + eta_v))
    ct_v = eta_v * cr_v
    mac_v = (2.0 / 3.0) * cr_v * ((1.0 + eta_v + eta_v**2) / (1.0 + eta_v))
    
    # 5. Podwozie (Wheelbase & Track)
    gear_wheelbase = round(0.38 * fuselage_len, 2) # Baza podwozia
    gear_track = round(0.24 * b, 2)               # Rozstaw kół podwozia głównego
    
    # 6. Rozkład obciążenia Schrenka wzdłuż półrozpiętości y w [0, b/2]
    # c_geom(y) z obrysu wybranego przez użytkownika
    # c_ellip(y) = (4 * S) / (pi * b) * sqrt(1 - (y / (b/2))^2)
    # c_schrenk(y) = (c_geom + c_ellip) / 2
    n_points = 25
    schrenk_data = []
    c_ellip_root = (4.0 * S) / (math.pi * b)
    
    for i in range(n_points + 1):
        y = (i / n_points) * half_span
        eta_span = y / half_span # y / (b/2) od 0 do 1
        c_geom = chord_at_y(y)
        arg = max(0.0, 1.0 - (eta_span ** 2))
        c_ellip = c_ellip_root * math.sqrt(arg)
        c_schrenk = 0.5 * (c_geom + c_ellip)
        cz_local_norm = 0.5 * (1.0 + (c_ellip / max(0.001, c_geom)))
        
        schrenk_data.append({
            "y": round(y, 2),
            "eta_span": round(eta_span, 3),
            "c_geom": round(c_geom, 3),
            "c_ellip": round(c_ellip, 3),
            "c_schrenk": round(c_schrenk, 3),
            "cz_local_norm": round(cz_local_norm, 3)
        })

    # Wyznaczenie przekroju krytycznego skrzydła wg metody Schrenka (maksimum cz_local_norm)
    crit_pt = max(schrenk_data[:-1], key=lambda pt: pt["cz_local_norm"])
    max_cz1_schrenk = crit_pt["cz_local_norm"]
    stall_eta_span = crit_pt["eta_span"]
    stall_y_m = crit_pt["y"]

    # Powierzchnie omywane poszczególnych zespołów płatowca (Raymer rozdz. 12.5 / Torenbeek)
    tc_wing = float(params.get("tc_ratio", 0.12))
    tc_tail = 0.09
    s_exposed = max(0.75 * S, S - cr * fuselage_diam)
    s_wet_wing = 2.0 * s_exposed * (1.0 + 0.25 * tc_wing)
    s_wet_fus = math.pi * fuselage_diam * fuselage_len * math.pow(max(0.5, 1.0 - 2.0 / fuselage_fineness), 2.0 / 3.0) * (1.0 + 1.0 / (fuselage_fineness ** 2))
    s_wet_htail = 2.0 * S_h * (1.0 + 0.25 * tc_tail)
    s_wet_vtail = 2.0 * S_v * (1.0 + 0.25 * tc_tail)
    s_wet_total = s_wet_wing + s_wet_fus + s_wet_htail + s_wet_vtail

    # =========================================================================
    # 7. MECHANIZACJA KRAWĘDZI SPŁYWU: KLAPY (FLAPS) ORAZ LOTKI (AILERONS)
    # Wg wytycznych BIPOL I (prof. C. Galiński rozdz. 16, T. Grabowski wzór 7, Danilecki rozdz. 8, Raymer rozdz. 12)
    # =========================================================================
    flap_type = params.get("flap_type", "single_slotted")
    aileron_type = params.get("aileron_type")
    if not aileron_type:
        aileron_type = "flaperon" if flap_type == "flaperon" else "differential"

    is_flaperon = (flap_type == "flaperon") or (aileron_type == "flaperon")

    r_fus = fuselage_diam / 2.0
    eta_fus = r_fus / half_span

    if is_flaperon:
        # Klapolotka: pojedyncza powierzchnia sterowa na niemal pełnej rozpiętości
        eta_f_in = min(0.15, max(eta_fus, 0.08))
        eta_f_out = 0.95
        eta_a_in = eta_f_in
        eta_a_out = eta_f_out
        cf_c_ratio = float(params.get("flap_chord_ratio", 0.25))
        ca_c_ratio = float(params.get("aileron_chord_ratio", cf_c_ratio))
        bf_b_ratio = eta_f_out - eta_f_in
        ba_b_ratio = bf_b_ratio
    else:
        # Standardowy układ: Klapy wewnętrzne (przykadłubowe) + Lotki zewnętrzne (przykońcówkowe)
        user_bf_b = float(params.get("flap_span_ratio", 0.60))
        user_ba_b = float(params.get("aileron_span_ratio", 0.28))
        cf_c_ratio = float(params.get("flap_chord_ratio", 0.25))
        ca_c_ratio = float(params.get("aileron_chord_ratio", 0.22))

        eta_f_in = max(eta_fus, 0.05)
        eta_f_out = min(0.74, max(eta_f_in + 0.15, eta_f_in + user_bf_b))
        bf_b_ratio = eta_f_out - eta_f_in

        eta_gap = 0.015
        eta_a_in = min(0.85, eta_f_out + eta_gap)
        eta_a_out = min(0.97, max(eta_a_in + 0.10, eta_a_in + user_ba_b))
        ba_b_ratio = eta_a_out - eta_a_in

    y_f_in = eta_f_in * half_span
    y_f_out = eta_f_out * half_span
    y_a_in = eta_a_in * half_span
    y_a_out = eta_a_out * half_span

    b_flap_m = 2.0 * (y_f_out - y_f_in)
    b_aileron_m = 2.0 * (y_a_out - y_a_in)

    c_f_in = chord_at_y(y_f_in)
    c_f_out = chord_at_y(y_f_out)
    # Integrate the actual planform (trapezoid shortcut is wrong across a
    # compound-wing break and for elliptical wings).
    def segment_area(y1, y2):
        steps = 200
        dy = (y2 - y1) / steps
        return 2 * dy * (chord_at_y(y1) + chord_at_y(y2) +
            sum((4 if i % 2 else 2) * chord_at_y(y1 + i * dy) for i in range(1, steps))) / 3
    s_flapped_wing = segment_area(y_f_in, y_f_out)
    s_flap_surface = s_flapped_wing * cf_c_ratio

    c_a_in = chord_at_y(y_a_in)
    c_a_out = chord_at_y(y_a_out)
    s_aileron_wing = segment_area(y_a_in, y_a_out)
    s_aileron_surface = s_aileron_wing * ca_c_ratio

    # Skuteczność poprzeczna i sterowność lotek (Roll Authority pb/2V wg Raymera eq. 12.18 / Roskama)
    tau_a = 1.2 * math.sqrt(ca_c_ratio)
    aw_est = (2.0 * math.pi * AR) / (2.0 + math.sqrt(4.0 + (AR / max(0.2, math.cos(sweep_rad))) ** 2))

    geom_roll_integral = int_y_c(y_a_out) - int_y_c(y_a_in)
    cl_delta_a = (2.0 * aw_est * tau_a / (S * b)) * geom_roll_integral
    # C_l,p = -4 a/(S b²) integral_0^(b/2) y² c(y) dy, with p_hat = pb/(2V).
    # Integrating the actual outline also covers elliptical and compound wings.
    roll_steps = 400
    roll_dy = half_span / roll_steps
    roll_moment = roll_dy / 3 * (half_span**2 * chord_at_y(half_span) +
        sum((4 if i % 2 else 2) * (i*roll_dy)**2 * chord_at_y(i*roll_dy)
            for i in range(1, roll_steps)))
    cl_p = -4 * aw_est * roll_moment / (S * b**2)

    delta_a_max_deg = 20.0
    delta_a_max_rad = math.radians(delta_a_max_deg)
    roll_helix_pb_2v = abs((cl_delta_a / min(-0.01, cl_p)) * delta_a_max_rad)

    # Preliminary handling-quality targets; not a certification finding.
    if ac_type in ("glider", "motoglider"):
        min_pb_2v_req = 0.040
    elif ac_type in ("jet_business", "jet_transport"):
        min_pb_2v_req = 0.055
    else: # piston_ga
        min_pb_2v_req = 0.070
    roll_authority_ok = roll_helix_pb_2v >= min_pb_2v_req

    # Ocena bezpieczeństwa przeciągnięcia
    stall_inboard_of_aileron = stall_eta_span < eta_a_in
    if planform == "rectangular":
        stall_safety_verdict = "Schrenk wskazuje większe obciążenie przy nasadzie. Zachowanie przy przeciągnięciu wymaga sprawdzenia profili, zwichrzenia i przepływu."
    elif planform == "compound_trapezoid":
        stall_safety_verdict = "Obliczono rozkład obciążenia centropłata i końcówek. Sam obrys nie gwarantuje sterowności po przeciągnięciu."
    elif planform == "elliptical":
        stall_safety_verdict = "Idealny rozkład eliptyczny daje jednakowe lokalne Cz. To nie określa rzeczywistej kolejności przeciągnięcia."
    elif stall_inboard_of_aileron:
        stall_safety_verdict = "Przekrój o największym lokalnym Cz wypada przed lotkami. Potwierdzenie sterowności wymaga danych profilu i zwichrzenia."
    else:
        stall_safety_verdict = "Ostrzeżenie: przekrój krytyczny w rejonie lotek. Wymagane zwichrzenie geometryczne końcówek."

    flap_names = {
        "none": "Bez klap",
        "plain": "Klapa zwykła (uchylna)",
        "split": "Klapa krokowa",
        "single_slotted": "Klapa jednoszczelinowa",
        "double_slotted": "Klapa dwuszczelinowa",
        "fowler": "Klapa wysuwana Fowlera",
        "junkers": "Klapa zewnętrzna Junkersa (szczelinowa)",
        "flaperon": "Klapolotka (Flaperon)"
    }
    flap_name_pl = flap_names.get(flap_type, "Klapa jednoszczelinowa")

    aileron_names = {
        "plain": "Lotka zwykła",
        "differential": "Lotka różnicowa (ograniczenie momentu oporowego)",
        "frise": "Lotka typu Frise (kompensacja aerodynamiczna)",
        "slotted": "Lotka szczelinowa",
        "flaperon": "Klapolotka (sterowanie łączone ze sprzężeniem)"
    }
    aileron_name_pl = aileron_names.get(aileron_type, "Lotka różnicowa")

    control_surfaces = {
        "layout": "flaperon" if is_flaperon else "flaps_and_ailerons",
        "is_flaperon": is_flaperon,
        "slats": {
            "type": params.get('slat_type', 'none'),
            "y_in_m": round(max(fuselage_diam*.6, half_span*.08), 3),
            "y_out_m": round(half_span*.94, 3),
            "s_equipped_over_s": max(0, segment_area(min(half_span*.94, max(fuselage_diam*.6, half_span*.08)), half_span*.94)) / S
                if params.get('slat_type', 'none') != 'none' else 0.0,
        },
        "flaps": {
            "type": flap_type,
            "name": flap_name_pl,
            "b_f_m": round(b_flap_m, 2),
            "bf_over_b": round(bf_b_ratio, 3),
            "cf_over_c": round(cf_c_ratio, 3),
            "eta_in": round(eta_f_in, 3),
            "eta_out": round(eta_f_out, 3),
            "y_in_m": round(y_f_in, 2),
            "y_out_m": round(y_f_out, 2),
            "S_flapped_m2": round(s_flapped_wing, 2),
            "s_flapped_over_s": s_flapped_wing / S,
            "S_flap_surface_m2": round(s_flap_surface, 2),
            "s_flap_over_s": round(s_flap_surface / S, 3),
        },
        "ailerons": {
            "type": aileron_type,
            "name": aileron_name_pl,
            "b_a_m": round(b_aileron_m, 2),
            "ba_over_b": round(ba_b_ratio, 3),
            "ca_over_c": round(ca_c_ratio, 3),
            "eta_in": round(eta_a_in, 3),
            "eta_out": round(eta_a_out, 3),
            "y_in_m": round(y_a_in, 2),
            "y_out_m": round(y_a_out, 2),
            "S_aileron_segment_m2": round(s_aileron_wing, 2),
            "s_aileron_seg_over_s": round(s_aileron_wing / S, 3),
            "S_aileron_surface_m2": round(s_aileron_surface, 2),
            "s_aileron_over_s": round(s_aileron_surface / S, 3),
            "roll_helix_pb_2v": round(roll_helix_pb_2v, 3),
            "cl_p": round(cl_p, 5),
            "cl_delta_a": round(cl_delta_a, 5),
            "tau_a": tau_a,
            "a_w_est": aw_est,
            "int_y_c": geom_roll_integral,
            "int_y2_c": roll_moment,
            "roll_authority_ok": roll_authority_ok,
            "min_pb_2v_req": min_pb_2v_req,
            "delta_a_max_deg": delta_a_max_deg,
        },
        "trailing_edge_partition": {
            "fuselage_gap_pct": round(eta_fus * 100.0, 1),
            "flap_span_pct": round(bf_b_ratio * 100.0, 1),
            "clearance_gap_pct": round((eta_a_in - eta_f_out) * 100.0, 1) if not is_flaperon else 0.0,
            "aileron_span_pct": round(ba_b_ratio * 100.0, 1),
            "tip_clearance_pct": round((1.0 - eta_a_out) * 100.0, 1),
        },
        "stall_safety": {
            "stall_eta_span": round(stall_eta_span, 3),
            "stall_inboard_of_aileron": stall_inboard_of_aileron,
            "verdict": stall_safety_verdict
        },
        "elevator": {
            "ce_over_ch": round(float(params.get("elevator_chord_ratio", params.get("ce_ch", 0.35))), 3),
            "type": "stabilator" if float(params.get("elevator_chord_ratio", params.get("ce_ch", 0.35))) >= 0.99 else "hinged_elevator",
            "name": "Płytowy (stabilator)" if float(params.get("elevator_chord_ratio", params.get("ce_ch", 0.35))) >= 0.99 else "Klasyczny ster wysokości zawiasowy"
        },
        "rudder": {
            "cr_over_cv": round(float(params.get("rudder_chord_ratio", params.get("cr_cv", 0.35))), 3),
            "name": "Klasyczny ster kierunku zawiasowy"
        }
    }

    return {
        "wing": {
            # Input mode as used here; parameter states later copy S and b back into params.
            "span_fixed": req_span_val > 0.5,
            "area_fixed": bool(params.get("wing_area_m2")),
            "S": S,
            "S_exposed": s_exposed,
            "S_wet": s_wet_wing,
            "b": b,
            "AR": AR,
            "eta": eta,
            "cr": cr,
            "ct": ct,
            "mac": mac,
            "y_mac": y_mac,
            "x_le_mac": x_le_mac,
            "sweep_deg": sweep_deg,
            "dihedral_deg": dihedral_deg,
            "wing_config": wing_config,
            "wing_planform": planform,
            "planform_name_pl": planform_name_pl,
            "break_station_m": y_brk_m,
            "tc_ratio": tc_wing
        },
        "fuselage": {
            "seats_abreast": seats_abreast if ac_type in ('turboprop_regional', 'jet_business', 'jet_transport') else None,
            "sizing_note": ("Obwiednia ładowni: D ≥ √(szerokość² + wysokość²) + 0,30 m; L ≥ długość ładowni + 4D. Wymiary użytkowe są założeniami, wymagają sprawdzenia rampy, prześwitów i konstrukcji."
                            if cargo_bay else "Kabina: rozstaw rzędów 0,80 m, fotel 0,48 m; przejście i poszycie oraz 4 średnice na nos i ogon. Układ roboczy, wymaga projektu kabiny." if ac_type in ('turboprop_regional','jet_business','jet_transport') else "Wstępna proporcja zależna od rozpiętości; wymaga sprawdzenia zabudowy."),
            "cargo_bay": cargo_bay,
            "length": fuselage_len,
            "diameter": fuselage_diam,
            "fineness": fuselage_fineness,
            "S_wet": s_wet_fus,
            "cargo_hold": hold,
        },
        "horizontal_tail": {
            "x_ac_m": .90 * fuselage_len,
            "S_h": S_h,
            "S_wet": s_wet_htail,
            "b_h": b_h,
            "AR_h": ar_h,
            "cr_h": cr_h,
            "ct_h": ct_h,
            "mac_h": mac_h,
            "l_h": l_h,
            "vh_coeff": vh_coeff,
            "ce_over_ch": round(float(params.get("elevator_chord_ratio", params.get("ce_ch", 0.35))), 3)
        },
        "vertical_tail": {
            "x_ac_m": .90 * fuselage_len,
            "S_v": S_v,
            "S_wet": s_wet_vtail,
            "h_v": h_v,
            "AR_v": ar_v,
            "cr_v": cr_v,
            "ct_v": ct_v,
            "mac_v": mac_v,
            "l_v": l_v,
            "vv_coeff": vv_coeff,
            "cr_over_cv": round(float(params.get("rudder_chord_ratio", params.get("cr_cv", 0.35))), 3)
        },
        "gear": {
            "wheelbase": gear_wheelbase,
            "track": gear_track
        },
        "wetted_area": {
            "total_m2": s_wet_total,
            "swet_over_s": round(s_wet_total / S, 2)
        },
        "schrenk": schrenk_data,
        "schrenk_Pinpoint": {
            "max_cz1": max_cz1_schrenk,
            "stall_eta_span": stall_eta_span,
            "stall_y_m": stall_y_m
        },
        "control_surfaces": control_surfaces
    }
