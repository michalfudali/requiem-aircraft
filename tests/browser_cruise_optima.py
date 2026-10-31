"""Chrome: continuous optima, unavailable flight, glider reset and offline P5."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from browser_helpers import navigate,reveal_details,serve_in_process
from calculations.presets import AIRCRAFT_PRESETS

OUT=ROOT/'work'/'cruise-optima-20261031'
OUT.mkdir(parents=True,exist_ok=True)


def main():
    cases=[('trainer',AIRCRAFT_PRESETS['ga_trainer'],'available'),
           ('underpowered',dict(AIRCRAFT_PRESETS['ga_trainer'],power_input_mode='fixed',engine_power_kw=.001),'unreachable'),
           ('glider',AIRCRAFT_PRESETS['glider_pw5'],'unpowered'),
           ('jet',AIRCRAFT_PRESETS['vlj_jet'],'available')]
    errors,records=[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
        serve_in_process(page,'http://bipol-cruise.local')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('dialog',lambda dialog:dialog.accept())
        page.goto('http://bipol-cruise.local')
        page.wait_for_function('currentResults!==null',timeout=60000)
        for name,params,status in cases:
            file=OUT/(name+'.json')
            file.write_text(json.dumps({'name':name,'params':params}),encoding='utf-8')
            previous=page.evaluate('getActiveProjectId()')
            page.locator('#projectImportFileInput').set_input_files(file)
            page.wait_for_function('(old)=>getActiveProjectId()!==old && !document.querySelector("#calcBtn").disabled',arg=previous,timeout=60000)
            data=page.evaluate('currentResults.performance.paturski_p6.range_endurance_6_5')
            assert data['optimization']['status']==status
            button=page.locator('#btnModeProjects')
            reveal_details(button)
            button.click()
            page.locator('#pill-p5').click()
            summary=page.locator('#p5_paturski_range_summary')
            reveal_details(summary)
            summary.scroll_into_view_if_needed()
            text=summary.inner_text()
            if status=='available':
                assert f"{data['v_l_max_kmh']:.1f} km/h TAS" in text
                assert f"{data['t_max_h']:.3f} h" in text
                assert 'bez paliwa powrotu i rezerwy' in text
            elif status=='unpowered':
                assert 'nie dotyczą szybowca' in text and 'T_max =' not in text
            else:
                assert 'Nie wyznaczono optimum' in text and 'T_max =' not in text
            summary.screenshot(path=str(OUT/(name+'-summary.png')))
            if name=='trainer':
                navigate(page,'tab-reports')
                for checkbox in page.locator('[name="studio-report-section"]').all():
                    reveal_details(checkbox)
                    checkbox.set_checked(checkbox.get_attribute('value')=='p5')
                button=page.locator('[data-studio-action="download-report"]')
                reveal_details(button)
                with page.expect_download(timeout=90000) as download:button.click()
                path=OUT/'report.html'
                download.value.save_as(path)
                offline=browser.new_context(offline=True)
                report=offline.new_page()
                report.goto(path.as_uri())
                assert 'Optima wyznaczono ciągle' in report.locator('body').inner_text()
                assert report.locator('.katex-error').count()==0
                report.pdf(path=str(OUT/'report.pdf'),format='A4',print_background=True)
                offline.close()
            records.append({'case':name,'status':status,'range_km':data['l_max_km'],
                            'range_speed_kmh':data['v_l_max_kmh'],'passed':True})
            print(json.dumps(records[-1]),flush=True)
        assert not errors,errors
        (OUT/'browser-summary.json').write_text(json.dumps({'cases':records,'page_errors':errors},indent=2),encoding='utf-8')
        browser.close()


if __name__=='__main__':main()
