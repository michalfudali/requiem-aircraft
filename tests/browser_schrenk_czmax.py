"""Real browser: P3 card 3.4 — required profile c_z,max without data, wing C_z,max from the profile value after recalculation."""
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
    page.evaluate("setPortalMode('projects'); selectSemesterProject('p3')")
    assert page.input_value('#airfoil_cz_max')=='0'
    note=page.inner_text('#p3_czmax_schrenk')
    assert 'profil musi mieć' in note and '≥' in note,note  # c_z,max wyświetla się z indeksem dolnym
    assert 'karta 3.4' in page.inner_text('#p3_czmax_wing')

    page.fill('#airfoil_cz_max','1.6')
    page.click('#p3SchrenkControls button')
    page.wait_for_function("currentResults && currentResults.params.airfoil_cz_max === 1.6",timeout=30000)
    summary=page.evaluate("currentResults.bipol_projects.p3.schrenk_summary")
    assert abs(summary['cz_max_wing_est']-1.6/summary['max_cz1'])<1e-3,summary
    note=page.inner_text('#p3_czmax_schrenk')
    assert 'płata = 1,6 /' in note and 'założenie jest osiągalne' in note,note
    assert page.inner_text('#p3_czmax_wing')==f"{summary['cz_max_wing_est']:.3f}".rstrip('0').replace('.',',')

    if args.screenshot:page.locator('#p3SchrenkControls').locator('xpath=ancestor::div[contains(@class,"subpoint-card")]').screenshot(path=args.screenshot)
    assert not errors,errors
    browser.close()
print('OK: C_z,max płata ze Schrenka — wymagane c_z,max profilu i wynik z wartości katalogowej')
