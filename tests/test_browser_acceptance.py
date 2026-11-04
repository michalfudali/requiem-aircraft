"""Real HTTP and Chromium acceptance, collected by pytest and run in CI.

No optional dependency is imported until --browser selects these tests. Each
case owns its server, both databases, storage, trace and screenshot directory.
"""
import pytest

from browser_helpers import edit_inputs, navigate, reveal_details
from calculations.presets import AIRCRAFT_PRESETS

pytestmark = pytest.mark.browser


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
    # Presets and saved projects may predate the current design rules. Start from
    # the API-normalized design (crew mass, take-off requirement and category),
    # then use the actual edit/calculate controls with that valid baseline.
    baseline = page.request.post(base + '/api/calculate', data=params)
    assert baseline.ok, baseline.text()
    params = baseline.json()['params']
    from calculations.polish_law import resolve_category, ui_limits
    takeoff_limit = ui_limits(resolve_category(params['category'])).get('takeoff_distance_m', {}).get('max')
    if takeoff_limit is not None:
        params['takeoff_distance_m'] = min(params.get('takeoff_distance_m', takeoff_limit), takeoff_limit)
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


def test_repeated_masses_do_not_form_columns_in_live_and_offline_charts(studio, chromium):
    page, base, output = studio
    page.evaluate('''async params => {
        loadProjectIntoForm({name:'Scatter layout',params}); await performCalculation();
    }''', AIRCRAFT_PRESETS['pzl_kos'])
    navigate(page, 'tab-trends')
    points = page.evaluate('''currentResults.bipol_projects.p1.trend_analysis.similar_aircraft
        .filter(r=>r.empty_fraction>.15&&r.empty_fraction<.95)
        .map(r=>({x:r.m0,y:r.empty_fraction,model:r.model}))''')
    from collections import Counter
    counts = Counter(p['x'] for p in points)
    repeated_x, count = counts.most_common(1)[0]
    assert count > 1  # Independent families may legitimately share the same MTOW.
    indices = [i for i, p in enumerate(points) if p['x'] == repeated_x]
    for width in (1440, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        coords = page.locator('#trendMassChart circle[fill="#5478a9"]').evaluate_all(
            'els=>els.map(el=>el.getAttribute("cx"))')
        assert len({coords[i] for i in indices}) == count
        assert 'rozsunięto poziomo' in page.locator('#trendMassChart svg').text_content()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        page.locator('#trendMassChart').screenshot(path=str(output / f'panel-{width}.png'))
    params = page.evaluate('currentResults.params')
    with chromium.new_context(offline=True, viewport={'width': 1100, 'height': 900}) as offline:
        report = offline.new_page()
        response = page.request.post(base + '/report/project/p1', data=params, timeout=90000)
        assert response.ok
        report.set_content(response.text(), wait_until='load')
        report.evaluate('document.fonts.ready')
        chart = report.locator('#fig-mass-trend svg')
        coords = chart.locator('circle[fill="#5478a9"]').evaluate_all(
            'els=>els.map(el=>el.getAttribute("cx"))')
        assert len({coords[i] for i in indices}) == count
        assert 'rozsunięto poziomo' in chart.text_content()
        # Footnotes and the rightmost trend reading must remain inside the SVG.
        assert chart.evaluate('''svg=>[...svg.querySelectorAll('text')].every(el=>{
            const b=el.getBoundingClientRect(), bounds=svg.getBoundingClientRect();
            return b.left>=bounds.left && b.right<=bounds.right;
        })''')
        report.locator('#fig-mass-trend').screenshot(path=str(output / 'report.png'))
        report.pdf(path=str(output / 'report.pdf'), prefer_css_page_size=True)


def test_trend_sample_uses_best_family_variants_in_panel_export_and_report(studio, chromium):
    import json
    page, base, output = studio
    page.evaluate('''async params => {
        loadProjectIntoForm({name:'Independent families',params}); await performCalculation();
    }''', AIRCRAFT_PRESETS['motoglider_aos'])
    navigate(page, 'tab-trends')
    analysis = page.evaluate('currentResults.bipol_projects.p1.trend_analysis')
    rows = analysis['similar_aircraft']
    assert len(rows) == len({r['family_key'] for r in rows})
    assert analysis['sample']['variant_policy'] == 'best_in_family'
    assert 'Jedna odmiana z każdej rodziny' in page.locator('#trendClassDescription').inner_text()
    assert page.locator('#trend_weighting').is_disabled()
    # A saved manual choice of an inferior variant still selects the best of that family.
    representative = next(r for r in rows if r['variant_selection']['omitted_ids'])
    params = page.evaluate('currentResults.params')
    params['trend_aircraft_ids'] = [r['id'] for r in rows if r['id'] != representative['id']]
    params['trend_aircraft_ids'].append(representative['variant_selection']['omitted_ids'][0])
    page.evaluate('''async params => {
        loadProjectIntoForm({name:'Manual families',params}); await performCalculation();
    }''', params)
    actual = page.evaluate('currentResults.bipol_projects.p1.trend_analysis')
    assert {r['id'] for r in actual['similar_aircraft']} == {r['id'] for r in rows}
    with page.expect_download() as pending:
        page.locator('#trendExportJson').click()
    pending.value.save_as(output / 'analysis.json')
    exported = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))
    exported_rows = exported['analysis']['trend_analysis']['similar_aircraft']
    assert len(exported_rows) == len({r['family_key'] for r in exported_rows})
    with chromium.new_context(offline=True) as offline:
        report = offline.new_page()
        response = page.request.post(base + '/report/project/p1', data=page.evaluate('currentResults.params'))
        assert response.ok
        report.set_content(response.text(), wait_until='load')
        assert report.locator('#tab-sample tbody tr').count() == len(exported_rows)
        assert 'Jedna odmiana z każdej rodziny' in report.locator('[data-trend-report]').inner_text()
        assert not report.locator('.katex-error').count()
        report.locator('#fig-mass-trend').screenshot(path=str(output / 'unique-families.png'))


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
    navigate(page, 'tab-inputs')
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
