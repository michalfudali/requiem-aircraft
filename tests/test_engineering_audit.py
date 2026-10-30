"""
Testy jednostkowe modułu audytu inżynierskiego i weryfikatora pułapek konstrukcyjnych.
"""
import pytest
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.engineering_audit import perform_engineering_audit, generate_defense_questions


def test_engineering_audit_basic_structure():
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    assert audit['status'] == 'success'
    assert 'passed_count' in audit
    assert 'total_count' in audit
    assert audit['total_count'] >= 4
    assert 0.0 <= audit['quality_score_pct'] <= 100.0
    assert len(audit['checks']) >= 4
    assert len(audit['defense_questions']) >= 3

    # Check metrics
    metrics = audit['metrics']
    assert 'tipover_angle_deg' in metrics
    assert 'tailstrike_angle_deg' in metrics
    assert 'stall_eta_span' in metrics
    assert metrics['tipover_angle_deg'] > 0.0
    assert metrics['tailstrike_angle_deg'] > 0.0


def test_engineering_audit_multi_engine_oei():
    # Multi-engine topic (e.g. twin engine topic)
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    params.update(n_engines=2, engine_type='prop')
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    # Check that OEI check is present
    oei_check = next((c for c in audit['checks'] if c['id'] == 'oei_directional_control'), None)
    assert oei_check is not None
    assert audit['metrics']['oei_yaw_margin'] is not None


def test_engineering_audit_defense_questions_content():
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    questions = audit['defense_questions']
    ids = {q['id'] for q in questions}
    assert 'q_matching_chart' in ids
    assert 'q_climb_speed' in ids
    assert 'q_stability_margin' in ids
    assert 'q_stall_origin' in ids

    for q in questions:
        assert len(q['question']) > 20
        assert len(q['expected_answer']) > 20
        assert len(q['faculty_tip']) > 10


def test_engineering_audit_glider():
    # Glider with engine_type='none'
    params = dict(AIRCRAFT_PRESETS['glider_pw5'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    assert audit['status'] == 'success'
    # For glider, OEI should not be triggered
    oei_check = next((c for c in audit['checks'] if c['id'] == 'oei_directional_control'), None)
    assert oei_check is None

def test_engineering_audit_wing_loading_and_jet_compressibility():
    params = dict(AIRCRAFT_PRESETS['vlj_jet'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    checks_ids = {c['id'] for c in audit['checks']}
    assert 'wing_loading_benchmark' in checks_ids
    assert 'compressibility_drag_divergence' in checks_ids

    comp_check = next(c for c in audit['checks'] if c['id'] == 'compressibility_drag_divergence')
    assert 'M =' in comp_check['value']
    assert audit['metrics']['mach_cruise'] > 0.4

def test_engineering_audit_flutter_safety_and_defense_question():
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    flutter_check = next((chk for chk in audit['checks'] if chk['id'] == 'flutter_safety_margin'), None)
    assert flutter_check is not None
    assert 'V_flater =' in flutter_check['value']
    assert audit['metrics']['flutter_speed_kmh'] > 0.0

    questions_ids = {q['id'] for q in audit['defense_questions']}
    assert 'q_aeroelastics' in questions_ids

def test_engineering_audit_noise_check():
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    noise_check = next((chk for chk in audit['checks'] if chk['id'] == 'noise_compliance_check'), None)
    assert noise_check is not None
    assert 'dBA' in noise_check['value']
    assert audit['metrics']['noise_flyover'] > 0.0
