"""Chrome: named profile families, cruise scope and offline P4/P5 with worked equations."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import edit_inputs, navigate, reveal_details, serve_in_process
from browser_airfoil_state import p3, ready, import_project
from calculations.presets import AIRCRAFT_PRESETS

OUT = ROOT/'work'/'compressibility-20261101'
OUT.mkdir(parents=True, exist_ok=True)


def p4(page):
    p3(page); page.locator('#pill-p4').click()
    page.locator('#p4_compressibility_summary').scroll_into_view_if_needed()


def calculate(page, condition):
    navigate(page, 'tab-inputs'); page.locator('#calcBtn').click()
    page.wait_for_function(condition + ' && !document.querySelector("#calcBtn").disabled', timeout=60000)
    ready(page)


def export_report(page, browser, label, required):
    navigate(page, 'tab-reports')
    for checkbox in page.locator('[name="studio-report-section"]').all():
        reveal_details(checkbox); checkbox.set_checked(checkbox.get_attribute('value') in ('p4','p5'))
    button = page.locator('[data-studio-action="download-report"]'); reveal_details(button)
    with page.expect_download(timeout=90000) as download:
        button.click()
    path = OUT/(label+'.html'); download.value.save_as(path)
    offline = browser.new_context(offline=True)
    report = offline.new_page(); report.goto(path.as_uri())
    notes = report.locator('.compressibility-assessment')
    assert notes.count() == 2
    for note in notes.all():
        assert note.get_attribute('data-wave-polar-required') == str(required).lower()
        assert 'nie jest dodany' in note.inner_text()
        assert note.locator('a').get_attribute('href').endswith('ConfigAeroTransonics.pdf')
    if required:
        assert 'Niezweryfikowane dla zadanej prędkości' in report.locator('body').inner_text()
    assert not report.locator('.katex-error').count()
    report.pdf(path=str(OUT/(label+'.pdf')), prefer_css_page_size=True, print_background=True)
    offline.close()


def main():
    cases, errors = [], []
    def passed(name):
        cases.append(name); print(json.dumps(dict(case=name, passed=True)), flush=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport=dict(width=1440,height=1000), accept_downloads=True)
        serve_in_process(page, 'http://compressibility.local')
        page.on('dialog', lambda dialog: dialog.accept())
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://compressibility.local'); ready(page)
        import_project(page, 'low-speed-scope', dict(AIRCRAFT_PRESETS['ga_trainer']))
        p4(page)
        assert page.locator('#p4_compressibility_summary').get_attribute('data-wave-polar-required') == 'false'
        assert 'MTOW' in page.locator('#p4_compressibility_summary').inner_text()
        passed('low_speed_cruise_has_no_wave_scope_warning')

        p3(page); page.locator('#airfoil').fill('NACA 0016'); page.locator('#btn_fetch_airfoil').click()
        page.wait_for_function('currentResults.params.airfoil==="NACA 0016" && !document.querySelector("#calcBtn").disabled', timeout=60000)
        p4(page)
        assert page.evaluate('currentResults.aerodynamics.compressibility.family') == 'conventional_assumption'
        assert page.evaluate('currentResults.aerodynamics.compressibility.tc_ratio') == .16
        assert 'serii 6' not in page.locator('#p4_compressibility_summary').inner_text()
        passed('naca_0016_keeps_conventional_technology_and_selected_thickness')

        import_project(page, 'wave-cruise-scope', dict(AIRCRAFT_PRESETS['vlj_jet'], cruise_speed_kmh=800, airfoil='NACA 0016'))
        p4(page)
        assert page.locator('#p4_compressibility_summary').get_attribute('data-wave-polar-required') == 'true'
        assert 'niezweryfikowane' in page.locator('#p4_compressibility_summary').inner_text()
        assert page.evaluate('currentResults.compliance_checks.some(c=>c.parameter.startsWith("[Ściśliwość]")&&!c.passed)')
        passed('high_speed_cruise_is_not_presented_as_verified_parabolic_performance')
        export_report(page, browser, 'wave-cruise-report', True)
        passed('offline_p4_p5_keep_scope_equations_and_source')

        page.set_viewport_size(dict(width=390,height=850)); p4(page)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(OUT/'mobile-scope.png'))
        passed('mobile_scope_note_fits_the_page')
        page.set_viewport_size(dict(width=1440,height=1000))
        edit_inputs(page, 'cruise_speed_kmh').fill('500')
        calculate(page, 'currentResults.params.cruise_speed_kmh===500')
        p4(page)
        assert page.locator('#p4_compressibility_summary').get_attribute('data-wave-polar-required') == 'false'
        assert not page.evaluate('currentResults.compliance_checks.some(c=>c.parameter.startsWith("[Ściśliwość]"))')
        passed('slower_cruise_recalculates_scope_and_clears_old_warning')

        p3(page); page.locator('#airfoil').fill('NACA 64-212')
        calculate(page, 'currentResults.params.airfoil==="NACA 64-212"')
        p4(page)
        assert page.evaluate('currentResults.aerodynamics.compressibility.family') == 'naca6'
        assert page.evaluate('currentResults.aerodynamics.compressibility.kappa_a') == .87
        assert 'referencyjna Masona' in page.locator('#p4_compressibility_summary').inner_text()
        passed('six_series_has_reference_factor_and_explicit_provenance')

        # The GUI accepts cruise TAS up to 950 km/h. An imported API-only value
        # must produce a clear validation error, rather than showing old results.
        invalid_path = OUT/'outside-gui-range.json'
        invalid_path.write_text(json.dumps(dict(name='Outside GUI range', params=dict(
            AIRCRAFT_PRESETS['vlj_jet'], cruise_speed_kmh=1200, airfoil='NACA 0016'))), encoding='utf-8')
        old = page.evaluate('getActiveProjectId()')
        page.locator('#projectImportFileInput').set_input_files(invalid_path)
        page.wait_for_function('(old)=>getActiveProjectId()!==old && document.querySelector("#calculationStatus").classList.contains("is-error")', arg=old, timeout=60000)
        assert '950' in page.locator('#calculationStatus').inner_text()
        passed('out_of_gui_range_import_is_rejected_clearly')
        edit_inputs(page, 'cruise_speed_kmh').fill('950')
        calculate(page, 'currentResults.params.cruise_speed_kmh===950')
        p4(page)
        assert page.locator('#p4_compressibility_summary').get_attribute('data-wave-polar-required') == 'true'
        export_report(page, browser, 'corrected-range-report', True)
        passed('corrected_input_recalculates_and_keeps_the_wave_scope_warning')
        assert not errors, errors
        (OUT/'browser-summary.json').write_text(json.dumps(dict(cases=cases,page_errors=errors),indent=2),encoding='utf-8')
        print(json.dumps(dict(passed=len(cases),page_errors=errors)),flush=True)
        browser.close()


if __name__ == '__main__':
    main()
