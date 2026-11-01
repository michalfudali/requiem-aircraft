"""Real browser: P2 card 2.2 — the author's airfoil comparison is ranked, saved in the project and feeds P3 Schrenk."""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process',action='store_true',help='serve the Flask app inside the test, without a server')
parser.add_argument('--screenshot',default='')
args=parser.parse_args()

TEXT='NACA 23012; 0,0062; 0,0071; 1,55; umiarkowane\nNACA 2415; 0,0070; 0,0075; 1,50; łagodne\nNACA 4412; 0,0065; 0,0068; 1,60; łagodne'

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
    assert 'Brak danych porównawczych' in page.inner_text('#p2_airfoil_note')

    page.click('#p2AirfoilControls summary')
    page.fill('#airfoil_comparison','NACA 0012; 0,006')
    page.click('#p2AirfoilControls button')
    page.wait_for_function("document.getElementById('calculationStatus').textContent.includes('Porównanie profili, wiersz 1')",timeout=15000)

    page.fill('#airfoil_comparison',TEXT)
    page.select_option('#airfoil_criterion','cruise')
    page.click('#p2AirfoilControls button')
    page.wait_for_function("currentResults && currentResults.params.airfoil_criterion === 'cruise' && currentResults.bipol_projects.p2.airfoil_selection.comparison_by_author",timeout=30000)
    rows=page.locator('#p2_airfoil_tbody tr')
    assert rows.count()==3
    assert rows.nth(0).inner_text().startswith('NACA 4412') and 'Najlepszy wg kryterium' in rows.nth(0).inner_text()
    cz_proj=page.evaluate('currentResults.bipol_projects.p2.airfoil_selection.cz_proj')
    assert str(round(cz_proj/0.0068,1)) in rows.nth(0).inner_text(),rows.nth(0).inner_text()  # K(Cz_proj) = Cz_proj / Cx(Cz_proj)
    note=page.inner_text('#p2_airfoil_note')
    assert 'Najlepszy: NACA 4412' in note,note
    schrenk=page.text_content('#p3_czmax_schrenk')
    selected=page.evaluate("currentResults.bipol_projects.p2.airfoil_selection.selected_airfoil")
    if selected in ('NACA 23012','NACA 2415','NACA 4412'):
        assert 'porównanie profili P2' in schrenk,schrenk

    page.reload()
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
    assert page.input_value('#airfoil_comparison').startswith('NACA 23012') and page.input_value('#airfoil_criterion')=='cruise'

    if args.screenshot:
        page.evaluate("setPortalMode('projects'); selectSemesterProject('p2')")
        page.click('#p2AirfoilControls summary')
        page.locator('#p2AirfoilControls').locator('xpath=ancestor::div[contains(@class,"subpoint-card")]').screenshot(path=args.screenshot)
    assert not errors,errors
    browser.close()
print('OK: porównanie profili P2 — ranking wg kryterium BIPOL_3, zapis w projekcie, c_z,max do Schrenka')
