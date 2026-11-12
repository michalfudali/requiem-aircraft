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
| A14 | Największy kąt wznoszenia liczony przy prędkości przeciągnięcia | Prędkość nie mniejsza niż 1,2 VS (`paturski_ml.eval_climb_at_alt`) | pełny pytest |
| A15 | Opór podwozia motoszybowca stały (0,105 m²) niezależnie od masy i układu | Pole kół z tabeli opon wykładu 4, przednie lub ogonowe trzecie koło | raport P4 |
| A16 | Kąt ochrony ogona: stała wysokość ogona, 92 projekty niezaliczone | Wymagane podcięcie tyłu kadłuba jako wynik; niezaliczone tylko, gdy przekracza 0,35 d_k nad osią | przeliczenie tematów |
| A17 | `/report?preset=` liczył przykład inaczej niż aplikacja | Wspólna funkcja `app.example_parameters` | pełny pytest |
| A18 | Temat 7 w katalogu startował z niewykonalnego punktu (354 kg) | Seed tematu 7 z pliku projektu, bez silnika; istniejąca lokalna baza nie jest nadpisywana (README bazy) | `test_topic_configuration.py`, `test_design_integrity.py` |
| A10 | Test `test_live_polar_chart…[390]` padał pod obciążeniem (limit 5 s) | Limit 20 s | `--browser` |

## B. Otwarte — do naprawy

Pozycje B1–B5 i B7 z pierwszej wersji tej listy są naprawione (tabela A, wiersze A14–A19).

### B6. Tematy ultralekkie 15–19 przekraczają 600 kg
- **Objaw:** m₀ = 663–725 kg przy limicie 600 kg (`[UL-A] Maksymalna masa startowa`).
- **Przyczyna:** próba samolotów ≤ 660 kg z bazy ma średni udział masy pustej 0,60; przy dwóch osobach (90 + 115 kg)
  bilans nie zamyka się w 600 kg nawet dla zasięgu 300 km.
- **Naprawa:** decyzja o temacie, nie o programie: uzupełnić bazę o współczesne konstrukcje UL 600 kg ze źródłami
  (udział masy pustej około 0,50–0,55) albo zmienić misję/masy osób w seedzie. Limitu nie zmieniać.
- **Test:** kontrola MTOM zaliczona dla tematów 15–19.

### B9. Hałas domyślnego tematu 7 z silnikiem dobranym z wykresu
- **Objaw:** temat 7 z katalogu (bez wybranego silnika, moc 28,6 kW): szacunek 72,1 dBA przy limicie 70,3 dBA.
  Z silnikiem 58 kW (plik projektu) zapas wynosi +1,7 dBA, bo samolot przelatuje wyżej nad punktem pomiaru.
- **Naprawa:** sprawdzić w `acoustics.py`, dlaczego zmiana `propeller_diameter_m` i `propeller_rpm` nie zmienia
  wyniku dla tego wariantu; jeśli model jest poprawny, zostawić jako ostrzeżenie projektowe.
- **Test:** `tests/test_acoustics.py`; wynik reaguje na średnicę i obroty.

## C. Ograniczenia metod z przewodnika — nie „naprawiać” wzoru, tylko opisać w raporcie

| Nr | Ograniczenie | Gdzie | Co zrobić |
|---|---|---|---|
| C1 | Paliwo wznoszenia ≈ 0 (0,03 kg na 2000 m): wykres Corke’a zaczyna się od M = 0,1 | `bipol1.mission_model`, flaga `below_chart` | Zdanie w P2 dodane (A13); dalej nie zmieniać metody |
| C2 | Start i lądowanie po 2,5% masy: 32 z 49 kg paliwa motoszybowca | BIPOL_1, s. 6 | Zdanie w P2 dla klas lekkich; pola `takeoff_mass_fraction`, `landing_mass_fraction` pokazać w kreatorze |
| C3 | Szacunkowa biegunowa P1 z krzywej „szybowce”: K = 48,6 wobec 31,7 z P4 | `bipol1.raymer_family` | Dla motoszybowca ze stałym napędem zaproponować w UI `sketch_swet_ratio` z P4 i przycisk „iteruj biegunową”; nie dodawać własnej krzywej |
| C4 | Pułap praktyczny 10,3 km silnika wolnossącego | `flight_model.propulsion_lapse` (Gagg–Farrar) | Zdanie w P5 dodane (A13) |
| C5 | Koszt egzemplarza 1,2 mln USD | BIPOL_2, Corke | Zdanie już dodane dla szybowców i motoszybowców; rozważyć dla UL/VLA |
| C6 | Masa własna: rozrzut wzorów −14%…+20% | `mass.estimate_component_masses` | Podawać przedział w P3 (dane z testu A3) |
| C8 | Długotrwałość największa przy dolnej granicy prędkości (blisko przeciągnięcia) | BIPOL_5: zakres prędkości z wykresu ofertowego | Nie zawężać zakresu (próba zawężenia łamie testy zgodności z BIPOL_5); ewentualnie zdanie w P5 |
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

## E. Stan przeliczenia wszystkich 120 projektów (12.11.2026, po poprawkach)

Pozycje niezaliczone w ustawieniach domyślnych tematów. Są to sygnały projektowe do rozstrzygnięcia w danym temacie,
a nie błędy rachunku; do sprawdzenia przez agenta tylko tam, gdzie zaznaczono.

| Kontrola | Liczba projektów | Uwaga |
|---|---|---|
| Brak wybranego silnika ze źródłem zużycia | 119 | Stan wyjściowy; wybiera autor (D6) |
| Gabaryty ładowni, zabudowa misji specjalnej | 33 / 26 | Wymagają danych ładunku od autora |
| Zakres biegunowej parabolicznej przy dużej prędkości | 19 + 10 | Odrzutowce; ograniczenie metody |
| Operacje na wodzie (wyporność, start, lądowanie) | 7 | Model nie obejmuje wodnosamolotów |
| Cz przelotu daleko od Cz,opt | 86 | Prędkości przelotowe w seedzie; decyzja autora |
| Malejąca zależność masy pustej bez oparcia w próbie | 84 | D5 |
| Hałas (szacunek) | 65 | Model wstępny; B9 |
| Suma mas zespołów ≠ masa pusta z bilansu | 54 | Znika po włączeniu domknięcia `empty_mass_closure=components` |
| Sterowność z jednym silnikiem | 44 | Wymiarowanie usterzenia pionowego — do sprawdzenia przez agenta |
| Obciążenie powierzchni poza przedziałem klasy | 40 | Decyzja autora |
| Kąt ochrony ogona | 22 | Po A16; pozostałe wymagają dłuższej goleni |
| Zakres ŚC i położenie kół (2 odrzutowce dyspozycyjne) | 2 | **Do sprawdzenia przez agenta** (tematy szturmowe 100, 102) |
| MTOM tematów UL | 3 | B6 |

## F. Uzupełnienie z 12.11.2026 (po tabeli E)

- **Tematy 100 i 102 (zakres ŚC, koła główne):** naprawione. Przy silnikach z tyłu kadłuba skrzydło dochodziło do
  granicy 0,56 l_k; granica dla tego układu wynosi teraz 0,64 l_k (`balance.py`).
- **Sterowność z jednym silnikiem:** ramię silnika dla gondol przy tyle kadłuba to jedna średnica kadłuba, nie 35%
  półrozpiętości. V_V rośnie do zapasu 105% (najwyżej 0,14), jeśli autor go nie zablokował. Niezaliczone: 4 projekty
  zamiast 44 — tam potrzebne większe V_V niż 0,14 albo silniki bliżej osi.
- **B9 (hałas):** model reaguje na śmigło dopiero powyżej M_tip = 0,65 i na moc dopiero powyżej 20 kW, więc dla
  małych, wolnych śmigieł wynik zależy tylko od wysokości przelotu nad punktem pomiaru. To cecha modelu wstępnego,
  nie błąd rachunku; zostaje jako ostrzeżenie projektowe.
