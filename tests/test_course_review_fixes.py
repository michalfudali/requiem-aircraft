"""Regressions for the 2026-10-23 subject-matter review: certification envelopes,
sailplane drag, course characteristics (P3/P4), service ceiling, costs and P2/P4/P5 consistency."""
import math

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.atmosphere import G0, isa_atmosphere
from calculations.costs import calculate_costs
from calculations.envelope import cs23_speed_factors
from calculations.instructor import POLAR_CONSISTENCY_TOLERANCE
from calculations.paturski_ml import default_retractable_gear
from calculations.validation import validate_parameters


@pytest.fixture(scope='module')
def results():
    return {name: run_bipol_project(params) for name, params in AIRCRAFT_PRESETS.items()}


def test_sailplane_envelope_uses_cs22_factors_gusts_and_geometric_chord(results):
    r = results['glider_pw5']
    env, wing = r['envelope'], r['geometry']['wing']
    lim, spd, gf = env['limits'], env['speeds'], env['gust_factors']
    assert lim['basis'] == 'CS-22'
    assert (lim['n_max'], lim['n_at_vd_pos'], lim['n_at_vd_neg'], lim['n_min']) == (5.3, 4.0, -1.5, -2.65)
    assert spd['v_c_kmh'] is None and spd['v_b_kmh'] == spd['v_a_kmh']
    assert spd['v_a_kmh'] == pytest.approx(spd['v_s_kmh'] * math.sqrt(5.3), abs=.2)
    # CS 22.335(d)(1): VD ≥ 18·∛((W/S [daN/m²])/Cd,min) km/h
    ws_dan = r['mass']['m0'] * G0 / 10 / wing['S']
    assert spd['v_d_kmh'] >= 18 * (ws_dan / r['aerodynamics']['cx0_clean']) ** (1 / 3) - .2
    assert [(g['speed'], g['u_ms']) for g in gf['gusts']] == [('VB', 15.0), ('VD', 7.5)]
    assert gf['chord_m'] == pytest.approx(wing['S'] / wing['b'], abs=.002)
    assert env['flap']['n_flap'] == 4.0 and env['flap']['v_f_kmh'] >= 1.4 * spd['v_s_kmh'] - .2
    assert [p['point'][0] for p in env['key_points']] == ['S', 'A', 'B', 'D', 'E', 'G']


@pytest.mark.parametrize('category, ws, vc0, vd0', [
    ('normal', 20, 33.0, 1.40), ('utility', 20, 33.0, 1.50), ('aerobatic', 20, 36.0, 1.55),
    ('normal', 100, 28.6, 1.35), ('aerobatic', 100, 28.6, 1.35), ('normal', 60, 30.8, 1.375)])
def test_cs23_speed_factors_decrease_linearly_above_20_psf(category, ws, vc0, vd0):
    assert cs23_speed_factors(category, ws) == pytest.approx((vc0, vd0), abs=1e-9)


def test_transport_dive_speed_follows_cs25_and_light_jet_uses_reduced_cs23_factor(results):
    env = results['regional_turboprop']['envelope']
    assert env['limits']['basis'] == 'CS-25'
    assert env['speeds']['v_d_kmh'] == pytest.approx(env['speeds']['v_c_kmh'] / .8, abs=.2)
    vlj = results['vlj_jet']['envelope']
    assert vlj['limits']['basis'] == 'CS-23' and '32.2·√(W/S)' in vlj['limits']['speed_rule']


@pytest.mark.parametrize('name, k_min', [('glider_pw5', 23), ('motoglider_aos', 21)])
def test_sailplane_drag_is_not_calibrated_to_powered_ga_statistics(results, name, k_min):
    r = results[name]
    p3 = r['aerodynamics']['paturski_p3']
    rows = {row['lp']: row for row in p3['table_3_1_parasite']}
    assert rows[2]['cx_s_m2'] == 0  # canopy lies inside the fuselage frontal area
    assert rows[1]['cx_j'] <= .15
    assert p3['k_interf'] == (.02 if name == 'glider_pw5' else .04)
    assert p3['statistical_benchmarks_abc']['summary']['matched_a_lp'] is None
    assert r['aerodynamics']['k_max'] >= k_min
    assert r['geometry']['fuselage']['diameter'] <= 1.10
    assert r['aerodynamics']['cx0_clean'] < .02


def test_glider_has_no_engine_items_and_a_partly_recessed_single_wheel(results):
    rows = {row['lp']: row for row in results['glider_pw5']['aerodynamics']['paturski_p3']['table_3_1_parasite']}
    assert rows[6]['cx_s_m2'] == 0
    assert 0 < rows[4]['cx_s_m2'] < .01


def test_uav_fuselage_scales_with_mass_and_has_no_canopy(results):
    small, large = results['uav_tactical'], results['uav_male']
    assert small['geometry']['fuselage']['diameter'] < large['geometry']['fuselage']['diameter'] < 1.0
    for r in (small, large):
        rows = {row['lp']: row for row in r['aerodynamics']['paturski_p3']['table_3_1_parasite']}
        assert rows[2]['cx_s_m2'] == 0


@pytest.mark.parametrize('params, expected', [
    ({'aircraft_type': 'glider'}, False), ({'aircraft_type': 'motoglider', 'engine_type': 'prop'}, False),
    ({'aircraft_type': 'piston_ga', 'engine_type': 'prop', 'cruise_speed_kmh': 180}, False),
    ({'aircraft_type': 'piston_ga', 'engine_type': 'prop', 'cruise_speed_kmh': 300}, True),
    ({'aircraft_type': 'turboprop_regional', 'engine_type': 'prop', 'cruise_speed_kmh': 180}, True),
    ({'aircraft_type': 'uav', 'engine_type': 'jet', 'cruise_speed_kmh': 180}, True),
    ({'aircraft_type': 'turboprop_regional', 'retractable_gear': False}, False)])
def test_one_landing_gear_rule_is_shared_by_all_drag_models(params, expected):
    assert default_retractable_gear(params) is expected


def test_motoglider_landing_polar_does_not_add_retracted_gear_drag_twice(results):
    a = results['motoglider_aos']['aerodynamics']
    landing_flap = a['flap_configurations']['landing']['delta_cx0']
    assert a['cx0_lnd'] == pytest.approx(a['cx0_clean'] + landing_flap, abs=2e-4)


@pytest.mark.parametrize('mode, expected', [('fixed', False), ('retractable', True)])
def test_gear_selector_overrides_the_class_rule(mode, expected):
    p = validate_parameters({**AIRCRAFT_PRESETS['ga_trainer'], 'gear_retraction': mode})
    assert p['retractable_gear'] is expected
    assert 'retractable_gear' not in validate_parameters({**AIRCRAFT_PRESETS['ga_trainer'], 'gear_retraction': 'auto'})


def test_wing_characteristics_give_cz_cm_and_cx_against_alpha(results):
    r = results['ga_trainer']
    p2 = r['aerodynamics']['paturski_p2']
    rows = r['bipol_projects']['p3']['wing_alpha_table']
    assert [row['alpha_deg'] for row in rows] == sorted(row['alpha_deg'] for row in rows)
    for row in rows:
        assert row['cm_le'] == pytest.approx(p2['cm_sa_profile'] - p2['x_sa_bar'] * row['cz'], abs=1e-4)
    assert r['bipol_projects']['p3']['isolated_wing_aero']['cm_0_wing'] == p2['cm_sa_profile']


def test_aircraft_characteristics_cover_both_extreme_cg_positions(results):
    r = results['ga_trainer']
    cc = r['bipol_projects']['p4']['cg_characteristics']
    cm = cc['cm_model']
    assert cm['x_fwd_pct'] == r['balance']['cg_range']['forward_pct']
    assert cm['x_aft_pct'] == r['balance']['cg_range']['aft_pct']
    assert cm['dcm_dcz_fwd'] < cm['dcm_dcz_aft'] < 0  # forward CG is more stable
    a, b = cc['alpha_table'][3], cc['alpha_table'][-1]
    slope_fwd = (b['cm_fwd'] - a['cm_fwd']) / (b['cz'] - a['cz'])
    assert slope_fwd == pytest.approx(cm['dcm_dcz_fwd'], abs=2e-3)
    assert all(row['e'] == pytest.approx(row['cz'] ** 3 / row['cx'] ** 2, rel=.02) for row in cc['alpha_table'] if row['cz'] > .2)
    fwd, aft = cc['speed_polars']['forward'], cc['speed_polars']['aft']
    assert fwd['w_min_ms'] > aft['w_min_ms'] and fwd['k_max'] < aft['k_max']  # trim drag
    points = r['bipol_projects']['p4']['glide_polar']['points']
    assert any(p['w_sink_fwd_ms'] is not None and p['w_sink_fwd_ms'] > p['w_sink_aft_ms'] for p in points)


def test_speed_polar_obeys_glide_equilibrium(results):
    cc = results['glider_pw5']['bipol_projects']['p4']['cg_characteristics']
    S = results['glider_pw5']['geometry']['wing']['S']
    for p in cc['speed_polars']['aft']['points']:
        v = p['v_kmh'] / 3.6
        lift = .5 * cc['rho'] * v ** 2 * S * math.hypot(p['cz'], p['cx'])
        assert lift == pytest.approx(cc['mass_kg'] * G0, rel=.01)
        assert p['w_ms'] == pytest.approx(v * p['cx'] / math.hypot(p['cz'], p['cx']), rel=.01)


def test_service_ceiling_is_defined_by_half_metre_per_second_for_jets_too(results):
    ceilings = results['vlj_jet']['performance']['paturski_p6']['table_6_2_climb_and_ceilings']['ceilings']
    assert ceilings['w_crit_ceiling_ms'] == .5


def test_costs_reproduce_1986_coefficients_and_extrapolate_linearly():
    params = {'aircraft_type': 'piston_ga', 'engine_type': 'prop', 'n_engines': 1}
    w_lb, v_kt = 1000 * 2.20462, 300 * .539957
    c1986 = calculate_costs({**params, 'cost_year': 1986}, 1000, 300, power_kw=150)
    h_e = 4.86 * w_lb ** .777 * v_kt ** .894 * 4 ** .163
    assert c1986['rdte']['hours']['E'] == pytest.approx(h_e, rel=1e-3)
    assert c1986['rates_usd_h'] == {'E': 59.1, 'T': 61.7, 'ML': 55.4, 'QC': 50.1}
    assert c1986['production']['items_usd']['C_D'] == 0 and c1986['production']['items_usd']['C_FT'] == 0
    c1970 = calculate_costs({**params, 'cost_year': 1970}, 1000, 300, power_kw=150)
    c2002 = calculate_costs({**params, 'cost_year': 2002}, 1000, 300, power_kw=150)
    assert c2002['rates_usd_h']['E'] == pytest.approx(2 * 59.1 - 16.0)
    assert c2002['rdte']['hours']['E'] == pytest.approx(2 * c1986['rdte']['hours']['E'] - c1970['rdte']['hours']['E'], abs=2)
    # Formula 5.10 with C_P = 0
    # Galiński (2016), rozdz. 2.7: samolot lekki amortyzuje rozwój na ok. 150 egzemplarzach.
    assert c2002['amortization_count'] == 150
    expected = c2002['production']['total_usd'] / 250 + c2002['rdte']['total_usd'] / 150
    assert c2002['unit_cost_usd'] == pytest.approx(expected, abs=1)


def test_cost_coefficients_match_bipol2_tables():
    # BIPOL_2 (Galiński, Studium wykonalności), s. 7–10: wzory (13)–(21) i tab. 5.9.
    from calculations.costs import COEFFICIENTS, RATES, QC_FACTOR, QC_FACTOR_CARGO, ENGINE_C1_1970
    assert COEFFICIENTS['H_E'] == {1970: (0.027, 0.791, 1.526, 0.183), 1986: (4.860, 0.777, 0.894, 0.163)}
    assert COEFFICIENTS['C_D'] == {1970: (0.00549, 0.873, 1.890, 0.346), 1986: (45.42, 0.630, 1.300, 0)}
    assert COEFFICIENTS['H_ML'] == {1970: (20.348, 0.740, 0.543, 0.524), 1986: (7.370, 0.820, 0.484, 0.641)}
    assert COEFFICIENTS['C_MM'] == {1970: (18.47, 0.689, 0.624, 0.792), 1986: (11.00, 0.921, 0.621, 0.799)}
    assert COEFFICIENTS['H_T'] == {1970: (2.79, 0.764, 0.899, 0.178, 0.066), 1986: (5.99, 0.777, 0.696, 0.263, 0)}
    assert COEFFICIENTS['C_FT'] == {1970: (0.000714, 1.160, 1.371, 1.281), 1986: (1243.03, 0.325, 0.822, 1.210)}
    assert RATES == {1970: {'E': 16.0, 'T': 11.5, 'ML': 10.0, 'QC': 10.0}, 1986: {'E': 59.1, 'T': 61.7, 'ML': 55.4, 'QC': 50.1}}
    assert (QC_FACTOR, QC_FACTOR_CARGO) == (0.13, 0.076)
    assert ENGINE_C1_1970 == {'turbojet': 109.0, 'turbofan': 130.0}


def test_cost_assumptions_come_from_the_project():
    params = {'aircraft_type': 'turboprop_regional', 'engine_type': 'prop', 'n_engines': 2}
    base = calculate_costs(params, 6000, 450, power_kw=1600)
    cargo = calculate_costs({**params, 'cost_qc_factor': 0.076}, 6000, 450, power_kw=1600)
    assert base['qc_factor'] == 0.13 and cargo['qc_factor'] == 0.076
    assert cargo['production']['hours']['QC'] == pytest.approx(0.076 / 0.13 * base['production']['hours']['QC'], abs=1)
    assert cargo['production']['hours']['ML'] == base['production']['hours']['ML']
    small = calculate_costs({**params, 'cost_n_production': 100, 'cost_n_amortization': 80, 'cost_profit_pct': 5}, 6000, 450, power_kw=1600)
    assert (small['series_count'], small['amortization_count'], small['profit_pct']) == (100, 80, 5)
    assert small['unit_cost_usd'] == pytest.approx(small['production']['total_usd'] / 100 + small['rdte']['total_usd'] / 80, abs=1)


def test_turbojet_uses_its_own_1970_engine_coefficient():
    params = {'aircraft_type': 'jet_business', 'engine_type': 'jet', 'n_engines': 1, 'cost_year': 1970}
    fan = calculate_costs(params, 1000, 600, thrust_kn=5, mach_max=.6)
    jet = calculate_costs({**params, 'bypass_ratio': 0}, 1000, 600, thrust_kn=5, mach_max=.6)
    assert jet['engine_price_usd'] == pytest.approx(fan['engine_price_usd'] * 109 / 130, abs=1)
    assert 'turboodrzutowy' in jet['engine_basis'] and 'turbowentylatorowy' in fan['engine_basis']


def test_transport_topics_use_the_cargo_quality_control_factor_and_cost_inputs_are_validated():
    from calculations.official_topics import ALL_TOPICS
    topics = {t['num']: t for t in ALL_TOPICS}
    assert topics[68]['parameters']['cost_qc_factor'] == 0.076
    assert 'cost_qc_factor' not in topics[78]['parameters']
    ok = validate_parameters({'cost_n_production': 300, 'cost_n_amortization': 250, 'cost_qc_factor': '0.076'})
    assert ok['cost_qc_factor'] == 0.076
    with pytest.raises(ValueError, match='N_am'):
        validate_parameters({'cost_n_production': 100, 'cost_n_amortization': 250})
    with pytest.raises(ValueError, match='całkowita'):
        validate_parameters({'cost_n_production': 100.5})
    with pytest.raises(ValueError, match='cost_year'):
        validate_parameters({'cost_year': None})


def test_turbofan_price_uses_formula_15_and_glider_cost_has_a_speed(results):
    c = results['vlj_jet']['bipol_projects']['p2']['cost_analysis']
    assert c['engine_basis'].startswith('wzór (15)')
    glider = results['glider_pw5']['bipol_projects']['p2']['cost_analysis']
    assert glider['engine_price_usd'] == 0 and glider['vmax_knots'] > 100


def test_p2_and_p4_polars_are_checked_for_consistency(results):
    for name, r in results.items():
        check = [c for c in r['instructor_review']['checks'] if c['key'] == 'polar_consistency']
        k_p2 = r['mass']['mission_assumptions'].get('k_max_preliminary')
        if not k_p2:
            continue
        assert check[0]['passed'] == (abs(k_p2 - r['aerodynamics']['k_max']) <= POLAR_CONSISTENCY_TOLERANCE * r['aerodynamics']['k_max'])
        # The graph estimate is retained even if a detailed P4 polar disagrees;
        # the review flags the actual discrepancy instead of clipping the reading.
        assert k_p2 == pytest.approx(r['mass']['preliminary_polar']['kmax'])


def test_p5_explains_why_range_or_cruise_requirements_fail(results):
    for name, r in results.items():
        p5 = r['bipol_projects']['p5']
        failed = [row for row in p5['critical_evaluation_table_5_1'] if row['comment'] == 'Niespełnione wymaganie projektu']
        if any(row['param'].startswith(('Zasięg', 'Prędkość przelotowa')) for row in failed):
            assert p5['performance_findings'], name
    finding = results['regional_turboprop']['bipol_projects']['p5']['performance_findings'][0]
    assert '0,94·Kmax' in finding


def test_wing_cz_max_follows_from_schrenk_and_the_profile_maximum():
    """Opis Projektu 3: Cz_max płata ze Schrenka = c_z,max profilu / (c_z/C_z)_max (bez stałej 1,06)."""
    from calculations.bipol_projects import schrenk_cz_max
    assert schrenk_cz_max(0, 1.45, 1.06) == {'airfoil_cz_max': None, 'airfoil_cz_max_required': pytest.approx(1.537),
                                             'cz_max_wing_est': None, 'cz_max_consistent': None}
    given = schrenk_cz_max(1.6, 1.45, 1.06)
    assert given['cz_max_wing_est'] == pytest.approx(1.6 / 1.06, abs=1e-3) and given['cz_max_consistent']
    assert schrenk_cz_max(1.5, 1.45, 1.06)['cz_max_consistent'] is False
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'airfoil_cz_max': 1.6}
    summary = run_bipol_project(validate_parameters(params))['bipol_projects']['p3']['schrenk_summary']
    assert summary['cz_max_wing_est'] == pytest.approx(1.6 / summary['max_cz1'], abs=1e-3)
    with pytest.raises(ValueError, match='airfoil_cz_max'):
        validate_parameters({'airfoil_cz_max': 5})


def test_amortization_default_and_offer_prices_follow_galinski_2016():
    from calculations.costs import default_amortization_count
    assert default_amortization_count({'category': 'cs23_level2'}) == 150
    assert default_amortization_count({'category': 'cs23_commuter'}) == 250
    assert default_amortization_count({'category': 'cs25_transport'}) == 250
    base = {'aircraft_type': 'piston_ga', 'engine_type': 'prop', 'n_engines': 1, 'category': 'cs23_level2'}
    assert calculate_costs({**base, 'cost_n_production': 100}, 800, 250, power_kw=120)['amortization_count'] == 100
    estimate = calculate_costs({**base, 'engine_price_usd': 0, 'avionics_price_usd': 0}, 800, 250, power_kw=120)
    offer = calculate_costs({**base, 'engine_price_usd': 31000, 'avionics_price_usd': 12000}, 800, 250, power_kw=120)
    assert estimate['engine_basis'].startswith('założenie spoza wzoru (15)') and estimate['avionics_price_usd'] == 28000
    assert offer['engine_price_usd'] == 31000 and 'oferty' in offer['engine_basis'] and offer['avionics_price_usd'] == 12000
    assert offer['production']['items_usd']['C_EN'] == 250 * (31000 + 12000)
