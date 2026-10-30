"""
Moduł wyboru obciążenia powierzchni skrzydła (W/S) i obciążenia ciągu (T/W) lub mocy (P/W)
Wykres doboru wg BIPOL_2.pdf (C. Galiński, „Studium wykonalności”), wzory (1)–(12):
start na 15 m, lądowanie, wznoszenie, prędkość minimalna, przelot i największy zasięg.
"""
import math
from calculations.flight_model import propulsion_lapse, mission_masses
from calculations.atmosphere import isa_atmosphere, G0, RHO0

SIGMA_AIRFIELD = 1.0  # BIPOL_2: lotnisko na poziomie morza (σ = 1)
CZ_SAFETY = 1.1       # BIPOL_2 (10): przy prędkości minimalnej 1,1·Cz = Cz,max
MU_GROUND = 0.04      # tarcie kół, tylko w zastępczym ograniczeniu rozbiegu


def takeoff_mean_speed(ws, cz_max_to):
    """Mean ground-roll speed V_LOF/sqrt(2), V_LOF = 1.12 V_S,TO.

    Propeller thrust is converted to power at this speed, as in
    runway.takeoff_distance(); converting at V_LOF overstates power by sqrt(2).
    """
    return 1.12 * math.sqrt(max(1.0, 2.0 * ws / (RHO0 * cz_max_to))) / math.sqrt(2.0)


def takeoff_tw(ws, cz_max_to, s_to, sigma=SIGMA_AIRFIELD):
    """BIPOL_2 eq. (2): T/W for a take-off distance to 15 m s_to [m] at W/S [N/m²].

    Metric form of s = 20.9·TOP + 87·sqrt(TOP·T/W) [ft, lb/ft²]. None where the
    distance cannot be reached at this W/S whatever the thrust.
    """
    top = ws / (cz_max_to * sigma)
    margin = s_to - 3.834 * math.sqrt(top)
    return 0.133 * top / margin if margin > 0 else None


def landing_ws(cz_max_lnd, s_l, sigma=SIGMA_AIRFIELD):
    """BIPOL_2 eq. (3): highest W/S [N/m²] at landing weight for a landing distance from 15 m s_l [m]."""
    return sigma * cz_max_lnd * (s_l - 122.0) / 0.75


def climb_tw(ws, q, cx0, k_ind, gradient):
    """BIPOL_2 eq. (9): T/W giving climb gradient G = w/V at dynamic pressure q."""
    return q * cx0 / ws + ws * k_ind / q + gradient


def calculate_matching_chart(params: dict, m0: float = None, mass: dict = None):
    """
    Parametry wejściowe:
      - engine_type: 'jet' lub 'prop'
      - v_stall_kmh: wymagana prędkość minimalna VS0 [km/h]
      - takeoff_distance_m: długość startu na 15 m [m] (BIPOL_2 wzór 2)
      - takeoff_run_m: rozbieg [m], używany tylko bez długości startu na 15 m
      - landing_distance_m: długość lądowania z 15 m [m] (BIPOL_2 wzór 3)
      - climb_rate_ms: wymagana prędkość wznoszenia przy ziemi [m/s]
      - cruise_speed_kmh, cruise_altitude_m: przelot
      - aspect_ratio, oswald_e, cx0: biegunowa analityczna Cx = Cx0 + Cz²/(πAe)
      - cz_max_to, cz_max_lnd: Cz,max do startu i do lądowania
      - prop_efficiency, prop_eff_to: sprawność śmigła w locie i na rozbiegu
    mass: wynik bilansu masy (P1/P2); daje masę do lądowania i w połowie przelotu.
    """
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = "none" if ac_type == "glider" else params.get("engine_type", "prop")
    v_min_ms = float(params.get("v_stall_kmh", 100.0)) / 3.6

    s_to = float(params.get("takeoff_distance_m") or 0.0)
    s_run = float(params.get("takeoff_run_m", 500.0))
    s_l = float(params.get("landing_distance_m") or 0.0)
    water = params.get('operating_surface') == 'water'
    if water:
        s_to = s_l = 0.0
    wy_req = float(params.get("climb_rate_ms", 5.0))

    v_cr_kmh = float(params.get("cruise_speed_kmh", 240.0))
    v_cr_ms = v_cr_kmh / 3.6
    h_cr = float(params.get("cruise_altitude_m", 3000.0))

    AR = float(params.get("aspect_ratio", 8.0))
    e = float(params.get("oswald_e", 0.80))
    cx0_base = float(params.get("cx0", 0.025))
    wing_config = params.get("wing_config", "low")
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")

    cx0 = cx0_base
    if wing_config == "braced_high" and not params.get('preliminary_polar_includes_configuration'):
        cx0 += 0.0020
    if flap_type == "junkers" and not params.get('preliminary_polar_includes_configuration'):
        cx0 += 0.0025
    if slat_type == "fixed_slot" and not params.get('preliminary_polar_includes_configuration'):
        cx0 += 0.0030

    cz_max_to = float(params.get("cz_max_to", 1.8))
    cz_max_lnd = float(params.get("cz_max_lnd", 2.2))

    eta_p = float(params.get("prop_efficiency", 0.82))
    eta_to = float(params.get("prop_eff_to", 0.65))

    # Warunki atmosferyczne na przelocie
    isa_cr = isa_atmosphere(h_cr)
    rho_cr = isa_cr["rho"]
    sigma_cr = isa_cr["sigma"]
    k_ind = 1.0 / (math.pi * AR * e)

    # Ciężary z projektu 1: lądowanie (z rezerwą paliwa) i połowa przelotu (BIPOL_2, uwagi do (3) i (11)–(12))
    m_landing = m_mid_cruise = m0
    if m0 is not None and mass:
        fractions = mass.get("fuel_fractions_detail") or {}
        if fractions.get("total_mff") and fractions.get("landing"):
            m_landing = m0 * fractions["total_mff"] / fractions["landing"]
        m_mid_cruise = m0 - 0.5 * float(mass.get("m_fuel", 0.0))
        if 'warmup' in fractions:
            phases = mission_masses(mass)
            m_landing = phases['landing_start']
            m_mid_cruise = phases['cruise_mean']
    to_takeoff = (lambda ws, m: ws * m0 / m) if m0 else (lambda ws, m: ws)

    # 1. Prędkość minimalna (wzór 10): W/S ≤ q·Cz,max/1,1 — linia pionowa
    ws_min_speed = 0.5 * RHO0 * v_min_ms ** 2 * cz_max_lnd / CZ_SAFETY

    # 2. Lądowanie (wzory 3–5): W/S przy masie do lądowania przeliczone na masę startową
    ws_landing_l = ws_landing = None
    if s_l:
        if s_l <= 122.0:
            raise ValueError("Długość lądowania z 15 m musi przekraczać 122 m (wzór 3, BIPOL_2).")
        ws_landing_l = landing_ws(cz_max_lnd, s_l)
        ws_landing = to_takeoff(ws_landing_l, m_landing)

    ws_limit, limit_by = ws_min_speed, "prędkość minimalna"
    if ws_landing is not None and ws_landing < ws_limit:
        ws_limit, limit_by = ws_landing, "długość lądowania"

    fixed_area = float(params.get('wing_area_m2') or 0)
    if fixed_area and m0 is not None:
        ws_design, limit_by = float(m0) * G0 / fixed_area, "zadana powierzchnia skrzydła"
    else:
        ws_design = ws_limit

    # 3. Wznoszenie (wzory 6–9) przy V = Vmin + 0,25(Vmax − Vmin); Vmax przyjęto równą Vprzel
    v_climb_ms = v_min_ms + 0.25 * max(0.0, v_cr_ms - v_min_ms)
    q_climb = 0.5 * RHO0 * v_climb_ms ** 2
    gradient = wy_req / v_climb_ms
    tw_climb_min = gradient + 2.0 * math.sqrt(cx0 * k_ind)  # wzór 8 = G + 1/Kmax

    # 4. Największy zasięg (wzory 11–12) w połowie przelotu — linia pionowa (punkt „B”)
    q_cr = 0.5 * rho_cr * v_cr_ms ** 2
    ws_max_range = None
    if engine_type != "none":
        ws_range_cr = q_cr * math.sqrt(math.pi * AR * e * cx0 / (3.0 if engine_type == "jet" else 1.0))
        ws_max_range = to_takeoff(ws_range_cr, m_mid_cruise)

    # Siatka W/S obejmująca punkt projektowy i linie pionowe (zasięg tylko, gdy nie spłaszcza wykresu)
    shown = [ws_limit, ws_design, ws_min_speed] + [w for w in (ws_landing, ws_max_range)
                                                    if w is not None and w <= 2.5 * ws_limit]
    ws_min = min(200.0, 0.25 * ws_limit, 0.7 * ws_design)
    ws_max = max(800.0, 1.15 * max(shown))
    steps = 40
    ws_values = [ws_min + i * (ws_max - ws_min) / steps for i in range(steps + 1)]

    # 5. Optional mission requirements: maximum speed at sea level (racing, aerobatic) and
    #    climb with a glider in tow, which carries the glider's drag and climbs its weight too.
    v_max_req_ms = float(params.get("v_max_required_kmh") or 0.0) / 3.6
    q_vmax = 0.5 * RHO0 * v_max_req_ms ** 2
    m_glider = float(params.get("tow_glider_mass_kg") or 0.0) if engine_type == "prop" else 0.0
    v_tow_ms = float(params.get("tow_speed_kmh", 120.0)) / 3.6
    q_tow = 0.5 * RHO0 * v_tow_ms ** 2
    w_tow = float(params.get("tow_climb_rate_ms", 3.0))
    ld_glider = float(params.get("tow_glider_ld", 25.0))
    tow_ratio = m_glider / float(m0) if (m_glider and m0) else 0.0

    def extra_requirements(ws):
        """Vmax at sea level and climb in tow, in the units of the matching chart (None when not required)."""
        vmax = tow = None
        if v_max_req_ms and engine_type != "none":
            tw = climb_tw(ws, q_vmax, cx0, k_ind, 0.0) / max(1e-6, propulsion_lapse(params, 0.0, v_max_req_ms))
            vmax = tw if engine_type == "jet" else tw * v_max_req_ms / eta_p
        if tow_ratio:
            tw = climb_tw(ws, q_tow, cx0, k_ind, 0.0) + tow_ratio / ld_glider + (1.0 + tow_ratio) * w_tow / v_tow_ms
            tow = tw * v_tow_ms / eta_p
        return vmax, tow

    def requirements(ws):
        """T/W (jet) or P/W [W/N] (prop) for take-off, climb and cruise at one W/S."""
        if water:
            tw_to = 0.0  # excluded constraint, not a prediction of water take-off
        elif s_to:
            tw_to = takeoff_tw(ws, cz_max_to, s_to)
        else:  # zastępczo: rozbieg, gdy nie podano długości startu na 15 m
            tw_to = (1.21 * ws) / (G0 * RHO0 * cz_max_to * max(30.0, s_run)) + MU_GROUND
        tw_cl = climb_tw(ws, q_climb, cx0, k_ind, gradient)
        tw_cr_alt = climb_tw(ws, q_cr, cx0, k_ind, 0.0)  # wzór (61) BIPOL_1_wzory: T = D przy Vprzel
        if engine_type == "jet":
            return tw_to, tw_cl, tw_cr_alt / max(1e-6, propulsion_lapse(params, h_cr, v_cr_ms))
        return (None if tw_to is None else tw_to * takeoff_mean_speed(ws, cz_max_to) / eta_to,
                tw_cl * v_climb_ms / eta_p,
                tw_cr_alt * v_cr_ms / (eta_p * max(1e-6, propulsion_lapse(params, h_cr, v_cr_ms))))

    curve_takeoff, curve_climb, curve_cruise, curve_vmax, curve_tow = [], [], [], [], []
    for ws in ws_values:
        if engine_type == "none":
            values = (0.0, 0.0, 0.0, None, None)
        else:
            values = requirements(ws) + extra_requirements(ws)
        digits = 4 if engine_type == "jet" else 2
        for curve, value in zip((curve_takeoff, curve_climb, curve_cruise, curve_vmax, curve_tow), values):
            curve.append(None if value is None else round(value, digits))

    climb_min = None
    tw_design = pw_design = None
    governing = None
    at_design = {}
    if engine_type != "none":
        climb_min = tw_climb_min if engine_type == "jet" else tw_climb_min * v_climb_ms / eta_p
        at_design = dict(zip(("start", "wznoszenie", "przelot"), requirements(ws_design)))
        vmax_at_design, tow_at_design = extra_requirements(ws_design)
        if vmax_at_design is not None:
            at_design["prędkość maksymalna"] = vmax_at_design
        if tow_at_design is not None:
            at_design["holowanie szybowca"] = tow_at_design
        if at_design["start"] is None:
            raise ValueError(
                f"Zadana długość startu na 15 m ({s_to:g} m) jest za krótka przy W/S = {ws_design:.0f} N/m² "
                "(wzór 2, BIPOL_2). Zwiększ długość startu lub Cz,max do startu albo zmniejsz obciążenie powierzchni.")
        governing = max(at_design, key=at_design.get)
        if engine_type == "jet":
            tw_design = round(at_design[governing] * 1.06, 3)  # 6% margines projektowy
        else:
            pw_design = round(at_design[governing] * 1.08, 2)  # 8% margines projektowy

    w_newtons = (float(m0) * G0) if m0 is not None else None
    power_kw = round((pw_design * w_newtons) / 1000.0, 1) if (pw_design and w_newtons) else None
    power_hp = round((pw_design * w_newtons) / 735.5, 1) if (pw_design and w_newtons) else None
    thrust_kn = round((tw_design * w_newtons) / 1000.0, 2) if (tw_design and w_newtons) else None
    required_power_kw = power_kw
    if engine_type == 'prop' and 'engine_power_kw' in params.get('locked_params', []):
        power_kw = float(params['engine_power_kw'])
        power_hp = power_kw * 1000 / 735.5
        pw_design = power_kw * 1000 / w_newtons

    return {
        "engine_type": engine_type,
        # Unrounded: refine_takeoff_sizing() solves the take-off model on these points.
        "ws_values": ws_values,
        "ws_stall_max": round(ws_min_speed, 1),
        "ws_landing": round(ws_landing, 1) if ws_landing is not None else None,
        "ws_max_range": round(ws_max_range, 1) if ws_max_range is not None else None,
        "ws_limit": round(ws_limit, 1),
        "curve_takeoff": curve_takeoff,
        "curve_climb": curve_climb,
        "curve_cruise": curve_cruise,
        "curve_vmax": curve_vmax if v_max_req_ms and engine_type != "none" else None,
        "curve_tow": curve_tow if tow_ratio else None,
        "climb_min": round(climb_min, 4) if climb_min is not None else None,
        "takeoff_basis": "unmodelled_water" if water else "15m" if s_to else "ground_roll",
        # Unrounded intermediate values of the design point, shown step by step in reports.
        "terms": {
            "cx0": cx0, "cx0_base": cx0_base, "k_ind": k_ind, "aspect_ratio": AR, "oswald_e": e,
            "v_min_ms": v_min_ms, "ws_min_speed": ws_min_speed, "ws_landing_l": ws_landing_l,
            "ws_landing": ws_landing, "ws_limit": ws_limit, "m_landing": m_landing,
            "m_mid_cruise": m_mid_cruise, "v_climb_ms": v_climb_ms, "q_climb": q_climb,
            "gradient": gradient, "tw_climb_min": tw_climb_min, "v_cr_ms": v_cr_ms, "rho_cr": rho_cr,
            "q_cr": q_cr, "lapse_cr": propulsion_lapse(params, h_cr, v_cr_ms) if engine_type != "none" else None,
            "ws_max_range_cruise": ws_range_cr if ws_max_range is not None else None,
            "v_mean_to": takeoff_mean_speed(ws_design, cz_max_to), "eta_p": eta_p, "eta_to": eta_to,
            "s_to": s_to, "s_run": s_run, "s_l": s_l, "climb_rate_ms": wy_req,
            "cz_max_to": cz_max_to, "cz_max_lnd": cz_max_lnd,
            "at_design": at_design, "margin": 1.06 if engine_type == "jet" else 1.08,
            "v_max_required_ms": v_max_req_ms or None, "tow_glider_mass_kg": m_glider or None,
            "tow_speed_ms": v_tow_ms if m_glider else None, "tow_climb_rate_ms": w_tow if m_glider else None,
            "tow_glider_ld": ld_glider if m_glider else None,
        },
        "assumptions": {
            "source": "BIPOL_2.pdf (C. Galiński, Studium wykonalności), wzory (1)–(12)",
            "sigma": SIGMA_AIRFIELD,
            "cz_safety": CZ_SAFETY,
            "takeoff_distance_m": s_to or None,
            "takeoff_run_m": None if s_to else s_run,
            "landing_distance_m": s_l or None,
            "ws_landing_at_landing_mass": round(ws_landing_l, 1) if ws_landing_l is not None else None,
            "m_landing_kg": round(m_landing, 1) if m_landing is not None else None,
            "m_mid_cruise_kg": round(m_mid_cruise, 1) if m_mid_cruise is not None else None,
            "v_climb_kmh": round(v_climb_ms * 3.6, 1),
            "climb_gradient": round(gradient, 4),
            "v_max_kmh": v_cr_kmh,
            "note": "Vmax przyjęto równą prędkości przelotowej (brak osobnego wymagania). "
                    "Punkt projektowy leży na granicy W/S; linia największego zasięgu jest punktem odniesienia „B”.",
        },
        "design_point": {
            "ws": ws_design,
            "ws_N_m2": ws_design,
            "limit_by": limit_by,
            "governing": governing,
            "tw": tw_design,
            "pw": pw_design, # W/N
            "pw_hp_kg": round(pw_design * G0 / 735.5, 3) if pw_design else None, # KM/kg
            "power_kw": power_kw,
            "required_power_kw": required_power_kw,
            "power_hp": power_hp,
            "thrust_kn": thrust_kn,
            "tw_min_climb_bipol18": round(tw_climb_min, 4)
        }
    }
