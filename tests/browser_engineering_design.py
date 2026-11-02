"""Engineer acceptance: all aircraft types, CAD mass conservation and design variants.

Uses actual browser controls and a real isolated HTTP server. Evaluation reads
results and DOM; it never substitutes calculations or sets application state.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright
from browser_helpers import launch_chromium, navigate, edit_inputs, reveal_details
from browser_live_server import live_server
from browser_design_integrity import physics
from calculations.presets import AIRCRAFT_PRESETS
from calculations.official_topics import ALL_TOPICS

OUT = ROOT / 'work/headless-engineering'


def store(name, data):
    path = OUT / (name + '.json')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return path


def imported(page, name, params):
    path = store(name + '-project', dict(name=name, params=params))
    previous = page.evaluate('getActiveProjectId()')
    page.locator('#projectImportFileInput').set_input_files(path)
    page.wait_for_function('(old) => getActiveProjectId() !== old && !document.querySelector("#calcBtn").disabled', arg=previous, timeout=90000)
    assert 'is-error' not in (page.locator('#calculationStatus').get_attribute('class') or ''), page.locator('#calculationStatus').inner_text()
    result = page.evaluate('currentResults')
    assert result['params']['name'] == name + ' (Import)'
    return result


def check_cad(page, name, result):
    navigate(page, 'tab-cad')
    page.wait_for_selector('#blueprintView svg')
    assert page.locator('#blueprintView [data-cad-checked]').text_content() == '—'
    assert page.locator('#blueprintView [data-cad-approved]').text_content() == '—'
    for key, value in result['mass']['breakdown'].items():
        text = page.locator(f'#blueprintView [data-cad-mass="{key}"]').text_content()
        assert text == f'{value:.1f} kg', (name, key, text, value)
    body = page.locator('#cadBomTableBody')
    reveal_details(body)
    values = body.locator('[data-cad-component-mass]').all_text_contents()
    assert len(values) == 6
    assert abs(sum(map(float, values)) - result['mass']['m_empty']) <= .31, (name, values, result['mass']['m_empty'])
    if result['params']['engine_type'] == 'none':
        assert 'Nie dotyczy' in body.locator('[data-cad-component="propulsion"]').inner_text()
        assert '100.0 kg' not in page.locator('#blueprintView').text_content()
    (OUT / (name + '-cad.svg')).write_text(page.locator('#blueprintView svg').evaluate('(el) => el.outerHTML'), encoding='utf-8')
    page.locator('#blueprintView').screenshot(path=str(OUT / (name + '-cad.png')))


def metrics(result):
    return dict(m0=result['mass']['m0'], fuel=result['mass']['m_fuel'],
                area=result['geometry']['wing']['S'], aspect_ratio=result['geometry']['wing']['AR'],
                ld=result['performance']['glide']['best_glide']['ld'],
                sink=result['performance']['glide']['minimum_sink']['sink_ms'],
                power=result['sizing']['design_point']['power_kw'],
                failed=[c['parameter'] for c in result['compliance_checks'] if not c['passed']])


def main():
    with live_server(OUT) as base, sync_playwright() as p:
        browser = launch_chromium(p, headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=1000), accept_downloads=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'warning' and m.text.startswith('Błąd ') else None)
        page.on('dialog', lambda d: d.accept())
        page.goto(base)
        page.wait_for_function('currentResults && !document.querySelector("#calcBtn").disabled', timeout=90000)
        cases = {key: AIRCRAFT_PRESETS[key] for key in ['ga_trainer', 'twin_turboprop', 'vlj_jet', 'motoglider_aos', 'glider_pw5', 'uav_tactical']}
        cases['jet_transport'] = next(t['parameters'] for t in ALL_TOPICS if t['num'] == 83)
        records = []
        for name, params in cases.items():
            result = imported(page, name, params)
            checks = physics(result)
            assert all(c['passed'] for c in checks), (name, [c for c in checks if not c['passed']])
            node = next(n for n in result['calculation_graph']['nodes'] if n['id'] == 'm0')
            assert abs(node['value'] - result['mass']['m0']) < 1e-8
            check_cad(page, name, result)
            for target in ['tab-p1-p2', 'tab-p3', 'tab-p4', 'tab-p5', 'tab-glide', 'tab-p6', 'tab-compliance']:
                navigate(page, target)
                assert page.locator('#' + target).is_visible()
            if name == 'uav_tactical':
                assert result['mass']['m_crew'] == 0 and result['params']['n_crew'] == 0
            if name == 'glider_pw5':
                assert result['mass']['m_fuel'] == 0 and result['mass']['breakdown']['m_propulsion'] == 0
                assert not result['performance']['takeoff']['available']
                assert result['performance']['glide']['best_glide']['ld'] > 1
            store(name + '-results', result)
            records.append(dict(case=name, aircraft_type=result['params']['aircraft_type'], physics=checks, metrics=metrics(result)))
            print(name, 'physics, CAD, P1–P6 and glide OK', flush=True)

        # A student compares two fixed-span motoglider concepts. A changed aspect
        # ratio changes area, drag, mass and performance together; keep the
        # baseline immutable and allow reopening it as an independent project.
        page.locator('.quiet-project-menu > summary').click()
        page.locator('#btnNewProjectWizard').click()
        page.locator('#wiz_topic').select_option('topic_1')
        page.locator('#wiz_name').fill('Motoszybowiec 13,5 m — studium')
        page.locator('.wizard-step-tab[data-step="5"]').click()
        page.locator('#wizFinishBtn').click()
        page.wait_for_function('currentResults?.params.name === "Motoszybowiec 13,5 m — studium" && !document.querySelector("#calcBtn").disabled', timeout=90000)
        baseline = page.evaluate('currentResults')
        assert baseline['geometry']['wing']['b'] == 13.5
        navigate(page, 'tab-variants')
        page.locator('#studioVariantName').fill('Bazowy 13,5 m')
        page.locator('#studioVariantForm button[type=submit]').click()
        page.wait_for_selector('[data-load-variant]')
        ar = baseline['geometry']['wing']['AR'] * 1.1
        field = edit_inputs(page, 'aspect_ratio')
        field.fill(str(ar))
        page.keyboard.press('Control+Enter')
        page.wait_for_function('(ar) => currentResults.params.aspect_ratio === ar && !document.querySelector("#calcBtn").disabled', arg=ar, timeout=90000)
        alternative = page.evaluate('currentResults')
        assert alternative['geometry']['wing']['b'] == 13.5
        assert abs(alternative['geometry']['wing']['S'] - 13.5 ** 2 / ar) < .001
        assert all(c['passed'] for c in physics(alternative))
        navigate(page, 'tab-variants')
        page.locator('#studioVariantName').fill('Wydłużenie +10%')
        page.locator('#studioVariantForm button[type=submit]').click()
        page.wait_for_function("projectStore.read('bipol_studio_variants_v1', []).length === 2")
        assert page.evaluate("projectStore.read('bipol_studio_variants_v1', [])[1].params.aspect_ratio") == baseline['params']['aspect_ratio']
        assert page.locator('#studioComparison table').count() == 1
        store('motoglider-study', dict(baseline=metrics(baseline), alternative=metrics(alternative)))
        page.locator('[data-load-variant]').last.click()
        page.wait_for_function('currentResults?.params.name === "Bazowy 13,5 m" && !document.querySelector("#calcBtn").disabled', timeout=90000)
        assert page.evaluate('currentResults.params.aspect_ratio') == baseline['params']['aspect_ratio']
        navigate(page, 'tab-reports')
        export = page.locator('[data-studio-action="export-json"]')
        reveal_details(export)
        with page.expect_download() as download:
            export.click()
        backup = OUT / 'motoglider-13_5m-baseline.bipol.json'
        download.value.save_as(backup)
        page.locator('#projectImportFileInput').set_input_files(backup)
        page.wait_for_function('currentResults?.params.name === "Bazowy 13,5 m (Import)" && !document.querySelector("#calcBtn").disabled', timeout=90000)
        assert abs(page.evaluate('currentResults.mass.m0') - baseline['mass']['m0']) < .001
        assert page.evaluate('currentResults.geometry.wing.b') == 13.5
        for width in [1440, 390, 320]:
            page.set_viewport_size(dict(width=width, height=950))
            navigate(page, 'tab-variants')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors, errors
        store('summary', dict(cases=records, page_errors=errors))
        print('Topic 1: fixed span, coupled variant change, immutable baseline, restore, actual JSON round trip and mobile OK', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
