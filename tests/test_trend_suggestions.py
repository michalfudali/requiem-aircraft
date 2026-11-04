"""Unit and integration tests for Empirical Statistical Parameter Suggestions Engine (Milestone 1, R1).

Verifies get_trend_suggestions() and GET /api/trends/suggestions across all 7 aircraft classes:
- piston_ga, turboprop_regional, jet_business, jet_transport, glider, motoglider, uav.
"""
import math
import pytest
from app import app
from calculations.trends import (
    CLASSES,
    get_trend_suggestions,
    load_aircraft,
    select_references,
    SUGGESTION_TYPICAL_RANGES,
)

REQUIRED_PARAMS = [
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

REQUIRED_SUGGESTION_FIELDS = [
    'key',
    'name',
    'symbol',
    'unit',
    'suggested_value',
    'model_type',
    'equation',
    'r2',
    'n',
    'stats',
    'typical_range',
    'available_n',
    'provenance',
]


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


# =========================================================================
# 1. API Endpoint Contract Tests Across All 7 Classes
# =========================================================================

@pytest.mark.parametrize('ac_class', list(CLASSES.keys()))
def test_api_suggestions_endpoint_all_classes_schema(client, ac_class):
    """Verify GET /api/trends/suggestions returns valid schema for all 7 aircraft classes."""
    res = client.get(f'/api/trends/suggestions?aircraft_type={ac_class}')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['aircraft_type'] == ac_class
    assert data['m0'] is None
    assert 'suggestions' in data

    suggestions = data['suggestions']
    for param_key in REQUIRED_PARAMS:
        assert param_key in suggestions, f"Missing parameter {param_key} for {ac_class}"
        item = suggestions[param_key]
        assert item['key'] == param_key
        for field in REQUIRED_SUGGESTION_FIELDS:
            assert field in item, f"Missing field {field} in {param_key} for {ac_class}"

        # If populated, verify stats structure
        if item['stats'] is not None:
            stats = item['stats']
            for stat_field in ['min', 'max', 'mean', 'median']:
                assert stat_field in stats
                assert isinstance(stats[stat_field], (int, float))
            assert stats['min'] <= stats['max']

        # If typical_range is present, verify [min, max]
        if item['typical_range'] is not None:
            assert isinstance(item['typical_range'], list)
            assert len(item['typical_range']) == 2
            assert item['typical_range'][0] <= item['typical_range'][1]


@pytest.mark.parametrize('ac_class', list(CLASSES.keys()))
def test_direct_python_get_trend_suggestions_all_classes(ac_class):
    """Verify get_trend_suggestions direct function call across all 7 classes."""
    res = get_trend_suggestions(ac_class)
    assert res['status'] == 'ok'
    assert res['aircraft_type'] == ac_class
    assert res['m0'] is None
    assert set(res['suggestions'].keys()) == set(REQUIRED_PARAMS)


# =========================================================================
# 2. Dynamic Evaluation with m0 Provided vs Omitted
# =========================================================================

def test_piston_ga_sample_follows_design_mass(client):
    """Without m0 the whole class is the sample; with m0 (the design mass) the 50 aircraft nearest in MTOW."""
    res_no_m0 = client.get('/api/trends/suggestions?aircraft_type=piston_ga').get_json()
    assert res_no_m0['m0'] is None
    class_rows = select_references(dict(aircraft_type='piston_ga', engine_type='prop', trend_nearest_count=0))
    assert res_no_m0['sample']['selected_n'] == len(class_rows)
    # Equation (1) needs the design mass: without it the BIPOL_1 average is shown.
    assert res_no_m0['suggestions']['me_m0']['model_type'] == 'mean'

    res_with_m0 = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150.0').get_json()
    assert res_with_m0['m0'] == 1150.0
    assert res_with_m0['sample']['selected_n'] == min(50, len(class_rows))
    assert 'masie projektu 1150 kg' in res_with_m0['sample']['description']
    me = res_with_m0['suggestions']['me_m0']
    assert me['model_type'] == 'power'
    fit = me['provenance']['fit']
    assert me['suggested_value'] == pytest.approx(fit['A'] * 1150.0 ** fit['C'] * fit['k_vs'], abs=5e-4)
    for key in ('ws', 'pw'):
        item = res_with_m0['suggestions'][key]
        assert item['suggested_value'] > 0
        assert item['model_type'] in ('time_trend', 'mean')


def test_jet_transport_dynamic_m0_evaluation(client):
    """Verify dynamic evaluation of wing loading and thrust loading for jet_transport."""
    # Narrow-body jet (A320, 77000 kg)
    res_a320 = client.get('/api/trends/suggestions?aircraft_type=jet_transport&m0=77000&trend_nearest_count=20').get_json()
    assert res_a320['m0'] == 77000.0
    ws_a320 = res_a320['suggestions']['ws']['suggested_value']
    tw_a320 = res_a320['suggestions']['tw']['suggested_value']
    # A320: 77 000 kg / 122,6 m² ≈ 628 kg/m²
    assert 550.0 <= ws_a320 <= 650.0
    # T/W comes from the selected independent families, not the A320 alone.
    item = res_a320['suggestions']['tw']
    if item['model_type'] == 'mean':
        obs = item['provenance']['observations']
        assert tw_a320 == pytest.approx(sum(o['value'] * o['weight'] for o in obs) /
                                       sum(o['weight'] for o in obs), abs=.005)
    else:
        from calculations.trends import predict
        assert tw_a320 == pytest.approx(predict(item['provenance']['fit'], res_a320['forecast_year']), abs=.005)

    # Wide-body heavy jet (B747, 390000 kg): a different nearest-mass sample
    res_heavy = client.get('/api/trends/suggestions?aircraft_type=jet_transport&m0=390000&trend_nearest_count=20').get_json()
    ws_heavy = res_heavy['suggestions']['ws']['suggested_value']
    # Heavier similar aircraft have higher wing loading
    assert ws_heavy > ws_a320
    item = res_heavy['suggestions']['ws']
    if item['model_type'] == 'mean':
        obs = item['provenance']['observations']
        expected = sum(o['value'] * o['weight'] for o in obs) / sum(o['weight'] for o in obs)
    else:
        from calculations.trends import predict
        expected = predict(item['provenance']['fit'], res_heavy['forecast_year'])
    assert ws_heavy == pytest.approx(expected, abs=.05)


# =========================================================================
# 3. Propulsion Loading Mutual Exclusivity and Glider Unpowered Handling
# =========================================================================

def test_propeller_classes_propulsion_parameters(client):
    """Verify prop classes have pw populated and tw null."""
    for prop_class in ['piston_ga', 'turboprop_regional', 'motoglider']:
        data = client.get(f'/api/trends/suggestions?aircraft_type={prop_class}').get_json()
        pw = data['suggestions']['pw']
        tw = data['suggestions']['tw']
        assert pw['suggested_value'] is not None and pw['suggested_value'] > 0
        assert pw['unit'] == 'kg/kW'
        assert pw['n'] > 0
        assert pw['stats'] is not None
        # tw must be null
        assert tw['suggested_value'] is None
        assert tw['n'] == 0
        assert tw['stats'] is None


def test_jet_classes_propulsion_parameters(client):
    """Verify jet classes have tw populated and pw null."""
    for jet_class in ['jet_business', 'jet_transport']:
        data = client.get(f'/api/trends/suggestions?aircraft_type={jet_class}').get_json()
        tw = data['suggestions']['tw']
        pw = data['suggestions']['pw']
        assert tw['suggested_value'] is not None and 0.20 <= tw['suggested_value'] <= 0.45
        assert tw['unit'] == '−'
        assert tw['n'] > 0
        assert tw['stats'] is not None
        # pw must be null
        assert pw['suggested_value'] is None
        assert pw['n'] == 0
        assert pw['stats'] is None


def test_unpowered_glider_propulsion_is_null(client):
    """Verify unpowered glider has both pw and tw null."""
    data = client.get('/api/trends/suggestions?aircraft_type=glider').get_json()
    assert data['suggestions']['pw']['suggested_value'] is None
    assert data['suggestions']['pw']['n'] == 0
    assert data['suggestions']['tw']['suggested_value'] is None
    assert data['suggestions']['tw']['n'] == 0


# =========================================================================
# 4. Wing Configuration Effect on Dihedral Suggestion
# =========================================================================

def test_dihedral_is_the_sample_average_and_configuration_only_sets_the_comparison_range(client):
    """BIPOL_1 asks for the average dihedral; the wing layout changes only the literature range and warnings."""
    res_low = client.get('/api/trends/suggestions?aircraft_type=piston_ga&wing_configuration=low').get_json()
    res_high = client.get('/api/trends/suggestions?aircraft_type=piston_ga&wing_configuration=high').get_json()
    low, high = res_low['suggestions']['dihedral_deg'], res_high['suggestions']['dihedral_deg']
    assert low['suggested_value'] == high['suggested_value']
    assert low['model_type'] == 'mean'
    observations = low['provenance']['observations']
    weights = [o['weight'] for o in observations]
    mean = sum(o['value'] * o['weight'] for o in observations) / sum(weights)
    assert low['suggested_value'] == pytest.approx(mean, abs=0.05)
    assert low['typical_range'] == [3.5, 7.0] and high['typical_range'] == [0.0, 2.5]
    # The class mean is a low-wing value; a high-wing design is warned, not silently changed.
    assert any('górnopłatów' in w for w in high['provenance']['warnings'])


# =========================================================================
# 5. Control Surfaces and Tail Volume Ratios
# =========================================================================

@pytest.mark.parametrize('ac_class', list(CLASSES.keys()))
def test_control_surfaces_and_tail_volume_within_literature(ac_class):
    """Verify control surface chord/span ratios and V_H are within plausible aeronautical bounds."""
    res = get_trend_suggestions(ac_class)
    s = res['suggestions']

    # Horizontal tail volume V_H typically 0.40 to 1.20
    assert 0.40 <= s['vh']['suggested_value'] <= 1.20
    assert s['vh']['n'] > 0

    # Aileron span ratio typically 0.20 to 0.55
    assert 0.20 <= s['b_ail_ratio']['suggested_value'] <= 0.55
    assert s['b_ail_ratio']['n'] > 0

    # Aileron chord ratio typically 0.15 to 0.30
    assert 0.15 <= s['c_ail_ratio']['suggested_value'] <= 0.30
    assert s['c_ail_ratio']['n'] > 0

    # Elevator chord ratio typically 0.25 to 0.45
    assert 0.25 <= s['c_e_ratio']['suggested_value'] <= 0.45
    assert s['c_e_ratio']['n'] > 0

    # Rudder chord ratio typically 0.25 to 0.50
    assert 0.25 <= s['c_r_ratio']['suggested_value'] <= 0.50
    assert s['c_r_ratio']['n'] > 0


# =========================================================================
# 6. Small Cohort Handling (UAV & Glider)
# =========================================================================

def test_uav_small_cohort_handles_gracefully(client):
    """A small cohort (UAV) gives values traceable to every observation, with the sample-size warning."""
    res = client.get('/api/trends/suggestions?aircraft_type=uav&m0=25.0').get_json()
    assert res['status'] == 'ok'
    ws = res['suggestions']['ws']
    assert ws['n'] == len(ws['provenance']['observations']) >= 8
    assert ws['provenance']['observations'][0]['source']
    assert any('20 samolotów' in w for w in ws['provenance']['warnings'])
    me_m0 = res['suggestions']['me_m0']
    assert 0.45 <= me_m0['suggested_value'] <= 0.65


def test_glider_small_cohort_handles_gracefully(client):
    """Verify glider cohort (N=11) provides accurate high aspect ratio and low wing loading."""
    res = client.get('/api/trends/suggestions?aircraft_type=glider&m0=450.0').get_json()
    assert res['status'] == 'ok'
    assert res['suggestions']['ws']['suggested_value'] < 50.0
    # High aspect ratio standard for gliders
    assert res['suggestions']['ar']['suggested_value'] >= 18.0


# =========================================================================
# 7. Input Validation & Error Handling
# =========================================================================

def test_api_missing_aircraft_type_returns_400(client):
    """Verify missing aircraft_type returns HTTP 400 Bad Request."""
    res = client.get('/api/trends/suggestions')
    assert res.status_code == 400
    data = res.get_json()
    assert data['status'] == 'error'
    assert 'Missing required parameter' in data['message']


def test_api_unknown_aircraft_type_returns_400(client):
    """Verify invalid aircraft_type returns HTTP 400 Bad Request."""
    res = client.get('/api/trends/suggestions?aircraft_type=space_shuttle')
    assert res.status_code == 400
    data = res.get_json()
    assert data['status'] == 'error'
    assert 'Unknown aircraft_type' in data['message']


def test_api_negative_m0_returns_400(client):
    """Verify negative m0 returns HTTP 400 Bad Request."""
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=-100')
    assert res.status_code == 400
    data = res.get_json()
    assert data['status'] == 'error'


def test_api_non_numeric_m0_returns_400(client):
    """Verify non-numeric m0 returns HTTP 400 Bad Request."""
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=invalid_mass')
    assert res.status_code == 400
    data = res.get_json()
    assert data['status'] == 'error'


def test_api_zero_m0_is_treated_as_unknown_mass(client):
    """m0=0 means the design mass is unknown: the whole class is the sample, as without m0."""
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=0')
    assert res.status_code == 200
    data = res.get_json()
    assert data['m0'] is None
    plain = client.get('/api/trends/suggestions?aircraft_type=piston_ga').get_json()
    assert data['suggestions'] == plain['suggestions']


def test_direct_python_validation():
    """Verify ValueError is raised on invalid inputs in get_trend_suggestions."""
    with pytest.raises(ValueError, match="Unknown aircraft_type"):
        get_trend_suggestions('unsupported_class')

    with pytest.raises(ValueError, match="m0 must be a positive finite number"):
        get_trend_suggestions('piston_ga', m0=-50)

    with pytest.raises(ValueError, match="m0 must be a positive finite number"):
        get_trend_suggestions('piston_ga', m0=float('nan'))


# =========================================================================
# 8. Reactive In-Memory Recalculation Verification
# =========================================================================

def test_cache_clearing_reloads_catalog_without_crash():
    """Verify load_aircraft.cache_clear() triggers clean reload for suggestions."""
    load_aircraft.cache_clear()
    res = get_trend_suggestions('piston_ga', m0=1200.0)
    assert res['status'] == 'ok'
    selected = select_references(dict(aircraft_type='piston_ga', engine_type='prop', _reference_mass=1200))
    assert res['sample']['selected_n'] == len(selected)
    assert res['suggestions']['ws']['available_n'] == sum(r['wing_loading_kg_m2'] is not None for r in selected)
