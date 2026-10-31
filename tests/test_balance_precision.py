"""Mass/moment conservation and decisions at the P3 stability boundary."""
from copy import deepcopy
import math

import pytest

from calculations import run_bipol_project
from calculations.balance import calculate_balance_and_stability
from calculations.presets import AIRCRAFT_PRESETS


@pytest.fixture(scope='module', params=list(AIRCRAFT_PRESETS))
def design(request):
    return run_bipol_project(AIRCRAFT_PRESETS[request.param])


def test_component_table_and_balance_conserve_mass_and_first_moment(design):
    mass, balance = design['mass'], design['balance']
    rows = design['bipol_projects']['p3']['table_3_1_components']
    assert math.fsum(mass['breakdown'].values()) == pytest.approx(mass['m_empty'], rel=1e-12)
    mtow = balance['loading_states'][-1]
    assert math.fsum(row['mass_kg'] for row in rows) == pytest.approx(mtow['mass_kg'], rel=1e-12)
    assert math.fsum(row['mass_kg'] * row['x_m'] for row in rows) == pytest.approx(mtow['moment_kg_m'], rel=1e-12)
    for state in balance['loading_states']:
        assert state['xcg_m'] * state['mass_kg'] == pytest.approx(state['moment_kg_m'], rel=1e-12)
        assert state['xcg_mac_pct'] == pytest.approx(
            100 * (state['xcg_m'] - balance['x_lemac_m']) / design['geometry']['wing']['mac'], abs=1e-10)
    # The empty aircraft is not assessed as an airborne loading case.
    empty = balance['loading_states'][0]
    assert empty['in_flight'] is False
    assert empty['minimum_margin_passed'] is None
    assert empty['cg_criterion_passed'] is None
    # P4 must use the same CG and neutral point as P3, including the derivative
    # identity dCm/dCL = -Kn (Kn expressed as a fraction of MAC).
    cm = design['bipol_projects']['p4']['cg_characteristics']['cm_model']
    assert cm['x_fwd_pct'] == pytest.approx(balance['cg_range']['forward_pct'], abs=1e-10)
    assert cm['x_aft_pct'] == pytest.approx(balance['cg_range']['aft_pct'], abs=1e-10)
    assert cm['dcm_dcz_aft'] == pytest.approx(-balance['stability']['static_margin_aft_pct'] / 100, abs=1e-12)


def test_geometric_scaling_preserves_dimensionless_cg_and_stability(design):
    base = calculate_balance_and_stability(design['mass'], design['geometry'], {}, design['params'])
    for scale in (0.2, 2.7):
        geom = deepcopy(design['geometry'])
        for key in ('length', 'diameter'):
            geom['fuselage'][key] *= scale
        for key in ('mac', 'x_le_mac'):
            geom['wing'][key] *= scale
        geom['wing']['S'] *= scale ** 2
        geom['horizontal_tail']['S_h'] *= scale ** 2
        geom['horizontal_tail']['x_ac_m'] *= scale
        result = calculate_balance_and_stability(design['mass'], geom, {}, design['params'])
        assert result['x_lemac_m'] == pytest.approx(base['x_lemac_m'] * scale, rel=1e-10)
        assert result['stability']['static_margin_aft_pct'] == pytest.approx(base['stability']['static_margin_aft_pct'], abs=1e-9)
        for state, original in zip(result['loading_states'], base['loading_states']):
            assert state['xcg_mac_pct'] == pytest.approx(original['xcg_mac_pct'], abs=1e-9)


@pytest.mark.parametrize('margin,passed', [(4.96, False), (5.04, True)])
def test_minimum_margin_decision_does_not_round_up_to_five(margin, passed):
    design = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    geom = deepcopy(design['geometry'])
    base = calculate_balance_and_stability(design['mass'], geom, {}, design['params'])
    terms = base['neutral_point']['terms']
    target_np = base['cg_range']['aft_pct'] + margin
    tail_gain = terms['eta_h'] * terms['a_h'] / terms['a_w'] * (1 - terms['de_da']) * 100
    target_vh = (target_np - terms['x_ac_wbn_pct']) / tail_gain
    geom['horizontal_tail']['S_h'] = target_vh * geom['wing']['S'] * geom['wing']['mac'] / terms['l_h']
    result = calculate_balance_and_stability(design['mass'], geom, {}, design['params'])
    assert result['stability']['static_margin_aft_pct'] == pytest.approx(margin, abs=1e-9)
    assert result['stability']['is_stable'] is passed


def test_payload_release_conserves_mass_and_moment():
    design = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'm_cargo': 120,
                               'payload_drop_kg': 70, 'mission_type': 'drop'})
    balance = design['balance']
    states = {state['key']: state for state in balance['loading_states']}
    assert design['mass']['m_payload_dropped'] == 70
    before, after = states['before_drop'], states['after_drop']
    assert before['mass_kg'] - after['mass_kg'] == pytest.approx(70, abs=1e-10)
    assert before['moment_kg_m'] - after['moment_kg_m'] == pytest.approx(70 * balance['arms']['baggage'], abs=1e-9)
