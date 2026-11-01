# Mechanika Lotu I — zeszyt P1–P6

Widok `/ml1` otwiera się z nawigacji „Materiały i zaliczenie”. Jest osobnym
zeszytem **znanego samolotu**. Masa w locie jest daną pomiarową; nie uruchamia
iteracji doboru masy BIPOL. Numeracja odpowiada projektom Z. Paturskiego:
P4 — lot szybowy, P5 — napęd, P6 — osiągi.

Źródło zakresu: [materiały ML1 MEiL PW](https://www.meil.pw.edu.pl/zm/ZM/Dydaktyka/Prowadzone-przedmioty/Mechanika-Lotu-I/Materialy-do-pobrania),
odczyt 2026-11-01. Inwentarz obejmuje 33 podstrony i 39 plików. Lista adresów,
liczb stron i sum kontrolnych znajduje się w `data/ml1_sources.json`.
Repozytorium nie zawiera pobranych materiałów ani danych logowania.

## Praca z danymi

1. Wczytaj przykład odpowiedniej gałęzi albo zaimportuj własny zeszyt JSON.
   Cztery przykłady (szybowiec, śmigło stałe, przestawialne, odrzutowiec)
   zawierają **dane syntetyczne**. Nie reprezentują konkretnego typu samolotu.
2. Uzupełnij źródła, geometrię i masy P1, obrys oraz charakterystyki P2,
   parametry usterzenia i opory podzespołów P3. Pola współczynników zachowują
   powierzchnie odniesienia z pomiarów.
3. Wprowadź mapę śmigła i dane silnika P5 albo charakterystyki ciągu odrzutowego.
   Pole silnika przyjmuje JSON; przycisk wstawia przykładową strukturę każdego
   obsługiwanego modelu, wymagającą zastąpienia wartości danymi źródłowymi.
4. Wybierz wysokości, zakres Cz i dane paliwowe P6. Wysokości muszą objąć
   przecięcia wmax = 0 i 0,5 m/s, aby wyznaczyć oba pułapy. Jeżeli dane nie
   obejmują przecięcia prędkości maksymalnej, wynik pozostaje niedostępny.
5. Oblicz zeszyt. Zapisz dane/wyniki JSON lub samodzielny raport HTML z wykresami
   SVG. Raport działa bez serwera i internetu; można wydrukować go do PDF.
   Załącznik danych wejściowych można rozwinąć przed wydrukiem. Tabele dokładnej
   równowagi pokazują najlepszą gałąź i liczbę rozwiązań; pełna diagnostyka jest
   zachowana w eksporcie JSON.

Każdą metodę można też uruchomić oddzielnie z „Kalkulatorów metod”. Katalog
API `/api/ml1/catalog` podaje wszystkie parametry i przykłady wywołań;
`POST /api/ml1/calculate` przyjmuje `{ "method": "identyfikator", "inputs": {...} }`.
Pełny zeszyt używa identyfikatora `workbook`. Raport: `POST /ml1/report` z tym
samym zestawem wejściowym. Dane pozostają lokalne do chwili przesłania obliczeń;
aplikacja nie zapisuje zeszytów ML1 w bazie serwera.

Zmiana danych unieważnia wyniki i eksport. Zapis lokalny zachowuje dane wejściowe,
również edytowaną treść JSON; po przeładowaniu wymagane jest ponowne obliczenie.

## Jednostki i format tabel

Obliczenia: m, m², kg, s, N i W. Kąty w polach wejściowych: stopnie; pochodne
siły nośnej: 1/rad. Posuw J = V/(nD), CN = P/(ρn³D⁵), **n w obr/s**. Pola
`rpm`, `rpm_limit`, `rpm_max` i pierwsza kolumna charakterystyki obrotowej
silnika używają obr/min wału śmigła. Reduktor uwzględnia się, sprowadzając dane
silnika na ten wał. Moc i ciąg silnika są wartościami **jednego silnika**;
`engine_count` służy do obliczenia sumarycznych wielkości napędu.

Jednostkowe zużycie paliwa śmigłowego: kg/(kW·h); odrzutowego: kg/(daN·h).
Wewnątrz całek przepływ paliwa ma jednostkę kg/s. Masy początkowa i końcowa
dotyczą odcinka przelotowego. Rezerwy odejmuje się tylko raz. Domyślnie (6.13)
przyjmuje nominalną nastawę przez 30 + 45 minut. Można podać osobne ekonomiczne
zużycie rezerwowe `reserve_fuel_flow_kgh`.

CSV obsługuje separator `,`, `;` lub tabulator, cytowane pola i BOM. Przy
separatorze `;` dopuszcza przecinek dziesiętny. Nagłówki są nazwami pól:

- obrys: `y_m,x_le_m,chord_m`;
- profile: `re,cl,cd,alpha_deg` — grupowanie według Re;
- śmigło: `beta_deg,j,cn,eta` — grupowanie według kąta łopaty;
- podzespoły: `name,cd,reference_area_m2,source`;
- przypadki szybowania: `mass_kg,altitude_m`.

Pomiary siły oporu podzespołu przyjmują `drag_n` oraz `dynamic_pressure_pa`
albo parę `rho_kgm3,velocity_ms`. Sam współczynnik bez swojej powierzchni
odniesienia nie wystarcza. Pozostałe tabele i struktury można wczytać jako JSON.

## Macierz metod, źródeł i weryfikacji

Wszystkie poniższe metody są dostępne przez katalog i API. Test
`test_every_published_method_example_is_executable_through_the_api` wykonuje
każdy wpis katalogu; nie zastępuje niezależnych prób liczbowych z ostatniej kolumny.

| Zakres źródła | Metody / identyfikatory katalogu | Niezależna kontrola |
|---|---|---|
| P1, tabela danych, źródła, skala 1:50–1:100 | `known_aircraft`, `drawing_scale` | Stała masa wejściowa, relacje mas, zmiana skali 1:100 → 1:50 |
| P2 (2.1)–(2.5a): obrys prostokątny, trapezowy, złożony, elipsa | `planform_integrals`, `ellipse` | Ręczne całki c, c², c·x i y·c; translacja układu; elipsa z prostą linią połówek cięciw |
| P2 §2.1 i tab. 2.0/2.1 | `tunnel_data_assembly`, `reynolds_selection`, `lift_sampling`, `lift_slope_fit` | Najmniejsze Re wyłącznie do estymacji VS, najbliższe Re do doboru; regresja 6,18/rad; jawna ekstrapolacja przy kątach krytycznych |
| P2 (2.7)–(2.13) | `reynolds_correction`, `section_to_wing` | Zerowa poprawka na obu niesymetrycznych końcach krytycznych; opór techniczny 0,15 albo 0,50; kontrola radianów |
| P2 (2.14)–(2.20) | `glauert` | Ręcznie obliczone wielomiany τ i δ, zerowe poprawki elipsy, brak ukrytego ograniczania współczynników |
| P2 (2.22)–(2.27): dane tunelowe płata | `finite_wing_transfer`, `inverse_section_slope`, `wing_slope_check` | Tożsamość geometrii, zmiana oporu i kąta, odwrotna relacja pochodnych, porównanie ±10%; osobna elipsa |
| P3 (3.1), rys. Z.67–69, załącznik oporów kadłubów | `fuselage`, `chart_reading`, `chart_surface` | Własna powierzchnia odniesienia kadłuba, powierzchnia omywana mierzona albo przybliżona, interpolacja liniowa/logarytmiczna i między krzywymi |
| P3 tab. 3.1 i rys. Z.35–55, zbiory oporów J.R.A. i IAW | `component_drag` | Ten sam Cx·S z dwóch formatów danych tunelowych; wymagane źródło |
| P3 (3.3)–(3.10) | `vertical_tail`, `aircraft_polar` | Reszta momentu równowagi = 0; kontrola objętości i stosunku qH/q, sum oporów i wkładu usterzenia do Cz |
| P3 §3.6, (3.11), rys. 3.4 | `parabolic_fit`, `graphical_fit` | Znana parabola daje te same CD0 i k obiema metodami; e poza 0,7–0,98 pozostaje jawne |
| Załącznik „Zestawienie”, tabele A/B/C | `drag_statistics` | Porównuje z klasami; nie kalibruje i nie zmienia obliczonej biegunowej |
| P4 (4.1)–(4.5), tab. 4.1 | `exact_glide` | Obie składowe równowagi sił, także dla pionowego nurkowania; trzy masy/wysokości; punkt przy 1,2 Vmax |
| P4 (4.6)–(4.12) | `approximate_glide` | Stosunki Vopt/Vek = 3^(1/4) i wopt/wek = 3^(3/4)/2, porównanie z dokładną biegunową |
| P5 (5.1)–(5.3), raporty śmigłowe NACA 350/640/642/643/650 | `propeller_selection` | Odtworzenie znanej średnicy z CN i J, maksimum spośród dostarczonych krzywych, sprawdzenie Ma końcówki i warunków zabudowy |
| P5 (5.4), (5.5), tab. 5-1 | `variable_pitch` | Kąt łopaty i η z interpolacji mapy; Nrozp = η·N; brak domyślnej wymyślonej sprawności |
| P5 (5.6)–(5.8), załącznik sprężarki dwubiegowej, charakterystyki silników | `shaft_power` | Silnik bez doładowania, turbosprężarka, sprężarka dwubiegowa (cztery zakresy), turbośmigłowy i tabela; wartości w punktach przejścia |
| P5 (5.9)–(5.17), tab. 5-2 | `fixed_pitch`, `constant_torque` | Równowaga rzeczywistej charakterystyki obrotowej; niezależna metoda N/n = const; redukcja mocy przy ograniczeniu obrotów |
| P5 (5.18)–(5.20), tab. 5-3 | `jet_thrust` | Odrębne modele jedno- i dwuprzepływowe, spadek z wysokością, interpolacja tabel producenta |
| P6 (6.1) | `method_eligibility` | Kryteria >6 kg/kW i >300 kg/kN, sumaryczny napęd i MTOW |
| P6 (6.2)–(6.9), tab. 6.1/6.2 | `performance` | Zgodność metod mocy i ciągu, pierwiastki znanego równania oporu, osobne maksima wznoszenia i gradientu |
| P6 równania sił przed przybliżeniem małych kątów; [konwencja NASA](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/forces-in-a-climb/) | `exact_force_equilibrium` | Obie składowe równowagi dla dużego kąta toru, opcjonalnie pochylenie ciągu według α i kąta osi; porównanie z metodą mocy |
| P6 §6.4, (6.10)–(6.12), rys. 6.3/6.4 | `offer_chart`, `chart_climb`, `linear_climb` | Ciągłe miejsca zerowe wmax = 0 i 0,5; całka Simpsona, pole pod wykresem 1/w; rozwiązanie logarytmiczne; brak skończonego czasu do pułapu teoretycznego |
| P6 (6.13)–(6.28) | `fuel_budget`, `integrated_range` | Jednostki qe, liczba silników, bilans paliwa; kontrola dostępnej mocy/ciągu w każdym punkcie masy |
| P6 (6.29)–(6.38), tab. 6.3 | `analytical_range`, `range_table` | Wszystkie cztery kombinacje: śmigło/odrzut × Cz/V stałe; zgodność każdej całki z niezależnym wzorem zamkniętym |
| Suplement P6 | `prandtl`, `altitude_polars` oraz sprzężenie z `performance`, `offer_chart`, `integrated_range`, `range_table` | Korekta całego CD, nie samego składnika indukowanego; Ma i korekta przeliczane z masą; mniejszy zasięg i prędkość maksymalna; odrzucenie Ma ≥ 1 |

Trzy zbiory opisów samolotów i skany serii profili NACA są materiałem do
wyboru danych, nie dodatkowymi modelami fizycznymi. Ich wartości i pochodzenie
wprowadza się przez P1/P2. Analogicznie skany charakterystyk napędu i oporów
czyta się jako dane z własnym zakresem i powierzchnią odniesienia. Raporty
NACA 350/640/642/643/650 dotyczą **śmigieł**. Nie są źródłem biegunowych profili.

## Zakres modeli

- Aproksymacja P3 ma domyślny zakres dodatni do 0,85 Cz_max. To wybór roboczy
  aplikacji, nie wymaganie źródła; zakres można zmienić. e i różnica CD0 od
  minimum danych są raportowane bez przycinania do „poprawnych” wartości.
- P3 stosuje konwencję wzorów (3.9)/(3.10): wkład usterzenia mnożony przez SH/S;
  stosunek ciśnień wchodzi do kappa-prime w równowadze (3.4). Raport podaje to
  przybliżenie. Pełna analiza momentów całego samolotu należy do MLII.
- Metoda mocy/ciągu P6 przyjmuje cos(gamma) ≈ 1. Wskaźnik obciążenia i punkty
  przekraczające 20° są oznaczone. Zeszyt oblicza też bezpośrednie numeryczne
  rozwiązanie obu równań równowagi bez przybliżenia małego kąta toru, opcjonalnie
  z nachyleniem ciągu względem cięciwy i z charakterystyką α(Cz). Zestawienie
  dokładnych punktów jest oddzielone od klasycznego wykresu ofertowego ML1.
  P6 wspomina metodę Żukowskiego bez jej wyprowadzenia; aplikacja nie przypisuje
  tej nazwy innej historycznej konstrukcji graficznej.
- Suplement Prandtla dla poddźwiękowego odrzutowca stosuje CD/sqrt(1−Ma²).
  To odrębna metoda dydaktyczna; nie zastępuje pełnego modelu transonicznego
  ani diagnozy Korn/Lock w BIPOL. W całkach zasięgu korekta zależy od aktualnego
  punktu lotu. Analityczne wzory paraboliczne pozostają porównaniem nieściśliwym.
- Dopasowanie śmigła wykorzystuje dostarczone mapy. Nie ekstrapoluje ich ani
  nie narzuca średnicy, obrotów, kąta łopaty i sprawności na podstawie kategorii.
  Dobór maksymalizuje η spośród podanych krzywych ustawienia; dokładność zależy
  od rozdzielczości odczytów. W metodzie stałego skoku reszta równowagi jest
  wielomianem trzeciego stopnia na każdym przedziale; jej punkty stacjonarne
  rozdzielają wszystkie przecięcia.
- Brak pokrycia danych nie jest zerową mocą, nieograniczoną prędkością albo
  potwierdzeniem osiągów. Wiersze niedostępne zawierają przyczynę; raporty i CSV
  zachowują je. Ekstrema tabel P4 i zasięgu odnoszą się do wybranej siatki danych.
- Rysunek samolotu w trzech rzutach oraz identyfikacja profilu i źródeł pozostają
  danymi autora projektu. Kalkulator podziałki nie tworzy fikcyjnego rysunku
  istniejącego samolotu z kilku wymiarów.

## Weryfikacja

Pliki testów: `tests/test_ml1_geometry_prandtl.py`, `tests/test_ml1_wing.py`,
`tests/test_ml1_aircraft_glide_propulsion_range.py`, `tests/test_ml1_performance.py`,
`tests/test_ml1_api.py`. Test Chrome: `python tests/browser_ml1.py` (Windows,
Chrome w standardowej lokalizacji). Uruchamia Flask w procesie testu i nie
wymaga zajmowania portu innego agenta.

Test przeglądarkowy wykonuje wszystkie cztery zeszyty, sprawdza wykresy,
eksport JSON, edycję i przeładowanie, import trzech Re przez CSV, błąd zakresu
Prandtla, źródła, raport otwierany lokalnie oraz obliczenia na ekranie 390 px.

Weryfikacja po integracji z `master` z 2026-11-01:

- 1585 testów Python przeszło (351,94 s), w tym 126 testów ML1;
- 36 testów JavaScript przeszło; składnia nowego skryptu ML1 sprawdzona w Node;
- Chrome: cztery gałęzie zeszytu, wykresy, dane, eksport, zakresy i mobile;
- po zmianach składu: dodatkowo 3 próby API/raportu oraz ponowna ścieżka Chrome
  dla szybowca, odrzutowca, CSV, równań, źródeł, przeładowania i mobile;
- wydruk samodzielnego raportu odrzutowca w Chrome: 63 strony A4 poziomo,
  bez tekstu wykraczającego poza stronę; pliki PDF i zrzuty są artefaktami lokalnymi.

Katalog zawiera 43 odrębne kalkulatory; gałęzie modeli silnika, oba programy
lotu i alternatywne formaty pomiarów są parametrami odpowiednich metod.
