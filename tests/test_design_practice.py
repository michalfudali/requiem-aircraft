"""Refined sizing and design-practice requirements found in the 2026-10-30 audit."""
import pytest

from app import app
from calculations import refine_bipol_project, run_bipol_project
from calculations.bipol1 import refined_cruise_ld
from calculations.official_topics import ALL_TOPICS


def topic(num, **changes):
    return dict(next(t['parameters'] for t in ALL_TOPICS if t['num'] == num), **changes)


def check(result, prefix):
    return next(c for c in result['compliance_checks'] if c['parameter'].startswith(prefix))


@pytest.mark.parametrize('num', [10, 21, 40, 56, 68, 78, 88, 99])
def test_refined_sizing_meets_range_and_level_flight_at_the_required_cruise(num):
    first, refined, steps = refine_bipol_project(topic(num, design_iteration_mode='preliminary'))
    # The guideline estimate (0.94 Kmax) is optimistic at the required speed; the refined one is not.
    assert not check(first, 'Zasięg')['passed']
    assert check(refined, 'Zasięg')['passed'] and check(refined, 'Lot poziomy')['passed']
    assert refined['mass']['mission_assumptions']['ld_source'] == 'p4_integrated'
    polar = refined['mass']['mission_assumptions']['cruise_polar']
    assert polar['cx0'] == pytest.approx(refined['aerodynamics']['cx0_clean'], rel=5e-4)
    assert 1 <= len(steps) <= 40
    assert abs(steps[-1]['m0'] - steps[-2]['m0']) <= .002 * steps[-2]['m0'] if len(steps) > 1 else True


def test_refined_cruise_ld_is_used_only_where_it_was_found():
    p = dict(cruise_ld_p4=11.0, cruise_ld_p4_speed_kmh=240, cruise_ld_p4_altitude_m=2500,
             cruise_speed_kmh=240, cruise_altitude_m=2500)
    assert refined_cruise_ld(p) == 11.0
    assert refined_cruise_ld(dict(p, cruise_speed_kmh=260)) is None
    assert refined_cruise_ld(dict(p, cruise_altitude_m=3000)) is None


def test_refined_variant_api_reports_its_iterations():
    response = app.test_client().post('/api/coursework/iterate-polar', json=topic(40))
    body = response.get_json()
    assert response.status_code == 200 and body['iterations']
    assert body['mtow_after'] == body['iterations'][-1]['m0']


def test_horizontal_tail_is_sized_for_the_minimum_static_margin():
    r = run_bipol_project(topic(23, design_iteration_mode='preliminary'))
    assert r['params']['v_h'] > .7
    assert r['balance']['stability']['static_margin_aft_pct'] >= 5
    assert r['constraints']['parameter_states']['v_h']['state'] == 'derived'
    fixed = run_bipol_project(topic(23, design_iteration_mode='preliminary', locked_params=['n_pax', 'range_km', 'v_h']))
    assert fixed['params']['v_h'] == .7 and not fixed['balance']['stability']['is_stable']


def test_two_seat_ultralight_fits_the_ul_mass_limit():
    r = run_bipol_project(topic(17))
    assert r['mass']['m0'] <= 600
    assert .48 <= r['mass']['empty_fraction'] <= .56
    assert all(c['ok'] for c in r['easa_compliance']['checks'] if c['severity'] != 'warning')


def test_freighter_fuselage_holds_its_cargo():
    r = run_bipol_project(topic(71))  # 23 t: BWP-1 or Rosomak
    fuselage = r['geometry']['fuselage']
    assert fuselage['cargo_hold']['width'] > 3 and fuselage['length'] > 25 and fuselage['diameter'] > 3.5
    assert r['aerodynamics']['cx0_clean'] < .04
    assert run_bipol_project(topic(76))['geometry']['fuselage']['cargo_hold'] is None


def test_glider_tug_is_sized_for_climb_with_a_glider_in_tow():
    p = topic(31)
    assert p['tow_glider_mass_kg'] == 600 and p['tow_climb_rate_ms'] == 3
    first, refined, _ = refine_bipol_project(p)
    assert first['sizing']['design_point']['governing'] == 'holowanie szybowca'
    assert first['sizing']['curve_tow'] is not None
    assert check(refined, 'Wznoszenie z szybowcem')['passed']
    assert refined['performance']['tow']['speed_to_vs1'] >= 1.2
    solo = run_bipol_project(dict(p, tow_glider_mass_kg=0))
    assert solo['sizing']['design_point']['power_kw'] < first['sizing']['design_point']['power_kw']


def test_racer_has_a_race_speed_requirement_and_cruises_slower():
    p = topic(23)
    assert (p['v_max_required_kmh'], p['cruise_speed_kmh']) == (380, 300)
    _, refined, _ = refine_bipol_project(p)
    assert check(refined, 'Prędkość maksymalna')['passed']
    assert refined['performance']['speeds']['v_max_sl_kmh'] >= 380


def test_advanced_trainers_use_aerobatic_loads_and_course_power_caps():
    assert [topic(n)['category'] for n in (34, 37, 38)] == ['cs23_aerobatic'] * 3
    assert topic(32)['category'] == 'cs23_level1'
    r = run_bipol_project(topic(37))
    assert r['envelope']['limits']['n_max'] >= 6
    assert next(c for c in r['easa_compliance']['checks'] if 'Klasa' in c['name'])['ok']
    assert [topic(n).get('engine_power_limit_kw') for n in (32, 34, 36)] == [100, 200, None]
    assert check(run_bipol_project(topic(32)), 'Moc silnika')['passed']


def test_alternating_rounded_lift_coefficients_settle_on_the_larger_wing():
    r = run_bipol_project(topic(67))
    assert r['params']['cz_max_lnd'] == r['aerodynamics']['cz_max_lnd']


def test_refined_heavy_topic_moves_to_cs25():
    _, refined, _ = refine_bipol_project(topic(62))
    assert refined['mass']['m0'] > 8618
    assert (refined['params']['category'], refined['params']['n_crew']) == ('cs25_transport', 2)
