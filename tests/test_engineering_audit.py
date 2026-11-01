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


def test_engineering_audit_flying_qualities_and_defense_question():
    params = dict(AIRCRAFT_PRESETS['pzl_kos'])
    result = run_bipol_project(params)
    audit = perform_engineering_audit(result)

    fq_check = next((chk for chk in audit['checks'] if chk['id'] == 'flying_qualities_cap_check'), None)
    assert fq_check is not None
    assert 'CAP =' in fq_check['value']
    assert audit['metrics']['cap_rad_s2_per_g'] > 0.0

    questions_ids = {q['id'] for q in audit['defense_questions']}
    assert 'q_flying_qualities' in questions_ids


def test_defense_questions_follow_the_actual_design():
    """Pytania na obronę: miejsce przeciągnięcia względem lotek i warianty dla szybowca bez napędu."""
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    trainer = {q['id']: q for q in run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer']))['engineering_audit']['defense_questions']}
    stall = trainer['q_stall_origin']['expected_answer']
    assert 'Lotki zaczynają się w η ≈ 0,71' in stall and 'przed nimi' in stall
    assert 'wznoszenie' in trainer['q_matching_chart']['expected_answer']  # rzeczywiste ograniczenie aktywne
    glider = {q['id']: q for q in run_bipol_project(dict(AIRCRAFT_PRESETS['glider_pw5']))['engineering_audit']['defense_questions']}
    assert 'szybowca' in glider['q_matching_chart']['question'] and 'kN' not in glider['q_matching_chart']['question']
    assert 'najmniejszego opadania' in glider['q_climb_speed']['question']


def test_stall_origin_is_compared_with_actual_aileron_edge():
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    audit = run_bipol_project(dict(AIRCRAFT_PRESETS['vlj_jet']))['engineering_audit']
    check = next(c for c in audit['checks'] if c['id'] == 'stall_progression')
    eta_aileron = audit['metrics']['aileron_inner_eta']
    assert 0.6 < eta_aileron < 0.8 and f"{eta_aileron:.2f}".replace('.', ',') in check['required']
    assert check['passed'] == (audit['metrics']['stall_eta_span'] < eta_aileron)


def test_main_gear_angles_follow_lecture_7():
    """Wykład 7, slajd 17: koło–ogon ≥ α(Cz_max), pion przez ŚC–koło ≥ α(0,9·Cz_max) + 3°."""
    import math
    from calculations.paturski_ml import wing_alpha_deg
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['vlj_jet']))
    audit = result['engineering_audit']
    tm = result['bipol_projects']['p4']['paturski_aero']['trim_model']
    m = audit['metrics']
    assert m['tailstrike_required_deg'] == pytest.approx(wing_alpha_deg(tm, tm['cz_max_clean']), abs=.05)
    assert m['tipback_required_deg'] == pytest.approx(wing_alpha_deg(tm, .9 * tm['cz_max_clean']) + 3, abs=.05)
    # Kąt α płata z tabeli 2.2 to ten sam wzór co w helperze.
    row = next(r for r in result['bipol_projects']['p4']['paturski_aero']['table_2_2_complete'] if r['cz_inf'] == round(tm['cz_max_clean'], 3))
    assert row['alpha_p_deg'] == pytest.approx(wing_alpha_deg(tm, tm['cz_max_clean']), abs=.01)
    checks = {c['id']: c for c in audit['checks']}
    tip = checks['main_gear_tipback']
    assert tip['passed'] == (m['tipback_angle_deg'] >= m['tipback_required_deg'])
    # Podane położenie kół spełnia wymaganie: kąt z tego położenia równa się wymaganemu.
    b, mac = result['balance'], result['geometry']['wing']['mac']
    x_aft = b['x_lemac_m'] + max(35, b['cg_range']['aft_pct']) / 100 * mac  # BIPOL_3, krok 10
    assert m['tipback_cg_mac_pct'] == pytest.approx(max(35, b['cg_range']['aft_pct']), abs=.05)
    angle = math.degrees(math.atan2(m['main_gear_x_required_m'] - x_aft, m['h_cg_ground_m']))
    assert angle == pytest.approx(m['tipback_required_deg'], abs=.3)
    assert any(q['id'] == 'q_main_gear' for q in audit['defense_questions'])


def test_sailplane_skips_tricycle_gear_angles():
    audit = run_bipol_project(dict(AIRCRAFT_PRESETS['glider_pw5']))['engineering_audit']
    ids = {c['id'] for c in audit['checks']}
    assert 'main_gear_tipback' not in ids and 'tailstrike_clearance' not in ids
    assert all(q['id'] != 'q_main_gear' for q in audit['defense_questions'])
