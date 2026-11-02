"""
calculations/empennage.py
Milestone 2: Propulsion Matching, Propeller Sizing, Propeller Ground/Fuselage Clearances,
Empennage Volume Sizing, Tail Layouts (Conventional, T-Tail, Cruciform, V-Tail, Canard),
and Rudder Spin Recovery Unshielded Area (Corke / Raymer Criterion).

Traceable strictly to:
- Wyklad 5: okBIPOL_1_handout_5.pdf (Propulsion integration, helical tip Mach, advance ratio)
- Wyklad 6: okBIPOL_1_handout_6.pdf & Usterzenie_wymiary.pdf (T.C. Corke: Volume coefficients,
  V-tail Rudlicki projection, 30-60 deg spin recovery wake cone)
- Wyklad 4 & 7: Handout 4 & Handout 7 (Clearance limits: 230mm tricycle, 180mm taildragger)
"""

import math
from calculations.atmosphere import isa_atmosphere

# Corke Volume Coefficients Table across aircraft categories (Usterzenie_wymiary.pdf, p. 4)
CORKE_VOLUME_COEFFICIENTS = {
    "sailplane": {"V_H": 0.50, "V_V": 0.020, "AR_H": 7.0, "AR_V": 1.8},
    "homebuilt": {"V_H": 0.50, "V_V": 0.040, "AR_H": 4.0, "AR_V": 1.5},
    "piston_ga": {"V_H": 0.70, "V_V": 0.040, "AR_H": 4.0, "AR_V": 1.6},
    "twin_piston": {"V_H": 0.80, "V_V": 0.070, "AR_H": 4.5, "AR_V": 1.7},
    "turboprop_regional": {"V_H": 0.90, "V_V": 0.080, "AR_H": 4.5, "AR_V": 1.8},
    "jet_trainer": {"V_H": 0.70, "V_V": 0.060, "AR_H": 3.8, "AR_V": 1.4},
    "jet_fighter": {"V_H": 0.40, "V_V": 0.070, "AR_H": 3.5, "AR_V": 1.2},
    "military_transport": {"V_H": 1.00, "V_V": 0.080, "AR_H": 4.5, "AR_V": 1.7},
    "jet_transport": {"V_H": 1.00, "V_V": 0.090, "AR_H": 4.5, "AR_V": 1.8},
}

# Tail arm ratios relative to fuselage length (Corke, p. 7)
TAIL_ARM_RATIOS = {
    "nose": {"l_H_ratio": 0.60, "l_V_ratio": 0.55},
    "wing": {"l_H_ratio": 0.53, "l_V_ratio": 0.50},
    "rear": {"l_H_ratio": 0.47, "l_V_ratio": 0.45},
    "fuselage": {"l_H_ratio": 0.47, "l_V_ratio": 0.45},
}


def size_propeller_diameter(power_kw: float, blade_count: int = 2) -> float:
    """
    Sizes baseline propeller diameter in meters from engine shaft power [kW]
    using BIPOL Wyklad 5 and standard general aviation scaling:
    D_p = 0.22 * sqrt(P_kW) * (2 / blade_count)^0.25.
    """
    p_kw = max(1.0, float(power_kw))
    nb = max(2, int(blade_count))
    d2 = 0.22 * math.sqrt(p_kw)
    d_nb = d2 * ((2.0 / nb) ** 0.25)
    return round(d_nb, 3)


def calculate_propulsion_clearance(params: dict) -> dict:
    """
    Calculates propeller diameter sizing, tip Mach number, ground/fuselage clearances,
    and multi-phase propulsion efficiency curves according to Wyklad 5 and Handouts 4/5/7.

    Parameters
    ----------
    params : dict
        - engine_power_kw / power_kw: float
        - engine_type: 'prop', 'jet', or 'none'
        - n_engines: int (default 1)
        - gear_type: 'tricycle' or 'taildragger'
        - prop_rpm: float (default 2400)
        - blade_count: int (default 2)
        - cruise_speed_kmh: float (default 200)
        - cruise_speed_ms: float (optional)
        - stall_speed_kmh: float (default 90)
        - altitude_m: float (default 1000)
        - prop_shaft_height_m: float (default 1.40)
        - fuselage_radius_at_prop_m: float (default 0.60)
        - prop_axis_lateral_y_m: float (default 0.0)
        - gear_compressed_deflection_m: float (default 0.08)
        - prop_pitch_type: 'variable' or 'fixed'
        - propeller_diameter_m: float (optional override)

    Returns
    -------
    dict
    """
    engine_type = params.get("engine_type", "prop")
    if engine_type in ('none', 'jet'):
        return {
            'applicable': False,
            'note': 'Sprawdzenie śmigła nie dotyczy napędu odrzutowego ani lotu bez napędu.',
            "propeller_diameter_m": 0.0,
            "blade_count": 0,
            "disk_loading_kw_m2": 0.0,
            "helical_tip_speed_ms": 0.0,
            "tip_mach": 0.0,
            "tip_mach_passed": True,
            "ground_clearance_m": 0.50,
            "ground_clearance_req_m": 0.23,
            "ground_clearance_passed": True,
            "fuselage_clearance_m": 0.50,
            "fuselage_clearance_req_m": 0.025,
            "fuselage_clearance_passed": True,
            "efficiencies": {"eta_takeoff": 0.0, "eta_climb": 0.0, "eta_cruise": 0.0, "eta_loiter": 0.0},
            "static_thrust_n": 0.0,
        }

    power_kw = float(params.get("engine_power_kw") or params.get("power_kw") or 118.0)
    ac_type = params.get("aircraft_type", "piston_ga")
    count = params.get('n_engines', 2 if ac_type == 'turboprop_regional' else 1)
    if isinstance(count, bool) or not math.isfinite(float(count)) or float(count) < 1 or not float(count).is_integer():
        raise ValueError('Liczba silników musi być dodatnią liczbą całkowitą.')
    n_engines = int(count)
    power_per_engine_kw = power_kw / n_engines
    default_blades = 4 if ac_type == "turboprop_regional" else 2
    blade_count = int(params.get("blade_count", default_blades))
    gear_type = params.get("gear_type", "tricycle")
    rpm = float(params.get("prop_rpm", 2400.0))
    pitch_type = params.get("prop_pitch_type", "variable")
    alt_m = float(params.get("altitude_m", 1000.0))

    if "cruise_speed_ms" in params and params["cruise_speed_ms"] is not None:
        v_cr_ms = float(params["cruise_speed_ms"])
    else:
        v_cr_ms = float(params.get("cruise_speed_kmh", 220.0)) / 3.6

    # Speed of sound at cruise altitude
    atm = isa_atmosphere(alt_m)
    a_sound = atm["a"]
    n_rps = rpm / 60.0

    # 1. Propeller Diameter Sizing
    if "propeller_diameter_m" in params and params["propeller_diameter_m"]:
        d_p = float(params["propeller_diameter_m"])
    else:
        d_p = size_propeller_diameter(power_per_engine_kw, blade_count)
        # Physical aerodynamic limit: M_tip <= 0.85 constrains maximum diameter
        v_max_rot_sq = (0.84 * a_sound) ** 2 - (v_cr_ms ** 2)
        if v_max_rot_sq > 0 and n_rps > 0:
            d_p_max = math.sqrt(v_max_rot_sq) / (math.pi * n_rps)
            if d_p > d_p_max:
                d_p = d_p_max

    disk_area = (math.pi / 4.0) * (d_p ** 2)
    disk_loading = power_per_engine_kw / max(0.01, disk_area)

    # 2. Helical Tip Speed & Tip Mach (Wyklad 5)
    v_tip_rot = math.pi * n_rps * d_p
    v_tip_helical = math.sqrt((v_cr_ms ** 2) + (v_tip_rot ** 2))
    tip_mach = v_tip_helical / a_sound
    tip_mach_passed = tip_mach <= 0.85

    # 3. Clearances
    shaft_h = float(params.get("prop_shaft_height_m", 1.40))
    deflection = float(params.get("gear_compressed_deflection_m", 0.08))
    ground_clearance_m = shaft_h - (d_p / 2.0) - deflection
    ground_clearance_req_m = 0.180 if gear_type in ["taildragger", "tailwheel"] else 0.230
    ground_clearance_passed = ground_clearance_m >= ground_clearance_req_m

    y_axis = float(params.get("prop_axis_lateral_y_m", 0.0))
    fus_radius = float(params.get("fuselage_radius_at_prop_m", 0.60))
    if y_axis > 0:
        fuselage_clearance_m = (y_axis - fus_radius) - (d_p / 2.0)
    else:
        # Tractor nose propeller: radial clearance to outer cowl contour
        fuselage_clearance_m = max(0.05, (d_p / 2.0) - fus_radius)
    fuselage_clearance_req_m = max(0.025, 0.10 * d_p)
    fuselage_clearance_passed = fuselage_clearance_m >= fuselage_clearance_req_m

    # 4. Propeller Efficiencies Across Flight Phases
    if pitch_type == "fixed":
        efficiencies = {
            "eta_takeoff": 0.58,
            "eta_climb": 0.70,
            "eta_cruise": 0.81,
            "eta_loiter": 0.66,
        }
    else:  # variable / constant-speed
        efficiencies = {
            "eta_takeoff": 0.72,
            "eta_climb": 0.80,
            "eta_cruise": 0.85,
            "eta_loiter": 0.77,
        }

    # Static thrust estimation (Wyklad 5 actuator / momentum disc formula)
    rho0 = 1.225
    static_thrust_n = n_engines * ((2.0 * rho0 * disk_area) ** (1.0 / 3.0)) * ((efficiencies["eta_takeoff"] * power_per_engine_kw * 1000.0) ** (2.0 / 3.0))

    return {
        'applicable': True,
        'n_engines': n_engines,
        'power_per_engine_kw': power_per_engine_kw,
        "propeller_diameter_m": round(d_p, 3),
        "blade_count": blade_count,
        "disk_loading_kw_m2": round(disk_loading, 2),
        "helical_tip_speed_ms": round(v_tip_helical, 1),
        "tip_mach": round(tip_mach, 3),
        "tip_mach_passed": tip_mach_passed,
        "ground_clearance_m": round(ground_clearance_m, 3),
        "ground_clearance_req_m": ground_clearance_req_m,
        "ground_clearance_passed": ground_clearance_passed,
        "fuselage_clearance_m": round(fuselage_clearance_m, 3),
        "fuselage_clearance_req_m": round(fuselage_clearance_req_m, 3),
        "fuselage_clearance_passed": fuselage_clearance_passed,
        "efficiencies": efficiencies,
        "static_thrust_n": round(static_thrust_n, 1),
    }


def calculate_empennage_sizing(params: dict) -> dict:
    """
    Empennage volume sizing, layout configuration, and spin recovery assessment
    according to BIPOL I Wyklad 6, okBIPOL_1_handout_6, and Corke (Usterzenie_wymiary.pdf).

    Parameters
    ----------
    params : dict
        - S / wing_area_m2: float [m²]
        - b / wingspan_m: float [m]
        - mac / mac_m: float [m]
        - fuselage_len / length: float [m]
        - aircraft_type: str (e.g. 'piston_ga', 'turboprop_regional', 'jet_transport', etc.)
        - tail_layout: str ('conventional', 't_tail', 'cruciform', 'v_tail')
        - engine_location: str ('nose', 'wing', 'rear', 'fuselage')
        - v_h: float (optional volume coefficient override)
        - v_v: float (optional volume coefficient override)
        - v_c: float (optional canard volume coefficient)
        - ar_h: float (horizontal tail aspect ratio)
        - ar_v: float (vertical tail aspect ratio)
        - taper_h: float (horizontal tail taper ratio)
        - taper_v: float (vertical tail taper ratio)
        - elevator_chord_ratio: float (c_e / c_H, default 0.35)
        - rudder_chord_ratio: float (c_r / c_V, default 0.35)
        - h_tail_pos_z_fraction: float (z_H / h_V: 0.0=fuselage, 0.5=cruciform, 1.0=t_tail)

    Returns
    -------
    dict
    """
    # 1. Parameter extraction
    S = float(params.get("S") or params.get("wing_area_m2") or 15.0)
    b = float(params.get("b") or params.get("wingspan_m") or 10.0)
    mac = float(params.get("mac") or params.get("mac_m") or 1.5)
    l_f = float(params.get("fuselage_len") or params.get("length") or 8.0)
    ac_type = params.get("aircraft_type", "piston_ga")
    tail_layout = params.get("tail_layout", "conventional")
    eng_loc = params.get("engine_location", "nose")

    category_data = CORKE_VOLUME_COEFFICIENTS.get(ac_type, CORKE_VOLUME_COEFFICIENTS["piston_ga"])
    arm_data = TAIL_ARM_RATIOS.get(eng_loc, TAIL_ARM_RATIOS["nose"])

    # Tail moment arms (Corke, p. 7)
    l_H = float(params.get("l_H") or params.get("_tail_arm_h") or (arm_data["l_H_ratio"] * l_f))
    l_V = float(params.get("l_V") or params.get("_tail_arm_v") or (arm_data["l_V_ratio"] * l_f))

    # Base volume coefficients
    V_H_base = float(params.get("v_h") or category_data["V_H"])
    V_V_base = float(params.get("v_v") or category_data["V_V"])

    # Layout adjustments: T-tail end-plate effect reduces required V_V by 5% (Corke, p. 6)
    if tail_layout == "t_tail":
        V_V = round(V_V_base * 0.95, 4)
        z_frac_default = 1.0
    elif tail_layout == "cruciform":
        V_V = V_V_base
        z_frac_default = 0.50
    else:
        V_V = V_V_base
        z_frac_default = 0.22

    V_H = V_H_base
    h_tail_pos_z_fraction = float(params.get("h_tail_pos_z_fraction", z_frac_default))

    # Tail areas: S_H = V_H * S * mac / l_H, S_V = V_V * S * b / l_V
    S_H = (V_H * S * mac) / max(0.1, l_H)
    S_V = (V_V * S * b) / max(0.1, l_V)

    ar_h = float(params.get("ar_h") or category_data["AR_H"])
    ar_v = float(params.get("ar_v") or category_data["AR_V"])
    taper_h = float(params.get("taper_h", 0.60))
    taper_v = float(params.get("taper_v", 0.65))

    # Geometric planforms
    b_H = math.sqrt(S_H * ar_h)
    cr_H = (2.0 * S_H) / (b_H * (1.0 + taper_h))
    ct_H = taper_h * cr_H
    mac_H = (2.0 / 3.0) * cr_H * ((1.0 + taper_h + taper_h ** 2) / (1.0 + taper_h))

    h_V = math.sqrt(S_V * ar_v)
    cr_V = (2.0 * S_V) / (h_V * (1.0 + taper_v))
    ct_V = taper_v * cr_V
    mac_V = (2.0 / 3.0) * cr_V * ((1.0 + taper_v + taper_v ** 2) / (1.0 + taper_v))

    # V-Tail Rudlicki calculations (Corke, p. 6 & 9)
    v_tail_data = None
    if tail_layout == "v_tail":
        gamma_rad = math.atan(math.sqrt(S_V / S_H))
        gamma_deg = math.degrees(gamma_rad)
        s_vtail_total = S_H + S_V
        s_panel = s_vtail_total / 2.0
        s_h_proj = s_vtail_total * (math.cos(gamma_rad) ** 2)
        s_v_proj = s_vtail_total * (math.sin(gamma_rad) ** 2)
        v_tail_data = {
            "dihedral_deg": round(gamma_deg, 2),
            "S_vtail_total": round(s_vtail_total, 3),
            "S_vtail_panel": round(s_panel, 3),
            "S_H_proj": round(s_h_proj, 3),
            "S_V_proj": round(s_v_proj, 3),
            "interference_factor_Q": 1.03,
            "wetted_area_savings_pct": 12.5,
        }

    # Canard sizing (Corke, p. 5)
    canard_data = None
    if params.get("is_canard", False):
        V_C = float(params.get("v_c", 0.11))
        l_C = float(params.get("l_c", 0.35 * l_f))
        S_C = (V_C * S * mac) / max(0.1, l_C)
        canard_data = {"S_C": round(S_C, 3), "l_C": round(l_C, 3), "V_C": V_C}

    # 2. Rudder Spin Recovery Unshielded Area (Corke / Raymer Criterion)
    # Wyklad 6, p. 3 & Corke, p. 10: 30° - 60° Stall Wake Cone
    rudder_chord_ratio = float(params.get("rudder_chord_ratio", 0.35))
    elevator_chord_ratio = float(params.get("elevator_chord_ratio", 0.35))

    # Reference waterlines:
    # Vertical fin root at z = 0, tip at z = h_V.
    # Horizontal tail placed at z_H = h_tail_pos_z_fraction * h_V.
    z_H = h_tail_pos_z_fraction * h_V

    # Fin leading edge sweep angle (typically 35 deg):
    sweep_v_rad = math.radians(float(params.get("sweep_v_deg", 35.0)))
    sweep_h_rad = math.radians(float(params.get("sweep_h_deg", 10.0)))

    # Stabilizer root chord LE/TE at z_H
    x_le_v_root = 0.0
    x_le_v_zh = x_le_v_root + z_H * math.tan(sweep_v_rad)
    c_v_zh = cr_V - (z_H / max(1e-4, h_V)) * (cr_V - ct_V)
    x_hinge_zh = x_le_v_zh + (1.0 - rudder_chord_ratio) * c_v_zh

    if "x_le_h_offset" in params:
        x_le_h = float(params["x_le_h_offset"])
        x_te_h = x_le_h + cr_H
    else:
        # Standard layout: horizontal tail trailing edge placed forward of rudder hinge line (Raymer/Corke)
        x_hinge_root = (1.0 - rudder_chord_ratio) * cr_V
        if tail_layout == "t_tail":
            x_te_h = x_hinge_zh
        else:
            x_te_h = x_hinge_root - 0.35 * cr_V
        x_le_h = x_te_h - cr_H

    # Slice integration of rudder area and shielded wake cone across vertical fin height
    n_slices = 50
    dz = h_V / n_slices
    total_rudder_area = 0.0
    unshielded_rudder_area = 0.0

    # Wake cone angles relative to horizontal:
    # 60 deg upper forward cone, 30 deg lower aft cone (Corke, p. 10)
    tan_60 = math.tan(math.radians(60.0))
    tan_30 = math.tan(math.radians(30.0))

    for i in range(n_slices):
        z_mid = (i + 0.5) * dz
        eta_z = z_mid / h_V
        # Chord of vertical fin at z_mid
        c_v_z = cr_V - eta_z * (cr_V - ct_V)
        # Leading and trailing edges of vertical fin at z_mid
        x_le_v_z = x_le_v_root + z_mid * math.tan(sweep_v_rad)
        x_te_v_z = x_le_v_z + c_v_z

        # Rudder chord and bounds
        c_rudder_z = rudder_chord_ratio * c_v_z
        x_hinge_z = x_te_v_z - c_rudder_z

        rudder_slice_area = c_rudder_z * dz
        total_rudder_area += rudder_slice_area

        if tail_layout == "t_tail" or z_mid < z_H:
            # Below the horizontal tail, the rudder is entirely clear of the stall wake cone!
            unshielded_slice_area = rudder_slice_area
        else:
            # At or above the horizontal tail, evaluate wake cone intersection
            delta_z = z_mid - z_H
            x_wake_fwd = x_le_h + (delta_z / tan_60)
            x_wake_aft = x_te_h + (delta_z / tan_30)

            # Intersection between rudder chord [x_hinge_z, x_te_v_z] and wake [x_wake_fwd, x_wake_aft]
            overlap_start = max(x_hinge_z, x_wake_fwd)
            overlap_end = min(x_te_v_z, x_wake_aft)
            shielded_chord = max(0.0, overlap_end - overlap_start)
            unshielded_chord = max(0.0, c_rudder_z - shielded_chord)
            unshielded_slice_area = unshielded_chord * dz

        unshielded_rudder_area += unshielded_slice_area

    urda = unshielded_rudder_area / max(1e-4, total_rudder_area)
    urdv = (unshielded_rudder_area * l_V) / (S * b)

    if urda >= 0.50:
        spin_verdict = "EXCELLENT"
    elif urda >= 0.40:
        spin_verdict = "GOOD"
    elif urda >= 0.30:
        spin_verdict = "ACCEPTABLE"
    else:
        spin_verdict = "UNACCEPTABLE"

    spin_passed = urda >= 0.30

    return {
        "S_H": round(S_H, 3),
        "S_V": round(S_V, 3),
        "l_H": round(l_H, 3),
        "l_V": round(l_V, 3),
        "V_H": round(V_H, 3),
        "V_V": round(V_V, 3),
        "rudder_spin_unshielded_area": round(unshielded_rudder_area, 3),
        "rudder_total_area": round(total_rudder_area, 3),
        "rudder_unshielded_fraction": round(urda, 3),
        "tail_volume_spin_index": round(urdv, 4),
        "spin_recovery_verdict": spin_verdict,
        "spin_recovery_passed": spin_passed,
        "tail_layout": tail_layout,
        "v_tail_data": v_tail_data,
        "canard_data": canard_data,
        "dimensions": {
            "b_H": round(b_H, 2),
            "cr_H": round(cr_H, 2),
            "ct_H": round(ct_H, 2),
            "mac_H": round(mac_H, 2),
            "sweep_H_deg": float(params.get("sweep_h_deg", 10.0)),
            "h_V": round(h_V, 2),
            "cr_V": round(cr_V, 2),
            "ct_V": round(ct_V, 2),
            "mac_V": round(mac_V, 2),
            "sweep_V_deg": float(params.get("sweep_v_deg", 35.0)),
        },
    }
