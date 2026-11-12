# Aktualny temat 7 i profil skrzydła w OpenVSP

Stan: 12.11.2026. Nowy projekt z tematu 7 używa FX 61-163, wydłużenia 28,
rozpiętości 21 m, prędkości przelotowej 115 km/h i kompozytowej technologii.
Katalog pozostawia wybór rzeczywistego silnika autorowi. Wariant z udokumentowanym
punktem zużycia Rotax 912 UL znajduje się w `data/design_cases/topic7_motoszybowiec_21m.json`.
Nie uzupełniono za autora zatwierdzenia misji, szkicu ani danych kompletnej zabudowy napędu.

## Istniejąca baza i zapisane projekty

Nowe instalacje tworzą bazę z bieżącego `course_seed.json`. Wcześniej aktualizacja
tego pliku nie zmieniała istniejącego katalogu SQLite, więc nowy temat 7 mógł
startować ze starszych parametrów.

Przy odczycie katalogu porównuje się teraz cały rekord tematu z dokładnymi,
publicznymi wersjami w `topic_history.json`. Historia wskazuje commity źródłowe.
Rozpoznane, niezmienione rekordy tematów 7 i 25 są aktualizowane atomowo do
bieżącego katalogu. Jakakolwiek lokalna zmiana parametrów, dodatkowych pól,
tytułu, konfiguracji lub wymagań chroni cały rekord przed zastąpieniem.
Warunkowy zapis chroni też zmianę dokonaną równocześnie przez inny proces.

Tabela zapisanych projektów nie jest aktualizowana. Projekt wcześniej zapisany
przez autora zachowuje swoje założenia. Aby rozpocząć aktualny wariant katalogowy,
wybiera się **Nowy projekt → Temat 7** w kreatorze. Ponowny odczyt aktualnego katalogu
nie zapisuje bazy. Błąd dowolnej aktualizacji wycofuje wszystkie zmiany tej transakcji.

## Rzędne wybranego profilu

Obie ścieżki budowy geometrii OpenVSP — Studio 3D i adapter analiz — korzystają
z tej samej geometrii profilu, która jest dostępna w P3. Profile NACA 4- i 5-cyfrowe
powstają z obsługiwanych wzorów analitycznych, a inne profile wymagają podanych rzędnych.
Rzędne mają pierwszeństwo przed samym oznaczeniem profilu.

Górna i dolna powierzchnia są normalizowane przez cięciwę i przekazywane jako
wektory do `SetAirfoilPnts` dla każdego przekroju skrzydła typu `XS_FILE_AIRFOIL`.
Dotyczy to także przekroju pośredniego w skrzydle złożonym i przybliżeniu eliptycznym.
Nie zastępuje się FX 61-163 profilem NACA o podobnej grubości lub strzałce.
[Oficjalny opis API OpenVSP 3.55](https://openvsp.org/api_docs/3.55.0/group___x_sec.html).

Dla tematu 7 zachowuje się 98 rzędnych. Testy natywne sprawdzają współrzędne
przed i po zapisie oraz ponownym otwarciu `.vsp3`, z tolerancją 10⁻¹² cięciwy.
OpenVSP interpoluje punkty własną krzywą; jego parametr `ThickChord` nie musi być
tożsamy z maksimum pionowej szczeliny między liniowymi interpolantami rzędnych
używanym przez model P3. Test przekazania punktów nie jest badaniem aerodynamicznym.

Bez wyboru profilu pozostaje jawne założenie geometrii 4-cyfrowej. Niepoprawny
lub nieobsługiwany profil podany bez rzędnych zatrzymuje budowę przed usunięciem
istniejącego modelu. Ręczne założenie t/c nie skaluje ukradkiem wybranego profilu:
różnica jest widoczna w metadanych i w panelu OpenVSP.

## Synchronizacja i widok mobilny

Przycisk synchronizacji przekazuje rzeczywisty wynik aktywnego projektu. Poprzednio
odwoływał się do nieistniejącego `window.currentResults` i wysyłał pusty obiekt,
co uruchamiało budowę domyślnego samolotu. Brak obliczonego projektu daje teraz
komunikat zamiast domyślnego modelu.

Panel pokazuje profil przyjęty przy budowie, liczbę rzędnych i ostrzeżenie o
różnicy t/c. Czyszczenie modelu i wczytanie innego `.vsp3` usuwa poprzednie
powiązanie z obliczeniami. Tabele mogą przewijać się wewnątrz panelu; nie rozszerzają
całej strony. Testy z rzeczywistym SDK obejmują wszystkie sześć podzakładek przy
szerokościach 390 i 1440 px.

Scenariusze natywnego przeglądarkowego testu można uruchomić z interpretera
Playwright, wskazując osobny interpreter z poprawnie zainstalowanym OpenVSP:

```powershell
$env:BIPOL_OPENVSP_PYTHON='C:/sciezka/do/interpretera/OpenVSP/python.exe'
python -m pytest tests/test_browser_catalog_profile.py --browser
```

Backend natywny działa wtedy w osobnym procesie i na izolowanych bazach testowych.
Każdy scenariusz ma także własny katalog plików roboczych OpenVSP, więc równoległe
procesy nie zapisują tego samego `.vsp3`.
Bez tej zmiennej pomija się tylko dwa scenariusze wymagające natywnego SDK;
testy katalogu w przeglądarce nadal są wykonywane.

Kontrola aktualnych modeli ujawniła też rozbieżność wysokości podwozia przy
automatycznie dobranej średnicy śmigła. Końcowa geometria publikuje teraz wysokość
z tej samej średnicy co P4, wyważenie i model natywny, przed zamrożeniem podpisów
przeglądu projektu. Dotyczy to również rysunku i podglądu 3D w aplikacji.

Otwarta pozostaje osobna kwestia obrysu eliptycznego: jego obecne przybliżenie
dwoma segmentami daje w próbie b = 21 m powierzchnię 14,9198 m² wobec 15,75 m²
z P3. Testy zachowania profilu nie potwierdzają zgodności całego obrysu.
Wariant tematu 7 opisany w raporcie ma skrzydło trapezowe; dla niego zweryfikowano
natywne S = 15,75 m² i TotalSpan = 21 m. Definicja rzutu rozpiętości przy wzniosie
wymaga osobnego ujednolicenia pomiędzy modelem wstępnym i OpenVSP.

OpenVSP rozróżnia `TotalSpan` i `TotalProjectedSpan`, a `TotalAR` oblicza jako
kwadrat drugiej z tych wielkości podzielony przez `TotalArea`. Potwierdza to
[kod wersji 3.55.0, `UpdateTotalParameters`](https://github.com/OpenVSP/OpenVSP/blob/OpenVSP_3.55.0/src/geom_core/WingGeom.cpp#L1322-L1332).
Dla obecnego przekazania 21 m i wzniosu 3,5° daje to 20,9608 m rzutu i AR = 27,8956
zamiast AR = 28 w P3. Zapis zgodnych `TotalSpan` i powierzchni nie rozstrzyga tej
różnicy definicji. Nie zmieniono jej ukradkiem przy poprawce rzędnych profilu.

## Weryfikacja tej aktualizacji

- Pełny backend Python 3.11: **2491 zaliczonych, 28 pominiętych**, bez błędów;
  pokrycie **94,33%** (13 484 z 14 294 linii), przy wymaganych 90%.
  Pominięcia obejmują natywne wywołania OpenVSP niedostępne dla tego interpretera;
  sprawdzono je osobno w środowisku zgodnym z SDK.
- Chromium: 52 zaliczone scenariusze, łącznie z dwoma scenariuszami natywnego
  backendu OpenVSP i sprawdzeniem sześciu podzakładek przy 390 oraz 1440 px.
  Zestaw obejmuje też obie ścieżki oporu w kreatorze, zapis szkicu, ponowne
  otwarcie, klawiaturę, podgląd biegunowej i ochronę przed spóźnionymi odpowiedziami.
- Python 3.13 / OpenVSP 3.55: 29 zaliczonych testów Studio (w tym kontrola UI)
  i 14 testów adaptera. Zapis/odczyt
  `.vsp3`, profile NACA i FX, trzy obrysy, odmowa niepoprawnego profilu oraz
  oba układy podwozia mają osobne kontrole. Osobne regresje backendu sprawdzają
  także przekazywanie błędów SDK podczas ustawiania rzędnych i odczytu pliku profilu.
- JavaScript: 55 zaliczonych testów.
- Oba studia tematu 7: 13/13 niezależnych kontroli liczbowych. Ponownie
  wygenerowano i otwarto offline 12 raportów P1–P6 i raport zbiorczy bez błędów
  JavaScript i KaTeX. PDF wariantu 21 m ma 93 strony, żadna nie jest pusta.
- Oba modele `.vsp3` mają po siedem brył. Po zapisie i ponownym otwarciu
  sprawdzono powierzchnię, `TotalSpan`, położenia i kontakt kół z ziemią.
  Dla FX 61-163 maksymalny błąd przekazania rzędnych wynosi 0 w odczycie API.
- Integralność i klucze obce obu baz SQLite są poprawne; śledzona baza samolotów
  nie została zmieniona. Testy i procesy przeglądarkowe korzystają z izolowanych baz.

Dowody lokalne znajdują się w `work/catalog-profile-final-*.xml`,
`work/catalog-profile-js.log` oraz `work/topic7-audit/` i `work/topic7-projekt/`.
Manifesty w katalogach studiów zawierają sumy SHA-256 aktualnych wejść, wyników,
raportów i modeli. Pliki `work/` są pomijane przez Git.

Wyniki dotyczą implementacji oraz wskazanych kontroli spójności. Nie zamykają
otwartych spraw opisanych w audycie tematu 7 ani rozbieżności obrysu i rzutu
rozpiętości wskazanych powyżej.
