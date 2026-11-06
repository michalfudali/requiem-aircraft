"""Shared BIPOL mass sizing and parametric component mass estimation engine.

Implements:
- Class-II parametric component mass estimation based on Daniel P. Raymer
  ("Aircraft Design: A Conceptual Approach", Ch. 15 Weights) and Warsaw University
  of Technology (MEiL PW) course materials ("Analiza_masowa.pdf", pp. 1, 5, 6, 7).
- Advanced composites and structural technology correction factors (Table 15.4).
- Dual-compatible component breakdown dictionaries ensuring machine-precision mass conservation.
- Graceful statistical fallback when geometry is absent.
"""
import math
from typing import Any, Dict, Optional, Union

from calculations.bipol1 import mission_model, solve_mass
from calculations.polish_law import TURBINE_TYPES, is_unmanned


# ---------------------------------------------------------------------------
# Authoritative Unit Conversion Constants (IEEE-754 double precision)
# ---------------------------------------------------------------------------
KG_TO_LB = 1.0 / 0.45359237
LB_TO_KG = 0.45359237
M_TO_FT = 1.0 / 0.3048
FT_TO_M = 0.3048
M2_TO_FT2 = (1.0 / 0.3048) ** 2
FT2_TO_M2 = 0.3048 ** 2
PA_TO_PSF = 1.0 / 47.88026


# ---------------------------------------------------------------------------
# Statistical Breakdown Shares Baseline (Fallback for conceptual sizing)
# ---------------------------------------------------------------------------
BREAKDOWN_SHARES = {
    "piston_ga": {
        "wing": 0.28, "fuselage": 0.24, "tail": 0.05, "gear": 0.12,
        "propulsion": 0.21, "systems": 0.10,
    },
    "turboprop_regional": {
        "wing": 0.25, "fuselage": 0.23, "tail": 0.06, "gear": 0.11,
        "propulsion": 0.22, "systems": 0.13,
    },
    "jet_business": {
        "wing": 0.26, "fuselage": 0.24, "tail": 0.06, "gear": 0.10,
        "propulsion": 0.19, "systems": 0.15,
    },
    "jet_transport": {
        "wing": 0.27, "fuselage": 0.25, "tail": 0.05, "gear": 0.11,
        "propulsion": 0.18, "systems": 0.14,
    },
    "uav": {
        "wing": 0.30, "fuselage": 0.22, "tail": 0.06, "gear": 0.08,
        "propulsion": 0.20, "systems": 0.14,
    },
    "glider": {
        "wing": 0.35, "fuselage": 0.30, "tail": 0.08, "gear": 0.12,
        "propulsion": 0.00, "systems": 0.15,
    },
}


class ComponentBreakdown(dict):
    """Dual-compatible detailed component breakdown dictionary.

    Exposes the 11 detailed Raymer parametric components as dictionary items.
    Provides backward-compatible alias access for legacy macro keys:
    'm_wing', 'm_fuselage', 'm_tail', 'm_gear', 'm_propulsion', 'm_systems',
    as well as aggregate names ('tail', 'gear', 'systems').
    """

    _ALIASES = {
        "m_wing": lambda d: d["wing"],
        "m_fuselage": lambda d: d["fuselage"],
        "m_tail": lambda d: d["horizontal_tail"] + d["vertical_tail"],
        "m_gear": lambda d: d["landing_gear"],
        "m_propulsion": lambda d: d["propulsion"] + d["fuel_system"],
        "m_systems": lambda d: (
            d["flight_controls"] + d["avionics"] + d["electrical"] + d["furnishings"]
        ),
        "tail": lambda d: d["horizontal_tail"] + d["vertical_tail"],
        "gear": lambda d: d["landing_gear"],
        "systems": lambda d: (
            d["flight_controls"] + d["avionics"] + d["electrical"] + d["furnishings"]
        ),
    }

    def __getitem__(self, key: str) -> Any:
        if super().__contains__(key):
            return super().__getitem__(key)
        if key in self._ALIASES:
            return self._ALIASES[key](self)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        return super().__contains__(key) or (isinstance(key, str) and key in self._ALIASES)


class MacroBreakdown(dict):
    """Dual-compatible macro breakdown dictionary for calculate_mass_sizing.

    Primary keys: 'm_wing', 'm_fuselage', 'm_tail', 'm_gear', 'm_propulsion', 'm_systems'.
    The sum of values strictly satisfies: math.fsum(values()) == m_empty to within 1e-12.
    Provides alias access for unprefixed keys: 'wing', 'fuselage', 'tail', etc.
    """

    _ALIASES = {
        "wing": "m_wing",
        "fuselage": "m_fuselage",
        "tail": "m_tail",
        "gear": "m_gear",
        "propulsion": "m_propulsion",
        "systems": "m_systems",
    }

    def __getitem__(self, key: str) -> Any:
        if super().__contains__(key):
            return super().__getitem__(key)
        if key in self._ALIASES and super().__contains__(self._ALIASES[key]):
            return super().__getitem__(self._ALIASES[key])
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        return super().__contains__(key) or (
            isinstance(key, str) and key in self._ALIASES and self._ALIASES[key] in self
        )


def corke_climb_fuel_fraction(engine_type: str, h_cr_m: float, v_cr_ms: float) -> float:
    p = dict(engine_type=engine_type, cruise_altitude_m=h_cr_m, cruise_speed_kmh=v_cr_ms * 3.6)
    return mission_model(p, 15)[1]["corke"]["fraction"]


def estimate_component_masses(
    m0_or_m_empty: Union[float, int, dict],
    params_or_ac_type: Union[dict, str, None] = None,
    geom: Optional[dict] = None,
    flight_envelope: Optional[dict] = None,
    **kwargs: Any,
) -> dict:
    """Estimate aircraft component mass breakdown using Raymer GA Class-II parametric equations.

    Traceable to: MEiL PW "Analiza_masowa.pdf", pp. 1, 5, 6, 7 and Raymer Ch. 15.

    Parameters:
      m0_or_m_empty: Maximum Takeoff Weight (m0) [kg] or empty weight (for legacy audit signature),
                     or full parameters dictionary.
      params_or_ac_type: Project configuration dictionary or aircraft type string.
      geom: Optional dictionary of geometric dimensions (wing, tails, fuselage, landing gear).
      flight_envelope: Optional flight envelope results (n_ult, n_pos, q_max_pa).
      **kwargs: Additional optional parameters.

    Returns:
      Dictionary containing m_empty, m_structure, m_propulsion, m_systems,
      detailed breakdown dictionary, fractional percentages, and estimation method.
    """
    if isinstance(m0_or_m_empty, dict) and params_or_ac_type is None:
        params = dict(m0_or_m_empty)
        m0 = float(params.get("m0") or params.get("mtow") or params.get("MTOW", 1000.0))
    elif isinstance(params_or_ac_type, str):
        ac_type = params_or_ac_type
        m_empty_input = float(m0_or_m_empty)
        if m_empty_input <= 0.0:
            raise ValueError("Aircraft mass must be positive.")
        m0 = m_empty_input / 0.62
        params = {"aircraft_type": ac_type, "m_empty": m_empty_input}
    else:
        m0 = float(m0_or_m_empty)
        params = dict(params_or_ac_type) if params_or_ac_type is not None else {}

    if m0 <= 0.0:
        raise ValueError("Aircraft mass m0 must be positive.")

    for k, v in kwargs.items():
        if k not in params:
            params[k] = v

    if geom is None:
        geom = params.get("geometry") or params.get("geom")
    if flight_envelope is None:
        flight_envelope = params.get("flight_envelope") or params.get("envelope")

    # Physical validation of geometric inputs if provided
    if geom and "wing" in geom and "S" in geom["wing"]:
        if float(geom["wing"]["S"]) <= 0.0:
            raise ValueError("Wing area must be positive.")
    if "wing_area_m2" in params and params["wing_area_m2"] is not None and float(params["wing_area_m2"]) < 0.0:
        raise ValueError("Wing area must be positive.")
    if "S" in params and params["S"] is not None and float(params["S"]) < 0.0:
        raise ValueError("Wing area must be positive.")

    # Determine whether geometric parameters are sufficient for Raymer parametric equations
    has_geom = False
    s_w_m2 = None
    if geom and "wing" in geom and "S" in geom["wing"] and float(geom["wing"]["S"]) > 0.0:
        s_w_m2 = float(geom["wing"]["S"])
        has_geom = True
    elif "wing_area_m2" in params and params["wing_area_m2"] is not None and float(params["wing_area_m2"]) > 0.0:
        s_w_m2 = float(params["wing_area_m2"])
        has_geom = True
    elif "S" in params and params["S"] is not None and float(params["S"]) > 0.0:
        s_w_m2 = float(params["S"])
        has_geom = True

    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = params.get("engine_type", "prop")
    wing_config = params.get("wing_config", "low")
    is_glider = (
        (ac_type in ("glider", "motoglider") and engine_type == "none")
        or (engine_type == "none")
        or (ac_type == "glider")
    )
    unmanned = is_unmanned(params) or ac_type == "uav" or (
        int(params.get("n_pax", 0)) == 0 and int(params.get("n_crew", 0)) == 0 and not is_glider
    )

    # -----------------------------------------------------------------------
    # Branch 1: Statistical Fallback (when geometry is not provided)
    # -----------------------------------------------------------------------
    if not has_geom:
        shares = dict(BREAKDOWN_SHARES.get(ac_type, BREAKDOWN_SHARES["piston_ga"]))
        if is_glider:
            remaining = 1.0 - shares["propulsion"]
            shares = {k: (0.0 if k == "propulsion" else v / remaining) for k, v in shares.items()}
        if wing_config == "braced_high" or params.get("wing_braced"):
            shares["wing"] *= 0.82
            shares["fuselage"] = 1.0 - sum(v for k, v in shares.items() if k != "fuselage")

        m_empty_target = float(params.get("m_empty", kwargs.get("m_empty", m0 * 0.62)))

        m_w = m_empty_target * shares["wing"]
        m_ht = m_empty_target * shares["tail"] * 0.65
        m_vt = m_empty_target * shares["tail"] * 0.35
        m_g = m_empty_target * shares["gear"]

        if is_glider:
            m_prop = 0.0
            m_fs = 0.0
        else:
            m_prop = m_empty_target * shares["propulsion"] * 0.85
            m_fs = m_empty_target * shares["propulsion"] * 0.15

        if unmanned:
            m_fc = m_empty_target * shares["systems"] * (1.0 / 3.0)
            m_av = m_empty_target * shares["systems"] * (1.0 / 3.0)
            m_el = m_empty_target * shares["systems"] * (1.0 / 3.0)
            m_furn = 0.0
        else:
            m_fc = m_empty_target * shares["systems"] * 0.25
            m_av = m_empty_target * shares["systems"] * 0.25
            m_el = m_empty_target * shares["systems"] * 0.25
            m_furn = m_empty_target * shares["systems"] * 0.25

        # Close residual into fuselage for exact machine precision conservation
        other_sum = m_w + m_ht + m_vt + m_g + m_prop + m_fs + m_fc + m_av + m_el + m_furn
        m_f = m_empty_target - other_sum

        m_struct = m_w + m_f + m_ht + m_vt + m_g
        m_prop_group = m_prop + m_fs
        m_sys = m_fc + m_av + m_el + m_furn
        m_empty = m_struct + m_prop_group + m_sys

        bd = ComponentBreakdown({
            "wing": m_w,
            "fuselage": m_f,
            "horizontal_tail": m_ht,
            "vertical_tail": m_vt,
            "landing_gear": m_g,
            "propulsion": m_prop,
            "fuel_system": m_fs,
            "flight_controls": m_fc,
            "avionics": m_av,
            "electrical": m_el,
            "furnishings": m_furn,
        })
        pcts = {k: (100.0 * bd[k] / m_empty if m_empty > 0 else 0.0) for k in bd}

        return {
            "m_empty": m_empty,
            "m_structure": m_struct,
            "m_propulsion": m_prop_group,
            "m_systems": m_sys,
            "breakdown": bd,
            "percentages": pcts,
            "method": "statistical_fallback",
        }

    # -----------------------------------------------------------------------
    # Branch 2: Raymer General Aviation Parametric Equations
    # -----------------------------------------------------------------------
    # Structural technology multipliers (Table 15.4)
    tech = str(params.get("technology", params.get("structural_material", "metallic"))).lower()
    wing_braced = bool(params.get("wing_braced", False) or params.get("wing_config") == "braced_high")

    k_wing = 1.0
    k_tail = 1.0
    k_fus = 1.0
    k_gear = 1.0

    if tech in ("advanced_composites", "composite", "composites"):
        k_wing *= 0.85
        k_tail *= 0.83
        k_fus *= 0.90
        k_gear *= 0.95

    if wing_braced:
        k_wing *= 0.82

    fus_mat = str(params.get("fuselage_material", "")).lower()
    if fus_mat == "wood" or tech == "wood":
        k_fus = 1.60
    elif fus_mat in ("steel_tube", "welded_steel") or tech in ("steel_tube", "welded_steel"):
        k_fus = 1.80
    elif bool(params.get("is_flying_boat", False)) or str(params.get("fuselage_type", "")).lower() == "flying_boat":
        k_fus = 1.25

    # Design gross weight [lb]
    w_dg = m0 * KG_TO_LB

    # Ultimate structural maneuvering load factor Nz = 1.5 * n_pos
    final_limits = (flight_envelope or {}).get('limits',{})
    ultimate_values = [abs(float(final_limits[k])) for k in ('n_ult_pos','n_ult_neg') if final_limits.get(k) is not None]
    if ultimate_values:
        n_z = max(ultimate_values)
        load_basis = 'final_envelope_limits'
    elif flight_envelope and "n_ult" in flight_envelope:
        n_z = float(flight_envelope["n_ult"])
        load_basis = 'explicit_ultimate'
    elif flight_envelope and "n_pos" in flight_envelope:
        n_z = 1.5 * float(flight_envelope["n_pos"])
    elif "n_ult" in params:
        n_z = float(params["n_ult"])
    elif "n_pos" in params:
        n_z = 1.5 * float(params["n_pos"])
    else:
        n_z = 5.7  # Standard CS-23 normal/commuter default: 1.5 * 3.8
    if not ultimate_values and not (flight_envelope and 'n_ult' in flight_envelope):
        load_basis = 'limit_factor_or_legacy_default'

    # Dynamic pressure at cruise speed q [psf]
    if flight_envelope and "q_max_pa" in flight_envelope:
        q_pa = float(flight_envelope["q_max_pa"])
    elif "q_max_pa" in params:
        q_pa = float(params["q_max_pa"])
    elif "cruise_speed_kmh" in params and "cruise_altitude_m" in params:
        from calculations.atmosphere import isa_atmosphere
        h = float(params.get("cruise_altitude_m", 2500.0))
        v_ms = float(params.get("cruise_speed_kmh", 225.0)) / 3.6
        atm = isa_atmosphere(h)
        rho = atm.get("rho", atm.get("density", 1.225))
        q_pa = 0.5 * rho * (v_ms ** 2)
    else:
        q_pa = 1869.0
    q_psf = max(1.0, q_pa * PA_TO_PSF)

    # 1. Wing Structural Weight (lbs)
    s_w_ft2 = s_w_m2 * M2_TO_FT2
    wing_geom = geom.get("wing", {}) if geom else {}
    ar = float(wing_geom.get("AR", params.get("aspect_ratio", 7.5)))
    sweep_25 = math.radians(float(wing_geom['sweep_deg'])) if 'sweep_deg' in wing_geom else float(
        wing_geom.get(
            "sweep_25",
            wing_geom.get(
                "sweep",
                math.radians(float(params.get("sweep_quarter_deg", params.get("sweep_deg", 0.0)))),
            ),
        )
    )
    cos_sweep = max(0.1, math.cos(sweep_25))
    taper = max(0.01, float(wing_geom.get('eta',wing_geom.get("taper_ratio", params.get("taper_ratio", 0.65)))))
    thickness = next((source[key] for source in (wing_geom,params)
                      for key in ('tc_ratio','thickness_ratio','tc') if source.get(key) is not None),.15)
    tc = max(.01,float(thickness))

    # Fuel weight in wing tanks [lb] (with singularity guard max(1.0, W_fw))
    if is_glider:
        w_fw = 1.0
    else:
        m_fuel_w = float(params.get("m_fuel_wing", params.get("m_fuel", 120.0)))
        w_fw = max(1.0, m_fuel_w * KG_TO_LB)

    w_wing = (
        0.036
        * (s_w_ft2 ** 0.758)
        * (w_fw ** 0.0035)
        * ((ar / (cos_sweep ** 2)) ** 0.6)
        * (q_psf ** 0.006)
        * (taper ** 0.04)
        * (((100.0 * tc) / cos_sweep) ** -0.3)
        * ((n_z * w_dg) ** 0.49)
        * k_wing
    )
    m_wing = w_wing * LB_TO_KG

    # Wing span [m]
    b_m = float(wing_geom.get("b", math.sqrt(s_w_m2 * ar)))

    # 2. Horizontal Tail Structural Weight (lbs)
    ht_geom = geom.get("horizontal_tail", {}) if geom else {}
    s_ht_m2 = float(ht_geom.get("S_h", ht_geom.get("S", params.get("s_ht", 0.20 * s_w_m2))))
    s_ht_ft2 = max(0.01, s_ht_m2 * M2_TO_FT2)
    ar_ht = max(0.1, float(ht_geom.get("AR_h", params.get("ar_ht", 4.0))))
    taper_ht = max(0.01, float(ht_geom.get("taper_ratio", 0.60)))
    tc_ht = max(0.01, float(ht_geom.get("thickness_ratio", 0.12)))
    sweep_ht = float(ht_geom.get("sweep", math.radians(float(params.get("sweep_ht_deg", 0.0)))))
    cos_sweep_ht = max(0.1, math.cos(sweep_ht))

    w_ht = (
        0.016
        * ((n_z * w_dg) ** 0.414)
        * (q_psf ** 0.168)
        * (s_ht_ft2 ** 0.896)
        * (((100.0 * tc_ht) / cos_sweep_ht) ** -0.12)
        * ((ar_ht / (cos_sweep_ht ** 2)) ** 0.043)
        * (taper_ht ** -0.02)
        * k_tail
    )
    m_horizontal_tail = w_ht * LB_TO_KG

    # 3. Vertical Tail Structural Weight (lbs)
    vt_geom = geom.get("vertical_tail", {}) if geom else {}
    s_vt_m2 = float(vt_geom.get("S_v", vt_geom.get("S", params.get("s_vt", 0.10 * s_w_m2))))
    s_vt_ft2 = max(0.01, s_vt_m2 * M2_TO_FT2)
    ar_vt = max(0.1, float(vt_geom.get("AR_v", params.get("ar_vt", 1.5))))
    taper_vt = max(0.01, float(vt_geom.get("taper_ratio", 0.65)))
    tc_vt = max(0.01, float(vt_geom.get("thickness_ratio", 0.12)))
    sweep_vt = float(vt_geom.get("sweep", math.radians(float(params.get("sweep_vt_deg", 0.0)))))
    cos_sweep_vt = max(0.1, math.cos(sweep_vt))
    ht_over_hv = 1.0 if (params.get("tail_type") == "t_tail" or params.get("is_t_tail", False)) else 0.0

    w_vt = (
        0.073
        * (1.0 + 0.2 * ht_over_hv)
        * ((n_z * w_dg) ** 0.376)
        * (q_psf ** 0.122)
        * (s_vt_ft2 ** 0.873)
        * (((100.0 * tc_vt) / cos_sweep_vt) ** -0.49)
        * ((ar_vt / (cos_sweep_vt ** 2)) ** 0.357)
        * (taper_vt ** 0.039)
        * k_tail
    )
    m_vertical_tail = w_vt * LB_TO_KG

    # 4. Fuselage Structural Weight (lbs)
    fus_geom = geom.get("fuselage", {}) if geom else {}
    l_f_m = float(fus_geom.get("length", params.get("fuselage_length_m", max(5.5, 0.72 * b_m))))
    d_f_m = float(fus_geom.get("diameter", params.get("fuselage_diameter_m", 1.20)))
    s_f_m2 = float(fus_geom.get("S_wet", params.get("fuselage_swet_m2", 0.75 * math.pi * d_f_m * l_f_m)))
    s_f_ft2 = max(1.0, s_f_m2 * M2_TO_FT2)

    l_t_m = float(ht_geom.get('l_h',ht_geom.get("arm", params.get("l_h", 0.55 * l_f_m))))
    l_t_ft = max(3.0, l_t_m * M_TO_FT)
    l_over_d = max(1.0, l_f_m / max(0.1, d_f_m))

    if bool(params.get("is_pressurized", False)):
        d_ft = d_f_m * M_TO_FT
        l_ft = l_f_m * M_TO_FT
        v_pr = 0.6 * (math.pi * (d_ft ** 2) / 4.0) * l_ft
        p_delta = float(params.get("cabin_pressure_diff_psi", 8.0))
        w_press = 11.9 + ((v_pr * p_delta) ** 0.271)
    else:
        w_press = 0.0

    w_fus = (
        (
            0.052
            * (s_f_ft2 ** 1.086)
            * ((n_z * w_dg) ** 0.177)
            * (l_t_ft ** -0.051)
            * (l_over_d ** -0.072)
            * (q_psf ** 0.241)
            + w_press
        )
        * k_fus
    )
    m_fuselage = w_fus * LB_TO_KG

    # 5. Landing Gear Structural Weight (lbs)
    gear_geom = geom.get("gear", {}) if geom else {}
    l_m_m = float(gear_geom.get("length_main_m", params.get("gear_length_main_m", 0.71)))
    l_n_m = float(gear_geom.get("length_nose_m", params.get(
        "gear_length_nose_m", 0.25 if params.get("landing_gear_type") == "tailwheel" else 0.51)))
    l_m_ft = max(0.5, l_m_m * M_TO_FT)
    l_n_ft = max(0.5, l_n_m * M_TO_FT)

    n_l = float(params.get("n_gear_ult", 1.5 * float(params.get("n_gear", 2.7))))
    w_l = w_dg  # For GA conceptual sizing, landing weight equals MTOW

    w_mlg = 0.095 * ((n_l * w_l) ** 0.768) * (l_m_ft ** 0.409) * k_gear
    w_nlg = 0.125 * ((n_l * w_l) ** 0.566) * (l_n_ft ** 0.845) * k_gear
    w_gear = w_mlg + w_nlg
    m_landing_gear = w_gear * LB_TO_KG

    # 6. Propulsion & Fuel System Group
    if is_glider:
        w_installed_engine = 0.0
        w_fuel_system = 0.0
        m_propulsion = 0.0
        m_fuel_system = 0.0
    else:
        n_en = max(1, int(params.get("n_engines", 1)))
        if "engine_dry_weight_lb" in params:
            w_en = float(params["engine_dry_weight_lb"])
        elif "engine_mass_kg" in params:
            w_en = (float(params["engine_mass_kg"]) * KG_TO_LB) / n_en
        elif float(params.get("engine_power_kw") or params.get("power_kw") or 0.0) > 0.0:
            p_kw = float(params.get("engine_power_kw") or params.get("power_kw"))
            w_en = (engine_dry_mass_kg(p_kw, ac_type) * KG_TO_LB) / n_en
        else:
            w_en = (280.0 * (w_dg / (1150.0 * KG_TO_LB))) / n_en

        w_installed_engine = 2.575 * (w_en ** 0.922) * n_en
        m_propulsion = w_installed_engine * LB_TO_KG

        if "fuel_capacity_gal" in params:
            v_t_gal = float(params["fuel_capacity_gal"])
        elif "v_t_gal" in params:
            v_t_gal = float(params["v_t_gal"])
        else:
            m_fuel = float(params.get("m_fuel", 120.0))
            density = float(params.get('fuel_density_kg_l',.72))
            if not math.isfinite(density) or density<=0:
                raise ValueError('Gęstość paliwa do wymiarowania instalacji musi być dodatnia i skończona.')
            v_t_gal = max(1.0, m_fuel / density / 3.785411784)
        v_i_over_v_t = float(params.get("integral_tank_ratio", 1.0))
        n_t = max(1, int(params.get("n_fuel_tanks", 2)))

        w_fuel_system = (
            2.49
            * (v_t_gal ** 0.726)
            * ((1.0 / (1.0 + v_i_over_v_t)) ** 0.363)
            * (n_t ** 0.242)
            * (n_en ** 0.157)
        )
        m_fuel_system = w_fuel_system * LB_TO_KG

    # 7. Secondary Systems & Equipment Group
    l_fus_ft = l_f_m * M_TO_FT
    b_span_ft = b_m * M_TO_FT

    w_fc = (
        0.053
        * (l_fus_ft ** 1.536)
        * (b_span_ft ** 0.371)
        * (((n_z * w_dg) / 10000.0) ** 0.80)
    )
    m_flight_controls = w_fc * LB_TO_KG

    w_uav = float(params.get("m_avionics_uninstalled_lb", params.get(
        "m_avionics_uninstalled", 10.0 if ac_type in ("glider", "motoglider") else 50.0)))
    w_av = 2.117 * (w_uav ** 0.933)
    m_avionics = w_av * LB_TO_KG

    w_fs_for_el = w_fuel_system if not is_glider else 0.0
    w_el = 12.57 * ((w_fs_for_el + w_av) ** 0.51)
    m_electrical = w_el * LB_TO_KG

    if unmanned:
        m_furnishings = 0.0
    else:
        n_pax = int(params.get("n_pax", 3))
        n_crew = int(params.get("n_crew", 1))
        n_seats = max(1, n_pax + n_crew)
        w_furn = max(n_seats * 12.0, 0.0582 * w_dg - 65.0)
        m_furnishings = w_furn * LB_TO_KG

    # Aggregates and Totals
    m_structure = m_wing + m_horizontal_tail + m_vertical_tail + m_fuselage + m_landing_gear
    m_propulsion_group = m_propulsion + m_fuel_system
    m_systems = m_flight_controls + m_avionics + m_electrical + m_furnishings
    m_empty = m_structure + m_propulsion_group + m_systems

    bd = ComponentBreakdown({
        "wing": m_wing,
        "fuselage": m_fuselage,
        "horizontal_tail": m_horizontal_tail,
        "vertical_tail": m_vertical_tail,
        "landing_gear": m_landing_gear,
        "propulsion": m_propulsion,
        "fuel_system": m_fuel_system,
        "flight_controls": m_flight_controls,
        "avionics": m_avionics,
        "electrical": m_electrical,
        "furnishings": m_furnishings,
    })
    pcts = {k: (100.0 * bd[k] / m_empty if m_empty > 0 else 0.0) for k in bd}

    return {
        "m_empty": m_empty,
        "m_structure": m_structure,
        "m_propulsion": m_propulsion_group,
        "m_systems": m_systems,
        "breakdown": bd,
        "percentages": pcts,
        "method": "raymer_ga_parametric",
        "reference": 'Analiza_masowa.pdf, s.5: General-Aviation Weights; s.6–7: jednostki i definicje',
        "applicability": 'general_aviation_reference' if ac_type=='piston_ga' else 'class_extrapolation_requires_validation',
        "inputs": dict(m0_kg=m0,wing_area_m2=s_w_m2,aspect_ratio=ar,tc_ratio=tc,
                       sweep_quarter_rad=sweep_25,taper_ratio=taper,ultimate_load_factor=n_z,
                       ultimate_load_basis=load_basis,dynamic_pressure_pa=q_pa,
                       dynamic_pressure_psf=q_psf,fuselage_length_m=l_f_m,
                       fuselage_wetted_area_m2=s_f_m2,horizontal_tail_arm_m=l_t_m,
                       mission_fuel_mass_kg=float(params.get('m_fuel',120)),
                       engine_total_power_kw=float(params.get('engine_power_kw') or params.get('power_kw') or 0)),
    }


def engine_dry_mass_kg(power_kw: float, aircraft_type: str = "piston_ga") -> float:
    """Dry mass of the engines from their total power when no real engine has been chosen.

    Piston engines about 0,94 kg/kW (Rotax 912 UL: 56 kg, 58 kW), turboprops about 0,35 kg/kW
    (PT6A-60A: 216 kg, 783 kW). W_en of the installed-engine equation, Analiza_masowa.pdf, p. 5.
    """
    return power_kw * (0.35 if aircraft_type in TURBINE_TYPES else 0.94)


def group_masses(detail, m_empty: float):
    """Component masses that add up exactly to the empty mass of the balance (BIPOL_1, eq. 1).

    Analiza_masowa.pdf gives every component from its own dimensions, while the balance gives
    m_e from the sample. The engine is a bought unit of known mass, so the difference between
    the two goes to the airframe only. Returns the scaled components, groups and that factor.
    """
    engine = detail["propulsion"]
    airframe = sum(value for key, value in detail.items() if key != "propulsion")
    # An engine too heavy for the sample's m_e cannot stay whole: every component is scaled then.
    engine_fixed = airframe > 0.0 and engine < 0.5 * m_empty
    k_airframe = (m_empty - engine) / airframe if engine_fixed else m_empty / max(1e-9, engine + airframe)
    scaled = {key: value * (1.0 if engine_fixed and key == "propulsion" else k_airframe)
              for key, value in detail.items()}
    groups = {
        "m_wing": scaled["wing"],
        "m_tail": scaled["horizontal_tail"] + scaled["vertical_tail"],
        "m_gear": scaled["landing_gear"],
        "m_propulsion": scaled["propulsion"],
        "m_systems": (scaled["fuel_system"] + scaled["flight_controls"] + scaled["avionics"]
                      + scaled["electrical"] + scaled["furnishings"]),
    }
    groups["m_fuselage"] = m_empty - sum(groups.values())
    scaled["fuselage"] = groups["m_fuselage"]
    return scaled, MacroBreakdown(groups), k_airframe


def refine_component_allocation(mass, sizing, geometry, params, envelope):
    """Use the actual airframe, propulsion and envelope for the provisional P3 distribution.

    The independent Class-II empty mass stays visible. Scaling its groups to
    P1's empty mass supplies a conditional CG calculation, not mass substantiation.
    """
    context=dict(params,m_fuel=mass['m_fuel'])
    power_kw=None
    if params['engine_type']=='prop':
        power_kw=sizing['design_point']['power_kw']
        context['engine_power_kw']=power_kw
    estimate=estimate_component_masses(mass['m0'],context,geom=geometry,flight_envelope=envelope)
    detail=estimate['breakdown']
    scaled,groups,factor=group_masses(detail,mass['m_empty'])
    mass.update(breakdown=groups,component_masses=estimate,detailed_breakdown=detail,parametric_breakdown=detail,
                scaled_components=scaled,installed_power_kw=power_kw,
                component_closure=dict(sum_kg=estimate['m_empty'],m_empty_kg=mass['m_empty'],k_airframe=factor,
                                       n_ult=estimate['inputs']['ultimate_load_factor'],engine_kg=scaled['propulsion']),
                component_allocation=dict(basis='provisional_cg_at_p1_empty_mass',normalization_factor=factor,
                                          independent_empty_mass_kg=estimate['m_empty'],adopted_empty_mass_kg=mass['m_empty']))


def mission_loads(params: dict):
    """Parametry z liczbą osób, masa ładunku i masa załogi do bilansu masy (kg)."""
    unmanned = is_unmanned(params)
    n_pax = 0 if unmanned else int(params.get("n_pax", 4))
    n_crew = 0 if unmanned else int(params.get("n_crew", 1 if n_pax <= 4 else 2))
    payload = n_pax * (params.get("m_pax", 80) + params.get("m_bag", 0)) + params.get("m_cargo", 0)
    crew = n_crew * float(params.get("m_crew_person", 90) or 90)
    return dict(params, n_pax=n_pax, n_crew=n_crew), payload, crew


def calculate_mass_sizing(params: dict) -> dict:
    """Perform preliminary mass sizing and component mass allocation.

    Evaluates mission fuel fractions, solves for MTOW (m0) and empty weight (m_empty),
    and derives parametric component mass breakdown conforming to Raymer Class-II formulations.
    """
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = params.get("engine_type", "prop")
    wing_config = params.get("wing_config", "low")
    unmanned = is_unmanned(params)
    p, payload, crew = mission_loads(params)
    n_pax, n_crew = p["n_pax"], p["n_crew"]
    result = solve_mass(p, payload, crew)
    m_empty = result["m_empty"]
    m0 = result["m0"]

    geom = params.get("geometry") or params.get("geom")
    envelope = params.get("flight_envelope") or params.get("envelope")
    has_geom = (geom is not None) or ("wing_area_m2" in params) or ("S" in params)

    if has_geom:
        est = estimate_component_masses(m0, params, geom=geom, flight_envelope=envelope, m_empty=m_empty)
        scaled, mass_components, k_airframe = group_masses(est["breakdown"], m_empty)
    else:
        shares = dict(BREAKDOWN_SHARES.get(ac_type, BREAKDOWN_SHARES["piston_ga"]))
        if ac_type == "glider" or engine_type == "none":
            remaining = 1.0 - shares["propulsion"]
            shares = {key: (0.0 if key == "propulsion" else value / remaining) for key, value in shares.items()}
        if wing_config == "braced_high" or params.get("wing_braced"):
            shares["wing"] *= 0.82
            shares["fuselage"] = 1.0 - sum(value for key, value in shares.items() if key != "fuselage")

        m_w = m_empty * shares["wing"]
        m_t = m_empty * shares["tail"]
        m_g = m_empty * shares["gear"]
        m_p = m_empty * shares["propulsion"]
        m_s = m_empty * shares["systems"]
        m_f = m_empty - (m_w + m_t + m_g + m_p + m_s)

        mass_components = MacroBreakdown({
            "m_wing": m_w,
            "m_fuselage": m_f,
            "m_tail": m_t,
            "m_gear": m_g,
            "m_propulsion": m_p,
            "m_systems": m_s,
        })
        est = estimate_component_masses(m0, params, geom=None, flight_envelope=None, m_empty=m_empty)
        scaled, k_airframe = dict(est["breakdown"]), 1.0

    result.update(
        breakdown=mass_components,
        component_masses=est,
        detailed_breakdown=est["breakdown"],
        parametric_breakdown=est["breakdown"],
        scaled_components=scaled,
        component_closure=dict(sum_kg=est["m_empty"], m_empty_kg=m_empty, k_airframe=k_airframe, n_ult=None,
                               engine_kg=scaled["propulsion"]),
        n_pax=n_pax,
        n_crew=n_crew,
        unmanned=unmanned,
    )
    result["primary_method"] = "proportion" if result["mass_method"] == "proportions" else "iterative"
    result["mission_assumptions"]["method"] = result["primary_method"]
    result["payload_drop_kg"] = result["m_payload_dropped"]
    result["payload_remaining_kg"] = result["m_payload_landing"]
    law = result["empty_mass_law"]
    result["empty_mass_trend"] = (
        {k: law[k] for k in ("A", "C", "k_vs")}
        if law["mode"] in ("trend", "two_point")
        else None
    )
    result["sizing_methods"] = {}
    for method in ("proportion", "iterative"):
        if method == "proportion" and result["m_payload_dropped"]:
            result["sizing_methods"][method] = dict(
                applicable=False, reason="Metoda proporcji wymaga misji bez zrzutu."
            )
            continue
        r = result if method == result["primary_method"] else solve_mass(dict(p, mass_method=method), payload, crew)
        phases = {s["key"]: s["mass_end_kg"] for s in r["mission_phases"]}
        out = phases["cruise"]
        task = phases.get("task", out)
        drop = phases.get("drop", task)
        result["sizing_methods"][method] = dict(
            applicable=True,
            method=method,
            m0=r["m0"],
            m_empty=r["m_empty"],
            m_fuel=r["m_fuel"],
            m_drop=r["m_payload_dropped"],
            empty_fraction=r["empty_fraction"],
            fuel_fraction=r["fuel_fraction"],
            total_mff=r["fuel_fractions_detail"]["total_mff"],
            iterations=r["iterations"],
            residual=r["iterations"][-1]["diff"],
            residual_relative=r["mission_assumptions"]["empty_mass_residual_relative"],
            phases=dict(
                m0=r["m0"],
                m1_takeoff=phases["takeoff"],
                m2_climb=phases["climb"],
                m3_outbound=out,
                m3_post_task=task,
                m4_post_drop=drop,
                m5_return=phases.get("return", drop),
                m6_loiter=phases["loiter"],
                m7_landing=phases["landing"],
            ),
        )

    # BIPOL_1, s. 4: the same balance written out iteration by iteration for the report.
    from calculations.mass_iteration import guideline_trace

    trace_params = p
    trace_start = params.get("mass_iteration_start_kg")
    if p.get("_mission_polar") and trace_start is None:
        trace_start = 1.1 * result["m0"]
        trace_params = dict(p, _mass_trace_start_rule="1,1·m0 rozwiązania przedziałowego; odtworzenie toku obliczeń")
    result["guideline_traces"] = {
        method: guideline_trace(trace_params, payload, crew, method, trace_start)
        for method, info in result["sizing_methods"].items()
        if info["applicable"]
    }
    return result
