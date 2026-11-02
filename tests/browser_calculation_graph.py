"""Native Chrome: graph navigation, actual maths, gestures and fresh snapshots."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from browser_helpers import navigate,edit_inputs,launch_chromium
from browser_live_server import live_server
from calculations.presets import AIRCRAFT_PRESETS

OUT=ROOT/'work'/'headless-calculation-graph';OUT.mkdir(parents=True,exist_ok=True)
BASE='http://graph.test'


def ready(page):
    page.wait_for_function("currentResults!==null&&!document.querySelector('#calcBtn').disabled&&currentResults.calculation_graph",timeout=60000)


def search(page,key):
    page.locator('#calculationGraphSearch').fill(key)
    page.locator(f'[data-graph-match="{key}"]').click()
    page.wait_for_function('(key)=>BipolCalculationTree.state.selected===key',arg=key)


with live_server(OUT) as BASE, sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    context=browser.new_context(viewport=dict(width=1600,height=1100),accept_downloads=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE);ready(page);navigate(page,'tab-calculation-tree')
    page.locator('.calc-graph-node.is-project').first.wait_for()
    math_errors=page.evaluate('''()=>currentResults.calculation_graph.nodes.flatMap(n=>[n.formula,n.substitution_tex,n.tex].filter(Boolean).map(t=>{try{katex.renderToString(t,{throwOnError:true});return null}catch(e){return n.id+': '+e.message}})).filter(Boolean)''')
    assert math_errors==[],math_errors
    assert page.locator('.calc-graph-node.is-project').count()==7
    assert page.locator('.calc-graph-edge').count()>10
    page.locator('#calculationGraphWorkspace').screenshot(path=str(OUT/'overview.png'))
    # Pan via real mouse. Keep page position fixed and do not activate nodes.
    vp=page.locator('#calculationTreeRoot');box=vp.bounding_box()
    before=page.evaluate('({...BipolCalculationTree.state.camera})')
    page.mouse.move(box['x']+22,box['y']+220);page.mouse.down()
    page.mouse.move(box['x']+182,box['y']+275,steps=12);page.mouse.up()
    page.wait_for_timeout(50)
    after=page.evaluate('BipolCalculationTree.state.camera')
    assert abs(after['x']-before['x']-160)<1 and abs(after['y']-before['y']-55)<1
    assert page.locator('#calculationGraphInspector').is_hidden()
    assert abs(vp.bounding_box()['y']-box['y'])<1
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.wheel(0,-300)
    page.wait_for_function('(s)=>BipolCalculationTree.state.camera.scale>s',arg=after['scale'])
    print('mouse pan, wheel zoom and graph isolation OK',flush=True)
    # Search exact symbol, display real formula and numerical substitutions.
    search(page,'S')
    assert page.locator('#calculationGraphScope').input_value()=='path'
    assert page.locator('#calculationGraphDetail .katex').count()>=3
    assert not page.locator('.katex-error').count()
    assert 'Podstawienie liczb' in page.locator('#calculationGraphDetail').inner_text()
    node=page.evaluate("BipolCalculationTree.state.model.byId.get('S')")
    assert node['value']==page.evaluate('currentResults.geometry.wing.S')
    assert node['tex'] in page.locator('#calculationGraphDetail .is-worked annotation').all_text_contents()
    assert page.locator('.calc-graph-node.is-cycle').count()>0
    page.locator('#calculationGraphWorkspace').screenshot(path=str(OUT/'area-path.png'))
    # Jump to an actual dependency and then to full mass iteration equations.
    page.locator('#calculationGraphDetail .calc-graph-dependencies [data-graph-entry="m0"]').first.click()
    assert page.evaluate('BipolCalculationTree.state.selected')=='m0'
    method=page.evaluate('currentResults.mass.primary_method');key='@mass_iteration_'+method
    search(page,key)
    assert page.locator('[data-graph-iteration]').count()>=2
    page.locator('[data-graph-iteration] > summary').first.click()
    page.wait_for_function("document.querySelector('[data-graph-iteration] .katex')!==null")
    expected=page.evaluate('(key)=>BipolCalculationTree.state.model.byId.get(key).iterations[0].steps.length',key)
    assert page.locator('[data-graph-iteration]').first.locator('.katex').count()==expected
    assert not page.locator('.katex-error').count()
    with page.expect_download() as download:page.locator('[data-graph-action=latex]').click()
    tex=OUT/'iteration.tex';download.value.save_as(tex)
    text=tex.read_text(encoding='utf-8');assert '\\documentclass' in text and '\\subsubsection*{Iteracja 2}' in text
    print('actual sheet formulas, numerical values, feedback and every iteration OK',flush=True)
    # Keyboard and full graph / minimap / project scopes.
    page.locator('[data-graph-action=close]').click();vp.focus()
    x=page.evaluate('BipolCalculationTree.state.camera.x');page.keyboard.press('ArrowRight')
    assert page.evaluate('BipolCalculationTree.state.camera.x')==x-60
    page.keyboard.press('Home')
    page.locator('#calculationGraphScope').select_option('all')
    assert page.locator('.calc-graph-node').count()>200
    assert page.locator('#calculationGraphMinimap').is_visible()
    page.locator('#calculationGraphMinimap').click(position=dict(x=50,y=50))
    for scope in ['p1','p2','p3','p4','p5','p6']:
        page.locator('#calculationGraphScope').select_option(scope)
        assert page.locator('.calc-graph-node').count()>5
        assert page.evaluate('BipolCalculationTree.state.camera.scale')>=.8
    print('keyboard, full graph, minimap and all project scopes OK',flush=True)
    # Stale exports are blocked immediately on input edits; recalc refreshes sheet.
    range_input=edit_inputs(page,'range_km');old=float(range_input.input_value());range_input.fill(str(old+100))
    assert page.evaluate('BipolCalculationTree.state.stale')
    assert page.locator('[data-graph-action=latex]').is_disabled()
    page.locator('#calcBtn').click();ready(page);navigate(page,'tab-calculation-tree')
    page.wait_for_function('BipolCalculationTree.state.model&&!BipolCalculationTree.state.stale')
    assert page.locator('#calculationGraphStale').is_hidden()
    assert page.locator('[data-graph-action=latex]').is_enabled()
    # New project: no old values survive; native profile differs for unpowered / jet.
    for kind in ['glider_pw5','vlj_jet']:
        params=dict(AIRCRAFT_PRESETS[kind]);name='Graf '+kind;params['name']=name
        file=OUT/(kind+'.json');file.write_text(json.dumps(dict(name=name,params=params)),encoding='utf-8')
        page.locator('#projectImportFileInput').set_input_files(file)
        page.wait_for_function('(name)=>currentResults?.params?.name===name+" (Import)"&&!document.querySelector("#calcBtn").disabled',arg=name,timeout=60000)
        navigate(page,'tab-calculation-tree');page.wait_for_function('BipolCalculationTree.state.view!==null')
        search(page,'m0');assert not page.locator('.katex-error').count()
        assert page.evaluate("BipolCalculationTree.state.model.byId.get('m0').value")==page.evaluate('currentResults.mass.m0')
    assert not errors,errors
    print('freshness, recalculation and project isolation across prop/glider/jet OK',flush=True)
    context.close()
    # Real touch events and a narrow viewport.
    mobile=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
    m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)))
    m.goto(BASE);ready(m);navigate(m,'tab-calculation-tree');m.locator('.calc-graph-node.is-project').first.wait_for()
    m.locator('#calculationGraphWorkspace').scroll_into_view_if_needed();rect=m.locator('#calculationTreeRoot').bounding_box()
    cdp=mobile.new_cdp_session(m);before=m.evaluate('({...BipolCalculationTree.state.camera})')
    x=rect['x']+60;y=rect['y']+180
    cdp.send('Input.dispatchTouchEvent',dict(type='touchStart',touchPoints=[dict(x=x,y=y)]))
    cdp.send('Input.dispatchTouchEvent',dict(type='touchMove',touchPoints=[dict(x=x+80,y=y+50)]))
    cdp.send('Input.dispatchTouchEvent',dict(type='touchEnd',touchPoints=[]));m.wait_for_timeout(80)
    after=m.evaluate('BipolCalculationTree.state.camera');assert after['x']>before['x']+60
    pinch_before=after['scale'];mid_x=rect['x']+180;mid_y=rect['y']+230
    cdp.send('Input.dispatchTouchEvent',dict(type='touchStart',touchPoints=[dict(id=1,x=mid_x-30,y=mid_y),dict(id=2,x=mid_x+30,y=mid_y)]))
    cdp.send('Input.dispatchTouchEvent',dict(type='touchMove',touchPoints=[dict(id=1,x=mid_x-65,y=mid_y),dict(id=2,x=mid_x+65,y=mid_y)]))
    cdp.send('Input.dispatchTouchEvent',dict(type='touchEnd',touchPoints=[]));m.wait_for_timeout(80)
    assert m.evaluate('BipolCalculationTree.state.camera.scale')>pinch_before*1.4
    search(m,'S');assert m.locator('#calculationGraphInspector').is_visible()
    assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert not m.locator('.katex-error').count()
    m.locator('#calculationGraphWorkspace').screenshot(path=str(OUT/'mobile.png'))
    assert not errors,errors
    print('mobile touch pan, pinch zoom, equations and width OK',flush=True)
    mobile.close();browser.close()
