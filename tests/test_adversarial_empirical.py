"""Adversarial and Empirical Verification Test Suite for Milestone 1 Suggestions Engine and API.

Written by Challenger 1 (teamwork_preview_challenger) to stress-test:
1. Parameter estimation correctness across all 7 classes.
2. Mathematical stability under extreme MTOW values (1 kg to 10^7 kg, 10^300 kg, 10^-300 kg).
3. Non-positive numbers, empty parameters, division by zero, domain errors.
4. Physical invariants (0 < me/m0 < 1, W/S > 0, AR > 0, V_H > 0, control surface ratios in (0, 1)).
5. API input validation, robustness, and boundary handling.
"""
import math
import pytest
from app import app
from calculations.trends import (
    CLASSES,
    get_trend_suggestions,
    load_aircraft,
    select_references,
    predict,
    fit_regression,
    compute_vector_stats,
    SUGGESTION_TYPICAL_RANGES,
)

ALL_CLASSES = list(CLASSES.keys())

EXTREME_MASSES = [
    1e-300,
    1e-50,
    1e-15,
    1e-5,
    1e-3,
    0.01,
    0.1,
    1.0,
    5.0,
    25.0,
    100.0,
    500.0,
    1150.0,
    5000.0,
    18600.0,
    77000.0,
    150000.0,
    400000.0,
    1e6,
    1e7,
    1e8,
    1e15,
    1e50,
    1e300,
]

REQUIRED_KEYS = [
    'ws',
    'ar',
    'me_m0',
    'pw',
    'tw',
    'vh',
    'v_v',
    'b_ail_ratio',
    'c_ail_ratio',
    'c_e_ratio',
    'c_r_ratio',
    'dihedral_deg',
]


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


# =========================================================================
# 1. Parameter Estimation Correctness Across All 7 Classes
# =========================================================================

@pytest.mark.parametrize('ac_class', ALL_CLASSES)
def test_empirical_estimation_correctness(ac_class):
    """Verify parameters, formulas, sample sizes, and statistics for each aircraft class."""
    res = get_trend_suggestions(ac_class)
    assert res['status'] == 'ok'
    assert res['aircraft_type'] == ac_class
    s = res['suggestions']

    # All 12 parameters must be present
    assert set(s.keys()) == set(REQUIRED_KEYS)

    # Verify the independent-family sample of this class and its default propulsion.
    all_ac = select_references(dict(aircraft_type=ac_class, engine_type=res['engine_type'], trend_nearest_count=0))
    n_total = len(all_ac)
    assert n_total > 0, f"Class {ac_class} has 0 records in catalog"
    assert res['sample']['selected_n'] == n_total

    # Wing loading n
    n_ws_catalog = len([r for r in all_ac if r.get('m0') and r.get('wing_loading_kg_m2')])
    assert s['ws']['available_n'] == n_ws_catalog
    assert s['ws']['suggested_value'] > 0

    # Empty mass fraction n
    n_me_catalog = len([r for r in all_ac if r.get('m0') and r.get('empty_fraction') and 0.15 < r['empty_fraction'] < 0.95])
    assert s['me_m0']['n'] == n_me_catalog
    assert 0.15 < s['me_m0']['suggested_value'] < 0.95

    # A constrained slope can fit worse than the mean: R² may be negative.
    # Keep that diagnostic; clipping it to zero would hide poor agreement.
    for k, item in s.items():
        if item['r2'] is not None:
            assert math.isfinite(item['r2']) and item['r2'] <= 1.0
            if item['r2'] < 0:
                assert k == 'me_m0' and item['provenance']['fit']['physically_constrained']

        # Stats bounds when present
        if item['stats'] is not None:
            st = item['stats']
            assert st['min'] <= st['mean'] <= st['max'] + 1e-6
            assert st['min'] <= st['median'] <= st['max']
            assert st['min'] > 0 if k in ('ws', 'ar', 'me_m0', 'vh') else True


# =========================================================================
# 2. Stress Test Mathematical Stability (Extreme MTOW Values)
# =========================================================================

@pytest.mark.parametrize('ac_class', ALL_CLASSES)
@pytest.mark.parametrize('mass', EXTREME_MASSES)
def test_mathematical_stability_extreme_mtow(ac_class, mass):
    """Stress test power-law and linear regressions against extreme MTOW (10^-300 to 10^300 kg).

    Must never raise ZeroDivisionError, OverflowError, ValueError, or produce NaN / Inf.
    """
    res = get_trend_suggestions(ac_class, m0=mass)
    assert res['status'] == 'ok'
    assert res['m0'] == mass

    s = res['suggestions']
    for k, item in s.items():
        val = item['suggested_value']
        if val is not None:
            assert isinstance(val, (int, float)), f"Non-numeric suggested_value in {ac_class}.{k} for m0={mass}: {val}"
            assert math.isfinite(val), f"Non-finite suggested_value in {ac_class}.{k} for m0={mass}: {val}"
            assert not math.isnan(val), f"NaN suggested_value in {ac_class}.{k} for m0={mass}"


# =========================================================================
# 3. Physical Invariants Verification Across Full Operational Range
# =========================================================================

@pytest.mark.parametrize('ac_class', ALL_CLASSES)
@pytest.mark.parametrize('mass', [1.0, 10.0, 50.0, 500.0, 1150.0, 10000.0, 77000.0, 1e6, 1e7])
def test_physical_invariants_hold(ac_class, mass):
    """Verify that physical aeronautical invariants hold across the entire mass spectrum:

    - 0 < me/m0 < 1
    - W/S > 0
    - AR > 0
    - V_H > 0
    - 0 < b_ail/(b/2) < 1
    - 0 < c_ail/c < 1
    - 0 < c_e/c_H < 1
    - 0 < c_r/c_V < 1
    - 0 <= Gamma <= 15 deg
    """
    res = get_trend_suggestions(ac_class, m0=mass)
    s = res['suggestions']

    # Empty mass fraction invariant: 0 < me/m0 < 1
    me_val = s['me_m0']['suggested_value']
    assert 0.0 < me_val < 1.0, f"Empty mass fraction invariant violated: {me_val} for {ac_class} m0={mass}"

    # Wing loading invariant: W/S > 0
    ws_val = s['ws']['suggested_value']
    assert ws_val > 0.0, f"Wing loading invariant violated: {ws_val} for {ac_class} m0={mass}"

    # Aspect ratio invariant: AR > 0 (and plausible aeronautical range 2.0 to 60.0)
    ar_val = s['ar']['suggested_value']
    assert 2.0 <= ar_val <= 60.0, f"Aspect ratio invariant violated: {ar_val} for {ac_class} m0={mass}"

    # Geometry averages exist only where the nearest-mass sample has geometry data;
    # a missing average stays missing and says so instead of taking a default.
    for key, low, high in (('vh', 0.2, 2.0), ('b_ail_ratio', 0.0, 1.0), ('c_ail_ratio', 0.0, 1.0),
                           ('c_e_ratio', 0.0, 1.0), ('c_r_ratio', 0.0, 1.0), ('dihedral_deg', 0.0, 15.0)):
        value = s[key]['suggested_value']
        if value is None:
            assert s[key]['available_n'] == 0 and s[key]['provenance']['warnings']
        else:
            assert low <= value <= high, f"{key} invariant violated: {value} for {ac_class} m0={mass}"

    # Propulsion exclusivity and positivity
    if ac_class in ('piston_ga', 'turboprop_regional', 'motoglider', 'uav'):
        pw_val = s['pw']['suggested_value']
        assert pw_val is not None and pw_val > 0, f"Power loading must be positive for {ac_class}"
        assert s['tw']['suggested_value'] is None, f"Thrust loading must be None for prop class {ac_class}"
    elif ac_class in ('jet_business', 'jet_transport'):
        tw_val = s['tw']['suggested_value']
        assert tw_val is not None and 0.0 < tw_val < 1.0, f"Thrust loading must be in (0, 1) for {ac_class}"
        assert s['pw']['suggested_value'] is None, f"Power loading must be None for jet class {ac_class}"
    elif ac_class == 'glider':
        assert s['pw']['suggested_value'] is None
        assert s['tw']['suggested_value'] is None


# =========================================================================
# 4. Stress Test Non-Positive Numbers and Domain Errors
# =========================================================================

@pytest.mark.parametrize('invalid_m0', [0, -1, -0.0001, -1e7, float('nan'), float('inf'), float('-inf'), 'abc', ''])
def test_direct_call_rejects_invalid_m0(invalid_m0):
    """Direct get_trend_suggestions() must raise ValueError on non-positive or non-finite m0."""
    with pytest.raises(ValueError, match="m0 must be a positive finite number"):
        get_trend_suggestions('piston_ga', m0=invalid_m0)


@pytest.mark.parametrize('invalid_ac', ['', 'space_shuttle', 'submarine', 'heli', None, 123])
def test_direct_call_rejects_invalid_class(invalid_ac):
    """Direct get_trend_suggestions() must raise ValueError on unknown aircraft class."""
    with pytest.raises(ValueError, match="Unknown aircraft_type"):
        get_trend_suggestions(invalid_ac)


# =========================================================================
# 5. API Robustness and Boundary Tests
# =========================================================================

def test_api_zero_m0_behavior(client):
    """m0=0 in query param is treated as unspecified m0: the whole class is the sample."""
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=0')
    assert res.status_code == 200
    data = res.get_json()
    assert data['m0'] is None
    assert 'wszystkie pasujące konstrukcje' in data['sample']['description']


@pytest.mark.parametrize('bad_param', ['m0=-5', 'm0=-1e-15', 'm0=nan', 'm0=inf', 'm0=-inf', 'm0=text'])
def test_api_rejects_bad_m0_with_400(client, bad_param):
    """API must return HTTP 400 with descriptive error message for invalid m0."""
    res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&{bad_param}')
    assert res.status_code == 400
    data = res.get_json()
    assert data['status'] == 'error'


@pytest.mark.parametrize('mass_str', ['1', '10.5', '1150', '77000', '1e6', '10000000'])
def test_api_valid_numeric_m0_strings(client, mass_str):
    """API parses various valid float representations correctly."""
    res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={mass_str}')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['m0'] == float(mass_str)


# =========================================================================
# 6. Low-level Regression Engine Robustness
# =========================================================================

def test_fit_regression_edge_cases():
    """Verify fit_regression() handles degeneracies without crashing."""
    # Empty points
    assert fit_regression([]) is None

    # Less than 3 points
    assert fit_regression([(1, 2), (2, 3)]) is None

    # Points with NaN or Inf
    assert fit_regression([(1, 2), (2, float('nan')), (3, 4)]) is None  # remaining 2 pts < 3

    # Identical x values (sxx == 0)
    assert fit_regression([(5.0, 1.0), (5.0, 2.0), (5.0, 3.0)]) is None

    # Power law with non-positive points
    assert fit_regression([(0, 1), (1, 2), (2, 3)], power=True) is None
    assert fit_regression([(-1, 1), (1, 2), (2, 3)], power=True) is None
    assert fit_regression([(1, -1), (2, 2), (3, 3)], power=True) is None

    # predict() with non-finite or non-positive x
    fit_power = {'kind': 'power', 'intercept': 2.0, 'C': 0.5}
    assert predict(fit_power, -5) is None
    assert predict(fit_power, 0) is None
    assert predict(fit_power, float('nan')) is None
    assert predict(fit_power, float('inf')) is None

    fit_linear = {'kind': 'linear', 'intercept': 10.0, 'slope': 2.0}
    assert predict(fit_linear, float('nan')) is None
    assert predict(fit_linear, float('inf')) is None
    assert predict(None, 100) is None
