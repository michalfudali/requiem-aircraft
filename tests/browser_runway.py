"""Chrome: change ground surface, recalculate, reload, export, import legacy project."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright
from browser_helpers import edit_inputs, navigate, reveal_details, serve_in_process
from calculations.presets import AIRCRAFT_PRESETS

OUT = ROOT / 'work' / 'runway-20261031'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    params = {**AIRCRAFT_PRESETS['ga_trainer'], 'wing_input_mode':'area_aspect', 'wing_area_m2':20,
              'takeoff_distance_m':300, 'climb_rate_ms':2, 'range_km':500,
              'power_input_mode':'sized', 'engine_power_kw':0, 'design_iteration_mode':'coupled'}
    filename = OUT / 'legacy-project.json'
    filename.write_text(json.dumps({'name':'Runway test','params':params}), encoding='utf-8')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000}, accept_downloads=True)
        serve_in_process(page, 'http://bipol-runway.local')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto('http://bipol-runway.local')
        page.wait_for_function('currentResults !== null', timeout=60000)
        old = page.evaluate('getActiveProjectId()')
        page.locator('#projectImportFileInput').set_input_files(filename)
        page.wait_for_function('(old)=>getActiveProjectId()!==old && !document.querySelector("#calcBtn").disabled', arg=old, timeout=60000)
        paved = page.evaluate('currentResults')
        assert paved['params']['runway_surface'] == 'paved'
        selector = edit_inputs(page, 'runway_surface')
        selector.select_option('grass')
        page.locator('#calcBtn').click()
        page.wait_for_function('currentResults.params.runway_surface === "grass" && !document.querySelector("#calcBtn").disabled', timeout=60000)
        grass = page.evaluate('currentResults')
        assert grass['performance']['takeoff']['terms']['mu_ground'] == .055
        assert grass['sizing']['takeoff_model_requirement'] > paved['sizing']['takeoff_model_requirement']
        assert grass['sizing']['design_point']['power_kw'] > paved['sizing']['design_point']['power_kw']
        assert grass['performance']['takeoff']['distance_to_15m'] <= 300
        page.screenshot(path=str(OUT/'grass-inputs.png'), full_page=True)
        page.reload()
        page.wait_for_function('currentResults?.params?.runway_surface === "grass"', timeout=60000)
        assert page.locator('#runway_surface').input_value() == 'grass'
        navigate(page, 'tab-reports')
        for checkbox in page.locator('[name="studio-report-section"]').all():
            reveal_details(checkbox)
            checkbox.set_checked(checkbox.get_attribute('value') == 'p5')
        control = page.locator('[data-studio-action="download-report"]')
        reveal_details(control)
        with page.expect_download(timeout=90000) as download:
            control.click()
        report_path = OUT/'report.html'
        download.value.save_as(report_path)
        offline = browser.new_context(offline=True)
        report = offline.new_page()
        report.goto(report_path.as_uri())
        assert '0{,}055' in report_path.read_text(encoding='utf-8')
        assert report.locator('.katex-error').count() == 0
        report.pdf(path=str(OUT/'report.pdf'), format='A4', print_background=True)
        offline.close()
        source = page.evaluate('getActiveProjectId()')
        page.locator('#projectImportFileInput').set_input_files(filename)
        page.wait_for_function('(old)=>getActiveProjectId()!==old && currentResults.params.runway_surface==="paved" && !document.querySelector("#calcBtn").disabled', arg=source, timeout=60000)
        assert page.locator('#runway_surface').input_value() == 'paved'
        assert not errors, errors
        summary = {'paved_power_kw':paved['sizing']['design_point']['power_kw'],
                   'grass_power_kw':grass['sizing']['design_point']['power_kw'],
                   'grass_distance_m':grass['performance']['takeoff']['distance_to_15m'],
                   'legacy_reset':'paved', 'page_errors':errors, 'passed':True}
        (OUT/'browser-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps(summary))
        browser.close()


if __name__ == '__main__':
    main()
