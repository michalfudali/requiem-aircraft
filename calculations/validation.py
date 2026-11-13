"""Wspólne wartości wejściowe i walidacja przed uruchomieniem obliczeń."""
import math
from calculations.instructor import (CRUISE_LD_FACTOR, PASSENGER_WITH_BAG_KG,
                                     FLAP_TAKEOFF_DEFLECTION_DEG, FLAP_LANDING_DEFLECTION_DEG)

NUMERIC_LIMITS = {
    'airfield_elevation_m': (-500, 6000), 'airfield_delta_t_k': (-60, 60),
    'service_ceiling_m': (0, 20000), 'ceiling_climb_rate_ms': (0, 20),
    'turbine_inlet_temp_k': (300, 3000),
    'cost_rate_rdte_per_month': (0.000001, 100000),
    'cost_rate_production_per_month': (0.000001, 100000),
    'fuel_density_kg_l': (.5, 1.0), 'engine_custom_power_kw': (0, 100000),
    'engine_custom_thrust_kn': (0, 10000), 'engine_static_thrust_kn': (0, 10000),
    'propeller_rpm': (100, 6000), 'propeller_diameter_m': (.1, 8),
    'engine_installed_mass_kg': (.001, 100000),
    'fuselage_length_m': (0, 100), 'gear_height_m': (0, 10),
    "n_pax": (0, 1000), "n_crew": (0, 20), "m_pax": (0, 500),
    "m_bag": (0, 500), "m_cargo": (0, 500000), "m_crew_person": (0, 500),
    "range_km": (0, 30000), "cruise_altitude_m": (0, 20000),
    "cruise_speed_kmh": (1, 1200), "v_stall_kmh": (30, 400),
    "takeoff_run_m": (0, 10000), "climb_rate_ms": (0, 100),
    "mu_ground": (0, 0.5),
    "takeoff_distance_m": (0, 20000), "landing_distance_m": (0, 20000),
    "aspect_ratio": (2, 35), "taper_ratio": (0, 1),
    "sweep_quarter_deg": (-30, 60), "dihedral_deg": (-15, 20),
    "cx0": (0.001, 0.3), "oswald_e": (0.1, 1),
    "cz_max_clean": (0.1, 5), "cz_max_to": (0.1, 6), "cz_max_lnd": (0.1, 7),
    "prop_efficiency": (0.1, 1), "prop_eff_to": (0.1, 1),
    "sfc": (0, 1000), "loiter_time_min": (0, 1440),
    "wingspan_m": (0, 100), "span_limit": (0, 100),
    "v_h": (0.05, 2), "v_v": (0.005, 0.3), "ar_h": (1, 12), "ar_v": (0.5, 6),
    "tc_ratio": (0.04, 0.3), "delta_cx0_flaps_to": (0, 0.5),
    "delta_cx0_flaps_lnd": (0, 0.5), "delta_cx0_gear": (0, 0.5),
    "flap_span_ratio": (0.05, 0.98), "flap_chord_ratio": (0.05, 0.50),
    "aileron_span_ratio": (0.05, 0.90), "aileron_chord_ratio": (0.05, 0.45),
    "vmo_kcas": (1, 1000), "mmo": (0.01, 2),
    "trend_count": (0, 716), "trend_nearest_count": (0, 716), "trend_engine_count": (0, 8),
    "trend_year_min": (0, 2100), "trend_year_max": (0, 2100),
    "fuel_reserve_factor": (1, 1.5), "mission_ld_factor": (0.5, 1),
    "wing_area_m2": (0, 1000), "engine_power_kw": (0, 100000),
    "break_span_ratio": (0.1, 0.9), "m_payload": (0, 500000),
    "empty_mass_fraction": (0.15, 0.95), "n_engines": (0, 8),
    "empty_mass_trend_A": (1e-6, 1e6), "empty_mass_trend_C": (-2, 2),
    "elevator_chord_ratio": (0.05, 1), "rudder_chord_ratio": (0.05, 1),
    "ce_ch": (0.05, 1), "cr_cv": (0.05, 1),
    "mass_initial_guess": (1, 1000000), "payload_drop_kg": (0, 500000),
    "mass_iteration_start_kg": (1, 1000000),
    "water_displacement_volume_m3": (0, 10000),
    "cargo_bay_length_m": (0, 100), "cargo_bay_width_m": (0, 20), "cargo_bay_height_m": (0, 20),
    "return_range_km": (0, 30000), "outbound_range_km": (0, 30000), "max_power_time_min": (0, 1440),
    "max_power_kw": (0, 1000000), "max_thrust_kn": (0, 10000), "max_power_sfc": (0.001, 1000),
    "loiter_speed_kmh": (1, 1200), "climb_start_speed_kmh": (1, 1200),
    "climb_start_altitude_m": (0, 20000), "mission_climb_rate_ms": (.05, 100),
    "corke_start_ordinate": (0.001, 1), "corke_end_ordinate": (0.001, 1),
    "sketch_swet_ratio": (1, 20), "raymer_kmax": (1, 150),
    "empty_mass_a": (0.000001, 10000), "empty_mass_c": (-2, 2),
    "mass_point_x1": (1, 1000000), "mass_point_x2": (1, 1000000),
    "mass_point_y1": (0.01, .99), "mass_point_y2": (0.01, .99),
    "takeoff_mass_fraction": (.970, .975), "landing_mass_fraction": (.970, .975),
    "cruise_ld_p4": (1, 80), "cruise_ld_p4_speed_kmh": (1, 1200), "cruise_ld_p4_altitude_m": (0, 20000),
    "tow_glider_mass_kg": (0, 2000), "tow_glider_ld": (5, 60), "tow_speed_kmh": (60, 250),
    "tow_climb_rate_ms": (0, 20), "engine_power_limit_kw": (0, 100000),
    "v_max_required_kmh": (0, 1200), "cargo_hold_density_kg_m3": (0, 2000),
    # BIPOL_2, analiza kosztów: N_P i N_am ustala się z prowadzącym.
    "cost_year": (1970, 2100), "cost_n_production": (1, 100000), "cost_n_amortization": (1, 100000),
    "cost_n_prototypes": (1, 50), "cost_profit_pct": (0, 100), "cost_qc_factor": (0.05, 0.2),
    "usd_pln": (0.5, 50), "bypass_ratio": (0, 20),
    "engine_price_usd": (0, 1e8), "avionics_price_usd": (0, 1e8),  # 0 = szacunek
    "airfoil_cz_max": (0, 4),  # 0 = nie podano (P3: Cz_max płata ze Schrenka)
}
NUMERIC_STEPS = {
    'propeller_diameter_m': .01, 'propeller_rpm': 1, 'fuselage_length_m': .01, 'gear_height_m': .01,
    'engine_installed_mass_kg': .001,
    # Aerodynamic coefficients & efficiencies
    "taper_ratio": 0.01,
    "tc_ratio": 0.005,
    "cx0": 0.001,
    "oswald_e": 0.01,
    "cz_max_clean": 0.01,
    "cz_max_to": 0.01,
    "cz_max_lnd": 0.01,
    "airfoil_cz_max": 0.01,
    "prop_efficiency": 0.01,
    "prop_eff_to": 0.01,
    "delta_cx0_flaps_to": 0.001,
    "delta_cx0_flaps_lnd": 0.001,
    "delta_cx0_gear": 0.001,
    "mu_ground": 0.005,
    "fuel_reserve_factor": 0.01,
    "mission_ld_factor": 0.01,
    "empty_mass_fraction": 0.01,
    "takeoff_mass_fraction": 0.001,
    "landing_mass_fraction": 0.001,
    "fuel_density_kg_l": 0.01,
    "mmo": 0.01,
    "cost_qc_factor": 0.01,
    "usd_pln": 0.01,
    # Volume and area ratios
    "v_h": 0.01,
    "v_v": 0.005,
    "ar_h": 0.1,
    "ar_v": 0.1,
    "aspect_ratio": 0.01,
    "flap_span_ratio": 0.01,
    "flap_chord_ratio": 0.01,
    "break_span_ratio": 0.01,
    "aileron_span_ratio": 0.01,
    "aileron_chord_ratio": 0.01,
    "elevator_chord_ratio": 0.01,
    "rudder_chord_ratio": 0.01,
    "ce_ch": 0.01,
    "cr_cv": 0.01,
    "sketch_swet_ratio": 0.05,
    "corke_start_ordinate": 0.005,
    "corke_end_ordinate": 0.005,
    "mass_point_y1": 0.01,
    "mass_point_y2": 0.01,
    # Angles
    "sweep_quarter_deg": 0.5,
    "dihedral_deg": 0.5,
    "airfield_delta_t_k": 1,
    # Dimensions & Rates
    "wingspan_m": 0.05,
    "span_limit": 0.05,
    "wing_area_m2": 0.05,
    "climb_rate_ms": 0.1,
    "ceiling_climb_rate_ms": 0.1,
    "tow_climb_rate_ms": 0.1,
    "cargo_bay_length_m": 0.05,
    "cargo_bay_width_m": 0.05,
    "cargo_bay_height_m": 0.05,
    "water_displacement_volume_m3": 0.1,
    "bypass_ratio": 0.1,
    "sfc": 0.01,
    "max_power_sfc": 0.01,
    "engine_custom_sfc": 0.01,
    "engine_custom_thrust_kn": 0.1,
    "engine_static_thrust_kn": 0.1,
    "max_thrust_kn": 0.1,
    "tow_glider_ld": 0.5,
    "raymer_kmax": 0.5,
    "cost_rate_rdte_per_month": 0.1,
    "cost_rate_production_per_month": 0.1,
    "cost_profit_pct": 0.5,
    # Integers and large units
    "m_crew_person": 0.5,
    "m_pax": 0.5,
    "m_bag": 1,
    "m_cargo": 1,
    "m_payload": 1,
    "tow_glider_mass_kg": 1,
    "mass_initial_guess": 1,
    "mass_iteration_start_kg": 1,
    "mass_point_x1": 1,
    "mass_point_x2": 1,
    "payload_drop_kg": 1,
    "range_km": 1,
    "outbound_range_km": 1,
    "return_range_km": 1,
    "cruise_speed_kmh": 1,
    "v_stall_kmh": 1,
    "v_max_required_kmh": 1,
    "loiter_speed_kmh": 1,
    "climb_start_speed_kmh": 1,
    "tow_speed_kmh": 1,
    "vmo_kcas": 1,
    "cruise_altitude_m": 10,
    "service_ceiling_m": 50,
    "climb_start_altitude_m": 10,
    "airfield_elevation_m": 10,
    "takeoff_run_m": 5,
    "takeoff_distance_m": 5,
    "landing_distance_m": 5,
    "loiter_time_min": 1,
    "max_power_time_min": 1,
    "engine_power_kw": 1,
    "engine_power_limit_kw": 1,
    "engine_custom_power_kw": 1,
    "max_power_kw": 1,
    "n_pax": 1,
    "n_crew": 1,
    "n_engines": 1,
    "turbine_inlet_temp_k": 10,
    "cargo_hold_density_kg_m3": 1,
    "cost_year": 1,
    "cost_n_production": 1,
    "cost_n_amortization": 1,
    "cost_n_prototypes": 1,
    "engine_price_usd": 100,
    "avionics_price_usd": 100,
    "trend_year_min": 1,
    "trend_year_max": 1,
    "trend_count": 1,
    "trend_nearest_count": 1,
    "trend_engine_count": 1,
    "cruise_ld_p4": 0.1,
    "cruise_ld_p4_speed_kmh": 1,
    "cruise_ld_p4_altitude_m": 10,
    "empty_mass_trend_A": 0.0001,
    "empty_mass_trend_C": 0.0001,
    "empty_mass_a": 0.0001,
    "empty_mass_c": 0.0001,
}

COUNT_KEYS = ("cost_year", "cost_n_production", "cost_n_amortization", "cost_n_prototypes")

ENUM_CHOICES = {
    'trend_source': ('all', 'fast', 'cado', 'motogliders', 'geometry_trends', 'primary_research', 'user'),
    'matching_design_mode': ('wing_limit', 'minimum_power', 'range'),
    'design_iteration_mode': ('preliminary', 'coupled'),
    'wing_input_mode': ('loading', 'span_aspect', 'span_area', 'area_aspect'),
    'payload_input_mode': ('seats', 'total'),
    'airfoil_criterion': ('auto', 'cruise', 'lift'),
    'power_input_mode': ('sized', 'fixed'),
    'gear_attachment': ('fuselage', 'wing'),
    'landing_gear_type': ('tricycle', 'tailwheel'),
    'empty_mass_closure': ('trend', 'components'),
    'technology': ('metallic', 'composite', 'wood', 'steel_tube'),
    'runway_surface': ('paved', 'grass'),
    'cs22_gust_model': ('amendment3', 'pratt'),
    'profile_thickness_mode': ('auto', 'assumed'),
    'gear_retraction': ('auto', 'fixed', 'retractable'),
    'trend_weighting': ('family', 'variant'),
    'mission_phase_model': ('standard', 'galinski'),
    'flap_type': ('none', 'plain', 'split', 'junkers', 'single_slotted', 'fowler', 'double_slotted', 'flaperon'),
    'aileron_type': ('differential', 'frise', 'slotted', 'plain', 'flaperon'),
    'slat_type': ('none', 'fixed_slot', 'slats_auto', 'krueger'),
    'wing_planform': ('trapezoidal', 'rectangular', 'compound_trapezoid', 'elliptical', 'swept_trapezoidal')
}


DEFAULTS = {
    "aircraft_type": "piston_ga", "engine_type": "prop", "engine_location": "nose",
    "category": "jar23_normal", "n_pax": 4, "n_crew": 1, "m_pax": PASSENGER_WITH_BAG_KG,
    "m_bag": 0, "m_cargo": 0, "m_crew_person": 90,
    "range_km": 1200, "cruise_altitude_m": 3000, "cruise_speed_kmh": 250,
    "v_stall_kmh": 100, "takeoff_run_m": 500, "climb_rate_ms": 4,
    "aspect_ratio": 8, "taper_ratio": 0.55, "oswald_e": 0.8, "cx0": 0.025,
    "cz_max_clean": 1.45, "cz_max_to": 1.8, "cz_max_lnd": 2.2,
    "prop_efficiency": 0.82, "prop_eff_to": 0.65,
    "flap_type": "single_slotted", "slat_type": "none",
    "aileron_type": "differential",
    "flap_span_ratio": 0.60, "flap_chord_ratio": 0.25,
    "aileron_span_ratio": 0.28, "aileron_chord_ratio": 0.22,
    "wing_planform": "trapezoidal", "break_span_ratio": 0.40,
    "mission_phase_model": "galinski", "mission_ld_factor": CRUISE_LD_FACTOR,
    "gear_attachment": "fuselage",
    "takeoff_distance_m": 0, "landing_distance_m": 0,
    "mass_method": "auto", "empty_mass_model": "trend",
    "payload_drop_kg": 0, "return_range_km": 0,
    "design_iteration_mode": "preliminary", "operating_surface": "land", "runway_surface": "paved",
    "cs22_gust_model": "pratt",
    "profile_thickness_mode": "auto", "tc_ratio": 0.12,
    "cargo_bay_length_m": 0, "cargo_bay_width_m": 0, "cargo_bay_height_m": 0,
    "max_power_time_min": 0, "preliminary_polar_mode": "raymer",
    "climb_fraction_mode": "energy", "mission_climb_rate_ms": 3., "trend_year_basis": "certification",
}


def validate_parameters(data):
    if not isinstance(data, dict):
        raise ValueError("Parametry projektu muszą być obiektem JSON.")
    p = {**DEFAULTS, **data}
    from calculations.propeller import shaft_rpm
    if 'propeller_rpm' in p or 'prop_rpm' in p:
        p['propeller_rpm'] = shaft_rpm(p)
        p.pop('prop_rpm', None)
    if p.get('airfoil_model'):
        section = p['airfoil_model']
        limits = dict(a_inf_rad=(3, 8), alpha_0_deg=(-12, 6), cm_ac=(-.4, .2), cx_min=(.002, .05), re_ref=(1e4, 1e9),
                      cz_cx_min=(-1, 2), cx_quad=(0, .1))
        if not isinstance(section, dict):
            raise ValueError('Dane profilu muszą być obiektem z wielkościami profilu.')
        for key, (low, high) in limits.items():
            if key in section and not low <= float(section[key]) <= high:
                raise ValueError(f'Dane profilu: {key} poza zakresem {low:g}–{high:g}.')
    if 'cx0_deviation_reason' in p and (not isinstance(p['cx0_deviation_reason'], str) or len(p['cx0_deviation_reason']) > 2000):
        raise ValueError('Uzasadnienie odchylenia Cx₀ musi być tekstem do 2000 znaków.')
    if 'airfoil_source' in p and (not isinstance(p['airfoil_source'], str) or len(p['airfoil_source']) > 4000):
        raise ValueError('Źródło profilu: podaj tekst do 4000 znaków.')
    if 'climb_source' in p and (not isinstance(p['climb_source'], str) or len(p['climb_source']) > 4000):
        raise ValueError('Źródło danych wznoszenia: podaj tekst do 4000 znaków.')
    # One comparison sample: the aircraft nearest in MTOW to the design (BIPOL_1, s. 1).
    for key in ('trend_reference_mode', 'mass_initial_guess'):
        p.pop(key, None)
    if p['operating_surface'] not in ('land', 'water'):
        raise ValueError('Nieznane środowisko startu i lądowania.')
    if 'preliminary_polar_includes_configuration' in p and not isinstance(p['preliminary_polar_includes_configuration'], bool):
        raise ValueError('Źródło biegunowej P4: wymagany znacznik logiczny.')
    if 'coursework' in p:
        from calculations.coursework import validate_coursework
        validate_coursework(p['coursework'])
    # Migrate earlier mission keys without silently discarding a task or route.
    if 'max_power_time_min' not in data:
        p['max_power_time_min'] = data.get('t_max_thrust_min') or data.get('task_time_min') or 0
    if data.get('mission_has_drop') is True and 'payload_drop_kg' not in data:
        p['payload_drop_kg'] = data.get('m_cargo',0)
    for optional_speed in ('loiter_speed_kmh','climb_start_speed_kmh'):
        if p.get(optional_speed) == 0:
            p.pop(optional_speed)
    if p.get('airfoil_comparison'):
        from calculations.airfoil_comparison import parse_comparison
        if not isinstance(p['airfoil_comparison'], str) or len(p['airfoil_comparison']) > 4000:
            raise ValueError('Porównanie profili: wymagany tekst do 4000 znaków.')
        parse_comparison(p['airfoil_comparison'])
    for key in ('report_notes', 'source_notes'):
        if key in p and (not isinstance(p[key], str) or len(p[key]) > 15000):
            raise ValueError(f'Pole {key}: wymagany tekst do 15000 znaków.')
    if data.get("aircraft_type") == "uav" and "m_cargo" not in data:
        p["m_cargo"] = 80
    if data.get("aircraft_type") == "glider":
        p["engine_type"] = "none"
        if "takeoff_run_m" not in data:
            p["takeoff_run_m"] = 0
        if "sfc" not in data:
            p["sfc"] = 0
    elif data.get("aircraft_type") in ("jet_business", "jet_transport") and "engine_type" not in data:
        p["engine_type"] = "jet"
    # Cached outputs are never inputs to a new calculation on a different basis.
    if p.get('wing_input_mode') in ('loading', 'span_aspect'):
        p['wing_area_m2'] = 0.0
    if p.get('wing_input_mode') in ('loading', 'area_aspect'):
        p['wingspan_m'] = 0.0
        p['span_limit'] = 0.0
    if p.get('wing_input_mode') == 'span_area':
        p['aspect_ratio'] = DEFAULTS['aspect_ratio']
    locked = p.get('locked_params', [])
    if p.get('payload_input_mode') == 'total' or (isinstance(locked, list) and 'm_payload' in locked and 'payload_input_mode' not in p):
        p.pop('m_cargo', None)
    if p.get('payload_input_mode') == 'seats':
        p.pop('m_payload', None)
    if p.get('wing_planform') in ('rectangular','elliptical'):
        p['taper_ratio'] = 1.0 if p['wing_planform'] == 'rectangular' else 0.0
    for key, (lower, upper) in NUMERIC_LIMITS.items():
        if key not in p:
            continue
        value = p[key]
        try:
            number = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Pole {key}: podaj liczbę.") from None
        if isinstance(value, bool) or not math.isfinite(number) or not lower <= number <= upper:
            raise ValueError(f"Pole {key}: wymagana skończona liczba od {lower} do {upper}.")
        if key in ("n_pax", "n_crew", "n_engines") and not number.is_integer():
            raise ValueError(f"Pole {key}: liczba osób musi być całkowita.")
        if key in COUNT_KEYS and not number.is_integer():
            raise ValueError(f"Pole {key}: wymagana liczba całkowita.")
        p[key] = number
    if p.get('cost_n_amortization', 0) > p.get('cost_n_production', math.inf):
        raise ValueError('Koszty: liczba egzemplarzy amortyzujących koszty rozwoju N_am nie może przekraczać serii N_P.')
    dimensions = [p[key] for key in ('cargo_bay_length_m', 'cargo_bay_width_m', 'cargo_bay_height_m')]
    if any(dimensions) and not all(dimensions):
        raise ValueError('Podaj wszystkie trzy wymiary ładowni albo pozostaw wszystkie równe zero.')
    if p["aircraft_type"] not in ("piston_ga", "turboprop_regional", "jet_business", "jet_transport", "uav", "motoglider", "glider"):
        raise ValueError("Nieznana klasa konstrukcyjna samolotu.")
    if p["engine_type"] not in ("prop", "jet", "none"):
        raise ValueError("Nieznany rodzaj napędu.")
    if p['engine_type'] == 'none':
        p['n_engines'] = 0
    else:
        p.setdefault('n_engines', 2 if p.get('engine_location') == 'wing' or p['engine_type'] == 'jet' else 1)
        if p['n_engines'] < 1:
            raise ValueError('Samolot z napędem wymaga co najmniej jednego silnika.')
        from calculations.engine_fuel import apply_engine_inputs
        apply_engine_inputs(p)
        p.setdefault('sfc', .62 if p['engine_type'] == 'jet' else 265.)
        # One unit convention in forms, mass sizing and performance. Never
        # silently substitute another engine's consumption for a submitted value.
        low, high = (.15, 4.) if p['engine_type'] == 'jet' else (80., 1000.)
        if not low <= p['sfc'] <= high:
            unit = '1/h' if p['engine_type'] == 'jet' else 'g/(kW·h)'
            raise ValueError(f'SFC: dla tego napędu podaj wartość {low:g}–{high:g} {unit}.')
    if p['engine_type'] == 'none':
        from calculations.engine_fuel import apply_engine_inputs
        apply_engine_inputs(p)
    for key in ('turbocharged', 'retractable_gear'):
        if key in p and not isinstance(p[key], bool):
            raise ValueError(f'Pole {key}: wymagana wartość logiczna.')
    for key in ('trend_count', 'trend_nearest_count', 'trend_engine_count', 'trend_year_min', 'trend_year_max'):
        if key in p and not float(p[key]).is_integer():
            raise ValueError(f'Pole {key}: wymagana liczba całkowita.')
    for key, allowed in ENUM_CHOICES.items():
        if key in p and p[key] not in allowed:
            raise ValueError(f'Nieznana opcja: {key}.')
    if p.get('gear_retraction', 'auto') != 'auto':
        p['retractable_gear'] = p['gear_retraction'] == 'retractable'
    if p.get("flap_type") == "flaperon" and "aileron_type" not in data:
        p["aileron_type"] = "flaperon"
    if p.get('trend_year_min') and p.get('trend_year_max') and p['trend_year_min'] > p['trend_year_max']:
        raise ValueError('Początkowy rok próby musi być nie większy od końcowego.')
    if 'variable_sweep' in p and not isinstance(p['variable_sweep'], bool):
        raise ValueError('Pole variable_sweep: wymagana wartość logiczna.')
    if ('empty_mass_trend_A' in p) != ('empty_mass_trend_C' in p):
        raise ValueError('Równanie (1) masy pustej wymaga obu współczynników: A i C.')
    if 'locked_params' in p and not isinstance(p['locked_params'], list):
        raise ValueError('Pole locked_params: wymagana lista identyfikatorów parametrów.')
    if any(not isinstance(k, str) for k in p.get('locked_params', [])):
        raise ValueError('Pole locked_params: identyfikatory parametrów muszą być tekstem.')
    if 'trend_aircraft_ids' in p:
        ids = p['trend_aircraft_ids']
        if not isinstance(ids, list) or len(ids) > 716 or any(not isinstance(i, str) for i in ids):
            raise ValueError('Dobór konstrukcji: wymagana lista identyfikatorów (maks. 716).')
        from calculations.trends import load_aircraft
        known = {r['id'] for r in load_aircraft()}
        if any(i not in known for i in ids):
            raise ValueError('Dobór konstrukcji zawiera nieznany identyfikator.')
    if p["v_stall_kmh"] >= p["cruise_speed_kmh"]:
        raise ValueError("Prędkość przelotowa musi być większa od prędkości przeciągnięcia VS0.")
    if p["engine_type"] != "none" and p.get("takeoff_run_m", 0) < 50:
        raise ValueError("Pole takeoff_run_m: wymagana skończona liczba od 50 do 10000.")
    if p["cz_max_to"] < p["cz_max_clean"] or p["cz_max_lnd"] < p["cz_max_to"]:
        raise ValueError("Wymagane Cz max: konfiguracja gładka ≤ startowa ≤ lądowania.")
    # The lecture supersedes the older PDF's 0.8 factor and phase defaults.
    # Validate submitted data above, then canonicalize the course assumptions.
    p['mission_ld_factor'] = CRUISE_LD_FACTOR
    p['mission_phase_model'] = 'galinski'
    p['flap_takeoff_deg'] = FLAP_TAKEOFF_DEFLECTION_DEG
    p['flap_landing_deg'] = FLAP_LANDING_DEFLECTION_DEG
    # A supplied C_D0 describes the complete clean aircraft, referenced to wing area.
    # Preserve the author's explicit starting method; do not silently replace it with Fig. 2.
    if p['preliminary_polar_mode'] == 'input':
        p['preliminary_polar_includes_configuration'] = True
    elif p['preliminary_polar_mode'] in ('raymer', 'reading') and 'wetted_example' not in data and 'sketch_swet_ratio' in data:
        # Earlier projects measured S_wet/S on the sketch.
        p['wetted_example'] = 'sketch'
    # A saved calculation cannot authenticate the fixed-point reference of another design.
    for key in ('_reference_mass', '_reference', '_similar_count'):
        p.pop(key, None)
    # BIPOL_1, s. 1 i 4: masa pusta z równania (1) analizy trendów; korelacja klasy, stały udział
    # i własne A, C nie należą do ścieżki projektu.
    if p.get('empty_mass_model') != 'two_point':
        p['empty_mass_model'] = 'trend'
    for key in ('empty_mass_trend_A', 'empty_mass_trend_C', 'empty_mass_fraction', 'empty_mass_a', 'empty_mass_c'):
        p.pop(key, None)
    from calculations.bipol1 import validate_bipol1
    validate_bipol1(p)
    if 'trend_observations' in p:
        from calculations.trend_observations import validate_observations
        p['trend_observations'] = validate_observations(p['trend_observations'])
    from calculations.aeroelastics import validate_aeroelastic_inputs
    validate_aeroelastic_inputs(p)
    return p
