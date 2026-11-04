"""Real HTTP and Chromium acceptance, collected by pytest and run in CI.

No optional dependency is imported until --browser selects these tests. Each
case owns its server, both databases, storage, trace and screenshot directory.
"""
from pathlib import Path
import re

import pytest

from browser_helpers import edit_inputs, navigate, reveal_details
from browser_live_server import live_server
from calculations.presets import AIRCRAFT_PRESETS

pytestmark = pytest.mark.browser
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def chromium():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def studio(request, chromium):
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', request.node.name)
    output = ROOT / 'work/browser' / name
    output.mkdir(parents=True, exist_ok=True)
    with live_server(output) as base:
        context = chromium.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: errors.append(f'{response.status} {response.url}')
                if response.status >= 500 else None)
        page.set_default_timeout(20000)
        try:
            page.goto(base)
            page.wait_for_function('currentResults !== null', timeout=60000)
            yield page, base, output
            assert not errors, errors
        finally:
            try:
                page.screenshot(path=str(output / 'last-page.png'), full_page=True)
            finally:
                context.tracing.stop(path=str(output / 'trace.zip'))
                context.close()


CASES = [('ga_trainer', 'piston_ga'), ('regional_turboprop', 'turboprop_regional'),
         ('vlj_jet', 'jet_business'), ('motoglider_aos', 'motoglider'),
         ('glider_pw5', 'glider'), ('uav_tactical', 'uav'), ('transport', 'jet_transport')]


@pytest.mark.parametrize('preset,aircraft_type', CASES, ids=[case[1] for case in CASES])
def test_every_aircraft_class_calculates_in_browser_and_renders_offline_report(studio, chromium, preset, aircraft_type):
    page, base, output = studio
    params = dict(AIRCRAFT_PRESETS['vlj_jet' if preset == 'transport' else preset])
    if preset == 'transport':
        params.update(aircraft_type='jet_transport', category='cs25_transport', n_pax=120,
                      range_km=3500, cruise_speed_kmh=750, cruise_altitude_m=10000, v_stall_kmh=200)
    # Set up a reproducible project, then use the same edit and calculate controls as a student.
    page.evaluate('params => loadProjectIntoForm({name:"CI acceptance",params})', params)
    field = edit_inputs(page, 'aspect_ratio')
    field.fill(str(params['aspect_ratio']))
    page.locator('#calcBtn').click()
    page.wait_for_function('(type) => currentResults?.params.aircraft_type === type && '
                           '!document.querySelector("#calcBtn").disabled', arg=aircraft_type, timeout=60000)
    result = page.evaluate('currentResults')
    mass = result['mass']
    assert mass['m0'] > 0
    assert sum(mass[key] for key in ('m_empty', 'm_fuel', 'm_payload', 'm_crew')) == pytest.approx(mass['m0'], abs=.2)
    assert result['geometry']['wing']['b'] ** 2 / result['geometry']['wing']['S'] == pytest.approx(
        result['geometry']['wing']['AR'], rel=.002)
    if aircraft_type == 'glider':
        assert mass['m_fuel'] == 0
        assert result['params']['engine_type'] == 'none'
    navigate(page, 'tab-overview')
    assert page.locator('.kpi-card:visible').count() == 4
    assert page.locator('#studioAircraft svg').count() == 1
    # Real generated P1 and P6 documents with offline JS, fonts and mathematics.
    with chromium.new_context(offline=True) as offline:
        report = offline.new_page()
        for part in ('p1', 'p6'):
            response = page.request.post(base + '/report/project/' + part, data=result['params'], timeout=90000)
            assert response.ok, response.text()[:500]
            html = response.text()
            (output / f'{part}.html').write_text(html, encoding='utf-8')
            report.set_content(html, wait_until='load')
            report.evaluate('document.fonts.ready')
            assert report.locator('.katex').count() > 10
            assert report.locator('.katex-error').count() == 0


def test_error_recovery_reload_and_mobile_navigation(studio):
    page, _, _ = studio
    field = edit_inputs(page, 'aspect_ratio')
    field.fill('0')
    page.locator('#calcBtn').click()
    page.wait_for_function('document.querySelector("#calculationStatus").classList.contains("is-error")')
    assert page.locator('#openReportBtn').get_attribute('data-results-stale') == 'true'
    field.fill('9.5')
    page.locator('#calcBtn').click()
    page.wait_for_function('currentResults.params.aspect_ratio === 9.5 && '
                          'document.querySelector("#openReportBtn").dataset.resultsStale === "false"')
    page.reload()
    page.wait_for_function('currentResults?.params.aspect_ratio === 9.5')
    for width in (1440, 768, 390, 320):
        page.set_viewport_size({'width': width, 'height': 950})
        for target in ('tab-overview', 'tab-inputs', 'tab-trends'):
            navigate(page, target)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width, target)


def test_calculation_graph_mouse_pan_and_real_formula(studio):
    page, _, _ = studio
    navigate(page, 'tab-calculation-tree')
    page.locator('.calc-graph-node.is-project').first.wait_for()
    viewport = page.locator('#calculationTreeRoot')
    box = viewport.bounding_box()
    before = page.evaluate('({...BipolCalculationTree.state.camera})')
    page.mouse.move(box['x'] + 22, box['y'] + 220)
    page.mouse.down()
    page.mouse.move(box['x'] + 182, box['y'] + 275, steps=12)
    page.mouse.up()
    page.wait_for_function('(x) => Math.abs(BipolCalculationTree.state.camera.x-x-160)<1', arg=before['x'])
    page.locator('#calculationGraphSearch').fill('S')
    page.locator('[data-graph-match="S"]').click()
    assert page.locator('#calculationGraphDetail .katex').count() >= 3
    assert page.locator('#calculationGraphDetail .katex-error').count() == 0
    assert page.evaluate('BipolCalculationTree.state.model.byId.get("S").value') == page.evaluate('currentResults.geometry.wing.S')


def test_engine_proposal_drives_fuel_and_survives_reload(studio):
    page, _, _ = studio
    page.evaluate('async params => {loadProjectIntoForm({name:"Engine acceptance",params}); await performCalculation();}',
                  AIRCRAFT_PRESETS['motoglider_aos'])
    navigate(page, 'tab-p1-p2')
    reveal_details(page.locator('#engineFuelPanel'))
    page.locator('#engine_fuel_mode').select_option('catalog')
    page.locator('#engine_model_id').select_option('rotax_912_ul')
    page.locator('#engine_fuel_point').select_option('cruise75')
    page.locator('#applyEngineFuel').click()
    page.wait_for_function('currentResults.engine_selection.model === "Rotax 912 UL"')
    assert page.evaluate('currentResults.params.sfc') == pytest.approx(16.2 * .72 * 1000 / 43.5)
    assert 'OM-912' in page.locator('#engineFuelStatus').inner_text()
    page.reload()
    page.wait_for_function('currentResults?.params.engine_model_id === "rotax_912_ul"')
    assert page.evaluate('currentResults.params.sfc') == pytest.approx(16.2 * .72 * 1000 / 43.5)
