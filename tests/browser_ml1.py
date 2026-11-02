"""Real Chrome: all ML1 workbook branches, edits, CSV, local save and reports."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import launch_chromium
from browser_live_server import live_server

OUT=ROOT/'work'/'headless-ml1'
OUT.mkdir(parents=True,exist_ok=True)
BASE='http://ml1.test'


def completed(page):
    page.wait_for_function("document.querySelector('#calculationMessage').className==='success'",timeout=180000)
    assert page.locator('#resultsSection').is_visible()
    assert page.locator('#downloadResults').is_enabled()


with live_server(OUT) as BASE, sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    context=browser.new_context(viewport=dict(width=1440,height=1000),accept_downloads=True)
    page=context.new_page()
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/ml1');page.locator('#ml1-aircraft-flight_mass_kg').wait_for()
    page.wait_for_function("document.querySelector('#methodSelect').options.length>=40")
    legends=page.locator('#workbookFields > fieldset > legend').all_text_contents()
    assert [text[:2] for text in legends[:4]]==['P1','P2','P2','P3']
    for kind in (['glider','jet'] if '--quick' in sys.argv else ['glider','propeller','fixed','jet']):
        page.locator('#exampleKind').select_option(kind);page.locator('#loadExample').click()
        page.wait_for_function("document.querySelector('#calculationMessage').textContent.includes('Wczytano przykład')")
        page.locator('#workbookForm > button[type=submit]').click();completed(page)
        assert page.locator('#results svg').count()>=2
        with page.expect_download() as d:page.locator('#downloadResults').click()
        target=OUT/(kind+'-results.json');d.value.save_as(target)
        exported=json.loads(target.read_text(encoding='utf-8'))
        assert exported['method']=='workbook'
        assert exported['result']['p1']['mass_basis']=='known_aircraft_fixed_measurements'
        page.locator('#resultsSection').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/(kind+'.png')),full_page=False)
        print(kind,'workbook, charts and export OK',flush=True)
    # Edit after calculation: old results/exports are immediately unavailable.
    page.locator('#ml1-aircraft-name').fill('Własny opis testu ML1')
    assert page.locator('#resultsSection').is_hidden()
    assert page.locator('#downloadResults').is_disabled()
    page.reload();page.locator('#ml1-aircraft-name').wait_for()
    assert page.locator('#ml1-aircraft-name').input_value()=='Własny opis testu ML1'
    assert page.locator('#resultsSection').is_hidden()
    # Recompute jet, export report, and open the downloaded HTML without the app.
    page.locator('#workbookForm > button[type=submit]').click();completed(page)
    with page.expect_download(timeout=180000) as d:page.locator('#downloadReport').click()
    report=OUT/'jet-report.html';d.value.save_as(report)
    offline=context.new_page();offline.goto(report.as_uri())
    assert offline.locator('svg').count()>=5
    assert 'Własny opis testu ML1' in offline.locator('body').inner_text()
    offline.close()
    print('local reload, stale results and standalone report OK',flush=True)
    # CSV imports three Reynolds datasets, retaining negative CL.
    csv='re;cl;cd;alpha_deg\n'+''.join(f'{re};{cl};0,02;{cl*10}\n' for re in [1000000,3000000,6000000] for cl in [-.8,0,1.5])
    file=OUT/'profiles.csv';file.write_text(csv,encoding='utf-8-sig')
    page.locator('#ml1-profile-datasets').locator('xpath=..').locator('input[type=file]').set_input_files(file)
    page.wait_for_function("document.querySelector('#calculationMessage').textContent.includes('Wczytano tabelę CSV')")
    curves=json.loads(page.locator('#ml1-profile-datasets').input_value())
    assert len(curves)==3 and curves[0]['rows'][0]['cl']==-.8
    # Method calculator: scalar valid/invalid PG and disabled exports on edit.
    page.locator('[data-view=methods]').click();page.locator('#projectFilter').select_option('6')
    page.locator('#methodSelect').select_option('prandtl')
    assert '/23997/' in page.locator('#methodSource a').get_attribute('href')
    page.locator('#methodNotes').locator('xpath=..').locator('summary').click()
    assert 'Suplement' in page.locator('#methodNotes').inner_text()
    page.locator('#ml1-mach').fill('.6');page.locator('#methodForm > button[type=submit]').click();completed(page)
    page.locator('#ml1-mach').fill('1');page.locator('#methodForm > button[type=submit]').click()
    page.wait_for_function("document.querySelector('#calculationMessage').className==='error'")
    assert 'M < 1' in page.locator('#calculationMessage').inner_text()
    assert page.locator('#downloadResults').is_disabled()
    page.locator('[data-view=sources]').click();assert page.locator('#sourceList li').count()==39
    assert not errors,errors
    print('CSV, scalar methods, domain errors and sources OK',flush=True)
    # Mobile user path and overflow, including a real calculation.
    mobile=browser.new_context(viewport=dict(width=390,height=844))
    m=mobile.new_page();m.goto(BASE+'/ml1')
    m.locator('#ml1-aircraft-name').wait_for();m.locator('#exampleKind').select_option('glider');m.locator('#loadExample').click()
    m.wait_for_function("document.querySelector('#calculationMessage').textContent.includes('Wczytano przykład')")
    m.locator('#workbookForm > button[type=submit]').click();completed(m)
    assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    m.screenshot(path=str(OUT/'mobile.png'),full_page=False)
    print('mobile calculation and layout OK',flush=True)
    mobile.close();context.close();browser.close()
