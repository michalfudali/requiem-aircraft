"""P1 reference cohort, exports, persistence and mobile integration checks."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, edit_inputs, reveal_details

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:5000')
parser.add_argument('--browser-path', default=None)
parser.add_argument('--output', default='work/trends-qa')
args = parser.parse_args()
out = Path(args.output); out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':1600,'height':1100}, accept_downloads=True)
    context.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    page = context.new_page(); errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.base_url)
    page.wait_for_function('currentResults !== null')
    navigate(page, 'tab-trends')
    page.wait_for_function("document.querySelectorAll('#trendAircraftRows tr').length > 1")
    assert str(page.request.get(args.base_url+'/api/aircraft').json()['total']) in page.locator('#trendSummary').inner_text()
    assert page.locator('#trendMassChart svg').count() == 1
    assert 'brak' not in page.locator('#trendStatus').inner_text().lower() or 'braki danych' in page.locator('#trendStatus').inner_text()

    # Controls use the API cohort, not only a filter on the visible table.
    page.locator('#trendSelectionPanel-tab').click()
    page.locator('#trend_source').select_option('cado')
    page.locator('#trend_nearest_count').select_option('20')
    page.locator('#trend_engine_count').select_option('1')
    page.locator('#trendRecalculate').click()
    page.wait_for_function("currentResults.params.trend_source === 'cado' && currentResults.params.trend_engine_count === 1")
    assert page.evaluate("currentResults.bipol_projects.p1.trend_analysis.similar_aircraft.every(r => r.n_engines === 1 && r.source_id === 'cado')")
    assert page.evaluate('currentResults.bipol_projects.p1.trend_analysis.selected_n') == 20
    print('SOURCE, COUNT AND ENGINE FILTERS: OK')

    page.locator('#trendSearch').fill('PA-')
    assert page.locator('#trendAircraftRows tr').count() >= 2
    page.locator('#trendClearSelection').click()
    checkboxes = page.locator('#trendAircraftRows input[type=checkbox]')
    chosen = [checkboxes.nth(i).get_attribute('data-aircraft-id') for i in range(2)]
    for i in range(2): checkboxes.nth(i).check()
    page.locator('#trendApplySelection').click()
    page.wait_for_function('currentResults.bipol_projects.p1.trend_analysis.selected_n === 2')
    assert set(page.evaluate('currentResults.params.trend_aircraft_ids')) == set(chosen)
    reveal_details(page.locator('#trendWarnings'))
    assert 'co najmniej 20' in page.locator('#trendWarnings').inner_text()
    assert page.evaluate('currentResults.bipol_projects.p1.trend_analysis.mass_fit') is None
    page.reload(); page.wait_for_function('currentResults?.bipol_projects.p1.trend_analysis.selected_n === 2')
    navigate(page, 'tab-trends')
    assert page.locator('#trend_nearest_count').input_value() == '0'
    assert set(page.evaluate('getActiveProject().params.trend_aircraft_ids')) == set(chosen)
    print('CUSTOM COHORT AND RELOAD PERSISTENCE: OK')

    with page.expect_download() as download:
        page.locator('#trendExportCsv').click()
    download.value.save_as(out/'proba.csv')
    csv = (out/'proba.csv').read_bytes()
    assert csv.startswith(b'\xef\xbb\xbf') and b'ODbL-1.0' in csv and b'10.57745/LLRJO0' in csv
    with page.expect_download() as download:
        page.locator('#trendExportJson').click()
    download.value.save_as(out/'analiza.json')
    analysis = json.loads((out/'analiza.json').read_text(encoding='utf-8'))
    assert analysis['analysis']['trend_analysis']['selected_n'] == 2
    params = page.evaluate('currentResults.params')
    report = page.request.post(args.base_url+'/report?sections=p1',data=params)
    assert report.ok
    html = report.text()
    assert 'data-trend-report' in html and '<script src=' not in html
    offline = browser.new_context(offline=True)
    offline_page = offline.new_page(); offline_page.on('pageerror', lambda error: errors.append('REPORT: '+str(error)))
    offline_page.set_content(html, wait_until='load')
    assert offline_page.locator('[data-trend-report] svg').count() >= 1
    offline.close()
    print('CSV, JSON AND OFFLINE P1 REPORT: OK')

    page.locator('#trendSelectionPanel-tab').click()
    page.locator('#trendAutomatic').click()
    page.wait_for_function('currentResults.params.trend_aircraft_ids === undefined')
    reveal_details(page.locator('#trend_year_min'))
    page.locator('#trend_year_min').fill('2005');page.locator('#trend_year_max').fill('1990')
    page.locator('#trendRecalculate').click()
    page.wait_for_function("document.getElementById('calculationStatus').classList.contains('is-error')")
    assert page.locator('#openReportBtn').get_attribute('data-results-stale') == 'true'
    page.locator('#trend_year_min').fill('0');page.locator('#trend_year_max').fill('0')
    page.locator('#trendRecalculate').click()
    page.wait_for_function("document.getElementById('openReportBtn').dataset.resultsStale === 'false'")

    # Analytical assumptions really feed the mass solver and persist in the project.
    page.locator('#trendMethodPanel-tab').click()
    reveal_details(page.locator('#trendMissionApply'))
    mass_before = page.evaluate('currentResults.mass.m0')
    page.locator('#fuel_reserve_factor').fill('1.10')
    assert page.locator('#mission_phase_model').is_disabled()
    assert page.locator('#mission_phase_model').input_value() == 'galinski'
    assert page.locator('#mission_ld_factor').input_value() == '0.94'
    assert not page.locator('#mission_ld_factor').is_editable()
    page.locator('#trendMissionApply').click()
    page.wait_for_function("currentResults.mass.mission_assumptions.reserve_factor === 1.1 && currentResults.params.mission_phase_model === 'galinski'")
    assert page.evaluate('currentResults.mass.m0') > mass_before
    assert page.evaluate('getActiveProject().params.fuel_reserve_factor') == 1.1
    print('VALIDATION AND MISSION MODEL INTEGRATION: OK')

    # Dated, jet-only data; no disguised power or invented TAS from Mach.
    navigate(page, 'tab-p3')
    edit_inputs(page,'aircraft_type').select_option('jet_transport')
    page.wait_for_function("currentResults.params.aircraft_type === 'jet_transport'")
    navigate(page, 'tab-trends')
    page.locator('#trendSelectionPanel-tab').click()
    page.locator('#trend_source').select_option('fast');page.locator('#trend_engine_count').select_option('0')
    page.locator('#trend_nearest_count').select_option('100');page.locator('#trendRecalculate').click()
    page.wait_for_function("currentResults.params.trend_source === 'fast' && currentResults.params.trend_engine_count === 0")
    page.locator('#trendResultsPanel-tab').click()
    page.locator('#trendChartView').select_option('1')
    assert page.locator('#trendTimeChart svg').count() == 1
    assert page.evaluate('currentResults.bipol_projects.p1.trend_analysis.time_trends[0].forecast_year === currentResults.bipol_projects.p1.trend_analysis.reference_year + 5 || currentResults.bipol_projects.p1.trend_analysis.time_trends[0].forecast_year === currentResults.bipol_projects.p1.trend_analysis.time_trends[0].fit.x_max + 5')
    page.screenshot(path=out/'desktop-viewport.png', animations='disabled')
    for width in [1280,768,390,320]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), width
        page.screenshot(path=out/f'trends-{width}.png',animations='disabled')
    assert not errors, errors
    print('DATED JET TRENDS, +5 YEARS, WIDTHS 320–1600 AND JAVASCRIPT: OK')
    browser.close()
