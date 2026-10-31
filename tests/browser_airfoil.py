"""Real browser: P3 airfoil card — NACA from formula, refusal of profiles without formula, pasted ordinates, 1:1 SVG."""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process',action='store_true',help='serve the Flask app inside the test, without a server')
parser.add_argument('--screenshot',default='')
args=parser.parse_args()

SELIG='FX TEST\n'+'\n'.join(f'{x} {y}' for x,y in ((1,0.001),(0.5,0.06),(0.3,0.075),(0.1,0.05),(0.025,0.025),(0,0),(0.025,-0.015),(0.1,-0.025),(0.3,-0.03),(0.5,-0.02),(1,0)))

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
    page.wait_for_function("document.getElementById('airfoil').placeholder === 'NACA 23012'",timeout=15000)
    assert page.input_value('#airfoil')==''  # puste pole = profil przyjęty w P2

    page.click('#btn_fetch_airfoil')
    page.wait_for_selector('#p3_airfoil_svg_container svg',timeout=10000)
    svg=page.evaluate("(() => { const s = document.querySelector('#p3_airfoil_svg_container svg'); return {w: s.getAttribute('width'), vb: s.getAttribute('viewBox'), shown: s.getBoundingClientRect().width}; })()")
    assert svg['w']=='220.0mm' and svg['vb'].split()[2]=='220.00' and svg['shown']>200,svg
    desc=page.inner_text('#p3_airfoil_desc')
    assert 'NACA 23012' in desc and 'Grubość względna: 12' in desc,desc
    assert page.locator('#p3_airfoil_coords_tbody tr').count()==25
    upper_max=page.evaluate("Math.max(...[...document.querySelectorAll('#p3_airfoil_coords_tbody tr')].map(r => parseFloat(r.cells[2].textContent.replace(',', '.'))))")
    assert 14<upper_max<16,upper_max  # NACA 23012 przy c = 200 mm: ok. 15 mm, a nie 94 mm jak dawniej
    assert page.is_enabled('#btn_print_airfoil') and page.is_enabled('#btn_download_airfoil')

    page.fill('#airfoil','Wortmann FX 61-163')
    page.click('#btn_fetch_airfoil')
    page.wait_for_function("document.getElementById('p3_airfoil_desc').classList.contains('airfoil-error')",timeout=10000)
    assert 'Wklej' in page.inner_text('#p3_airfoil_desc')

    page.click('.airfoil-paste summary')
    page.fill('#airfoil_coordinates',SELIG)
    page.click('.airfoil-paste button')
    page.wait_for_function("!document.getElementById('p3_airfoil_desc').classList.contains('airfoil-error')",timeout=10000)
    desc=page.inner_text('#p3_airfoil_desc')
    assert 'Wortmann FX 61-163' in desc and 'wklejone' in desc,desc
    assert page.locator('#p3_airfoil_coords_tbody tr').count()==12  # 6 punktów górnych i 6 dolnych (krawędź natarcia w obu)

    # Profil i rzędne zapisują się w projekcie: przeliczenie, P2 przyjmuje profil autora, po przeładowaniu wracają.
    page.wait_for_function("currentResults && currentResults.params.airfoil === 'Wortmann FX 61-163'",timeout=30000)
    assert page.evaluate("currentResults.bipol_projects.p2.airfoil_selection.selected_airfoil")=='Wortmann FX 61-163'
    assert page.evaluate("currentResults.bipol_projects.p3.airfoil_200mm_table.length")==12
    page.reload()
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
    assert page.input_value('#airfoil')=='Wortmann FX 61-163' and 'FX TEST' in page.input_value('#airfoil_coordinates')

    if args.screenshot:page.locator('#p3_airfoil_svg_container').screenshot(path=args.screenshot)
    assert not errors,errors
    browser.close()
print('OK: profil 200 mm — NACA ze wzoru, odmowa dla profilu bez wzoru, wklejone rzędne, SVG w mm')
