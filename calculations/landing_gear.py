"""
calculations/landing_gear.py
Milestone 2: Fuselage Packaging, Cabin Ergonomics, Landing Gear Kinematics,
Energy Absorption, Ground Stability, and Turnover Analysis.
Conforming strictly to MEiL PW BIPOL I:
- Wyklad 3: okBIPOL_1_handout_3.pdf (Fuselage, Cabin, Ergonomics, Cargo ULDs, Upsweep)
- Wyklad 4: okBIPOL_1_handout_4.pdf (Landing gear sizing, ground stability, turnover)
- Wyklad 15: okBIPOL_1_handout_15.pdf (Energy balance, shock absorption, fullness, loads)
- Wyklad 7: okBIPOL_1_handout_7.pdf (Ground clearances, nose/main static load share)
"""

import math
from calculations.atmosphere import G0
from calculations.propeller_clearance import minimum_ground_clearance_m, meets_minimum, REFERENCE

# Standard Cargo Unit Load Devices (ULD) Envelopes (Handout 3, p. 7)
ULD_CONTAINERS = {
    "LD-2": {
        "height_m": 1.626,
        "width_m": 1.562,
        "depth_m": 1.534,
        "volume_m3": 3.398,
        "max_gross_kg": 1224.7,
    },
    "LD-3": {
        "height_m": 1.626,
        "width_m": 2.007,
        "depth_m": 1.534,
        "volume_m3": 4.417,
        "max_gross_kg": 1587.6,
    },
    "LD-4": {
        "height_m": 1.626,
        "width_m": 2.438,
        "depth_m": 1.534,
        "volume_m3": 5.522,
        "max_gross_kg": 2449.4,
    },
    "LD-5": {
        "height_m": 1.626,
        "width_m": 3.175,
        "depth_m": 1.534,
        "volume_m3": 7.900,
        "max_gross_kg": 2449.4,
    },
    "LD-8": {
        "height_m": 1.626,
        "width_m": 3.175,
        "depth_m": 1.534,
        "volume_m3": 6.938,
        "max_gross_kg": 2449.4,
    },
    "LD-11": {
        "height_m": 1.626,
        "width_m": 3.175,
        "depth_m": 1.534,
        "volume_m3": 7.160,
        "max_gross_kg": 3175.0,
    },
}

# Empirical Tire Sizing Regressions: d = A * W_m^B, w = A * W_m^B (W_m in lb, d/w in inches)
# Source: Wyklad 4 / Handout 4, p. 5
TIRE_COEFFICIENTS = {
    "piston_ga": {"Ad": 1.51, "Bd": 0.349, "Aw": 0.715, "Bw": 0.312},
    "light": {"Ad": 1.51, "Bd": 0.349, "Aw": 0.715, "Bw": 0.312},
    "jet_business": {"Ad": 2.69, "Bd": 0.251, "Aw": 1.170, "Bw": 0.216},
    "jet_transport": {"Ad": 1.63, "Bd": 0.315, "Aw": 0.104, "Bw": 0.480},
    "turboprop_regional": {"Ad": 1.63, "Bd": 0.315, "Aw": 0.104, "Bw": 0.480},
    "jet_trainer": {"Ad": 1.59, "Bd": 0.302, "Aw": 0.098, "Bw": 0.467},
    "fighter": {"Ad": 1.59, "Bd": 0.302, "Aw": 0.098, "Bw": 0.467},
    "uav": {"Ad": 1.51, "Bd": 0.349, "Aw": 0.715, "Bw": 0.312},
    "glider": {"Ad": 1.51, "Bd": 0.349, "Aw": 0.715, "Bw": 0.312},
}

# Pilot Cockpit Vision Angles (Handout 3, p. 5)
PILOT_VISION_ANGLES = {
    "piston_ga": {"alpha_F_deg": 8.0, "alpha_S_deg": 35.0},
    "light": {"alpha_F_deg": 8.0, "alpha_S_deg": 35.0},
    "glider": {"alpha_F_deg": 10.0, "alpha_S_deg": 35.0},
    "uav": {"alpha_F_deg": 0.0, "alpha_S_deg": 0.0},
    "jet_business": {"alpha_F_deg": 14.0, "alpha_S_deg": 35.0},
    "turboprop_regional": {"alpha_F_deg": 15.0, "alpha_S_deg": 35.0},
    "jet_transport": {"alpha_F_deg": 18.0, "alpha_S_deg": 45.0},
    "jet_trainer": {"alpha_F_deg": 13.0, "alpha_S_deg": 40.0},
    "fighter": {"alpha_F_deg": 14.0, "alpha_S_deg": 40.0},
}


def size_tire(m0_kg: float, aircraft_type: str = "piston_ga", n_wheels: int = 2) -> tuple:
    """
    Computes tire diameter and width in meters using empirical regressions from Handout 4, p. 5.
    d = A_d * W_m^B_d, w = A_w * W_m^B_w, where W_m = 0.9 * W_TO / n_wheels in [lb].
    """
    coeffs = TIRE_COEFFICIENTS.get(aircraft_type, TIRE_COEFFICIENTS["piston_ga"])
    # 0.9 * W_TO on main gear, converted to pounds (1 kg = 2.20462262 lb)
    w_to_lb = m0_kg * 2.20462262
    w_m_lb = max(10.0, (0.90 * w_to_lb) / max(1, n_wheels))

    d_in = coeffs["Ad"] * (w_m_lb ** coeffs["Bd"])
    w_in = coeffs["Aw"] * (w_m_lb ** coeffs["Bw"])

    d_m = d_in * 0.0254
    w_m = w_in * 0.0254
    return round(d_m, 4), round(w_m, 4)


def calculate_fuselage_and_gear(params: dict) -> dict:
    """
    Calculates fuselage ergonomics, cabin layout, cargo container sizing, landing gear kinematics,
    energy absorption, ground stability, turnover angles, and tailstrike clearances per Wyklad 3, 4, 15.

    Parameters
    ----------
    params : dict
        Airframe, mass, and configuration parameters:
        - 'm0' / 'mtow_kg': float (Takeoff mass [kg])
        - 'wing_loading' / 'ws': float (Wing loading [N/m²])
        - 'wingspan_m' / 'b': float (Wingspan [m])
        - 'fuselage_length_m' / 'fuselage_len': float (optional length [m])
        - 'fuselage_diameter_m' / 'fuselage_diam': float (optional diameter [m])
        - 'aircraft_type': str
        - 'n_pax': int (Passenger count, default 0)
        - 'n_crew': int (Crew count, default 1)
        - 'range_category': str ('short_range' | 'long_range')
        - 'm_cargo': float (Cargo payload mass [kg])
        - 'container_type': str ('LD-2', 'LD-3', 'LD-4', 'LD-5', 'LD-8', 'LD-11', 'bulk')
        - 'landing_gear_type': str ('tricycle' | 'tailwheel', default 'tricycle')
        - 'track_m': float (optional override for gear track [m])
        - 'wheelbase_m': float (optional override for wheelbase [m])
        - 'w_drop_m_s': float (optional touchdown vertical velocity [m/s])
        - 'lift_ratio_touchdown': float (P_z / (mg), default 0.67)
        - 'oleo_stroke_m': float (optional shock strut stroke [m])
        - 'oleo_fullness': float (strut fullness coefficient, default 0.80)
        - 'tire_fullness': float (tire fullness coefficient, default 0.45)
        - 'friction_coeff': float (braking friction coefficient, default 0.35)
        - 'cg_fwd_m', 'cg_aft_m', 'z_cg_m': float (CG locations)
        - 'propeller_diameter_m': float (optional)
        - 'prop_shaft_height_m': float (optional)

    Returns
    -------
    dict
        Structured verification results conforming to Milestone 2 interface contracts.
    """
    # 1. Parameter extraction and normalization
    m0 = float(params.get("m0") or params.get("mtow_kg") or 1100.0)
    ws = float(params.get("wing_loading") or params.get("ws") or 650.0)
    b = float(params.get("wingspan_m") or params.get("b") or 11.0)
    ac_type = params.get("aircraft_type", "piston_ga")
    n_pax = int(params.get("n_pax", 0))
    n_crew = int(params.get("n_crew", 1))
    range_cat = params.get("range_category", "short_range")
    m_cargo = float(params.get("m_cargo", 0.0))
    container_type = params.get("container_type", "bulk")
    gear_type = params.get("landing_gear_type", "tricycle")

    # 2. Cabin Sizing & Ergonomics (Handout 3, p. 5-7)
    if range_cat == "long_range":
        seat_width = float(params.get("seat_width_m", 0.48))
        seat_pitch = float(params.get("seat_pitch_m", 0.90))
        aisle_width = float(params.get("aisle_width_m", 0.56))
        aisle_height = 1.93
        pax_per_lav = 20
        galley_vol_per_pax = 0.08
    else:  # short_range
        seat_width = float(params.get("seat_width_m", 0.44))
        seat_pitch = float(params.get("seat_pitch_m", 0.78))
        aisle_width = float(params.get("aisle_width_m", 0.38))
        aisle_height = 1.52
        pax_per_lav = 45
        galley_vol_per_pax = 0.02

    # Seating abreast determination
    if n_pax <= 4:
        seats_abreast = 2 if n_pax > 1 else (1 if n_pax == 1 else 0)
        n_aisles = 0
    elif n_pax <= 9:
        seats_abreast = 2
        n_aisles = 1
    elif n_pax <= 19:
        seats_abreast = 3
        n_aisles = 1
    elif n_pax <= 70:
        seats_abreast = 4
        n_aisles = 1
    elif n_pax <= 180:
        seats_abreast = 6
        n_aisles = 1
    else:
        seats_abreast = 7
        n_aisles = 2

    # Cabin cross section
    armrest_width = 0.05
    wall_clearance = 0.05
    delta_t_wall = 0.12  # Structural wall thickness [m]
    floor_height = 0.20   # Floor grid structure [m]

    if n_pax > 0:
        cabin_width = (seats_abreast * seat_width +
                       n_aisles * aisle_width +
                       (seats_abreast + 1) * armrest_width +
                       2 * wall_clearance)
        n_rows = math.ceil(n_pax / max(1, seats_abreast))
        cabin_length = n_rows * seat_pitch
        cabin_height = aisle_height
        n_lav = math.ceil(n_pax / pax_per_lav)
        lavatory_length = n_lav * 0.90
        cockpit_length = 2.40 if n_crew >= 2 else 1.50
        vestibule_length = 1.20 if n_pax >= 19 else 0.50
    else:
        cabin_width = 0.85
        cabin_height = 1.20
        n_rows = 0
        cabin_length = 0.0
        n_lav = 0
        lavatory_length = 0.0
        cockpit_length = 1.40 if n_crew > 0 else 0.50
        vestibule_length = 0.0

    # Minimum fuselage diameter based on ergonomics
    min_fus_diam = max(
        cabin_width + 2 * delta_t_wall,
        cabin_height + floor_height + 2 * delta_t_wall
    )

    fuselage_diam = float(params.get("fuselage_diameter_m") or params.get("fuselage_diam") or max(1.20, min_fus_diam))
    total_cabin_core = cockpit_length + cabin_length + lavatory_length + vestibule_length
    min_fus_len = 1.5 * fuselage_diam + total_cabin_core + 3.0 * fuselage_diam
    fuselage_len = float(params.get("fuselage_length_m") or params.get("fuselage_len") or max(7.5, min_fus_len))

    # Fineness ratio and Raymer/Torenbeek wetted area (Handout 3, p. 20)
    fineness_ratio = fuselage_len / max(0.1, fuselage_diam)
    # S_wet = pi * d_f * l_f * (1 - 2/lambda)^(2/3) * (1 + 1/lambda^2)
    lambda_term = max(2.01, fineness_ratio)
    s_wet_fus = (math.pi * fuselage_diam * fuselage_len *
                 ((1.0 - 2.0 / lambda_term) ** (2.0 / 3.0)) *
                 (1.0 + 1.0 / (lambda_term ** 2)))

    # Aft cone upsweep angle (Handout 3, p. 20: max 24 deg)
    aft_cone_len = max(1.5, 3.0 * fuselage_diam)
    aft_upsweep_h = fuselage_diam * 0.38
    upsweep_rad = math.atan2(aft_upsweep_h, aft_cone_len)
    upsweep_angle_deg = round(math.degrees(upsweep_rad), 1)
    upsweep_compliant = upsweep_angle_deg <= 24.0

    # Vision angles
    vis_data = PILOT_VISION_ANGLES.get(ac_type, PILOT_VISION_ANGLES["piston_ga"])

    # 3. Cargo ULD Container Envelopes (Handout 3, p. 7)
    cargo_diag = 0.0
    container_compatible = True
    n_containers = 0
    hold_volume_required = 0.0

    if m_cargo > 0:
        if container_type in ULD_CONTAINERS:
            uld = ULD_CONTAINERS[container_type]
            cargo_diag = math.hypot(uld["width_m"], uld["height_m"])
            # Diameter check: container diagonal + 0.30 m clearance
            container_compatible = (cargo_diag + 0.30) <= fuselage_diam
            n_containers = math.ceil(m_cargo / uld["max_gross_kg"])
            hold_volume_required = n_containers * uld["volume_m3"]
        else:  # bulk cargo (density 160 kg/m3)
            hold_volume_required = m_cargo / 160.0
            container_compatible = True

    # 4. Landing Gear Sizing & Energy Absorption (Handout 4, 15)
    # Touchdown vertical descent speed w_drop (CS-23.723 / Handout 15)
    if "w_drop_m_s" in params and params["w_drop_m_s"] is not None:
        w_drop = float(params["w_drop_m_s"])
    else:
        # w_drop = max(2.13, min(3.05, 0.51 * (W/S)^0.25))
        w_calc = 0.51 * (ws ** 0.25)
        w_drop = max(2.13, min(3.05, w_calc))

    # Tire sizing from Handout 4 empirical regressions
    tire_diam, tire_width = size_tire(m0, ac_type, n_wheels=2)
    tire_deflection = float(params.get("tire_deflection_m") or (0.16 * tire_diam))

    # Shock absorber stroke and fullness
    oleo_stroke = float(params.get("oleo_stroke_m", 0.20))
    eta_a = float(params.get("oleo_fullness", 0.80))
    eta_p = float(params.get("tire_fullness", 0.45))
    i_strut = float(params.get("strut_leverage", 1.0))
    k_lift = float(params.get("lift_ratio_touchdown", 0.67))
    friction_mu = float(params.get("friction_coeff", 0.35))

    # Energy balance: E = E_kin + E_pot = 0.5 * m * w^2 + (mg - P_z) * h
    h_total = i_strut * oleo_stroke + tire_deflection
    e_kin = 0.5 * m0 * (w_drop ** 2)
    e_pot = (m0 * G0 * (1.0 - k_lift)) * h_total
    e_total = e_kin + e_pot

    # Work capacity: L_a = Z * (i * h_a * eta_a + h_p * eta_p)
    delta_s_eff = (i_strut * oleo_stroke * eta_a) + (tire_deflection * eta_p)
    z_max = e_total / max(1e-4, delta_s_eff)

    # Dynamic load factor increment Delta n_L and total landing load factor n_L
    delta_n_l = z_max / (m0 * G0)
    n_l = delta_n_l + k_lift

    # Ground braking force and horizontal load factor
    x_braking = friction_mu * z_max
    n_x = friction_mu * delta_n_l

    # Pitch moment and angular acceleration
    x_p = float(params.get("main_gear_offset_m", 0.25))
    z_p = float(params.get("gear_height_m", 0.85))
    pitch_moment = z_max * x_p + x_braking * z_p
    # I_yy estimation for light aircraft: ~ 0.20 * m0 * (0.5 * l_f)^2
    i_yy = max(100.0, 0.20 * m0 * ((0.5 * fuselage_len) ** 2))
    pitch_accel = pitch_moment / i_yy

    # 5. Landing Gear Geometry, Turnover & Ground Stability (Handout 4, 7)
    # Default geometry heuristics if not explicitly given
    track_m = float(params['track_m'] if params.get('track_m') is not None else 0.24 * b)
    supplied_base = params.get('wheelbase_m')
    wheelbase_m = float(supplied_base if supplied_base is not None else 0.38 * fuselage_len)

    # Center of gravity positions
    z_cg = float(params.get("z_cg_m", 1.20))
    cg_aft = float(params['cg_aft_m'] if params.get('cg_aft_m') is not None else 0.48 * fuselage_len)
    cg_fwd = float(params['cg_fwd_m'] if params.get('cg_fwd_m') is not None else 0.42 * fuselage_len)

    if gear_type == "tailwheel":
        # Main gear is 15 deg ahead of forward CG
        x_main = float(params['x_main_m']) if params.get('x_main_m') is not None else cg_fwd - z_cg * math.tan(math.radians(15.0))
        x_nose = float(params['x_nose_m']) if params.get('x_nose_m') is not None else x_main + wheelbase_m if supplied_base is not None else 0.92 * fuselage_len
        if params.get('x_main_m') is None and params.get('x_nose_m') is not None and supplied_base is not None:
            x_main = x_nose - wheelbase_m
        wheelbase_m = abs(x_main - x_nose)
        nose_arm = abs(x_nose - cg_aft)
        main_arm = abs(cg_aft - x_main)
        nose_load_pct = (main_arm / max(0.1, main_arm + nose_arm)) * 100.0
        main_load_pct = 100.0 - nose_load_pct
        main_gear_cg_angle_deg = round(math.degrees(math.atan2(cg_fwd - x_main, z_cg)), 1)
    else:  # Tricycle gear
        # Main gear is placed 13 - 15 deg aft of critical aft CG
        main_gear_target_offset = z_cg * math.tan(math.radians(14.0))
        x_main = float(params['x_main_m']) if params.get('x_main_m') is not None else cg_aft + main_gear_target_offset
        x_nose = float(params['x_nose_m']) if params.get('x_nose_m') is not None else x_main - wheelbase_m if supplied_base is not None else 0.12 * fuselage_len
        if params.get('x_main_m') is None and params.get('x_nose_m') is not None and supplied_base is not None:
            x_main = x_nose + wheelbase_m
        wheelbase_actual = abs(x_main - x_nose)
        wheelbase_m = wheelbase_actual

        # Main gear angle aft of CG
        dx_cg_main = x_main - cg_aft
        main_gear_cg_angle_deg = round(math.degrees(math.atan2(dx_cg_main, z_cg)), 1)

        # Static load distribution on nose and main gear (Handout 7, p. 10: typically 8% - 15%)
        nose_load_pct = round(((x_main - cg_aft) / max(0.1, wheelbase_actual)) * 100.0, 1)
        main_load_pct = round(100.0 - nose_load_pct, 1)

    # Lateral turnover angle (Handout 4, p. 5)
    # 2D transverse formula: tan(psi) = 2 * z_cg / track
    half_track = track_m / 2.0
    tipover_angle_deg = round(math.degrees(math.atan2(z_cg, half_track)), 1)

    # 3D base triangle turnover angle (Handout 4 & Handout 7):
    # d_tip = y_m * l_n / sqrt(B^2 + y_m^2)
    critical_cg = min((cg_fwd, cg_aft), key=lambda x: abs(x - x_nose))
    l_n = abs(critical_cg - x_nose)
    diagonal = math.hypot(wheelbase_m, half_track)
    d_tip = (half_track * l_n) / diagonal if diagonal > 0 else 0.0
    tipover_angle_3d_deg = round(math.degrees(math.atan2(z_cg, d_tip)), 1)

    supported = min(x_nose, x_main) < min(cg_fwd, cg_aft) and max(cg_fwd, cg_aft) < max(x_nose, x_main)
    tipover_compliant = track_m > 0 and wheelbase_m > 0 and supported and tipover_angle_3d_deg < 60.0

    # Main gear compliance check (13 to 15 deg aft, with standard 12.5 - 16.5 tolerance)
    main_gear_cg_compliant = (12.5 <= main_gear_cg_angle_deg <= 16.5)

    # Tailstrike clearance angle (Handout 4, p. 7: >= 10 - 15 deg)
    x_tail = float(params.get("x_tail_m", 0.92 * fuselage_len))
    z_tail = float(params.get("z_tail_m", 0.85))
    dx_tail = max(0.1, x_tail - x_main)
    tail_clearance_rad = math.atan2(z_tail, dx_tail)
    tail_clearance_deg = round(math.degrees(tail_clearance_rad), 1)
    tail_clearance_compliant = tail_clearance_deg >= 10.0

    # Compare the dimension under the assumed compression. Oleo full stroke plus
    # tyre deflection is a conservative screen, not a measured static deflection.
    prop_diam = float(params.get("propeller_diameter_m", 0.0))
    prop_shaft_h = float(params.get("prop_shaft_height_m", 1.40))
    ground_clearance_m = round(z_tail, 2)  # Belly clearance baseline

    prop_applicable = params.get('engine_type', 'prop') not in ('none', 'jet')
    req_prop_clearance = minimum_ground_clearance_m(params) if prop_applicable and params.get('operating_surface') != 'water' else None
    if prop_diam > 0 and req_prop_clearance is not None:
        # clearance under compressed gear
        gear_compressed = oleo_stroke + tire_deflection
        prop_ground_clearance_raw = prop_shaft_h - (prop_diam / 2.0) - gear_compressed
        prop_ground_clearance_m = round(prop_ground_clearance_raw, 3)
        prop_clearance_compliant = meets_minimum(prop_ground_clearance_raw, req_prop_clearance)
    else:
        prop_ground_clearance_m = None
        prop_ground_clearance_raw = None
        prop_clearance_compliant = None

    return {
        "tipover_angle_deg": tipover_angle_deg,
        "tipover_angle_3d_deg": tipover_angle_3d_deg,
        "tipover_reference_cg_m": critical_cg,
        "ground_clearance_m": ground_clearance_m,
        "tail_clearance_deg": tail_clearance_deg,
        "tipover_compliant": tipover_compliant,
        "tail_clearance_compliant": tail_clearance_compliant,
        "main_gear_cg_compliant": main_gear_cg_compliant,
        "propeller_clearance_m": prop_ground_clearance_m,
        "propeller_clearance_applicable": prop_applicable,
        "propeller_clearance_unrounded_m": prop_ground_clearance_raw,
        "propeller_clearance_req_m": req_prop_clearance,
        "propeller_clearance_reference": REFERENCE,
        "propeller_clearance_deflection_basis": "full_stroke_plus_tyre_deflection",
        "propeller_clearance_assumed_deflection_m": oleo_stroke+tire_deflection,
        "propeller_clearance_certification_compliant": None,
        "propeller_clearance_compliant": prop_clearance_compliant,
        "gear_reactions": {
            "max_vertical_reaction_n": round(z_max, 1),
            "vertical_load_factor_increment": round(delta_n_l, 3),
            "total_landing_load_factor": round(n_l, 3),
            "braking_force_n": round(x_braking, 1),
            "horizontal_load_factor": round(n_x, 3),
            "nose_gear_static_load_pct": nose_load_pct,
            "main_gear_static_load_pct": main_load_pct,
            "pitch_moment_nm": round(pitch_moment, 1),
            "pitch_angular_accel_rad_s2": round(pitch_accel, 3),
            "sink_rate_drop_m_s": round(w_drop, 2),
            "total_energy_j": round(e_total, 1),
            "cs23_load_factor_compliant": n_l <= 3.5,
        },
        "fuselage": {
            "fuselage_length_m": round(fuselage_len, 2),
            "fuselage_diameter_m": round(fuselage_diam, 2),
            "fineness_ratio": round(fineness_ratio, 2),
            "s_wet_fus_m2": round(s_wet_fus, 2),
            "cabin_width_m": round(cabin_width, 2),
            "cabin_height_m": round(cabin_height, 2),
            "cabin_length_m": round(cabin_length, 2),
            "n_rows": n_rows,
            "seats_abreast": seats_abreast,
            "seat_pitch_m": seat_pitch,
            "seat_width_m": seat_width,
            "aisle_width_m": aisle_width,
            "upsweep_angle_deg": upsweep_angle_deg,
            "upsweep_compliant": upsweep_compliant,
            "pilot_vision_forward_deg": vis_data["alpha_F_deg"],
            "pilot_vision_side_deg": vis_data["alpha_S_deg"],
        },
        "cargo": {
            "container_type": container_type,
            "n_containers": n_containers,
            "hold_volume_required_m3": round(hold_volume_required, 3),
            "container_compatible": container_compatible,
        },
        "gear_dimensions": {
            'x_main_m': x_main,
            'x_nose_m': x_nose,
            "wheelbase_m": round(wheelbase_m, 2),
            "track_m": round(track_m, 2),
            "tire_diameter_m": tire_diam,
            "tire_width_m": tire_width,
            "tire_deflection_m": round(tire_deflection, 3),
            "oleo_stroke_m": round(oleo_stroke, 3),
            "main_gear_cg_angle_deg": main_gear_cg_angle_deg,
        },
    }
