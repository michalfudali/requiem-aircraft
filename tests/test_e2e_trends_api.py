"""End-to-End Test Suite for BIPOL Studio Statistical Parameter Suggestions Engine.

Covers:
- Requirement R1: Empirical parameter suggestion derivations across 7 classes
- Requirement R4: Automated verification, numerical stability, and schema contracts
- Tier 1: Core Feature Coverage (>=5 test cases per feature)
- Tier 2: Boundary, Negative & Numerical Stability Cases (>=5 test cases per feature)
"""
import json
import math
import time
import pytest


AIRCRAFT_CLASSES = [
    'piston_ga',
    'turboprop_regional',
    'jet_business',
    'jet_transport',
    'glider',
    'motoglider',
    'uav',
]

REQUIRED_SUGGESTION_KEYS = [
    'ws',          # Wing Loading W/S [kg/m²]
    'ar',          # Aspect Ratio Lambda [-]
    'me_m0',       # Empty Mass Fraction me/m0 [-]
    'vh',          # Horizontal Tail Volume V_H [-]
    'b_ail_ratio', # Aileron Span Ratio b_ail/(b/2)
    'c_ail_ratio', # Aileron Chord Ratio c_ail/c
    'c_e_ratio',   # Elevator Chord Ratio c_e/c_H
    'c_r_ratio',   # Rudder Chord Ratio c_r/c_V
    'dihedral_deg' # Wing Dihedral Angle Gamma [deg]
]


# ==============================================================================
# Tier 1: Feature Coverage (Requirement R1 & R4)
# ==============================================================================

@pytest.mark.tier1
@pytest.mark.parametrize('aircraft_type', AIRCRAFT_CLASSES)
def test_tier1_r1_suggestions_all_7_aircraft_classes(client, aircraft_type):
    """Verifies GET /api/trends/suggestions returns valid responses for all 7 aircraft classes."""
    res = client.get(f'/api/trends/suggestions?aircraft_type={aircraft_type}')
    assert res.status_code == 200, f"Expected 200 for {aircraft_type}, got {res.status_code}: {res.data}"
    
    data = res.get_json()
    assert data is not None, "Response must be valid JSON"
    assert data.get('status') in ('ok', 'success'), f"Expected status 'ok' or 'success', got {data.get('status')}"
    assert data.get('aircraft_type') == aircraft_type
    assert 'suggestions' in data, "Response must contain 'suggestions' dictionary"
    
    suggestions = data['suggestions']
    for key in REQUIRED_SUGGESTION_KEYS:
        assert key in suggestions, f"Key '{key}' missing from suggestions for {aircraft_type}"
        item = suggestions[key]
        assert 'suggested_value' in item, f"'suggested_value' missing in {key}"
        assert 'n' in item, f"'n' missing in {key}"
        assert isinstance(item['n'], int), f"'n' must be int in {key}"
        assert item['n'] >= 0, f"'n' must be non-negative in {key}"
        
        # If suggested_value is present, verify reasonable physical range
        val = item['suggested_value']
        if val is not None:
            assert isinstance(val, (int, float))
            assert math.isfinite(val), f"Suggested value for {key} must be finite"


@pytest.mark.tier1
def test_tier1_r1_suggestions_dynamic_evaluation_with_m0(client):
    """A sample narrowed around a light or a heavy reference mass gives different suggestions."""
    narrow = '&trend_nearest_count=20&mass_initial_guess='
    res_light = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=800' + narrow + '800')
    res_heavy = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=2500' + narrow + '2500')
    
    assert res_light.status_code == 200
    assert res_heavy.status_code == 200
    
    data_light = res_light.get_json()
    data_heavy = res_heavy.get_json()
    
    assert data_light.get('m0') == 800.0 or data_light.get('m0') == 800
    assert data_heavy.get('m0') == 2500.0 or data_heavy.get('m0') == 2500
    
    ws_light = data_light['suggestions']['ws']['suggested_value']
    ws_heavy = data_heavy['suggestions']['ws']['suggested_value']
    
    # In GA piston aircraft, heavier aircraft have systematically higher wing loading W/S
    assert ws_heavy > ws_light, f"Heavy W/S ({ws_heavy}) must exceed light W/S ({ws_light})"
    assert 40.0 <= ws_light <= 150.0, f"Light W/S {ws_light} outside expected GA range"
    assert 60.0 <= ws_heavy <= 250.0, f"Heavy W/S {ws_heavy} outside expected GA range"


@pytest.mark.tier1
def test_tier1_r1_suggestions_fallback_when_m0_omitted(client):
    """Verifies that omitting m0 falls back to cohort central tendency (median/mean)."""
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res.status_code == 200
    data = res.get_json()
    
    ws_item = data['suggestions']['ws']
    val = ws_item['suggested_value']
    assert val is not None, "suggested_value must not be None when m0 is omitted"
    
    stats = ws_item.get('stats', {})
    if stats and 'min' in stats and 'max' in stats:
        assert stats['min'] <= val <= stats['max'], "Fallback value must lie within observed range"


@pytest.mark.tier1
def test_tier1_r1_suggestions_required_parameter_schema(client):
    """Verifies that every suggestion block conforms to documented structural contracts."""
    res = client.get('/api/trends/suggestions?aircraft_type=turboprop_regional&m0=20000')
    assert res.status_code == 200
    data = res.get_json()
    suggestions = data['suggestions']
    
    # Check ws structure
    ws = suggestions['ws']
    assert 'unit' in ws
    assert ws['unit'] in ('kg/m²', 'kg/m2', 'N/m²')
    assert 'model_type' in ws or 'method' in ws
    if ws.get('r2') is not None:
        assert 0.0 <= ws['r2'] <= 1.0, f"R² must be in [0, 1], got {ws['r2']}"
    
    # Check aspect ratio
    ar = suggestions['ar']
    assert ar['suggested_value'] > 0
    assert 5.0 <= ar['suggested_value'] <= 25.0, f"Regional turboprop AR must be plausible, got {ar['suggested_value']}"
    
    # Check empty mass fraction
    me_m0 = suggestions['me_m0']
    assert 0.40 <= me_m0['suggested_value'] <= 0.80, f"me/m0 must be within aeronautical bounds, got {me_m0['suggested_value']}"


@pytest.mark.tier1
def test_tier1_r1_suggestions_wing_configuration_options(client):
    """Verifies that wing_configuration parameter is supported and handled."""
    res_cantilever = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150&wing_configuration=cantilever')
    res_strut = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150&wing_configuration=strut_braced')
    
    assert res_cantilever.status_code == 200
    assert res_strut.status_code == 200
    data_c = res_cantilever.get_json()
    data_s = res_strut.get_json()
    assert data_c['status'] in ('ok', 'success')
    assert data_s['status'] in ('ok', 'success')


@pytest.mark.tier1
def test_tier1_r4_suggestions_json_purity_no_nan_or_infinite(client):
    """Verifies that no NaN or infinite floats exist in any suggestions payload."""
    for ac_type in AIRCRAFT_CLASSES:
        res = client.get(f'/api/trends/suggestions?aircraft_type={ac_type}&m0=1000')
        if res.status_code == 200:
            # Strict JSON parsing rejecting NaN, Infinity, -Infinity
            raw_text = res.data.decode('utf-8')
            parsed = json.loads(raw_text)
            # Re-serialize with allow_nan=False
            serialized = json.dumps(parsed, allow_nan=False)
            assert 'NaN' not in serialized
            assert 'Infinity' not in serialized


@pytest.mark.tier1
def test_tier1_r4_suggestions_latency_under_threshold(client):
    """Verifies response latency of /api/trends/suggestions is below 500 ms."""
    t0 = time.perf_counter()
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1200')
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    
    if res.status_code == 200:
        assert elapsed_ms < 500.0, f"Suggestions API too slow: {elapsed_ms:.1f} ms >= 500 ms"


# ==============================================================================
# Tier 2: Boundary, Negative & Numerical Stability Cases (Requirement R1 & R4)
# ==============================================================================

@pytest.mark.tier2
@pytest.mark.parametrize('invalid_class', [
    'spaceship',
    'hyperloop',
    'submarine',
    'invalid_class_xyz',
    '',
    '   ',
    '1234',
])
def test_tier2_r1_boundary_unknown_aircraft_class_returns_400(client, invalid_class):
    """Verifies that an unknown aircraft_type returns HTTP 400 with an error description."""
    res = client.get(f'/api/trends/suggestions?aircraft_type={invalid_class}')
    assert res.status_code == 400, f"Expected 400 Bad Request for '{invalid_class}', got {res.status_code}"
    data = res.get_json()
    assert data.get('status') == 'error'
    assert 'message' in data or 'error' in data


@pytest.mark.tier2
def test_tier2_r1_boundary_missing_aircraft_type_returns_400(client):
    """Verifies that omitting aircraft_type returns HTTP 400."""
    res = client.get('/api/trends/suggestions')
    assert res.status_code == 400
    data = res.get_json()
    assert data.get('status') == 'error'


@pytest.mark.tier2
@pytest.mark.parametrize('bad_m0', [-500, -0.01, 0, 'abc', 'none', '-'])
def test_tier2_r1_boundary_negative_and_zero_m0_handling(client, bad_m0):
    """Verifies that non-positive or non-numeric m0 values are rejected or safely sanitized."""
    res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={bad_m0}')
    if res.status_code == 200:
        # If server accepts it by falling back to cohort default, verify values remain positive
        data = res.get_json()
        ws = data['suggestions']['ws']['suggested_value']
        assert ws is not None and ws > 0, f"W/S must never be negative or zero, got {ws}"
    else:
        assert res.status_code == 400


@pytest.mark.tier2
def test_tier2_r1_boundary_extreme_m0_no_overflow(client):
    """Verifies that extreme m0 values (e.g. 1e8 kg or 0.1 kg) do not trigger mathematical overflow."""
    for extreme_m0 in [0.01, 100_000_000]:
        res = client.get(f'/api/trends/suggestions?aircraft_type=jet_transport&m0={extreme_m0}')
        # Should either return 200 with finite numbers or 400 (validation rejected out of bounds), NEVER 500
        assert res.status_code in (200, 400), f"Extreme m0={extreme_m0} crashed with status {res.status_code}"
        if res.status_code == 200:
            data = res.get_json()
            for k, item in data['suggestions'].items():
                val = item.get('suggested_value')
                if val is not None:
                    assert math.isfinite(val), f"Parameter {k} produced non-finite value {val}"


@pytest.mark.tier2
def test_tier2_r1_boundary_small_cohort_glider_and_uav(client):
    """Verifies that small cohort classes (glider N=11, uav N=8) compute without singularity."""
    for small_class in ('glider', 'uav'):
        res = client.get(f'/api/trends/suggestions?aircraft_type={small_class}')
        assert res.status_code == 200
        data = res.get_json()
        suggestions = data['suggestions']
        
        # In small cohorts, sample sizes must be positive and not crash regression
        assert suggestions['ws']['n'] > 0
        assert suggestions['ar']['n'] > 0
        assert suggestions['me_m0']['n'] > 0
        
        # For gliders, AR must be typical of sailplanes (>= 12)
        if small_class == 'glider':
            ar_val = suggestions['ar']['suggested_value']
            assert ar_val is not None and ar_val >= 12.0, f"Glider AR must be high, got {ar_val}"


@pytest.mark.tier2
def test_tier2_r1_boundary_propulsion_loading_mutual_exclusion(client):
    """Verifies mutual exclusivity of power loading P/W and thrust loading T/W."""
    # 1. Piston GA: has power loading P/W, null thrust loading T/W
    res_ga = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1200')
    if res_ga.status_code == 200:
        s_ga = res_ga.get_json()['suggestions']
        assert 'pw' in s_ga or 'power_loading' in s_ga
        pw_item = s_ga.get('pw') or s_ga.get('power_loading')
        assert pw_item['suggested_value'] is not None and pw_item['suggested_value'] > 0
        if 'tw' in s_ga:
            assert s_ga['tw']['suggested_value'] is None

    # 2. Jet Transport: has thrust loading T/W, null power loading P/W
    res_jet = client.get('/api/trends/suggestions?aircraft_type=jet_transport&m0=70000')
    if res_jet.status_code == 200:
        s_jet = res_jet.get_json()['suggestions']
        assert 'tw' in s_jet or 'thrust_loading' in s_jet
        tw_item = s_jet.get('tw') or s_jet.get('thrust_loading')
        assert tw_item['suggested_value'] is not None and tw_item['suggested_value'] > 0
        if 'pw' in s_jet:
            assert s_jet['pw']['suggested_value'] is None

    # 3. Pure Glider: unpowered, both null
    res_glider = client.get('/api/trends/suggestions?aircraft_type=glider')
    if res_glider.status_code == 200:
        s_glider = res_glider.get_json()['suggestions']
        if 'pw' in s_glider:
            assert s_glider['pw']['suggested_value'] is None
        if 'tw' in s_glider:
            assert s_glider['tw']['suggested_value'] is None


@pytest.mark.tier2
@pytest.mark.parametrize('malicious_input', [
    '<script>alert("xss")</script>',
    "piston_ga' OR '1'='1",
    '../../etc/passwd',
    'piston_ga\x00nullbyte',
])
def test_tier2_r1_boundary_special_characters_in_query(client, malicious_input):
    """Verifies that malicious or meta-character query strings are safely rejected with 400."""
    res = client.get(f'/api/trends/suggestions?aircraft_type={malicious_input}')
    assert res.status_code in (400, 404), f"Expected 400/404 for malicious query, got {res.status_code}"
