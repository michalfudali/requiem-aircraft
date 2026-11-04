"""Task-focused workspace: navigation, editing, disclosures and offline reports."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, edit_inputs, reveal_details

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://127.0.0.1:5000')
parser.add_argument('--browser-path',default=None)
parser.add_argument('--output',default='work/declutter')
args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(args.base_url);page.wait_for_function('currentResults !== null')
    assert page.locator('.project-modal-backdrop.active,.wizard-backdrop.active').count()==0
    assert not page.locator('#designForm').is_visible()
    assert page.locator('.kpi-card:visible').count()==4
    assert page.locator('#studioSidebar nav > .studio-nav-item:visible').count()==7
    assert page.locator('#studioAircraft svg').count()==1
    assert page.locator('#studioAircraftProportions').input_value()=='concept'
    original_geometry=page.evaluate('JSON.stringify(currentResults.geometry)')
    page.locator('#studioAircraftProportions').select_option('calculated')
    assert page.locator('#studioAircraft svg').get_attribute('data-proportions')=='calculated'
    page.locator('#studioAircraftProportions').select_option('concept')
    assert page.evaluate('JSON.stringify(currentResults.geometry)')==original_geometry
    # The published CG visualizer is a separate panel below the original overview.
    assert page.evaluate("document.body.scrollHeight-document.getElementById('layoutBalanceVisualizer').getBoundingClientRect().height")<2000
    duplicates=page.evaluate("Object.entries([...document.querySelectorAll('[id]')].reduce((m,e)=>(m[e.id]=(m[e.id]||0)+1,m),{})).filter(([id,n])=>n>1).map(([id])=>id)")
    assert not duplicates,duplicates
    page.locator('.quiet-project-menu>summary').click()
    page.locator('#btnOpenProjectManager').click()
    page.wait_for_function("document.getElementById('projectManagerModalBackdrop').classList.contains('active')")
    page.locator('#closeProjectManagerBtn').click()
    page.wait_for_function("document.activeElement.matches('.quiet-project-menu>summary')")
    assert page.locator('#btnNewProjectWizard').is_visible()
    page.locator('#btnNewProjectWizard').click()
    page.locator('#closeWizardBtn').click()
    page.wait_for_function("document.activeElement.id === 'btnNewProjectWizard'")
    navigate(page,'tab-overview')
    page.screenshot(path=out/'overview-desktop.png',full_page=True,animations='disabled')
    print('DIRECT START, SEVEN NAV ITEMS, FOUR METRICS, NO DUPLICATE IDS: OK',flush=True)

    page.get_by_role('button',name='Edytuj założenia',exact=True).click()
    assert page.locator('#designForm').is_visible()
    assert not page.locator('#body_mod2').is_visible()
    header=page.locator('#accordion_mod2 .module-header')
    header.focus();page.keyboard.press('Enter');assert page.locator('#body_mod2').is_visible()
    page.keyboard.press('Space');assert not page.locator('#body_mod2').is_visible()
    page.locator('#studioParameterSearch').fill('rozpietosc')
    page.locator('#studioParameterResults button').first.click()
    page.wait_for_function("document.activeElement.id === 'wingspan_m'")
    assert page.locator('#body_mod2').is_visible()
    page.locator('#studioParameterSearch').fill('nieistniejacyparametr')
    assert 'Nie znaleziono' in page.locator('#studioParameterCount').inner_text()
    page.locator('#studioParameterSearch').fill('')
    page.locator('[data-input-section=mod4]').click()
    assert page.locator('#body_mod4').is_visible()
    field=edit_inputs(page,'aspect_ratio');field.fill('9.5');page.locator('#calcBtn').click()
    page.wait_for_function('currentResults.params.aspect_ratio === 9.5')
    page.locator('#lock_btn_aspect_ratio').click()
    page.wait_for_function("window.userLockedParams.has('aspect_ratio')")
    assert page.locator('#lock_btn_aspect_ratio').get_attribute('aria-pressed')=='true'
    page.wait_for_function("document.getElementById('openReportBtn').dataset.resultsStale === 'false'")
    field.fill('0');page.locator('#calcBtn').click()
    page.wait_for_function("document.getElementById('calculationStatus').classList.contains('is-error')")
    page.wait_for_function("document.getElementById('studioProjectHealth').dataset.state === 'error'")
    navigate(page,'tab-overview');assert page.locator('#workspaceNotice').is_visible()
    page.get_by_role('button',name='Sprawdź założenia').click()
    assert page.locator('#aspect_ratio').is_visible()
    assert page.evaluate('document.activeElement.id')=='aspect_ratio'
    page.locator('#aspect_ratio').fill('9.5');page.locator('#calcBtn').click()
    page.wait_for_function("document.getElementById('openReportBtn').dataset.resultsStale === 'false'")
    assert not page.locator('#workspaceNotice').is_visible()
    print('INPUT PAGE, KEYBOARD ACCORDIONS, LOCKS, VISIBLE ERROR RECOVERY: OK',flush=True)

    navigate(page,'tab-p3')
    assert not page.locator('#designForm').is_visible()
    assert page.locator('#tab-p3 > .quiet-disclosure[open]').count()==1
    assert not page.locator('#tab-p3 [data-quiet-explanation]').first.is_visible()
    page.locator('#tab-p3 [data-toggle-explanations]').click()
    assert page.locator('#tab-p3 [data-quiet-explanation]').first.is_visible()
    page.locator('#tab-p3 [data-toggle-explanations]').click()
    secondary=page.locator('#tab-p3 > .quiet-disclosure').nth(1)
    secondary.locator(':scope > summary').click();assert secondary.get_attribute('open') is not None
    print('SEPARATE ANALYSES AND SECONDARY RESULTS ON DEMAND: OK',flush=True)

    navigate(page,'tab-trends')
    assert page.locator('#trendMassChart').is_visible()
    assert not page.locator('#trendTimeChart').is_visible()
    assert not page.locator('#trendControls').is_visible()
    page.locator('#trendChartView').select_option('1');assert page.locator('#trendTimeChart').is_visible()
    page.locator('#trendResultsPanel-tab').focus();page.keyboard.press('ArrowRight')
    assert page.locator('#trendSelectionPanel-tab').get_attribute('aria-selected')=='true'
    assert page.locator('#trendControls').is_visible()
    page.locator('#trend_source').select_option('cado');page.locator('#trend_nearest_count').select_option('20')
    page.locator('#trendRecalculate').click()
    page.wait_for_function("currentResults.params.trend_source === 'cado' && currentResults.bipol_projects.p1.trend_analysis.selected_n === 20")
    page.locator('#trendResultsPanel-tab').click()
    print('ONE TREND CHART, KEYBOARD SUBTABS AND WORKING FILTERS: OK',flush=True)

    page.locator('#openReportBtn').click()
    assert page.locator('#tab-reports').is_visible()
    assert not page.locator('#studioMeta_student_name').is_visible()
    reveal_details(page.locator('#studioMeta_student_name'));page.locator('#studioMeta_student_name').fill('Test czytelnego interfejsu')
    for checkbox in page.locator('[name=studio-report-section]').all():checkbox.set_checked(checkbox.input_value()=='p1')
    with page.expect_download() as download:page.locator('[data-studio-action=download-report]').click()
    download.value.save_as(out/'raport.html');html=(out/'raport.html').read_text(encoding='utf-8')
    assert 'cdn.jsdelivr.net' not in html
    assert 'data:font/woff2;base64,' in html
    offline=browser.new_context(offline=True);report=offline.new_page()
    report.on('pageerror',lambda e:errors.append('REPORT: '+str(e)))
    report.set_content(html,wait_until='load');report.evaluate('document.fonts.ready')
    assert report.locator('.katex').count()>0
    assert report.locator('.katex-error').count()==0
    assert report.locator('.katex-mathml math').count()>0
    offline.close()
    print('REPORT METADATA AND OFFLINE MATH WITH EMBEDDED FONTS: OK',flush=True)

    for width in [1440,1024,768,390,320]:
        page.set_viewport_size({'width':width,'height':950})
        for target in ['tab-overview','tab-inputs','tab-trends','tab-p3']:
            navigate(page,target)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(width,target)
            assert page.locator('#projectSwitcherSelect').bounding_box()['width']>=130,(width,target)
            if width in [1440,390]:page.screenshot(path=out/f'{target}-{width}.png',full_page=True,animations='disabled')
    page.locator('#studioMenuToggle').click()
    page.keyboard.press('Escape')
    assert page.locator('#studioMenuToggle').get_attribute('aria-expanded')=='false'
    assert page.evaluate('document.activeElement.id')=='studioMenuToggle'
    assert not errors,errors
    print('RESPONSIVE 320–1440, MOBILE MENU AND NO JAVASCRIPT ERRORS: OK',flush=True)
    browser.close()
