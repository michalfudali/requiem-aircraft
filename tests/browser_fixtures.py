"""One Playwright runtime per pytest session, shared by all browser modules."""
from pathlib import Path
import re
import os
import subprocess
import time

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


@pytest.fixture
def native_studio(request, chromium):
    """Drive a native OpenVSP backend from the usual Playwright interpreter.

    Opt in with BIPOL_OPENVSP_PYTHON pointing to a compatible Python interpreter.
    The child inherits the worker's isolated database paths, never personal stores.
    """
    executable = os.environ.get('BIPOL_OPENVSP_PYTHON')
    if not executable:
        pytest.skip('Set BIPOL_OPENVSP_PYTHON to run the native OpenVSP browser scenarios.')
    output = ROOT/'work/browser'/re.sub(r'[^a-zA-Z0-9_.-]', '_', request.node.name)
    output.mkdir(parents=True, exist_ok=True)
    ready = output/'native-ready.txt'
    ready.unlink(missing_ok=True)
    backend_directory = output/'backend'
    backend_directory.mkdir(exist_ok=True)
    code = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from app import app
from werkzeug.serving import make_server
server = make_server('127.0.0.1', 0, app, threaded=True)
ready = Path(sys.argv[1])
temporary = ready.with_suffix('.tmp')
temporary.write_text(str(server.server_port), encoding='ascii')
temporary.replace(ready)
server.serve_forever()
'''
    with (output/'native-server.log').open('w', encoding='utf8') as log:
        process = subprocess.Popen([executable, '-c', code, str(ready), str(ROOT)], cwd=backend_directory,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        context = None
        trace_started = False
        try:
            deadline = time.monotonic()+60
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.1)
            assert ready.exists(), 'Native backend did not start; see '+str(output/'native-server.log')
            base = 'http://127.0.0.1:'+ready.read_text(encoding='ascii')
            context = chromium.new_context(viewport={'width':1440,'height':1000}, accept_downloads=True)
            assert context.request.get(base+'/api/openvsp/status').json()['available'], 'Configured native backend is unavailable'
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            trace_started = True
            page = context.new_page(); errors=[]
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}') if response.status>=500 else None)
            page.set_default_timeout(20000)
            page.goto(base)
            page.wait_for_function('currentResults !== null', timeout=60000)
            yield page, base, output
            assert not errors, errors
        finally:
            if context:
                try:
                    if context.pages:
                        context.pages[0].screenshot(path=str(output/'last-page.png'),full_page=True)
                    if trace_started:
                        context.tracing.stop(path=str(output/'trace.zip'))
                finally:
                    context.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=10)


