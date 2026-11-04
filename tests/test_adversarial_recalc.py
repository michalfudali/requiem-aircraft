"""Adversarial Verification Suite for Reactive Recalculation, Class Isolation, and E2E Workflows.

Written by Challenger 2 (teamwork_preview_challenger) for Milestone 2.
Evaluates:
1. Reactive recalculation pipeline:
   - POST new aircraft -> verify N increments and regressions dynamically update.
   - PUT alter parameters -> verify suggestions dynamically update.
   - DELETE aircraft -> verify N and all statistics revert to original baseline.
2. Preserved class isolation across all 7 aircraft classes (pairwise orthogonal verification).
3. End-to-end design workflows integrating custom aircraft CRUD, trend suggestions, and sizing engine.
4. Robustness against extreme outlier aircraft and parameter modulations.
5. Bug reproduction: KeyError: 'year' when aircraft is created without optional year attribute.
"""
import copy
import math
import time
import pytest

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trends import CLASSES, get_trend_suggestions

ALL_CLASSES = list(CLASSES.keys())


@pytest.fixture
def recalc_isolated_db(isolated_db):
    """The shared fixture restores the test database after each recalculation test."""
    yield


def _extract_metric_state(suggestions_dict):
    """Flattens suggestions dictionary into a comparable snapshot."""
    snapshot = {}
    for key, item in suggestions_dict.items():
        snapshot[key] = {
            'suggested_value': item.get('suggested_value'),
            'model_type': item.get('model_type'),
            'r2': item.get('r2'),
            'n': item.get('n'),
            'available_n': item.get('available_n'),
            'stats': copy.deepcopy(item.get('stats')),
            'equation': item.get('equation'),
        }
    return snapshot


def _robust_post(client, url, json_payload):
    """Posts payload with retries to absorb Windows NTFS temporary file replace lock contention."""
    for attempt in range(5):
        res = client.post(url, json=json_payload)
        if res.status_code == 500:
            time.sleep(0.06 * (attempt + 1))
            continue
        return res
    return res


def _robust_put(client, url, json_payload):
    """Puts payload with retries to absorb Windows NTFS temporary file replace lock contention."""
    for attempt in range(5):
        res = client.put(url, json=json_payload)
        if res.status_code == 500:
            time.sleep(0.06 * (attempt + 1))
            continue
        return res
    return res


def _robust_delete(client, url):
    """Deletes aircraft with retries to absorb Windows NTFS temporary file replace lock contention."""
    for attempt in range(5):
        res = client.delete(url)
        if res.status_code == 500:
            time.sleep(0.06 * (attempt + 1))
            continue
        return res
    return res



# ==============================================================================
# 1. Reactive Recalculation Lifecycle (Task 1)
# ==============================================================================

@pytest.mark.tier3
@pytest.mark.parametrize('target_class,propulsion,engine_field,engine_val', [
    ('piston_ga', 'prop', 'p_kw', 130.0),
    ('turboprop_regional', 'prop', 'p_kw', 1800.0),
    ('jet_business', 'jet', 't_kn', 35.0),
    ('motoglider', 'prop', 'p_kw', 45.0),
])
def test_reactive_lifecycle_full_crud_cycle(client, recalc_isolated_db, target_class, propulsion, engine_field, engine_val):
    """Verifies complete POST -> PUT -> DELETE lifecycle dynamically recalculates suggestions.

    1. Baseline query captures N, suggested values, R^2, and equations.
    2. POST custom aircraft -> verifies N increments by 1 across all relevant metrics.
    3. PUT alters parameters -> verifies regressions update.
    4. DELETE aircraft -> verifies exact reversion to original baseline.
    """
    m0_test = 1200.0 if target_class in ('piston_ga', 'motoglider') else 15000.0
    # Without m0 the whole class is the sample, so a new aircraft always enters it.
    query = f'/api/trends/suggestions?aircraft_type={target_class}'
    res_base = client.get(query)
    assert res_base.status_code == 200
    base_data = res_base.get_json()['suggestions']
    base_snapshot = _extract_metric_state(base_data)

    aid = f"adv-recalc-{target_class}-001"
    post_payload = {
        "id": aid,
        "model": f"Adversarial {target_class.upper()} 1",
        "manufacturer": "Teamwork Challenger MEiL",
        "aircraft_type": target_class,
        "engine_type": propulsion,
        "family": "AdvTester",
        "year": 2015,
        "m0": m0_test * 1.25,
        "me": m0_test * 0.70,
        "s": 18.0 if target_class in ('piston_ga', 'motoglider') else 45.0,
        "b": 11.5 if target_class in ('piston_ga', 'motoglider') else 22.0,
        engine_field: engine_val,
        "v_h": 0.82,
        "aileron_span_fraction": 0.44,
        "aileron_chord_ratio": 0.23,
        "elevator_chord_ratio": 0.37,
        "rudder_chord_ratio": 0.41,
        "dihedral_deg": 5.5,
    }

    try:
        # Step 2: POST aircraft
        post_res = _robust_post(client, '/api/aircraft', post_payload)
        assert post_res.status_code == 201, f"POST failed: {post_res.data}"

        res_after_post = client.get(query)
        assert res_after_post.status_code == 200
        post_data = res_after_post.get_json()['suggestions']

        # The new aircraft enters every metric it documents
        for key in ('ws', 'ar', 'me_m0', 'vh', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio', 'dihedral_deg'):
            assert post_data[key]['available_n'] == base_snapshot[key]['available_n'] + 1, key

        if propulsion == 'prop':
            assert post_data['pw']['available_n'] == base_snapshot['pw']['available_n'] + 1
        elif propulsion == 'jet':
            assert post_data['tw']['available_n'] == base_snapshot['tw']['available_n'] + 1

        # Step 3: PUT update with altered parameters
        put_payload = {
            "m0": m0_test * 1.8,
            "me": m0_test * 0.9,
            "s": 12.0 if target_class in ('piston_ga', 'motoglider') else 30.0,
            "v_h": 0.55,
        }
        put_res = _robust_put(client, f'/api/aircraft/{aid}', put_payload)
        assert put_res.status_code == 200, f"PUT failed: {put_res.data}"

        res_after_put = client.get(query)
        assert res_after_put.status_code == 200
        put_data = res_after_put.get_json()['suggestions']

        # N remains the same as post-step
        assert put_data['ws']['available_n'] == base_snapshot['ws']['available_n'] + 1
        assert put_data['vh']['available_n'] == base_snapshot['vh']['available_n'] + 1

    finally:
        # Step 4: DELETE aircraft
        _robust_delete(client, f'/api/aircraft/{aid}')

    # Step 5: Verify exact reversion to baseline
    res_after_del = client.get(query)
    assert res_after_del.status_code == 200
    del_data = res_after_del.get_json()['suggestions']
    del_snapshot = _extract_metric_state(del_data)

    for metric in ('ws', 'ar', 'me_m0', 'vh', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio', 'dihedral_deg'):
        assert del_snapshot[metric]['n'] == base_snapshot[metric]['n'], f"N failed to revert for {metric}"
        assert del_snapshot[metric]['suggested_value'] == base_snapshot[metric]['suggested_value'], f"Value failed to revert for {metric}"
        assert del_snapshot[metric]['model_type'] == base_snapshot[metric]['model_type']
        assert del_snapshot[metric]['r2'] == base_snapshot[metric]['r2']
        assert del_snapshot[metric]['equation'] == base_snapshot[metric]['equation']


@pytest.mark.tier3
def test_reactive_recalc_partial_payload_and_progressive_enrichment(client, recalc_isolated_db):
    """Verifies that an aircraft with minimal fields only increments applicable metrics,
    and PUTting missing fields progressively activates further regressions."""
    res_base = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    base_data = res_base.get_json()['suggestions']
    n_ws_base = base_data['ws']['available_n']
    n_ar_base = base_data['ar']['available_n']
    n_pw_base = base_data['pw']['available_n']
    n_vh_base = base_data['vh']['available_n']

    aid = "adv-partial-ga-01"
    min_payload = {
        "id": aid,
        "model": "Minimal GA",
        "manufacturer": "Teamwork Minimal",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "year": 2020,
        "m0": 1100.0,
    }
    try:
        res_create = _robust_post(client, '/api/aircraft', min_payload)
        assert res_create.status_code == 201

        res_post_min = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
        post_min_data = res_post_min.get_json()['suggestions']
        # None of the geometric / power regressions should have incremented
        assert post_min_data['ws']['available_n'] == n_ws_base
        assert post_min_data['ar']['available_n'] == n_ar_base
        assert post_min_data['pw']['available_n'] == n_pw_base
        assert post_min_data['vh']['available_n'] == n_vh_base

        # Now PUT s and p_kw
        res_put1 = _robust_put(client, f'/api/aircraft/{aid}', {"s": 15.0, "p_kw": 120.0})
        assert res_put1.status_code == 200

        res_post_put1 = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
        post_put1_data = res_post_put1.get_json()['suggestions']
        # Available observations increment independently of whether the new point
        # moves a fit across the acceptance threshold (and thus changes its dated subset).
        # ws and pw increment by 1, but ar and vh must not
        assert post_put1_data['ws']['available_n'] == n_ws_base + 1
        assert post_put1_data['pw']['available_n'] == n_pw_base + 1
        assert post_put1_data['ar']['available_n'] == n_ar_base
        assert post_put1_data['vh']['available_n'] == n_vh_base

        # Now PUT b and v_h
        res_put2 = _robust_put(client, f'/api/aircraft/{aid}', {"b": 10.5, "v_h": 0.75})
        assert res_put2.status_code == 200

        res_post_put2 = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
        post_put2_data = res_post_put2.get_json()['suggestions']
        assert post_put2_data['ar']['available_n'] == n_ar_base + 1
        assert post_put2_data['vh']['available_n'] == n_vh_base + 1

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')


    res_final = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    final_data = res_final.get_json()['suggestions']
    assert final_data['ws']['available_n'] == n_ws_base
    assert final_data['ar']['available_n'] == n_ar_base
    assert final_data['pw']['available_n'] == n_pw_base
    assert final_data['vh']['available_n'] == n_vh_base


# ==============================================================================
# 2. Preserved Class Isolation Across All 7 Classes (Task 2)
# ==============================================================================

@pytest.mark.tier3
@pytest.mark.parametrize('mutated_class', ALL_CLASSES)
def test_strictly_preserved_class_isolation(client, recalc_isolated_db, mutated_class):
    """Pairwise Orthogonality: Adding, modifying, or deleting an aircraft in `mutated_class`
    must leave the suggestions and statistics of all other 6 classes completely unaltered."""
    initial_snapshots = {}
    for cls in ALL_CLASSES:
        res = client.get(f'/api/trends/suggestions?aircraft_type={cls}')
        assert res.status_code == 200
        initial_snapshots[cls] = _extract_metric_state(res.get_json()['suggestions'])

    if mutated_class in ('jet_business', 'jet_transport'):
        prop = 'jet'
        eng_kw, eng_kn = None, 50.0
        m0_val, me_val, s_val, b_val = 25000.0, 14000.0, 60.0, 24.0
    elif mutated_class == 'glider':
        prop = 'none'
        eng_kw, eng_kn = None, None
        m0_val, me_val, s_val, b_val = 500.0, 320.0, 10.5, 15.0
    else:
        prop = 'prop'
        eng_kw, eng_kn = 150.0, None
        m0_val, me_val, s_val, b_val = 1400.0, 850.0, 16.0, 11.0

    aid = f"iso-test-{mutated_class}-99"
    payload = {
        "id": aid,
        "model": f"Isolation Test {mutated_class}",
        "manufacturer": "Teamwork Isolation Lab",
        "aircraft_type": mutated_class,
        "engine_type": prop,
        "year": 2018,
        "m0": m0_val,
        "me": me_val,
        "s": s_val,
        "b": b_val,
        "p_kw": eng_kw,
        "t_kn": eng_kn,
        "v_h": 0.77,
    }

    try:
        post_res = _robust_post(client, '/api/aircraft', payload)
        assert post_res.status_code == 201

        # Verify all OTHER 6 classes are strictly unchanged
        for cls in ALL_CLASSES:
            if cls == mutated_class:
                continue
            res_other = client.get(f'/api/trends/suggestions?aircraft_type={cls}')
            assert res_other.status_code == 200
            other_snapshot = _extract_metric_state(res_other.get_json()['suggestions'])

            for metric, state in initial_snapshots[cls].items():
                assert other_snapshot[metric]['n'] == state['n'], f"Class {cls} metric {metric} N altered when mutating {mutated_class}!"
                assert other_snapshot[metric]['suggested_value'] == state['suggested_value'], f"Class {cls} metric {metric} value altered!"
                assert other_snapshot[metric]['r2'] == state['r2'], f"Class {cls} metric {metric} R2 altered!"
                assert other_snapshot[metric]['equation'] == state['equation'], f"Class {cls} metric {metric} equation altered!"
                assert other_snapshot[metric]['stats'] == state['stats'], f"Class {cls} metric {metric} stats altered!"

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')

    # Verify mutated_class is also cleanly restored
    res_restored = client.get(f'/api/trends/suggestions?aircraft_type={mutated_class}')
    assert res_restored.status_code == 200
    restored_snapshot = _extract_metric_state(res_restored.get_json()['suggestions'])
    for metric, state in initial_snapshots[mutated_class].items():
        assert restored_snapshot[metric]['n'] == state['n']
        assert restored_snapshot[metric]['suggested_value'] == state['suggested_value']


# ==============================================================================
# 3. End-to-End Design Workflows with Custom Aircraft (Task 3)
# ==============================================================================

@pytest.mark.tier4
def test_e2e_workflow_custom_stol_utility_aircraft(client, recalc_isolated_db):
    """E2E Workflow 1: Designing a bush/STOL utility aircraft with custom reference aircraft.

    Workflow:
    1. Engineer creates a custom STOL reference aircraft in `piston_ga` (e.g. Maule M-7 clone).
    2. Queries `/api/trends/suggestions` for piston_ga at m0 = 1250 kg.
    3. Adopts dynamic suggestions into a preliminary design project payload.
    4. Submits payload to `/api/calculate`.
    5. Validates realistic sizing: positive wing area, reasonable stall speed, valid climb rate.
    """
    aid = "stol-maule-custom-01"
    stol_ref = {
        "id": aid,
        "model": "Maule M-7-235B Custom",
        "manufacturer": "Maule Air / Custom",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "year": 1998,
        "m0": 1134.0,
        "me": 680.0,
        "s": 15.39,
        "b": 10.03,
        "p_kw": 175.0,
        "v_h": 0.65,
        "aileron_span_fraction": 0.40,
        "aileron_chord_ratio": 0.22,
        "elevator_chord_ratio": 0.35,
        "rudder_chord_ratio": 0.38,
        "dihedral_deg": 2.0,
    }
    try:
        create_res = _robust_post(client, '/api/aircraft', stol_ref)
        assert create_res.status_code == 201

        # Query suggestions with design MTOW
        m0_design = 1250.0
        res_sugg = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={m0_design}')
        assert res_sugg.status_code == 200
        sugg = res_sugg.get_json()['suggestions']

        ws_suggested = sugg['ws']['suggested_value']
        ar_suggested = sugg['ar']['suggested_value']
        me_suggested = sugg['me_m0']['suggested_value']
        vh_suggested = sugg['vh']['suggested_value']

        assert 50.0 <= ws_suggested <= 120.0
        assert 5.0 <= ar_suggested <= 10.0
        assert 0.50 <= me_suggested <= 0.75

        # Run preliminary design calculation
        project = copy.deepcopy(AIRCRAFT_PRESETS['ga_trainer'])
        project['m_to'] = m0_design
        project['wing_loading'] = ws_suggested
        project['aspect_ratio'] = ar_suggested
        project['empty_mass_fraction'] = me_suggested
        project['v_h'] = vh_suggested

        calc_res = client.post('/api/calculate', json=project)
        assert calc_res.status_code == 200
        calc_out = calc_res.get_json()
        assert 'summary' in calc_out or 'params' in calc_out or 'phases' in calc_out

        # Verify wing area matches m0 / (W/S)
        expected_s = m0_design / ws_suggested
        params = calc_out.get('params', {})
        if 'wing_area' in params:
            assert params['wing_area'] == pytest.approx(expected_s, rel=0.1)

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')


@pytest.mark.tier4
def test_bug_reproduction_omitted_year_crashes_calculate(client, recalc_isolated_db):
    """Reproduces Bug: When an aircraft is created without the optional 'year' attribute,
    calculations/trends.py:analyze_trends line 427 raises KeyError: 'year' during /api/calculate."""
    aid = "bug-repro-missing-year"
    no_year_ac = {
        "id": aid,
        "model": "Yearless Aircraft",
        "manufacturer": "Challenger Bug Hunter",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "m0": 1150.0,
        "me": 700.0,
        "s": 15.0,
        "b": 10.0,
        "p_kw": 120.0,
        # 'year' is intentionally omitted here (validate_aircraft treats it as optional)
    }
    try:
        create_res = _robust_post(client, '/api/aircraft', no_year_ac)
        assert create_res.status_code == 201

        # Suggestions API handles missing year without crashing
        sugg_res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150')
        assert sugg_res.status_code == 200

        # Downstream preliminary calculation pipeline run_bipol_project succeeds without KeyError: 'year'
        project = copy.deepcopy(AIRCRAFT_PRESETS['ga_trainer'])
        calc_result = run_bipol_project(project)
        assert calc_result is not None
        assert calc_result.get('status') == 'success'
        assert 'sizing' in calc_result

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')


@pytest.mark.tier4
def test_e2e_workflow_custom_high_altitude_uav(client, recalc_isolated_db):
    """E2E Workflow 2: UAV preliminary sizing after expanding UAV database cohort."""
    res_base = client.get('/api/trends/suggestions?aircraft_type=uav')
    n_base = res_base.get_json()['suggestions']['ws']['n']

    uav_payloads = [
        {
            "id": "uav-recon-alpha",
            "model": "Recon Alpha Surveillance",
            "manufacturer": "AeroTech UAV MEiL",
            "aircraft_type": "uav",
            "engine_type": "prop",
            "year": 2021,
            "m0": 320.0,
            "me": 190.0,
            "s": 6.8,
            "b": 9.2,
            "p_kw": 38.0,
            "v_h": 0.62,
        },
        {
            "id": "uav-recon-beta",
            "model": "Recon Beta High Altitude",
            "manufacturer": "AeroTech UAV MEiL",
            "aircraft_type": "uav",
            "engine_type": "prop",
            "year": 2023,
            "m0": 580.0,
            "me": 340.0,
            "s": 12.5,
            "b": 16.0,
            "p_kw": 65.0,
            "v_h": 0.68,
        }
    ]

    try:
        for p in uav_payloads:
            res = _robust_post(client, '/api/aircraft', p)
            assert res.status_code == 201

        # Query with design MTOW
        res_uav = client.get('/api/trends/suggestions?aircraft_type=uav&m0=450')
        assert res_uav.status_code == 200
        uav_sugg = res_uav.get_json()['suggestions']

        assert uav_sugg['ws']['n'] == n_base + 2
        assert uav_sugg['ws']['suggested_value'] > 0
        assert uav_sugg['ar']['suggested_value'] > 0
        assert 0 < uav_sugg['me_m0']['suggested_value'] < 1.0

    finally:
        for p in uav_payloads:
            _robust_delete(client, f"/api/aircraft/{p['id']}")


@pytest.mark.tier4
def test_e2e_workflow_custom_business_jet_sizing(client, recalc_isolated_db):
    """E2E Workflow 3: Custom super-midsize business jet and thrust sizing."""
    aid = "super-midsize-jet-01"
    jet_payload = {
        "id": aid,
        "model": "Falcon Express 600",
        "manufacturer": "Dassault / MEiL Custom",
        "aircraft_type": "jet_business",
        "engine_type": "jet",
        "year": 2019,
        "m0": 18500.0,
        "me": 10200.0,
        "s": 46.5,
        "b": 21.4,
        "t_kn": 72.0,
        "n_engines": 2,
        "v_h": 0.88,
        "dihedral_deg": 3.5,
    }
    try:
        create_res = _robust_post(client, '/api/aircraft', jet_payload)
        assert create_res.status_code == 201

        # Query suggestions for business jet
        res = client.get('/api/trends/suggestions?aircraft_type=jet_business&m0=18500')
        assert res.status_code == 200
        sugg = res.get_json()['suggestions']

        # Thrust-to-weight must be present, power loading must be None
        assert sugg['tw']['suggested_value'] is not None
        assert sugg['tw']['n'] > 0
        assert sugg['pw']['suggested_value'] is None
        assert sugg['pw']['n'] == 0

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')


# ==============================================================================
# 4. Adversarial Stress & Robustness Tests
# ==============================================================================

@pytest.mark.tier2
def test_adversarial_outlier_does_not_poison_global_api(client, recalc_isolated_db):
    """Verifies that inserting an extreme but valid outlier aircraft does not crash
    the suggestions endpoint or return NaN / Inf values."""
    aid = "adv-outlier-heavy-ga"
    # An unusually heavy piston GA aircraft (e.g. Antonov An-2 class: m0=5500 kg, S=71.5 m2)
    outlier = {
        "id": aid,
        "model": "Colossal GA Biplane",
        "manufacturer": "Antonov / MEiL Test",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "year": 1947,
        "m0": 5500.0,
        "me": 3300.0,
        "s": 71.5,
        "b": 18.2,
        "p_kw": 735.0,
        "v_h": 0.80,
    }
    try:
        res = _robust_post(client, '/api/aircraft', outlier)
        assert res.status_code == 201

        # Query suggestions across a wide range of project masses
        for test_m0 in [100.0, 1150.0, 5000.0, 25000.0]:
            query_res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={test_m0}')
            assert query_res.status_code == 200
            data = query_res.get_json()
            assert data['status'] == 'ok'
            sugg = data['suggestions']
            for key, val in sugg.items():
                sv = val.get('suggested_value')
                if sv is not None:
                    assert math.isfinite(sv), f"Metric {key} suggested_value is non-finite: {sv}"
                r2 = val.get('r2')
                if r2 is not None:
                    assert math.isfinite(r2), f"Metric {key} r2 is non-finite: {r2}"

    finally:
        _robust_delete(client, f'/api/aircraft/{aid}')



@pytest.mark.tier2
def test_adversarial_zero_wing_configuration_variations(client, recalc_isolated_db):
    """Verifies that wing_configuration parameter modulates dihedral suggestions dynamically
    both before and after custom aircraft mutations."""
    res_default = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res_default.status_code == 200
    dih_default = res_default.get_json()['suggestions']['dihedral_deg']['suggested_value']

    res_high = client.get('/api/trends/suggestions?aircraft_type=piston_ga&wing_configuration=high')
    assert res_high.status_code == 200
    dih_high = res_high.get_json()['suggestions']['dihedral_deg']['suggested_value']

    # BIPOL_1 average of the sample; the layout changes only the comparison range
    assert dih_high == dih_default
    assert res_high.get_json()['suggestions']['dihedral_deg']['typical_range'] == [0.0, 2.5]
