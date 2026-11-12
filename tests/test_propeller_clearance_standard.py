"""Independent limits from EASA CS-22 Amdt 3, page 80, CS 22.925(a)."""
import pytest

from calculations.geometry import axis_height_m
from calculations.empennage import calculate_propulsion_clearance
from calculations.landing_gear import calculate_fuselage_and_gear


@pytest.mark.parametrize('layout,minimum', [('tricycle', .180), ('tailwheel', .230)])
def test_cs22_axis_height_uses_the_correct_limit_for_each_gear_layout(layout, minimum):
    p = dict(engine_type='prop', engine_location='nose', landing_gear_type=layout)
    assert axis_height_m(p, .5, 1.7) == pytest.approx(.85+minimum)


@pytest.mark.parametrize('layout,minimum', [('tricycle', .180), ('tailwheel', .230)])
@pytest.mark.parametrize('offset,passed', [(-.001, False), (0., True), (.001, True)])
def test_source_limits_are_used_under_static_deflection(layout, minimum, offset, passed):
    p = dict(engine_type='prop', landing_gear_type=layout, propeller_diameter_m=2.,
             engine_power_kw=120., prop_shaft_height_m=1+minimum+.08+offset,
             gear_compressed_deflection_m=.08)
    result = calculate_propulsion_clearance(p)
    assert result['ground_clearance_req_m'] == minimum
    assert result['ground_clearance_passed'] is passed


@pytest.mark.parametrize('layout,minimum', [('tricycle', .180), ('tailwheel', .230)])
def test_rounding_cannot_make_inadequate_landing_gear_clearance_compliant(layout, minimum):
    p = dict(landing_gear_type=layout, propeller_diameter_m=2., m0=1100,
             prop_shaft_height_m=1+minimum+.1+.03-.0001, oleo_stroke_m=.1, tire_deflection_m=.03)
    result = calculate_fuselage_and_gear(p)
    assert result['propeller_clearance_compliant'] is False


def test_canonical_layout_overrides_the_legacy_gear_type():
    result = calculate_propulsion_clearance(dict(engine_power_kw=120, landing_gear_type='tailwheel',
        gear_type='tricycle', propeller_diameter_m=2., prop_shaft_height_m=1.28,
        gear_compressed_deflection_m=.08))
    assert result['ground_clearance_req_m'] == .230
    assert result['ground_clearance_passed'] is False


@pytest.mark.parametrize('engine', ['none', 'jet'])
def test_aircraft_without_a_propeller_does_not_get_a_fictitious_clearance(engine):
    result = calculate_propulsion_clearance(dict(engine_type=engine))
    assert result['ground_clearance_m'] is None
    assert result['ground_clearance_req_m'] is None
    assert result['ground_clearance_passed'] is None
    gear = calculate_fuselage_and_gear(dict(engine_type=engine))
    assert gear['propeller_clearance_m'] is None
    assert gear['propeller_clearance_compliant'] is None


@pytest.mark.parametrize('location,count', [('nose', 2), ('rear', 1), ('wing', 2), ('retractable', 1)])
def test_without_shaft_positions_the_project_does_not_claim_clearance_is_verified(location, count):
    from calculations.propeller_clearance import nominal_ground_assessment
    assessment = nominal_ground_assessment(dict(engine_type='prop', engine_location=location,
        n_engines=count, landing_gear_type='tailwheel'), 1.08, 1.7)
    assert assessment['clearance_m'] is None
    assert assessment['nominal_passed'] is None
    assert assessment['certification_compliant'] is None


def test_water_clearance_requires_a_waterline_instead_of_inheriting_a_ground_check():
    from calculations.propeller_clearance import nominal_ground_assessment
    assessment = nominal_ground_assessment(dict(engine_type='prop', operating_surface='water'), 1.4, 2.)
    assert assessment['required_m'] is assessment['clearance_m'] is assessment['nominal_passed'] is None
    gear = calculate_fuselage_and_gear(dict(engine_type='prop', operating_surface='water', propeller_diameter_m=2.))
    assert gear['propeller_clearance_compliant'] is None


@pytest.mark.parametrize('height,diameter', [(None,1.7), (float('nan'),1.7), (1.08,0), (-1,1.7)])
def test_invalid_dimensions_cannot_produce_a_nominal_result(height, diameter):
    from calculations.propeller_clearance import nominal_ground_assessment
    with pytest.raises(ValueError, match='dodatnie i skończone'):
        nominal_ground_assessment(dict(engine_type='prop'), height, diameter)


def test_legacy_taildragger_and_unknown_layout_are_handled_explicitly():
    from calculations.propeller_clearance import minimum_ground_clearance_m
    assert minimum_ground_clearance_m(dict(gear_type='taildragger')) == .23
    with pytest.raises(ValueError, match='Nieznany układ'):
        minimum_ground_clearance_m(dict(landing_gear_type='unknown'))


@pytest.mark.parametrize('layout,height,minimum', [('tailwheel',1.08,.230), ('tricycle',1.03,.180)])
def test_topic7_publishes_a_nominal_calculation_without_claiming_complete_cs22_compliance(layout, height, minimum):
    import json
    from pathlib import Path
    from calculations import run_bipol_project
    from calculations.calc_sheet import build_sheet
    p = json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    result = run_bipol_project(dict(p, landing_gear_type=layout))
    assessment = result['geometry']['propeller_ground_clearance']
    assert result['geometry']['gear']['axis_height_m'] == pytest.approx(height)
    assert assessment['clearance_m'] == pytest.approx(minimum)
    assert assessment['required_m'] == minimum
    assert assessment['nominal_passed'] is True
    assert assessment['certification_compliant'] is None
    assert result['bipol_projects']['p3']['blueprint_checks']['prop_ground_clearance_assessment'] == assessment
    sheet = build_sheet(result)
    for key in ['pc_ground', 'pc_margin']:
        assert sheet.entries[key]['consistent']
    assert sheet.entries['pc_H']['consistent']
    assert sheet.entries['pc_margin']['value'] == 0.


@pytest.mark.parametrize('category,rule', [('cs22_motoglider','cs22.925a'), ('jar23_normal','cs23.925a'), ('cs25_transport','cs25.925a')])
def test_ground_requirement_has_a_registered_source_for_the_category(category, rule):
    from calculations.propeller_clearance import clearance_rule
    from calculations import regulations as R
    found = clearance_rule(dict(category=category))
    assert found['id'] == rule
    assert R.find_rules(found['paragraph']) == [rule]
    assert R.find_rules(found['paragraph'].replace('CS ', 'CS-')) == [rule]
