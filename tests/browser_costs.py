"""Real browser: P2 cost assumptions (N_P, N_am, QC factor) go into the project, the result and back after reload."""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process',action='store_true',help='serve the Flask app inside the test, without a server')
parser.add_argument('--screenshot',default='')
args=parser.parse_args()

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1000})
    if args.in_process:serve_in_process(page,args.base_url)
    page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(args.base_url)
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
    page.evaluate("setPortalMode('projects'); selectSemesterProject('p2')")
    assert page.input_value('#cost_n_production')=='250' and page.input_value('#cost_qc_factor')=='0.13'
    assert page.inner_text('#p2_series_count')=='250'

    # N_am > N_P: czytelny błąd zamiast cichego przeliczenia.
    page.fill('#cost_n_production','100')
    page.click('#p2CostControls button')
    page.wait_for_function("document.getElementById('calculationStatus').textContent.includes('amortyzuj')",timeout=15000)

    page.fill('#cost_n_amortization','80')
    page.select_option('#cost_qc_factor','0.076')
    page.fill('#cost_profit_pct','5')
    page.click('#p2CostControls button')
    page.wait_for_function("currentResults && currentResults.params.cost_n_amortization === 80",timeout=30000)
    costs=page.evaluate("currentResults.bipol_projects.p2.cost_analysis")
    assert (costs['series_count'],costs['amortization_count'],costs['qc_factor'],costs['profit_pct'])==(100,80,0.076,5),costs
    assert page.inner_text('#p2_series_count')=='100' and page.inner_text('#p2_amortization_count')=='80'
    assert page.inner_text('#p2_qc_factor')=='0,076' and page.inner_text('#p2_profit_pct')=='5'
    assert 'USD' in page.inner_text('#p2_rdte_total') and 'USD' in page.inner_text('#p2_production_total')

    page.reload()
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
    assert page.input_value('#cost_n_production')=='100' and page.input_value('#cost_n_amortization')=='80'
    assert page.input_value('#cost_qc_factor')=='0.076'

    if args.screenshot:
        page.evaluate("setPortalMode('projects'); selectSemesterProject('p2')")
        page.locator('#p2CostControls').locator('xpath=ancestor::div[contains(@class,"subpoint-card")]').screenshot(path=args.screenshot)
    assert not errors,errors
    browser.close()
print('OK: założenia kosztów P2 — N_P, N_am, k_QC i zysk w projekcie, wyniku i po przeładowaniu')
