"""A user changes the gear layout and reviews the sourced clearance calculation."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from browser_helpers import navigate, reveal_details

pytestmark = pytest.mark.browser
CASE = Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json'


@pytest.mark.parametrize('width', [1440, 390])
@pytest.mark.parametrize('layout,minimum,height', [('tricycle',180,1.03), ('tailwheel',230,1.08)])
def test_wizard_gear_layout_reaches_p3_formulas_saved_project_and_offline_report(studio, width, layout, minimum, height):
    page, base, out = studio
    page.set_viewport_size({'width':width, 'height':1000})
    page.locator('#projectImportFileInput').set_input_files(str(CASE))
    page.wait_for_function('currentResults?.params.airfoil === "FX 61-163"', timeout=60000)
    navigate(page, 'tab-wizard')
    page.locator('.wizard-step-tab[data-step="4"]').click()
    page.locator('#wiz_landing_gear_type').select_option(layout)
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)
    assert page.evaluate('currentResults.geometry.gear.axis_height_m') == pytest.approx(height)
    assert page.evaluate('currentResults.geometry.propeller_ground_clearance.required_m') == minimum/1000
    assert page.evaluate('currentResults.geometry.propeller_ground_clearance.certification_compliant') is None
    navigate(page, 'tab-p3')
    field = page.locator('#p3_chk_prop_clear')
    reveal_details(field)
    expect(field).to_contain_text(f'wymagane {minimum} mm')
    expect(field).to_contain_text('położeniu poziomym')
    expect(field).to_contain_text('najbardziej niekorzystna masa')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    page.screenshot(path=str(out/'nominal-clearance.png'),full_page=True)
    response = page.request.post(base+'/report/project/p3', data=page.evaluate('currentResults.params'))
    assert response.ok
    html = response.text()
    assert 'q-pc_ground' in html and 'Pełna zgodność zabudowy pozostaje nierozstrzygnięta' in html
    context = page.context.browser.new_context(offline=True)
    try:
        report = context.new_page()
        errors = []
        report.on('pageerror', lambda error: errors.append(str(error)))
        report.set_content(html,wait_until='load')
        report.evaluate('document.fonts.ready')
        assert not errors and not report.locator('.katex-error').count()
        expect(report.locator('#q-pc_ground .katex')).to_be_visible()
    finally:
        context.close()
    page.reload()
    page.wait_for_function('layout => currentResults?.params.landing_gear_type===layout',arg=layout,timeout=60000)
    assert page.evaluate('currentResults.geometry.gear.axis_height_m') == pytest.approx(height)
