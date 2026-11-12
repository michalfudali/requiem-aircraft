"""The current topic reaches the wizard and a real native CAD model."""
from pathlib import Path

import pytest
from playwright.sync_api import expect

from browser_helpers import navigate

pytestmark = pytest.mark.browser
CASE = Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json'


@pytest.mark.parametrize('width', [1440, 390])
def test_topic7_from_catalogue_uses_current_profile_and_geometry_without_rewriting_saved_project(studio, width):
    page, _, _ = studio
    page.set_viewport_size({'width':width,'height':1000})
    first = page.evaluate('getActiveProjectId()')
    original = page.evaluate('JSON.stringify(getActiveProject().params)')
    page.locator('#btnNewProjectWizard').click()
    page.locator('#wiz_topic').select_option('topic_7')
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    page.wait_for_function('currentResults?.params.topic_id===7 && currentResults?.params.airfoil==="FX 61-163"', timeout=60000)
    p = page.evaluate('currentResults.params')
    assert (p['aspect_ratio'],p['cruise_speed_kmh'],p['technology']) == (28,115,'composite')
    assert page.evaluate('currentResults.geometry.wing.b') == 21
    assert page.evaluate('currentResults.profile_geometry.tc_ratio') == pytest.approx(.16353)
    assert page.evaluate('getActiveProjectId()') != first
    page.locator('#projectSwitcherSelect').select_option(first)
    page.wait_for_function('id => getActiveProjectId()===id',arg=first)
    assert page.evaluate('JSON.stringify(getActiveProject().params)') == original


@pytest.mark.parametrize('width', [1440, 390])
def test_native_sync_builds_the_actual_selected_profile_instead_of_a_default_aircraft(native_studio, width):
    page, base, out = native_studio
    page.set_viewport_size({'width':width,'height':1000})
    page.locator('#projectImportFileInput').set_input_files(str(CASE))
    page.wait_for_function('currentResults?.params.airfoil==="FX 61-163"', timeout=60000)
    navigate(page,'tab-openvsp')
    with page.expect_response(lambda r: '/api/openvsp/build-from-bipol' in r.url and r.request.method=='POST') as pending:
        page.locator('#vspSyncFromBipolBtn').click()
    response = pending.value
    assert response.ok
    model = response.json()
    assert model['build_meta']['wing_airfoil']['profile_name'] == 'FX 61-163'
    assert model['build_meta']['wing_airfoil']['point_count'] == 98
    assert model['build_meta']['bipol_summary']['b_m'] == 21
    assert model['build_meta']['bipol_summary']['m0_kg'] == pytest.approx(page.evaluate('currentResults.mass.m0'), abs=.0051)
    expect(page.locator('#vspWingAirfoilStatus')).to_contain_text('FX 61-163')
    bounds = page.locator('#vspWingAirfoilStatus').bounding_box()
    assert bounds and bounds['x']>=0 and bounds['x']+bounds['width'] <= width
    for button in page.locator('[data-vsp-subtab]').all():
        button.click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), button.get_attribute('data-vsp-subtab')
    page.locator('[data-vsp-subtab="vsp-sub-model"]').click()
    page.screenshot(path=str(out/'native-fx61163.png'),full_page=True)
