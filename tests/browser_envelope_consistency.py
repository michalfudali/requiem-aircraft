"""Chrome: CS-22 model selection, signed envelope, offline P6 and sinking flight.

Run directly from this worktree. All edits use the application controls. Canvas
instrumentation observes drawing calls and forwards them to the native methods.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from browser_helpers import edit_inputs, navigate, reveal_details, serve_in_process
from calculations.presets import AIRCRAFT_PRESETS

OUT = ROOT / 'work' / 'envelope-20261031'
OUT.mkdir(parents=True, exist_ok=True)

OBSERVE_CANVAS = """(() => {
  window.chartObservation = {};
  const proto = CanvasRenderingContext2D.prototype;
  for (const name of ['clearRect','beginPath','moveTo','lineTo','fillText','stroke']) {
    const native = proto[name];
    proto[name] = function(...args) {
      const id = this.canvas.id;
      if (['chartVn','chartVnP6','chartClimb'].includes(id)) {
        const record = window.chartObservation[id] ||= {texts:[],strokes:[],path:[],version:0};
        if (name === 'clearRect') { record.texts=[]; record.strokes=[]; record.version++; }
        if (name === 'beginPath') record.path=[];
        if (name === 'moveTo' || name === 'lineTo') record.path.push(args.slice(0,2));
        if (name === 'fillText') record.texts.push(String(args[0]));
        if (name === 'stroke') record.strokes.push({color:this.strokeStyle,path:record.path.slice()});
      }
      return native.apply(this,args);
    };
  }
})();"""


def import_project(page, name, params):
    filename = OUT / (name + '-project.json')
    filename.write_text(json.dumps({'name': name, 'params': params}), encoding='utf-8')
    previous = page.evaluate('getActiveProjectId()')
    page.locator('#projectImportFileInput').set_input_files(filename)
    page.wait_for_function('(old) => getActiveProjectId() !== old && !document.querySelector("#calcBtn").disabled',
                           arg=previous, timeout=60000)
    status = page.locator('#calculationStatus')
    assert 'is-error' not in (status.get_attribute('class') or ''), status.inner_text()
    (OUT / (name + '-results.json')).write_text(json.dumps(page.evaluate('currentResults'), indent=2), encoding='utf-8')


def inspect_envelope(page, name, model):
    env = page.evaluate('currentResults.envelope')
    assert env['limits']['cs22_gust_model'] == model
    assert env['speed_basis'] == 'EAS'
    amendment = '3' if model == 'amendment3' else '2'
    assert 'Amdt ' + amendment in env['gust_factors']['gust_basis']
    version = page.evaluate('chartObservation.chartVn?.version || 0')
    navigate(page, 'tab-p6')
    canvas = page.locator('#chartVn')
    reveal_details(canvas)
    canvas.scroll_into_view_if_needed()
    page.wait_for_function('(old) => chartObservation.chartVn?.version > old && chartObservation.chartVn.strokes.some(s=>s.color==="#15803d")', arg=version)
    drawn = page.evaluate('chartObservation.chartVn')
    assert any('km/h EAS' in text for text in drawn['texts'])
    assert not any('przyrządowa' in text for text in drawn['texts'])
    width, height = page.evaluate('[parseFloat(document.querySelector("#chartVn").style.width),parseFloat(document.querySelector("#chartVn").style.height)]')
    colors = {'#15803d', '#0284c7', '#f59e0b', '#7c3aed'}
    assert colors <= {s['color'] for s in drawn['strokes']}
    for stroke in drawn['strokes']:
        if stroke['color'] in colors:
            assert all(49 <= x <= width - 24 and 24 <= y <= height - 44 for x, y in stroke['path'])
    assert 'Amdt ' + amendment in page.locator('#p6EnvelopeTableBody').inner_text()
    canvas.screenshot(path=str(OUT / (name + '-vn.png')))
    half = len(env['composite_polygon']) // 2
    upper, lower = env['composite_polygon'][half-1], env['composite_polygon'][half]
    gust = next(g for g in env['gust_factors']['gusts'] if g['speed'] == 'VD')
    assert abs(upper['n'] - max(env['limits']['n_at_vd_pos'], gust['n_positive'])) <= .006
    assert abs(lower['n'] - min(env['limits']['n_at_vd_neg'], gust['n_negative'])) <= .006
    button = page.locator('#btnModeProjects')
    reveal_details(button)
    button.click()
    page.locator('#pill-p6').click()
    marker = page.locator('#p6_n_flap_val')
    reveal_details(marker)
    assert marker.inner_text() == '4.0'
    return {'case': name, 'model': model, 'k_g': env['gust_factors']['k_g'],
            'vd_positive': upper['n'], 'vd_negative': lower['n'], 'passed': True}


def export_report(page, browser, name, model):
    navigate(page, 'tab-reports')
    for checkbox in page.locator('[name="studio-report-section"]').all():
        reveal_details(checkbox)
        checkbox.set_checked(checkbox.get_attribute('value') == 'p6')
    button = page.locator('[data-studio-action="download-report"]')
    reveal_details(button)
    with page.expect_download(timeout=90000) as download:
        button.click()
    path = OUT / (name + '-report.html')
    download.value.save_as(path)
    offline = browser.new_context(offline=True)
    report = offline.new_page()
    report.goto(path.as_uri())
    report.wait_for_selector('#repVn svg')
    text = report.locator('body').inner_text()
    assert ('Amdt 3 (podmuch 1-cos)' if model == 'amendment3' else 'Amdt 2 (Pratt)') in text
    assert 'Ujemny przyrost przeciążenia od podmuchu przy VB' in text
    assert 'Zewnętrzna granica manewrów i podmuchów' in report.locator('#repVn').inner_text()
    assert 'km/h EAS' in report.locator('#repVn').inner_text()
    assert report.locator('.katex-error').count() == 0
    report.pdf(path=str(OUT / (name + '-report.pdf')), format='A4', print_background=True)
    offline.close()


def main():
    errors, records = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page.add_init_script(OBSERVE_CANVAS)
        serve_in_process(page, 'http://bipol-envelope.local')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto('http://bipol-envelope.local')
        page.wait_for_function('currentResults !== null', timeout=60000)
        import_project(page, 'glider-amendment3', AIRCRAFT_PRESETS['glider_pw5'])
        records.append(inspect_envelope(page, 'glider-amendment3', 'amendment3'))
        export_report(page, browser, 'glider-amendment3', 'amendment3')

        field = edit_inputs(page, 'cs22_gust_model')
        field.select_option('pratt')
        page.locator('#calcBtn').click()
        page.wait_for_function('currentResults?.params.cs22_gust_model === "pratt" && !document.querySelector("#calcBtn").disabled', timeout=60000)
        records.append(inspect_envelope(page, 'glider-pratt', 'pratt'))
        assert records[0]['k_g'] != records[1]['k_g']
        export_report(page, browser, 'glider-pratt', 'pratt')
        page.reload()
        page.wait_for_function('currentResults?.params.cs22_gust_model === "pratt"', timeout=60000)
        assert edit_inputs(page, 'cs22_gust_model').input_value() == 'pratt'
        page.set_viewport_size({'width': 390, 'height': 850})
        page.locator('#cs22_gust_model').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        page.screenshot(path=str(OUT / 'model-mobile.png'))
        page.set_viewport_size({'width': 1440, 'height': 1000})

        # A legacy file must reset the previous project's model to the explicit default.
        import_project(page, 'motoglider-legacy', AIRCRAFT_PRESETS['motoglider_aos'])
        records.append(inspect_envelope(page, 'motoglider-legacy', 'amendment3'))
        # Force gusts far beyond the manoeuvre range: the old scale clipped them.
        import_project(page, 'glider-high-gust', dict(AIRCRAFT_PRESETS['glider_pw5'],
            cz_max_clean=1., cz_max_to=1.2, cz_max_lnd=1.6, wing_input_mode='area_aspect',
            wing_area_m2=20., aspect_ratio=20.))
        assert page.evaluate('currentResults.envelope.limits.n_dimensioning_neg < currentResults.envelope.limits.n_min * 1.3'), page.evaluate('currentResults.envelope.limits')
        records.append(inspect_envelope(page, 'glider-high-gust', 'amendment3'))
        import_project(page, 'underpowered', dict(AIRCRAFT_PRESETS['ga_trainer'], power_input_mode='fixed', engine_power_kw=.001))
        edit_inputs(page, 'category')
        assert page.locator('#cs22GustModelGroup').is_hidden()
        version = page.evaluate('chartObservation.chartClimb?.version || 0')
        navigate(page, 'tab-p5')
        canvas = page.locator('#chartClimb')
        reveal_details(canvas)
        canvas.scroll_into_view_if_needed()
        page.wait_for_function('(old) => chartObservation.chartClimb?.version > old && chartObservation.chartClimb.strokes.some(s=>s.color==="#2563eb")', arg=version)
        climb = page.evaluate('currentResults.performance.climb')
        assert climb['wy_max_ms'] < 0
        drawn = page.evaluate('chartObservation.chartClimb')
        assert any(re.match(r'^-\d', text) for text in drawn['texts'])
        assert any('km/h TAS' in text for text in drawn['texts'])
        curve = next(s['path'] for s in drawn['strokes'] if s['color'] == '#2563eb')
        assert max(y for x, y in curve) - min(y for x, y in curve) > 5
        assert f"{climb['wy_max_ms']:.2f} m/s" in canvas.get_attribute('aria-label')
        canvas.screenshot(path=str(OUT / 'underpowered-climb.png'))
        records.append({'case': 'underpowered', 'wy_max_ms': climb['wy_max_ms'], 'negative_ticks': True, 'passed': True})
        assert not errors, errors
        (OUT / 'browser-summary.json').write_text(json.dumps({'cases': records, 'page_errors': errors}, indent=2), encoding='utf-8')
        for record in records:
            print(json.dumps(record), flush=True)
        browser.close()


if __name__ == '__main__':
    main()
