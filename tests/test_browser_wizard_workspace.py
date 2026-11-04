"""The primary design tab: actual calculations, independent drafts and accessible navigation."""
import math

import pytest
from playwright.sync_api import expect

from browser_helpers import navigate

pytestmark = pytest.mark.browser


def step(page, number):
    page.locator(f'.wizard-step-tab[data-step="{number}"]').click()


def finish(page):
    step(page, 5)
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)


@pytest.mark.parametrize('width', [1440, 390])
def test_cd0_route_is_previewed_calculated_saved_and_reopened(studio, width):
    page, _, out = studio
    page.set_viewport_size({'width':width, 'height':1000})
    expect(page.locator('#tab-wizard')).to_be_visible()
    assert page.locator('#projectWizardBackdrop').get_attribute('role') != 'dialog'
    assert page.evaluate('getComputedStyle(document.body).overflow') != 'hidden'
    step(page, 4)
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.032')
    page.locator('#wiz_oswald_e').fill('0.82')
    page.locator('#wiz_graph_source').fill('Biegunowa całego samolotu, konfiguracja gładka')
    expect(page.locator('#wizardPolarPreview')).to_contain_text('0,03200')
    assert page.locator('#wiz_sketch_swet_ratio').is_disabled()
    assert page.locator('#wiz_wetted_example').is_disabled()
    bounds = page.locator('#wiz_cx0').bounding_box()
    assert bounds and bounds['x'] >= 0 and bounds['x']+bounds['width'] <= width
    assert page.locator('.wizard-body').evaluate('el => el.scrollWidth <= el.clientWidth + 1')
    page.screenshot(path=str(out/'cd0-workspace.png'), full_page=True)
    finish(page)
    polar = page.evaluate('currentResults.mass.preliminary_polar')
    assert polar['mode'] == 'input' and polar['cx0'] == .032
    assert polar['kmax'] == pytest.approx(.5*math.sqrt(math.pi*polar['aspect_ratio']*.82/.032))
    assert page.evaluate('currentResults.sizing.terms.cx0') == .032
    page.reload(); page.wait_for_function('currentResults?.params.cx0 === .032')
    step(page, 4)
    expect(page.locator('[name="wiz_drag_basis"][value="input"]')).to_be_checked()
    assert page.locator('#wiz_cx0').input_value() == '0.032'
    assert page.locator('#wiz_graph_source').input_value().startswith('Biegunowa całego')
    # Switching basis removes the direct-input flag and uses the selected sketch ratio.
    page.locator('[name="wiz_drag_basis"][value="raymer"]').check()
    page.locator('#wiz_wetted_example').select_option('sketch')
    page.locator('#wiz_sketch_swet_ratio').fill('4.6')
    expect(page.locator('#wizardPolarPreview')).to_contain_text('4,60')
    assert page.locator('#wiz_cx0').is_disabled()
    finish(page)
    assert page.evaluate('currentResults.params.preliminary_polar_mode') == 'raymer'
    assert page.evaluate('currentResults.mass.preliminary_polar.swet_ratio') == 4.6
    assert page.evaluate('!currentResults.params.preliminary_polar_includes_configuration')


def test_unapplied_draft_survives_navigation_and_reload_without_changing_results(studio):
    page, _, _ = studio
    saved_name = page.evaluate('getActiveProject().name')
    original_cd0 = page.evaluate('currentResults.params.cx0')
    step(page, 4)
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.041')
    page.locator('#wiz_graph_source').fill('Szkic do sprawdzenia')
    step(page, 1); page.locator('#wiz_name').fill('Niezastosowany szkic')
    step(page, 4)
    navigate(page, 'tab-overview')
    assert page.evaluate('getActiveProject().name') == saved_name
    assert page.evaluate('currentResults.params.cx0') == original_cd0
    navigate(page, 'tab-wizard')
    assert page.locator('#wiz_cx0').input_value() == '0.041'
    page.reload(); page.wait_for_function('currentResults !== null')
    expect(page.locator('#wizardPane4')).to_be_visible()
    assert page.locator('#wiz_name').input_value() == 'Niezastosowany szkic'
    assert page.locator('#wiz_cx0').input_value() == '0.041'
    assert page.evaluate('getActiveProject().name') == saved_name


def test_inactive_fields_do_not_block_direct_input_and_invalid_active_value_is_reported(studio):
    page, _, _ = studio
    step(page, 4)
    page.locator('#wiz_wetted_example').select_option('sketch')
    page.locator('#wiz_sketch_swet_ratio').fill('21')
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    for value in ('', '0', '0.31'):
        page.locator('#wiz_cx0').fill(value)
        step(page, 5); page.locator('#wizFinishBtn').click()
        expect(page.locator('#wizardPane4')).to_be_visible()
        expect(page.locator('#wizardValidationStatus')).not_to_be_empty()
    page.locator('#wiz_cx0').fill('0.029')
    page.keyboard.press('Control+Enter')
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)
    assert page.evaluate('currentResults.params.cx0') == .029


def test_manual_kmax_route_and_step_keyboard_navigation(studio):
    page, _, _ = studio
    tab = page.locator('.wizard-step-tab[data-step="4"]')
    tab.focus(); page.keyboard.press('Enter')
    expect(page.locator('#wizardPane4')).to_be_visible()
    assert tab.get_attribute('aria-current') == 'step'
    page.locator('#wiz_raymer_reading').select_option('reading')
    page.locator('#wiz_raymer_kmax').fill('18')
    expect(page.locator('#wizardPolarPreview')).to_contain_text('18,00')
    finish(page)
    assert page.evaluate('currentResults.params.preliminary_polar_mode') == 'reading'
    assert page.evaluate('currentResults.mass.preliminary_polar.kmax') == 18


def test_new_project_commit_does_not_leave_a_create_draft_on_the_previous_project(studio):
    page, _, _ = studio
    first = page.evaluate('getActiveProjectId()')
    first_cd0 = page.evaluate('currentResults.params.cx0')
    page.locator('#btnNewProjectWizard').click()
    page.locator('#wiz_name').fill('Drugi samolot')
    step(page, 4)
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.037')
    finish(page)
    second = page.evaluate('getActiveProjectId()')
    assert second != first
    page.locator('#projectSwitcherSelect').select_option(first)
    page.wait_for_function('currentResults?.params.cx0 === '+str(first_cd0))
    navigate(page, 'tab-wizard')
    assert page.evaluate('wizardProjectMode') == 'edit'
    assert page.locator('#wiz_name').input_value() != 'Drugi samolot'
    assert not page.evaluate('Boolean(projectStore.read("bipol_wizard_drafts_v1", {})[getActiveProjectId()])')
    page.locator('#projectSwitcherSelect').select_option(second)
    page.wait_for_function('currentResults?.params.cx0 === .037')
    expect(page.locator('[name="wiz_drag_basis"][value="input"]')).to_be_checked()
    assert page.locator('#wiz_name').input_value() == 'Drugi samolot'


def test_dark_workspace_and_explanations_have_no_horizontal_overflow(studio):
    page, _, output = studio
    page.locator('#themeToggleBtn').click()
    step(page, 4)
    for width in (1440, 768, 390, 320):
        page.set_viewport_size({'width':width, 'height':950})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
    page.locator('#wizExplanationToggle').click()
    expect(page.locator('#wizExplanationToggle')).to_have_attribute('aria-pressed', 'true')
    assert page.locator('#tab-wizard .param-didactic-hint:visible').count() > 0
    page.locator('#wizExplanationToggle').click()
    assert page.locator('#tab-wizard .param-didactic-hint:visible').count() == 0
    page.screenshot(path=str(output/'wizard-dark-mobile.png'), full_page=True)


def test_previous_wizard_response_cannot_save_into_a_new_session(studio):
    page, base, _ = studio
    before = page.evaluate('getProjectsList().map(p => ({id:p.id, name:p.name}))')
    pending = []
    page.route('**/api/calculate', lambda route: pending.append(route))
    step(page, 5); page.locator('#wizFinishBtn').click()
    page.wait_for_function('document.querySelector("#wizFinishBtn").disabled')
    page.locator('#btnNewProjectWizard').click()
    assert pending
    old_request = pending[0]
    response = page.request.post(base+'/api/calculate', data=old_request.request.post_data_json)
    assert response.ok
    old_request.fulfill(response=response)
    page.wait_for_function('!document.querySelector("#wizFinishBtn").disabled')
    assert page.evaluate('getProjectsList().map(p => ({id:p.id, name:p.name}))') == before
    expect(page.locator('#tab-wizard')).to_be_visible()
    assert page.evaluate('wizardProjectMode') == 'create'
