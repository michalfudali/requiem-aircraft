"""The chosen climb model is editable in the primary wizard and survives a real calculation."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect
from browser_helpers import navigate, reveal_details

pytestmark = pytest.mark.browser
CASE = Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json'


def topic7(page):
    params = json.loads(CASE.read_text(encoding='utf8'))
    page.locator('#projectImportFileInput').set_input_files(dict(name='topic7.json', mimeType='application/json',
                                                               buffer=json.dumps(params).encode('utf8')))
    page.wait_for_function('currentResults?.params.airfoil === "FX 61-163"', timeout=60000)
    navigate(page, 'tab-wizard')
    page.locator('.wizard-step-tab[data-step="2"]').click()


def finish(page):
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    page.wait_for_function('document.querySelector("#tab-overview").classList.contains("active") || document.querySelector("#wizardValidationStatus").textContent.trim()',timeout=60000)
    assert not page.locator('#wizardValidationStatus').inner_text().strip()
    expect(page.locator('#tab-overview')).to_be_visible(timeout=60000)


@pytest.mark.parametrize('width', [1440, 390])
def test_energy_profile_is_calculated_saved_and_rendered_in_the_offline_report(studio, chromium, width):
    page, base, out = studio
    page.set_viewport_size({'width':width, 'height':1000})
    topic7(page)
    expect(page.locator('#wiz_climb_fraction_mode')).to_have_value('energy')
    page.locator('#wiz_mission_climb_rate_ms').fill('2.5')
    page.locator('#wiz_climb_start_altitude_m').fill('100')
    page.locator('#wiz_climb_start_speed_kmh').fill('100')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(out/'climb-wizard.png'))
    finish(page)
    result = page.evaluate('currentResults')
    cl = result['mass']['mission_assumptions']['climb']
    assert cl['roc_ms'] == 2.5 and cl['altitude_start_m'] == 100
    assert cl['duration_s'] == 760 and cl['fuel_kg'] > 0
    assert cl['assessment']['passed']
    response = page.request.post(base+'/report/project/p2', data=result['params'])
    assert response.ok
    with chromium.new_context(offline=True, viewport={'width':width, 'height':1000}) as context:
        report = context.new_page()
        errors=[]
        report.on('pageerror', lambda error: errors.append(str(error)))
        report.set_content(response.text(), wait_until='load')
        expect(report.locator('#tab-mission-climb')).to_be_visible()
        assert report.locator('#tab-mission-climb tbody tr').count() == len(cl['nodes'])
        assert report.locator('.katex').count() > 100
        assert not report.locator('.katex-error').count() and not errors
        assert 'Zapas na tę fazę zawiera rezerwa paliwa' not in report.inner_text('body')
        report.screenshot(path=str(out/'climb-report.png'))
    page.reload()
    page.wait_for_function('currentResults?.params.mission_climb_rate_ms===2.5', timeout=60000)
    page.locator('.wizard-step-tab[data-step="2"]').click()
    expect(page.locator('#wiz_mission_climb_rate_ms')).to_have_value('2.5')
    expect(page.locator('#wiz_climb_start_speed_kmh')).to_have_value('100')


def test_out_of_chart_corke_is_rejected_and_documented_own_reading_is_preserved(studio):
    page, _, _ = studio
    topic7(page)
    old_mass = page.evaluate('currentResults.mass.m0')
    page.locator('#wiz_mission_climb_rate_ms').fill('0')
    page.locator('#wiz_climb_fraction_mode').select_option('corke')
    assert page.locator('#wiz_mission_climb_rate_ms').is_disabled()
    page.locator('.wizard-step-tab[data-step="5"]').click()
    page.locator('#wizFinishBtn').click()
    expect(page.locator('#wizardValidationStatus')).to_contain_text('zakresem wykresu Corke', timeout=60000)
    assert page.evaluate('currentResults.mass.m0') == old_mass
    page.locator('.wizard-step-tab[data-step="2"]').click()
    page.locator('#wiz_climb_fraction_mode').select_option('reading')
    page.locator('#wiz_corke_start_ordinate').fill('0.999')
    page.locator('#wiz_corke_end_ordinate').fill('0.996')
    page.locator('#wiz_climb_source').fill('Udokumentowany własny odczyt: wykres, punkty początku i końca profilu.')
    finish(page)
    assert page.evaluate('currentResults.mass.fuel_fractions_detail.climb') == pytest.approx(.996/.999)
    assert page.evaluate('currentResults.params.climb_source').startswith('Udokumentowany własny')
    assert page.evaluate('currentResults.bipol1_review.checks.find(c=>c.key==="corke").passed')


def test_glider_does_not_require_or_claim_an_engine_climb_profile(studio):
    page, _, _ = studio
    page.locator('.wizard-step-tab[data-step="2"]').click()
    page.locator('#wiz_mission_climb_rate_ms').fill('0')
    page.locator('.wizard-step-tab[data-step="3"]').click()
    page.locator('#wiz_engine_type').select_option('none')
    page.locator('.wizard-step-tab[data-step="1"]').click()
    page.locator('#wiz_m_crew_person').fill('110')
    page.locator('.wizard-step-tab[data-step="2"]').click()
    expect(page.locator('.wizard-climb-profile')).to_be_hidden()
    page.locator('#wiz_v_stall_kmh').fill('72')
    assert page.locator('#wiz_mission_climb_rate_ms').is_disabled()
    finish(page)
    assert page.evaluate('currentResults.params.engine_type') == 'none'
    assert page.evaluate('currentResults.mass.mission_assumptions.climb') is None


def test_advanced_panel_ignores_invalid_energy_input_when_own_readings_are_selected(studio):
    page, _, _ = studio
    topic7(page)
    navigate(page, 'tab-trends')
    field = page.locator('#mission_climb_rate_ms')
    reveal_details(field)
    field.fill('0')
    page.locator('#climb_fraction_mode').select_option('reading')
    page.locator('#corke_start_ordinate').fill('0.999')
    page.locator('#corke_end_ordinate').fill('0.996')
    page.locator('#climb_source').fill('Źródło własnego odczytu w panelu założeń.')
    page.locator('#bipol1Calculate').click()
    page.wait_for_function('currentResults?.params.climb_fraction_mode==="reading"',timeout=60000)
    assert page.evaluate('currentResults.mass.fuel_fractions_detail.climb') == pytest.approx(.996/.999)


def test_official_jet_profile_inherits_its_requirement_and_keeps_an_explicit_edit(studio):
    page, _, _ = studio
    topic_id = page.evaluate('topicsData.find(t=>t.num===61).id')
    page.locator('#wiz_topic').select_option(topic_id)
    page.locator('.wizard-step-tab[data-step="2"]').click()
    expect(page.locator('#wiz_mission_climb_rate_ms')).to_have_value('12')
    page.locator('#wiz_mission_climb_rate_ms').fill('7.5')
    page.reload()
    page.wait_for_function('currentResults !== null')
    expect(page.locator('#wiz_mission_climb_rate_ms')).to_have_value('7.5')


def test_minimum_profile_rate_survives_wizard_save_reload_and_panel_sync(studio):
    page, _, _ = studio
    page.locator('.wizard-step-tab[data-step="2"]').click()
    page.locator('#wiz_mission_climb_rate_ms').fill('0.05')
    # Check the field's valid minimum without commanding an eleven-hour climb:
    # a profile already at final altitude/TAS has zero duration.
    page.locator('#wiz_climb_start_altitude_m').fill(page.locator('#wiz_cruise_altitude_m').input_value())
    page.locator('#wiz_climb_start_speed_kmh').fill(page.locator('#wiz_cruise_speed_kmh').input_value())
    finish(page)
    assert page.evaluate('currentResults.params.mission_climb_rate_ms') == .05
    assert page.evaluate('currentResults.mass.mission_assumptions.climb.duration_s') == 0
    page.reload()
    page.wait_for_function('currentResults?.params.mission_climb_rate_ms === .05', timeout=60000)
    page.locator('.wizard-step-tab[data-step="2"]').click()
    expect(page.locator('#wiz_mission_climb_rate_ms')).to_have_value('0.05')
    navigate(page, 'tab-trends')
    reveal_details(page.locator('#mission_climb_rate_ms'))
    expect(page.locator('#mission_climb_rate_ms')).to_have_value('0.05')
