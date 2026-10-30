"""
Główny moduł integrujący obliczenia wstępnego projektowania samolotu BIPOL I
"""
import math

from calculations.atmosphere import G0, RHO0
from calculations.high_lift import high_lift
from calculations.mass import calculate_mass_sizing
from calculations.sizing import calculate_matching_chart
from calculations.geometry import calculate_geometry
from calculations.aerodynamics import calculate_aerodynamics
from calculations.performance import calculate_performance
from calculations.envelope import calculate_vn_envelope
from calculations.balance import calculate_balance_and_stability, MAX_TAIL_VOLUME
from calculations.bipol_projects import calculate_all_bipol_projects
from calculations.polish_law import normalize_occupants, check_compliance
from calculations.validation import validate_parameters
from calculations.glide import calculate_glide_polar
from calculations.runway import refine_takeoff_sizing
from calculations.instructor import review_coursework
from calculations.official_topics import validate_topic_geometry, check_topic_requirements
from calculations.design_solver import resolve_design
from calculations.model_scope import assessment, is_water
from calculations.constraints import resolve_and_lock_parameters, finalize_parameter_states, get_initial_constraint_suggestions, WING_PLANFORMS

def _size_airframe(params, param_states):
    mass_res = calculate_mass_sizing(params)
    if params.get('preliminary_polar_mode','input') != 'input':
        params['cx0'] = mass_res['preliminary_polar']['cx0']
        param_states['cx0'] = dict(state='derived',value=params['cx0'],
            formula='BIPOL_1 (3): π·AR·e/(4·Kmax²)',sources=['sketch_swet_ratio','raymer_family','raymer_kmax'])
    if mass_res['empty_mass_law'].get('aircraft_ids'):
        # Freeze the cohort used in the nonlinear solve for the P1 report.
        params['trend_aircraft_ids'] = mass_res['empty_mass_law']['aircraft_ids']
        params['trend_count'] = 0
    m0 = mass_res["m0"]

    # Kategoria operacji UAS zależy od ryzyka operacji, a nie od progu masy 600 kg.
    
    # Etap P2: Dobór obciążenia powierzchni skrzydła i ciągu/mocy (Matching Chart)
    sizing_res = calculate_matching_chart(params, m0=m0, mass=mass_res)
    ws = sizing_res["design_point"]["ws"]
    
    # Etap P3: Wymiarowanie zespołów (skrzydło, kadłub, usterzenia, Schrenk)
    geom_res = calculate_geometry(m0, ws, params)
    # Wing area and high-lift coverage depend on each other. Close this loop
    # before propulsion, stall checks and reports consume the coefficients.
    for _ in range(20):
        lift = high_lift(params, geometry=geom_res)
        if all(abs(params[key] - lift[key]) < 1e-9 for key in ('cz_max_to', 'cz_max_lnd')):
            for key in ('cz_max_to', 'cz_max_lnd'):
                params[key] = lift[key]
                param_states[key]['value'] = lift[key]
            break
        for key in ('cz_max_to', 'cz_max_lnd'):
            params[key] = lift[key]
            param_states[key].update(value=lift[key],
                formula='Przyrost profilowy × udział powierzchni z mechanizacją',
                sources=['cz_max_clean', 'flap_type', 'slat_type', 'flap_span_ratio', 'wing_planform'])
        sizing_res = calculate_matching_chart(params, m0=m0, mass=mass_res)
        ws = sizing_res['design_point']['ws']
        geom_res = calculate_geometry(m0, ws, params)
    else:
        raise ValueError('Nie uzyskano spójnej powierzchni skrzydła i mechanizacji; zmień geometrię lub założenia.')
    validate_topic_geometry(params, geom_res)


    # Etap P4: Charakterystyki aerodynamiczne (biegunowe, doskonałość)
    aero_res = calculate_aerodynamics(geom_res, params, m0=m0)

    # Close the geometric loop: the tail arms must be measured from the wing
    # quarter-MAC found by balancing, not from an unrelated fraction of length.
    # The horizontal tail grows when the class volume leaves less than the minimum static
    # margin at the aft centre of gravity (X-plot), unless the designer fixed V_H.
    tail_volume_free = 'v_h' not in params.get('locked_params', [])
    for _ in range(20):
        balance_res = calculate_balance_and_stability(mass_res, geom_res, aero_res, params)
        wing_ac = balance_res['x_lemac_m'] + .25 * geom_res['wing']['mac']
        arms = {key: geom_res[name]['x_ac_m'] - wing_ac for key, name in
                (('_tail_arm_h', 'horizontal_tail'), ('_tail_arm_v', 'vertical_tail'))}
        if min(arms.values()) <= 0:
            raise ValueError('Usterzenie musi leżeć za środkiem aerodynamicznym skrzydła w tym układzie.')
        error = max(abs(arms['_tail_arm_h'] - geom_res['horizontal_tail']['l_h']),
                    abs(arms['_tail_arm_v'] - geom_res['vertical_tail']['l_v']))
        stability = balance_res['stability']
        v_h = float(params.get('v_h', .7))
        grow = (tail_volume_free and not stability['is_stable'] and v_h < MAX_TAIL_VOLUME
                and stability['vh_for_min_margin'] > v_h + 1e-3)
        if error <= .015 and not grow:
            break
        if grow:
            params['v_h'] = round(min(MAX_TAIL_VOLUME, stability['vh_for_min_margin']), 3)
            param_states['v_h'] = dict(state='derived', value=params['v_h'], sources=['v_h'],
                formula='V_H z warunku Kn ≥ 5% ŚDA w tylnym położeniu ŚC (wykres X)')
        geom_res = calculate_geometry(m0, ws, {**params, **arms})
        aero_res = calculate_aerodynamics(geom_res, params, m0=m0)
    else:
        raise ValueError('Nie uzyskano spójnego położenia skrzydła i ramion usterzenia; zmień układ lub założenia geometrii.')
    
    refine_takeoff_sizing(sizing_res, geom_res, aero_res, params, m0)
    return mass_res, sizing_res, geom_res, aero_res


def run_bipol_project(params: dict):
    """
    Wykonuje pełny ciąg obliczeniowy projektu BIPOL I (etapy P1 - P6).
    """
    # Normalizacja domeny: napęd odrzutowy nie występuje w konfiguracji ciągnącej w nosie kadłuba (GA tractor)
    params = validate_parameters(params)
    params, law_corrections = normalize_occupants(params)
    params["_law_corrections"] = law_corrections
    params, param_states, constraint_warnings = resolve_and_lock_parameters(params, params.get("locked_params", []))
    if params.get("engine_type") == "jet" and params.get("engine_location") in ("nose", "retractable", "none"):
        params["engine_location"] = "wing" if params.get("aircraft_type") == "jet_transport" else "rear"

    lift = high_lift(params)
    for key in ('cz_max_to', 'cz_max_lnd'):
        params[key] = lift[key]
        param_states[key] = dict(state='derived', value=lift[key],
            formula='Model mechanizacji 20°/40°', sources=['cz_max_clean','flap_type','slat_type'])

    # Etap P1 i P2: Bilans masowy (szacowanie MTOW)
    mass_res, sizing_res, geom_res, aero_res, design_iteration = resolve_design(params, param_states, _size_airframe)
    m0 = mass_res["m0"]
    finalize_parameter_states(params, param_states, mass_res, sizing_res, geom_res)

    # Etap P5: Osiągi samolotu (prędkości, wznoszenie, pułap, start, lądowanie)
    perf_res = calculate_performance(m0, geom_res, aero_res, sizing_res, params, mass_result=mass_res)
    perf_res["glide"] = calculate_glide_polar(m0, geom_res, aero_res, params["cruise_altitude_m"], params=params)
    
    # Etap P6: Obwiednia obciążeń dopuszczalnych V-n
    envelope_res = calculate_vn_envelope(m0, geom_res, aero_res, perf_res, params)
    
    # Etap P6: Wyważenie i stateczność statyczna
    balance_res = calculate_balance_and_stability(mass_res, geom_res, aero_res, params)
    
    # Ocena zgodności z wymaganiami taktyczno-technicznymi
    model_scope = assessment(params, mass_res)
    checks = check_topic_requirements(params, sizing_res) + model_scope['checks']
    if design_iteration["mode"] == "coupled":
        checks.append(dict(parameter="Zbieżność masy, geometrii i biegunowej misji",
            required=f"Błąd względny ≤ {design_iteration['tolerance']:.4g}", actual=f"{design_iteration['iterations']} iteracji",
            passed=design_iteration["converged"], note=design_iteration["failure"] or "Bilans paliwa przy zadanej TAS i wysokości, z końcową biegunową P4."))
    # 1. Zgodność z prędkością przeciągnięcia
    req_v_stall = float(params.get("v_stall_kmh", 100.0))
    act_v_stall = perf_res["speeds"]["vs_lnd_kmh"]
    checks.append({
        "parameter": "Prędkość przeciągnięcia z klapami Vs0",
        "required": f"≤ {req_v_stall} km/h",
        "actual": f"{act_v_stall} km/h",
        "passed": act_v_stall <= req_v_stall + 1.0,
        "note": "Warunek zdatności do lądowania na krótkich pasach"
    })
    
    # 2. Zgodność z prędkością wznoszenia
    req_climb = float(params.get("climb_rate_ms", 4.0))
    act_climb = perf_res["climb"]["wy_max_ms"]
    checks.append({
        "parameter": "Maksymalna prędkość wznoszenia wy_max",
        "required": f"≥ {req_climb} m/s",
        "actual": f"{act_climb} m/s",
        "passed": act_climb >= req_climb - 0.1,
        "note": "Bezpieczeństwo przy odejściu na drugi krąg i przewyższenie przeszkód"
    })
    
    if params['engine_type'] != 'none':
        cruise = perf_res['cruise_check']
        checks.append(dict(parameter='Lot poziomy przy wymaganej prędkości i wysokości',
            required=f"{params['cruise_speed_kmh']:g} km/h TAS na {params['cruise_altitude_m']:g} m",
            actual=f"Cz={cruise['cl']:.3f}; nadmiar mocy {cruise['available_w']-cruise['required_w']:.0f} W",
            passed=cruise['cl'] <= cruise['cl_max'] and cruise['climb_ms'] >= 0,
            note='Sprawdzenie przy masie początku przelotu z bilansu misji: poniżej Czmax oraz moc dostępna co najmniej równa wymaganej.'))
        mission_range = perf_res['mission_range']['total_available_km']
        checks.append(dict(parameter='Zasięg przy wymaganej prędkości i wysokości',
            required=f"≥ {params['range_km']:g} km", actual=f'{mission_range:g} km' if mission_range is not None else 'Lot nieosiągalny',
            passed=perf_res['mission_range']['passed'],
            note='Biegunowa P4 i paliwo każdego odcinka przelotu z bilansu P2; dolot i powrót oceniane osobno, bez zużycia rezerwy.'))
    if perf_res['speeds']['mach_cruise'] > .75:
        checks.append(dict(parameter='Zakres modelu aerodynamicznego przy dużej prędkości',
            required='Dane oporu falowego i profilu', actual=f"M={perf_res['speeds']['mach_cruise']:.3f}",
            passed=False, severity='warning', note='Biegunowa paraboliczna nie zawiera wzrostu oporu falowego; wynik wymaga weryfikacji.'))

    # Full distances are not interchangeable with ground roll.
    if params['engine_type'] != 'none':
        req_to = params.get('takeoff_distance_m', 0)
        act_to = perf_res['takeoff']['distance_to_15m']
        checks.append(dict(parameter='Całkowita długość startu do 15 m',
            required=f'≤ {req_to:g} m' if req_to else 'Podaj założenie',
            actual=f'{act_to:g} m' if act_to is not None else 'Nie wyznaczono — operacje na wodzie' if is_water(params) else 'Start nieosiągalny',
            passed=bool(req_to and act_to is not None and act_to <= req_to),
            note='Rozbieg + odcinek powietrzny do wysokości 15 m.'))
    req_lnd = params.get('landing_distance_m', 0)
    act_lnd = perf_res['landing']['distance_from_15m']
    checks.append(dict(parameter='Całkowita długość lądowania znad 15 m',
        required=f'≤ {req_lnd:g} m' if req_lnd else 'Podaj założenie', actual=f'{act_lnd:g} m' if act_lnd is not None else 'Nie wyznaczono — operacje na wodzie',
        passed=bool(req_lnd and act_lnd is not None and act_lnd <= req_lnd), note='Podejście + wyrównanie + dobieg do zatrzymania.'))
    checks += mission_checks(params, sizing_res, geom_res, aero_res, perf_res, m0)

    # 4. Zapas stateczności statycznej w skrajnym tylnym położeniu ŚM
    act_sm = balance_res["stability"]["static_margin_aft_pct"]
    checks.append({
        "parameter": "Zapas stateczności statycznej Kn (tylne ŚM)",
        "required": "≥ 5.0% ŚDA",
        "actual": f"{act_sm}% ŚDA",
        "passed": act_sm >= 5.0,
        "note": "Kryterium stateczności podłużnej bez autopilota"
    })
    cg = balance_res["cg_range"]
    checks.append({
        "parameter": "Zakres położeń ŚC w locie (BIPOL_3)",
        "required": balance_res["cg_check"]["required"],
        "actual": f"{cg['forward_pct']}–{cg['aft_pct']}% ŚDA (zakres {cg['delta_pct']}%)",
        "passed": balance_res["cg_check"]["passed"],
        "note": "Stany w locie z lekkim (55 kg) i ciężkim (110 kg) pilotem; poza zakresem zmień położenie skrzydła lub rozmieszczenie mas."
    })

    # Obliczenia dedykowane dla projektów semestralnych BIPOL I (P1 do P6)
    bipol_projects_res = calculate_all_bipol_projects(
        mass_res, sizing_res, geom_res, aero_res, perf_res, envelope_res, balance_res, params
    )

    # Zgodność z klasyfikacją statków powietrznych (t.j. Dz. U. z 2025 r. poz. 1137, Tabele nr 1–3)
    law_res = check_compliance(params, mass_res, geom_res, perf_res, envelope_res)
    for c in law_res["checks"]:
        checks.append({
            "parameter": f"[{law_res['code']}] {c['name']}",
            "required": c["limit"],
            "actual": c["value"],
            "passed": c["ok"],
            "severity": c["severity"],
            "note": c["source"] + (" (zalecenie)" if c["severity"] == "warning" else "")
        })

    result = {
        "status": "success",
        "design_iteration": design_iteration,
        "model_scope": model_scope,
        "params": params,
        "mass": mass_res,
        "sizing": sizing_res,
        "geometry": geom_res,
        "aerodynamics": aero_res,
        "performance": perf_res,
        "envelope": envelope_res,
        "balance": balance_res,
        "compliance_checks": checks,
        "easa_compliance": law_res,
        "polish_law": law_res,
        "bipol_projects": bipol_projects_res,
        "constraints": {
            "parameter_states": param_states,
            "locked_keys": params.get("locked_params", []),
            "initial_suggestions": get_initial_constraint_suggestions(params.get("category", "cs23_level2"), params.get("aircraft_type", "piston_ga")),
            "available_planforms": WING_PLANFORMS,
            "warnings": constraint_warnings
        }
    }

    result["instructor_review"] = review_coursework(result)
    from calculations.bipol1 import review_bipol1
    result['bipol1_review'] = review_bipol1(result)
    from calculations.coursework import review_submission
    result['submission_review'] = review_submission(result)
    from calculations.aeroelastics import estimate_aeroelastics
    result['aeroelastics'] = estimate_aeroelastics(geom_res, aero_res, mass_res, envelope_res, params)
    from calculations.acoustics import estimate_aircraft_noise
    result['acoustics'] = estimate_aircraft_noise(params, sizing_res, perf_res, geom_res, mass_res)
    from calculations.engineering_audit import perform_engineering_audit
    result['engineering_audit'] = perform_engineering_audit(result)
    return result


def mission_checks(params, sizing_res, geom_res, aero_res, perf_res, m0):
    """Topic requirements beyond the course minimum: race speed, glider towing, engine power cap."""
    from calculations.flight_model import flight_point
    checks = []
    if params['engine_type'] == 'none':
        return checks
    v_req = float(params.get('v_max_required_kmh') or 0)
    if v_req:
        v_max = perf_res['speeds']['v_max_sl_kmh']
        checks.append(dict(parameter='Prędkość maksymalna przy ziemi', required=f'≥ {v_req:g} km/h',
            actual=f'{v_max:g} km/h', passed=v_max >= v_req,
            note='Moc dostępna równa mocy niezbędnej przy ziemi; biegunowa P4.'))
    m_glider = float(params.get('tow_glider_mass_kg') or 0)
    if m_glider and params['engine_type'] == 'prop':
        v_tow = float(params.get('tow_speed_kmh', 120)) / 3.6
        S, ld_glider = geom_res['wing']['S'], float(params.get('tow_glider_ld', 25))
        point = flight_point(params, sizing_res, m0, S, aero_res['cx0_clean'], aero_res['k_clean'], 0.0, v_tow)
        # Excess power of the tug, less the power to pull the glider, lifts both aircraft.
        climb = (point['climb_ms'] * m0 - m_glider * v_tow / ld_glider) / (m0 + m_glider)
        stall_margin = v_tow / math.sqrt(2 * m0 * G0 / (RHO0 * S * aero_res['cz_max_clean']))
        perf_res['tow'] = dict(glider_mass_kg=m_glider, speed_kmh=v_tow * 3.6, climb_ms=round(climb, 2),
                               glider_ld=ld_glider, speed_to_vs1=round(stall_margin, 2))
        required = float(params.get('tow_climb_rate_ms', 3.0))
        checks.append(dict(parameter='Wznoszenie z szybowcem na holu',
            required=f'≥ {required:g} m/s z szybowcem {m_glider:g} kg przy {v_tow * 3.6:g} km/h',
            actual=f'{climb:.2f} m/s; V/VS1 = {stall_margin:.2f}', passed=climb >= required and stall_margin >= 1.2,
            note='Holownik przy MTOW, biegunowa P4; szybowiec o doskonałości K przy prędkości holowania. '
                 'Prędkość holowania co najmniej 1,2 VS1 holownika (jak V2 przy wznoszeniu po starcie).'))
    limit = float(params.get('engine_power_limit_kw') or 0)
    if limit and params['engine_type'] == 'prop':
        power = sizing_res['design_point']['power_kw']
        checks.append(dict(parameter='Moc silnika w granicy tematu', required=f'≤ {limit:g} kW',
            actual=f'{power:.1f} kW', passed=power <= limit, note='Limit mocy z treści tematu.'))
    return checks


def refine_bipol_project(params: dict, max_iterations: int = 20, tolerance: float = .002):
    """Create a new P4-based variant using the shared changing-weight design solver.

    Legacy keyword arguments remain accepted. Numerical closure is governed by
    resolve_design's documented tolerance and iteration bound, for every caller.
    """
    from calculations.polish_law import CS23_MTOM_MAX_KG
    baseline = run_bipol_project(params)
    aero = baseline['aerodynamics']
    updated = {**baseline['params'], 'cx0': aero['cx0_clean'], 'oswald_e': aero['oswald_e'],
               'preliminary_polar_mode': 'input', 'design_iteration_mode': 'coupled',
               'preliminary_polar_includes_configuration': True}
    if (updated.get('topic_origin') == 'official' and str(updated.get('category')).startswith('cs23')
            and baseline['mass']['m0'] > CS23_MTOM_MAX_KG):
        updated.update(category='cs25_transport', n_crew=max(2, int(updated.get('n_crew', 1))))
    result = run_bipol_project(updated)
    return baseline, result, result['design_iteration']['history']
