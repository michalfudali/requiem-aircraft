"""Design workflows and independent physical invariants found in the 2026-10 audit."""
import json
import math

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0, isa_atmosphere
from calculations.envelope import calculate_vn_envelope
from calculations.geometry import calculate_geometry
from calculations.mass import calculate_mass_sizing
from calculations.official_topics import ALL_TOPICS
from calculations.validation import validate_parameters
from calculations.flight_model import climb_time_to_height


@pytest.mark.parametrize('topic', ALL_TOPICS, ids=lambda t: str(t['num']))
def test_every_official_design_has_consistent_phases_geometry_and_reports(topic):
    r = run_bipol_project(topic['parameters'])
    json.dumps(r, allow_nan=False)
    p, g, a, m = (r[k] for k in ('params', 'geometry', 'aerodynamics', 'mass'))
    assert p['n_pax'] == topic['parameters']['n_pax']
    assert p['cz_max_to'] == a['cz_max_to']
    assert p['cz_max_lnd'] == a['cz_max_lnd']
    assert r['bipol_projects']['p5']['paturski_p6'] == r['performance']['paturski_p6']
    fractions = m['fuel_fractions_detail']
    expected_start = m['m0'] * fractions['warmup'] * fractions['takeoff'] * fractions['climb']
    cruise = r['performance']['paturski_p6']['range_endurance_6_5']
    assert cruise['m0_start_cr_kg'] == pytest.approx(expected_start, abs=.06)
    assert cruise['mk_end_cr_kg'] == pytest.approx(expected_start * fractions['cruise'], abs=.06)
    assert 0 < cruise['mk_end_cr_kg'] <= cruise['m0_start_cr_kg'] <= m['m0']
    for name, arm in [('horizontal_tail', 'l_h'), ('vertical_tail', 'l_v')]:
        assert g[name][arm] == pytest.approx(g[name]['x_ac_m'] - r['balance']['x_lemac_m'] - .25*g['wing']['mac'], abs=.016)
    rows = r['bipol_projects']['p3']['table_3_1_components']
    cg = sum(row['mass_kg']*row['x_m'] for row in rows)/sum(row['mass_kg'] for row in rows)
    takeoff_cg = next(state for state in r['balance']['loading_states'] if state['key']=='mtow')['xcg_m']
    assert cg == pytest.approx(takeoff_cg, abs=.004)
    assert r['performance']['landing']['mass_kg'] < m['m0']


def test_regional_stol_is_not_seeded_as_a_light_bush_plane():
    r = run_bipol_project(next(t['parameters'] for t in ALL_TOPICS if t['num']==82))
    assert r['params']['v_stall_kmh'] == 140
    assert r['params']['n_engines'] == 2
    assert r['geometry']['fuselage']['length'] < 35
    assert r['geometry']['wing']['b'] < 50
    assert (r['params']['takeoff_distance_m'], r['params']['landing_distance_m']) == (800, 700)


def topic(num):
    return next(t['parameters'] for t in ALL_TOPICS if t['num'] == num)


def test_topic_engine_count_is_explicit_and_follows_the_title():
    # The wizard copies topic parameters; a missing count kept the previous project's single engine.
    assert all('n_engines' in t['parameters'] for t in ALL_TOPICS)
    assert [topic(n)['n_engines'] for n in (37, 38, 40, 44, 45, 20, 103, 76)] == [1, 2, 1, 2, 2, 1, 2, 2]


def test_jet_topics_are_not_seeded_with_piston_stall_speeds():
    for num, low, high in ((20, 100, 120), (37, 140, 170), (49, 130, 160), (61, 130, 160), (100, 160, 190)):
        p = topic(num)
        assert low <= p['v_stall_kmh'] <= high, num
    r = run_bipol_project(topic(61))
    # A 10-seat business jet: CJ3/Phenom 300 have 27–29 m² and 16 m, not 70 m² and 24 m.
    assert r['geometry']['wing']['S'] < 35 and r['geometry']['wing']['b'] < 18
    assert r['mass']['m0'] / r['geometry']['wing']['S'] > 150


def test_ultralight_topics_meet_the_ul_stall_limit_without_an_invented_span():
    for num in range(15, 20):
        assert topic(num)['v_stall_kmh'] <= 45 * 1.852 and topic(num)['wing_input_mode'] == 'loading'
    r = run_bipol_project(topic(15))
    assert next(c for c in r['easa_compliance']['checks'] if 'VS0' in c['name'])['ok']


def test_aerobatic_topics_use_aerobatic_loads():
    assert [topic(n)['category'] for n in (27, 28, 29)] == ['cs23_aerobatic'] * 3
    assert topic(23)['category'] == 'cs23_level1'
    envelope = run_bipol_project(topic(28))['envelope']
    assert envelope['limits']['n_max'] >= 6
    # §23.333(b)(3): przy VD ujemna gałąź kończy się na −1 (akrobacyjna), a nie na 0 jak w normalnej.
    assert envelope['limits']['n_at_vd_neg'] == -1.0
    assert any(p['point'].startswith('E') and p['n'] == -1.0 for p in envelope['key_points'])
    assert run_bipol_project(topic(40))['envelope']['limits']['n_at_vd_neg'] == 0.0


def test_heavy_payload_topics_are_transport_category_with_two_pilots():
    for num in (67, 71, 91, 98):
        p = topic(num)
        assert (p['category'], p['n_crew']) == ('cs25_transport', 2), num
    assert topic(66)['category'] == 'cs23_level1'
    r = run_bipol_project(topic(68))
    assert r['mass']['m0'] > 8618 and all(c['ok'] for c in r['easa_compliance']['checks'] if 'MTOM' in c['name'])
    # The mass, not the seat count, puts a freighter in CS-25.
    assert not any('pasażerów' in c['name'] for c in r['easa_compliance']['checks'])


def test_design_cruising_speed_does_not_replace_operational_cas_and_mach_limits():
    level = lambda num: run_bipol_project(topic(num))['easa_compliance']['easa_performance_level']
    assert level(40).startswith('Nie określono')
    assert level(49).startswith('Nie określono')
    r = run_bipol_project(dict(topic(49), vmo_kcas=240, mmo=.55))
    assert r['easa_compliance']['easa_performance_level'] == 'Low Speed'


def test_topic_specific_payloads():
    boat = topic(95)  # four-seat touring flying boat carries people, not a ton of cargo
    assert (boat['aircraft_type'], boat['n_pax'], boat['m_cargo']) == ('piston_ga', 3, 0)
    assert topic(31)['n_pax'] == 0  # single-seat glider tug
    assert topic(30)['n_pax'] == 5


def test_known_empty_mass_fraction_changes_the_closed_mass_balance():
    base = AIRCRAFT_PRESETS['ga_trainer']
    light = run_bipol_project(dict(base, empty_mass_fraction=.5))
    heavy = run_bipol_project(dict(base, empty_mass_fraction=.65))
    assert heavy['mass']['m0'] > light['mass']['m0']
    for r, fraction in [(light,.5),(heavy,.65)]:
        assert r['mass']['m_empty']/r['mass']['m0'] == pytest.approx(fraction, abs=.0002)
        assert r['mass']['empty_mass_model']=='fixed_fraction'


def test_underpowered_aircraft_has_no_invented_level_flight_or_range():
    r=run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'], power_input_mode='fixed', engine_power_kw=.001))
    perf=r['performance']
    assert not perf['level_flight_available_sl']
    assert perf['speeds']['v_max_sl_kmh']==0
    assert perf['climb']['wy_max_ms'] < 0
    assert perf['range_and_endurance']['range_km']==0
    assert not next(c for c in r['compliance_checks'] if c['parameter'].startswith('Lot poziomy'))['passed']
    p5 = r['bipol_projects']['p5']
    assert all(row['range_km'] is None for row in p5['range_endurance_comparison'])
    assert 'nie spełnia' in p5['recommendations']
    assert p5['critical_evaluation_table_5_1'][2]['project_assumed'] is None
    assert p5['critical_evaluation_table_5_1'][5]['comment'].startswith('Niespełnione')


def test_sailplane_has_no_fictitious_propulsion_and_keeps_its_glide_polar():
    r=run_bipol_project(AIRCRAFT_PRESETS['glider_pw5'])
    assert r['bipol_projects']['p4']['paturski_propulsion']['engine_type']=='none'
    assert r['bipol_projects']['p4']['paturski_propulsion']['propeller_selection']=={}
    assert r['bipol_projects']['p4']['glide_polar']['w_min_ms'] < 10
    assert r['bipol_projects']['p4']['glide_polar']['points']
    assert all(row['range_km'] is None for row in r['bipol_projects']['p5']['range_endurance_comparison'])


def test_jet_breguet_tsfc_conversion_is_dimensionally_exact():
    r=run_bipol_project(AIRCRAFT_PRESETS['vlj_jet'])
    ranges=r['performance']['paturski_p6']['range_endurance_6_5']
    assert ranges['qe_paturski'] == pytest.approx(r['params']['sfc']*10/G0, abs=.00005)
    assert ranges['table_6_3']
    row=ranges['table_6_3'][0]
    # TSFC is fuel weight flow / thrust in 1/h: E = (L/D)/TSFC * ln(Wi/Wf).
    expected=row['cz']/row['cx']/r['params']['sfc']*math.log(ranges['m0_start_cr_kg']/ranges['mk_end_cr_kg'])
    assert row['t_breguet_h']==pytest.approx(expected,abs=.015)


def test_sensitivity_is_a_resolved_design_change_not_a_fixed_multiplier():
    r=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    rows=r['bipol_projects']['p2']['sensitivity']['table']
    changed=calculate_mass_sizing(dict(r['params'], range_km=r['params']['range_km']*1.1))
    assert rows[2]['d_mtow_kg']==pytest.approx(changed['m0']-r['mass']['m0'], abs=.11)
    assert rows[0]['d_mtow_kg'] > 0 and rows[1]['d_mtow_kg'] < 0


@pytest.mark.parametrize('mode', ['rectangular','elliptical','compound_trapezoid','trapezoidal'])
def test_planform_mac_location_and_control_area_follow_actual_outline(mode):
    p=dict(AIRCRAFT_PRESETS['ga_trainer'], wing_planform=mode, wing_area_m2=20, aspect_ratio=8, sweep_quarter_deg=20)
    g=calculate_geometry(1000,490.3325,p)
    w=g['wing']
    assert w['x_le_mac']==pytest.approx(w['y_mac']*math.tan(math.radians(20))+.25*(w['cr']-w['mac']),abs=.015)
    if mode=='elliptical':
        device=g['control_surfaces']['flaps']
        def primitive(eta):
            return .5*(eta*math.sqrt(1-eta**2)+math.asin(eta))
        area=w['cr']*w['b']*(primitive(device['eta_out'])-primitive(device['eta_in']))
        assert device['S_flapped_m2']==pytest.approx(area,abs=.04)


def test_cruise_tas_is_converted_before_plotting_eas_envelope():
    r=run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    perf={**r['performance'], 'speeds':{**r['performance']['speeds'],'v_cruise_kmh':900,'v_max_sl_kmh':1000}}
    p=dict(r['params'],cruise_altitude_m=11000)
    envelope=calculate_vn_envelope(r['mass']['m0'],r['geometry'],r['aerodynamics'],perf,p)
    assert envelope['speeds']['v_c_kmh']==pytest.approx(900*math.sqrt(isa_atmosphere(11000)['sigma']),abs=.1)


@pytest.mark.parametrize('engine,sfc', [('prop',.62),('prop',0),('jet',265),('jet',0)])
def test_engine_consumption_never_silently_changes_units(engine,sfc):
    with pytest.raises(ValueError,match='SFC'):
        validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'],engine_type=engine,sfc=sfc))


def test_uncomputed_checks_and_profile_polars_are_not_presented_as_measurements():
    r=run_bipol_project(AIRCRAFT_PRESETS['vlj_jet'])
    p3=r['bipol_projects']['p3']
    assert p3['blueprint_checks']['pilot_vision_angle_deg'] is None
    assert p3['blueprint_checks']['fan_intake_mach'] is None
    assert not p3['airfoil_200mm_table']
    assert all(c['cx_cz_proj'] is None for c in r['bipol_projects']['p2']['airfoil_selection']['candidates'])


@pytest.mark.parametrize('planform, divisor', [('rectangular', 6), ('elliptical', 8)])
def test_roll_damping_matches_independent_planform_integrals(planform, divisor):
    params = dict(AIRCRAFT_PRESETS['ga_trainer'], wing_planform=planform,
                  wing_area_m2=20, aspect_ratio=8, sweep_quarter_deg=0)
    geom = calculate_geometry(1000, 490.3325, params)
    ar = geom['wing']['AR']
    a = 2*math.pi*ar/(2+math.sqrt(4+ar*ar))
    assert geom['control_surfaces']['ailerons']['cl_p'] == pytest.approx(-a/divisor, abs=.0001)


def test_elliptical_unswept_wing_has_no_taper_polynomial_drag_penalty():
    from calculations.paturski_ml import paturski_project_2_wing
    params = dict(AIRCRAFT_PRESETS['ga_trainer'], wing_planform='elliptical', sweep_quarter_deg=0)
    geom = calculate_geometry(1000, 490.3325, params)
    aero = paturski_project_2_wing(geom, params, m0=1000)
    assert aero['delta_glauert'] == aero['tau_glauert'] == 0


def test_flap_span_changes_whole_aircraft_lift_and_sizing_consistently():
    base = dict(AIRCRAFT_PRESETS['ga_trainer'], flap_type='plain', slat_type='none')
    small = run_bipol_project(dict(base, flap_span_ratio=.2))
    large = run_bipol_project(dict(base, flap_span_ratio=.6))
    assert small['aerodynamics']['cz_max_lnd'] < large['aerodynamics']['cz_max_lnd']
    assert small['geometry']['wing']['S'] > large['geometry']['wing']['S']
    for r in (small, large):
        coverage = r['geometry']['control_surfaces']['flaps']['s_flapped_over_s']
        assert r['params']['cz_max_lnd'] == pytest.approx(r['params']['cz_max_clean'] + .60*coverage, abs=.005)
        assert r['params']['cz_max_lnd'] == r['aerodynamics']['cz_max_lnd']


def test_climb_time_integrates_actual_rate_and_does_not_invent_reachability():
    assert climb_time_to_height(3000, lambda h: 5) == pytest.approx(600)
    assert climb_time_to_height(5000, lambda h: 10-h/1000) == pytest.approx(1000*math.log(2), rel=.0001)
    assert climb_time_to_height(5000, lambda h: 5-h/1000) is None
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    rows = r['performance']['paturski_p6']['table_6_2_climb_and_ceilings']['altitudes_table']
    assert rows[0]['th_s'] == 0
    assert rows[-1]['th_s'] is None  # absolute ceiling: asymptotic, not zero time
    times = [row['th_s'] for row in rows if row['th_s'] is not None]
    assert times == sorted(times)


def test_report_range_methods_use_integrations_instead_of_fixed_percent_changes():
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    data = r['performance']['paturski_p6']['range_endurance_6_5']
    row = next(row for row in data['table_6_3'] if abs(row['v_kmh']-r['params']['cruise_speed_kmh']) < .06)
    methods = r['bipol_projects']['p5']['range_endurance_comparison']
    assert methods[1]['range_km'] == row['l_breguet_km']
    assert methods[1]['endurance_h'] == row['t_breguet_h']
    assert methods[2]['range_km'] == data['range_at_requested_speed_km']
    # For a propeller with constant BSFC and eta, constant-Cz range is independent of speed schedule.
    assert methods[0]['range_km'] == methods[1]['range_km']


def test_cs23_dive_speed_respects_vc_min_lower_bound():
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    # Artificially set a low operational cruise speed
    perf = {**r['performance'], 'speeds': {**r['performance']['speeds'], 'v_cruise_kmh': 120, 'v_max_sl_kmh': 150}}
    envelope = calculate_vn_envelope(r['mass']['m0'], r['geometry'], r['aerodynamics'], perf, r['params'])
    v_c_kmh = envelope['speeds']['v_c_kmh']
    v_d_kmh = envelope['speeds']['v_d_kmh']
    assert v_d_kmh >= 1.25 * v_c_kmh
    # Must also respect vd_factor * vc_min
    ws = r['mass']['m0'] * G0 / r['geometry']['wing']['S']
    ws_psf = ws / 47.88026
    vc_min_kts = 33.0 * math.sqrt(max(1.0, ws_psf))
    v_c_min_kmh = vc_min_kts * 1.852
    assert v_d_kmh >= 1.40 * v_c_min_kmh - 1.0


def test_cs23_load_factor_enforces_statutory_2_5_floor():
    from calculations.polish_law import limit_load_factors
    # Heavy commuter category aircraft under CS-23
    n_pos, n_neg, ref = limit_load_factors("cs23_commuter", 25000.0)
    assert n_pos >= 2.50
    assert n_pos == pytest.approx(2.50, abs=0.01)


def test_composite_vn_envelope_polygon_exists_and_bounds_points():
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    env = r['envelope']
    assert 'composite_polygon' in env
    assert len(env['composite_polygon']) >= 30
    # Every composite load factor must be within physical dimensioning limits
    n_dim_pos = env['limits']['n_dimensioning_pos']
    n_dim_neg = env['limits']['n_dimensioning_neg']
    for pt in env['composite_polygon']:
        assert pt['n'] <= n_dim_pos + 0.05
        assert pt['n'] >= n_dim_neg - 0.05


def test_grass_runway_friction_increases_takeoff_distance():
    from calculations.runway import takeoff_distance
    ws = 600.0
    cz_max = 1.6
    cx0 = 0.03
    k = 0.05
    engine = 'prop'
    loading = 70.0  # W/N
    d_paved = takeoff_distance(ws, cz_max, cx0, k, engine, loading, mu_ground=0.03)
    d_grass = takeoff_distance(ws, cz_max, cx0, k, engine, loading, mu_ground=0.055)
    assert d_paved['available'] and d_grass['available']
    assert d_grass['ground_roll_m'] > d_paved['ground_roll_m']
    assert d_grass['distance_to_15m'] > d_paved['distance_to_15m']

