"""
Moduł wyważenia samolotu i stateczności statycznej podłużnej (BIPOL I)
Wyznaczanie położenia środka masy w różnych konfiguracjach załadowania,
przeliczenie na % ŚDA (MAC), wyznaczenie punktu neutralnego oraz zapasu stateczności.
"""
import math
from calculations.flight_model import mission_masses
from calculations.geometry import axis_height_m, cg_height_m
from calculations.paturski_ml import wing_alpha_deg
from calculations.propeller import design_propeller

MIN_STATIC_MARGIN_PCT = 5.0
# Upper end of usual horizontal tail volumes (Raymer, tab. 6.4: up to 1.0 for transports).
MAX_TAIL_VOLUME = 1.2


GEAR_MAIN_SHARE = 0.85


def calculate_balance_and_stability(m_sizing: dict, geom: dict, aero: dict, params: dict):
    """
    Parametry:
      - m_sizing: wyniki bilansu mas (m0, m_empty, m_fuel, m_payload, m_crew, breakdown)
      - geom: geometria płatowca (L_fus, mac, x_le_mac, S, S_h, l_h)
      - aero: aerodynamika
      - params: konfiguracja układu (układ silników itp.)
    """
    l_f = float(geom["fuselage"]["length"])
    d_f = float(geom["fuselage"]["diameter"])
    S = float(geom["wing"]["S"])
    AR = float(geom["wing"]["AR"])
    mac = float(geom["wing"]["mac"])
    x_le_mac_offset = float(geom["wing"]["x_le_mac"])
    
    # Dobór podłużnego położenia skrzydła na kadłubie (x_lemac) metodą wyważenia grup masowych (wg Raymer / Torenbeek / BIPOL):
    # Zespoły związane z kadłubem: kadłub, usterzenie, instalacje oraz napęd (jeśli w dziobie lub z tyłu kadłuba).
    # Zespoły związane ze skrzydłem: płat, podwozie główne oraz gondole silnikowe (jeśli na skrzydle).
    engine_loc = params.get("engine_location", "nose") # 'nose', 'wing', 'rear'
    bd = m_sizing["breakdown"]
    m_empty = max(1.0, m_sizing["m_empty"])
    m_crew = m_sizing["m_crew"]
    m_fuel = m_sizing["m_fuel"]
    m_payload = m_sizing["m_payload"]

    x_fus = 0.44 * l_f
    x_tail = 0.91 * l_f
    x_sys = 0.40 * l_f
    # Raymer, tab. 15.2 (Analiza_masowa.pdf, s. 1): 85% masy podwozia to podwozie główne, 15% przednie.
    # Z kółkiem ogonowym podwozie główne stoi przed ŚC, a kółko na końcu kadłuba.
    tailwheel = params.get("landing_gear_type") == "tailwheel"
    # Wykład 4: koło główne przed ŚC, przednie ŚC 13° za pionem przez punkt styku koła z ziemią.
    power_kw = m_sizing.get("installed_power_kw")
    propeller = design_propeller(params, power_kw * 1000.0)["diameter_m"] if power_kw else params.get("propeller_diameter_m")
    main_gear_mac = (0.25 - axis_height_m(params, d_f, propeller) * math.tan(math.radians(13.0)) / mac) if tailwheel else 0.45
    # BIPOL_3, krok 10 i wykład 7: koła główne dobiera się do tylnego ŚC w 35% ŚCA, tak by kąt między pionem
    # przez ŚC a prostą do punktu styku koła był nie mniejszy niż α przy 0,9·Cz,max + 3°.
    trim_model = (aero.get("paturski_p3") or {}).get("trim_model")
    if trim_model and not tailwheel and params.get("aircraft_type") != "glider":
        tipback = math.radians(wing_alpha_deg(trim_model, 0.9 * trim_model["cz_max_clean"]) + 3.0)
        main_gear_mac = max(main_gear_mac, 0.35 + cg_height_m(params, d_f, propeller) * math.tan(tipback) / mac + 0.005)
    x_aux_gear = (0.96 if tailwheel else 0.12) * l_f
    m_main_gear = GEAR_MAIN_SHARE * bd["m_gear"]
    mom_aux_gear = (1.0 - GEAR_MAIN_SHARE) * bd["m_gear"] * x_aux_gear

    if engine_loc == "nose":
        x_prop_fixed = 0.10 * l_f
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed +
            mom_aux_gear
        )
        m_wing_group = bd["m_wing"] + m_main_gear
        mom_wing_offset = (bd["m_wing"] * 0.38 + m_main_gear * main_gear_mac) * mac
    elif engine_loc == "rear":
        x_prop_fixed = 0.76 * l_f
        target_oew_mac = 0.27
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed +
            mom_aux_gear
        )
        m_wing_group = bd["m_wing"] + m_main_gear
        mom_wing_offset = (bd["m_wing"] * 0.38 + m_main_gear * main_gear_mac) * mac
    else: # wing
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            mom_aux_gear
        )
        m_wing_group = bd["m_wing"] + m_main_gear + bd["m_propulsion"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + m_main_gear * main_gear_mac - bd["m_propulsion"] * 0.15) * mac

    denom_m = max(1.0, m_empty - m_wing_group)
    x_lemac_raw = (mom_fus_fixed + mom_wing_offset - target_oew_mac * mac * m_empty) / denom_m
    # Light tractor aircraft carry the wing leading edge from about a quarter of the fuselage length.
    # Z ciężkim silnikiem w nosie skrzydło przechodzi nad kabinę: dolna granica jest wtedy tuż za silnikiem.
    x_lemac_bounds = (0.15 if engine_loc == "nose" else 0.25) * l_f, 0.56 * l_f
    x_lemac_initial = max(x_lemac_bounds[0], min(x_lemac_bounds[1], x_lemac_raw))

    unmanned = bool(m_sizing.get("unmanned", False)) or params.get("aircraft_type") == "uav"
    n_crew = int(m_sizing.get("n_crew") or 0)
    phases = mission_masses(m_sizing)
    dropped = m_sizing.get('m_payload_dropped',0)
    m_fuel_res = max(0.0, phases['landing_start'] - (m_sizing['m0'] - m_fuel - dropped))

    def layout(x_lemac):
        """Ramiona mas, stany załadowania i zakres ŚC w locie dla danego położenia ŚDA."""
        if engine_loc == "nose":
            x_prop = 0.10 * l_f
        elif engine_loc == "rear":
            x_prop = 0.76 * l_f
        else:
            x_prop = x_lemac - 0.15 * mac

        x_arms = {
            "fuselage": x_fus,
            "wing": x_lemac + 0.38 * mac,
            "tail": x_tail,
            "propulsion": x_prop,
            "gear": x_lemac + main_gear_mac * mac,
            "gear_aux": x_aux_gear,
            "systems": x_sys,
            "crew": x_lemac - 0.18 * mac,
            "pax_front": x_lemac + 0.12 * mac,
            "pax_rear": x_lemac + 0.48 * mac,
            "baggage": x_lemac + 0.75 * mac,
            "fuel": x_lemac + 0.32 * mac
        }

        # 1. Moment masy pustej (OEW)
        def empty_moment():
            x_arms["gear_group"] = GEAR_MAIN_SHARE * x_arms["gear"] + (1.0 - GEAR_MAIN_SHARE) * x_aux_gear
            return (
                bd["m_fuselage"] * x_arms["fuselage"] +
                bd["m_wing"] * x_arms["wing"] +
                bd["m_tail"] * x_arms["tail"] +
                bd["m_propulsion"] * x_arms["propulsion"] +
                bd["m_gear"] * x_arms["gear_group"] +
                bd["m_systems"] * x_arms["systems"]
            )
        mom_empty = empty_moment()
        # BIPOL_3, pkt 7: rzut ŚC na ziemię leży między kołami także dla samolotu pustego.
        if not tailwheel and mom_empty / m_empty > x_arms["gear"] - 0.05 * mac:
            x_arms["gear"] = mom_empty / m_empty + 0.05 * mac
            mom_empty = empty_moment()

        if unmanned:
            # UAV: wyposażenie zadaniowe (głowica optoelektroniczna w dziobie/pod kadłubem + awionika misji w okolicy ŚM)
            x_arms["payload_sensor"] = x_lemac - 0.35 * mac
            x_arms["payload_bay"] = x_lemac + 0.20 * mac
            mom_payload = (m_payload * 0.60) * x_arms["payload_sensor"] + (m_payload * 0.40) * x_arms["payload_bay"]
        else:
            m_pax = int(params.get('n_pax', 0)) * (float(params.get('m_pax', 115)) + float(params.get('m_bag', 0)))
            cargo = float(params.get('m_cargo', 0))
            mom_payload = m_pax * (.45 * x_arms['pax_front'] + .55 * x_arms['pax_rear']) + cargo * x_arms['baggage']
        x_arms['payload_equivalent'] = mom_payload / m_payload if m_payload else x_arms['pax_front']

        # Funkcja pomocnicza: przeliczenie na % ŚDA (MAC)
        def to_percent_mac(x):
            return (x - x_lemac) / mac * 100.0

        def state(key, name, crew=0.0, payload=False, fuel=0.0, released=0.0):
            """Stan załadowania złożony z masy pustej, załogi, ładunku i paliwa (BIPOL_3, wzór 3.1)."""
            mass = m_empty + crew + (m_payload if payload else 0.0) + fuel - released
            drop_arm = x_arms['payload_equivalent'] if unmanned else x_arms['baggage']
            mom = mom_empty + crew * x_arms["crew"] + (mom_payload if payload else 0.0) + fuel * x_arms["fuel"] - released*drop_arm
            x_cg = mom / max(1.0, mass)
            return {"key": key, "name": name, "mass_kg": mass, "xcg_m": x_cg,
                    "moment_kg_m": mom,
                    "xcg_mac_pct": to_percent_mac(x_cg), "_payload": payload, "_fuel": fuel, "_released":released}

        # Warianty wg BIPOL_3: MTOW, lądowanie, start i lądowanie bez ładunku płatnego, samolot pusty.
        # Masą płatną szybowca i motoszybowca jest druga osoba, nie ładunek.
        no_payload = "drugiej osoby" if params.get("aircraft_type") in ("glider", "motoglider") else "ładunku płatnego"
        # MTOW pozostaje ostatni (odczytują go widoki rysunku).
        states = [state("oew", "Masa pusta (OEW)")]
        if not unmanned:
            # Bez masy płatnej stan „pusty + załoga” jest tym samym co masa bez paliwa.
            if m_payload > 0:
                states.append(state("crew", "Pusty + załoga", crew=m_crew))
        else:
            # UAV: pusty + pełne paliwo bez wyposażenia zadaniowego (lot techniczny / przebazowanie)
            states.append(state("ferry", "Pusty + paliwo, bez wyposażenia zadaniowego", fuel=m_fuel))
        states += [
            state("zfw", "Masa bez paliwa (ZFW)" if not unmanned else "Pusty + wyposażenie zadaniowe (ZFW)",
                  crew=m_crew, payload=True),
            state("mlw", "Masa lądowania (MLW)", crew=m_crew, payload=True, fuel=m_fuel_res,released=dropped),
        ]
        if dropped:
            before = next(s for s in m_sizing['mission_phases'] if s['key']=='drop')
            fuel_at_drop = before['mass_start_kg']-(m_empty+m_crew+m_payload)
            states += [state('before_drop','Przed zrzutem',crew=m_crew,payload=True,fuel=max(0,fuel_at_drop)),
                       state('after_drop','Po zrzucie',crew=m_crew,payload=True,fuel=max(0,fuel_at_drop),released=dropped)]
        if m_fuel > 0 and m_payload > 0:
            if not unmanned:
                states.append(state("tow_no_payload", f"Start bez {no_payload}", crew=m_crew, fuel=m_fuel))
            states.append(state("mlw_no_payload", f"Lądowanie bez {no_payload}", crew=m_crew, fuel=m_fuel_res))
        states.append(state("mtow", "Masa startowa (MTOW)", crew=m_crew, payload=True, fuel=m_fuel))

        # BIPOL_3, Tab. 3.1–3.2: obliczenia powtarza się dla lekkiego (55 kg) i ciężkiego (110 kg) pilota.
        variants = []
        if not unmanned and n_crew and m_crew > 0:
            for s in states[1:]:
                light, heavy = (state(s["key"], s["name"], crew=n_crew * pilot, payload=s["_payload"], fuel=s["_fuel"],released=s['_released'])
                                for pilot in (55.0, 110.0))
                variants.append({"key": s["key"], "name": s["name"],
                                 "light_pct": light["xcg_mac_pct"], "heavy_pct": heavy["xcg_mac_pct"]})
        for s in states:
            del s["_payload"], s["_fuel"], s['_released']

        # Zakres położeń środka ciężkości w locie (samolot pusty nie lata; BIPOL_3, pkt 7)
        flight = ([s["xcg_mac_pct"] for s in states if s["key"] != "oew"]
                  + [v[k] for v in variants for k in ("light_pct", "heavy_pct")])
        return x_arms, states, variants, min(flight), max(flight)

    def criterion(fwd, aft):
        # Dopuszcza się przednie położenie przed 25% ŚDA, jeśli zakres w locie przekracza 10% ŚDA.
        return fwd >= 25.0 or aft - fwd > 10.0, aft <= 35.0

    # 6. Punkt neutralny płatowca (Neutral Point x_N) wg równania stateczności podłużnej (Mechanika Lotu I - Projekt 6):
    # x_N/MAC = x_ac_wbn + eta_H * V_H * (a_H / a_W) * (1 - d_epsilon / d_alpha); nie zależy od położenia skrzydła.
    vh = float(geom["horizontal_tail"]["vh_coeff"])
    ar_h = float(geom["horizontal_tail"]["AR_h"])
    a_w = (2.0 * math.pi * AR) / (AR + 2.0)
    a_h = (2.0 * math.pi * ar_h) / (ar_h + 2.0)
    de_da = min(0.55, (2.0 * a_w) / (math.pi * AR))  # Gradient odchylenia strug za skrzydłem d_epsilon/d_alpha
    eta_h_eff = 0.72  # Współczynnik spiętrzenia i interferencji na usterzeniu poziomym (z wolnym/trymowanym sterem)

    # Destabilizujący wpływ kadłuba oraz gondoli/śmigła wg wzoru Munka-Multhoppa: Delta x_ac_fus + Delta x_ac_nac
    engine_type = params.get("engine_type", "prop")
    delta_xac_fus = min(0.11, max(0.055, (0.35 * (d_f ** 2) * l_f) / (S * mac * a_w)))
    if engine_type == "none":
        delta_xac_prop = 0.0
    elif engine_type == "jet":
        delta_xac_prop = 0.015 if engine_loc == "wing" else 0.008
    else:
        delta_xac_prop = 0.030 if engine_loc in ["nose", "wing"] else 0.010
    x_ac_wbn_pct = (0.25 - delta_xac_fus - delta_xac_prop) * 100.0
    delta_xn_tail_pct = (eta_h_eff * vh * (a_h / a_w) * (1.0 - de_da)) * 100.0
    neutral_point_pct = x_ac_wbn_pct + delta_xn_tail_pct

    # BIPOL_3, pkt 8: jeśli zakres wychodzi poza 25–35% ŚDA, przesuwa się skrzydło (zmiana rysunku):
    # przednie ŚC w locie na 25% ŚDA; przy zakresie > 10% ŚDA tylne na 35% ŚDA,
    # ale nie bliżej niż 5% ŚDA przed punktem neutralnym (zapas stateczności).
    x_lemac = x_lemac_initial
    x_arms, loading_states, pilot_variants, cg_forward_limit, cg_aft_limit = layout(x_lemac)
    if not all(criterion(cg_forward_limit, cg_aft_limit)):
        aft_target = min(35.0, neutral_point_pct - 5.0)

        def miss(x):  # > 0: skrzydło za bardzo z przodu (ŚC zbyt daleko do tyłu w % ŚDA)
            _, _, _, fwd, aft = layout(x)
            return aft - aft_target if aft - fwd > 10.0 else fwd - 25.0
        low, high = x_lemac_bounds  # %ŚDA maleje, gdy skrzydło przesuwa się do tyłu
        if miss(low) >= 0 >= miss(high):
            for _ in range(40):
                middle = 0.5 * (low + high)
                low, high = (middle, high) if miss(middle) > 0 else (low, middle)
            # Both ends bracket the boundary; keep the one satisfying the unrounded criterion.
            x_lemac = high if all(criterion(*layout(high)[3:])) or not all(criterion(*layout(low)[3:])) else low
        else:
            x_lemac = low if miss(low) < 0 else high
        x_arms, loading_states, pilot_variants, cg_forward_limit, cg_aft_limit = layout(x_lemac)
    x_le_wing = x_lemac - x_le_mac_offset

    # Aktualizacja rzeczywistego ramienia usterzenia i punktu neutralnego po ustaleniu x_lemac
    x_ac_h = geom["horizontal_tail"].get("x_ac_m")
    l_h_actual = None
    if x_ac_h is not None and mac > 0 and S > 0:
        l_h_actual = max(0.1, x_ac_h - (x_lemac + 0.25 * mac))
        s_h = float(geom["horizontal_tail"].get("S_h", 0.0))
        vh = (s_h * l_h_actual) / (S * mac)
        delta_xn_tail_pct = (eta_h_eff * vh * (a_h / a_w) * (1.0 - de_da)) * 100.0
        neutral_point_pct = x_ac_wbn_pct + delta_xn_tail_pct

    cg_span = cg_aft_limit - cg_forward_limit
    forward_ok, aft_ok = criterion(cg_forward_limit, cg_aft_limit)
    # BIPOL_3, pkt 7: wszystkie stany, także samolot pusty, stoją na kołach, nie na ogonie ani nosie.
    gear_limits = sorted((x_arms["gear"], x_arms["gear_aux"]))
    ground_cgs = [state["xcg_m"] for state in loading_states]
    ground_check = {
        "required": "Rzut ŚC między kołami podwozia we wszystkich stanach, także dla samolotu pustego",
        "source": "BIPOL_3.pdf (T. Grabowski, C. Galiński), analiza masowa, pkt 7",
        "x_front_m": gear_limits[0], "x_rear_m": gear_limits[1],
        "x_cg_min_m": min(ground_cgs), "x_cg_max_m": max(ground_cgs),
        "passed": gear_limits[0] < min(ground_cgs) and max(ground_cgs) < gear_limits[1],
    }
    cg_check = {
        "required": "25–35% ŚDA w locie; przednie przed 25% dopuszczalne przy zakresie > 10% ŚDA",
        "source": "BIPOL_3.pdf (T. Grabowski, C. Galiński), analiza masowa, pkt 7–8",
        "forward_ok": forward_ok,
        "aft_ok": aft_ok,
        "passed": forward_ok and aft_ok,
        "wing_shift_m": x_lemac - x_lemac_initial,
        "note": ("Położenie skrzydła dobrano do kryterium BIPOL_3." if abs(x_lemac - x_lemac_initial) > 1e-3 else
                 "Wstępne położenie skrzydła spełnia kryterium BIPOL_3.")
                if forward_ok and aft_ok else
                "Kryterium niespełnione w dopuszczalnym zakresie położenia skrzydła; zmień rozmieszczenie mas.",
    }

    neutral_point_m = x_lemac + (neutral_point_pct / 100.0) * mac
    
    # Zapas stateczności statycznej (Static Margin K_n = (x_N - x_CG)/MAC)
    static_margin_forward = neutral_point_pct - cg_forward_limit
    static_margin_aft = neutral_point_pct - cg_aft_limit
    
    is_stable = static_margin_aft >= MIN_STATIC_MARGIN_PCT
    # Apply the same unrounded criteria to every displayed state. Empty aircraft
    # is a ground configuration, so flight criteria do not apply to that row.
    for loading_state in loading_states:
        in_flight = loading_state['key'] != 'oew'
        cg = loading_state['xcg_mac_pct']
        margin = neutral_point_pct - cg
        loading_state.update(
            in_flight=in_flight,
            static_margin_pct=margin if in_flight else None,
            minimum_margin_passed=margin >= MIN_STATIC_MARGIN_PCT if in_flight else None,
            cg_criterion_passed=((cg >= 25.0 or cg_span > 10.0) and cg <= 35.0) if in_flight else None,
        )
    # X-plot: tail volume that places x_N one minimum margin behind the aft centre of gravity.
    vh_for_min_margin = (cg_aft_limit + MIN_STATIC_MARGIN_PCT + .2 - x_ac_wbn_pct) / (
        eta_h_eff * (a_h / a_w) * (1.0 - de_da) * 100.0)

    return {
        "x_le_wing_m": x_le_wing,
        "x_lemac_m": x_lemac,
        "arms": x_arms,
        "loading_states": loading_states,
        "pilot_variants": pilot_variants,
        "cg_range": {
            "forward_pct": cg_forward_limit,
            "aft_pct": cg_aft_limit,
            "delta_pct": cg_span,
            "basis": "stany w locie (bez samolotu pustego), z lekkim i ciężkim pilotem"
        },
        "cg_check": cg_check,
        "ground_check": ground_check,
        "neutral_point": {
            "x_n_m": neutral_point_m,
            "x_n_mac_pct": neutral_point_pct,
            # Unrounded terms of x_N = x_ac,wbn + eta_H V_H (a_H/a_w)(1 - d eps/d alpha), for reports.
            "terms": {"a_w": a_w, "a_h": a_h, "de_da": de_da, "eta_h": eta_h_eff,
                      "delta_xac_fus": delta_xac_fus, "delta_xac_prop": delta_xac_prop,
                      "x_ac_wbn_pct": x_ac_wbn_pct, "v_h": vh, "l_h": l_h_actual, "x_ac_h": x_ac_h,
                      "delta_xn_tail_pct": delta_xn_tail_pct, "ar_h": ar_h},
        },
        "wing_placement": {"x_fus": x_fus, "x_tail": x_tail, "x_sys": x_sys, "target_oew_mac": target_oew_mac,
                           "moment_fuselage_group": mom_fus_fixed, "moment_wing_offset": mom_wing_offset,
                           "m_wing_group": m_wing_group, "x_lemac_raw": x_lemac_raw, "x_lemac_initial": x_lemac_initial,
                           "x_lemac_bounds": list(x_lemac_bounds), "fuel_reserve_kg": m_fuel_res},
        "stability": {
            "static_margin_forward_pct": static_margin_forward,
            "static_margin_aft_pct": static_margin_aft,
            "is_stable": is_stable,
            "vh_for_min_margin": vh_for_min_margin,
            "evaluation": "Spełnione kryterium minimalnego zapasu stateczności 5% ŚDA" if is_stable else "Uwaga: mały zapas stateczności w tylnym położeniu ŚM!"
        }
    }


def calculate_balance_envelope(params: dict) -> dict:
    """
    Calculates comprehensive longitudinal mass distribution, CG travel envelope across
    6 discrete canonical loading cases, neutral point, static margin, and recommended wing shift.
    Traceable strictly to MEiL PW BIPOL I Wykład 7 and okBIPOL_1_handout_7.pdf.

    Parameters
    ----------
    params : dict
        Airframe parameters, masses, geometry:
        - m0 / mtow_kg: Gross takeoff weight [kg]
        - m_empty: Operating empty weight [kg]
        - m_fuel: Mission fuel mass [kg]
        - m_payload: Payload mass [kg]
        - m_crew: Crew mass [kg]
        - n_crew: Crew member count (default 1)
        - n_pax: Passenger count (default 0)
        - m_bag: Baggage mass [kg]
        - m_cargo: Dedicated cargo mass [kg]
        - breakdown: dict of component masses (m_wing, m_fuselage, m_tail, m_gear, m_propulsion, m_systems)
        - geometry / geom: dict of wing, fuselage, horizontal_tail, gear
        - engine_location: 'nose', 'wing', 'rear'
        - engine_type: 'prop', 'jet', 'none'
        - aircraft_type: str
        - wing_shift_user_m: float (manual override if specified)

    Returns
    -------
    dict
        Conformance to Milestone 2 interface contracts.
    """
    # 1. Parameter extraction & normalization
    geom = params.get("geometry") or params.get("geom") or {}
    fuselage = geom.get("fuselage") if isinstance(geom.get("fuselage"), dict) else {}
    wing = geom.get("wing") if isinstance(geom.get("wing"), dict) else {}
    htail = geom.get("horizontal_tail") if isinstance(geom.get("horizontal_tail"), dict) else {}
    gear_geom = geom.get("gear") if isinstance(geom.get("gear"), dict) else {}

    l_f = float(params.get("fuselage_length_m") or params.get("fuselage_len") or fuselage.get("length") or 8.0)
    d_f = float(params.get("fuselage_diameter_m") or params.get("fuselage_diam") or fuselage.get("diameter") or (0.15 * l_f))
    S = float(params.get("wing_area_m2") or params.get("S") or wing.get("S") or 15.0)
    b = float(params.get("wingspan_m") or params.get("b") or wing.get("b") or 10.0)
    AR = float(params.get("aspect_ratio") or params.get("AR") or wing.get("AR") or ((b ** 2) / max(0.1, S)))
    mac = float(params.get("mac_m") or params.get("mac") or wing.get("mac") or (S / max(0.1, b)))

    m_sizing = params.get("m_sizing") or params
    m0 = float(params.get("m0") or params.get("mtow_kg") or m_sizing.get("m0") or 1100.0)
    m_empty = float(params.get("m_empty") or m_sizing.get("m_empty") or (0.62 * m0))
    m_fuel = float(params.get("m_fuel") or m_sizing.get("m_fuel") or (0.18 * m0))
    m_payload = float(params.get("m_payload") or m_sizing.get("m_payload") or max(0.0, m0 - m_empty - m_fuel))
    n_crew = int(params.get("n_crew") or m_sizing.get("n_crew") or 1)
    m_crew_person = float(params.get("m_crew_person", 85.0) or 85.0)
    crew_ref_mass = float(params.get("m_crew") or m_sizing.get("m_crew") or (0.085 * m0 if "m_crew" not in params and m0 > 2500.0 else n_crew * m_crew_person))
    pilot_light = crew_ref_mass * (55.0 / 85.0)
    pilot_heavy = crew_ref_mass * (110.0 / 85.0)

    n_pax = int(params.get("n_pax", max(0, int(round((m_payload - 20.0) / 80.0))) if m_payload > 80.0 else 0))
    m_bag_nom = float(params.get("m_bag", 18.14 * n_pax if n_pax else 0.20 * m_payload))
    m_pax_nom = float(params.get("m_pax_total", n_pax * 80.0 if n_pax else 0.80 * m_payload))
    m_cargo = float(params.get("m_cargo", 0.0))

    # Component mass breakdown
    raw_bd = params.get("breakdown") or m_sizing.get("breakdown")
    if not raw_bd:
        try:
            from calculations.mass import estimate_component_masses
            bd_res = estimate_component_masses(m0, params, geom=geom)
            raw_bd = bd_res.get("breakdown")
        except Exception:
            raw_bd = None

    if raw_bd:
        m_w = float(raw_bd.get("m_wing") or raw_bd.get("wing") or (0.12 * m0))
        m_f = float(raw_bd.get("m_fuselage") or raw_bd.get("fuselage") or (0.13 * m0))
        m_ht = float(raw_bd.get("m_htail") or raw_bd.get("horizontal_tail") or 0.0)
        m_vt = float(raw_bd.get("m_vtail") or raw_bd.get("vertical_tail") or 0.0)
        m_t = float(raw_bd.get("m_tail") or raw_bd.get("tail") or (m_ht + m_vt) or (0.03 * m0))
        m_g = float(raw_bd.get("m_gear") or raw_bd.get("landing_gear") or raw_bd.get("gear") or (0.045 * m0))
        m_p = float(raw_bd.get("m_propulsion") or raw_bd.get("propulsion") or (0.17 * m0))
        m_s = float(raw_bd.get("m_systems") or raw_bd.get("systems") or (0.08 * m0))
        bd = {
            "m_wing": m_w,
            "m_fuselage": m_f,
            "m_tail": m_t,
            "m_gear": m_g,
            "m_propulsion": m_p,
            "m_systems": m_s,
        }
    else:
        bd = {
            "m_wing": 0.12 * m0,
            "m_fuselage": 0.13 * m0,
            "m_tail": 0.03 * m0,
            "m_gear": 0.045 * m0,
            "m_propulsion": 0.17 * m0,
            "m_systems": 0.08 * m0,
        }
    # Ensure sum of empty structure equals m_empty exactly
    empty_comp_sum = sum(bd.values())
    if empty_comp_sum > 0:
        f_norm = m_empty / empty_comp_sum
        bd = {k: v * f_norm for k, v in bd.items()}

    engine_loc = params.get("engine_location", "nose")
    engine_type = params.get("engine_type", "prop")

    # 2. Aerodynamic Neutral Point (Stick-fixed, Wyklad 7 & 10)
    vh = float(htail.get("vh_coeff") or params.get("v_h", 0.70))
    ar_h = float(htail.get("AR_h") or params.get("ar_h", 4.0))
    a_w = (2.0 * math.pi * AR) / (AR + 2.0)
    a_h = (2.0 * math.pi * ar_h) / (ar_h + 2.0)
    de_da = min(0.55, (2.0 * a_w) / (math.pi * AR))
    eta_h_eff = 0.72

    delta_xac_fus = min(0.11, max(0.055, (0.35 * (d_f ** 2) * l_f) / max(0.1, S * mac * a_w)))
    if engine_type == "none":
        delta_xac_prop = 0.0
    elif engine_type == "jet":
        delta_xac_prop = 0.015 if engine_loc == "wing" else 0.008
    else:
        delta_xac_prop = 0.030 if engine_loc in ["nose", "wing"] else 0.010

    x_ac_wbn_pct = (0.25 - delta_xac_fus - delta_xac_prop) * 100.0
    delta_xn_tail_pct = (eta_h_eff * vh * (a_h / a_w) * (1.0 - de_da)) * 100.0
    neutral_point_pct = x_ac_wbn_pct + delta_xn_tail_pct

    # 3. Component Stations & Loading Cases Evaluation Subroutine
    x_fus = 0.44 * l_f
    x_tail = 0.91 * l_f
    x_sys = 0.40 * l_f
    x_prop = 0.10 * l_f if engine_loc == "nose" else (0.76 * l_f if engine_loc == "rear" else None)

    def evaluate_layout_envelope(x_le):
        # Component longitudinal arms
        x_p = x_prop if x_prop is not None else (x_le - 0.15 * mac)
        arms = {
            "wing": x_le + 0.38 * mac,
            "fuselage": x_fus,
            "htail": x_tail,
            "vtail": x_tail,
            "gear_main": x_le + 0.45 * mac,
            "gear_nose": 0.12 * l_f,
            "propulsion": x_p,
            "systems": x_sys,
            "crew": x_le - 0.18 * mac,
            "pax_front": x_le + 0.12 * mac,
            "pax_rear": x_le + 0.48 * mac,
            "baggage": x_le + 0.75 * mac,
            "fuel": x_le + 0.32 * mac,
        }
        pax_centroid_arm = 0.45 * arms["pax_front"] + 0.55 * arms["pax_rear"]

        # 11 component items for empty airframe
        # 1: wing, 2: fuselage, 3: htail, 4: vtail, 5: gear_main, 6: gear_nose, 7: propulsion, 8: systems
        comp_empty = [
            ("1. Skrzydło (struktura płata)", bd["m_wing"], arms["wing"], 0.0, 0.15),
            ("2. Kadłub (struktura kadłuba)", bd["m_fuselage"], arms["fuselage"], 0.0, 0.0),
            ("3. Usterzenie poziome", bd["m_tail"] * 0.65, arms["htail"], 0.0, 0.35),
            ("4. Usterzenie pionowe", bd["m_tail"] * 0.35, arms["vtail"], 0.0, 0.75),
            ("5. Podwozie główne", bd["m_gear"] * GEAR_MAIN_SHARE, arms["gear_main"], 0.0, -0.85),
            ("6. Podwozie przednie", bd["m_gear"] * (1.0 - GEAR_MAIN_SHARE), arms["gear_nose"], 0.0, -0.80),
            ("7. Zespół napędowy", bd["m_propulsion"], arms["propulsion"], 0.0, 0.05),
            ("8. Instalacje i awionika", bd["m_systems"], arms["systems"], 0.0, 0.0),
        ]

        def build_case_record(key, name, m_cr, m_px, m_bg, m_fl, in_fl=True):
            items = list(comp_empty)
            # Item 9: Pilot & crew
            items.append(("9. Załoga (pilot)", m_cr, arms["crew"], 0.0, 0.10))
            # Item 10: Passengers & baggage
            # Split into pax and bag moments
            pax_bag_mass = m_px + m_bg
            pax_bag_arm = ((m_px * pax_centroid_arm + m_bg * arms["baggage"]) / max(1e-4, pax_bag_mass)) if pax_bag_mass > 0 else pax_centroid_arm
            items.append(("10. Pasażerowie i ładunek", pax_bag_mass, pax_bag_arm, 0.0, 0.0))
            # Item 11: Fuel
            items.append(("11. Paliwo", m_fl, arms["fuel"], 0.0, 0.15))

            # Machine-precision mass and moment summation
            total_mass = sum(it[1] for it in items)
            total_moment = sum(it[1] * it[2] for it in items)
            x_cg = total_moment / max(1.0, total_mass)
            cg_mac = ((x_cg - x_le) / mac) * 100.0

            station_list = [
                {
                    "item": it[0],
                    "mass_kg": round(it[1], 3),
                    "x_m": round(it[2], 3),
                    "y_m": round(it[3], 3),
                    "z_m": round(it[4], 3),
                    "moment_kg_m": round(it[1] * it[2], 3),
                }
                for it in items
            ]

            return {
                "key": key,
                "name": name,
                "mass_kg": round(total_mass, 2),
                "xcg_m": round(x_cg, 4),
                "xcg_mac_pct": round(cg_mac, 2),
                "moment_kg_m": round(total_moment, 2),
                "in_flight": in_fl,
                "_raw_cg": cg_mac,
                "_raw_xcg": x_cg,
                "stations": station_list,
            }

        cases = {}
        # Case 1: Operating Empty Weight (OEW)
        cases["case1_oew"] = build_case_record("case1_oew", "Case 1: Operating Empty Weight (OEW)",
                                               0.0, 0.0, 0.0, 0.0, in_fl=False)

        # Case 2a: OEW + Pilot Light (55 kg)
        cases["case2_pilot_light"] = build_case_record("case2_pilot_light", "Case 2a: OEW + Pilot Light (55 kg)",
                                                       pilot_light, 0.0, 0.0, 0.5 * m_fuel, in_fl=True)

        # Case 2b: OEW + Pilot Heavy (110 kg) + Reserve Fuel -> yields critical forward CG limit (BIPOL_3)
        cases["case2_pilot_heavy"] = build_case_record("case2_pilot_heavy", "Case 2b: OEW + Pilot Heavy (110 kg)",
                                                       pilot_heavy, 0.0, 0.0, 0.20 * m_fuel, in_fl=True)

        # Case 3: Full Passengers + Minimal Baggage
        m_bag_min = min(m_bag_nom, 0.10 * m_payload) if m_payload > 0 else 5.0
        m_pax_case3 = max(0.0, m_payload - m_bag_min)
        cases["case3_full_pax_min_bag"] = build_case_record("case3_full_pax_min_bag", "Case 3: Full Pax + Min Bag",
                                                            crew_ref_mass, m_pax_case3, m_bag_min, 0.8 * m_fuel, in_fl=True)

        # Case 4: Full Baggage + Minimal Passengers (0 pax) -> yields critical aft CG limit (BIPOL_3)
        cases["case4_full_bag_min_pax"] = build_case_record("case4_full_bag_min_pax", "Case 4: Full Bag + Min Pax",
                                                            crew_ref_mass, 0.0, m_payload, 0.90 * m_fuel, in_fl=True)

        # Case 5: Zero Fuel Weight (ZFW)
        m_pax_zfw = min(m_pax_nom, max(0.0, m_payload - m_bag_nom))
        m_bag_zfw = max(0.0, m_payload - m_pax_zfw)
        cases["case5_zfw"] = build_case_record("case5_zfw", "Case 5: Zero Fuel Weight (ZFW)",
                                               crew_ref_mass, m_pax_zfw, m_bag_zfw, 0.0, in_fl=True)

        # Case 6: Maximum Takeoff Weight (MTOW)
        cases["case6_mtow"] = build_case_record("case6_mtow", "Case 6: Maximum Takeoff Weight (MTOW)",
                                                crew_ref_mass, m_pax_zfw, m_bag_zfw, m_fuel, in_fl=True)

        flight_cgs = [v["_raw_cg"] for k, v in cases.items() if v["in_flight"]]
        cg_fwd_val = min(flight_cgs)
        cg_aft_val = max(flight_cgs)
        return arms, cases, cg_fwd_val, cg_aft_val

    # 4. Initial Wing Placement Guess & Bisection Optimization
    target_oew_mac = 0.25
    m_wing_group = bd["m_wing"] + bd["m_gear"] + (bd["m_propulsion"] if engine_loc == "wing" else 0.0)
    denom = max(1.0, m_empty - m_wing_group)
    mom_fixed = (bd["m_fuselage"] * x_fus + bd["m_tail"] * x_tail + bd["m_systems"] * x_sys +
                 (bd["m_propulsion"] * x_prop if x_prop else 0.0))
    mom_wing_off = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45) * mac
    x_lemac_init = max(0.20 * l_f, min(0.56 * l_f, (mom_fixed + mom_wing_off - target_oew_mac * mac * m_empty) / denom))

    x_lemac = x_lemac_init
    arms, cases, cg_fwd, cg_aft = evaluate_layout_envelope(x_lemac)
    aft_target = min(35.0, neutral_point_pct - 5.0)

    # Check criteria: fwd >= 25.0 (or span > 10.0), aft <= 35.0, static margin >= 5.0%
    criterion_met = (cg_fwd >= 25.0 or (cg_aft - cg_fwd) > 10.0) and (cg_aft <= 35.0) and (neutral_point_pct - cg_aft >= 5.0)

    if not criterion_met:
        # Bisection over [0.20 * l_f, 0.56 * l_f] to center the CG
        low, high = 0.20 * l_f, 0.56 * l_f
        for _ in range(40):
            mid = 0.5 * (low + high)
            _, _, fwd_m, aft_m = evaluate_layout_envelope(mid)
            err = (aft_m - aft_target) if (aft_m - fwd_m > 10.0) else (fwd_m - 25.0)
            if err > 0:
                low = mid
            else:
                high = mid
        x_lemac = 0.5 * (low + high)
        arms, cases, cg_fwd, cg_aft = evaluate_layout_envelope(x_lemac)

    wing_shift_m = x_lemac - x_lemac_init
    neutral_point_m = x_lemac + (neutral_point_pct / 100.0) * mac
    kn_min = (neutral_point_pct - cg_aft) / 100.0
    kn_max = (neutral_point_pct - cg_fwd) / 100.0

    # 5. Landing Gear Turnover Stability Triangle
    track_m = float(gear_geom.get("track") or params.get("track_m") or (0.24 * b))
    wheelbase_m = float(gear_geom.get("wheelbase") or params.get("wheelbase_m") or max(0.8, arms["gear_main"] - arms["gear_nose"]))
    zcg_mtow = 0.05
    h_cg_m = max(0.40, zcg_mtow - (-0.85))
    xcg_mtow_m = cases["case6_mtow"]["xcg_m"]
    dn_m = ((xcg_mtow_m - arms["gear_nose"]) * (track_m / 2.0)) / math.sqrt(wheelbase_m ** 2 + (track_m / 2.0) ** 2)
    turnover_angle_deg = round(math.degrees(math.atan2(h_cg_m, max(1e-4, dn_m))), 1)

    dx_main_aft = arms["gear_main"] - cases["case4_full_bag_min_pax"]["xcg_m"]
    main_gear_cg_angle_deg = round(math.degrees(math.atan2(dx_main_aft, h_cg_m)), 1)
    tailstrike_deg = round(math.degrees(math.atan2(0.85, max(0.1, 0.91 * l_f - arms["gear_main"]))), 1)

    cg_within_target = (cg_fwd >= 25.0 or (cg_aft - cg_fwd) > 10.0) and (cg_aft <= 35.0)

    # Clean up internal temporary keys from case dicts
    for c in cases.values():
        c.pop("_raw_cg", None)
        c.pop("_raw_xcg", None)

    return {
        "cg_positions": cases,
        "cg_fwd": round(cg_fwd, 2),
        "cg_aft": round(cg_aft, 2),
        "cg_fwd_m": round(x_lemac + (cg_fwd / 100.0) * mac, 3),
        "cg_aft_m": round(x_lemac + (cg_aft / 100.0) * mac, 3),
        "cg_travel_span_pct": round(cg_aft - cg_fwd, 2),
        "x_np": round(neutral_point_m, 3),
        "x_np_mac_pct": round(neutral_point_pct, 2),
        "kn_min": round(kn_min, 4),
        "kn_max": round(kn_max, 4),
        "static_margin_aft_pct": round(kn_min * 100.0, 2),
        "static_margin_fwd_pct": round(kn_max * 100.0, 2),
        "is_stable": kn_min >= 0.05,
        "wing_shift_recommendation_m": round(wing_shift_m, 3),
        "optimal_x_lemac_m": round(x_lemac, 3),
        "target_cg_window": {"fwd_pct": 25.0, "aft_pct": 35.0},
        "cg_within_target": cg_within_target,
        "component_stations": cases["case6_mtow"]["stations"],
        "turnover_stability": {
            "track_m": round(track_m, 2),
            "wheelbase_m": round(wheelbase_m, 2),
            "dn_m": round(dn_m, 3),
            "h_cg_m": round(h_cg_m, 2),
            "turnover_angle_deg": turnover_angle_deg,
            "turnover_compliant": turnover_angle_deg < 60.0,
            "main_gear_cg_angle_deg": main_gear_cg_angle_deg,
            "main_gear_compliant": 13.0 <= main_gear_cg_angle_deg <= 16.0,
            "tailstrike_clearance_deg": tailstrike_deg,
            "tailstrike_compliant": tailstrike_deg >= 10.0,
        },
    }

