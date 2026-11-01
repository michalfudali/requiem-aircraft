"""
Kompleksowy test przeglądarkowy dla Modern UI i Dark Mode:
- Przełączanie motywu (jasny / ciemny) za pomocą przycisku w navbarze i skrótu Alt+T,
- Paleta poleceń i szybkie wyszukiwanie parametrów (Ctrl+K),
- Monitor stanu synchronizacji projektu i szybkie przeliczanie (Ctrl+Enter),
- Nakładka skrótów klawiszowych (?),
- Sprawdzenie braku błędów JS w konsoli przeglądarki.
"""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:5088')
parser.add_argument('--browser-path', default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process', action='store_true', default=True)
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

    # 1. Sprawdzenie obecności kontrolek Modern UI w pasku nawigacyjnym
    print("1. Sprawdzanie elementów paska nawigacyjnego...")
    search_btn = page.locator('#btnNavSearch')
    recalc_pill = page.locator('#navRecalcPill')
    theme_btn = page.locator('#themeToggleBtn')
    shortcuts_btn = page.locator('#btnShortcutsNav')

    assert search_btn.count() == 1, "Brak przycisku wyszukiwania #btnNavSearch"
    assert recalc_pill.count() == 1, "Brak wskaźnika synchronizacji #navRecalcPill"
    assert theme_btn.count() == 1, "Brak przełącznika motywu #themeToggleBtn"
    assert shortcuts_btn.count() == 1, "Brak przycisku skrótów #btnShortcutsNav"
    print("-> Wszystkie kontrolki nawigacji są obecne.")

    # 2. Test przełączania trybu ciemnego (Dark Mode)
    print("2. Test przełączania motywu ciemnego...")
    initial_theme = page.evaluate("document.documentElement.getAttribute('data-theme') || 'light'")
    print(f"-> Początkowy motyw: {initial_theme}")

    # Kliknięcie w przycisk motywu
    theme_btn.click()
    page.wait_for_timeout(200)
    new_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
    expected_theme = 'dark' if initial_theme != 'dark' else 'light'
    assert new_theme == expected_theme, f"Oczekiwano motywu {expected_theme}, otrzymano: {new_theme}"
    saved_theme = page.evaluate("localStorage.getItem('bipol_theme')")
    assert saved_theme == expected_theme, f"Brak poprawnego zapisu w localStorage: {saved_theme}"
    print(f"-> Pomyślnie przełączono na motyw: {new_theme}")

    # Skrót klawiszowy Alt+T
    page.keyboard.press('Alt+t')
    page.wait_for_timeout(200)
    toggled_back = page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert toggled_back == initial_theme, f"Skrót Alt+T nie przywrócił motywu {initial_theme}"
    print("-> Skrót Alt+T działa prawidłowo.")

    # Przełącz na dark mode do dalszych testów wizualnych
    if toggled_back != 'dark':
        page.keyboard.press('Alt+t')
        page.wait_for_timeout(100)

    # 3. Test Command Palette (Ctrl+K)
    print("3. Test Palety Poleceń (Ctrl+K)...")
    palette = page.locator('.bipol-palette-backdrop')
    assert not palette.is_visible(), "Paleta nie powinna być widoczna przed otwarciem"

    page.keyboard.press('Control+k')
    page.wait_for_timeout(200)
    assert palette.is_visible(), "Paleta poleceń nie otworzyła się po naciśnięciu Ctrl+K"

    # Wyszukiwanie parametru
    palette_input = page.locator('.bipol-palette-input')
    palette_input.fill('rozpiętość')
    page.wait_for_timeout(200)

    items = page.locator('.bipol-palette-item')
    assert items.count() > 0, "Brak wyników wyszukiwania dla hasła 'rozpiętość'"
    first_title = items.first.locator('.bipol-palette-item-title').inner_text()
    assert 'Rozpiętość' in first_title or 'rozpiętość' in first_title.lower(), f"Nieoczekiwany wynik: {first_title}"
    print(f"-> Wynik wyszukiwania: {first_title}")

    # Wybór parametru przez Enter
    page.keyboard.press('Enter')
    page.wait_for_timeout(400)
    assert not palette.is_visible(), "Paleta poleceń powinna się zamknąć po wybraniu pozycji"

    # Sprawdzenie, czy aktywna zakładka to tab-inputs
    active_tab = page.evaluate("document.querySelector('.tab-content.active')?.id")
    assert active_tab == 'tab-inputs', f"Oczekiwano aktywnej zakładki tab-inputs, otrzymano: {active_tab}"
    print("-> Paleta poleceń pomyślnie przekierowała do parametru.")

    # 4. Test monitora zmian parametrów i szybkiego przeliczania (Ctrl+Enter)
    print("4. Test wskaźnika synchronizacji i przeliczania...")
    assert 'synced' in (recalc_pill.get_attribute('class') or ''), "Początkowy stan powinien być synced"

    # Wprowadzenie zmiany w polu rozpiętości
    span_input = page.locator('#in_wing_span')
    if span_input.count() > 0 and span_input.first.is_visible():
        current_span = float(span_input.first.input_value() or '10')
        span_input.first.fill(str(current_span + 0.5))
        span_input.first.dispatch_event('input')
        page.wait_for_timeout(200)
        assert 'dirty' in (recalc_pill.get_attribute('class') or ''), "Po edycji wskaźnik powinien zmienić się na dirty"
        print("-> Wykryto zmianę parametru (stan dirty).")

        # Naciśnięcie Ctrl+Enter do przeliczenia
        page.keyboard.press('Control+Enter')
        page.wait_for_timeout(600)
        page.wait_for_function("document.getElementById('navRecalcPill')?.classList.contains('synced')", timeout=15000)
        print("-> Projekt przeliczony pomyślnie za pomocą Ctrl+Enter (stan synced).")

    # 5. Test okna pomocy i skrótów (?)
    print("5. Test okna skrótów klawiszowych (?)..")
    # Upewnij się, że fokus nie jest w polu tekstowym
    page.locator('body').click(position={'x': 10, 'y': 10})
    page.keyboard.press('?')
    page.wait_for_timeout(200)
    shortcuts_modal = page.locator('.bipol-shortcuts-card')
    assert shortcuts_modal.is_visible(), "Okno skrótów (?) nie otworzyło się"

    # Zamknięcie przez Esc
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    assert not shortcuts_modal.is_visible(), "Okno skrótów nie zamknęło się po naciśnięciu Esc"
    print("-> Okno skrótów (?) działa prawidłowo.")

    # 6. Sprawdzenie błędów JS w konsoli
    print(f"-> Liczba błędów strony: {len(errors)}")
    if errors:
        for err in errors:
            print("  BŁĄD JS:", err)
    assert len(errors) == 0, f"Wystąpiły błędy JS na stronie: {errors}"

    print("\n[PASS] Wszystkie testy Modern UI & Dark Mode zakonczone z sukcesem!")
