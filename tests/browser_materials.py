"""Real HTTP: primary course PDFs, ML1 link and narrow materials navigation.

Pass --materials with the user's local scraped_materials directory. The test
reads it and saves downloads only in this checkout's ignored work directory.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers import launch_chromium, navigate
from browser_live_server import live_server

OUT = Path(__file__).resolve().parents[1] / 'work/headless-materials'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials', type=Path, required=True)
    args = parser.parse_args()
    materials = args.materials.resolve()
    assert (materials / 'mechanika_lotu').is_dir() and (materials / 'bipol').is_dir()
    with live_server(OUT) as base, sync_playwright() as p:
        from app import app
        app.config['MATERIALS_DIR'] = str(materials)
        browser = launch_chromium(p, headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=1000), accept_downloads=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base)
        page.wait_for_function('currentResults && !document.querySelector("#calcBtn").disabled', timeout=90000)
        navigate(page, 'tab-faculty-docs')
        page.locator('#scrapedMlFiles a').first.wait_for()
        counts = {kind: page.locator(selector + ' a').count() for kind, selector in
                  [('BIPOL', '#scrapedBipolFiles'), ('ML1', '#scrapedMlFiles')]}
        assert min(counts.values()) > 0
        checked = []
        for selector in ['#scrapedMlFiles a', '#scrapedBipolFiles a']:
            link = page.locator(selector).first
            href = link.get_attribute('href')
            response = page.request.get(base + href)
            assert response.ok and response.body().startswith(b'%PDF')
            checked.append(dict(url=href, status=response.status, bytes=len(response.body())))
        with page.expect_download(timeout=30000) as download:
            page.locator('#scrapedMlFiles a').first.click()
        download.value.save_as(OUT / 'primary-ml1.pdf')
        assert (OUT / 'primary-ml1.pdf').read_bytes().startswith(b'%PDF')
        for width in [1440, 390, 320]:
            page.set_viewport_size(dict(width=width, height=950))
            navigate(page, 'tab-faculty-docs')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
        page.screenshot(path=str(OUT / 'materials-mobile.png'))
        for target in ['tab-methods', 'tab-coursework', 'tab-bipol-guide']:
            navigate(page, target)
            assert page.locator('#' + target).is_visible(), target
        assert not errors, errors
        (OUT / 'summary.json').write_text(json.dumps(dict(counts=counts, pdf=checked, errors=errors), ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: local primary sources', counts, 'PDF download and learning views at 1440/390/320 px', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
