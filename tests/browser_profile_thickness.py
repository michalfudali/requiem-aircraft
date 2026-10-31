"""Chrome: thickness source, manual mismatch, raw coordinates and project isolation."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import edit_inputs, navigate, reveal_details, serve_in_process
from browser_airfoil_state import p3, ready, import_project
from calculations.presets import AIRCRAFT_PRESETS
from test_profile_thickness import ORDINATES, TC

OUT = ROOT / 'work' / 'profile-thickness-20261101'
OUT.mkdir(parents=True, exist_ok=True)


def calculate(page, condition):
    if not page.locator('#calcBtn').is_visible():
        navigate(page, 'tab-inputs')
    page.locator('#calcBtn').click()
    page.wait_for_function(condition + ' && !document.querySelector("#calcBtn").disabled', timeout=60000)
    ready(page)


def summary(page):
    return page.locator('[data-profile-thickness-summary]').last.inner_text()


def reports(page, browser):
    navigate(page, 'tab-reports')
    for checkbox in page.locator('[name="studio-report-section"]').all():
        reveal_details(checkbox)
        checkbox.set_checked(checkbox.get_attribute('value') in ('p3', 'p4'))
    button = page.locator('[data-studio-action="download-report"]'); reveal_details(button)
    with page.expect_download(timeout=90000) as download:
        button.click()
    path = OUT / 'manual-mismatch-report.html'; download.value.save_as(path)
    offline = browser.new_context(offline=True)
    report = offline.new_page(); report.goto(path.as_uri())
    notes = report.locator('.profile-thickness-assessment')
    assert notes.count() == 2
    for note in notes.all():
        assert note.get_attribute('data-mismatch') == 'true'
        assert '12% zamiast 15%' in note.inner_text()
        assert 'NACA 23012' in note.inner_text()
    assert not report.locator('.katex-error').count()
    report.pdf(path=str(OUT / 'manual-mismatch-report.pdf'), prefer_css_page_size=True, print_background=True)
    offline.close()


def main():
    records, errors = [], []
    def passed(name):
        records.append(name); print(json.dumps(dict(case=name, passed=True)), flush=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=1000), accept_downloads=True)
        serve_in_process(page, 'http://profile-thickness.local')
        page.on('dialog', lambda dialog: dialog.accept())
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://profile-thickness.local'); ready(page)
        import_project(page, 'thickness-test', dict(AIRCRAFT_PRESETS['ga_trainer']))
        page.locator('#airfoil').fill('NACA 0015'); page.locator('#btn_fetch_airfoil').click()
        page.wait_for_function('currentResults.params.airfoil==="NACA 0015" && currentResults.geometry.wing.tc_ratio===.15 && !document.querySelector("#calcBtn").disabled', timeout=60000)
        assert page.locator('#tc_ratio').input_value() == '0.15'
        assert page.locator('#tc_ratio').get_attribute('readonly') is not None
        assert 'NACA' in summary(page)
        passed('selected_naca_drives_calculations_and_derived_input')

        edit_inputs(page, 'profile_thickness_mode').select_option('assumed')
        calculate(page, 'currentResults.params.profile_thickness_mode==="assumed"')
        assert page.locator('#tc_ratio').is_editable()
        page.locator('#tc_ratio').fill('0.12')
        calculate(page, 'currentResults.geometry.wing.tc_ratio===.12')
        p3(page)
        assert '12% zamiast 15%' in summary(page)
        assert page.locator('[data-profile-thickness-summary]').last.get_attribute('data-mismatch') == 'true'
        passed('manual_assumption_preserved_and_mismatch_visible')
        reports(page, browser); passed('offline_p3_p4_explain_mismatch_and_polar_source')

        page.set_viewport_size(dict(width=390, height=850)); p3(page)
        page.locator('[data-profile-thickness-summary]').last.scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(OUT / 'mobile-mismatch.png'))
        passed('mobile_mismatch_readable_without_page_overflow')
        page.set_viewport_size(dict(width=1440, height=1000))
        edit_inputs(page, 'profile_thickness_mode').select_option('auto')
        calculate(page, 'currentResults.geometry.wing.tc_ratio===.15')
        assert page.locator('#tc_ratio').get_attribute('readonly') is not None
        passed('automatic_mode_restores_profile_thickness')

        p3(page); page.locator('#airfoil').fill('UNKNOWN PROFILE')
        calculate(page, 'currentResults.params.airfoil==="UNKNOWN PROFILE"')
        p3(page)
        assert page.evaluate('currentResults.geometry.wing.tc_ratio') == .15
        assert page.locator('#tc_ratio').is_editable()
        assert 'Brak poprawnej geometrii' in summary(page)
        passed('unavailable_geometry_is_an_explicit_assumption')

        page.locator('#airfoil').fill('')
        reveal_details(page.locator('#airfoil_coordinates'))
        page.locator('#airfoil_coordinates').fill(ORDINATES)
        page.locator('.airfoil-paste button').click()
        page.wait_for_function('(tc)=>Math.abs(currentResults.geometry.wing.tc_ratio-tc)<1e-12 && !document.querySelector("#calcBtn").disabled', arg=TC, timeout=60000)
        assert math.isclose(float(page.locator('#tc_ratio').input_value()), TC, abs_tol=5e-7)
        assert float(page.locator('#tc_ratio').input_value()) != .15
        page.reload(); ready(page); p3(page)
        assert math.isclose(page.evaluate('currentResults.geometry.wing.tc_ratio'), TC, abs_tol=1e-14)
        passed('pasted_knot_maximum_survives_display_and_reload')

        import_project(page, 'legacy-defaults', dict(AIRCRAFT_PRESETS['ga_trainer']))
        assert page.locator('#profile_thickness_mode').input_value() == 'auto'
        assert page.locator('#tc_ratio').input_value() == '0.12'
        assert page.locator('#tc_ratio').is_editable()
        assert not page.evaluate('currentResults.profile_geometry.derived')
        passed('legacy_import_does_not_inherit_previous_mode_or_thickness')
        assert not errors, errors
        (OUT / 'browser-summary.json').write_text(json.dumps(dict(cases=records, page_errors=errors), indent=2), encoding='utf-8')
        print(json.dumps(dict(passed=len(records), page_errors=errors)), flush=True)
        browser.close()


if __name__ == '__main__':
    main()
