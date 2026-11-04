# Wspólna analiza trendów i zapis obliczeń — 3 listopada 2026

## Wymagania i źródła

Podstawą zakresu raportów jest `scraped_materials/bipol/BIPOL1_Opis_Projektow.pdf`, s. 5–10. Metody statystyczne i oszacowanie biegunowej wynikają z `BIPOL_1.pdf`, s. 1–3. Przewodnik wymaga **ośmiu średnich**; usunięcie wszystkich średnich byłoby sprzeczne z tym wymaganiem. Zachowano jedno zestawienie tych ośmiu parametrów, z liczbowym obliczeniem każdej średniej. Usunięto powielone porównanie proporcji geometrycznych oparte na innej próbie.

## Wprowadzone reguły

- Kreator, panel trendów, P1, diagnostyka geometrii i bilans masy wybierają tę samą próbę. Filtry źródła, napędu, dat, ręczne identyfikatory i uzupełnienia autora mają wspólne znaczenie.
- Domyślnie wybrane są wszystkie pasujące konstrukcje. Zawężenie do najbliższych masą jest jawną opcją `trend_nearest_count`, z ustaloną masą odniesienia. Wynik obliczenia MTOW nie zmienia próby w trakcie iteracji.
- Wagi rodzin oblicza się osobno dla każdej wielkości, z wariantów o znanej obserwacji. Braków danych nie uzupełnia się inną próbą ani wartością typową.
- Prognoza czasowa ma pierwszeństwo, gdy jest fizyczna, ma co najmniej trzy pary danych z co najmniej pięciu lat, R² ≥ 0,2 i ekstrapolację poza ostatnią obserwację nie dłuższą od okresu obserwacji. Próg R² jest jawnym założeniem selekcji, a nie normą projektowania samolotów. Wyjście poza historyczny zakres wartości nie przekreśla poprawnej ekstrapolacji. Przy odrzuceniu prognozy podaje się powód użycia średniej zastępczej.
- Automatyczny model masy przedkłada trend wybranej próby nad ogólną korelację klasy, gdy dostępne jest przynajmniej 20 obserwacji z 8 rodzin, R² ≥ 0,5 i C < 0. To przyjęta reguła selekcji. Jawny model autora, współczynniki i stały udział masy pozostają nadrzędne.
- P1 pokazuje sumy ważone, średnie współrzędnych, Sxx, Sxy, nachylenie, wyraz wolny, R² i podstawienie roku prognozy. Dla masy pokazuje transformację logarytmiczną i współczynniki A, C. Zapis odpowiada obserwacjom i pełnej precyzji obliczeń, z zaokrągleniem dopiero w raporcie.
- Załącznik zawiera wybraną próbę, osiem wymaganych obserwacji i dodatkowo tylko kolumny użyte w regresjach lub doborze parametrów. Literatura obejmuje użyte źródła.
- Udział rozpiętości lotek oznacza b_a,Σ/b = 2 b_a,1/b. Względna cięciwa jest osobną wielkością. Odchylenie od średniej nie jest kryterium skuteczności sterowania.

## Zakres projektów i sposób sprawdzenia

| Projekt | Zakres wymagany w przewodniku | Bieżąca realizacja |
| --- | --- | --- |
| P1 | Koncepcja, szkic, dobór parametrów, analiza trendów i wyniki do dalszych etapów | `reports/p1.html`, `trend_report.html`; jedno źródło danych do analizy i pełny rachunek regresji |
| P2 | Misja, bilans masy, dobór obciążeń i napędu, profil, wrażliwość, koszty | `reports/p2.html`; źródło modelu masy i uzasadnienie automatycznego wyboru; wzory i iteracje w arkuszu |
| P3 | Geometria i rysunek, masy i wyważenie, profil 200 mm, charakterystyki płata, Schrenk | `reports/p3.html`; źródła wielkości, wzory, podstawienia i wyniki arkusza; poprawione zawijanie nagłówków tabeli wyważenia |
| P4 | Charakterystyki samolotu, biegunowa prędkości przy skrajnych SC, mechanizacja i napęd | `reports/p4.html`; zapis obliczeń i tabele/wykresy według przewodników BIPOL i ML1 |
| P5 | Wykres ofertowy, zasięg i długotrwałość, start/lądowanie, krytyczna ocena osiągów | `reports/p5.html`; wzory, podstawienia i porównanie wymagań z wynikami |
| P6 | Obwiednie dla konfiguracji gładkiej i mechanizacji, charakterystyczne punkty | `reports/p6.html`; warunki wyboru, wzory, podstawienia, tabela punktów i obciążeń |

## Weryfikacja

- `tests/test_unified_trend_reports.py`: zgodność prób i wag, reguły pierwszeństwa, ręczne założenia, rekonstrukcja współczynników ze źródłowych obserwacji, jeden zestaw ośmiu średnich i brak zmiany danych przy składaniu raportu.
- `tests/test_calc_sheet.py`: niezależne przeliczenie podstawień arkusza dla presetów i wariantów; wartości, jednostki, zależności, pochodzenie danych.
- `tests/browser_unified_trends.py`: rzeczywisty Chromium, raporty P1–P6 dla siedmiu klas (42 dokumenty), wzory offline, brak błędów KaTeX i wychodzenia tabel poza szerokość A4. Przykład HTML, PDF i obraz tabeli zapisują się w `work/unified-trends/`.
- `tests/browser_trends.py`: obsługa jak użytkownik: filtry, ręczny dobór, ponowne otwarcie projektu, CSV/JSON, raport P1 offline, walidacja i szerokości 320–1600 px.

Końcowa weryfikacja:

- Pełna seria: **1987 testów Pythona zaliczonych**, 428,92 s (`work/unified-trends/pytest-release.log`). Po dodaniu regresji zmiany próby uruchomiono ponownie 30 testów pochodzenia trendów i nowego modelu raportu: wszystkie zaliczone.
- **51 testów JavaScript zaliczonych** (`work/unified-trends/node.log`); składnia zmienionych plików sprawdzona przez Node.
- **42 raporty** (7 klas × P1–P6): wzory offline, poprawny KaTeX, brak wychodzenia tabel i samych wzorów poza szerokość A4. Szczegóły zawiera `WYNIKI_UNIFIKACJI_TRENDOW_2026-11-03.json`.
- Rzeczywiste pobranie DOCX dla P1–P6 motoszybowca: poprawne archiwa OOXML i odpowiednio 134, 202, 251, 166, 130, 86 edytowalnych równań Worda.
- Przeglądarka: filtry, ręczna próba, zapis/ponowne otwarcie, CSV i JSON, raport offline, walidacja i szerokości 320–1600 px — zaliczone.
- Przeglądarka: kliknięcie zastosowania równania masy, zmiana próby z 50 na 100 samolotów, kontrola zgodności A i C w P1 i bilansie oraz przeładowanie projektu — zaliczone. Stare współczynniki nie pozostają nadpisaniem wejść.
- `tests/browser_workspace.py`: przełączanie analiz, edycja i walidacja, raport offline, obsługa klawiaturą, brak błędów JavaScript i szerokości 320–1440 px — zaliczone. Poprawiono czytelność wyboru projektu na szerokości 1024 px.
- `git diff --check`: brak błędów. Katalog danych samolotów nie został zmieniony.

Źródłowe materiały i niezakończone zmiany w głównym katalogu projektu pozostawiono na miejscu; pracę wykonano w osobnym worktree `bipol-trends-20261103`.
