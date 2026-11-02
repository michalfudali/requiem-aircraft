"""Chrome: actual ballast correction, optimal/wrong station, report and export."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process,reveal_details,edit_inputs,navigate,launch_chromium
from calculations.ballast import solve_ballast
from calculations.presets import AIRCRAFT_PRESETS
from app import app

OUT=ROOT/'work'/'ballast-20261101';OUT.mkdir(parents=True,exist_ok=True)

def compare(a,b):
    assert a['status']==b['status'],(a,b)
    if a['feasible']:
        assert abs(a['mass_kg']-b['mass_kg'])<1e-7
        for x,y in zip(a['after'],b['after']):
            assert abs(x['xcg_mac_pct']-y['xcg_mac_pct'])<1e-7
            assert x['passed'] and y['passed']

with sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    page=browser.new_page(viewport=dict(width=1500,height=1000),accept_downloads=True);serve_in_process(page,'http://ballast.test')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://ballast.test');page.wait_for_function('currentResults!==null&&!document.querySelector("#calcBtn").disabled',timeout=60000)
    params={**AIRCRAFT_PRESETS['motoglider_aos'],'v_h':.35,'locked_params':['v_h']}
    file=OUT/'ballast-input.json';file.write_text(json.dumps(dict(name='Korekta wyważenia',params=params)),encoding='utf-8')
    old=page.evaluate('getActiveProjectId()');page.locator('#projectImportFileInput').set_input_files(file)
    page.wait_for_function('(id)=>getActiveProjectId()!==id&&!document.querySelector("#calcBtn").disabled',arg=old,timeout=60000)
    navigate(page,'tab-p3')
    panel=page.locator('#ballastPanel');reveal_details(panel);panel.locator('summary').click();panel.scroll_into_view_if_needed()
    page.locator('#pilotLoadingMass').fill('55')
    model=page.evaluate('BipolBallastUI.model');reference=solve_ballast(model,55.)
    assert reference['feasible'] and reference['mass_kg']>0,reference
    # The browser consumes coefficients from the server; compare many interior settings.
    for person in (55.,61.7,70.,85.,110.):
        for station in (None,0.,model['station_domain_m'][1]*.37,model['station_domain_m'][1]):
            actual=page.evaluate('(v)=>BipolBallast.solve(BipolBallastUI.model,v.p,v.x)',dict(p=person,x=station))
            compare(actual,solve_ballast(model,person,station))
    page.locator('#ballastUseOptimal').click()
    chosen=page.evaluate('BipolBallastUI.chosen');compare(chosen,reference)
    assert page.locator('#ballastStates tr').count()==len(reference['after'])
    assert not panel.locator('.katex-error').count()
    with page.expect_download() as download:page.locator('#ballastExport').click()
    path=OUT/'ballast.tex';download.value.save_as(path);tex=path.read_text(encoding='utf-8')
    assert 'Z=w x_B' in tex and '\\begin{document}' in tex and '\\geq0' in tex
    panel.screenshot(path=str(OUT/'ballast.png'))
    page.set_viewport_size(dict(width=390,height=844));panel.scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.wait_for_function('document.querySelector("#ballastAxis svg").viewBox.baseVal.width<=Math.max(340,document.querySelector("#ballastAxis").clientWidth)+1')
    assert page.evaluate('''()=>[...document.querySelectorAll('#ballastMath .katex-html')].every(e=>e.getBoundingClientRect().left>=document.querySelector('#ballastMath').getBoundingClientRect().left-1)''')
    panel.screenshot(path=str(OUT/'ballast-mobile.png'));page.set_viewport_size(dict(width=1500,height=1000))
    page.locator('#ballastStation').press('End')
    assert page.locator('#ballastResult').get_attribute('data-feasible')=='false'
    page.locator('#pilotLoadingMass').fill('110')
    assert not page.evaluate('BipolBallastUI.optimal.feasible')
    assert page.locator('#ballastUseOptimal').is_disabled()
    # Report reference and graph must represent the same frozen model.
    result=page.evaluate('currentResults')
    response=app.test_client().post('/report/project/p3',json=result['params']);assert response.status_code==200
    html=response.get_data(as_text=True);(OUT/'report.html').write_text(html,encoding='utf-8')
    context=browser.new_context(offline=True);report=context.new_page();report.set_content(html,wait_until='load');report.evaluate('document.fonts.ready')
    assert not report.locator('.katex-error').count()
    table=report.locator('table').filter(has=report.locator('caption',has_text='Wspólny balast: 55 kg'))
    assert table.locator('tbody tr').count()==len(reference['after'])
    for i,row in enumerate(reference['after']):
        value=table.locator('tbody tr').nth(i).locator('td').nth(3).inner_text().replace('\xa0','').replace(' ','')
        assert value==f'{row["mass_kg"]:.3f}'.replace('.',',')
    report.pdf(path=str(OUT/'report.pdf'),prefer_css_page_size=True,print_background=True);context.close()
    page.locator('#ballastGraph').click();page.wait_for_function('BipolCalculationTree.state.selected==="ballast_light_mass"')
    assert page.evaluate('BipolCalculationTree.state.model.byId.get("ballast_light_mass").value')==result['balance']['pilot_loading']['ballast']['references'][0]['mass_kg']
    field=edit_inputs(page,'range_km');field.fill(str(float(field.input_value())+1))
    assert page.locator('#ballastExport').is_disabled() and page.locator('#ballastStation').is_disabled()
    assert not errors,errors
    print('Real ballast correction, Python/JS parity, wrong station, overweight, mobile, LaTeX, graph, offline report and freshness OK',flush=True)
    browser.close()
