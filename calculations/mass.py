"""Shared BIPOL mass sizing and preliminary component allocation."""
from calculations.bipol1 import solve_mass, mission_model
from calculations.polish_law import is_unmanned


def corke_climb_fuel_fraction(engine_type, h_cr_m, v_cr_ms):
    p = dict(engine_type=engine_type, cruise_altitude_m=h_cr_m, cruise_speed_kmh=v_cr_ms*3.6)
    return mission_model(p,15)[1]['corke']['fraction']


def calculate_mass_sizing(params: dict):
    ac_type = params.get('aircraft_type', 'piston_ga')
    engine_type = params.get('engine_type', 'prop')
    wing_config = params.get('wing_config', 'low')
    unmanned = is_unmanned(params)
    n_pax = 0 if unmanned else int(params.get('n_pax', 4))
    n_crew = 0 if unmanned else int(params.get('n_crew', 1 if n_pax <= 4 else 2))
    payload = n_pax*(params.get('m_pax',80)+params.get('m_bag',0))+params.get('m_cargo',0)
    crew = n_crew*params.get('m_crew_person',90)
    p = dict(params,n_pax=n_pax,n_crew=n_crew)
    result = solve_mass(p,payload,crew)
    m_empty = result['m_empty']
    breakdown_shares = {
        "piston_ga": {
            "wing": 0.28, "fuselage": 0.24, "tail": 0.05, "gear": 0.12, 
            "propulsion": 0.21, "systems": 0.10
        },
        "turboprop_regional": {
            "wing": 0.25, "fuselage": 0.23, "tail": 0.06, "gear": 0.11,
            "propulsion": 0.22, "systems": 0.13
        },
        "jet_business": {
            "wing": 0.26, "fuselage": 0.24, "tail": 0.06, "gear": 0.10,
            "propulsion": 0.19, "systems": 0.15
        },
        "jet_transport": {
            "wing": 0.27, "fuselage": 0.25, "tail": 0.05, "gear": 0.11,
            "propulsion": 0.18, "systems": 0.14
        },
        "uav": {
            "wing": 0.30, "fuselage": 0.22, "tail": 0.06, "gear": 0.08,
            "propulsion": 0.20, "systems": 0.14
        }
    }
    shares = dict(breakdown_shares.get(ac_type, breakdown_shares["piston_ga"]))
    if ac_type == "glider" or engine_type == "none":
        remaining = 1.0 - shares["propulsion"]
        shares = {key: (0.0 if key == "propulsion" else value / remaining) for key, value in shares.items()}
    if wing_config == "braced_high":
        shares["wing"] = round(shares["wing"] * 0.89, 3)
        shares["fuselage"] = round(1.0 - (shares["wing"] + shares["tail"] + shares["gear"] + shares["propulsion"] + shares["systems"]), 3)

    mass_components = {
        "m_wing": round(m_empty * shares["wing"], 1),
        "m_fuselage": round(m_empty * shares["fuselage"], 1),
        "m_tail": round(m_empty * shares["tail"], 1),
        "m_gear": round(m_empty * shares["gear"], 1),
        "m_propulsion": round(m_empty * shares["propulsion"], 1),
        "m_systems": round(m_empty * shares["systems"], 1),
    }

    result.update(breakdown=mass_components, n_pax=n_pax, n_crew=n_crew, unmanned=unmanned)
    result['primary_method'] = 'proportion' if result['mass_method']=='proportions' else 'iterative'
    result['mission_assumptions']['method'] = result['primary_method']
    result['payload_drop_kg'] = result['m_payload_dropped']
    result['payload_remaining_kg'] = result['m_payload_landing']
    law = result['empty_mass_law']
    result['empty_mass_trend'] = {k:law[k] for k in ('A','C','k_vs')} if law['mode'] in ('trend','coefficients','two_point','bipol1_trend') else None
    result['sizing_methods'] = {}
    for method in ('proportion','iterative'):
        if method=='proportion' and result['m_payload_dropped']:
            result['sizing_methods'][method] = dict(applicable=False, reason='Metoda proporcji wymaga misji bez zrzutu.')
            continue
        r = result if method==result['primary_method'] else solve_mass(dict(p,mass_method=method),payload,crew)
        phases = {s['key']:s['mass_end_kg'] for s in r['mission_phases']}
        out = phases['cruise']; task = phases.get('task',out); drop = phases.get('drop',task)
        result['sizing_methods'][method] = dict(applicable=True, method=method,
            m0=r['m0'],m_empty=r['m_empty'],m_fuel=r['m_fuel'],m_drop=r['m_payload_dropped'],
            empty_fraction=r['empty_fraction'],fuel_fraction=r['fuel_fraction'],
            total_mff=r['fuel_fractions_detail']['total_mff'],iterations=r['iterations'],
            residual=r['iterations'][-1]['diff'],residual_relative=r['mission_assumptions']['empty_mass_residual_relative'],
            phases=dict(m0=r['m0'],m1_takeoff=phases['takeoff'],m2_climb=phases['climb'],
                m3_outbound=out,m3_post_task=task,m4_post_drop=drop,m5_return=phases.get('return',drop),
                m6_loiter=phases['loiter'],m7_landing=phases['landing']))
    # BIPOL_1, s. 4: the same balance written out iteration by iteration for the report.
    from calculations.mass_iteration import guideline_trace
    trace_params = p
    trace_start = params.get('mass_iteration_start_kg')
    if p.get('_mission_polar') and trace_start is None:
        trace_start = 1.1 * result['m0']
        trace_params = dict(p, _mass_trace_start_rule='1,1·m0 rozwiązania przedziałowego; odtworzenie toku obliczeń')
    result['guideline_traces'] = {
        method: guideline_trace(trace_params, payload, crew, method, trace_start)
        for method, info in result['sizing_methods'].items() if info['applicable']}
    return result
