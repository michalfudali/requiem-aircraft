"""Engineering regressions from the category/browser audit, including independent ODE checks."""
import copy
import json
import math

import pytest

from calculations import run_bipol_project
from calculations.atmosphere import G0, isa_atmosphere
from calculations.calc_sheet import build_sheet
from calculations.mission_cruise import cruise_distance, mass_after_cruise
from calculations.official_topics import ALL_TOPICS
from calculations.presets import AIRCRAFT_PRESETS

REPRESENTATIVES = [7, 17, 20, 28, 32, 42, 43, 63, 68, 82, 94, 95, 101]


def topic(number):
    return copy.deepcopy(next(t['parameters'] for t in ALL_TOPICS if t['num'] == number))


@pytest.mark.parametrize('number', REPRESENTATIVES)
def test_category_design_closes_mission_with_actual_polar_and_documents_it(number):
    inputs = topic(number)
    before = copy.deepcopy(inputs)
    result = run_bipol_project(inputs)
    assert inputs == before
    json.dumps(result, allow_nan=False)
    closure = result['design_iteration']
    assert closure['converged'], closure
    assert closure['history'][-1]['relative_error'] <= closure['tolerance']
    mass, aero, wing = result['mass'], result['aerodynamics'], result['geometry']['wing']
    phases = {p['key']: p for p in mass['mission_phases']}
    start, end = (phases['cruise'][key] for key in ('mass_start_kg', 'mass_end_kg'))
    # Independent distance integral using the final geometry, not the mission solver's last polar.
    v = inputs['cruise_speed_kmh']/3.6
    qs = .5*isa_atmosphere(inputs['cruise_altitude_m'])['rho']*v*v*wing['S']
    a, b = qs*aero['cx0_clean'], aero['k_clean']*G0*G0/qs
    c = (inputs['sfc']/(3600*G0*v) if inputs['engine_type']=='jet'
         else inputs['sfc']/(3.6e9*inputs['prop_efficiency']))
    actual = (math.atan(start*math.sqrt(b/a))-math.atan(end*math.sqrt(b/a)))/(c*math.sqrt(a*b))/1000
    assert actual >= inputs['range_km']
    performance = result['performance']
    assert performance['paturski_p6']['range_endurance_6_5']['range_at_requested_speed_km'] >= inputs['range_km']
    assert performance['cruise_check']['mass_kg'] == start
    assert performance['cruise_check']['available_w'] >= performance['cruise_check']['required_w']
    sheet = build_sheet(result)
    assert not {e['key']:(e['value'], e['computed']) for e in sheet.entries.values() if e['consistent'] is False}
    assert 'a_mis' in sheet.entries and 'r_CR_end' in sheet.entries


@pytest.mark.parametrize('engine,sfc', [('prop',265),('jet',.62)])
def test_analytic_cruise_matches_independent_runge_kutta_integration(engine, sfc):
    p = dict(cruise_speed_kmh=350, cruise_altitude_m=3000, engine_type=engine,
             sfc=sfc, prop_efficiency=.82)
    polar = dict(S=25, cx0=.025, k=.04)
    v=p['cruise_speed_kmh']/3.6
    qs=.5*isa_atmosphere(3000)['rho']*v*v*25

    def rate(mass):
        drag = qs*.025 + .04*(mass*G0)**2/qs
        shaft_power = drag*v/.82
        fuel_kg_s = sfc*drag/(3600*G0) if engine=='jet' else sfc*shaft_power/3.6e9
        return -fuel_kg_s/v

    start, mass, step = 3000., 3000., 1000.
    for _ in range(500):
        a=rate(mass);b=rate(mass+step*a/2);c=rate(mass+step*b/2);d=rate(mass+step*c)
        mass += step*(a+2*b+2*c+d)/6
    calculated = mass_after_cruise(start, 500000, p, polar)
    assert calculated == pytest.approx(mass, abs=1e-7)
    assert cruise_distance(start, calculated, p, polar) == pytest.approx(500000, abs=1e-6)


@pytest.mark.parametrize('number', [27,28,29])
def test_aerobatic_requirement_cannot_disappear_when_category_is_changed(number):
    result = run_bipol_project(topic(number))
    assert result['envelope']['limits']['n_max'] == 6
    assert result['envelope']['limits']['n_min'] == -3
    changed = run_bipol_project(dict(topic(number), category='cs23_level1'))
    assert not next(c for c in changed['compliance_checks'] if c['parameter'].endswith('Przeznaczenie akrobacyjne'))['passed']


@pytest.mark.parametrize('number,engines', [(7,1),(20,1),(37,1),(38,2),(44,2),(103,2),(104,2)])
def test_catalogue_api_and_solver_keep_explicit_topic_engine_count(number, engines, client):
    data = client.get('/api/topics').get_json()
    catalogue = next(t for t in data['topics'] if t['num'] == number)
    assert catalogue['parameters']['n_engines'] == engines
    assert catalogue['requirements']['n_engines'] == engines
    result = run_bipol_project(catalogue['parameters'])
    assert result['params']['n_engines'] == engines


def test_official_training_power_limit_is_reported_without_overwriting_selected_engine(client):
    response = client.post('/api/calculate', json=dict(topic(32), power_input_mode='fixed', engine_power_kw=180))
    assert response.status_code == 200
    result = response.get_json()
    assert result['sizing']['design_point']['power_kw'] == 180
    check = next(c for c in result['compliance_checks'] if 'Maksymalna moc zainstalowana' in c['parameter'])
    assert not check['passed'] and check['required'] == '≤ 100 kW'
    # Submitted metadata cannot loosen the actual catalogue requirement.
    forged = dict(topic(32), power_input_mode='fixed', engine_power_kw=180, requirements={'power_per_engine_max_kw':10000})
    result = run_bipol_project(forged)
    assert not next(c for c in result['compliance_checks'] if 'Maksymalna moc zainstalowana' in c['parameter'])['passed']


@pytest.mark.parametrize('number', [93,94,95,96,97,98,110])
def test_water_aircraft_never_get_wheel_takeoff_or_braking_as_water_results(number, client):
    result = run_bipol_project(topic(number))
    assert result['params']['operating_surface'] == 'water'
    assert result['performance']['takeoff']['distance_to_15m'] is None
    assert result['performance']['landing']['distance_from_15m'] is None
    assert 'terms' not in result['performance']['takeoff']
    assert 'mu_brake' not in result['performance']['landing']['terms']
    water = result['model_scope']['water']
    assert water['required_buoyant_volume_m3'] == pytest.approx(1.8*result['mass']['m0']/1000)
    assert not water['hydrodynamic_performance_available']
    if result['mass']['m0'] > 8618:
        assert not water['cs23_criterion_applicable']
        assert 'Projekt poza zakresem JAR-23' in water['source']
    assert not next(c for c in result['compliance_checks'] if c['parameter'].startswith('[Woda] Wyporność'))['passed']
    sheet = build_sheet(result)
    assert not {e['key']:(e['value'], e['computed']) for e in sheet.entries.values() if e['consistent'] is False}
    assert 'mu_h' not in sheet.entries and 'mu_r' not in sheet.entries
    report = client.post('/report/project/p5', json=topic(number))
    assert report.status_code == 200
    assert 'oporu hydrodynamicznego' in report.get_data(as_text=True)


def test_buoyancy_volume_is_a_physical_check_and_does_not_certify_water_stability():
    result = run_bipol_project(dict(topic(95), water_displacement_volume_m3=20))
    checks = result['compliance_checks']
    assert next(c for c in checks if c['parameter'].startswith('[Woda] Wyporność'))['passed']
    assert not next(c for c in checks if c['parameter'].startswith('[Woda] Operacje'))['passed']
    assert topic(95)['m_cargo'] == 0


def test_underpowered_supplied_engine_is_not_replaced_by_automatic_mission_closure():
    p=dict(AIRCRAFT_PRESETS['ga_trainer'], design_iteration_mode='coupled', power_input_mode='fixed', engine_power_kw=.001)
    result=run_bipol_project(p)
    assert result['sizing']['design_point']['power_kw'] == .001
    assert result['performance']['paturski_p6']['range_endurance_6_5']['range_at_requested_speed_km'] is None
    assert not next(c for c in result['compliance_checks'] if c['parameter'].startswith('Lot poziomy'))['passed']


def test_climb_requirement_comes_from_jar_23_65_with_its_paragraph():
    result=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    check=next(c for c in result['compliance_checks'] if 'gradient ustalonego wznoszenia' in c['parameter'])
    assert check['rule']=='jar23.65a' and check['required']=='≥ 8.3 %'
    climb=result['performance']['climb']
    assert check['actual']==f"{100*climb['wy_max_ms']/(climb['v_wy_max_kmh']/3.6):.1f} %"


def test_iteration_does_not_count_configuration_drag_again_after_copying_p4(client):
    inputs=dict(AIRCRAFT_PRESETS['ga_trainer'], flap_type='junkers', slat_type='fixed_slot')
    answer=client.post('/api/coursework/iterate-polar',json=inputs)
    assert answer.status_code==200
    result=answer.get_json()['result']
    assert result['params']['preliminary_polar_includes_configuration']
    assert result['mass']['preliminary_polar']['cx0']==result['params']['cx0']
    assert result['sizing']['terms']['cx0']==result['params']['cx0']


def test_coupled_return_and_payload_drop_check_both_legs_without_spending_reserve():
    p=dict(AIRCRAFT_PRESETS['ga_trainer'], design_iteration_mode='coupled', m_cargo=200,
           payload_drop_kg=150, return_range_km=300)
    result=run_bipol_project(p)
    route=result['performance']['mission_range']
    assert result['design_iteration']['converged']
    assert len(route['legs'])==2 and route['passed']
    assert all(leg['available_km']>=leg['required_km'] for leg in route['legs'])
    assert route['total_available_km']>=p['range_km']
    mass=result['mass']
    phases={phase['key']:phase for phase in mass['mission_phases']}
    assert phases['drop']['payload_drop_kg']==150
    assert phases['return']['mass_start_kg']==phases['drop']['mass_end_kg']
    assert phases['landing']['mass_end_kg']==pytest.approx(mass['m_empty']+mass['m_crew']+mass['m_payload_landing']+mass['reserve_fuel_kg'],abs=.001)


def test_recreational_jet_range_edit_does_not_jump_to_unstable_mass_branch(client):
    original = run_bipol_project(topic(20))
    edited = run_bipol_project(dict(original['params'], range_km=1210))
    assert edited['design_iteration']['converged'], edited['design_iteration']
    assert edited['performance']['mission_range']['passed']
    assert original['mass']['m0'] < edited['mass']['m0'] < original['mass']['m0']*1.05
    answer = client.post('/api/coursework/iterate-polar', json=edited['params'])
    assert answer.status_code == 200
    variant = answer.get_json()['result']
    assert variant['design_iteration']['converged']
    assert variant['performance']['mission_range']['passed']


@pytest.mark.parametrize('number', [71, 74])
def test_heavy_cargo_uses_explicit_bay_instead_of_empty_passenger_cabin(number):
    result = run_bipol_project(topic(number))
    assert result['design_iteration']['converged']
    assert result['performance']['mission_range']['passed']
    fuselage = result['geometry']['fuselage']
    bay = fuselage['cargo_bay']
    assert bay['length_m'] == 8.5
    assert fuselage['diameter'] >= math.hypot(bay['width_m'], bay['height_m'])+.3
    assert fuselage['length'] >= bay['length_m']+4*fuselage['diameter']
    assert any(not c['passed'] for c in result['compliance_checks'] if 'misja specjalna' in c['parameter'])
    sheet = build_sheet(result)
    assert not {e['key']:(e['value'],e['computed']) for e in sheet.entries.values() if e['consistent'] is False}


@pytest.mark.parametrize('value', [8.5, '8.5'])
def test_partial_cargo_bay_cannot_silently_disable_geometric_sizing(value):
    with pytest.raises(ValueError, match='wszystkie trzy'):
        run_bipol_project(dict(topic(71), cargo_bay_length_m=value, cargo_bay_width_m='0', cargo_bay_height_m=0))


@pytest.mark.parametrize('entry', ALL_TOPICS, ids=lambda t: f"topic-{t['num']}")
def test_entire_official_catalogue_has_finite_closed_numerical_starting_designs(entry):
    result = run_bipol_project(entry['parameters'])
    json.dumps(result, allow_nan=False)
    assert result['design_iteration']['converged'], result['design_iteration']
    assert result['performance']['mission_range']['passed'], result['performance']['mission_range']
    # BIPOL_1: S_wet/S -> K_max -> eq. (3); the empty-mass law comes from
    # two points on the trend line of the SAME comparison sample.
    pp, mass = result['mass']['preliminary_polar'], result['mass']
    ta, law = result['bipol_projects']['p1']['trend_analysis'], mass['empty_mass_law']
    assert pp['mode'] == 'raymer' and pp['swet_ratio'] and pp['cx0_bounds']
    assert pp['cx0'] == pytest.approx(math.pi*pp['aspect_ratio']*pp['oswald_e']/(4*pp['kmax']**2))
    assert result['params']['cx0'] == pp['cx0']
    assert law['mode'] == 'trend'
    assert (law['A'], law['C']) == (ta['two_point']['A'], ta['two_point']['C'])
    assert set(law['aircraft_ids']) <= {x['id'] for x in ta['similar_aircraft']}
    # Physical climb must pay for height and drag and preserve phase continuity.
    # A clipped Corke comparison must never be mistaken for the actual fuel ratio.
    assumptions = mass['mission_assumptions']
    corke = assumptions.get('corke') or {}
    climb = assumptions.get('climb')
    if climb:
        phase = next(s for s in mass['mission_phases'] if s['key'] == 'climb')
        assert climb['model'] == 'energy' and not corke['used_for_balance']
        assert 0 < climb['fraction'] <= 1
        assert climb['fraction'] == pytest.approx(phase['fuel_fraction'])
        assert climb['fuel_kg'] == pytest.approx(phase['fuel_burn_kg'])
        dh = climb['altitude_end_m']-climb['altitude_start_m']
        assert climb['duration_s'] == pytest.approx(dh/climb['roc_ms'])
        if dh > 0:
            assert climb['fuel_kg'] > 0 and climb['potential_work_j'] > 0
            assert climb['drag_work_j'] > 0 and len(climb['nodes']) >= 2
        previous = None
        for state in mass['mission_phases']:
            if previous is not None:
                assert state['mass_start_kg'] == pytest.approx(previous)
            previous = state['mass_end_kg']
        assert sum(x['fuel_burn_kg'] for x in mass['mission_phases']) == pytest.approx(mass['fuel_burn_kg'])
    else:
        assert not corke or (corke['mode'] == 'corke' and not corke['provisional'] and corke['used_for_balance'])
