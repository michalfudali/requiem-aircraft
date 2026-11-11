# Błędy programu wykryte przy projektowaniu motoszybowca (temat 7) — zadania dla agentów

Stan: 12.11.2026, gałąź `master` po scaleniu tej listy. Przegląd wykonano na projekcie
`data/design_cases/topic7_motoszybowiec_21m.json` (b = 21 m, Rotax 912 UL, m₀ ≈ 655 kg), na domyślnym temacie 7
z katalogu oraz na przeliczeniu wszystkich 110 tematów i 10 przykładów.

## Zasady pracy (obowiązują każdego agenta)

- Pracuj w osobnym worktree, na końcu `git rebase origin/master`, push na `origin/master`, usuń worktree.
  Konflikty rozwiązuj tak, żeby nie zgubić cudzej pracy. Nie uruchamiaj ani nie zatrzymuj serwera użytkownika.
- Metody obliczeń tylko z materiałów kursu (BIPOL_1–5, Analiza_masowa, wykłady, przewodnik ML Paturskiego,
  wyjątki z przepisów JAR). Nie zastępuj metody z przewodnika inną; jej ograniczenie opisz w raporcie.
- Każda liczba w raporcie ma mieć pochodzenie. Nie wpisuj danych bez źródła (silniki, profile, masy).
- Testy: `py -3.11 -m pytest -p no:cacheprovider -q < /dev/null` (seryjnie), przeglądarkowe z `--browser`,
  JS: `ELECTRON_RUN_AS_NODE=1 "<VS Code>/Code.exe" --test tests/*.test.mjs`.
- Narzędzia kontrolne:
  - `py -3.11 tools/audit_topic7.py --input data/design_cases/topic7_motoszybowiec_21m.json --output work/topic7-projekt`
    (raporty P1–P6, niezmienniki liczbowe, otwarte kontrole);
  - test `tests/test_topic7_design.py` (rachunek ręczny niezależny od modułów).
- Projekt tematu 7 po każdej zmianie ma dalej spełniać: wszystkie `compliance_checks`, audyt inżynierski bez
  pozycji innych niż `engine_installation_mass`, lista BIPOL_1 bez pozycji innych niż `sketch` i `mission`.

## A. Naprawione w tej serii (do wiedzy; testy już są)

| Nr | Błąd | Poprawka | Test |
|---|---|---|---|
| A1 | P3 liczył płat zawsze danymi profilu NACA 23012, także po wyborze innego profilu | Parametr `airfoil_model` (a∞, α₀, Cm, parabola oporu, Re odniesienia) w `paturski_ml.py`, `calc_sheet.py`, walidacja | `test_topic7_design.py`, raport P3 |
| A2 | Tabela profili w P2 pusta dla tematu 7 | Porównanie czterech profili z biegunowych XFOIL (Re = 10⁶) w pliku projektu; wybrano FX 61-163 | raport P2 |
| A3 | Brak dowodu, że wzory mas Raymera pasują do motoszybowców | Test na 21 rzeczywistych konstrukcjach: mediana 1,00, zakres 0,86–1,20 | `test_mass_equations_reproduce_real_motogliders` |
| A4 | JAR 25.121 (jeden silnik niepracujący) nie był liczony, zawsze „do oceny” | Gradient z biegunowej startowej przy V2; wchodzi do doboru mocy/ciągu | `test_regressions.py::test_one_engine_inoperative…` |
| A5 | Wymagana Vmax tematu nie wchodziła do mocy z biegunowej P4 (tematy 23, 24, 27 jej nie osiągały) | `design_solver.refine_flight_sizing` | przeliczenie tematów |
| A6 | Gradient JAR 23.65 liczony przy prędkości największego wznoszenia, która bywała równa VS1 | Prędkość nie mniejsza niż 1,2 VS1 (`perf.climb.gradient_pct`) | pełny pytest |
| A7 | Stan „Pusty + załoga” dublował „Masa bez paliwa” w samolocie bez masy płatnej | Stan pomijany, gdy masa płatna = 0 | pełny pytest |
| A8 | Przykłady (presety) z aplikacji liczone bez domknięcia biegunową P4 i bez przejścia do właściwej kategorii | `/api/presets` dodaje `design_iteration_mode`, `topic_origin='example'` | przeliczenie presetów |
| A9 | Samoloty ultralekkie porównywane z dużo cięższymi tej samej klasy | Próba ≤ 660 kg, gdy ma co najmniej 8 rodzin (`trends.select_references`) | przeliczenie tematów 15–19 |
| A11 | Dwie prędkości oderwania: 1,12 VS na wykresie doboru i 1,15 VS w modelu startu | Jedna stała `runway.LIFTOFF_FACTOR = 1,15` | pełny pytest |
| A12 | Wiersze zerowe w tabeli oporów P4 | Pomijane w `reports/p4.html` | raport P4 |
| A13 | Brak opisu ograniczeń: paliwo wznoszenia poniżej wykresu Corke’a, pułap silnika wolnossącego | Zdania w P2 i P5 | raport |
| A10 | Test `test_live_polar_chart…[390]` padał pod obciążeniem (limit 5 s) | Limit 20 s | `--browser` |

## B. Otwarte — do naprawy

Kolejność według wagi dla poprawności projektu.

### B1. Wznoszenie pod największym kątem i długotrwałość liczone przy prędkości przeciągnięcia
- **Objaw:** tabela „Osiągi samolotu w funkcji wysokości”: „V przy γmax” = Vmin na każdej wysokości, powyżej 4 km
  także „V przy wy,max” = Vmin. Tabela zasięgu: Tmax przy dolnej granicy prędkości (76,5 km/h < VS1 = 77,4 km/h).
- **Przyczyna:** `paturski_ml.py`, `eval_climb_at_alt`: `samples = [flight['stall_ms'] * (1 + i/50) …]`, oraz
  `flight_model.level_flight_envelope` (dolna granica = VS). Zakres tabeli zasięgu zaczyna się od VS dla masy przelotu.
- **Naprawa:** dolną granicę prędkości użytkowych przyjąć 1,2 VS1 (wznoszenie; JAR 23.65) i 1,1 VS1 (długotrwałość,
  jak zapas z BIPOL_2 wzór 10). Vmin w wykresie ofertowym zostaje VS1. W raporcie dopisać, skąd granica.
- **Test:** dla tematu 7 `V przy γmax ≥ 1,2·VS1` na każdej wysokości; `test_ml1_api.py` i `test_calc_sheet.py` zielone.

### B3. Domyślny temat 7 z katalogu nie jest wykonalnym punktem startu
- **Objaw:** `tools`/kreator → temat 7: m₀ = 354 kg, W/S = 19 kg/m² (poniżej klasy), Cz przelotu = 0,29 Cz,opt,
  próba 50 konstrukcji z szybowcami z balastem wodnym, surowe C = +0,25 zastąpione wymuszonym −0,05 (R² < 0),
  suma mas zespołów 406 kg wobec 211 kg z bilansu, `seats_config = side` w samolocie jednomiejscowym,
  klapolotki na całej rozpiętości.
- **Naprawa:** w `data/projects/course_seed.json` (temat 7, `parameters` i `defaults`) przyjąć wartości z
  `data/design_cases/topic7_motoszybowiec_21m.json` bez pól silnika katalogowego i bez `source_notes`.
  Rozważyć to samo dla tematów 8 i 9 (b > 20 m). Uwaga: istniejąca lokalna baza `projects.sqlite3` nie jest
  nadpisywana — dodać w `production.initialize_projects` aktualizację wierszy `topics` z nowszego seeda
  (bez dotykania tabeli `projects`), z testem w `tests/test_project_store.py`.
- **Test:** `t7sum`-owy przegląd: brak niezaliczonych kontroli poza silnikiem/szkicem/misją;
  `tests/test_topic_configuration.py`, `tests/test_browser_topic7_propeller.py`, `tests/test_design_integrity.py`.

### B4. Opór podwozia niezależny od wielkości samolotu i układu
- **Objaw:** P4, tabela oporów: „Podwozie” S = 0,105 m² (`paturski_ml.py:623`, `s_gear = 3 * 0.035`) dla każdego
  samolotu ze stałym podwoziem, także z kółkiem ogonowym.
- **Naprawa:** pole czołowe kół z wymiarów opon z wykładu 4 (d = A·W_m^B, w = A·W_m^B, tabela „Samoloty lekkie”),
  dwa koła główne + przednie albo małe kółko ogonowe (`landing_gear_type`). Pokazać wzór w `calc_sheet.py`.
- **Test:** S_j rośnie z m₀; dla tematu 7 raport P4 podaje wymiary kół i ich źródło.

### B5. Kąt ochrony ogona nie przechodzi w 92 projektach z kołem przednim
- **Objaw:** audyt `tailstrike_clearance` niezaliczony (np. temat 17: 10,6° wobec 15,3°).
- **Przyczyna:** `engineering_audit.py`: punkt ogona na stałej wysokości −0,20 d_k, bez podcięcia tyłu kadłuba;
  wysokość goleni nie jest dobierana do warunku.
- **Naprawa:** dobierać `axis_height_m` (geometry.py) tak, żeby spełnić kąt α przy Cz,max (wykład 7), z górnym
  ograniczeniem długości goleni; gdy to niemożliwe, zostawić ostrzeżenie z wymaganą wysokością. Uwzględnić wynik w
  masie podwozia (długość goleni we wzorze Raymera) i w rysunku (`drawing_sheet.py`).
- **Test:** liczba projektów z niezaliczonym `tailstrike_clearance` spada; kąt przewrócenia na bok nadal < 60°.

### B6. Projekty domyślne poza zakresem własnych przepisów
- **Objaw:** tematy 15–19 (ultralekkie): m₀ = 663–725 kg przy limicie 600 kg; jeden temat tłokowy w JAR-25
  („Rodzaj napędu: turbinowy” niezaliczone).
- **Naprawa:** to decyzja o misji w seedzie: zmniejszyć zasięg/oczekiwanie albo masę osoby do wartości z przepisów
  UL, ewentualnie przenieść temat do JAR-VLA (MTOM 750 kg). Nie zmieniać limitu. Dla tematu tłokowego > 5670 kg
  sprawdzić `scope_category` (JAR-23 commuter wymaga dwóch silników śmigłowych).
- **Test:** `[UL-A] Maksymalna masa startowa` zaliczone dla 15–19 albo jawna zmiana kategorii z uzasadnieniem.

### B7. Raport z adresu `/report?preset=…` liczy przykład w trybie wstępnym
- **Objaw:** przykłady otwarte przez `/api/presets` są domknięte biegunową P4, a `/report?preset=pzl_kos` nie
  (`app._report_parameters` bierze `AIRCRAFT_PRESETS` bez `design_iteration_mode`); zasięg wychodzi niezaliczony.
- **Naprawa:** jedna funkcja `example_parameters(key)` użyta w obu miejscach. Wcześniejsza próba zmiany w
  `project_store.load_presets` psuła `tests/test_calc_sheet.py::test_iterative_method_follows_bipol1_points_1_to_12`
  (test zakłada tryb wstępny) — test przepisać na jawne `design_iteration_mode='preliminary'`.
- **Test:** `client.get('/report?preset=pzl_kos')` zawiera „Zasięg … spełnione”.

## C. Ograniczenia metod z przewodnika — nie „naprawiać” wzoru, tylko opisać w raporcie

| Nr | Ograniczenie | Gdzie | Co zrobić |
|---|---|---|---|
| C1 | Paliwo wznoszenia ≈ 0 (0,03 kg na 2000 m): wykres Corke’a zaczyna się od M = 0,1 | `bipol1.mission_model`, flaga `below_chart` | Zdanie w P2 dodane (A13); dalej nie zmieniać metody |
| C2 | Start i lądowanie po 2,5% masy: 32 z 49 kg paliwa motoszybowca | BIPOL_1, s. 6 | Zdanie w P2 dla klas lekkich; pola `takeoff_mass_fraction`, `landing_mass_fraction` pokazać w kreatorze |
| C3 | Szacunkowa biegunowa P1 z krzywej „szybowce”: K = 48,6 wobec 31,7 z P4 | `bipol1.raymer_family` | Dla motoszybowca ze stałym napędem zaproponować w UI `sketch_swet_ratio` z P4 i przycisk „iteruj biegunową”; nie dodawać własnej krzywej |
| C4 | Pułap praktyczny 10,3 km silnika wolnossącego | `flight_model.propulsion_lapse` (Gagg–Farrar) | Zdanie w P5 dodane (A13) |
| C5 | Koszt egzemplarza 1,2 mln USD | BIPOL_2, Corke | Zdanie już dodane dla szybowców i motoszybowców; rozważyć dla UL/VLA |
| C6 | Masa własna: rozrzut wzorów −14%…+20% | `mass.estimate_component_masses` | Podawać przedział w P3 (dane z testu A3) |
| C7 | Flatter, hałas, właściwości pilotażowe | odpowiednie moduły | Zostają szacunkami wstępnymi; nie opisywać jako wykazanie zgodności |

## D. Wymaga danych lub decyzji człowieka

- **D1. Szkic odręczny i uzgodnienie misji** (BIPOL_1): pola `sketch_reference`, `mission_approval_reference`
  wypełnia autor. Agent nie wpisuje ich sam.
- **D2. Masa kompletnej zabudowy silnika** (audyt `engine_installation_mass`): udokumentowane 55,4 kg sprzętu
  Rotax 912 UL, brak źródła dla śmigła, łoża, chłodnic i wydechu. Potrzebne dane producenta.
- **D3. Lżejszy silnik.** Potrzeba 32 kW, jest 58 kW. W katalogu (`data/aircraft/aircraft.sqlite3`, tabela
  `engines`) brak silnika 30–45 kW z udokumentowanym zużyciem. Sprawdzony Hirth 3503 (51,7 kW; 33,5 kg;
  436 g/(kW h); producent: „not a certificated aircraft engine”) — odrzucony. Do dodania tylko z dokumentem
  producenta: `tools/import_engine_hardware.py` i wpis w tabeli `engines`.
- **D4. Dane profilu.** Obecne to obliczenia XFOIL przy Re = 10⁶ (airfoiltools.com). Pomiary tunelowe
  (np. Stuttgarter Profilkatalog dla FX 61-163) autor wpisuje w `airfoil_comparison` i `airfoil_model`.
- **D5. Malejąca zależność mₑ/m₀ = f(m₀)** nie wynika z danych w 90 projektach (audyt
  `empty_mass_empirical_support`): program wymusza C < 0. Decyzja prowadzącego: dobór próby per temat
  (jak w temacie 7, gdzie C = −0,128 bez wymuszenia) albo akceptacja założenia.
- **D6. 119 projektów bez wybranego silnika.** To stan wyjściowy każdego tematu; katalog ma 7 silników.
  Rozszerzenie katalogu wymaga źródeł dla każdej pozycji.
