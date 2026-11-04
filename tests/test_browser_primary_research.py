"""A student can inspect the research evidence and select the new catalogue source."""
import json

import pytest
from playwright.sync_api import expect

from browser_helpers import navigate

pytestmark = pytest.mark.browser


@pytest.mark.parametrize('width', [1440,390])
def test_original_evidence_conditions_and_download_are_reachable_in_catalogue(studio, width):
    page, _, output = studio
    page.set_viewport_size({'width':width,'height':1000})
    navigate(page,'tab-trends')
    page.locator('#trendOpenDatabase').click()
    page.locator('#trendCatalogScope').select_option('all')
    page.locator('#trendSearch').fill('AS 34 Me')
    page.locator('.edit-ac-btn[data-id="pr-as34me-18"]').click()
    evidence=page.locator('#aircraftEvidence')
    expect(evidence).to_be_visible()
    evidence.locator('summary').click()
    expect(evidence).to_contain_text('Zapis w bazie odpowiada')
    expect(evidence).to_contain_text('477')
    expect(evidence).to_contain_text('575')
    assert evidence.locator('tbody tr').count()==6
    assert evidence.locator('a[href^="https://www.alexander-schleicher.de/"]').count()>=1
    with page.expect_download() as pending:
        evidence.locator('a[download]').click()
    pending.value.save_as(output/'evidence.json')
    data=json.loads((output/'evidence.json').read_text(encoding='utf-8'))
    assert len(data['records'])>=85
    assert any(r['id']=='pr-tecnam-p2006ng' for r in data['records'])
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.locator('#trendAircraftModal').screenshot(path=str(output/'research-evidence.png'))
    # Unsaved local changes cannot silently rewrite the source observations.
    page.locator('#ac_me').fill('410')
    page.locator('#saveTrendAircraftBtn').click()
    expect(page.locator('#trendAircraftModal')).not_to_be_visible()
    page.locator('.edit-ac-btn[data-id="pr-as34me-18"]').click()
    evidence.locator('summary').click()
    expect(evidence).to_contain_text('Wpis w bazie został zmieniony')
    expect(evidence).to_contain_text('402')
    expect(evidence).to_contain_text('410')


def test_research_source_can_be_selected_for_real_calculations_and_exported(studio):
    page, _, output=studio
    navigate(page,'tab-trends')
    page.locator('#trendOpenDatabase').click()
    page.locator('#trend_source').select_option('primary_research')
    page.locator('#trendRecalculate').click()
    page.wait_for_function('currentResults?.params.trend_source === "primary_research"',timeout=60000)
    rows=page.evaluate('currentResults.bipol_projects.p1.trend_analysis.similar_aircraft')
    assert len(rows)>=20
    assert all(r['source_id']=='primary_research' for r in rows)
    assert len({r['family_key'] for r in rows})==len(rows)
    with page.expect_download() as pending:
        page.locator('#trendExportJson').click()
    pending.value.save_as(output/'research-analysis.json')
    exported=json.loads((output/'research-analysis.json').read_text(encoding='utf-8'))
    actual=exported['analysis']['trend_analysis']['similar_aircraft']
    assert {r['id'] for r in actual}=={r['id'] for r in rows}


def test_wizard_occupant_limits_follow_seat_count_and_ignore_an_unused_passenger(studio):
    page, _, _=studio
    page.locator('#btnNewProjectWizard').click()
    page.locator('#wiz_aircraft_type').select_option('motoglider')
    page.locator('#wiz_n_pax').fill('1')
    expect(page.locator('#wiz_m_crew_person')).to_have_attribute('min','90')
    page.locator('#wiz_m_pax').fill('1')
    page.locator('#wiz_n_pax').fill('0')
    expect(page.locator('#wiz_m_crew_person')).to_have_attribute('min','110')
    expect(page.locator('#wiz_m_pax')).to_be_disabled()
    page.locator('#wiz_m_crew_person').fill('110')
    page.locator('#wizNextBtn').click()
    expect(page.locator('#wizardPane2')).to_be_visible()
