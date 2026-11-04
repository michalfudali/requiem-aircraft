"""One independent family, one real variant, identical selection at every entry point."""
from copy import deepcopy

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.reference_selection import best_variants, family_groups
from calculations.trends import derived, select_references


def aircraft(aid, family='Example', model=None, **changes):
    return derived(dict(id=aid, family=family, model=model or aid, source_id='user',
                        source_references='Documented test observation', aircraft_type='motoglider',
                        engine_type='prop', n_engines=1, m0=600, me=300, s=12, b=15,
                        **changes))


def test_family_aliases_are_joined_across_sources_and_case_without_guessing_manufacturers():
    rows = [aircraft('a', family='A-10', model='Maker Model 10'),
            aircraft('b', family='A 10', model='Model 10 B'),
            aircraft('c', family='Other label', model='Maker Model 10'),
            aircraft('d', family='Other label', model='Model 10 C'),
            aircraft('e', family=None, model='Maker Model 20')]
    groups = family_groups(rows)
    assert len({groups[r['id']][0] for r in rows[:4]}) == 1
    assert groups['e'][0] != groups['a'][0]
    assert family_groups(rows[::-1]) == groups


def test_glider_choice_uses_lift_drag_then_lowest_sink_and_never_hybridizes_rows():
    rows = [aircraft('slow', ld_max=40, w_z_min_ms=.3, range_km=2000),
            aircraft('best', ld_max=50, w_z_min_ms=.5, range_km=1000),
            aircraft('same_ld', ld_max=50, w_z_min_ms=.6, range_km=3000)]
    original = deepcopy(rows)
    selected = best_variants(rows, family_groups(rows), 'motoglider')
    assert len(selected) == 1 and selected[0]['id'] == 'best'
    assert selected[0]['range_km'] == 1000
    assert selected[0]['variant_selection']['omitted_ids'] == ['same_ld', 'slow']
    assert rows == original
    assert best_variants(rows[::-1], family_groups(rows), 'motoglider') == selected


def test_airplane_choice_uses_cruise_then_range_then_climb_not_largest_mass():
    rows = [aircraft('heavy', v_cruise_kmh=200, range_km=2000),
            aircraft('short', v_cruise_kmh=250, range_km=500),
            aircraft('low_climb', v_cruise_kmh=250, range_km=1000, climb_rate_ms=2),
            aircraft('best', v_cruise_kmh=250, range_km=1000, climb_rate_ms=4)]
    assert best_variants(rows, family_groups(rows), 'piston_ga')[0]['id'] == 'best'
    jets = [aircraft('fast', cruise_mach=.85, range_km=1000),
            aircraft('far', cruise_mach=.8, range_km=5000)]
    assert best_variants(jets, family_groups(jets), 'jet_business')[0]['id'] == 'fast'
    jets = [aircraft('fast', v_cruise_kmh=850, range_km=1000),
            aircraft('far', v_cruise_kmh=800, range_km=5000)]
    assert best_variants(jets, family_groups(jets), 'jet_business')[0]['id'] == 'fast'


def test_missing_or_nonfinite_performance_is_not_an_invented_advantage():
    rows = [aircraft('unknown', ld_max=None), aircraft('nan', ld_max=float('nan')),
            aircraft('known', ld_max=35)]
    assert best_variants(rows, family_groups(rows), 'motoglider')[0]['id'] == 'known'
    rows = [aircraft('a-unknown'), aircraft('z-invalid', ld_max=float('nan'))]
    assert best_variants(rows, family_groups(rows), 'motoglider')[0]['id'] == 'a-unknown'
    rows = [aircraft('z', year=2020), aircraft('a', year=2020), aircraft('old', year=2010)]
    assert best_variants(rows, family_groups(rows), 'motoglider')[0]['id'] == 'a'


def test_deduplication_precedes_mass_limit_and_manual_ids_select_families(monkeypatch):
    rows = [aircraft('near-inferior', ld_max=30), aircraft('far-best', ld_max=50),
            aircraft('other', family='Independent', ld_max=40)]
    rows[1]['m0'] = 900
    rows[2]['m0'] = 650
    monkeypatch.setattr('calculations.trends.load_aircraft', lambda: rows)
    params = dict(aircraft_type='motoglider', engine_type='prop', _reference_mass=600, trend_nearest_count=2)
    assert {r['id'] for r in select_references(params)} == {'far-best', 'other'}
    for ids in (['near-inferior'], ['near-inferior', 'far-best']):
        chosen = select_references(dict(params, trend_aircraft_ids=ids, trend_weighting='variant'))
        assert [r['id'] for r in chosen] == ['far-best']
    assert select_references(dict(params, trend_aircraft_ids=[])) == []


def test_best_variant_respects_source_engine_and_date_filters(monkeypatch):
    rows = [aircraft('old', ld_max=35, year=2000), aircraft('new', ld_max=50, year=2020),
            aircraft('twin', ld_max=60, year=2020)]
    rows[0]['source_id'] = 'cado'
    rows[2]['n_engines'] = 2
    monkeypatch.setattr('calculations.trends.load_aircraft', lambda: rows)
    params = dict(aircraft_type='motoglider', engine_type='prop', trend_nearest_count=0)
    assert select_references(dict(params, trend_year_max=2010))[0]['id'] == 'old'
    assert select_references(dict(params, trend_source='cado'))[0]['id'] == 'old'
    assert select_references(dict(params, trend_engine_count=1))[0]['id'] == 'new'


@pytest.mark.parametrize('preset', ['pzl_kos', 'motoglider_aos', 'regional_turboprop', 'vlj_jet', 'glider_pw5', 'uav_tactical'])
def test_project_and_wizard_use_one_variant_per_family_in_all_analyses(client, preset):
    params = AIRCRAFT_PRESETS[preset]
    result = run_bipol_project(params)
    analysis = result['bipol_projects']['p1']['trend_analysis']
    rows = analysis['similar_aircraft']
    assert analysis['selected_n'] == analysis['families_n'] == len({r['family_key'] for r in rows})
    assert all(r['variant_selection']['policy'] == 'best_in_family' for r in rows)
    response = client.post('/api/trends/suggestions', json=params)
    assert response.status_code == 200
    assert response.get_json()['sample'] == analysis['sample']
    assert response.get_json()['suggestions'] == analysis['suggestions']
    selected_models = {r['model'] for r in rows}
    assert all({p['model'] for p in t['points']} <= selected_models
               for t in [*analysis['time_trends'], *analysis['relationships']])


def test_catalog_aliases_cannot_reintroduce_multiple_skyhawks_or_sinuses():
    ga = select_references(dict(aircraft_type='piston_ga', engine_type='prop', trend_nearest_count=0))
    assert len([r for r in ga if r['family_key'] == 'c172']) == 1
    mg = select_references(dict(aircraft_type='motoglider', engine_type='prop', trend_nearest_count=0))
    assert len([r for r in mg if r['family_key'] == 'sinus']) == 1


def test_new_records_without_a_family_do_not_group_a_whole_manufacturer(client):
    for number in (10, 20):
        response = client.post('/api/aircraft', json=dict(
            id=f'family-default-{number}', model=f'Example Manufacturer {number}', manufacturer='Example Manufacturer',
            aircraft_type='piston_ga', engine_type='prop', m0=1000, me=500))
        assert response.status_code == 201
    rows = select_references(dict(aircraft_type='piston_ga', engine_type='prop',
                                  trend_source='user', trend_nearest_count=0))
    created = [r for r in rows if r['id'].startswith('family-default-')]
    assert len(created) == 2 and len({r['family_key'] for r in created}) == 2
