"""Render actual P1–P6 reports offline for every design class; check the student's calculations."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5016')
    parser.add_argument('--output', default='work/unified-trends')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    findings = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        api = browser.new_context()
        presets = api.request.get(args.base_url + '/api/presets').json()
        projects = {key: presets[key] for key in ('ga_trainer', 'regional_turboprop', 'vlj_jet',
                                                   'motoglider_aos', 'glider_pw5', 'uav_tactical')}
        projects['jet_transport'] = dict(presets['vlj_jet'], aircraft_type='jet_transport',
                                         category='cs25_transport', n_pax=120, range_km=3500,
                                         aspect_ratio=10, cruise_altitude_m=10000,
                                         cruise_speed_kmh=750, v_stall_kmh=200)
        errors = []
        offline = browser.new_context(offline=True, viewport={'width': 1100, 'height': 900})
        page = offline.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        for name, params in projects.items():
            for part in ('p1', 'p2', 'p3', 'p4', 'p5', 'p6'):
                response = api.request.post(args.base_url + '/report/project/' + part, data=params, timeout=90000)
                assert response.ok, (name, part, response.status, response.text()[:300])
                html = response.text()
                page.set_content(html, wait_until='load')
                page.evaluate('document.fonts.ready')
                assert page.locator('.katex').count() > 10, (name, part)
                assert not page.locator('.katex-error').count(), (name, part, page.locator('.katex-error').all_text_contents())
                overflow = page.evaluate('''() => [...document.querySelectorAll('table,figure,.equation')].filter(el => {
                    const r=el.getBoundingClientRect(),doc=document.querySelector('.document').getBoundingClientRect();
                    return r.right>doc.right-20 || r.left<doc.left;
                }).map(el=>({tag:el.tagName,id:el.id,width:el.getBoundingClientRect().width,text:el.innerText.slice(0,90)}))''')
                assert not overflow, (name, part, overflow)
                math_overflow = page.evaluate('''() => [...document.querySelectorAll('.formula')]
                    .filter(el=>el.scrollWidth>el.clientWidth+3).map(el=>el.innerText.slice(0,100))''')
                assert not math_overflow, (name, part, math_overflow)
                if part == 'p1':
                    assert page.locator('[data-trend-average]').count() == 8
                    assert page.locator('[data-trend-choice]').count() <= 4
                    assert 'Proporcje geometryczne projektu na tle' not in page.locator('body').inner_text()
                    assert page.locator('#tab-sample tbody tr').count() == page.locator('#tab-sample-averages tbody tr').count()
                    if name == 'motoglider_aos':
                        page.locator('#tab-trend-means').screenshot(path=str(out / 'motoglider-required-means.png'))
                        page.pdf(path=str(out / 'motoglider-p1.pdf'), prefer_css_page_size=True, print_background=True)
                        (out / 'motoglider-p1.html').write_text(html, encoding='utf-8')
                findings.append({'project': name, 'part': part, 'formulae': page.locator('.katex-display').count(),
                                 'calculations': page.locator('[data-calc]').count(), 'overflow': overflow})
            print(name + ': six reports, offline formulae and A4 layout OK', flush=True)
        assert not errors, errors
        (out / 'reports.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding='utf-8')
        offline.close()
        api.close()
        browser.close()


if __name__ == '__main__':
    main()
