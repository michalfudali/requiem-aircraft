"""Chrome: project VS0 pass/fail, real edit and offline P4 export."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import expect, sync_playwright
from browser_helpers import edit_inputs, navigate, reveal_details, serve_in_process
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS

OUT = ROOT / 'work' / 'p4-stall-20261031'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    fixed = {**AIRCRAFT_PRESETS['ga_trainer'], 'wing_input_mode': 'area_aspect', 'wing_area_m2': 20,
             'design_iteration_mode': 'coupled'}
    first = run_bipol_project(fixed)
    fixed['v_stall_kmh'] = first['performance']['terms']['vs_lnd'] * 3.6 - .04
    cases = [('trainer', AIRCRAFT_PRESETS['ga_trainer'], True), ('exceeded', fixed, False),
             ('transport', AIRCRAFT_PRESETS['regional_turboprop'], True)]
    records, errors = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        serve_in_process(page, 'http://bipol-stall.local')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto('http://bipol-stall.local')
        page.wait_for_function('currentResults !== null', timeout=60000)
        for name, params, passed in cases:
            filename = OUT / (name + '-project.json')
            filename.write_text(json.dumps({'name': name, 'params': params}), encoding='utf-8')
            previous = page.evaluate('getActiveProjectId()')
            page.locator('#projectImportFileInput').set_input_files(filename)
            page.wait_for_function('(old) => getActiveProjectId() !== old && !document.querySelector("#calcBtn").disabled', arg=previous, timeout=60000)
            result = page.evaluate('currentResults')
            check = result['bipol_projects']['p4']['high_lift']['stall_requirement']
            assert check['passed'] is passed
            if name == 'exceeded':
                assert -.05 < check['margin_kmh'] < -.03
            button = page.locator('#btnModeProjects')
            reveal_details(button)
            button.click()
            page.locator('#pill-p4').click()
            table = page.locator('#p4_high_lift_tbody')
            reveal_details(table)
            table.scroll_into_view_if_needed()
            badge = table.locator('.badge')
            expect(badge).to_have_class('badge ' + ('badge-success' if passed else 'badge-danger'))
            assert 'Wymaganie projektu' in badge.inner_text()
            assert 'EAS' in table.inner_text()
            assert 'CS-23' not in table.inner_text()
            controls = page.locator('#p4_control_surfaces_tbody')
            controls.scroll_into_view_if_needed()
            assert 'badge-success' not in controls.locator('tr').first.locator('.badge').get_attribute('class')
            assert 'Zgodne CS-' not in controls.inner_text()
            page.locator('#p4_high_lift_tbody').locator('xpath=..').screenshot(path=str(OUT / (name + '-p4.png')))
            if name == 'exceeded':
                page.set_viewport_size({'width': 390, 'height': 850})
                table.scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(OUT / 'exceeded-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate(page, 'tab-reports')
            for checkbox in page.locator('[name="studio-report-section"]').all():
                reveal_details(checkbox)
                checkbox.set_checked(checkbox.get_attribute('value') == 'p4')
            download_button = page.locator('[data-studio-action="download-report"]')
            reveal_details(download_button)
            with page.expect_download(timeout=90000) as download:
                download_button.click()
            report_path = OUT / (name + '-report.html')
            download.value.save_as(report_path)
            offline = browser.new_context(offline=True)
            report = offline.new_page()
            report.goto(report_path.as_uri())
            paragraph = report.locator('#p4-stall-requirement')
            assert ('Wymaganie jest spełnione' if passed else 'Wymaganie nie jest spełnione') in paragraph.inner_text()
            assert 'Nie stanowi wykazania zgodności certyfikacyjnej' in paragraph.inner_text()
            report.pdf(path=str(OUT / (name + '-report.pdf')), format='A4', print_background=True)
            offline.close()
            recovered = None
            if name == 'exceeded':
                new_limit = round(check['actual_kmh'] + 2, 1)
                field = edit_inputs(page, 'v_stall_kmh')
                field.fill(str(new_limit))
                page.locator('#calcBtn').click()
                page.wait_for_function('(limit) => currentResults?.params?.v_stall_kmh === limit && !document.querySelector("#calcBtn").disabled', arg=new_limit, timeout=60000)
                recovered = page.evaluate('currentResults.bipol_projects.p4.high_lift.stall_requirement.passed')
                assert recovered is True
            records.append({'case': name, 'assessment_passed': passed, 'margin_kmh': check['margin_kmh'],
                            'edited_limit_passed': recovered, 'browser_passed': True})
            print(json.dumps(records[-1]), flush=True)
        assert not errors, errors
        (OUT / 'browser-summary.json').write_text(json.dumps({'cases': records, 'page_errors': errors}, indent=2), encoding='utf-8')
        browser.close()


if __name__ == '__main__':
    main()
