# Podstawa przepisowa projektów — wyjątki z przepisów JAR (2026-11-04)

Źródło: [Wyjątki z przepisów](https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/WTLK/Wyjatki-z-przepisow)
(Zakład Samolotów i Śmigłowców, Wydział MEiL PW) — polskie przekłady JAR-22, JAR-23, JAR-25 i JAR-VLA,
rozdział po rozdziale (pliki PDF na `itlims-zsis.meil.pw.edu.pl/pomoce/JAR/`).

## Gdzie są wymagania

- `calculations/regulations.py` — jedyny katalog wymagań: identyfikator, paragraf w brzmieniu wyjątków
  (np. `JAR 23.337(a)`), rozdział (dokument PDF) i streszczenie wartości. Obliczenia, kreator i raport biorą
  paragrafy i odwołania stąd; raport cytuje rozdział jako pozycję literatury.
- `calculations/polish_law.py` — kategorie projektu, ich zakres stosowania, korekty danych wymagane
  przepisami, sprawdzenia zgodności, limity pól interfejsu (`ui_limits`) i macierz stosowalności (`features`).

## Kategorie

| Klucz | Przepisy | Zakres stosowania |
|---|---|---|
| `jar23_normal`, `jar23_utility`, `jar23_aerobatic` | JAR-23 | JAR 23.1(a)(1): ≤ 9 miejsc oprócz pilotów, ≤ 5670 kg |
| `jar23_commuter` | JAR-23 | JAR 23.1(a)(2): dwusilnikowy śmigłowy, ≤ 19 miejsc, ≤ 8618 kg |
| `cs_vla` | JAR-VLA | JAR-VLA 1: jeden silnik tłokowy, ≤ 2 miejsca, ≤ 750 kg, VS0 ≤ 45 kt |
| `cs22_glider`, `cs22_aerobatic` | JAR-22 | JAR 22.1(a)(1): szybowiec ≤ 750 kg, ≤ 2 osoby |
| `cs22_motoglider` | JAR-22 | JAR 22.1(a)(2): jeden silnik tłokowy, W/b² ≤ 3 kg/m², ≤ 850 kg |
| `cs25_transport` | JAR-25 | JAR 25.1(a): duże samoloty z napędem turbinowym |
| `cs_lsa`, `easa_optout_ul`, `easa_optout_ul115`, `easa_uas_*` | poza wyjątkami | CS-LSA, UE 2018/1139, UE 2019/947, STANAG 4671 |

Dawne klucze poziomów CS-23 Amdt 5 (`cs23_level1–3`, `cs23_aerobatic`, `cs23_commuter`) są aliasami
kategorii JAR-23, więc zapisane projekty otwierają się bez zmian. Temat oficjalny, który po obliczeniu
wykracza poza zakres JAR 23.1 swojej kategorii, jest liczony ponownie w kategorii, która go obejmuje
(normalna → commuter → JAR-25).

## Wymagania stosowane w obliczeniach

- Masa osoby do ciężaru maksymalnego: JAR 23.25(a)(2) 77/86 kg, JAR-VLA 25(a)(2) 86 kg,
  JAR 22.25(a)(2) 110 kg (jednomiejscowy) / 180 kg (dwumiejscowy); mniejsza wartość jest podnoszona z uwagą.
- VS0: JAR 23.49(c) 61 kt (jednosilnikowe), JAR-VLA 1 45 kt, JAR 22.49(b) 80 km/h; wymaganie tematu
  powyżej granicy jest obniżane z uwagą.
- Wznoszenie: JAR 23.65(a)/(b) (gradient 8,3/6,7/4 %), JAR-VLA 65 (2 m/s), JAR 22.65 (360 m w 4 min),
  JAR 22.51 (start do 15 m ≤ 500 m), JAR 22.71 (opadanie ≤ 1,0/1,2 m/s); JAR 25.121 zgłaszane jako
  wymaganie do wykazania analizą z silnikiem niepracującym.
- Obwiednia: JAR 23.333–23.345, JAR-VLA 333–345, JAR 22.333–22.345, JAR 25.333–25.345; współczynnik
  bezpieczeństwa wg paragrafu .303 kategorii; flatter do 1,2 VD (JAR 23.629(c), JAR-VLA 629(b), JAR 22.629,
  JAR 25.629(b)(1)). Szybowce domyślnie liczone wzorem Pratta z JAR 22.341 (podmuch 1-cos CS 22.341
  Amdt 3 do wyboru).

## Elementy zależne od klasy

`features()` decyduje, co istnieje w danej kategorii i klasie płatowca. Szybowiec nie ma napędu, paliwa,
bagażu ani ładunku; statki do dwóch miejsc (JAR-22, JAR-VLA, CS-LSA, UL) nie przewożą ładunku handlowego;
ładownię ma tylko płatowiec transportowy (turbośmigłowy, odrzutowy); bezzałogowiec przewozi wyposażenie
zadaniowe i nie ma załogi. Dane spoza tej macierzy są usuwane w `normalize_occupants` z uwagą, pola są
ukrywane w kreatorze i formularzu (`static/js/regulation-limits.js`), a raport pomija wiersze, wzory
i opisy, które ich dotyczą.

## Raport

Wstęp raportu ma podrozdział „Podstawa przepisowa” z tabelą wartości wynikających z przepisów
(paragraf, wymaganie, numer rozdziału w spisie literatury). Każda pozycja obliczona wzorem z przepisów ma
pod wzorem „Wymaganie przepisów: …”, a kryteria zgodności w podsumowaniu — paragraf.
