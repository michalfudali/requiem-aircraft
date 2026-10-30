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

## Kwestie metodyczne do decyzji

1. **Zasięg przy wymaganej prędkości jest niespełniony we wszystkich 110 tematach.**
   Zgodnie z wytyczną P2 liczy paliwo przy K = 0,94·Kmax. Przy wymaganej prędkości
   przelotowej biegunowa P4 daje niższą doskonałość. Rozbieżność zostaje także po
   zbieżnej iteracji biegunowej:

   | Temat | K w bilansie P2 | K przy Vcr (P4) | Zasięg / wymagany |
   | --- | --- | --- | --- |
   | 40 | 14,7 | 11,9 | 1298 / 1600 km |
   | 49 | 12,3 | 7,2 | 288 / 500 km |
   | 56 | 15,0 | 10,8 | 722 / 1000 km |
   | 76 | 15,6 | 11,4 | 1602 / 2200 km |

   Możliwe rozwiązania: bilans paliwa z K przy Vcr z P4 (wymaga zgody prowadzącego,
   bo odchodzi od wytycznej 0,94·Kmax), prędkość przelotowa bliższa prędkości
   największego zasięgu albo pozostawienie tego jako wniosku P5. Program opisuje już
   tę przyczynę w krytycznej ocenie P5.
2. **Cx₀ w P2 i P4.** Cx₀ profilu klasy jest niższy niż opór z P4: szkolny 0,027
   wobec 0,036, małe odrzutowce 0,020 wobec 0,032–0,037. Kontrola lotu poziomego
   nie przechodzi do czasu „Iteruj biegunową”. Iteracja zbiega się w 1–2 krokach.
3. **ULM dwumiejscowy: MTOM 732 kg przy limicie 600 kg.** Korelacja klasy tłokowej
   daje mₑ/m₀ ≈ 0,62, a rzeczywiste UL mają około 0,5. W bazie są tylko 4 konstrukcje
   ≤ 700 kg, wszystkie LSA/VLA. Potrzebna jest próba samolotów UL.
4. **Małe samoloty jednomiejscowe (wyścigowe, akrobacyjne, holownik).** Środek
   ciężkości w locie wynosi 25–33% ŚDA, a punkt neutralny około 36% ŚDA. Daje to
   Kn = 3–4%. Potrzebne jest większe V_H. Program poprawnie zgłasza to jako
   niespełnione.
5. **Holowanie szybowców (tematy 30–31).** Nie ma wymagania wznoszenia z szybowcem
   na holu. Jednomiejscowy holownik ma 377 kg, a Wilga i Pawnee około 1300 kg.
6. **Odrzutowe szkolne (37–38).** Masa 1090 kg jest daleko poniżej rzeczywistych
   samolotów tej klasy (TS-11 Iskra: 3,8 t). Wynika to z korelacji klasy odrzutowców
   dyspozycyjnych.

## Sprawdzenie

- `py -3.11 -m pytest tests -q`: 1083 testy zaliczone, w tym nowe testy w
  `tests/test_aeronautical_audit.py` (liczba silników, VS0 odrzutowców i UL,
  kategoria akrobacyjna i CS-25, ładunki tematów 30, 31 i 95, poziom osiągów).
- Przeglądarka (Chrome bez okna, Playwright, aplikacja obsługiwana w procesie testu):
  16 tematów, bez błędów JavaScript. Tematy dwusilnikowe mają w wynikach 2 silniki.
- Raport zbiorczy, sprawozdanie P6 i DOCX dla 13 reprezentantów: odpowiedź 200.
