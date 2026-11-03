"""Choose real engines as a user; verify persistence and source calculations offline."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_helpers import navigate, reveal_details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5017')
    parser.add_argument('--output', default='work/engine-fuel-qa')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    findings, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1600, 'height': 1100})
        context.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.base_url)
        page.wait_for_function('currentResults !== null')
        presets = page.request.get(args.base_url + '/api/presets').json()
        page.evaluate('async params => {loadProjectIntoForm({name:"Silnik — próba",params}); await performCalculation();}',
                      presets['motoglider_aos'])
        navigate(page, 'tab-p1-p2')
        reveal_details(page.locator('#engineFuelPanel'))
        page.locator('#engine_fuel_mode').select_option('catalog')
        page.locator('#engine_model_id').select_option('rotax_912_ul')
        page.locator('#engine_fuel_point').select_option('cruise75')
        page.locator('#applyEngineFuel').click()
        page.wait_for_function("currentResults.engine_selection.model === 'Rotax 912 UL'")
        assert abs(page.evaluate('currentResults.params.sfc') - 16.2 * .72 * 1000 / 43.5) < 1e-8
        assert page.locator('#sfc').get_attribute('readonly') is not None
        assert 'OM-912' in page.locator('#engineFuelStatus').inner_text()
        fuel_before = page.evaluate('currentResults.mass.m_fuel')
        page.locator('#fuel_density_kg_l').fill('.74')
        page.locator('#applyEngineFuel').click()
        page.wait_for_function('currentResults.params.fuel_density_kg_l === .74')
        assert page.evaluate('currentResults.mass.m_fuel') > fuel_before
        page.reload()
        page.wait_for_function('currentResults?.params.fuel_density_kg_l === .74')
        navigate(page, 'tab-p1-p2')
        reveal_details(page.locator('#engineFuelPanel'))
        assert page.locator('#engine_model_id').input_value() == 'rotax_912_ul'
        assert page.locator('#engine_fuel_point').input_value() == 'cruise75'
        assert abs(float(page.locator('#sfc').input_value()) - 16.2 * .74 * 1000 / 43.5) < 1e-8
        page.locator('#engineFuelPanel').screenshot(path=str(out / 'rotax-selection.png'))
        print('UI: model, operating point, density, mass and reload persistence OK', flush=True)
        page.locator('#engine_fuel_mode').select_option('custom')
        page.locator('#engine_custom_model').fill('Rotax 912 UL — dane autora')
        page.locator('#engine_custom_power_kw').fill('58')
        page.locator('#engine_custom_sfc').fill('285')
        page.locator('#applyEngineFuel').click()
        page.wait_for_function("document.querySelector('#calculationStatus').classList.contains('is-error')")
        assert page.locator('#openReportBtn').get_attribute('data-results-stale') == 'true'
        page.locator('#engine_fuel_source').fill('BRP-Rotax OM-912 Ed.4 Rev.1 §5.2, page 5-8')
        page.locator('#engine_fuel_conditions').fill('58 kW, 5500 rpm, maximum continuous, ISA')
        page.locator('#applyEngineFuel').click()
        page.wait_for_function("currentResults.engine_selection.status === 'author_source'")
        assert page.evaluate('currentResults.params.sfc') == 285
        page.reload()
        page.wait_for_function("currentResults?.engine_selection.status === 'author_source'")
        navigate(page, 'tab-p1-p2')
        assert page.locator('#engine_custom_sfc').input_value() == '285'
        assert 'OM-912' in page.locator('#engine_fuel_source').input_value()
        print('UI: missing-source error, own engine evidence and reload persistence OK', flush=True)

        # Each catalogue unit path is rendered in the actual P2/P4/P5 documents.
        cases = [('rotax_912_ul', 'motoglider_aos'), ('rotax_912_uls', 'motoglider_aos'),
                 ('lycoming_o360_a1a', 'ga_trainer'), ('lycoming_io360_a1a', 'ga_trainer'),
                 ('hirth_4103', 'uav_tactical'), ('pbs_tp100', 'regional_turboprop'),
                 ('pbs_tj100', 'vlj_jet')]
        offline = browser.new_context(offline=True, viewport={'width': 1100, 'height': 900})
        report = offline.new_page()
        report.on('pageerror', lambda error: errors.append('REPORT: ' + str(error)))
        for engine_id, preset in cases:
            params = dict(presets[preset], engine_fuel_mode='catalog', engine_model_id=engine_id)
            calculated = page.request.post(args.base_url + '/api/calculate', data=params)
            assert calculated.ok, (engine_id, calculated.text()[:400])
            result = calculated.json()
            assert result['engine_selection']['supported']
            for part in ('p2', 'p4', 'p5'):
                response = page.request.post(args.base_url + '/report/project/' + part, data=params)
                assert response.ok, (engine_id, part, response.text()[:300])
                report.set_content(response.text(), wait_until='load')
                report.evaluate('document.fonts.ready')
                assert report.locator('#tab-engine-fuel').count() == 1
                assert report.locator('.katex').count() > 10
                assert not report.locator('.katex-error').count(), (engine_id, part)
                overflow = report.evaluate('''() => [...document.querySelectorAll('table,.equation')].filter(el=>{
                  const r=el.getBoundingClientRect(),doc=document.querySelector('.document').getBoundingClientRect();
                  return r.right>doc.right-20 || r.left<doc.left;
                }).map(el=>({tag:el.tagName,id:el.id,width:el.getBoundingClientRect().width}))''')
                assert not overflow, (engine_id, part, overflow)
                assert not report.evaluate('''() => [...document.querySelectorAll('.formula')]
                  .some(el=>el.scrollWidth>el.clientWidth+3)'''), (engine_id, part, 'math overflow')
                findings.append(dict(engine=engine_id, part=part, sfc=result['params']['sfc'],
                                     adequate=result['engine_selection']['adequate']))
                if engine_id == 'rotax_912_ul' and part == 'p2':
                    report.locator('#tab-engine-fuel').screenshot(path=str(out / 'rotax-report.png'))
                    report.pdf(path=str(out / 'rotax-p2.pdf'), prefer_css_page_size=True, print_background=True)
                    (out / 'rotax-p2.html').write_text(response.text(), encoding='utf-8')
            print(engine_id + ': source data and three offline reports OK', flush=True)

        # Mobile users can operate the selector and see the source without page overflow.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.evaluate('async params => {loadProjectIntoForm({name:"Silnik — mobile",params}); await performCalculation();}',
                      dict(presets['motoglider_aos'], engine_fuel_mode='catalog', engine_model_id='rotax_912_uls'))
        navigate(page, 'tab-p1-p2')
        reveal_details(page.locator('#engineFuelPanel'))
        page.locator('#engine_fuel_point').select_option('continuous')
        page.locator('#applyEngineFuel').click()
        page.wait_for_function('currentResults.params.sfc === 285')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors, errors
        (out / 'results.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding='utf-8')
        browser.close()


if __name__ == '__main__':
    main()
