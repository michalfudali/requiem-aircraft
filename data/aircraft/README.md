# Baza referencyjna do analiz P1

Katalog jest bazą SQLite `aircraft.sqlite3` (1016 rekordów): 428 wariantów z FAST,
288 z CADO, 101 motoszybowców z wcześniejszego zestawienia, 114 konstrukcji
geometrycznych oraz 85 wariantów ze szczegółowo opisanej dokumentacji pierwotnej.
To liczba rekordów, nie liczba niezależnych rodzin. Wspólna próba wybiera jeden
rzeczywisty wariant z każdej rodziny; nie łączy najlepszych parametrów różnych
konfiguracji. Można także ograniczyć próbę do jednego źródła.
Baza jest lokalną migawką; aplikacja nie pobiera danych w trakcie obliczeń.

## Dokumentacja pierwotna — listopad 2026

Dodano 55 lekkich samolotów, 29 motoszybowców i jeden szybowiec, łącznie 85
wariantów z 47 nazwanych rodzin. 576 obserwacji liczbowych ma lokalizację w jednym
z 54 dokumentów producentów lub władz lotniczych. Wśród źródeł są TCDS EASA,
karty zatwierdzenia BMAA/CAA, instrukcje i broszury producentów. Reprezentowane są
m.in. Bristell, Evektor, Tecnam, Flight Design, Van’s, Sling, Aeroprakt, TL-Ultralight,
Blackwing, Skyleader, Zenith, RANS, Schleicher, Jonker, HpH, Lange, LAK,
DG i Schempp-Hirth. Różne silniki, rozpiętości, masy dopuszczalne oraz odmiany
wyposażenia zachowują oddzielne rekordy. Konfiguracje tej samej rodziny mają
wspólny identyfikator rodziny do ograniczenia wielokrotnego ważenia.

Wersjonowany [manifest odczytów](research/primary_aircraft.json) zawiera oryginalną
wartość i jednostkę, dokument, stronę/sekcję, warunki oraz jawne przekształcenia.
Adresy prowadzą do oryginalnych publikacji. Ich kopie nie są rozpowszechniane.
Sumy SHA-256 opisują dokumenty faktycznie pobrane podczas badania, gdy były
lokalnie dostępne. Warunki wykorzystania: [PRIMARY-RESEARCH.txt](licenses/PRIMARY-RESEARCH.txt).

Zasady doboru wartości:

- Maksymalna prędkość lotu poziomego nie jest limitem VNE. Limity szybowców
  zachowano poza kolumną `v_max`.
- Nie zastępowano przedziału masy pustej jego środkiem ani dowolnym końcem.
  Masa bez silnika lub bez baterii napędowych nie jest masą kompletnego motoszybowca.
- Osiągi przy podanej mniejszej masie są zachowane z warunkami poza próbą,
  jeżeli nie można ich przypisać do katalogowego MTOW. Czyste VS1 Slingów nie
  trafia do pola używanego do zadawania VS0 w kreatorze.
- Rozbieg/dobieg, długość do przeszkody 15 m, długość do przeszkody 50 ft i
  długość pola są rozróżnione. Nieopisanej podstawy nie zgaduje się z wielkości liczby.
- Rok certyfikacji dotyczy wskazanego wariantu. Daty publikacji, dostępu lub
  zmiany regulaminu nie zastępują nieznanego roku certyfikacji.
- Wartości sprzeczne, zaokrąglone lub o nieokreślonej konfiguracji mają uwagi.
  Nie korygowano samodzielnie opublikowanej geometrii do deklarowanego wydłużenia.
- Moc jest łączną mocą zainstalowaną; dla P2006T NG jawnie obliczono 2 × 73,5 kW.
  Moc startowa i ciągła nie są zamienne, a amerykańskie hp i metryczne PS mają
  osobne współczynniki przeliczenia.

W aplikacji wybierz źródło **Dokumentacja producentów i TCDS** w analizie trendów.
W edytorze rekordu rozwiń **Dokumentacja źródłowa, warunki i ograniczenia danych**:
można porównać odczyt z zapisem w bazie, przeczytać pominięte obserwacje i pobrać
pełny manifest JSON. Lokalna edycja jest oznaczana jako różnica względem odczytu;
zmiana liczby w edytorze nie zmienia dokumentu źródłowego.

Odtworzenie i walidacja bez sieci:

```sh
python tools/import_primary_research.py --check
python tools/import_primary_research.py
python tools/aircraft_db.py check
```

Import jest transakcyjny, nie zmienia wierszy innych źródeł, odrzuca kolizję
identyfikatora z cudzym źródłem i jest idempotentny (drugi import nie zmienia
nawet rewizji katalogu). Manifest jest wejściem do importu oraz dokumentacją;
wszystkie obliczenia nadal korzystają wyłącznie z SQLite.

## Struktura bazy

- `sources`: pochodzenie każdego zbioru (nazwa, adres, licencja, plik licencji,
  cytowanie, atrybucja): `fast`, `cado`, `motogliders`, `geometry_trends`, `primary_research` oraz `user`
  dla wpisów z edytora. Każdy samolot wskazuje źródło kluczem obcym `source_id`.
- `aircraft`: jeden wiersz na konstrukcję lub wariant, w jednostkach SI
  (kg, m², m, kW, kN, km/h, km). Brak danej w źródle to `NULL`, nie zero.
  Ograniczenia `CHECK` odpowiadają walidacji aplikacji, np. `0 < me < m0`,
  rodzaj napędu zgodny z mocą lub ciągiem, definicja długości startu.
  Tabela jest `STRICT`, więc nie przyjmie tekstu w kolumnie liczbowej.
  Kolumna `entry_no` zachowuje kolejność wpisów.
- `catalog_state.revision`: zmienia się przy każdym zapisie (wyzwalacze). Aplikacja
  przeładowuje katalog dopiero po zmianie rewizji, także po edycji innym narzędziem.

Bazę można przeglądać i edytować np. w [DB Browser for SQLite](https://sqlitebrowser.org/).
Polecenia pomocnicze:

```sh
python tools/aircraft_db.py check              # spójność, klucze obce, liczności
python tools/aircraft_db.py export cado        # rekordy jednego źródła jako JSON
python tools/aircraft_db.py dump               # pełny zrzut SQL
git config diff.sqlite3.textconv "python tools/aircraft_db.py dump"   # czytelny git diff
```

Zmienna `BIPOL_AIRCRAFT_DB` wskazuje inny plik bazy (testy używają kopii).
Do wersji `4565553` katalog był zapisany w plikach `fast.json`, `cado.json`,
`motogliders.json` i `geometry_trends.json`; przeniesiono je do bazy bez zmian wartości.

## FAST Aerobase

Copyright 2024 The Regents of the University of Michigan,
The Integrated Design of Efficient Aerospace Systems Laboratory.

Źródło: [ideas-um/FAST, +DatabasePkg](https://github.com/ideas-um/FAST/tree/482e77b921d616d00d9cdb5c0c673d55f511c52b/+DatabasePkg),
arkusz `EAP_Databases_Offline.xlsx`, rewizja
`482e77b921d616d00d9cdb5c0c673d55f511c52b`, pobrano 2026-10-20.
SHA-256: `3f31aadde6b71dab9c8a41b46d9b9707aceb9f2f4e35c02b9b5436b7f02eeaa4`.

Licencja: [Apache-2.0](licenses/FAST-Apache-2.0.txt).
Rekordy `source_id = 'fast'` to zmodyfikowana reprezentacja danych: wybrano pola z arkuszy
Jet Aircraft i Propeller Aircraft, ujednolicono nazwy i jednostki,
obliczono łączne parametry napędu i dodano klasy oraz grupowanie rodzin.
Każdy rekord wskazuje arkusz/kolumnę i zachowuje pole Sources.
Dla ciągu z tabeli silników zapisano także lokalizację dopasowanego silnika.
Pominięto rekordy bez MTOW lub źródła i powtórzoną identyczną nazwę wariantu.
Nie uzupełniano brakujących parametrów przez zgadywanie lub regresję.

Autorzy bazy proszą o cytowanie prac o FAST / Aerobase:
Mokotoff et al., *FAST: A Future Aircraft Sizing Tool for Conventional and
Electrified Aircraft Design*, DOI: [10.2514/1.C038452](https://doi.org/10.2514/1.C038452),
oraz Arnson, Aljaber i Çınar, *Predicting Aircraft Design Parameters Using Gaussian
Process Regressions on Historical Data*. Pełna bibliografia jest w repozytorium źródłowym.

## ENAC CADO v1.0

Monrolin, N.; Druot, T.; Peteilh, N.; Roches, P.; Kambiri, Y.-A. (2024),
*CADO airplane database*, Recherche Data Gouv,
[DOI:10.57745/LLRJO0](https://doi.org/10.57745/LLRJO0).

Contains information from CADO Airplane Database, which is made available here
under the Open Database License (ODbL).

Rekordy `source_id = 'cado'` są przekształconą bazą pochodną udostępnioną na
[ODbL-1.0](licenses/CADO-ODbL-1.0.txt); można je pobrać jako JSON w aplikacji
(`/download/aircraft/cado/data`) lub poleceniem `export`. Zmiany: wybrano kolumny, dodano identyfikatory,
klasy i heurystyczne rodziny, przeliczono moc/ciąg pojedynczego silnika na sumę,
oddzielono wartości Mach od km/h oraz odczytano lata z niepustych dat certyfikacji.
Numery w `source_locator` odpowiadają fizycznym wierszom oryginalnego CSV
(z nagłówkiem i dwoma wierszami jednostek).

Plik źródłowy `CADO_airplane_database_v1.0.csv`, identyfikator pliku Data Gouv
`188268`, pobrano 2026-10-20.
SHA-256: `6b986349811e66f50039347f7c3450636f8700b1ed0ad5ee7e523d89b8777180`.
Nie zmieniano wartości liczbowych katalogu poza jawną konwersją jednostek.
Nazwy i jakość danych zachowują ograniczenia oryginału; to baza do projektu
wstępnego, a nie do planowania rzeczywistych operacji lotniczych.

## Baza Geometrii i Trendów (`geometry_trends`) oraz Motoszybowców (`motogliders`)

Zestawienie certyfikowanych konstrukcji lotniczych (EASA, FAA, ULC, MEiL PW) rozszerzające
próbę o brakujące w FAST/CADO kategorie:
- Polskie samoloty tłokowe, szkolne i rolnicze (PZL-104 Wilga 35A, PZL-110 Koliber 150, PZL M-26 Iskierka, PZL M-18B Dromader, PZL-106BR Kruk, PZL-101 Gawron, Aero AT-3 R100)
- Nowoczesne samoloty General Aviation (Diamond DA40 NG, DA42 NG, DA62, Cirrus SR22T, Robin DR400, Pipistrel Virus SW 121, pierwszy w pełni certyfikowany samolot elektryczny Pipistrel Velis Electro)
- Samoloty regionalne i transportowe (PZL M28 Skytruck, PZL An-28, Pilatus PC-12 NGX)
- Szybowce certyfikowane CS-22 (SZD-9bis Bocian, SZD-30 Pirat, SZD-54-2 Perkoz, SZD-24-4 Foka, PW-2 Gapa, SZD-56-2 Diana 2)
- Samoloty odrzutowe szkolno-bojowe i dyspozycyjne (PZL TS-11 Iskra, PZL I-22 Iryda, Phenom 300E, Challenger 350)
- Bezzałogowe statki powietrzne UAV (WB Group FlyEye 3.0, WB Group Warmate, Bayraktar TB2, Orbiter 3, Hermes 450)

Dane pochodzą z oficjalnych arkuszy TCDS (EASA/FAA), instrukcji użytkowania w locie (AFM/POH) oraz dokumentacji technicznej MEiL PW.

## Wpisy użytkownika (`user`)

Nowe samoloty dodane w edytorze (lub przez `POST /api/aircraft` bez `source_id`)
trafiają do osobnego źródła `user`, a nie do wyselekcjonowanych zbiorów powyżej.
Dzięki temu w analizie można je odfiltrować (filtr „Wpisy użytkownika”), a w raporcie
nie mieszają się z cytowaniem FAST, CADO czy zestawienia geometrii. Każdy wpis podaje
własne źródło w `source_references`; zasady opisuje [USER-DATA.txt](licenses/USER-DATA.txt).
Puste źródło nie pojawia się w katalogu ani w bibliografii. Rekord dopisywany skryptem
z jawnym `source_id` (np. `geometry_trends`) zachowuje to
źródło; nieznane `source_id` jest odrzucane.

## Odtworzenie

Pobierz powyższe, przypięte wersje źródeł oraz:

```sh
python -m pip install -r requirements-data.txt
python tools/import_aircraft_data.py --fast /path/EAP_Databases_Offline.xlsx --cado /path/CADO_airplane_database_v1.0.csv
```

Importer sprawdza SHA-256, nie wymaga sieci i zastępuje w bazie wyłącznie rekordy
`fast` i `cado`, w osobnej transakcji dla każdego źródła. Nowa wersja źródła wymaga przeglądu
mapowania pól i świadomej aktualizacji skrótu. Do uruchomienia aplikacji nie jest
potrzebny openpyxl ani dostęp do źródeł zewnętrznych.


## Dane o konkretnych samolotach poza katalogiem (schemat w wersji 2)

Baza jest jedynym miejscem danych o samolotach porównawczych; kod ich nie zawiera.

- `wetted_area_examples` — stosunek powierzchni omywanej do powierzchni odniesienia
  przykładowych układów z rys. 1 materiałów BIPOL_1 (wg Raymera), z którego P1 dobiera S_wet/S.
- `model_examples` — przykładowe samoloty i ich dane przytaczane w opisach rozwiązań
  konstrukcyjnych (klapy, lotki, obrysy skrzydła, typowe wartości, przykłady nazw).
- `aircraft_supplements` — udokumentowane uzupełnienia danych katalogowych dla jednego
  projektu (import CSV); nie zmieniają wspólnego rekordu.

Projekty i tematy (projektowane samoloty) są w osobnej bazie `data/projects/projects.sqlite3`.
