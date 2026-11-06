"""The student can inspect independent component masses and their conditional allocation."""
import pytest
from playwright.sync_api import expect

from browser_helpers import navigate, reveal_details

pytestmark=pytest.mark.browser


@pytest.mark.parametrize('width',[1440,390])
def test_class2_comparison_is_visible_in_p3_and_in_the_actual_report(studio,width):
    page,base,output=studio
    page.set_viewport_size({'width':width,'height':1000})
    navigate(page,'tab-p3')
    expect(page.locator('#p3MassEstimateNote')).to_contain_text('Niezależne oszacowanie zespołów')
    reveal_details(page.locator('#p3ComponentComparison'))
    page.locator('#p3ComponentComparison > summary').click()
    rows=page.evaluate('currentResults.bipol_projects.p3.component_mass_estimation.rows')
    expect(page.locator('#p3ComponentEstimateBody tr')).to_have_count(len(rows))
    first=page.locator('#p3ComponentEstimateBody tr').first
    expect(first.locator('td').nth(1)).to_have_text(f"{rows[0]['estimated_mass_kg']:.2f}")
    expect(first.locator('td').nth(2)).to_have_text(f"{rows[0]['assigned_mass_kg']:.2f}")
    assert page.locator('#p3ComponentComparison').evaluate('el => el.scrollWidth <= el.clientWidth+1')
    assert page.locator('#p3ComponentComparison .table-responsive').evaluate('el => el.scrollWidth <= el.clientWidth+1')
    response=page.request.post(base+'/report/project/p3',data=page.evaluate('currentResults.params'))
    assert response.ok
    html=response.text()
    assert 'tab-component-estimates' in html
    assert 'normalization_factor' not in page.locator('#p3MassEstimateNote').inner_text()
    (output/'P3.html').write_text(html,encoding='utf8')
    page.screenshot(path=str(output/'component-comparison.png'),full_page=True)
