"""Chrome: landing-gust diagram, actual edits, no stale flap data and offline P6."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from browser_helpers import edit_inputs,navigate,reveal_details,serve_in_process
from calculations.presets import AIRCRAFT_PRESETS

OUT=ROOT/'work'/'flap-gust-20261031'
OUT.mkdir(parents=True,exist_ok=True)


def check_status(page):
    status=page.locator('#calculationStatus')
    assert 'is-error' not in (status.get_attribute('class') or ''),status.inner_text()


def import_project(page,name,params):
    path=OUT/(name+'.json')
    path.write_text(json.dumps(dict(name=name,params=params)),encoding='utf-8')
    old=page.evaluate('getActiveProjectId()')
    page.locator('#projectImportFileInput').set_input_files(path)
    page.wait_for_function('(old)=>getActiveProjectId()!==old && !document.querySelector("#calcBtn").disabled',arg=old,timeout=60000)
    check_status(page)


def edit(page,key,value):
    edit_inputs(page,key).select_option(value)
    page.locator('#calcBtn').click()
    page.wait_for_function('([key,value])=>currentResults.params[key]===value && !document.querySelector("#calcBtn").disabled',arg=[key,value],timeout=60000)
    check_status(page)


def inspect(page,name,applicable):
    result=page.evaluate('currentResults')
    flap=result['envelope']['flap']
    assert flap['applicable'] is applicable
    (OUT/(name+'-results.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    navigate(page,'tab-p6')
    main_plot=page.locator('#highLiftEnvelopePlot')
    reveal_details(main_plot)
    main_plot.scroll_into_view_if_needed()
    assert main_plot.locator('svg').count()==int(applicable)
    button=page.locator('#btnModeProjects')
    reveal_details(button);button.click()
    page.locator('#pill-p6').click()
    plot=page.locator('#p6_flap_plot')
    reveal_details(plot)
    plot.scroll_into_view_if_needed()
    table=page.locator('#p6_flap_loads_tbody')
    if applicable:
        assert plot.locator('svg').count()==1
        assert 'Podmuch dodatni' in plot.inner_text() and 'Podmuch ujemny' in plot.inner_text()
        assert 'Granica wypadkowa' in plot.inner_text() and 'km/h EAS' in plot.inner_text()
        assert len(plot.locator('path[clip-path]').all())==4
        for path in plot.locator('path[clip-path]').all():
            coordinates=re.findall(r'[ML](-?[\d.]+),(-?[\d.]+)',path.get_attribute('d'))
            assert coordinates and all(65.9<=float(x)<=620.1 and 21.9<=float(y)<=221.1 for x,y in coordinates)
        assert f"{flap['limits']['n_gust_min']:.2f}" in table.inner_text()
        assert page.locator('#p6_n_flap_val').inner_text()==f"{flap['n_flap']:.1f}"
        assert flap['basis'] in page.locator('#p6_flap_status').inner_text()
    else:
        assert plot.locator('svg').count()==0
        assert table.locator('tr').count()==0
        assert page.locator('#p6_n_flap_val').inner_text()=='—'
        assert page.locator('#p6_vf_val').inner_text()=='—'
        assert 'Brak wychylanej mechanizacji' in plot.inner_text()
    ids=page.locator('clipPath[id^="bipol-plot-"]').evaluate_all('(nodes)=>nodes.map(n=>n.id)')
    assert len(ids)==len(set(ids))
    global_=result['envelope']['configuration_limits']
    assert f"{global_['n_dimensioning_pos']:.2f} / {global_['n_dimensioning_neg']:.2f}" in page.locator('#p6_configuration_loads').inner_text()
    plot.screenshot(path=str(OUT/(name+'-plot.png')))
    return dict(case=name,applicable=applicable,flap_loads=flap['limits'],passed=True)


def export(page,browser,name,applicable):
    navigate(page,'tab-reports')
    for checkbox in page.locator('[name="studio-report-section"]').all():
        reveal_details(checkbox)
        checkbox.set_checked(checkbox.get_attribute('value')=='p6')
    button=page.locator('[data-studio-action="download-report"]')
    reveal_details(button)
    with page.expect_download(timeout=90000) as download:button.click()
    path=OUT/(name+'-report.html');download.value.save_as(path)
    offline=browser.new_context(offline=True)
    report=offline.new_page();report.goto(path.as_uri())
    report.wait_for_selector('#configuration-loads-basis')
    assert report.locator('#repFlapEnvelope svg').count()==int(applicable)
    if applicable:
        assert 'Podmuch ujemny' in report.locator('#repFlapEnvelope').inner_text()
        assert 'Przyrost przeciążenia od podmuchu z mechanizacją' in report.locator('body').inner_text()
    else:
        assert 'nie dotyczy' in report.locator('#flap-model-basis').inner_text()
    assert not report.locator('.katex-error').count()
    report.pdf(path=str(OUT/(name+'-report.pdf')),format='A4',print_background=True)
    offline.close()


def main():
    errors,records=[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        page=browser.new_page(viewport=dict(width=1440,height=1000),accept_downloads=True)
        serve_in_process(page,'http://bipol-flaps.local')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('dialog',lambda dialog:dialog.accept())
        page.goto('http://bipol-flaps.local');page.wait_for_function('currentResults!==null',timeout=60000)
        import_project(page,'glider-amendment3',AIRCRAFT_PRESETS['glider_pw5'])
        records.append(inspect(page,'glider-amendment3',True));export(page,browser,'glider-amendment3',True)
        edit(page,'cs22_gust_model','pratt')
        records.append(inspect(page,'glider-pratt',True))
        assert records[0]['flap_loads']['n_gust_min']!=records[1]['flap_loads']['n_gust_min']
        import_project(page,'trainer',AIRCRAFT_PRESETS['ga_trainer'])
        records.append(inspect(page,'trainer',True))
        edit(page,'flap_type','none')
        assert 'Brak klap spływu' in page.locator('#flapDidacticCard').inner_text()
        assert page.evaluate('currentResults.geometry.control_surfaces.flaps.S_flap_surface_m2')==0
        records.append(inspect(page,'no-flaps',False));export(page,browser,'no-flaps',False)
        page.reload();page.wait_for_function('currentResults?.envelope.flap.applicable===false',timeout=60000)
        assert edit_inputs(page,'flap_type').input_value()=='none'
        edit(page,'slat_type','krueger')
        records.append(inspect(page,'leading-edge-only',True))
        edit(page,'slat_type','none');edit(page,'flap_type','plain')
        records.append(inspect(page,'restored-flaps',True))
        page.set_viewport_size(dict(width=390,height=850))
        page.locator('#p6_flap_plot').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(OUT/'mobile-flaps.png'))
        page.set_viewport_size(dict(width=1440,height=1000))
        import_project(page,'transport',AIRCRAFT_PRESETS['regional_turboprop'])
        records.append(inspect(page,'transport',True));export(page,browser,'transport',True)
        assert 'analizy dynamicznej' in page.locator('#p6_flap_status').inner_text()
        assert not errors,errors
        (OUT/'browser-summary.json').write_text(json.dumps(dict(cases=records,page_errors=errors),indent=2),encoding='utf-8')
        for record in records:print(json.dumps(record),flush=True)
        browser.close()


if __name__=='__main__':main()
