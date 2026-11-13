# Wznoszenie i paliwo misji

Aktualizacja 13.11.2026. Poprzedni bilans przycinał punkty poniżej M = 0,1 do
początku wykresu Corke’a. Dla tematu 7, 115 km/h TAS i wysokości 0–2000 m,
obie rzędne wynosiły 1. Program wyznaczał zerowe paliwo wznoszenia i zaliczał
sprawdzenie. Raport błędnie sugerował, że brakującą fazę pokrywa rezerwa.

## Bilans sił i paliwa

Podstawą jest [bilans sił wznoszenia NASA Glenn](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/forces-in-a-climb/),
z ciągiem stycznym do toru. Zadany profil ma stałe tempo pionowe `w` oraz TAS
liniową z wysokością. Przy stałym wznoszeniu, bez krzywizny toru, równania
sprowadzają się do `L = mg cos γ` i `TV = DV + mgw`.

Przy zmianie TAS uwzględniono także przyspieszenie i krzywiznę toru:

```math
\sin\gamma=\frac{w}{V},\qquad
\dot V=w\frac{V_1-V_0}{H_1-H_0},\qquad
L=m(g\cos\gamma+V\dot\gamma),\qquad
T=D+mg\sin\gamma+m\dot V.
```

```math
TV=DV+mgw+mV\dot V,\qquad
D=qSC_{D0}+\frac{kL^2}{qS}.
```

W kolejnych iteracjach domknięcia używana jest biegunowa P4 z aktualną
powierzchnią skrzydła. Wstępny bilans używa jawnie opisanej stałej doskonałości
`D = L/K`. Wysokość, gęstość ISA i masa zmieniają się podczas całkowania.
Sprawność śmigła `η(V)` jest tą samą funkcją, której używają osiągi P4/P5.

```math
\frac{dm}{dH}=-\frac{\dot m_f}{w},\qquad
\dot m_f=\frac{SFC_P}{3{,}6\cdot10^9}\frac{TV}{\eta(V)}
\quad\text{(śmigłowy)},\qquad
\dot m_f=\frac{SFC_T}{3600g}T
\quad\text{(odrzutowy)}.
```

`SFC_P` jest w g/(kW·h), a wejściowe `SFC_T` ma konwencję `c_T g`, w 1/h,
stosowaną w pozostałych równaniach aplikacji. Moc i ciąg dotyczą całego
samolotu; liczby silników nie mnoży się ponownie przez wymagany całkowity ciąg.

RK4 całkuje masę, pracę przeciw oporowi, pracę zmiany wysokości i prędkości,
pracę na wale oraz impuls ciągu. Krok wysokości nie przekracza 100 m. Zapis
wyniku zawiera wszystkie węzły profilu i rzeczywisty krok. Bilans masy i jego
odtworzenie w raporcie używają identycznej integracji; podczas poszukiwania
masy nie tworzy się tabel pośrednich, a pełny ślad powstaje dla rozwiązania.
Oszczędza to czas bez zmiany równania ani dokładności paliwa.

## Dane autora i dostępność metody

Kreator, etap 2, oraz panel BIPOL_1 pozwalają wybrać bilans energii, wykres
Corke’a lub udokumentowane własne rzędne. Profil energetyczny wymaga dodatniego
tempa wznoszenia mniejszego od TAS, wysokości końcowej nie mniejszej niż
początkowa oraz dodatniej wymaganej pracy napędu. Rozpędzanie przy zerowym
przyroście wysokości wymaga osobnego profilu fazy i nie jest zgadywane.

Jeśli nie podano tempa profilu misji, program przyjmuje dodatnie wymaganie
`climb_rate_ms` z projektu, co najmniej 0,05 m/s (dolna granica pola profilu);
przy braku dodatniego wymagania przyjmuje roboczo 3 m/s. Jawne
`mission_climb_rate_ms` ma pierwszeństwo i podlega kontroli zakresu. To założenie stałego
profilu: wymaganie przy ziemi nie dowodzi osiągalności tej wartości na całej
wysokości. Osiągalność zadanej trajektorii sprawdza się osobno
w jej węzłach: dostępny napęd według modelu spadku mocy/ciągu P4/P5 oraz
`C_L ≤ C_L,max`. Wynik obliczenia paliwa nie jest potwierdzeniem osiągalności.
Bez domknięcia z P4 ocena profilu pozostaje nierozstrzygnięta.

Tryb `auto` dawnych projektów stosuje bilans energii, tak jak nowy jawny tryb
`energy`. Jawny wybór Corke’a odrzuca punkty poniżej początku wykresu zamiast
zamieniać je w zerowy ubytek paliwa. Własny odczyt zachowuje liczby i podane
źródło. Wykres w raporcie energetycznym jest oznaczony jako porównawczy.

Katalog tematu 7 otrzymał jawny profil 3 m/s i TAS 115 km/h. Migracja rozpoznaje
cały niezmieniony rekord opublikowany w `9de2d2b`; dowolna lokalna zmiana
rekordu chroni go przed nadpisaniem. Osobiste projekty nie są przepisywane.

## Zaktualizowany temat 7

Przy 21 m rozpiętości, S = 15,75 m², Rotax 912 UL i stałym SFC z punktu
75% mocy ciągłej:

| Wynik | Wartość |
| --- | --- |
| Profil | 0–2000 m, 115 km/h TAS, 3 m/s |
| Czas wznoszenia | 666,67 s |
| Praca przeciw oporowi | 4,624 MJ |
| Praca zmiany wysokości | 12,580 MJ |
| Praca na wale | 21,044 MJ |
| Paliwo wznoszenia | 1,567 kg |
| Minimalny zapas mocy na wale w węzłach | 15,064 kW |
| Największy C_L / granica | 0,773 / 1,440 |
| Masa startowa / własna / paliwo | 658,7 / 498,2 / 50,5 kg |

Oba studia tematu 7 spełniają 14 niezależnych kontroli liczbowych. Nowa
kontrola porównuje dodatnie paliwo z dolnym ograniczeniem pracy zmiany
wysokości przy stałej TAS. Ograniczenie nie korzysta z implementacji RK4.

SFC pochodzi z [instrukcji BRP-Rotax OM-912, Ed.4 Rev.1, § 5.2](https://www.rotax-owner.com/pdf/OM_912-Series_ED4_R1.pdf).
Przyjęto stałą wartość z konkretnego punktu producenta. Przeniesienie jej
na rzeczywistą moc wznoszenia oraz wysokość nadal wymaga mapy silnika.
Start i lądowanie pozostają statystycznymi ułamkami masy według przewodnika;
nie stają się pomiarem zużycia wybranego silnika. Te ograniczenia, kompletna
masa zabudowy oraz potwierdzenie struktury pozostają otwarte.

## Sprawdzenie implementacji

`tests/test_mission_climb.py` porównuje wynik z niezależnym rozwiązaniem
analitycznym przy stałej doskonałości, sprawdza pracę i impuls w jednostkach
SFC, zagęszczenie kroku, człon rozpędzania, ograniczenia mocy oraz C_L.
Weryfikuje również rzeczywisty temat 7 i odrzucenie niepoprawnego odczytu
Corke’a przez API. `tests/test_browser_mission_climb.py` prowadzi po polach
kreatora, przelicza i zapisuje dane, otwiera je ponownie oraz renderuje
raport offline, na komputerze i telefonie.

Katalog 110 tematów sprawdzany jest osobno dla każdego tematu: domknięcie
numeryczne, zasięg, wspólna próba porównawcza, równanie biegunowej, paliwo
wznoszenia, dodatnia praca i ciągłość mas między fazami. Umożliwia to wykonanie
testów równolegle oraz jednoznaczne wskazanie wadliwego tematu.

Test odrzutowca nie zakłada już, że dowolny nowy bilans masy musi zachować
powierzchnię poniżej 40 m². Weryfikuje wymagane S z aktualnej masy, VS0 i
C_L,max, z marginesem 1,1 przewodnika BIPOL_2. Porównanie z granicą 40 m²
wykonuje przy jednakowej masie odniesienia 6291 kg, podanej przez
[Textron dla CJ3 Gen3](https://cessna.txtav.com/en/citation/cj3).
Samolot ten pozostaje analogią, a nie definicją poprawności nowego projektu.
Domyślna stała trajektoria odrzutowca wymaga dalszego doboru: program wykazuje
niedobór ciągu w części węzłów, zamiast uznawać sam bilans paliwa za dowód osiągalności.

Ślady uruchomień, odświeżone raporty i modele są w katalogu `work/` osobnego
worktree `bipol-mission-climb-20261113`.

### Weryfikacja końcowa 13.11.2026

- Zbiorczo **2668 różnych testów backendu zaliczonych**, 81 pominięć SDK
  niezgodnego z Pythonem 3.11. Każdy ze **110 tematów** ma osobny zaliczony
  test domknięcia, zasięgu i spójności bilansu.
- Pełny przebieg z pokryciem na `82963e1`: 2662 zaliczenia, 81 pominięć.
  Po poprawce dolnej granicy profilu zaliczono dodatkowy zestaw 25 testów,
  w tym sześć nowych przypadków odtwarzania danych; łączne pokrycie **94,49%**.
- Końcowy pełny przebieg na `d213ce6`: 2667 zaliczeń i jeden błąd izolacji
  zagnieżdżonego pytest. Jego kolekcję ograniczono do własnego katalogu
  tymczasowego, po czym cały zestaw baz i wznoszenia zaliczył **35/35**.
  Żaden błąd tego przebiegu nie pozostał bez poprawki i ponownego sprawdzenia.
- Zbiorczo **84 różne scenariusze Chromium** zaliczone. W przebiegu 83
  scenariuszy wystąpił jeden błąd sprzątania SQLite w Windows po zakończeniu
  testu. Serwer czeka teraz na aktywne żądania przed usunięciem bazy;
  końcowy zestaw wznoszenia zaliczył **7/7**, w tym dodatkowy scenariusz
  minimalnego tempa, zapisu, odświeżenia i synchronizacji obu paneli.
- **96/96 testów natywnego OpenVSP**, **55/55 testów JavaScript** oraz
  poprawna integralność obu baz SQLite.
- **13 raportów HTML** sprawdzonych offline bez błędów JS i KaTeX; zbiorczy
  PDF ma **96 stron bez pustych stron**. Oba modele `.vsp3` otwarto ponownie;
  wariant 21 m zachowuje 98 rzędnych FX 61-163, pole 15,75 m² i prześwit 0,23 m.

Raporty i modele odtworzono na `82963e1`. Na końcowym kodzie `caa7963`
ponownie obliczono oba studia: pełne sekcje masy, geometrii, aerodynamiki,
osiągów i doboru są identyczne z danymi użytymi do renderowania artefaktów;
obie serie 14 kontroli pozostają zaliczone. Późniejsze scalanie dotyczyło
wyłącznie dokumentacji innych agentów.

`work/climb-verified-summary.json` zachowuje wyniki poszczególnych przebiegów
i liczy przypadki według identyfikatora, bez dublowania powtórek.
Źródła: `climb-release-backend.xml`, `climb-release-isolation.xml`,
`climb-final-browser.xml`, `climb-release-ui-final.xml`,
`climb-final-native.xml`, `climb-final-native-integration.xml` oraz
`climb-final-coverage.xml`. Nie są to dowody certyfikacji ani zamknięcia
otwartych zagadnień konstrukcyjnych opisanych powyżej.
