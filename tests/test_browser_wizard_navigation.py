"""Find real assumptions across stages and follow both aerodynamic starting routes."""
import math
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser


@pytest.mark.parametrize('width', [1440, 390])
def test_search_reveals_other_stage_without_mutating_project_or_draft(studio, width):
    page, _, out = studio
    page.set_viewport_size({'width': width, 'height': 950})
    saved = page.evaluate('JSON.stringify(getActiveProject().params)')
    results = page.evaluate('JSON.stringify(currentResults)')
    drafts = page.evaluate('JSON.stringify(projectStore.read("bipol_wizard_drafts_v1", {}))')
    search = page.locator('#wizardFieldSearch')
    search.fill('rozpietosc')  # Polish accents are optional.
    result = page.locator('[data-search-field="wiz_wingspan_m"]')
    expect(result).to_contain_text('wynik zależny')
    search.press('ArrowDown')
    expect(result).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.locator('#wizardPane1')).to_be_visible()
    expect(page.locator('#wiz_wingspan_m')).to_be_focused()
    assert page.locator('#wiz_wingspan_m').get_attribute('readonly') is not None
    search.fill('zasięg')
    search.press('ArrowUp')
    expect(page.locator('#wizardSearchResults button').last).to_be_focused()
    page.locator('[data-search-field="wiz_range_km"]').click()
    expect(page.locator('#wizardPane2')).to_be_visible()
    expect(page.locator('#wiz_range_km')).to_be_focused()
    assert page.evaluate('JSON.stringify(getActiveProject().params)') == saved
    assert page.evaluate('JSON.stringify(currentResults)') == results
    assert page.evaluate('JSON.stringify(projectStore.read("bipol_wizard_drafts_v1", {}))') == drafts
    search.fill('brak takiego parametru')
    expect(page.locator('#wizardSearchStatus')).to_contain_text('Brak parametrów')
    search.press('Escape')
    expect(search).to_have_value('')
    expect(page.locator('#wizardSearchResults')).to_be_hidden()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(out/'search-workspace.png'), full_page=True)


def test_search_only_offers_fields_in_active_drag_method_and_opens_details(studio):
    page, _, _ = studio
    page.locator('#wizardDragShortcut').click()
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    search = page.locator('#wizardFieldSearch')
    search.fill('CD0')
    expect(page.locator('[data-search-field="wiz_cx0"]')).to_be_visible()
    search.fill('sketch swet ratio')
    expect(page.locator('#wizardSearchStatus')).to_contain_text('Brak parametrów')
    search.fill('projektanta')
    page.locator('[data-search-field="wiz_student_name"]').click()
    expect(page.locator('#wizardPane1')).to_be_visible()
    expect(page.locator('#wiz_student_name')).to_be_visible()
    expect(page.locator('#wiz_student_name')).to_be_focused()
    assert page.locator('.wizard-author').get_attribute('open') is not None


@pytest.mark.parametrize('width', [1680, 390])
def test_prominent_ratio_entry_and_calculation_flow_follow_live_values(studio, width):
    page, _, out = studio
    page.set_viewport_size({'width': width, 'height': 1000})
    page.locator('#wizardDragShortcut').click()
    expect(page.locator('#wizardPane4')).to_be_visible()
    page.locator('[name="wiz_drag_basis"][value="raymer"]').check()
    page.locator('#wiz_wetted_example').select_option('')
    page.locator('#wizEnterOwnRatio').click()
    expect(page.locator('#wiz_sketch_swet_ratio')).to_be_focused()
    page.locator('#wiz_sketch_swet_ratio').fill('4.7')
    expect(page.locator('#wizardDragFlow')).to_contain_text(re.compile(r'S_?wet/S = 4,70'))
    expect(page.locator('#wizardDragShortcutValue')).to_have_text(re.compile(r'S_?wet/S = 4,70'))
    ar = float(page.locator('#wiz_aspect_ratio').input_value())
    expect(page.locator('#wizardDragFlow')).to_contain_text(re.compile(r'Λ_?wet = '+f'{ar/4.7:.2f}'.replace('.', ',')))
    page.locator('[name="wiz_drag_basis"][value="input"]').check()
    page.locator('#wiz_cx0').fill('0.028')
    page.locator('#wiz_oswald_e').fill('0.81')
    kmax = .5*math.sqrt(math.pi*ar*.81/.028)
    expect(page.locator('#wizardDragFlow')).to_contain_text(re.compile(r'C_?D0 = 0,02800'))
    expect(page.locator('#wizardDragFlow')).to_contain_text(re.compile(r'K_?max = '+f'{kmax:.2f}'.replace('.', ',')))
    assert 'Λwet' not in page.locator('#wizardDragFlow').inner_text().replace('_', '')
    page.locator('#wiz_cx0').fill('')
    expect(page.locator('#wizardDragFlow')).to_be_empty()
    page.locator('[name="wiz_drag_basis"][value="raymer"]').check()
    expect(page.locator('#wiz_sketch_swet_ratio')).to_have_value('4.7')
    expect(page.locator('#wizardDragFlow')).to_contain_text(re.compile(r'S_?wet/S = 4,70'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(out/'aerodynamics-workspace.png'), full_page=True)
