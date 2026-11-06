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


@pytest.mark.parametrize('width', [1440, 390])
def test_stage_navigation_reveals_heading_and_moves_keyboard_focus(studio, width):
    page, _, _ = studio
    page.set_viewport_size({'width':width, 'height':850})

    def assert_heading_visible(number):
        heading = page.locator(f'#wizardPane{number} h4')
        expect(heading).to_be_focused()
        heading_box = heading.bounding_box()
        navbar_box = page.locator('.bipol-navbar').bounding_box()
        assert heading_box and navbar_box
        # A stage can be shorter than the viewport and stop at the document end.
        assert navbar_box['y'] + navbar_box['height'] <= heading_box['y'] < 400

    for number in range(2, 6):
        page.locator('#wizNextBtn').click()
        assert_heading_visible(number)
    page.locator('#wizBackBtn').click()
    assert_heading_visible(4)
    stage = page.locator('.wizard-step-tab[data-step="2"]')
    assert stage.evaluate('el => el.tagName') == 'BUTTON'
    stage.focus(); page.keyboard.press('Space')
    assert_heading_visible(2)


@pytest.mark.parametrize('width', [1680, 390])
def test_live_polar_chart_matches_equations_and_probe_does_not_edit_project(studio, width):
    page, _, output = studio
    page.set_viewport_size({'width':width, 'height':1000})
    step(page, 4)
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.032')
    page.locator('#wiz_oswald_e').fill('0.82')
    expect(page.locator('#wizardPolarMetrics')).to_contain_text('0,03200')
    expect(page.locator('#wizardPolarChart svg')).to_be_visible()
    ar = float(page.locator('#wiz_aspect_ratio').input_value())
    k = 1/(math.pi*ar*.82)
    before = page.evaluate('JSON.stringify(projectStore.read("bipol_wizard_drafts_v1", {}))')
    saved_cd0 = page.evaluate('currentResults.params.cx0')
    page.locator('#wizPolarCl').fill('1')
    expect(page.locator('#wizardPolarPoint')).to_contain_text(f'{.032+k:.5f}'.replace('.', ','))
    expect(page.locator('#wizardPolarPoint')).to_contain_text(f'{1/(.032+k):.2f}'.replace('.', ','))
    assert page.evaluate('JSON.stringify(projectStore.read("bipol_wizard_drafts_v1", {}))') == before
    assert page.evaluate('currentResults.params.cx0') == saved_cd0
    page.locator('.wizard-polar-equations summary').click()
    expect(page.locator('#wizardPolarEquations .katex').first).to_be_visible()
    # The plotted optimum must be the analytic maximum of C_L / C_D.
    svg = page.locator('#wizardPolarChart svg')
    clmax = float(page.locator('#wizPolarCl').get_attribute('max'))
    optimal_y = float(svg.locator('.polar-optimum').get_attribute('cy'))
    assert (190-optimal_y)/162*clmax == pytest.approx(math.sqrt(.032/k))
    page.screenshot(path=str(output/'wizard-engineering-preview.png'), full_page=True)
    # Moving between responsive layouts keeps one plot and its controls.
    page.set_viewport_size({'width':390 if width > 1000 else 1680, 'height':1000})
    assert page.locator('#wizardPolarChart').count() == 1
    expect(page.locator('#wizardPolarChart svg')).to_be_visible()


def test_review_links_focus_invalid_field_and_preview_clears_stale_results(studio):
    page, _, _ = studio
    step(page, 4)
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.034')
    expect(page.locator('#wizardPolarMetrics')).to_contain_text('0,03400')
    page.locator('#wiz_cx0').fill('')
    expect(page.locator('#wizardPolarChart')).to_be_empty()
    expect(page.locator('#wizardPolarMetrics')).to_be_empty()
    expect(page.locator('#wizardPolarProbe')).to_be_hidden()
    expect(page.locator('#wizardReadinessProgress')).to_have_attribute('value', '3')
    page.locator('#wizReviewBtn').click()
    expect(page.locator('#wizardPane5')).to_be_visible()
    page.locator('[data-invalid-field="wiz_cx0"]').click()
    expect(page.locator('#wizardPane4')).to_be_visible()
    expect(page.locator('#wiz_cx0')).to_be_focused()
    page.locator('#wiz_cx0').fill('0.03')
    expect(page.locator('#wizardReadinessProgress')).to_have_attribute('value', '4')
    expect(page.locator('#wizardPolarMetrics')).to_contain_text('0,03000')


def test_preview_ignores_late_response_from_previous_drag_basis(studio):
    page, base, _ = studio
    step(page, 4)
    pending = []
    page.route('**/api/preliminary-polar', lambda route: pending.append(route))
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.031')
    page.wait_for_timeout(400)
    assert pending
    previous = pending[-1]
    page.locator('[name="wiz_drag_basis"][value="raymer"]').check()
    page.locator('#wiz_wetted_example').select_option('sketch')
    page.locator('#wiz_sketch_swet_ratio').fill('4.6')
    page.wait_for_timeout(400)
    current = pending[-1]
    assert current != previous
    current.fulfill(response=page.request.post(base+'/api/preliminary-polar', data=current.request.post_data_json))
    expect(page.locator('#wizardPolarBasis')).to_contain_text('wykres Raymera')
    expected = page.locator('#wizardPolarMetrics').inner_text()
    # An aborted request can still finish at the server. It must not replace the new basis.
    previous.fulfill(response=page.request.post(base+'/api/preliminary-polar', data=previous.request.post_data_json))
    expect(page.locator('#wizardPolarMetrics')).to_have_text(expected, use_inner_text=True)
