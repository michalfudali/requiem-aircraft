"""Chrome: import real designs, inspect both P3 tables and export the P3 report.

Run: python tests/browser_balance_precision.py
All writes stay in this checkout's ignored work directory.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import expect, sync_playwright
from browser_helpers import navigate, reveal_details, serve_in_process
from calculations.presets import AIRCRAFT_PRESETS

OUT = ROOT / 'work' / 'balance-precision-20261031'
OUT.mkdir(parents=True, exist_ok=True)


def check_rows(page, selector, states):
    reveal_details(page.locator(selector))
    page.locator(selector).scroll_into_view_if_needed()
    rows = page.locator(selector + ' tr')
    assert rows.count() == len(states)
    for index, state in enumerate(states):
        row = rows.nth(index)
        badge = row.locator('.badge')
        if not state['in_flight']:
            assert badge.inner_text() == 'Stan naziemny', (selector, row.evaluate('(el)=>el.outerHTML'), state, page.url)
            assert 'badge-success' not in badge.get_attribute('class')
        else:
            passed = state['cg_criterion_passed'] and state['minimum_margin_passed']
            assert ('badge-success' if passed else 'badge-danger') in badge.get_attribute('class')
        assert row.locator('td').nth(2).inner_text() == f"{state['xcg_m']:.3f}"


def main():
    records, errors = [], []
    cases = [('trainer', dict(AIRCRAFT_PRESETS['ga_trainer'])),
             ('small_tail', dict(AIRCRAFT_PRESETS['ga_trainer'], v_h=.4, locked_params=['v_h'])),
             ('uav', dict(AIRCRAFT_PRESETS['uav_tactical']))]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        serve_in_process(page, 'http://bipol-balance.local')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto('http://bipol-balance.local')
        page.wait_for_function('currentResults !== null', timeout=60000)
        for name, params in cases:
            filename = OUT / (name + '.json')
            filename.write_text(json.dumps({'name': name, 'params': params}), encoding='utf-8')
            previous = page.evaluate('getActiveProjectId()')
            page.locator('#projectImportFileInput').set_input_files(filename)
            page.wait_for_function('(old) => getActiveProjectId() !== old && !document.querySelector("#calcBtn").disabled', arg=previous, timeout=60000)
            result = page.evaluate('currentResults')
            states = result['balance']['loading_states']
            margin = result['balance']['stability']['static_margin_aft_pct']
            if name == 'small_tail':
                assert 0 < margin < 5
                assert any(s['minimum_margin_passed'] is False for s in states)
            navigate(page, 'tab-p6')
            check_rows(page, '#p6LoadingStatesTableBody', states)
            travel = page.locator('#p6StabilityTableBody tr').nth(4).locator('td').nth(1)
            reveal_details(travel)
            travel.scroll_into_view_if_needed()
            expect(travel).to_have_text(f"{result['balance']['cg_range']['delta_pct']:.1f}%")
            page.screenshot(path=str(OUT / (name + '-p6.png')), full_page=True)
            button = page.locator('#btnModeProjects')
            reveal_details(button)
            button.click()
            page.locator('#pill-p3').click()
            check_rows(page, '#p3_loading_tbody', states)
            page.locator('#p3_loading_table').screenshot(path=str(OUT / (name + '-p3.png')))
            navigate(page, 'tab-reports')
            for checkbox in page.locator('[name="studio-report-section"]').all():
                reveal_details(checkbox)
                checkbox.set_checked(checkbox.get_attribute('value') == 'p3')
            control = page.locator('[data-studio-action="download-report"]')
            reveal_details(control)
            with page.expect_download(timeout=90000) as download:
                control.click()
            report_path = OUT / (name + '-report.html')
            download.value.save_as(report_path)
            offline = browser.new_context(offline=True)
            report = offline.new_page()
            report.goto(report_path.as_uri())
            table = report.locator('table').filter(has=report.locator('caption', has_text='Rozpatrzone stany'))
            assert table.locator('tbody tr').count() == len(states)
            assert 'Moment [kg' in table.inner_text()
            assert 'Stan naziemny' in table.inner_text()
            if name == 'small_tail':
                assert 'Nie' in table.locator('tbody tr').nth(1).locator('td').last.inner_text()
            report.pdf(path=str(OUT / (name + '-report.pdf')), format='A4', print_background=True)
            offline.close()
            records.append({'case': name, 'states': len(states), 'margin_pct': margin, 'passed': True})
            print(json.dumps(records[-1]), flush=True)
        assert not errors, errors
        (OUT / 'browser-summary.json').write_text(json.dumps({'cases': records, 'page_errors': errors}, indent=2), encoding='utf-8')
        browser.close()


if __name__ == '__main__':
    main()
