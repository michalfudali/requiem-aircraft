"""A student's measured wetted-area ratio travels through the actual wizard."""
import pytest

from calculations.presets import AIRCRAFT_PRESETS

pytestmark = pytest.mark.browser


def step(page, number):
    page.locator(f'.wizard-step-tab[data-step="{number}"]').click()


def edit_wizard(page):
    page.locator('.quiet-project-menu > summary').click()
    page.locator('#btnEditProjectWizard').click()
    step(page,4)


def finish(page):
    step(page,5)
    with page.expect_response(lambda r:'/api/projects' in r.url and r.request.method in ('POST','PUT')):
        page.locator('#wizFinishBtn').click()
    page.wait_for_function('!document.querySelector("#projectWizardBackdrop").classList.contains("active")')


@pytest.mark.parametrize('width',[1440,390])
def test_custom_ratio_is_calculated_saved_and_reopened_in_wizard(studio, width):
    page, _, _ = studio
    page.evaluate('async p => {loadProjectIntoForm({name:"Wetted ratio test",params:p}); await performCalculation();}',
                  dict(AIRCRAFT_PRESETS['ga_trainer'],design_iteration_mode='preliminary',wetted_example=''))
    page.set_viewport_size({'width':width,'height':1000})
    page.locator('#btnNewProjectWizard').click();step(page,4)
    page.locator('#wiz_wetted_example').select_option('sketch')
    field=page.locator('#wiz_sketch_swet_ratio');field.fill('4.2')
    bounds=field.bounding_box()
    assert bounds and bounds['x']>=0 and bounds['x']+bounds['width']<=width
    step(page,5)
    assert '4.2' in page.locator('#wizardSummaryTableBody').inner_text()
    finish(page)
    assert page.evaluate('currentResults.params.sketch_swet_ratio') == 4.2
    assert page.evaluate('currentResults.params.wetted_example') == 'sketch'
    assert page.evaluate('currentResults.mass.preliminary_polar.swet_ratio') == 4.2
    assert page.locator('#sketch_swet_ratio').input_value() == '4.2'
    page.reload();page.wait_for_function('currentResults?.params.sketch_swet_ratio === 4.2')
    edit_wizard(page)
    assert page.locator('#wiz_sketch_swet_ratio').input_value() == '4.2'
    page.locator('#wiz_sketch_swet_ratio').fill('5.1');finish(page)
    assert page.evaluate('currentResults.mass.preliminary_polar.swet_ratio') == 5.1
    edit_wizard(page)
    page.locator('#wiz_wetted_example').select_option('')
    assert page.locator('#wiz_sketch_swet_ratio').is_disabled()
    finish(page)
    assert page.evaluate('!Object.hasOwn(currentResults.params,"sketch_swet_ratio")')
    assert page.evaluate('currentResults.mass.preliminary_polar.wetted_example') == 'light_single'


def test_invalid_wetted_ratio_cannot_be_committed_and_topic_resets_own_measurement(studio):
    page, _, _ = studio
    edit_wizard(page)
    page.locator('#wiz_wetted_example').select_option('sketch')
    for value in ('0.5','21',''):
        page.locator('#wiz_sketch_swet_ratio').fill(value)
        step(page,5);page.locator('#wizFinishBtn').click()
        assert page.locator('#wizardPane4').is_visible()
        assert page.locator('#wizardValidationStatus').inner_text()
    page.locator('#wiz_sketch_swet_ratio').fill('4.7')
    step(page,1)
    page.locator('#wiz_topic').select_option(index=1)
    step(page,4)
    assert page.locator('#wiz_wetted_example').input_value() == ''
    assert page.locator('#wiz_sketch_swet_ratio').is_disabled()
