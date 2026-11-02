"""Real HTTP/Chromium: command targets, calculation failures and current report."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_helpers import launch_chromium, navigate, edit_inputs, reveal_details
from browser_live_server import live_server

OUT = Path(__file__).resolve().parents[1] / 'work/headless-modern-ui'


def command(page, text):
    page.keyboard.press('Control+k')
    page.locator('.bipol-palette-input').fill(text)
    assert page.locator('.bipol-palette-item').count(), text
    page.keyboard.press('Enter')


def synced(page):
    page.wait_for_function("document.querySelector('#navRecalcPill').classList.contains('synced') && !document.querySelector('#calcBtn').disabled")
    assert page.locator('#openReportBtn').get_attribute('data-results-stale') == 'false'
    assert 'is-error' not in (page.locator('#calculationStatus').get_attribute('class') or '')
    assert not page.evaluate('BipolCalculationTree.state.stale')
    assert 'attention' not in (page.locator('#studioResultStatus').get_attribute('class') or '')
    assert page.locator('#pilotLoadingMass').is_enabled()


def main():
    with live_server(OUT) as base, sync_playwright() as p:
        browser = launch_chromium(p, headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=1000), accept_downloads=True)
        page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
        page.add_init_script("""window.chartFrames = {};
            const nativeClear = CanvasRenderingContext2D.prototype.clearRect;
            CanvasRenderingContext2D.prototype.clearRect = function(...args) {
                window.chartFrames[this.canvas.id] = (window.chartFrames[this.canvas.id] || 0) + 1;
                return nativeClear.apply(this, args);
            };""")
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base)
        page.wait_for_function('currentResults && !document.querySelector("#calcBtn").disabled', timeout=90000)
        synced(page)
        theme = page.locator('html').get_attribute('data-theme')
        page.locator('#themeToggleBtn').click()
        assert page.locator('html').get_attribute('data-theme') != theme
        page.keyboard.press('Alt+t')
        assert page.locator('html').get_attribute('data-theme') == theme
        page.locator('#btnShortcutsNav').click()
        assert page.locator('.bipol-shortcuts-card').is_visible()
        assert page.locator('html').get_attribute('data-theme') == theme
        assert page.locator('#btnShortcutsNav').get_attribute('aria-label') == 'Skróty klawiszowe (?)'
        page.keyboard.press('Escape')

        navigate(page, 'tab-p6')
        reveal_details(page.locator('#chartVn'))
        page.wait_for_function('chartFrames.chartVn > 0')
        frame = page.evaluate('chartFrames.chartVn')
        page.locator('#themeToggleBtn').click()
        page.wait_for_function('(previous) => chartFrames.chartVn > previous', arg=frame)
        synced(page)

        # Focus the real field through collapsed modules and the basic mode.
        for text, field in [('rozpiętość', 'wingspan_m'), ('współczynnik oporu', 'cx0'),
                            ('liczba pasażerów', 'n_pax'), ('liczba członków', 'n_crew'),
                            ('profil aerodynamiczny', 'airfoil')]:
            command(page, text)
            page.wait_for_function('(id) => document.activeElement.id === id', arg=field)
            assert page.locator('#' + field).is_visible()
        synced(page)

        # A resolved calculation promise must not mark validation failures clean.
        field = edit_inputs(page, 'aspect_ratio')
        original = field.input_value()
        field.fill('0')
        page.keyboard.press('Control+Enter')
        page.wait_for_function("document.querySelector('#calculationStatus').classList.contains('is-error')")
        assert 'synced' not in page.locator('#navRecalcPill').get_attribute('class')
        assert page.locator('#openReportBtn').get_attribute('data-results-stale') == 'true'
        page.screenshot(path=str(OUT / 'validation-error.png'))
        field.fill(original)
        page.locator('#calcBtn').click()
        synced(page)

        # A server failure must retain old results and mark them stale.
        previous = page.evaluate('currentResults.submission_review.signature')
        page.route('**/api/calculate', lambda route: route.fulfill(
            status=503, content_type='application/json', body=json.dumps({'message': 'Test niedostępnego serwera'})))
        page.keyboard.press('Control+Enter')
        page.wait_for_function("document.querySelector('#calculationStatus').classList.contains('is-error')")
        assert 'synced' not in page.locator('#navRecalcPill').get_attribute('class')
        assert page.evaluate('currentResults.submission_review.signature') == previous
        page.unroute('**/api/calculate')
        page.keyboard.press('Control+Enter')
        synced(page)

        # An answer for the previous inputs cannot validate a newer edit.
        pending = []
        page.route('**/api/calculate', lambda route: pending.append(route))
        page.keyboard.press('Control+Enter')
        page.wait_for_function('document.querySelector("#calcBtn").disabled')
        assert 'calculating' in page.locator('#navRecalcPill').get_attribute('class')
        page.wait_for_timeout(100)
        assert len(pending) == 1
        response = pending[0].fetch()
        field = edit_inputs(page, 'range_km')
        changed_range = float(field.input_value()) + 5
        field.fill(str(changed_range))
        pending[0].fulfill(response=response)
        page.wait_for_function('!document.querySelector("#calcBtn").disabled')
        assert 'synced' not in page.locator('#navRecalcPill').get_attribute('class')
        assert page.evaluate('currentResults.params.range_km') != changed_range
        page.unroute('**/api/calculate')
        page.keyboard.press('Control+Enter')
        synced(page)
        assert page.evaluate('currentResults.params.range_km') == changed_range

        # Analysis parameters outside designForm have the same delayed blur
        # semantics. Recomputing while focused must keep all consumers fresh.
        command(page, 'rok oszacowania')
        cost = page.locator('#cost_year')
        page.wait_for_function('document.activeElement.id === "cost_year"')
        cost.fill('2027')
        page.keyboard.press('Control+Enter')
        synced(page)

        # Exploration changes the view, not the calculation basis.
        navigate(page, 'tab-calculation-tree')
        page.locator('#calculationGraphSearch').fill('masa')
        synced(page)
        navigate(page, 'tab-overview')
        page.locator('#studioAircraft_yaw').fill('60')
        synced(page)
        navigate(page, 'tab-p3')
        slider = page.locator('#pilotLoadingMass')
        reveal_details(slider)
        slider.fill('55')
        synced(page)

        # The command opens the current project's report workflow. The download
        # must contain a distinct name, not the default aircraft from GET /report.
        page.locator('.quiet-project-menu > summary').click()
        page.locator('#btnEditProjectWizard').click()
        page.locator('#wiz_name').fill('Motoszybowiec — test bieżącego raportu')
        page.locator('.wizard-step-tab[data-step="5"]').click()
        page.locator('#wizFinishBtn').click()
        page.wait_for_function('currentResults?.params.name === "Motoszybowiec — test bieżącego raportu"', timeout=90000)
        synced(page)
        command(page, 'raport bieżącego')
        assert page.locator('#tab-reports').is_visible()
        button = page.locator('[data-studio-action="download-report"]')
        reveal_details(button)
        with page.expect_download(timeout=120000) as download:
            button.click()
        report_path = OUT / 'current-report.html'
        download.value.save_as(report_path)
        offline = browser.new_context(offline=True)
        report = offline.new_page()
        report.goto(report_path.as_uri())
        assert 'Motoszybowiec — test bieżącego raportu' in report.locator('body').inner_text()
        assert not report.locator('.katex-error').count()
        offline.close()

        page.locator('body').click(position=dict(x=10, y=10))
        page.keyboard.press('?')
        assert page.locator('.bipol-shortcuts-card').is_visible()
        page.keyboard.press('Escape')
        assert not page.locator('.bipol-shortcuts-card').is_visible()
        assert not errors, errors
        browser.close()
        print('PASS: real parameter focus; validation/HTTP failure/recovery; stale response rejection; shortcut/blur freshness in form and analysis; graph/pilot/report freshness; current offline report; theme and shortcuts')


if __name__ == '__main__':
    main()
