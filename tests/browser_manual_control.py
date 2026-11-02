"""Real browser: enter defaults stage by stage, export, and cancel a manual draft."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers import launch_chromium, navigate, reveal_details
from browser_live_server import live_server

OUT = Path(__file__).resolve().parents[1] / 'work/headless-manual-control'


def main():
    with live_server(OUT) as base, sync_playwright() as p:
        browser = launch_chromium(p, headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=1000), accept_downloads=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base)
        page.wait_for_function('currentResults && !document.querySelector("#calcBtn").disabled', timeout=90000)
        project = page.evaluate('getActiveProjectId()')
        page.locator('[data-manual-control]').click()
        page.locator('#manualControlGate').wait_for(state='visible')
        assert page.locator('[data-mc-submit]').is_disabled()
        stages = []
        for _ in range(15):
            state = page.evaluate('currentResults.manual_control')
            if not state['remaining']:
                break
            stages.append(state['stage'])
            assert page.locator('#manualControlGate').is_visible()
            for control in page.locator('#manualControlGate input[data-key]').all():
                assert control.input_value() == ''
                suggestion = control.get_attribute('placeholder').removeprefix('sugestia: ')
                control.fill(suggestion)
            assert page.locator('[data-mc-submit]').is_enabled()
            page.locator('[data-mc-submit]').click()
            page.wait_for_function('(old) => !document.querySelector("#calcBtn").disabled && currentResults.manual_control.accepted > old', arg=state['accepted'], timeout=90000)
        else:
            raise AssertionError('Manual acceptance did not converge: ' + str(stages))
        assert page.evaluate('currentResults.manual_control.remaining') == 0
        assert not page.locator('#manualControlGate').is_visible()
        # Entering an editable assumption can expose another value to confirm
        # within the same stage after recalculation; stages must not go back.
        assert stages == sorted(stages, key=lambda s: int(s[1:])), stages
        assert set(stages) == {'p1', 'p2', 'p3', 'p4', 'p5', 'p6'}
        assert stages[0] == 'p1' and stages[-1] == 'p6'
        navigate(page, 'tab-reports')
        button = page.locator('[data-studio-action="download-report"]')
        reveal_details(button)
        with page.expect_download(timeout=120000) as download:
            button.click()
        download.value.save_as(OUT / 'manual-report.html')
        assert (OUT / 'manual-report.html').stat().st_size > 10000
        # Opening a new manual draft must not overwrite the active design.
        page.locator('.quiet-project-menu > summary').click()
        page.locator('#btnNewProjectWizard').click()
        page.locator('#projectWizardBackdrop.active').wait_for()
        page.wait_for_function('document.querySelector("#projectWizardBackdrop [data-mc-cleared]") !== null')
        page.locator('#wizNextBtn').click()
        assert 'wpisz wszystkie dane' in page.locator('#wizardValidationStatus').inner_text()
        assert page.locator('#wizardPane1').is_visible()
        page.locator('#wizCancelBtn').click()
        assert page.evaluate('getActiveProjectId()') == project
        page.locator('[data-manual-control]').click()
        page.wait_for_function('!BipolManualControl.isEnabled() && !document.querySelector("#calcBtn").disabled')
        assert page.locator('#manualControlBanner').count() == 0
        assert page.evaluate('getActiveProjectId()') == project
        assert not errors, errors
        print('PASS: manual P1–P6 entry from visible suggestions, report export, draft validation/cancel, mode off and project preservation', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
