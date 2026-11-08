"""An actual installed-mass source reaches P3, persists and clears with another engine."""
import pytest
from playwright.sync_api import expect
from browser_helpers import navigate,reveal_details

pytestmark=pytest.mark.browser


@pytest.mark.parametrize('width',[1440,390])
def test_installed_engine_mass_can_be_applied_saved_and_reviewed(studio,width):
    page,base,out=studio
    page.set_viewport_size({'width':width,'height':1000})
    navigate(page,'tab-inputs')
    reveal_details(page.locator('#engineFuelPanel'))
    page.locator('#engine_fuel_mode').select_option('catalog')
    page.locator('#engine_model_id').select_option('rotax_912_ul')
    reveal_details(page.locator('#engine_installed_mass_kg'))
    page.locator('#engine_installed_mass_kg').fill('95.125')
    page.locator('#engine_mass_source').fill('Testowe zestawienie kompletnej instalacji napędu')
    page.locator('#engine_mass_conditions').fill('Silnik z przekładnią, śmigło, wydech, chłodzenie z płynami, mocowanie; bez paliwa i instalacji paliwowej')
    page.locator('#applyEngineFuel').click()
    page.wait_for_function('currentResults?.params.engine_installed_mass_kg===95.125',timeout=60000)
    assert page.evaluate('currentResults.mass.component_allocation.assigned_masses_kg.propulsion')==95.125
    expect(page.locator('#engineFuelStatus')).to_contain_text('55,4 kg')
    expect(page.locator('#engineFuelStatus')).to_contain_text('95,125 kg')
    navigate(page,'tab-p3')
    reveal_details(page.locator('#p3MassEstimateNote'))
    expect(page.locator('#p3MassEstimateNote')).to_contain_text('bez skalowania')
    report=page.request.post(base+'/report/project/p3',data=page.evaluate('currentResults.params'))
    assert report.ok and 'Testowe zestawienie kompletnej instalacji napędu' in report.text()
    (out/'P3-installed-mass.html').write_text(report.text(),encoding='utf8')
    page.reload();page.wait_for_function('currentResults?.params.engine_installed_mass_kg===95.125',timeout=60000)
    navigate(page,'tab-inputs');reveal_details(page.locator('#engineFuelPanel'))
    reveal_details(page.locator('#engine_installed_mass_kg'))
    assert page.locator('#engine_installed_mass_kg').input_value()=='95.125'
    page.locator('#engine_model_id').select_option('rotax_912_uls')
    assert page.locator('#engine_installed_mass_kg').input_value()==''
    assert page.locator('#engine_mass_source').input_value()==''
    page.locator('#applyEngineFuel').click()
    page.wait_for_function('currentResults?.params.engine_model_id==="rotax_912_uls"',timeout=60000)
    assert not page.evaluate('"engine_mass_owner" in currentResults.params')
