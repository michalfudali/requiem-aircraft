"""Choose the aerodynamic starting point from the main workspace, then save real calculations."""
import math
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser


def step(page, number):
    page.locator(f'.wizard-step-tab[data-step="{number}"]').click()


@pytest.mark.parametrize('width', [1680, 390])
def test_start_cards_preserve_both_inputs_and_commit_precise_aircraft_cd0(studio, width):
    page, _, output = studio
    page.set_viewport_size({'width': width, 'height': 1000})
    saved = page.evaluate('JSON.stringify(getActiveProject().params)')
    cd0 = page.locator('[data-wizard-start="input"]')
    wetted = page.locator('[data-wizard-start="raymer"]')
    cd0.focus()
    page.keyboard.press('Space')
    expect(page.locator('#wiz_cx0')).to_be_focused()
    expect(cd0).to_have_attribute('aria-pressed', 'true')
    expect(wetted).to_have_attribute('aria-pressed', 'false')
    page.locator('#wiz_cx0').fill('0.01705')
    page.locator('#wiz_oswald_e').fill('0.83')
    page.locator('#wiz_graph_source').fill('Biegunowa całego samolotu, konfiguracja gładka')
    expect(page.locator('#wizardPolarMetrics')).to_contain_text('0,01705')
    assert page.locator('#wiz_cx0').evaluate('el => el.validity.valid')
    wetted.click()
    expect(page.locator('#wiz_sketch_swet_ratio')).to_be_focused()
    expect(page.locator('#wiz_wetted_example')).to_have_value('sketch')
    page.locator('#wiz_sketch_swet_ratio').fill('4.23')
    expect(page.locator('#wizardPolarPreview')).to_contain_text('4,23')
    assert page.locator('#wiz_sketch_swet_ratio').evaluate('el => el.validity.valid')
    cd0.click()
    expect(page.locator('#wiz_cx0')).to_have_value('0.01705')
    assert page.evaluate('JSON.stringify(getActiveProject().params)') == saved
    page.reload()
    page.wait_for_function('currentResults !== null')
    expect(cd0).to_have_attribute('aria-pressed', 'true')
    saved = page.evaluate('JSON.stringify(getActiveProject().params)')
    wetted.click()
    expect(page.locator('#wiz_sketch_swet_ratio')).to_have_value('4.23')
    cd0.click()
    # The method switch did not write to the calculated project.
    assert page.evaluate('JSON.stringify(getActiveProject().params)') == saved
    page.locator('#wizardEditMissionModel').click()
    expect(page.locator('#wiz_design_iteration_mode')).to_be_focused()
    page.locator('#wiz_design_iteration_mode').select_option('preliminary')
    step(page, 5)
    review = page.locator('[data-review-step="4"]')
    expect(review).to_contain_text('0,01705')
    expect(page.locator('#wizardReviewScope')).to_contain_text('Bilans P1/P2')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(output/'starting-routes-review.png'), full_page=True)
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)
    assert page.evaluate('currentResults.params.cx0') == .01705
    polar = page.evaluate('currentResults.mass.preliminary_polar')
    assert polar['cx0'] == .01705
    assert polar['kmax'] == pytest.approx(.5*math.sqrt(math.pi*polar['aspect_ratio']*.83/.01705))
    assert page.evaluate('currentResults.sizing.terms.cx0') == .01705
    page.reload()
    page.wait_for_function('currentResults?.params.cx0 === .01705')
    expect(cd0).to_have_attribute('aria-pressed', 'true')


def test_review_cards_distinguish_independent_geometry_and_mission_polar(studio):
    page, _, _ = studio
    page.locator('#wiz_wing_input_mode').select_option('span_area')
    page.locator('#wiz_wingspan_m').fill('15')
    page.locator('#wiz_wing_area_m2').fill('12.5')
    page.locator('#wiz_design_iteration_mode').select_option('coupled')
    step(page, 5)
    geometry = page.locator('[data-review-step="1"]')
    expect(geometry).to_contain_text('15,00 m')
    expect(geometry).to_contain_text('12,50 m²')
    expect(geometry).to_contain_text('Zależne wydłużenie Λ = 18,00')
    expect(page.locator('#wizardReviewScope')).to_contain_text('opór jest następnie uściślany z geometrii')
    geometry.click()
    expect(page.locator('#wizardPane1')).to_be_visible()
    assert page.locator('#wiz_aspect_ratio').get_attribute('readonly') is not None
    page.locator('[data-wizard-start="input"]').click()
    expect(page.locator('#wizardModelScopeTitle')).to_contain_text('Domknięcie P2–P4')
    page.locator('#wizardEditMissionModel').click()
    page.locator('#wiz_design_iteration_mode').select_option('preliminary')
    step(page, 4)
    expect(page.locator('#wizardModelScopeTitle')).to_contain_text('Bilans P1/P2')


def test_invalid_drag_input_clears_review_result_and_review_edits_the_right_stage(studio):
    page, _, _ = studio
    page.locator('[data-wizard-start="input"]').click()
    page.locator('#wiz_cx0').fill('0.03456')
    expect(page.locator('#wizardPolarMetrics')).to_contain_text('0,03456')
    page.locator('#wiz_cx0').fill('')
    step(page, 5)
    review = page.locator('[data-review-step="4"]')
    expect(review).to_contain_text(re.compile(r'C_?D0 = —'))
    expect(review).not_to_contain_text('0,03456')
    expect(review).to_contain_text('oczekuje na poprawne dane')
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#wizardPane4')).to_be_visible()
    expect(page.locator('#wizardValidationStatus')).not_to_be_empty()
    step(page, 5)
    review.click()
    expect(page.locator('#wizardPane4')).to_be_visible()


@pytest.mark.parametrize('width', [1440, 768, 320])
def test_start_routes_and_review_remain_readable_in_dark_mode(studio, width):
    page, _, output = studio
    page.set_viewport_size({'width': width, 'height': 950})
    page.locator('#themeToggleBtn').click()
    for card in page.locator('[data-wizard-start]').all():
        bounds = card.bounding_box()
        assert bounds and 0 <= bounds['x'] and bounds['x']+bounds['width'] <= width
    page.locator('[data-wizard-start="raymer"]').click()
    page.locator('#wiz_sketch_swet_ratio').fill('4.35')
    expect(page.locator('#wizardPolarPreview')).to_contain_text('4,35')
    step(page, 5)
    expect(page.locator('[data-review-step="4"]')).to_contain_text('4,35')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    if width <= 720:
        # Document overflow can be hidden globally: inspect the actual value cells too.
        for cell in page.locator('#wizardSummaryTableBody td:nth-child(3)').all():
            bounds = cell.bounding_box()
            assert bounds and 0 <= bounds['x'] and bounds['x']+bounds['width'] <= width
        switch = page.locator('.work-mode-switch').bounding_box()
        assert switch and switch['x']+switch['width'] <= width
    page.screenshot(path=str(output/'start-routes-dark.png'), full_page=True)


@pytest.mark.parametrize('aircraft_type, propulsion', [
    ('piston_ga', 'Napęd śmigłowy'), ('motoglider', 'Napęd śmigłowy'),
    ('glider', 'Bez napędu'), ('turboprop_regional', 'Napęd śmigłowy'),
    ('jet_business', 'Napęd odrzutowy'), ('jet_transport', 'Napęd odrzutowy'),
    ('uav', 'Napęd śmigłowy'),
])
def test_review_matches_propulsion_for_every_aircraft_class(studio, aircraft_type, propulsion):
    page, _, _ = studio
    page.locator('#wiz_aircraft_type').select_option(aircraft_type)
    step(page, 5)
    card = page.locator('[data-review-step="3"]')
    expect(card).to_contain_text(propulsion)
    if aircraft_type.startswith('jet_'):
        expect(card).to_contain_text('Ciąg')
        expect(card).not_to_contain_text('moc')
    if aircraft_type == 'glider':
        expect(card).to_contain_text('bez bilansu paliwa')
    card.click()
    expect(page.locator('#wizardPane3')).to_be_visible()
