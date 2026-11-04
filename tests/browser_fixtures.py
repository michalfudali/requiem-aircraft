"""One Playwright runtime per pytest session, shared by all browser modules."""
from pathlib import Path
import re

import pytest
from browser_live_server import live_server

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


