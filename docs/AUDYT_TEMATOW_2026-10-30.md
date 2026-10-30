# Audyt tematów projektowych — 30.10.2026

## Zakres

Wszystkie 110 tematów przeliczono pełnym ciągiem P1–P6. Po jednym temacie z każdej
z 13 kategorii przejście użytkownika sprawdzono w przeglądarce (Chrome): kreator →
wyniki → weryfikacja → raport zbiorczy, sprawozdanie P6 i eksport DOCX.

| Kategoria | Temat | Kategoria | Temat |
| --- | --- | --- | --- |
| Motoszybowce | 10 | Dyspozycyjne | 56 (oraz 49) |
| Ultralekkie | 17 | Transportowe | 68 |
| Odrzutowe rekreacyjne | 21 | Pasażerskie | 76 (oraz 82) |
| Wyścigowe i akrobacyjne | 28 | Rolnicze i pożarnicze | 88 |
| Szkolne | 32 (oraz 31) | Łodzie latające | 95 |
| Turystyczne | 40 | Szturmowe | 99 |
| Medyczne | 44 | | |

## Poprawione założenia tematów

| Obszar | Problem | Zmiana |
| --- | --- | --- |
| Liczba silników | Parametry tematu nie zawierały liczby silników. Kreator zostawiał wartość poprzedniego projektu, więc tematy dwusilnikowe (44, 56, 68, 76 i inne) liczono jako jednosilnikowe. | Liczba silników wynika z tytułu („dwusilnikowy”, „2 silniki”, „1 silnik”), a bez takiej informacji z układu napędu. Odrzutowe rekreacyjne bez dopisku „dwa silniki” mają jeden silnik. |
| VS0 odrzutowców | Odrzutowce dyspozycyjne, szkolne i szturmowe dostawały VS0 = 90 km/h samolotu tłokowego. Temat 61 miał S = 70 m² i b = 24,4 m, temat 64 — 116 m², tematy 100 i 102 — około 100 m². | Rekreacyjne 110 km/h, dyspozycyjne 140 km/h, szkolne 150 km/h, szturmowe 170 km/h. Temat 61: S = 27,2 m², b = 15,2 m (Citation CJ3: 27,3 m², 16,3 m). |
| Ultralekkie | VS0 = 90 km/h przekraczało limit UL-A 45 KCAS (83 km/h). Rozpiętość 9 m była narzucona, chociaż temat jej nie podaje. | VS0 = 70 km/h. Skrzydło wynika z obciążenia powierzchni. |
| Akrobacyjne (27–29) | Kategoria CS-23 Level 1 (n = 3,8). | CS-23 akrobacyjna (n = 6). |
| Duża masa płatna | Samoloty transportowe, rolnicze i łodzie latające powyżej 8618 kg miały kategorię CS-23 Level 1. Kontrola MTOM zawsze wychodziła niespełniona. | Gdy szacowana MTOW przekracza 8618 kg: CS-25 i dwie osoby załogi. |
| STOL w klasach turbośmigłowej i odrzutowej | Tematy z „STOL” w tytule miały zwykłe długości 1300/1100 m lub 2200/1800 m. | Turbośmigłowe 800/700 m (DHC-7 ≈ 690/600 m), odrzutowe 1300/1200 m (BAe 146 ≈ 1200/1100 m). |
| Rolnicze i pożarnicze | VS0 = 140 km/h i sloty dawały Cz ≈ 1,0 w przelocie roboczym 240 km/h. | VS0 = 110 km/h, klapa Fowlera bez slotów. |
| Małe turbośmigłowe | Dwusilnikowy samolot medyczny miał 2 t i W/S = 213 kg/m², ze slotami. | Medyczne, 4-miejscowe dyspozycyjne i łodzie latające: 120 km/h bez slotów. Szturmowe: 140 km/h bez slotów. Temat 44: W/S = 144 kg/m² (DA62: 141). |
| Temat 95 | Czteromiejscowa turystyczna łódź latająca dostawała 1000 kg ładunku i napęd turbośmigłowy, co dawało około 6 t. | Napęd tłokowy pchający, bez ładunku: 1551 kg (Lake Renegade: 1383 kg). |
| Temat 31 | Jednomiejscowy holownik miał jednego pasażera. | Brak pasażerów. |
| Odrzutowe pasażerskie | Skos 12° z profilu VLJ przy M ≈ 0,77. | Skos 25° (CRJ, E-Jet, A320: 23–27°). |
| Poziom osiągów CS 23.2005(c) | Brak ustalonych VMO/VNO (KCAS) i MMO wymaga uzupełnienia danych. | Korekta po audycie: obliczeniowe VC w EAS nie zastępuje granic operacyjnych w CAS ani MMO. Bez tych danych program nie deklaruje poziomu osiągów. |
| Frachtowce CS-25 | Ostrzeżenie „co najmniej 10 pasażerów” pojawiało się dla samolotu bez pasażerów. | Powyżej 8618 kg o CS-25 decyduje masa, więc to zalecenie jest pomijane. |

## Rozwiązane kwestie metodyczne

| Kwestia | Rozwiązanie zgodne z praktyką projektową | Efekt |
| --- | --- | --- |
| Zasięg przy wymaganej prędkości był niespełniony we wszystkich 110 tematach. P2 liczy paliwo przy K = 0,94·Kmax, a przy wymaganej prędkości biegunowa P4 daje niższe K (temat 40: 11,9 zamiast 14,7). | Pierwsze oszacowanie zostaje zgodne z wytyczną. Wariant „bilans uściślony P2←P4” powtarza bilans masy z Cx₀ i e z P4 oraz ze średnią doskonałością przelotu przy wymaganej prędkości i wysokości, aż MTOW się ustali (refined sizing, Raymer rozdz. 19). Doskonałość z P4 obowiązuje tylko dla prędkości i wysokości, dla których ją wyznaczono. Paliwo dobiera się do gorszej z dwóch ostatnich wartości, z zapasem 0,1%. | Wszystkie 110 tematów zbiega się w 2–12 krokach. Spełniają zasięg, lot poziomy i wznoszenie. |
| Cx₀ w P2 był niższy niż opór z P4: szkolny 0,027 wobec 0,036, małe odrzutowce 0,020 wobec 0,032–0,037. | Ten sam bilans uściślony przenosi biegunową P4 do P2 aż do zgodności (±0,0002). | Kontrola lotu poziomego jest spełniona po uściśleniu. |
| ULM dwumiejscowy miał MTOM 732 kg przy limicie 600 kg. | Korelacja klasy tłokowej opisuje certyfikowane samoloty lekkie. Dla podstawy LTF-UL zastosowano modyfikator 0,85, bo dwumiejscowe UL 600 kg mają masę pustą 290–330 kg (mₑ/m₀ ≈ 0,48–0,55). | Temat 17: 562 kg, b = 10,2 m, S = 13,2 m² (Aeroprakt A-22: 10,4 m, 13,1 m²). Po uściśleniu 584 kg. |
| Małe samoloty jednomiejscowe miały Kn = 3–4%. | Usterzenie poziome jest wymiarowane warunkiem stateczności (wykres X). Gdy V_H klasy daje Kn < 5% w tylnym położeniu ŚC, V_H rośnie do wartości z równania punktu neutralnego, najwyżej do 1,2. Zablokowane V_H pozostaje bez zmian. Dolną granicę położenia krawędzi natarcia obniżono z 28 do 25% długości kadłuba, typowo dla lekkich samolotów ciągnących. Poprawiono też zaokrąglenie wyniku bisekcji, przez które przedni ŚC 24,95% był odrzucany. | Tematy 15, 23, 28, 31: Kn ≥ 5%, V_H = 0,70–0,76; kryterium BIPOL_3 spełnione. |
| Brak wymagania holowania szybowców (tematy 30–31). | Nowe ograniczenie na wykresie doboru i kontrola P5. Szybowiec dwumiejscowy 600 kg (ASK 21, Puchacz) przy 120 km/h, K = 25, wznoszenie ≥ 3 m/s, prędkość holowania ≥ 1,2 VS1 holownika. Holownik ma VS0 = 80 km/h. | Temat 31: 443 kg, 68 kW, 3,4 m/s z szybowcem (jak holowniki z Rotaxem 100 KM). |
| Odrzutowe szkolne (37–38) ważyły 1090 kg. | Szkolno-treningowe mają kategorię akrobacyjną (n = 6, CS-23 Amdt 4 dopuszcza każdy napęd). Bilans uściślony uwzględnia doskonałość przy 550 km/h na 7000 m. | 1,8–1,9 t (ViperJet ≈ 1,8 t). |

Przy uściślaniu ujawniły się też dodatkowe błędy, które poprawiono:

- **Kadłub frachtowców** był wymiarowany tylko od liczby pasażerów. Samolot na 23 t
  ładunku miał kadłub 8,4 × 1,7 m, ogromne usterzenie pionowe na krótkim ramieniu
  i Cx₀ = 0,061. Ładownię liczy się teraz z gęstości ładunku: transportowe
  150 kg/m³ (C-295 ≈ 140, C-130 ≈ 180), łodzie transportowe 167 kg/m³ (IATA).
  Wysokość ładowni to 0,9 szerokości, długość 4 szerokości, a szerokość co najmniej
  2,0 m (kontener LD-3). Temat 71 po uściśleniu: 92,9 t (C-130J: 79 t przy ~19 t
  ładunku).
- **Wyścigowe:** prędkość z tematu (380 km/h) jest wymaganiem Vmax przy ziemi,
  a przelot na zasięg odbywa się przy 300 km/h. Doszło ograniczenie Vmax na wykresie
  doboru i kontrola P5. Temat 23: 452 kg.
- **Wysokość przelotu:** odrzutowce rekreacyjne i szturmowe przelatują na 7500 m,
  szturmowe turbośmigłowe na 6000 m, czyli bliżej Kmax niż wcześniej (6000 m
  i 2500 m). VS0 odrzutowców rekreacyjnych wynosi 120 km/h (SF50 ≈ 124 km/h),
  a tłokowych dwusilnikowych 110 km/h (Seneca ≈ 113 km/h).
- **STOL ciężkie** (ładunek > 2300 kg): 1000/800 m zamiast 800/700 m, jak C-130
  i A400M przy pełnym obciążeniu.
- **Limit mocy z tematu** („moc silnika do 100/200 kW”) jest osobną kontrolą.
- **Kategoria po uściśleniu:** gdy uściślona MTOW tematu przekracza 8618 kg,
  kategoria zmienia się na CS-25 z dwiema osobami załogi, tak jak przy doborze tematu.
- **Pętla mechanizacji:** współczynniki Cz,max zaokrąglone do 0,01 mogły przeskakiwać
  między dwoma stanami (np. 2,55 ↔ 2,56) i przerywały obliczenia. Pętla przyjmuje
  teraz większe skrzydło z pary.

Ograniczenia, które pozostają:

- Masa pusta nie zależy od mocy zespołu napędowego, bo korelacja dotyczy całego
  samolotu.
- Kadłub nie uwzględnia geometrii konkretnych pojazdów (Honker, BWP-1); ładownię
  liczy się z gęstości ładunku.
- Samoloty szturmowe oceniane są według przepisów cywilnych, co jest przybliżeniem.
- Odrzutowce i turbośmigłowe dalekiego zasięgu (tematy 63–65: 3000 km) po uściśleniu
  wyraźnie przybierają na masie. Wynika to z wymaganych prędkości i wysokości,
  przy których przelot odbywa się daleko od Kmax.

## Sprawdzenie

- `py -3.11 -m pytest tests -q`: wszystkie testy zaliczone. Nowe testy są w
  `tests/test_aeronautical_audit.py` (liczba silników, VS0 odrzutowców i UL,
  kategoria akrobacyjna i CS-25, ładunki tematów 30, 31 i 95, poziom osiągów)
  oraz w `tests/test_design_practice.py` (bilans uściślony, V_H ze stateczności,
  masa UL, ładownia, holowanie, Vmax, kategorie szkolno-treningowych, pętla Cz,max).
- Bilans uściślony dla wszystkich 110 tematów: zbieżny, bez niespełnionych wymagań.
- Przeglądarka (Chrome bez okna, Playwright, aplikacja obsługiwana w procesie testu):
  16 tematów, bez błędów JavaScript. Tematy dwusilnikowe mają w wynikach 2 silniki.
- Raport zbiorczy, sprawozdanie P6 i DOCX dla 13 reprezentantów: odpowiedź 200.
