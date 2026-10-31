# -*- coding: utf-8 -*-
"""
Moduł osiągów samolotu (BIPOL I).
Oparty w pierwszej kolejności na oficjalnej metodyce MEiL PW:
dr inż. Zbigniew Paturski — "Przewodnik po projektach z Mechaniki Lotu"
(Projekt nr 6: Osiągi samolotu — Metoda Mocy, Wykres Ofertowy, Zasięg i Długotrwałość).

Obliczenia:
  - Prędkości przeciągnięcia i charakterystycznych (Vs, Vlof, V2, Vapp, Vtd, Vc, Vmax)
  - Prędkości wznoszenia wy(V), kąta toru gamma(V) i biegunowej mocy (Tabela 6.1)
  - Wykresu ofertowego i pułapów: praktycznego Hp i teoretycznego Ht (Tabela 6.2)
  - Czasu wznoszenia th oraz thp ze wzoru całkowego (6.10) / analitycznego (6.12)
  - Zasięgu i długotrwałości lotu ze wzorów Bregueta (6.13 - 6.38, Tabela 6.3)
  - Startu i lądowania znad przeszkody 15 m
  - Zakrętu ustalonego
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0
from calculations.paturski_ml import paturski_project_6_performance
from calculations.runway import takeoff_distance, rolling_coefficient, landing_air_path
from calculations.flight_model import flight_point, level_flight_envelope, mission_masses
from calculations.model_scope import is_water, suppress_water_distances
from calculations.mission_cruise import assess_mission_range


def calculate_performance(m0: float, geom: dict, aero: dict, sizing: dict, params: dict, mass_result: dict = None):
    """
    Parametry:
      - m0: masa startowa MTOW [kg]
      - geom: słownik geometrii
      - aero: słownik aerodynamiki (zawiera paturski_p3)
      - sizing: wyniki doboru napędu
      - params: parametry misji i napędu
    """
    S = float(geom["wing"]["S"])
    AR = float(geom["wing"]["AR"])
    W = m0 * G0
    ws = W / S

    engine_type = params.get("engine_type", "prop")
    is_glider = engine_type == "none" or params.get("aircraft_type") == "glider"
    cz_max_clean = float(aero["cz_max_clean"])
    cz_max_to = float(aero["cz_max_to"])
    cz_max_lnd = float(aero["cz_max_lnd"])
    cx0 = float(aero["cx0_clean"])
    k_clean = float(aero["k_clean"])

    # 1. METODYKA PATURSKIEGO PROJEKT NR 6 JAKO PIERWSZA I NADRZĘDNA
    p6 = paturski_project_6_performance(
        geom_res=geom,
        sizing_res=sizing,
        params=params,
        m0=m0,
        p3_aero=aero.get("paturski_p3"),
        m_fuel=mass_result["m_fuel"] if mass_result else None, mass_result=mass_result
    )
    t6_1 = p6["table_6_1_power_balance_h0"]
    t6_2 = p6["table_6_2_climb_and_ceilings"]
    ceilings = t6_2["ceilings"]
    offer = p6["offer_chart_summary"]
    range_res = p6["range_endurance_6_5"]

    # 2. Prędkości przeciągnięcia na poziomie morza [m/s] i [km/h]
    vs_clean_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_clean))
    vs_to_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_to))
    vs_lnd_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_lnd))

    # 3. Ciąg / Moc dostępna na poziomie morza
    dp = sizing["design_point"]
    eta_p = float(params.get("prop_efficiency", 0.82))
    if is_glider:
        T0_avail = 0.0
        P0_avail = 0.0
    elif engine_type == "jet":
        T0_avail = dp["tw"] * W
        P0_avail = None
    else:
        P0_avail = dp["pw"] * W
        T0_avail = None

    sl_flight = level_flight_envelope(params, sizing, m0, S, cx0, k_clean, cz_max_clean, 0)
    v_max_sl_ms = sl_flight['max_ms'] or 0.0

    # 5. Krzywa wznoszenia wy(V) na poziomie morza z Metody Mocy Paturskiego (Tabela 6.1)
    if is_glider:
        wy_max = 0.0
        v_wy_max = 0.0
        climb_curve = []
    else:
        wy_max = offer["w_max_h0_ms"]
        v_wy_max = offer["v_w_h0_kmh"] / 3.6

        # Tworzymy gładką krzywą wznoszenia w oparciu o punkty z Tabeli 6.1
        climb_curve = []
        for r in sorted(t6_1, key=lambda x: x["v_kmh"]):
            climb_curve.append({
                "v_kmh": r["v_kmh"],
                "wy_ms": r["w_ms"]
            })

    # 6. Prędkość przelotowa i liczba Macha
    v_cr_req_kmh = float(params.get("cruise_speed_kmh", 250.0))
    v_cr_req_ms = v_cr_req_kmh / 3.6
    h_cr = float(params.get("cruise_altitude_m", 3000.0))
    isa_cr = isa_atmosphere(h_cr)
    mach_cr = v_cr_req_ms / isa_cr["a"]

    # 7. Pułap praktyczny i teoretyczny z Tabeli 6.2 dr. Paturskiego
    h_pract = ceilings["h_p_practical_m"]
    h_absolute = ceilings["h_t_theoretical_m"]

    # 8. Full take-off distance; same model as the matching chart.
    v_lof_ms, v_2_ms = 1.15 * vs_to_ms, 1.20 * vs_to_ms
    k_to = aero['k_to']
    phi_ge = 1.6**2 / (1 + 1.6**2)
    takeoff = takeoff_distance(ws, cz_max_to, aero['cx0_to'], k_to, engine_type,
        (dp.get('tw') if engine_type == 'jet' else dp.get('pw')) or 0.,
        eta_p, float(params.get('prop_eff_to', .65)),
        mu_ground=rolling_coefficient(params))
    takeoff = {key: round(value, 1) if isinstance(value, float) else value
               for key, value in takeoff.items()}

    # 9. Lądowanie (Fiszdon / Raymer)
    v_app_ms = 1.30 * vs_lnd_ms
    v_td_ms = 1.15 * vs_lnd_ms
    # Landing is evaluated at mission landing mass, not take-off mass.
    landing_mass = mission_masses(mass_result)['landing_start'] if mass_result else m0
    ws_lnd = landing_mass * G0 / S
    vs_landing = math.sqrt(2 * ws_lnd / (RHO0 * cz_max_lnd))
    v_app_ms, v_td_ms = 1.30 * vs_landing, 1.15 * vs_landing
    cx0_lnd = aero["cx0_lnd"]
    gamma_app_rad = math.radians(3.5)
    landing_path = landing_air_path(v_app_ms, approach_angle_deg=math.degrees(gamma_app_rad))
    r_flare, h_flare = landing_path['radius_m'], landing_path['flare_height_m']
    s_air_lnd = landing_path['distance_m']

    s_free_lnd = 1.5 * v_td_ms
    mu_brake = 0.40
    v_rms_lnd = v_td_ms / math.sqrt(2.0)
    q_rms_lnd = 0.5 * RHO0 * (v_rms_lnd ** 2)
    cz_lnd_roll = 0.20
    cx_lnd_roll = cx0_lnd + phi_ge * aero["k_lnd"] * (cz_lnd_roll ** 2)
    a_mean_brake = G0 * (mu_brake + (q_rms_lnd / ws_lnd) * (cx_lnd_roll - mu_brake * cz_lnd_roll))
    s_brake_lnd = (v_td_ms ** 2) / (2.0 * a_mean_brake)
    s_g_lnd = s_free_lnd + s_brake_lnd
    s_lnd_15 = s_air_lnd + s_g_lnd

    # 10. Parametry zakrętu ustalonego
    v_turn_ms = max(vs_clean_ms * 1.45, min(v_cr_req_ms, v_max_sl_ms * 0.85))
    q_turn = 0.5 * RHO0 * (v_turn_ms ** 2)
    n_aero_max = (q_turn * cz_max_clean) / ws
    if is_glider:
        n_sustained = min(n_aero_max, math.sqrt(2))
        turn_mode = 'gliding'
    else:
        t_avail_turn = T0_avail if engine_type == "jet" else (P0_avail * eta_p) / v_turn_ms
        n_thrust_sq = ((t_avail_turn / W) * q_turn - (q_turn ** 2) * cx0 / ws) / (k_clean * ws)
        n_sustained = min(n_aero_max, math.sqrt(max(0.0, n_thrust_sq)))
        turn_mode = 'level' if n_sustained > 1 else 'unavailable'

    cos_phi = min(1.0, 1.0 / max(1.0, n_sustained))
    bank_angle_deg = math.degrees(math.acos(cos_phi))
    n_factor = math.sqrt(max(0.0, (n_sustained ** 2) - 1.0))
    r_min_turn_m = (v_turn_ms ** 2) / (G0 * n_factor) if n_factor > 0 else None
    psi_dot_rad_s = (G0 * n_factor) / v_turn_ms
    psi_dot_deg_s = math.degrees(psi_dot_rad_s)
    t_turn_360_s = (2.0 * math.pi) / psi_dot_rad_s if psi_dot_rad_s > 0 else None

    result = {
        "terms": dict(ws=ws, W=W, vs_clean=vs_clean_ms, vs_to=vs_to_ms, vs_lnd=vs_lnd_ms,
                      v_max_sl=v_max_sl_ms, p_avail_w=P0_avail, t_avail_n=T0_avail),
        "cruise_check": dict(flight_point(params, sizing, mission_masses(mass_result)['cruise_start'] if mass_result else m0,
            S, cx0, k_clean, h_cr, v_cr_req_ms),
            altitude_m=h_cr, tas_kmh=v_cr_req_kmh, cl_max=cz_max_clean,
            mass_kg=mission_masses(mass_result)['cruise_start'] if mass_result else m0),
        "level_flight_available_sl": sl_flight['available'] and not is_glider,
        "speeds": {
            "vs_clean_kmh": round(vs_clean_ms * 3.6, 1),
            "vs_to_kmh": round(vs_to_ms * 3.6, 1),
            "vs_lnd_kmh": round(vs_lnd_ms * 3.6, 1),
            "v_lof_kmh": round(v_lof_ms * 3.6, 1),
            "v_2_kmh": round(v_2_ms * 3.6, 1),
            "v_app_kmh": round(v_app_ms * 3.6, 1),
            "v_td_kmh": round(v_td_ms * 3.6, 1),
            "v_cruise_kmh": round(v_cr_req_kmh, 1),
            "v_max_sl_kmh": round(v_max_sl_ms * 3.6, 1),
            "mach_cruise": round(mach_cr, 3)
        },
        "climb": {
            "wy_max_ms": round(wy_max, 2),
            "v_wy_max_kmh": round(v_wy_max * 3.6, 1),
            "climb_curve": climb_curve
        },
        "ceiling": {
            "service_ceiling_m": int(h_pract),
            "service_ceiling_ft": int(h_pract * 3.28084),
            "absolute_ceiling_m": int(h_absolute),
            "time_to_service_ceiling_min": ceilings.get("t_hp_climb_to_practical_ceiling_min", 0.0),
            "model_upper_limit_m": 20000
        },
        "takeoff": takeoff,
        "landing": {
            "terms": dict(ws_lnd=ws_lnd, vs=vs_landing, v_app=v_app_ms, v_td=v_td_ms, cx0_lnd=cx0_lnd,
                          k_lnd=aero["k_lnd"], cz_max_lnd=cz_max_lnd, gamma_app_deg=3.5, r_flare=r_flare,
                          h_flare=h_flare, mu_brake=mu_brake, v_rms=v_rms_lnd, q_rms=q_rms_lnd,
                          phi_ge=phi_ge, cz_roll=cz_lnd_roll, cx_roll=cx_lnd_roll, a_mean=a_mean_brake,
                          effective_flare_angle_rad=landing_path['effective_flare_angle_rad']),
            "approach_straight_m": landing_path['straight_m'],
            "flare_horizontal_m": landing_path['flare_horizontal_m'],
            "mass_kg": landing_mass,
            "vs_landing_mass_kmh": vs_landing * 3.6,
            "air_approach_m": round(s_air_lnd, 1),
            "free_roll_m": round(s_free_lnd, 1),
            "braking_roll_m": round(s_brake_lnd, 1),
            "ground_roll_m": round(s_g_lnd, 1),
            "distance_from_15m": round(s_lnd_15, 1)
        },
        "turn": {
            "terms": dict(v=v_turn_ms, q=q_turn, n_aero_max=n_aero_max, ws=ws, vs_clean=vs_clean_ms,
                          v_cr=v_cr_req_ms, v_max=v_max_sl_ms,
                          t_avail=None if is_glider else t_avail_turn,
                          n_thrust_sq=None if is_glider else n_thrust_sq, n=n_sustained),
            "mode": turn_mode,
            "level_sustained": turn_mode == 'level',
            "note": 'Kinematyka zakrętu szybowego 45° z utratą energii/wysokości.' if turn_mode == 'gliding' else ('Brak nadmiaru ciągu do zakrętu poziomego przy tej prędkości.' if turn_mode == 'unavailable' else 'Ograniczenie aerodynamiczne i napędowe; sprawdź osobno obwiednię konstrukcyjną.'),
            "n_sustained": round(n_sustained, 2),
            "bank_angle_deg": round(bank_angle_deg, 1),
            "r_min_m": round(r_min_turn_m, 1) if r_min_turn_m is not None else None,
            "psi_dot_deg_s": round(psi_dot_deg_s, 2),
            "t_360_s": round(t_turn_360_s, 1) if t_turn_360_s is not None else None,
            "v_turn_kmh": round(v_turn_ms * 3.6, 1)
        },
        "range_and_endurance": {
            "range_km": range_res.get("l_max_km", 0.0),
            "endurance_h": range_res.get("t_max_h", 0.0),
            "v_cruise_kmh": range_res.get("v_l_max_kmh", 0.0),
            "h_cruise_m": range_res.get("h_cruise_m", 0)
        },
        "paturski_p6": p6
    }
    if is_water(params):
        suppress_water_distances(result)
    if mass_result:
        result['mission_range'] = assess_mission_range(params, mass_result, geom, aero, sizing)
    return result
