"""Shared navigation helpers for the focused workspace UI."""
def launch_chromium(playwright, **options):
    """Use an explicit browser, installed Chrome, or Playwright's Chromium."""
    import os
    from pathlib import Path
    explicit = os.environ.get('BIPOL_BROWSER_PATH')
    if explicit:
        return playwright.chromium.launch(executable_path=explicit, **options)
    installed = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    if installed.is_file():
        return playwright.chromium.launch(executable_path=str(installed), **options)
    return playwright.chromium.launch(**options)


def reveal_details(locator):
    for body in locator.locator('xpath=ancestor::div[contains(@class,"module-body") and contains(@class,"collapsed")]').all():
        body.locator('xpath=preceding-sibling::*[1]').click()
    for details in locator.locator('xpath=ancestor::details').all():
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()


def navigate(page, target):
    menu=page.locator('#studioMenuToggle')
    if page.viewport_size['width']<=1100 and menu.get_attribute('aria-expanded')!='true':
        menu.click()
    button=page.locator(f'[data-studio-nav="{target}"]')
    reveal_details(button)
    button.click()


def edit_inputs(page, field):
    navigate(page,'tab-inputs')
    locator=page.locator('#'+field)
    bodies=locator.locator('xpath=ancestor::div[contains(@class,"module-body")]')
    if bodies.count() and 'collapsed' in (bodies.first.get_attribute('class') or ''):
        bodies.first.locator('xpath=preceding-sibling::*[1]').click()
    if not locator.is_visible():page.locator('#modeAdvancedBtn').click()
    return locator


def serve_in_process(page, base_url):
    """Answer requests to base_url from the Flask app itself, without a running server."""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import app
    client=app.test_client()
    def handle(route):
        request=route.request
        response=client.open(request.url[len(base_url):] or '/',method=request.method,data=request.post_data_buffer,
                             headers={k:v for k,v in request.headers.items() if k.lower() in ('content-type','accept')})
        route.fulfill(status=response.status_code,body=response.get_data(),
                      headers={k:v for k,v in response.headers.items() if k.lower()!='content-length'})
    page.route(base_url.rstrip('/')+'/**',handle)
