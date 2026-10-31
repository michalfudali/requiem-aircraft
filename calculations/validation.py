"""Wspólne wartości wejściowe i walidacja przed uruchomieniem obliczeń."""
import math
from calculations.instructor import (CRUISE_LD_FACTOR, PASSENGER_WITH_BAG_KG,
                                     FLAP_TAKEOFF_DEFLECTION_DEG, FLAP_LANDING_DEFLECTION_DEG)

NUMERIC_LIMITS = {
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
    "trend_count": (0, 716), "trend_engine_count": (0, 8),
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
    "climb_start_altitude_m": (0, 20000),
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
}

DEFAULTS = {
    "aircraft_type": "piston_ga", "engine_type": "prop", "engine_location": "nose",
    "category": "cs23_level2", "n_pax": 4, "n_crew": 1, "m_pax": PASSENGER_WITH_BAG_KG,
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
    "mass_method": "auto", "empty_mass_model": "class_correlation",
    "mass_initial_guess": 5000, "payload_drop_kg": 0, "return_range_km": 0,
    "design_iteration_mode": "preliminary", "operating_surface": "land", "runway_surface": "paved",
    "cs22_gust_model": "amendment3",
    "cargo_bay_length_m": 0, "cargo_bay_width_m": 0, "cargo_bay_height_m": 0,
    "max_power_time_min": 0, "preliminary_polar_mode": "input",
    "climb_fraction_mode": "auto", "trend_year_basis": "certification",
}


def validate_parameters(data):
    if not isinstance(data, dict):
        raise ValueError("Parametry projektu muszą być obiektem JSON.")
    p = {**DEFAULTS, **data}
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
        p[key] = number
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
        p.setdefault('sfc', .62 if p['engine_type'] == 'jet' else 265.)
        # One unit convention in forms, mass sizing and performance. Never
        # silently substitute another engine's consumption for a submitted value.
        low, high = (.15, 4.) if p['engine_type'] == 'jet' else (80., 1000.)
        if not low <= p['sfc'] <= high:
            unit = '1/h' if p['engine_type'] == 'jet' else 'g/(kW·h)'
            raise ValueError(f'SFC: dla tego napędu podaj wartość {low:g}–{high:g} {unit}.')
    for key in ('turbocharged', 'retractable_gear'):
        if key in p and not isinstance(p[key], bool):
            raise ValueError(f'Pole {key}: wymagana wartość logiczna.')
    for key in ('trend_count', 'trend_engine_count', 'trend_year_min', 'trend_year_max'):
        if key in p and not float(p[key]).is_integer():
            raise ValueError(f'Pole {key}: wymagana liczba całkowita.')
    for key, allowed in {'trend_source': ('all', 'fast', 'cado', 'motogliders', 'geometry_trends', 'user'),
                         'wing_input_mode': ('loading', 'span_aspect', 'span_area', 'area_aspect'),
                         'payload_input_mode': ('seats', 'total'),
                         'power_input_mode': ('sized', 'fixed'),
                         'gear_attachment': ('fuselage', 'wing'),
                         'runway_surface': ('paved', 'grass'),
                         'cs22_gust_model': ('amendment3', 'pratt'),
                         'gear_retraction': ('auto', 'fixed', 'retractable'),
                         'trend_weighting': ('family', 'variant'),
                         'mission_phase_model': ('standard', 'galinski'),
                         'flap_type': ('none', 'plain', 'split', 'junkers', 'single_slotted', 'fowler', 'double_slotted', 'flaperon'),
                         'aileron_type': ('differential', 'frise', 'slotted', 'plain', 'flaperon'),
                         'slat_type': ('none', 'fixed_slot', 'slats_auto', 'krueger'),
                          'wing_planform': ('trapezoidal', 'rectangular', 'compound_trapezoid', 'elliptical', 'swept_trapezoidal')}.items():
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
    from calculations.bipol1 import validate_bipol1
    validate_bipol1(p)
    if 'trend_observations' in p:
        from calculations.trend_observations import validate_observations
        p['trend_observations'] = validate_observations(p['trend_observations'])
    return p
