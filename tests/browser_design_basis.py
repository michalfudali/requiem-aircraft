"""Topic-driven wizard, immutable dependent fields and saved independent assumptions."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, edit_inputs

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://127.0.0.1:5010')
parser.add_argument('--browser-path',default='/usr/bin/chromium')
args=parser.parse_args();out=Path('work/design-basis');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url);page.wait_for_function('currentResults!==null')
    def wizard(edit=False):
        page.locator('.quiet-project-menu>summary').click()
        page.locator('#btnEditProjectWizard' if edit else '#btnNewProjectWizard').click()
    def step(number):page.locator(f'.wizard-step-tab[data-step="{number}"]').click()
    def finish():
        step(5);page.locator('#wizFinishBtn').click()
        page.wait_for_function('!document.getElementById("projectWizardBackdrop").classList.contains("active")')
    wizard();page.locator('#wiz_topic').select_option('topic_7')
    page.locator('#wiz_basis_range_km').fill('800')
    assert page.locator('#wiz_range_km').input_value()=='800'
    assert page.locator('#wiz_lock_range_km').is_checked()
    assert page.locator('#wiz_wing_input_mode').input_value()=='span_aspect'
    assert not page.locator('#wiz_wing_area_m2').is_editable()
    page.locator('#wiz_wingspan_m').fill('22');page.locator('#wiz_aspect_ratio').fill('25')
    assert float(page.locator('#wiz_wing_area_m2').input_value())==19.36
    page.locator('#wiz_wing_input_mode').select_option('span_area');page.locator('#wiz_wing_area_m2').fill('22')
    assert float(page.locator('#wiz_aspect_ratio').input_value())==22
    assert not page.locator('#wiz_aspect_ratio').is_editable()
    page.locator('#wiz_wing_input_mode').select_option('span_aspect');page.locator('#wiz_aspect_ratio').fill('25')
    # JAR-22: a powered sailplane carries no cargo; its payload is the second occupant.
    assert page.locator('#wiz_payload_input_mode option[value="total"]').is_disabled()
    assert not page.locator('#wiz_m_cargo').is_visible()
    page.locator('#wiz_n_pax').fill('1');page.locator('#wiz_m_pax').fill('90')
    page.locator('#wiz_name').fill('Motoszybowiec 22 m')
    step(2);page.locator('#wiz_range_km').fill('650')
    assert page.locator('#wiz_basis_range_km').input_value()=='650'
    page.get_by_role('button',name='Automatycznie zasugeruj typowe osiągi').click()
    assert page.locator('#wiz_range_km').input_value()=='650'
    step(1)
    assert page.locator('#wiz_basis_range_km').input_value()=='650'
    step(2)
    step(3);page.locator('#wiz_power_input_mode').select_option('fixed');page.locator('#wiz_engine_power_kw').fill('60')
    finish()
    page.wait_for_function('currentResults.params.name==="Motoszybowiec 22 m"')
    r=page.evaluate('currentResults')
    assert r['geometry']['wing']['b']==22 and r['geometry']['wing']['AR']==25
    assert r['mass']['m_payload']==90 and r['params']['m_cargo']==0 and r['sizing']['design_point']['power_kw']==60
    assert r['params']['range_km']==650 and 'range_km' in r['params']['locked_params']
    print('TOPIC >20 M, SELECTED GEOMETRY, PAYLOAD AND REAL FIXED ENGINE POWER: OK',flush=True)
    page.reload();page.wait_for_function('currentResults?.params?.name==="Motoszybowiec 22 m"')
    assert not edit_inputs(page,'wing_area_m2').is_editable()
    assert not page.locator('#m_cargo').is_visible()
    assert page.locator('#wing_input_mode').input_value()=='span_aspect'
    assert page.locator('#payload_input_mode').input_value()=='seats'
    assert page.evaluate("window.userLockedParams.has('engine_power_kw')")
    # JAR 22.1(a)(3): at most two persons on board — the wizard flags a third one with the paragraph.
    wizard(True);page.locator('#wiz_n_pax').fill('2')
    assert 'JAR 22.1(a)(3)' in page.locator('#wiz_n_pax').locator('xpath=ancestor::div[contains(@class,"input-group")]').inner_text()
    assert page.locator('#wiz_n_pax').evaluate('(el)=>el.classList.contains("regulation-violation")')
    print('SAVED BASIS AND LOCKS, NO CARGO IN A SAILPLANE, SEAT LIMIT FROM JAR-22: OK',flush=True)
    step(1);page.locator('#wiz_n_pax').fill('0')
    step(3);page.locator('#wiz_engine_type').select_option('none')
    for key in ('engine_location','sfc','engine_power_kw','prop_efficiency'):
        assert not page.locator('#wiz_'+key).is_visible(),key
    assert page.locator('#wiz_engine_location').input_value()=='none'
    step(2)
    assert not page.locator('#wiz_takeoff_run_m').is_visible()
    assert not page.locator('#wiz_climb_rate_ms').is_visible()
    finish();page.wait_for_function('currentResults.params.engine_type==="none"')
    assert page.evaluate('currentResults.params.engine_location')=='none'
    assert page.evaluate('currentResults.mass.m_fuel')==0
    wizard(True);step(3);page.locator('#wiz_engine_type').select_option('prop')
    assert page.locator('#wiz_engine_location').is_visible()
    assert page.locator('#wiz_engine_location').input_value()!='none'
    assert page.locator('#wiz_sfc').is_editable()
    finish();page.wait_for_function('currentResults.params.engine_type==="prop"')
    print('NO ENGINE MEANS NO ENGINE QUESTIONS; POWERED FIELDS RESTORE CORRECTLY: OK',flush=True)
    wizard(True);step(4);page.locator('#wiz_wing_planform').select_option('rectangular')
    assert not page.locator('#wiz_taper_ratio').is_editable()
    assert page.locator('#wiz_taper_ratio').input_value()=='1'
    page.locator('#wiz_wing_planform').select_option('trapezoidal');assert page.locator('#wiz_taper_ratio').is_editable()
    for width in (1440,768,390,320):
        page.set_viewport_size({'width':width,'height':900});step(1)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
        assert page.locator('.wizard-body').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'),width
    page.screenshot(path=out/'wizard-mobile.png',full_page=True)
    page.locator('#closeWizardBtn').click();page.set_viewport_size({'width':1440,'height':1000})
    assert not errors,errors
    print('PLANFORM-DEPENDENT TAPER, MOBILE WIZARD 320–1440, NO JAVASCRIPT ERRORS: OK',flush=True)
    browser.close()
