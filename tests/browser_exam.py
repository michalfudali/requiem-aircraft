"""Real browser: exam problem panel — letters to data, solution steps, answer check, charts, phone width."""
import argparse
import json
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process',action='store_true',help='serve the Flask app inside the test, without a server')
parser.add_argument('--screenshot',default='')
args=parser.parse_args()


def open_exam(page):
    page.evaluate("document.getElementById('learningNavigation').open = true")
    page.click('[data-studio-nav="tab-exam"]')
    page.wait_for_selector('#tab-exam.active', timeout=5000)


with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True)
    for width in (1400,390):
        page=browser.new_page(viewport={'width':width,'height':1000})
        page.clock.set_fixed_time('2026-10-31T10:00:00')
        if args.in_process:serve_in_process(page,args.base_url)
        page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true'); if (!sessionStorage.getItem('exam_clean')) { localStorage.removeItem('bipol_exam_v1'); localStorage.removeItem('bipol_course_group_v1'); localStorage.removeItem('bipol_quiz_v1'); localStorage.removeItem('bipol_quiz_v1_lectures'); sessionStorage.setItem('exam_clean','1'); }")
        errors,posts=[],[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.on('request',lambda r: posts.append(r.post_data) if '/api/exam/' in r.url else None)
        page.goto(args.base_url)
        page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
        if width<1100:page.click('#studioMenuToggle')
        open_exam(page)

        page.fill('#examFirst','Michał')
        page.fill('#examLast','Fudali')
        assert page.input_value('#examX')=='6' and page.input_value('#examY')=='6',(page.input_value('#examX'),page.input_value('#examY'))
        page.fill('#examLast','Kowalska-Nowak')
        assert page.input_value('#examY')=='13'
        page.fill('#examY','7')
        page.click('#examForm button[type=submit]')
        page.wait_for_selector('#examResult:not([hidden]) #examSteps details',timeout=10000)

        # Do serwera trafiają tylko liczby liter.
        assert posts and json.loads(posts[-1])=={'x':6,'y':7},posts
        assert 'Michał' not in ''.join(posts)
        data=page.inner_text('#examData')
        assert '1300' in data.replace('\xa0','').replace(' ','') and 'commuter' in data,data

        # Kroki zwinięte do czasu „Rozwiń wszystko”; wzory złożone przez KaTeX.
        assert page.evaluate("[...document.querySelectorAll('#examSteps details')].every(d => !d.open)")
        page.click('[data-exam-expand="open"]')
        math=page.evaluate("({katex: document.querySelectorAll('#examSteps .katex').length, errors: document.querySelectorAll('#examSteps .katex-error').length})")
        assert math['katex']>60 and math['errors']==0,math

        # Sprawdzenie własnych wyników: zgodny S, błędne n_max.
        answers=page.evaluate("fetch('/api/exam/wing-loads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x:6,y:7})}).then(r=>r.json()).then(r=>r.answers)")
        page.fill('#examCheck_S',f"{answers['S']:.2f}".replace('.',','))
        page.fill('#examCheck_n_max','3,0')
        page.click('#examCheck button[type=submit]')
        assert '✓' in page.inner_text('[data-exam-verdict="S"]')
        assert 'rozwiązanie: 3,80' in page.inner_text('[data-exam-verdict="n_max"]')
        assert 'Zgodnych wyników: 1 z 2' in page.inner_text('#examCheckSummary')

        # Wykresy: obwiednia na płótnie, rozkład c_z oraz T i M w SVG; tabela 4 pasków.
        page.wait_for_timeout(200)
        painted=page.evaluate("""(() => { const c = document.getElementById('examEnvelopeCanvas');
          const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
          for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return {n, w: c.clientWidth}; })()""")
        assert painted['n']>2000 and painted['w']>250,painted
        assert page.locator('#examSchrenkChart svg rect.exam-bar').count()==4
        assert page.locator('#examShearChart svg polyline').count()>=2 and page.locator('#examMomentChart svg polyline').count()>=2
        assert page.locator('#examSchrenkTable tbody tr').count()==4 and page.locator('#examLoadTable tbody tr').count()==4
        assert 'bez paliwa' in page.inner_text('#examNotes')

        overflow=page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        assert overflow<=1,f'poziome przewijanie strony: {overflow}px'

        # Terminy oddania z regulaminu: 31.10.2026, P2 w tygodniu 5 (śr. 4.11 / pt. 6.11).
        page.evaluate("document.getElementById('learningNavigation').open = true")
        if width<1100:page.click('#studioMenuToggle')
        page.click('[data-studio-nav="tab-coursework"]')
        state=lambda key: page.inner_text(f'#courseworkSchedule [data-schedule="{key}"] [data-schedule-state]')
        assert state('p2')=='za 4–6 dni' and 'termin minął 8 dni temu'==state('p1'),(state('p1'),state('p2'))
        page.select_option('#courseworkGroup','1')
        assert state('p2')=='za 4 dni' and state('p1')=='termin minął 10 dni temu',(state('p1'),state('p2'))
        assert page.locator('#courseworkSchedule [data-schedule-head="friday"]').is_hidden()
        assert 'coursework-next' in page.get_attribute('#courseworkSchedule [data-schedule="p2"]','class')
        assert page.evaluate("localStorage.getItem('bipol_course_group_v1')")=='1'
        assert page.inner_text('#studioDeadlineText')=='P2 · Studium wykonalności — śr. 04.11 (za 4 dni)',page.inner_text('#studioDeadlineText')

        # Zejściówka z wykładu 12: dwa pytania, zegar 15 minut, odpowiedzi wzorcowe i samoocena.
        if width<1100:page.click('#studioMenuToggle')
        page.click('[data-studio-nav="tab-quiz"]')
        page.click('[data-quiz-range="none"]')
        page.check('#quizLectures input[value="w12"]')
        page.select_option('#quizCount','2')
        page.click('#quizDraw')
        items=page.locator('#quizItems .quiz-item')
        assert items.count()==2 and page.inner_text('#quizClock')=='15:00'
        assert all(i.startswith('w12_') for i in page.eval_on_selector_all('#quizItems .quiz-item','els => els.map(e => e.dataset.quizId)'))
        assert page.locator('#quizItems .quiz-model').first.is_hidden()
        page.click('#quizReveal')
        assert page.locator('#quizItems .quiz-model').first.is_visible()
        page.locator('#quizItems .quiz-item').first.locator('[data-quiz-grade="known"]').click()
        assert page.inner_text('[data-quiz-progress="w12"]').startswith('1/')
        assert 'Umiesz 1 z' in page.inner_text('#quizSummary')
        if width>1100:
            # Arkusz do druku: pytania wykładu 12, odpowiedzi od nowej strony.
            page.evaluate("window.__open = window.open; window.open = () => { const w = window.__open('about:blank', '_blank'); w.print = () => {}; return w; }")
            with page.context.expect_page() as popup:
                page.click('#quizPrint')
            sheet=popup.value.content()
            assert sheet.count('<li>')==16 and 'Odpowiedzi wzorcowe' in sheet and 'break-before:page' in sheet
            popup.value.close()

        # Po przeładowaniu zostają same liczby liter, bez imienia i nazwiska; zostaje też postęp zejściówek.
        page.reload()
        page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
        stored=page.evaluate("localStorage.getItem('bipol_exam_v1')")
        assert json.loads(stored)=={'x':6,'y':7} and page.input_value('#examFirst')=='',stored
        assert page.inner_text('[data-quiz-progress="w12"]').startswith('1/')
        assert page.evaluate("[...document.querySelectorAll('#quizLectures input:checked')].map(i => i.value)")==['w12']

        if args.screenshot and width==1400:
            if width<1100:page.click('#studioMenuToggle')
            open_exam(page)
            page.click('#examForm button[type=submit]')
            page.wait_for_selector('#examResult:not([hidden]) #examSteps details',timeout=10000)
            page.click('[data-exam-expand="open"]')
            page.wait_for_timeout(300)
            page.screenshot(path=args.screenshot,full_page=True)
        assert not errors,errors
        page.close()
    browser.close()
print('OK: zadanie kolokwialne, terminy oddania i zejściówki — 1400 i 390 px')
