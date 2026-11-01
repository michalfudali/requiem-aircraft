"""Real Chrome loading exploration, graph link, report and project isolation."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process,navigate,reveal_details,edit_inputs
from calculations.presets import AIRCRAFT_PRESETS

OUT=ROOT/'work'/'tree-20261101'/'browser';OUT.mkdir(parents=True,exist_ok=True)
BASE='http://pilot.test'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
    page=browser.new_page(viewport=dict(width=1500,height=1000));serve_in_process(page,BASE)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_function('currentResults!==null&&!document.querySelector("#calcBtn").disabled',timeout=60000)
    for preset in ('motoglider_aos','glider_pw5','vlj_jet'):
        name='Pilot '+preset;params={**AIRCRAFT_PRESETS[preset],'name':name}
        file=OUT/(preset+'-loading.json');file.write_text(json.dumps(dict(name=name,params=params)),encoding='utf-8')
        page.locator('#projectImportFileInput').set_input_files(file)
        page.wait_for_function('(n)=>currentResults?.params?.name===n+" (Import)"&&!document.querySelector("#calcBtn").disabled',arg=name,timeout=60000)
        navigate(page,'tab-p3')
        panel=page.locator('#pilotLoading');reveal_details(panel)
        panel.scroll_into_view_if_needed()
        assert panel.is_visible()
        study=page.evaluate('currentResults.balance.pilot_loading')
        assert page.locator('#pilotLoadingRows tr').count()==len(study['cases'])
        for key in ('mtow','mlw'):
            page.locator('#pilotLoadingCase').select_option(key)
            c=next(v for v in study['cases'] if v['key']==key)
            page.locator('#pilotLoadingMass').fill('110')
            displayed=page.locator('#pilotLoadingReadout')
            assert abs(float(displayed.get_attribute('data-mass'))-c['heavy']['mass_kg'])<1e-8
            assert abs(float(displayed.get_attribute('data-cg'))-c['heavy']['xcg_mac_pct'])<1e-8
            assert (displayed.get_attribute('data-failed')=='false')==c['heavy']['passed']
            assert not panel.locator('.katex-error').count()
        page.locator('#pilotLoadingCase').select_option('mtow')
        panel.screenshot(path=str(OUT/(preset+'-loading.png')))
        if preset=='motoglider_aos':
            page.set_viewport_size(dict(width=390,height=844));panel.scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert page.evaluate('''()=>[...document.querySelectorAll('#pilotLoadingMath .katex-html')].every(el=>el.getBoundingClientRect().left>=document.querySelector('#pilotLoadingMath').getBoundingClientRect().left-1)''')
            panel.locator('h5').click()
            panel.screenshot(path=str(OUT/'pilot-mobile.png'))
            page.set_viewport_size(dict(width=1500,height=1000))
        page.locator('#pilotLoadingGraph').click()
        page.wait_for_function('BipolCalculationTree.state.selected==="pilot_mtow_heavy_pct"')
        assert page.locator('#calculationGraphInspector').is_visible()
        assert not page.locator('#calculationGraphDetail .katex-error').count()
        if preset=='motoglider_aos':
            from app import app
            actual_params=page.evaluate('currentResults.params')
            response=app.test_client().post('/report/project/p3',json=actual_params)
            assert response.status_code==200
            html=response.get_data(as_text=True);(OUT/'pilot-report.html').write_text(html,encoding='utf-8')
            offline=browser.new_context(offline=True);report=offline.new_page();report.set_content(html,wait_until='load')
            report.evaluate('document.fonts.ready')
            assert report.get_by_role('heading',name='Wpływ masy załogi przy stałym płatowcu').is_visible()
            assert not report.locator('.katex-error').count()
            table=report.locator('#tab-pilot-loading')
            assert table.locator('tbody tr').count()==len(study['cases'])
            for i,c in enumerate(study['cases']):
                value=table.locator('tbody tr').nth(i).locator('td').nth(3).inner_text().replace(' ','').replace('\xa0','').replace(',','.')
                assert abs(float(value)-c['heavy']['mass_excess_kg'])<.051
                expected_cg=f"{c['heavy']['xcg_mac_pct']:.2f}".replace('.',',')
                assert table.locator('tbody tr').nth(i).locator('td').nth(2).inner_text().replace(' ','').replace('\xa0','')==expected_cg
            report.pdf(path=str(OUT/'pilot-report.pdf'),prefer_css_page_size=True,print_background=True)
            offline.close()
        print(preset+' loading and graph OK',flush=True)
    # An edited design cannot continue exploring old loading values unnoticed.
    field=edit_inputs(page,'range_km');field.fill(str(float(field.input_value())+1))
    navigate(page,'tab-p3')
    reveal_details(page.locator('#pilotLoading'))
    assert page.locator('#pilotLoadingStale').is_visible()
    assert page.locator('#pilotLoadingMass').is_disabled()
    # UAV must clear the former crew study completely.
    preset=next(v for v in AIRCRAFT_PRESETS.values() if v.get('aircraft_type')=='uav')
    file=OUT/'uav-loading.json';file.write_text(json.dumps(dict(name='Pilot UAV',params=preset)),encoding='utf-8')
    page.locator('#projectImportFileInput').set_input_files(file)
    page.wait_for_function('currentResults?.params?.aircraft_type==="uav"&&!document.querySelector("#calcBtn").disabled',timeout=60000)
    navigate(page,'tab-p3')
    assert page.locator('#pilotLoading').is_hidden()
    assert not errors,errors
    print('Pilot mass, exact CG, overweight states, LaTeX, graph links and UAV isolation OK',flush=True)
    browser.close()
