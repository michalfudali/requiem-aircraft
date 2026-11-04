# Testowanie projektu

## Co zepsuło origin/master

Przebieg [41757492540](https://github.com/michalfudali/requiem-aircraft/actions/runs/41757492540)
dla `9f5719a` kończył się kodem 4 podczas importu `tests/conftest.py`:
`Nieobsługiwana wersja schematu bazy projektów: 3 (oczekiwano 1)`.
Nie uruchamiał się żaden test obliczeń. Poprzedni przebieg dla `b9c9230` był zielony.

Baza projektów miała cztery dodatkowe, puste tabele migracji katalogu samolotów
(`wetted_area_examples`, `model_examples`, `aircraft_supplements`, `engines`).
Oba niezależne magazyny zaczynały od `user_version=1`; kod migracji katalogu
sprawdzał wyłącznie numer wersji, więc przy przekazaniu niewłaściwego pliku
mógł przekształcić bazę projektów. Naprawa usuwa tylko te puste tabele i przywraca
wersję 1, zachowując projekt użytkownika, 10 presetów, 13 kategorii i 110 tematów.
Katalog nadal ma swój schemat 3. Migracja katalogu teraz sprawdza tożsamość bazy
przed wykonaniem jakiegokolwiek DDL.

Lokalny `diff.sqlite3.textconv` był ustawiony na `python tools/aircraft_db.py dump`
dla wszystkich plików SQLite. Ten eksport otwierał bazę przez migrator katalogu,
co pozwalało uszkodzić schemat bazy projektów nawet przy zwykłym `git diff`.
`dump` używa teraz bezpośrednio SQLite w `mode=ro`, bez importu aplikacji,
obsługuje obie bazy i zachowuje `user_version` w eksporcie. Regresja sprawdza
niezmienność pliku także dla historycznej wersji schematu i brakującej bazy aplikacji.

## Powtarzalne środowisko

Polecenia wykonujemy w osobnym worktree. Python 3.11 jest wspólną wersją lokalną
i CI; dodatkowy przebieg Linux sprawdza Python 3.13. Utwórz środowisko:

```text
python -m venv work/test-venv
```

Aktywuj je (`work/test-venv/Scripts/Activate.ps1` na Windows lub
`source work/test-venv/bin/activate` na Linux), następnie:

```text
python -m pip install -r requirements-dev.txt -c requirements-test-constraints.txt
python tools/check_databases.py
python -m pytest -q -n 2 --dist=loadfile --cov --cov-fail-under=90 --cov-report=xml:work/coverage.xml --junitxml=work/pytest.xml
```

Constraints przypinają również zależności pośrednie do zweryfikowanych wersji.
Nie instalują Playwright w zwykłym zestawie Python. Przy aktualizacji odtwórz
świeże środowisko, zaktualizuj constraints i sprawdź wszystkie trzy zestawy.
`-n 2` uruchamia dwa procesy z osobnymi bazami; `--dist=loadfile` trzyma testy
jednego modułu w jednym procesie. Do debugowania wystarczy usunąć `-n 2`.

## Zestawy i zakres

| Zestaw | Uruchomienie | Co sprawdza |
|---|---|---|
| Bazy przed importem | `python tools/check_databases.py` | Wersje, tabele, kolumny, integralność i klucze obce obu dostarczonych baz; tylko odczyt, bez importu aplikacji |
| Python | `python -m pytest` | Obliczenia, niezmienniki fizyczne, jednostki, migracje, transakcje, API, raporty i scenariusze integracyjne |
| JavaScript | `python tools/run_js_tests.py` | Wszystkie `tests/*.test.mjs`, automatycznie wykrywane, raport JUnit w `work/javascript.xml` |
| Chromium | polecenie poniżej | Prawdziwy HTTP, formularze i przeliczanie siedmiu klas, raporty P1/P6 offline, błąd i naprawa danych, zapis po przeładowaniu, telefon, graf oraz propozycja silnika |

Node 24 musi być dostępny w PATH; lokalnie można podać `--node <ścieżka>`.
Zestaw JS nie wymaga pakietów npm. Poprzednie CI wywoływało tylko dwa z siedmiu
plików; nowy runner uwzględni także przyszłe pliki bez edycji workflow.

```text
python -m pip install -r requirements-browser.txt -c requirements-test-constraints.txt
python -m playwright install chromium
python -m pytest tests/test_browser_acceptance.py --browser -q --junitxml=work/browser.xml
```

Na Linux instalacja przeglądarki w CI używa `--with-deps`. Przy jawnym
`--browser` brak przeglądarki lub zależności jest błędem. Bez tej opcji testy
przeglądarkowe są jawnie odznaczone przy kolekcji; zwykły pytest działa bez
Playwright. Dotychczasowe `browser_*.py` pozostają narzędziami szczegółowej
inspekcji; nowy zestaw pytest jest automatycznym minimum akceptacyjnym w CI.

Testy obwiedni CS-22 nadal niezależnie sprawdzają podmuch 7,5 m/s przy VD,
spadek granic manewrowych do +4/−1,5 i zgodność wielokąta z tymi przypadkami.
Testy mechaniki lotu i misji zachowują niezależne równania odniesienia.

## Izolacja i diagnostyka

`database_sandbox.py` używa wyłącznie biblioteki standardowej i kopii SQLite
przed pierwszym importem `calculations` lub `app`. Kopie są oddzielne dla każdego
workera i serwera przeglądarkowego. Ustawione są **oba** `BIPOL_AIRCRAFT_DB`
i `BIPOL_PROJECTS_DB`; procesy potomne dziedziczą te ścieżki.

Fixture automatyczna obserwuje `PRAGMA data_version` na własnych połączeniach.
Po teście przywraca zmienione bazy także po wyjątku i bez jawnego `isolated_db`.
Zauważa zapisy innych połączeń, procesów i WAL. Przywraca konfigurację Flask
i czyści cache katalogu/trendów/silników. Testy tylko czytające nie kopiują baz
ponownie. Utrzymane `isolated_db` zapewnia zgodność starszych testów.

Każdy test Chromium dostaje nowy kontekst przeglądarki, serwer na wolnym porcie
i własne bazy. `work/browser/<test>/` zawiera ostatni zrzut ekranu i `trace.zip`;
testy klas zapisują też wygenerowane HTML. Ślad można otworzyć:

```text
python -m playwright show-trace work/browser/<test>/trace.zip
```

CI ma oddzielny preflight baz, trzy przebiegi Python (Linux 3.11/3.13,
Windows 3.11), JS i Chromium. JS działa niezależnie od powodzenia Python.
Raporty JUnit, pokrycie i ślady są publikowane jako artefakty także przy błędzie.
Pokrycie mierzymy w przebiegu Linux 3.11; pozostałe dwa przebiegi wykonują pełny
zestaw bez kosztu ponownego pomiaru tych samych linii.
Przebieg wprowadzający modernizację osiągnął 94% pokrycia linii `calculations`
i `app`. CI wymaga minimum 90% w pełnym zestawie; pojedyncze testy można nadal
uruchamiać z pokryciem bez tej bramki, pomijając `--cov-fail-under=90`.
Po testach CI sprawdza, czy obie dostarczone bazy pozostały niezmienione.
Przekroczenie czasu zadania, nieznany marker lub niespodziewany XPASS powodują błąd.
Awaria zaimplementowanego CRUD/suggestions jest asercją, a nie `pytest.skip`.

Przed push sprawdź `git status --short`; bazy z danymi użytkownika nie powinny
zmieniać się wskutek testowania. Nie rozwiązuj konfliktu binarnego przez
zastąpienie całej bazy starszym plikiem: zachowaj nowe rekordy i zmigruj schemat.
