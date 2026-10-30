"""
Kompleksowy test przeglądarkowy nowych funkcji:
- Przełącznik trybu dydaktycznego / konstrukcyjnego,
- Generator i wizualizator profilu 200 mm (SVG + tabela 25 stacji w trybie projektów P3),
- Audyt inżynierski (w tym aeroelastyczność/flater i zdatność akustyczna ICAO) oraz symulator obrony w panelu coursework,
- Wykres dopasowania (Matching Chart) i obwiednia Schrenka.
"""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, serve_in_process

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:5088')
parser.add_argument('--browser-path', default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process', action='store_true')
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    if args.in_process:
        serve_in_process(page, args.base_url)
    page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")

    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))

    print(f"Nawigacja do {args.base_url}...")
    page.goto(args.base_url)
    page.wait_for_function('currentResults?.submission_review?.signature', timeout=45000)
    print("Aplikacja załadowana pomyślnie.")

    # 1. TEST PRZEŁĄCZNIKA TRYBU DYDAKTYCZNEGO / KONSTRUKCYJNEGO
    print("1. Sprawdzanie przełącznika trybów pracy...")
    didactic_btn = page.locator('button[data-work-mode="didactic"]')
    construction_btn = page.locator('button[data-work-mode="construction"]')
    assert didactic_btn.count() > 0, "Brak przycisku trybu dydaktycznego"
    assert construction_btn.count() > 0, "Brak przycisku trybu konstrukcyjnego"

    construction_btn.click()
    page.wait_for_timeout(300)
    body_class = page.evaluate('document.body.className')
    assert 'mode-construction' in body_class, f"Oczekiwano mode-construction w body, otrzymano: {body_class}"

    didactic_btn.click()
    page.wait_for_timeout(300)
    body_class = page.evaluate('document.body.className')
    assert 'mode-didactic' in body_class, f"Oczekiwano mode-didactic w body, otrzymano: {body_class}"
    print("-> Przełącznik trybu dydaktycznego/konstrukcyjnego działa prawidłowo.")

    # 2. TEST AUDYTU INŻYNIERSKIEGO W ZAKŁADCE WYMAGAŃ (COURSEWORK)
    print("2. Sprawdzanie audytu inżynierskiego w zakładce Coursework...")
    navigate(page, 'tab-coursework')
    page.wait_for_timeout(600)

    audit_card = page.locator('#courseworkEngineeringAuditCard')
    assert audit_card.count() > 0, "Brak karty #courseworkEngineeringAuditCard"
    audit_items = page.locator('#courseworkAuditList .audit-item-card').count()
    print(f"-> Znaleziono {audit_items} pozycji audytu inżynierskiego")
    assert audit_items >= 6, f"Oczekiwano co najmniej 6 pozycji audytu, znaleziono {audit_items}"

    # Sprawdź obecność weryfikacji flatteru i hałasu w tekście audytu
    audit_text = page.locator('#courseworkAuditList').inner_text()
    assert 'flater' in audit_text.lower() or 'flatter' in audit_text.lower(), "Brak weryfikacji flatteru w audycie"
    assert 'hałas' in audit_text.lower() or 'akustyczn' in audit_text.lower() or 'icao' in audit_text.lower(), "Brak weryfikacji akustycznej w audycie"
    print("-> Weryfikacja flatteru i zdatności akustycznej ICAO obecna w audycie.")

    # Sprawdź symulator pytań na obronę
    quiz_card = page.locator('#courseworkDefenseQuestionsCard')
    assert quiz_card.count() > 0, "Brak karty #courseworkDefenseQuestionsCard"
    questions_count = page.locator('#courseworkDefenseQuestionsList details').count()
    print(f"-> Znaleziono {questions_count} pytań symulatora obrony")
    assert questions_count >= 4, f"Oczekiwano co najmniej 4 pytań, znaleziono {questions_count}"

    # 3. TEST ZAKŁADKI P3: PROFIL 200 MM I TABELA WSPÓŁRZĘDNYCH W TRYBIE PROJEKTÓW
    print("3. Sprawdzanie panelu P3 w trybie projektów i generatora profilu 200 mm...")
    page.evaluate("setPortalMode('projects'); selectSemesterProject('p3');")
    page.wait_for_timeout(600)

    fetch_btn = page.locator('#btn_fetch_airfoil')
    assert fetch_btn.count() > 0, "Brak przycisku #btn_fetch_airfoil"

    fetch_btn.click()
    page.wait_for_selector('#p3_airfoil_coords_tbody tr', timeout=10000)
    rows_count = page.locator('#p3_airfoil_coords_tbody tr').count()
    print(f"-> Liczba wierszy w tabeli profilu: {rows_count}")
    assert rows_count == 25, f"Oczekiwano 25 stacji pomiarowych, otrzymano {rows_count}"

    svg_content = page.locator('#p3_airfoil_svg_container svg').count()
    assert svg_content > 0, "Rysunek SVG profilu nie został wygenerowany"
    print("-> Wektorowy rysunek profilu 200 mm oraz tabela rzędnych wygenerowane prawidłowo.")

    # 4. TEST POWROTU DO TRYBU HOLISTYCZNEGO I WYKRESU DOPASOWANIA
    print("4. Sprawdzanie powrotu do trybu holistycznego i wykresu dopasowania...")
    page.evaluate("setPortalMode('holistic');")
    page.wait_for_timeout(300)
    navigate(page, 'tab-p1-p2')
    page.wait_for_timeout(600)

    matching_canvas = page.locator('#chartMatching')
    assert matching_canvas.count() > 0, "Brak canvasu #chartMatching w tab-p1-p2"
    print("-> Wykres dopasowania w tab-p1-p2 załadowany prawidłowo.")

    print("Błędy strony:", errors)
    assert len(errors) == 0, f"Wykryto błędy w konsoli: {errors}"
    print("WSZYSTKIE TESTY PRZEGLĄDARKOWE ZAKOŃCZONE SUKCESEM!")

    browser.close()
