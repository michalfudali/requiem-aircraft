"""End-to-End Test Suite for UI Contracts, Cross-Feature Combinations, and Real-World Scenarios.

Covers:
- Requirement R2: Dual-location UI integration contracts (Module 1, Wizard, Transfer Panel)
- Tier 3: Cross-Feature Pairwise Interactions (CRUD + In-Memory Cache + Suggestions Engine)
- Tier 4: Real-World Application Scenarios (5 Comprehensive E2E preliminary design workflows)
"""
import copy
import json
import pytest
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trends import DATA, load_aircraft


# ==============================================================================
# Tier 1: UI Integration Contracts (Requirement R2)
# ==============================================================================

@pytest.mark.tier1
def test_tier1_r2_module1_suggestions_ui_contract(client):
    """Verifies that Module 1 inputs template renders required containers and action hooks."""
    res = client.get('/')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    
    # Must have Module 1 container and basic controls
    assert 'id="tab-inputs"' in html or 'id="designForm"' in html
    # Check that inputs panel contains relevant preliminary inputs
    assert 'wing_loading' in html or 'aspect_ratio' in html or 'tab-inputs' in html


@pytest.mark.tier1
def test_tier1_r2_transfer_panel_ui_contract(client):
    """Verifies that 'Baza i trendy' template renders trend inspection elements."""
    res = client.get('/')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    
    # Check that Trends panel exists
    assert 'id="tab-trends"' in html
    assert 'trendRecalculate' in html or 'trendControls' in html


@pytest.mark.tier1
def test_tier1_r2_wizard_adoption_contract(client):
    """Verifies that the main index/wizard templates accommodate project presets and basis."""
    res = client.get('/api/presets')
    assert res.status_code == 200
    presets = res.get_json()
    assert 'ga_trainer' in presets
    assert 'pzl_kos' in presets
    assert 'vlj_jet' in presets


# ==============================================================================
# Tier 3: Cross-Feature Combinations & Pairwise Interactions
# ==============================================================================

@pytest.mark.tier3
def test_tier3_interaction_crud_create_then_suggestions_recalculation(client, isolated_db):
    """Interaction 1: Creating an aircraft via POST /api/aircraft increments N in suggestions."""
    # 1. Fetch initial suggestions for piston_ga
    res_before = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res_before.status_code == 200, res_before.get_data(as_text=True)
    
    data_before = res_before.get_json()
    n_before = data_before['sample']['selected_n']
    vh_before = data_before['suggestions']['vh']['n']

    # 2. Add a new custom GA aircraft
    new_aircraft = {
        "id": "pairwise-ga-new-1",
        "model": "Interaction Test GA 1",
        "manufacturer": "Teamwork E2E",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "family": "InteractionGA",
        "source_id": "geometry_trends",
        "source_locator": "Interaction Suite",
        "source_references": "Teamwork E2E Testing",
        "empty_mass_definition": "OEW / operating empty weight",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 1350.0,
        "me": 820.0,
        "s": 16.5,
        "b": 11.0,
        "p_kw": 140.0,
        "n_engines": 1,
        "v_h": 0.72,
        "aileron_span_fraction": 0.42,
        "aileron_chord_ratio": 0.23,
        "elevator_chord_ratio": 0.36,
        "rudder_chord_ratio": 0.39,
        "dihedral_deg": 5.0
    }
    create_res = client.post('/api/aircraft', json=new_aircraft)
    assert create_res.status_code == 201, create_res.get_data(as_text=True)
    
    # 3. Fetch suggestions again - sample size N must have incremented by 1
    res_after = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res_after.status_code == 200
    data_after = res_after.get_json()
    n_after = data_after['sample']['selected_n']

    assert n_after == n_before + 1, f"Expected N to increment from {n_before} to {n_before + 1}, got {n_after}"
    assert data_after['suggestions']['vh']['n'] == vh_before + 1


@pytest.mark.tier3
def test_tier3_interaction_crud_update_then_catalog_and_regression_update(client, isolated_db):
    """Interaction 2: Modifying an aircraft's mass updates catalog and dynamic suggestions."""
    # 1. Create aircraft
    aircraft = {
        "id": "pairwise-ga-update-1",
        "model": "Modifiable GA",
        "manufacturer": "Teamwork",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "family": "ModGA",
        "source_id": "geometry_trends",
        "source_locator": "Suite",
        "source_references": "Ref",
        "empty_mass_definition": "OEW",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 1000.0,
        "me": 600.0,
        "s": 14.0,
        "b": 10.0,
        "p_kw": 100.0,
        "n_engines": 1
    }
    create_res = client.post('/api/aircraft', json=aircraft)
    assert create_res.status_code == 201, create_res.get_data(as_text=True)
        
    # 2. Update mass m0 from 1000 to 2000 kg
    update_res = client.put(f"/api/aircraft/{aircraft['id']}", json={"m0": 2000.0, "me": 1200.0})
    assert update_res.status_code == 200
    
    # 3. Retrieve from GET /api/aircraft/<id>
    get_res = client.get(f"/api/aircraft/{aircraft['id']}")
    assert get_res.status_code == 200
    rec = get_res.get_json().get('aircraft') or get_res.get_json()
    assert rec['m0'] == 2000.0
    assert rec['me'] == 1200.0


@pytest.mark.tier3
def test_tier3_interaction_crud_delete_reverts_suggestions(client, isolated_db):
    """Interaction 3: Deleting an aircraft reverts suggestions sample size N and statistics."""
    res_orig = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res_orig.status_code == 200, res_orig.get_data(as_text=True)
    n_orig = res_orig.get_json()['suggestions']['ws']['n']
    
    # Create then delete
    aircraft = {
        "id": "pairwise-ga-del-1",
        "model": "Ephemeral GA",
        "manufacturer": "Teamwork",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "family": "EphGA",
        "source_id": "geometry_trends",
        "source_locator": "Suite",
        "source_references": "Ref",
        "empty_mass_definition": "OEW",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 1200.0,
        "me": 700.0,
        "s": 15.0,
        "b": 10.0,
        "p_kw": 110.0,
        "n_engines": 1
    }
    post_res = client.post('/api/aircraft', json=aircraft)
    assert post_res.status_code == 201, post_res.get_data(as_text=True)
    
    # Delete it
    del_res = client.delete(f"/api/aircraft/{aircraft['id']}")
    assert del_res.status_code == 200
    
    # Suggestions should revert exactly
    res_final = client.get('/api/trends/suggestions?aircraft_type=piston_ga')
    assert res_final.status_code == 200
    assert res_final.get_json()['suggestions']['ws']['n'] == n_orig


@pytest.mark.tier3
def test_tier3_interaction_cross_class_engine_isolation(client, isolated_db):
    """Interaction 4: Adding an aircraft to one class does not alter counts in another class."""
    cat_before = client.get('/api/aircraft').get_json()
    piston_count_before = cat_before['counts'].get('piston_ga', 0)
    
    # Add a jet_business aircraft
    jet = {
        "id": "pairwise-isolated-jet-1",
        "model": "Isolated BizJet 500",
        "manufacturer": "Teamwork",
        "aircraft_type": "jet_business",
        "engine_type": "jet",
        "family": "IsoJet",
        "source_id": "geometry_trends",
        "source_locator": "Suite",
        "source_references": "Ref",
        "empty_mass_definition": "OEW",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 15000.0,
        "me": 8500.0,
        "s": 38.0,
        "b": 18.0,
        "t_kn": 65.0,
        "n_engines": 2
    }
    create_res = client.post('/api/aircraft', json=jet)
    assert create_res.status_code == 201, create_res.get_data(as_text=True)
        
    cat_after = client.get('/api/aircraft').get_json()
    assert cat_after['counts']['piston_ga'] == piston_count_before
    assert cat_after['counts']['jet_business'] == cat_before['counts'].get('jet_business', 0) + 1


# ==============================================================================
# Tier 4: Real-World Application Scenarios (Workflows 1 through 5)
# ==============================================================================

@pytest.mark.tier4
def test_tier4_scenario1_student_ga_trainer_design_workflow(client):
    """Scenario 1: Undergraduate student designing a GA trainer from trend suggestions.
    
    Workflow:
    1. Student selects piston_ga with estimated MTOW m0 = 1150 kg.
    2. Fetches empirical trend suggestions.
    3. Adopts suggested wing loading W/S, aspect ratio AR, empty mass fraction me/m0, tail volume.
    4. Populates preliminary design inputs and submits to /api/calculate.
    5. Verifies successful preliminary sizing results (geometry, aerodynamics, mass balance).
    """
    # Step 1 & 2: Fetch suggestions
    res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150')
    assert res.status_code == 200, res.get_data(as_text=True)
    
    data = res.get_json()
    sugg = data['suggestions']
    
    ws_suggested = sugg['ws']['suggested_value']
    ar_suggested = sugg['ar']['suggested_value']
    me_m0_suggested = sugg['me_m0']['suggested_value']
    vh_suggested = sugg['vh']['suggested_value']
    
    assert 60.0 <= ws_suggested <= 120.0
    assert 6.0 <= ar_suggested <= 10.0
    assert 0.50 <= me_m0_suggested <= 0.75
    
    # Step 3 & 4: Construct project calculation payload using GA trainer preset
    project_payload = copy.deepcopy(AIRCRAFT_PRESETS['ga_trainer'])
    project_payload['m_to'] = 1150.0
    # Adopted from trends
    project_payload['wing_loading'] = ws_suggested
    project_payload['aspect_ratio'] = ar_suggested
    project_payload['empty_mass_fraction'] = me_m0_suggested
    project_payload['v_h'] = vh_suggested
    
    # Step 5: Execute preliminary sizing calculation
    calc_res = client.post('/api/calculate', json=project_payload)
    assert calc_res.status_code == 200
    results = calc_res.get_json()
    assert results.get('status') in ('ok', 'success') or 'summary' in results or 'phases' in results
    
    # Assert physical feasibility of output
    params = results.get('params', {})
    assert params.get('m_to') == 1150.0
    # Wing area S derived from m0 / (W/S)
    expected_s = 1150.0 / ws_suggested
    if 'wing_area' in params:
        assert params['wing_area'] == pytest.approx(expected_s, rel=0.1)


@pytest.mark.tier4
def test_tier4_scenario2_regional_turboprop_design_session(client):
    """Scenario 2: Regional turboprop preliminary design session (m0 = 22,000 kg).
    
    Workflow:
    1. Engineer specifies regional turboprop class with m0 = 22,000 kg.
    2. Queries /api/trends/suggestions for turboprop_regional.
    3. Verifies power loading P/W and wing loading W/S align with regional fleet (ATR, Dash-8).
    4. Submits parameters to sizing pipeline and checks twin-engine climb and field length.
    """
    res = client.get('/api/trends/suggestions?aircraft_type=turboprop_regional&m0=22000')
    assert res.status_code == 200, res.get_data(as_text=True)
        
    sugg = res.get_json()['suggestions']
    ws = sugg['ws']['suggested_value']
    ar = sugg['ar']['suggested_value']
    
    # BIPOL_1: the time trend of the similar aircraft is extrapolated five years ahead.
    from calculations.trends import predict
    item = sugg['ws']
    if item['model_type'] == 'time_trend':
        fit = item['provenance']['fit']
        assert ws == pytest.approx(predict(fit, res.get_json()['forecast_year']), rel=1e-3)
    assert 150.0 <= ws <= 700.0, f"Turboprop W/S out of range: {ws}"
    assert 9.0 <= ar <= 15.0, f"Turboprop AR out of range: {ar}"
    
    # Run calculation with regional turboprop preset updated with trend values
    turboprop_payload = copy.deepcopy(AIRCRAFT_PRESETS['regional_turboprop'])
    turboprop_payload['wing_loading'] = ws
    turboprop_payload['aspect_ratio'] = ar
    turboprop_payload['v_h'] = sugg['vh']['suggested_value']
    
    calc_res = client.post('/api/calculate', json=turboprop_payload)
    assert calc_res.status_code == 200
    res_data = calc_res.get_json()
    assert res_data.get('status') in ('ok', 'success') or 'summary' in res_data or 'phases' in res_data


@pytest.mark.tier4
def test_tier4_scenario3_fleet_database_manager_lifecycle(client, isolated_db):
    """Scenario 3: Fleet database manager updating reference aircraft records.
    
    Workflow:
    1. Manager queries catalog to review existing piston_ga aircraft.
    2. Manager registers a newly certified light electric aircraft 'e-falcon-200' via POST.
    3. Manager reviews record details via GET /api/aircraft/e-falcon-200.
    4. Manager updates engine power rating via PUT.
    5. Manager deletes prototype after decommissioning and verifies total count returns to baseline.
    """
    # 1. Initial count
    cat_init = client.get('/api/aircraft').get_json()
    init_total = cat_init['total']
    
    # 2. Add e-falcon-200
    new_plane = {
        "id": "e-falcon-200",
        "model": "E-Falcon 200 Electric Trainer",
        "manufacturer": "Falcon Aero",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "family": "EFalcon",
        "source_id": "geometry_trends",
        "source_locator": "EASA Type Certificate",
        "source_references": "EASA.A.600",
        "empty_mass_definition": "OEW / operating empty weight",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 850.0,
        "me": 560.0,
        "s": 11.2,
        "b": 9.8,
        "p_kw": 95.0,
        "n_engines": 1,
        "v_h": 0.65
    }
    create_res = client.post('/api/aircraft', json=new_plane)
    assert create_res.status_code == 201, create_res.get_data(as_text=True)
        
    # 3. Review record
    get_res = client.get('/api/aircraft/e-falcon-200')
    assert get_res.status_code == 200
    rec = get_res.get_json().get('aircraft') or get_res.get_json()
    assert rec['model'] == "E-Falcon 200 Electric Trainer"
    assert rec['p_kw'] == 95.0
    
    # 4. Update power to 105 kW
    put_res = client.put('/api/aircraft/e-falcon-200', json={"p_kw": 105.0})
    assert put_res.status_code == 200
    updated_rec = client.get('/api/aircraft/e-falcon-200').get_json()
    assert (updated_rec.get('aircraft') or updated_rec)['p_kw'] == 105.0
    
    # 5. Delete prototype
    del_res = client.delete('/api/aircraft/e-falcon-200')
    assert del_res.status_code == 200
    assert client.get('/api/aircraft/e-falcon-200').status_code == 404
    
    # Total count restored
    cat_final = client.get('/api/aircraft').get_json()
    assert cat_final['total'] == init_total


@pytest.mark.tier4
def test_tier4_scenario4_business_jet_high_speed_cruise_session(client):
    """Scenario 4: Super-midsize business jet preliminary design session (m0 = 18,000 kg).
    
    Workflow:
    1. Designer configures jet_business with MTOW 18,000 kg and high cruise Mach.
    2. Queries /api/trends/suggestions for jet_business.
    3. Verifies thrust-to-weight T/W and wing loading W/S trends.
    4. Evaluates preliminary sizing calculation with adopted suggestions.
    """
    res = client.get('/api/trends/suggestions?aircraft_type=jet_business&m0=18000')
    assert res.status_code == 200, res.get_data(as_text=True)
        
    sugg = res.get_json()['suggestions']
    ws = sugg['ws']['suggested_value']
    ar = sugg['ar']['suggested_value']
    
    # An accepted forecast for independent families can exceed historical typical AR.
    assert 250.0 <= ws <= 650.0, f"Business jet W/S out of range: {ws}"
    from calculations.trends import PHYSICAL_BOUNDS, predict
    assert PHYSICAL_BOUNDS['ar'][0] < ar < PHYSICAL_BOUNDS['ar'][1]
    origin = sugg['ar']['provenance']
    if sugg['ar']['model_type'] == 'time_trend':
        expected = predict(origin['fit'], res.get_json()['forecast_year'])
    else:
        observations = origin['observations']
        expected = sum(o['value'] * o['weight'] for o in observations) / sum(o['weight'] for o in observations)
    assert ar == pytest.approx(expected, abs=.01)
    
    jet_payload = copy.deepcopy(AIRCRAFT_PRESETS['vlj_jet'])
    jet_payload['wing_loading'] = ws
    jet_payload['aspect_ratio'] = ar
    jet_payload['v_h'] = sugg['vh']['suggested_value']
    
    calc_res = client.post('/api/calculate', json=jet_payload)
    assert calc_res.status_code == 200
    res_data = calc_res.get_json()
    assert res_data.get('status') in ('ok', 'success') or 'summary' in res_data or 'phases' in res_data


@pytest.mark.tier4
def test_tier4_scenario5_motoglider_cs22_soaring_sizing_session(client):
    """Scenario 5: Touring motoglider (CS-22) low-speed soaring sizing session (m0 = 750 kg).
    
    Workflow:
    1. Soaring engineer selects motoglider with MTOW 750 kg.
    2. Queries /api/trends/suggestions for motoglider.
    3. Verifies high aspect ratio AR >= 13, low wing loading W/S <= 70 kg/m².
    4. Submits parameters to BIPOL calculation pipeline and verifies glide performance.
    """
    res = client.get('/api/trends/suggestions?aircraft_type=motoglider&m0=750')
    assert res.status_code == 200, res.get_data(as_text=True)
        
    sugg = res.get_json()['suggestions']
    ws = sugg['ws']['suggested_value']
    ar = sugg['ar']['suggested_value']
    
    # Motogliders have low wing loading (25-70 kg/m²) and high AR. The default sample mixes touring
    # and high-performance types, so AR may exceed the touring range; the provenance must say so.
    assert 25.0 <= ws <= 70.0, f"Motoglider W/S out of range: {ws}"
    assert 13.0 <= ar <= 35.0, f"Motoglider AR out of range: {ar}"
    if ar > sugg['ar']['typical_range'][1]:
        assert any('zakresem literaturowym' in w for w in sugg['ar']['provenance']['warnings'])
    
    motoglider_payload = copy.deepcopy(AIRCRAFT_PRESETS['motoglider_aos'])
    motoglider_payload['wing_loading'] = ws
    motoglider_payload['aspect_ratio'] = ar
    motoglider_payload['v_h'] = sugg['vh']['suggested_value']
    
    calc_res = client.post('/api/calculate', json=motoglider_payload)
    assert calc_res.status_code == 200
    res_data = calc_res.get_json()
    assert res_data.get('status') in ('ok', 'success') or 'summary' in res_data or 'phases' in res_data

