"""Published lever example, a nontrivial LP minimum and conservation checks."""
from copy import deepcopy
from math import isfinite

import pytest

from calculations.ballast import ballast_model, solve_ballast
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS


def model_for(cases, lower, upper, maximum, length=5.):
    study = dict(n_crew=0, crew_arm_m=0., source_url='FAA',
                 cases=[dict(key=str(i), name='Stan '+str(i), base_mass_kg=m, base_moment_kg_m=m*x)
                        for i,(m,x) in enumerate(cases)],
                 limits=dict(forward_pct=100*lower if lower is not None else None,
                             aft_pct=100*upper, stability_aft_pct=100*upper,
                             maximum_mass_kg=maximum))
    geometry = dict(wing=dict(mac=1.), fuselage=dict(length=length))
    balance = dict(x_lemac_m=0., neutral_point=dict(x_n_mac_pct=100*upper+5))
    return ballast_model(study, geometry, balance)


def test_published_faa_ballast_example_converted_to_si():
    # FAA ch.7: 1876 lb, CG 32.2 in, target 33 in, ballast at 228 in.
    lb, inch = .45359237, .0254
    model = model_for([(1876*lb,32.2*inch)],33*inch,46*inch,2250*lb,228*inch)
    result = solve_ballast(model,0.,228*inch)
    expected = (1876*.8/195)*lb
    assert result['mass_kg'] == pytest.approx(expected, rel=1e-12)
    assert result['after'][0]['xcg_m'] == pytest.approx(33*inch, rel=1e-12)
    assert result['after'][0]['passed']
    optimum = solve_ballast(model,0.)
    assert optimum['mass_kg'] == pytest.approx(expected, rel=1e-12)
    assert optimum['station_m'] == pytest.approx(228*inch)


def test_global_minimum_can_require_an_interior_station():
    # Simultaneously: z >= 2.4*w+40 and z <= 2.6*w-80, so w>=600.
    model = model_for([(100.,2.),(200.,3.)],2.4,2.6,1000.)
    result = solve_ballast(model,0.)
    assert result['mass_kg'] == pytest.approx(600.)
    assert result['moment_kg_m'] == pytest.approx(1480.)
    assert result['station_m'] == pytest.approx(1480/600)
    assert all(row['passed'] for row in result['after'])
    assert not solve_ballast(model,0.,0.)['feasible']
    assert not solve_ballast(model,0.,5.)['feasible']


def test_single_point_feasible_set_and_mass_limit_are_retained():
    result = solve_ballast(model_for([(100.,2.),(200.,3.)],2.4,2.6,800.),0.)
    assert result['feasible']
    assert result['mass_kg'] == pytest.approx(600.)
    assert result['after'][-1]['mass_kg'] == pytest.approx(800.)


@pytest.mark.parametrize('station', [None,0.,2.5,5.])
def test_no_ballast_is_needed_when_all_states_already_meet_limits(station):
    result = solve_ballast(model_for([(100.,2.5),(200.,2.55)],2.4,2.6,200.),0.,station)
    assert result['status'] == 'unnecessary'
    assert result['mass_kg'] == 0.
    assert result['after'] == result['before']
    assert result['station_m'] == station


@pytest.mark.parametrize('station', [None,0.,3.,5.])
def test_positive_ballast_cannot_repair_overweight(station):
    result = solve_ballast(model_for([(100.,2.),(201.,2.5)],2.4,2.6,200.),0.,station)
    assert result['status'] == 'infeasible'
    assert result['reason'] == 'mass'
    assert result['mass_kg'] is None and result['after'] == []


@pytest.mark.parametrize('station', [0.,2.4])
def test_wrong_side_or_exactly_at_violated_limit_cannot_fix_cg(station):
    result = solve_ballast(model_for([(100.,2.)],2.4,2.6,200.),0.,station)
    assert not result['feasible']


def test_zero_mass_budget_cannot_fix_an_invalid_cg():
    result = solve_ballast(model_for([(100.,2.)],2.4,2.6,100.),0.)
    assert not result['feasible']


def test_one_ballast_must_satisfy_both_states_and_mass_ceiling():
    result = solve_ballast(model_for([(100.,2.),(200.,3.)],2.4,2.6,799.),0.)
    assert not result['feasible']


@pytest.mark.parametrize('person, station', [(float('nan'),None),(-1.,None),(55.,float('inf')),(55.,-1.),(55.,6.)])
def test_invalid_interactive_inputs_are_rejected(person,station):
    with pytest.raises(ValueError):solve_ballast(model_for([(100.,2.)],2.4,2.6,200.),person,station)


@pytest.mark.parametrize('scale', [.001, .3, 2000.])
def test_mass_and_length_scaling_preserve_the_solution(scale):
    model = model_for([(100*scale,2*scale),(200*scale,3*scale)],2.4*scale,2.6*scale,1000*scale,5*scale)
    result = solve_ballast(model,0.)
    assert result['mass_kg'] == pytest.approx(600*scale, rel=1e-10)
    assert result['station_m'] == pytest.approx(1480/600*scale, rel=1e-10)
    assert all(s['passed'] for s in result['after'])


def test_translating_the_datum_preserves_mass_and_relative_station():
    shift=123.4
    model=model_for([(100.,2.+shift),(200.,3.+shift)],2.4+shift,2.6+shift,1000.,5.+shift)
    model['station_domain_m']=[shift,5.+shift]
    result=solve_ballast(model,0.)
    assert result['mass_kg'] == pytest.approx(600.,rel=1e-10)
    assert result['station_m']-shift == pytest.approx(1480/600,rel=1e-10)


@pytest.fixture(scope='module',params=list(AIRCRAFT_PRESETS)+['small_tail'])
def design(request):
    params=({**AIRCRAFT_PRESETS['ga_trainer'],'v_h':.4,'locked_params':['v_h']}
            if request.param=='small_tail' else AIRCRAFT_PRESETS[request.param])
    return run_bipol_project(params)


def test_real_references_conserve_mass_moment_and_every_constraint(design):
    study=design['balance']['pilot_loading']
    if not study['available']:return
    model=study['ballast']['model'];saved=deepcopy(model)
    for reference in study['ballast']['references']:
        assert reference == solve_ballast(model,reference['person_kg'])
        if reference['feasible']:
            for before,after in zip(reference['before'],reference['after']):
                assert after['mass_kg']-before['mass_kg'] == pytest.approx(reference['mass_kg'],abs=1e-9)
                assert after['moment_kg_m']-before['moment_kg_m'] == pytest.approx(reference['moment_kg_m'],abs=1e-8)
                assert after['passed'],after
                assert all(isfinite(after[k]) for k in ['mass_kg','xcg_m','moment_kg_m'])
            if reference['mass_kg']:
                assert reference['active_constraints']
                chosen=solve_ballast(model,reference['person_kg'],reference['station_m'])
                assert chosen['mass_kg'] == pytest.approx(reference['mass_kg'],abs=1e-8)
    assert model==saved
