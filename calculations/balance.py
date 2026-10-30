"""
Moduł wyważenia samolotu i stateczności statycznej podłużnej (BIPOL I)
Wyznaczanie położenia środka masy w różnych konfiguracjach załadowania,
przeliczenie na % ŚDA (MAC), wyznaczenie punktu neutralnego oraz zapasu stateczności.
"""
import math
from calculations.flight_model import mission_masses

MIN_STATIC_MARGIN_PCT = 5.0
# Upper end of usual horizontal tail volumes (Raymer, tab. 6.4: up to 1.0 for transports).
MAX_TAIL_VOLUME = 1.2


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

    if engine_loc == "nose":
        x_prop_fixed = 0.10 * l_f
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45) * mac
    elif engine_loc == "rear":
        x_prop_fixed = 0.76 * l_f
        target_oew_mac = 0.27
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45) * mac
    else: # wing
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"] + bd["m_propulsion"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45 - bd["m_propulsion"] * 0.15) * mac

    denom_m = max(1.0, m_empty - m_wing_group)
    x_lemac_raw = (mom_fus_fixed + mom_wing_offset - target_oew_mac * mac * m_empty) / denom_m
    # Light tractor aircraft carry the wing leading edge from about a quarter of the fuselage length.
    x_lemac_bounds = (0.25 * l_f, 0.56 * l_f)
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
            "fuselage": round(x_fus, 2),
            "wing": round(x_lemac + 0.38 * mac, 2),
            "tail": round(x_tail, 2),
            "propulsion": round(x_prop, 2),
            "gear": round(x_lemac + 0.45 * mac, 2),
            "systems": round(x_sys, 2),
            "crew": round(x_lemac - 0.18 * mac, 2),
            "pax_front": round(x_lemac + 0.12 * mac, 2),
            "pax_rear": round(x_lemac + 0.48 * mac, 2),
            "baggage": round(x_lemac + 0.75 * mac, 2),
            "fuel": round(x_lemac + 0.32 * mac, 2)
        }

        # 1. Moment masy pustej (OEW)
        mom_empty = (
            bd["m_fuselage"] * x_arms["fuselage"] +
            bd["m_wing"] * x_arms["wing"] +
            bd["m_tail"] * x_arms["tail"] +
            bd["m_propulsion"] * x_arms["propulsion"] +
            bd["m_gear"] * x_arms["gear"] +
            bd["m_systems"] * x_arms["systems"]
        )

        if unmanned:
            # UAV: wyposażenie zadaniowe (głowica optoelektroniczna w dziobie/pod kadłubem + awionika misji w okolicy ŚM)
            x_arms["payload_sensor"] = round(x_lemac - 0.35 * mac, 2)
            x_arms["payload_bay"] = round(x_lemac + 0.20 * mac, 2)
            mom_payload = (m_payload * 0.60) * x_arms["payload_sensor"] + (m_payload * 0.40) * x_arms["payload_bay"]
        else:
            m_pax = int(params.get('n_pax', 0)) * (float(params.get('m_pax', 115)) + float(params.get('m_bag', 0)))
            cargo = float(params.get('m_cargo', 0))
            mom_payload = m_pax * (.45 * x_arms['pax_front'] + .55 * x_arms['pax_rear']) + cargo * x_arms['baggage']
        x_arms['payload_equivalent'] = mom_payload / m_payload if m_payload else x_arms['pax_front']

        # Funkcja pomocnicza: przeliczenie na % ŚDA (MAC)
        def to_percent_mac(x):
            return round(((x - x_lemac) / mac) * 100.0, 1)

        def state(key, name, crew=0.0, payload=False, fuel=0.0, released=0.0):
            """Stan załadowania złożony z masy pustej, załogi, ładunku i paliwa (BIPOL_3, wzór 3.1)."""
            mass = m_empty + crew + (m_payload if payload else 0.0) + fuel - released
            drop_arm = x_arms['payload_equivalent'] if unmanned else x_arms['baggage']
            mom = mom_empty + crew * x_arms["crew"] + (mom_payload if payload else 0.0) + fuel * x_arms["fuel"] - released*drop_arm
            x_cg = mom / max(1.0, mass)
            return {"key": key, "name": name, "mass_kg": round(mass, 1), "xcg_m": round(x_cg, 3),
                    "xcg_mac_pct": to_percent_mac(x_cg), "_payload": payload, "_fuel": fuel, "_released":released}

        # Warianty wg BIPOL_3: MTOW, lądowanie, start i lądowanie bez ładunku płatnego, samolot pusty.
        # MTOW pozostaje ostatni (odczytują go widoki rysunku).
        states = [state("oew", "Masa pusta (OEW)")]
        if not unmanned:
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
                states.append(state("tow_no_payload", "Start bez ładunku płatnego", crew=m_crew, fuel=m_fuel))
            states.append(state("mlw_no_payload", "Lądowanie bez ładunku płatnego", crew=m_crew, fuel=m_fuel_res))
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
    neutral_point_pct = round(x_ac_wbn_pct + delta_xn_tail_pct, 1)

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
            # Both ends lie on the boundary; keep the one that satisfies the criterion after rounding.
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
        neutral_point_pct = round(x_ac_wbn_pct + delta_xn_tail_pct, 1)

    cg_span = round(cg_aft_limit - cg_forward_limit, 1)
    forward_ok, aft_ok = criterion(cg_forward_limit, cg_aft_limit)
    cg_check = {
        "required": "25–35% ŚDA w locie; przednie przed 25% dopuszczalne przy zakresie > 10% ŚDA",
        "source": "BIPOL_3.pdf (T. Grabowski, C. Galiński), analiza masowa, pkt 7–8",
        "forward_ok": forward_ok,
        "aft_ok": aft_ok,
        "passed": forward_ok and aft_ok,
        "wing_shift_m": round(x_lemac - x_lemac_initial, 3),
        "note": ("Położenie skrzydła dobrano do kryterium BIPOL_3." if abs(x_lemac - x_lemac_initial) > 1e-3 else
                 "Wstępne położenie skrzydła spełnia kryterium BIPOL_3.")
                if forward_ok and aft_ok else
                "Kryterium niespełnione w dopuszczalnym zakresie położenia skrzydła; zmień rozmieszczenie mas.",
    }

    neutral_point_m = round(x_lemac + (neutral_point_pct / 100.0) * mac, 3)
    
    # Zapas stateczności statycznej (Static Margin K_n = (x_N - x_CG)/MAC)
    static_margin_forward = round(neutral_point_pct - cg_forward_limit, 1)
    static_margin_aft = round(neutral_point_pct - cg_aft_limit, 1)
    
    is_stable = static_margin_aft >= MIN_STATIC_MARGIN_PCT
    # X-plot: tail volume that places x_N one minimum margin behind the aft centre of gravity.
    vh_for_min_margin = (cg_aft_limit + MIN_STATIC_MARGIN_PCT + .2 - x_ac_wbn_pct) / (
        eta_h_eff * (a_h / a_w) * (1.0 - de_da) * 100.0)

    return {
        "x_le_wing_m": round(x_le_wing, 3),
        "x_lemac_m": round(x_lemac, 3),
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
            "evaluation": "Stateczny statycznie (zapas 5-20% ŚDA)" if is_stable else "Uwaga: mały zapas stateczności w tylnym położeniu ŚM!"
        }
    }
