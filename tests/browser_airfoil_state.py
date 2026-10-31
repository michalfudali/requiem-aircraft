"""Chrome: profile isolation, ordinate precedence, stale exports and delayed replies."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from playwright.sync_api import Error,sync_playwright
from browser_helpers import navigate,reveal_details,serve_in_process
from calculations.airfoils import airfoil_200mm
from calculations.presets import AIRCRAFT_PRESETS
from test_airfoil_project_state import SELIG

OUT=ROOT/'work'/'profile-state-20261031'
OUT.mkdir(parents=True,exist_ok=True)


def p3(page):
    menu=page.locator('#studioMenuToggle')
    if page.viewport_size['width']<=1100 and menu.get_attribute('aria-expanded')!='true':menu.click()
    button=page.locator('#btnModeProjects');reveal_details(button);button.click()
    if page.viewport_size['width']<=1100 and menu.get_attribute('aria-expanded')=='true':page.keyboard.press('Escape')
    page.locator('#pill-p3').click()
    reveal_details(page.locator('#airfoil'))


def ready(page):
    page.wait_for_function('currentResults!==null&&!document.querySelector("#calcBtn").disabled',timeout=60000)
    assert 'is-error' not in (page.locator('#calculationStatus').get_attribute('class') or ''),page.locator('#calculationStatus').inner_text()


def import_project(page,name,params):
    path=OUT/(name+'.json');path.write_text(json.dumps(dict(name=name,params=params)),encoding='utf-8')
    old=page.evaluate('getActiveProjectId()');page.locator('#projectImportFileInput').set_input_files(path)
    page.wait_for_function('(old)=>getActiveProjectId()!==old&&!document.querySelector("#calcBtn").disabled',arg=old,timeout=60000)
    ready(page);p3(page)
    return page.evaluate('getActiveProjectId()')


def inspect(page,name,kind=None):
    p3(page)
    if kind:
        page.wait_for_function('([name,kind])=>airfoilProfile?.airfoil===name&&airfoilProfile.kind===kind',arg=[name,kind],timeout=30000)
        assert name in page.locator('#p3_airfoil_svg_container svg').get_attribute('aria-label')
        assert name in page.locator('#p3_airfoil_desc').inner_text()
        assert page.locator('#btn_download_airfoil').is_enabled()
        assert page.locator('#btn_print_airfoil').is_enabled()
    else:
        assert page.locator('#p3_airfoil_svg_container svg').count()==0
        assert page.locator('#p3_airfoil_coords_tbody tr').count()==0
        assert page.locator('#btn_download_airfoil').is_disabled()
        assert page.locator('#btn_print_airfoil').is_disabled()


def wait_profile(page,name):
    page.wait_for_function('(name)=>currentResults.params.airfoil===name&&!document.querySelector("#calcBtn").disabled',arg=name,timeout=60000)


def export_report(page,browser,label,expected_svg):
    navigate(page,'tab-reports')
    for checkbox in page.locator('[name="studio-report-section"]').all():
        reveal_details(checkbox);checkbox.set_checked(checkbox.get_attribute('value')=='p3')
    button=page.locator('[data-studio-action="download-report"]');reveal_details(button)
    with page.expect_download(timeout=90000) as download:button.click()
    path=OUT/(label+'-report.html');download.value.save_as(path)
    offline=browser.new_context(offline=True);report=offline.new_page();report.goto(path.as_uri())
    assert report.locator('.airfoil-1to1 svg').count()==int(bool(expected_svg))
    if expected_svg:
        expected=re.search(r'<path d="([^"]+)"',expected_svg).group(1)
        assert report.locator('.airfoil-1to1 svg path').first.get_attribute('d')==expected
        assert report.locator('.airfoil-1to1 svg').get_attribute('width')=='220.0mm'
    assert not report.locator('.katex-error').count()
    report.pdf(path=str(OUT/(label+'-report.pdf')),print_background=True)
    offline.close()


def delayed_request(page):
    pending=[]
    def hold(route):
        if not pending:pending.append(route)
        else:route.fallback()
    page.route('**/api/airfoil/200mm*',hold)
    with page.expect_request(lambda r:'/api/airfoil/200mm' in r.url):page.locator('#btn_fetch_airfoil').click()
    page.wait_for_timeout(50)
    assert len(pending)==1
    return pending[0],hold


def release(page,route,handler,name,error=False):
    data=airfoil_200mm(name)
    body=dict(status='ok',airfoil=data['name'],**{k:v for k,v in data.items() if k!='name'})
    try:
        route.fulfill(status=400 if error else 200,content_type='application/json',
                      body=json.dumps(dict(message='OLD RESPONSE ERROR') if error else body))
    except Error as exc:
        assert 'Interception' in str(exc) or 'already handled' in str(exc),str(exc)
    page.unroute('**/api/airfoil/200mm*',handler)
    page.wait_for_timeout(150)


def main():
    class Cases(list):
        def append(self,case):
            super().append(case)
            print(json.dumps(dict(case=case,passed=True)),flush=True)
    errors,records=[],Cases()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        page=browser.new_page(viewport=dict(width=1440,height=1000),accept_downloads=True)
        serve_in_process(page,'http://profile-state.local')
        page.on('dialog',lambda d:d.accept());page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://profile-state.local');ready(page);inspect(page,'NACA 23012','naca')
        with page.expect_download() as download:page.locator('#btn_download_airfoil').click()
        assert download.value.suggested_filename=='NACA_23012_200mm.svg'
        download.value.save_as(OUT/'initial.svg');records.append('automatic_profile_and_filename')
        reveal_details(page.locator('#airfoil_coordinates'));page.locator('.airfoil-paste button').click()
        page.wait_for_function('document.querySelector("#p3_airfoil_desc").classList.contains("airfoil-error")')
        inspect(page,'',None);records.append('empty_paste_cannot_fake_success')
        page.locator('#btn_fetch_airfoil').click();inspect(page,'NACA 23012','naca')
        import_project(page,'named',dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil='NACA 0012'))
        inspect(page,'NACA 0012','naca');records.append('new_project_geometry')
        pasted_id=import_project(page,'legacy',AIRCRAFT_PRESETS['glider_pw5'])
        assert page.locator('#airfoil').input_value()==page.locator('#airfoil_coordinates').input_value()==''
        inspect(page,'NACA 23012','naca');records.append('legacy_resets_fields_and_plot')
        page.locator('#airfoil').fill('Wortmann FX 61-163')
        page.locator('#btn_fetch_airfoil').click()
        page.wait_for_function('document.querySelector("#p3_airfoil_desc").classList.contains("airfoil-error")')
        inspect(page,'',None);records.append('unsupported_profile_clears_old_plot')
        reveal_details(page.locator('#airfoil_coordinates'));page.locator('#airfoil_coordinates').fill(SELIG)
        page.locator('.airfoil-paste button').click();wait_profile(page,'Wortmann FX 61-163')
        inspect(page,'Wortmann FX 61-163','pasted');records.append('pasted_profile')
        page.locator('#btn_fetch_airfoil').click();inspect(page,'Wortmann FX 61-163','pasted')
        assert page.locator('#p3_airfoil_coords_tbody tr').count()==12;records.append('standard_button_keeps_ordinates')
        page.locator('#airfoil').fill('');page.locator('#btn_fetch_airfoil').click()
        wait_profile(page,'');inspect(page,'CUSTOM TEST','pasted')
        assert page.evaluate('currentResults.bipol_projects.p2.airfoil_selection.selected_airfoil')=='CUSTOM TEST'
        records.append('pasted_header_names_the_project_profile')
        page.locator('#airfoil').fill('Wortmann FX 61-163');page.locator('#btn_fetch_airfoil').click()
        wait_profile(page,'Wortmann FX 61-163')
        import_project(page,'other',dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil='NACA 2412'))
        assert page.locator('#airfoil_coordinates').input_value()==''
        inspect(page,'NACA 2412','naca');records.append('coordinates_do_not_leak')
        switcher=page.locator('#projectSwitcherSelect');reveal_details(switcher);switcher.select_option(pasted_id)
        page.wait_for_function('(id)=>getActiveProjectId()===id&&!document.querySelector("#calcBtn").disabled',arg=pasted_id,timeout=60000)
        inspect(page,'Wortmann FX 61-163','pasted')
        exported_svg=page.evaluate('currentResults.bipol_projects.p3.airfoil_200mm_svg')
        export_report(page,browser,'pasted',exported_svg);records.append('switch_back_and_report_match')
        import_project(page,'editing',dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil='NACA 0012'))
        reveal_details(page.locator('#airfoil_coordinates'));page.locator('#airfoil_coordinates').fill('INVALID COORDINATES')
        inspect(page,'',None)
        assert 'wymagają przeliczenia' in page.locator('#studioResultStatus').inner_text()
        export_report(page,browser,'invalid','');records.append('invalid_edit_clears_export_and_recalculates_report')
        p3(page);page.locator('#airfoil_coordinates').fill('');page.locator('#airfoil').fill('NACA 0015')
        page.locator('#btn_fetch_airfoil').click();wait_profile(page,'NACA 0015')
        inspect(page,'NACA 0015','naca');records.append('recovery')

        page.locator('#airfoil').fill('NACA 2412');route,handler=delayed_request(page)
        page.locator('#airfoil').fill('NACA 0012');page.locator('#btn_fetch_airfoil').click()
        wait_profile(page,'NACA 0012');release(page,route,handler,'NACA 2412')
        inspect(page,'NACA 0012','naca');records.append('late_success_after_edit_is_ignored')

        route,handler=delayed_request(page)
        import_project(page,'race-project',dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil='NACA 2412'))
        release(page,route,handler,'NACA 0012')
        inspect(page,'NACA 2412','naca');records.append('late_reply_after_project_switch_is_ignored')

        route,handler=delayed_request(page)
        page.locator('#airfoil').fill('NACA 0015');page.locator('#btn_fetch_airfoil').click()
        wait_profile(page,'NACA 0015');release(page,route,handler,'NACA 2412',error=True)
        inspect(page,'NACA 0015','naca')
        assert 'airfoil-error' not in page.locator('#p3_airfoil_desc').get_attribute('class').split()
        records.append('late_error_cannot_erase_current_profile')
        page.set_viewport_size(dict(width=390,height=850))
        page.locator('#p3_airfoil_svg_container').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(OUT/'mobile.png'))
        page.reload();ready(page);inspect(page,'NACA 0015','naca');records.append('reload_and_mobile')
        page.set_viewport_size(dict(width=1440,height=1000))
        with page.expect_download() as download:page.locator('#btn_download_airfoil').click()
        assert download.value.suggested_filename=='NACA_0015_200mm.svg'
        download.value.save_as(OUT/'current.svg')
        with page.expect_popup() as popup:page.locator('#btn_print_airfoil').click()
        printed=popup.value;printed.wait_for_selector('svg')
        assert 'NACA 0015' in printed.locator('svg').get_attribute('aria-label')
        printed.pdf(path=str(OUT/'current-profile.pdf'),prefer_css_page_size=True,print_background=True)
        printed.close();records.append('download_and_print_use_current_profile')
        assert not errors,errors
        (OUT/'browser-summary.json').write_text(json.dumps(dict(cases=records,page_errors=errors),indent=2),encoding='utf-8')
        print(json.dumps(dict(passed=len(records),cases=records,page_errors=errors)),flush=True)
        browser.close()


if __name__=='__main__':main()
