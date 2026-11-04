"""User operations for profile selection and every additional P2 option."""
import pytest

from browser_helpers import edit_inputs, navigate, reveal_details
from calculations.presets import AIRCRAFT_PRESETS

pytestmark = pytest.mark.browser

DAT = 'CUSTOM UI PROFILE\n' + '\n'.join(f'{x} {y}' for x,y in (
    (1,.001),(.5,.06),(.3,.075),(.1,.05),(.025,.025),(0,0),
    (.025,-.015),(.1,-.025),(.3,-.03),(.5,-.02),(1,0)))


def setup_ga(page):
    page.evaluate('async params => {loadProjectIntoForm({name:"P2 test",params}); await performCalculation();}',
                  dict(AIRCRAFT_PRESETS['ga_trainer'], wing_input_mode='loading'))
    navigate(page, 'tab-feasibility')


def apply(page, expected):
    with page.expect_response(lambda r: '/api/projects/' in r.url and r.request.method == 'PUT'):
        page.locator('#p2AirfoilEditor [data-p2-calculate]').click()
    page.wait_for_function(expected, timeout=60000)


def test_profile_selection_is_shared_with_p3_saved_and_reported(studio):
    page, base, _ = studio; setup_ga(page)
    page.locator('#p2AirfoilSelect').select_option('NACA 2415')
    page.locator('#airfoil_source').fill('Geometria analityczna NACA — źródło autora UI')
    apply(page, 'currentResults.params.airfoil === "NACA 2415"')
    assert page.evaluate('currentResults.profile_geometry.tc_ratio') == pytest.approx(.15, abs=.0001)
    assert page.locator('#p2ProfilePreview svg').count() == 1
    report = page.request.post(base + '/report/project/p2', data=page.evaluate('currentResults.params'))
    assert report.ok and 'źródło autora UI' in report.text()
    page.reload(); page.wait_for_function('currentResults?.params.airfoil === "NACA 2415"')
    navigate(page, 'tab-feasibility')
    assert page.locator('#p2AirfoilSelect').input_value() == 'NACA 2415'
    page.locator('#btnModeProjects').click(); page.locator('#pill-p3').click()
    assert page.locator('#airfoil').is_visible()
    assert page.locator('#airfoil').input_value() == 'NACA 2415'
    assert page.locator('#p3_airfoil_svg_container svg').count() == 1
    page.locator('#pill-p2').click()
    assert page.locator('#p2AirfoilSelect').is_visible()
    assert page.locator('#p2DesignDecisions').is_visible()


def test_imported_coordinates_are_not_relabelled_when_switching_profiles(studio):
    page, _, _ = studio; setup_ga(page)
    page.locator('#p2AirfoilFile').set_input_files({'name':'custom.dat','mimeType':'text/plain','buffer':DAT.encode()})
    page.wait_for_function('document.querySelector("#airfoil").value === "CUSTOM UI PROFILE"')
    page.locator('#airfoil_source').fill('Własne rzędne — przypadek kontrolny')
    apply(page, 'currentResults.bipol_projects.p3.airfoil_200mm_info?.kind === "pasted"')
    page.locator('#p2AirfoilSelect').select_option('NACA 0012')
    assert page.locator('#airfoil_coordinates').input_value() == ''
    assert page.locator('#airfoil_source').input_value() == ''
    assert page.locator('#p2ProfilePreview svg').count() == 0
    page.locator('#p2AirfoilSelect').select_option('CUSTOM UI PROFILE')
    assert page.locator('#airfoil_coordinates').input_value() == DAT
    assert 'Własne rzędne' in page.locator('#airfoil_source').input_value()
    apply(page, 'currentResults.params.airfoil === "CUSTOM UI PROFILE"')
    page.reload(); page.wait_for_function('currentResults?.params.airfoil === "CUSTOM UI PROFILE"')
    assert page.evaluate('currentResults.bipol_projects.p3.airfoil_200mm_info.kind') == 'pasted'


def test_advanced_assumptions_reach_calculations_and_survive_reload(studio):
    page, _, _ = studio; setup_ga(page)
    chosen = {'airfield_elevation_m':1000,'airfield_delta_t_k':10,'prop_eff_to':.7,
              'service_ceiling_m':4000,'ceiling_climb_rate_ms':.5,'loiter_time_min':30,
              'cost_rate_production_per_month':3.5,'cost_rate_rdte_per_month':.12,
              'flap_chord_ratio':.3,'aileron_chord_ratio':.2}
    for field, value in chosen.items():
        control = page.locator('#' + field); reveal_details(control); control.fill(str(value))
    page.locator('#matching_design_mode').select_option('minimum_power')
    page.locator('#turbocharged').select_option('true')
    apply(page, 'currentResults.params.matching_design_mode === "minimum_power"')
    result = page.evaluate('currentResults')
    for field,value in chosen.items(): assert result['params'][field] == value, field
    assert result['params']['turbocharged'] is True
    assert result['sizing']['assumptions']['sigma'] < 1
    assert result['bipol_projects']['p2']['cost_analysis']['production']['rate_per_month'] == 3.5
    assert 'Punkt A' in page.locator('#p2DecisionStatus').inner_text()
    page.reload(); page.wait_for_function('currentResults?.params.matching_design_mode === "minimum_power"')
    navigate(page, 'tab-feasibility')
    for field,value in chosen.items(): assert float(page.locator('#'+field).input_value()) == value
    control = page.locator('#airfield_delta_t_k'); reveal_details(control); control.fill('')
    apply(page, '!Object.hasOwn(currentResults.params,"airfield_delta_t_k")')


def test_finder_reaches_optional_fields_and_mobile_p2_has_no_overflow(studio):
    page, _, _ = studio; setup_ga(page)
    navigate(page, 'tab-inputs')
    page.locator('#studioParameterSearch').fill('tempo produkcji')
    page.locator('#studioParameterResults button').first.click()
    page.wait_for_function('document.activeElement.id === "cost_rate_production_per_month"')
    assert page.locator('#cost_rate_production_per_month').is_visible()
    for width in (1440, 768, 390, 320):
        page.set_viewport_size({'width':width,'height':950})
        navigate(page, 'tab-feasibility')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
        for field in page.locator('#p2CostControls input, #p2CostControls select, #p2AirfoilEditor input, #p2AirfoilEditor select').all():
            if not field.is_visible(): continue
            bounds = field.bounding_box()
            assert bounds and bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width, field.get_attribute('id')
    duplicates = page.evaluate('Object.entries([...document.querySelectorAll("[id]")].reduce((m,e)=>(m[e.id]=(m[e.id]||0)+1,m),{})).filter(([,n])=>n>1)')
    assert not duplicates


def test_optional_openvsp_panel_explains_missing_native_engine(studio):
    page, base, _ = studio
    status = page.request.get(base + '/api/openvsp/status').json()
    navigate(page,'tab-openvsp')
    if status['available']:
        assert page.locator('#vspSyncFromBipolBtn').is_enabled()
    else:
        notice = page.locator('#vspAvailability')
        notice.wait_for(state='visible')
        assert 'BIPOL i ML1' in notice.inner_text()
        assert page.locator('#vspSyncFromBipolBtn').is_disabled()
