"""Topic 7 can specify one propeller through the real wizard and engine panel."""
import math

import pytest
from playwright.sync_api import expect

from browser_helpers import navigate,reveal_details

pytestmark=pytest.mark.browser


def test_topic7_propeller_is_saved_from_wizard_and_used_with_real_engine(studio):
    page,_,output=studio
    page.locator('#btnNewProjectWizard').click()
    page.locator('#wiz_topic').select_option('topic_7')
    page.locator('#wiz_m_crew_person').fill('110')
    page.locator('.wizard-step-tab[data-step="3"]').click()
    page.locator('#wiz_propeller_diameter_m').fill('1.7')
    page.locator('#wiz_propeller_rpm').fill('2100')
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)
    assert page.evaluate('currentResults.geometry.propeller.diameter_m')==1.7
    assert page.evaluate('currentResults.acoustics.propeller_rpm')==2100
    navigate(page,'tab-inputs')
    reveal_details(page.locator('#engineFuelPanel'))
    reveal_details(page.locator('#propeller_rpm'))
    assert page.locator('#propeller_rpm').input_value()=='2100'
    assert page.locator('#propeller_diameter_m').input_value()=='1.7'
    page.locator('#engine_fuel_mode').select_option('catalog')
    page.locator('#engine_model_id').select_option('rotax_912_ul')
    page.locator('#engine_fuel_point').select_option('continuous')
    page.locator('#applyEngineFuel').click()
    page.wait_for_function('currentResults?.engine_selection.model === "Rotax 912 UL"',timeout=60000)
    noise=page.evaluate('currentResults.acoustics')
    expected=math.hypot(math.pi*1.7*2100/60,noise['evaluation_speed_ms'])/noise['evaluation_speed_of_sound_ms']
    assert noise['propeller_tip_mach']==pytest.approx(expected,abs=.0005)
    assert page.evaluate('currentResults.params.sfc')==285
    page.reload();page.wait_for_function('currentResults?.params.engine_model_id === "rotax_912_ul"',timeout=60000)
    page.locator('.wizard-step-tab[data-step="3"]').click()
    assert page.locator('#wiz_propeller_rpm').input_value()=='2100'
    assert page.locator('#wiz_propeller_diameter_m').input_value()=='1.7'
    page.screenshot(path=str(output/'topic7-propeller.png'),full_page=True)
    page.locator('#wiz_propeller_rpm').fill('')
    page.locator('#wiz_propeller_diameter_m').fill('')
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)
    assert page.evaluate('currentResults.geometry.propeller.basis')=='preliminary_sizing'
    assert page.evaluate('currentResults.geometry.propeller.rpm')==2400
    assert not page.evaluate('"propeller_rpm" in currentResults.params')


def test_unpowered_wizard_does_not_require_or_submit_propeller_inputs(studio):
    page,_,_=studio
    page.locator('#wiz_aircraft_type').select_option('glider')
    page.locator('.wizard-step-tab[data-step="3"]').click()
    expect(page.locator('#wiz_propeller_rpm')).to_be_hidden()
    expect(page.locator('#wiz_propeller_diameter_m')).to_be_hidden()
    params=page.evaluate('BipolDesignBasis.snapshot()')
    assert 'propeller_rpm' not in params and 'propeller_diameter_m' not in params
