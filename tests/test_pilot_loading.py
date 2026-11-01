"""Independent lever examples, exact admissible intervals and real project data."""
from copy import deepcopy

import pytest

from calculations import run_bipol_project
from calculations.calc_sheet import build_sheet
from calculations.pilot_loading import calculate_pilot_loading, intersect_limits
from calculations.presets import AIRCRAFT_PRESETS


def example():
    # Fixed 180 kg airframe; 332 kg m moment. Crew at 1.13 m, 80 kg nominal.
    mass = dict(n_crew=1, m_crew=80., m0=260.)
    geom = dict(wing=dict(mac=.7))
    balance = dict(x_lemac_m=1.5, arms=dict(crew=1.13),
                   neutral_point=dict(x_n_mac_pct=45.), cg_range=dict(delta_pct=15.),
                   loading_states=[dict(key='oew', name='Pusty', mass_kg=180., moment_kg_m=332.),
                                   dict(key='mtow', name='Start', mass_kg=260., moment_kg_m=422.4)])
    return mass, geom, balance


def test_lever_example_and_overweight_pilot():
    study = calculate_pilot_loading(*example())
    case = study['cases'][0]
    assert case['light']['mass_kg'] == 235.
    assert case['light']['moment_kg_m'] == pytest.approx(394.15)
    assert case['light']['xcg_m'] == pytest.approx(394.15/235)
    assert case['heavy']['mass_excess_kg'] == 30.
    assert case['heavy']['checks']['mass'] is False
    assert study['common_interval'] == dict(min_kg=55., max_kg=80.)
    assert case['nominal']['passed']
    assert case['nominal']['sensitivity_pct_per_kg'] < 0


@pytest.mark.parametrize('constraints, expected', [
    ([dict(a=1., b=-70.), dict(a=-1., b=90.)], dict(min_kg=70., max_kg=90.)),
    ([dict(a=1., b=-70.), dict(a=-1., b=70.)], dict(min_kg=70., max_kg=70.)),
    ([dict(a=0., b=-1.)], None),
    ([dict(a=0., b=0.)], dict(min_kg=55., max_kg=110.)),
    ([dict(a=-1., b=54.)], None),
    ([dict(a=1., b=-111.)], None),
])
def test_exact_interval_including_constant_and_singleton_limits(constraints, expected):
    assert intersect_limits(constraints, [55., 110.]) == expected


def test_pilot_at_base_cg_has_zero_sensitivity():
    mass, geom, bal = example()
    bal['arms']['crew'] = 332/180
    bal['loading_states'][1]['moment_kg_m'] = 332+80*332/180
    case = calculate_pilot_loading(mass, geom, bal)['cases'][0]
    assert case['light']['xcg_m'] == pytest.approx(case['heavy']['xcg_m'])
    assert case['nominal']['sensitivity_pct_per_kg'] == pytest.approx(0, abs=1e-12)


@pytest.fixture(scope='module', params=list(AIRCRAFT_PRESETS))
def design(request):
    return run_bipol_project(AIRCRAFT_PRESETS[request.param])


def test_real_projects_match_independent_loading_states_and_variants(design):
    bal = design['balance']; study = bal['pilot_loading']
    if not study['available']:
        assert design['mass']['n_crew'] == 0
        return
    variants = {s['key']: s for s in bal['pilot_variants']}
    original = {s['key']: s for s in bal['loading_states']}
    assert {c['key'] for c in study['cases']} == set(original)-{'oew'}
    for c in study['cases']:
        for kind in ('light', 'heavy'):
            row = c[kind]
            assert row['xcg_mac_pct'] == pytest.approx(variants[c['key']][kind+'_pct'])
            assert row['moment_kg_m'] == pytest.approx(row['mass_kg']*row['xcg_m'])
        nominal = c['nominal']
        assert nominal['mass_kg'] == pytest.approx(original[c['key']]['mass_kg'])
        assert nominal['xcg_m'] == pytest.approx(original[c['key']]['xcg_m'])
        for row in c['samples']:
            assert row['checks']['mass'] == (row['mass_kg'] <= design['mass']['m0']+1e-8)
            assert row['checks']['stability'] == (row['static_margin_pct'] >= 5.-1e-8)
            if c['interval']:
                inside = c['interval']['min_kg']-1e-8 <= row['person_kg'] <= c['interval']['max_kg']+1e-8
                assert row['passed'] == inside
    # Exact inequality intersection must work between samples as well.
    interval = study['common_interval']
    if interval:
        for p in (interval['min_kg'], interval['max_kg'], sum(interval.values())/2):
            assert all(v['a']*p+v['b'] >= -1e-7 for c in study['cases'] for v in c['constraints'])


def test_cg_sensitivity_matches_finite_difference(design):
    bal=design['balance']; study=bal['pilot_loading']
    if not study['available']:return
    # Compare the analytic derivative with a central difference of actual moments.
    for c in study['cases']:
        n=study['n_crew'];p=study['nominal_person_kg'];arm=study['crew_arm_m'];h=.001
        def cg(m):return 100*((c['base_moment_kg_m']+n*m*arm)/(c['base_mass_kg']+n*m)-bal['x_lemac_m'])/design['geometry']['wing']['mac']
        assert (cg(p+h)-cg(p-h))/(2*h) == pytest.approx(c['nominal']['sensitivity_pct_per_kg'], rel=1e-7, abs=1e-8)


def test_pilot_equations_share_report_and_graph_values(design):
    sheet=build_sheet(design)
    for key, entry in sheet.entries.items():
        if entry['section']=='p3.pilot_loading' and entry['kind']=='calc':
            assert entry['consistent'], key
            assert '[[' not in entry['tex']


def test_uav_has_no_pilot_case():
    mass, geom, bal = example();mass['unmanned']=True
    assert not calculate_pilot_loading(mass,geom,bal)['available']


def test_study_does_not_reposition_or_resize_the_aircraft():
    inputs=example();saved=deepcopy(inputs)
    calculate_pilot_loading(*inputs)
    assert inputs == saved
