# Analiza trendów i wdrożenie materiałów P1

Materiały przekazane przez użytkownika: `BIPOL_1.pdf` (6 stron) oraz
`BIPOL_1_wzory.pdf` (9 stron) ze strony przedmiotu BIPOL I. Repozytorium nie
zawiera ich kopii; program odsyła do strony źródłowej.

## Co wynika z materiałów i jak działa program

| Materiał | Wdrożenie |
| --- | --- |
| Analizy wstępne, s. 1: co najmniej 20 podobnych samolotów | 716 rekordów referencyjnych, automatyczny dobór domyślnie do 50 najbliższych względną masą, filtry i ręczna próba. Liczba wariantów, rodzin i kompletnych par są osobnymi wartościami; próby poniżej 20 dostają ostrzeżenie. |
| Zależności od roku produkcji; ekstrapolacja +5 lat | Dostępne źródła zawierają **daty certyfikacji**, nie produkcji. Program jawnie używa tej osi zastępczej, nie twierdzi, że spełnia wymaganie dat produkcji. Prognozuje od ostatniej daty próby +5 lat, wymaga ≥3 par i ≥5 lat rozpiętości. Nie uzupełnia brakujących lat. |
| Osiągi a AR, W/S, moc lub ciąg | Wykresy punktowe i regresje dla prędkości przelotowej, liczby Macha, zasięgu i drogi startu. m₀/S w kg/m², m₀/P w kg/kW, T/W bezwymiarowe. Bez łączenia Mach z km/h i mocy z ciągiem. |
| Wzór (1): We/W₀ = A·W₀ᶜ·Kvs | Rzeczywista ważona regresja log(OEW/MTOW) względem log(m₀[kg]), A, C, n, R², błąd i zakres mas. Kvs=1 lub 1,04 po deklaracji zmiennego skosu. Porównanie nie zmienia automatycznie korelacji masowej używanej przez solver. |
| Średnie parametrów | Średnie z udokumentowanych obserwacji i liczebność dla każdej wielkości. Usunięto fikcyjne średnie V_H, V_V i udziałów sterów; brakuje ich pomiarów i ramion usterzeń. |
| Analizy, s. 2–3: Swet, biegunowa i Kmax | Kontrola wydłużenia omywanego AR/(Swet/S), Kmax oraz odwróconego Cx₀=1/(4kKmax²). Bez wymyślonej digitalizacji wykresów Raymera. |
| Analizy, s. 4–6: metoda proporcji, dokładność 0,1% | Paliwo obejmuje wszystkie siedem faz, również lądowanie. Domyślnie Wf/W₀=1,06·(1−Mff); jawna rezerwa i reszta równania masowego. Obowiązuje dla misji bez zrzutu ładunku. |
| Analizy, s. 5–6: 0,8 Kmax i ułamki startu/lądowania | Domyślne K przelotu=0,8 Kmax; ustawialny mnożnik. Osobny wariant faz Galińskiego: start i lądowanie po 0,975, bez podwójnego rozruchu. Dotychczasowy model faz też jest dostępny. |
| Wyprowadzenia, s. 1–5: różne optima | Cz doskonałości √(Cx₀/k), zasięgu odrzutowego √(Cx₀/(3k)), długotrwałości śmigłowej √(3Cx₀/k); prędkości TAS dla rzeczywistej wysokości, masy i S. Punkty ponad Czmax są oznaczone jako nieosiągalne. |
| Wyprowadzenia, s. 2–3 i 6–9: ciąg, wznoszenie, zakręt | Warunek T/W≥G+1/Kmax, kinematyka zakrętu 45° i wymagany ciąg z biegunowej. Solver przestał wymuszać dodatni zakręt przy braku ciągu; krążenie szybowca ma osobny opis i nie jest zakrętem poziomym bez utraty energii. |

## Dobór i regresje

Próba zachowuje klasę konstrukcyjną oraz rodzaj napędu projektu. Filtry obejmują
źródło, liczbę silników, udokumentowane daty i liczbę najbliższych masą wariantów.
Odległość masowa to `abs(log(m_ref/m_project))`. Pusta próba pozostaje pusta;
nie zastępujemy szybowców samolotami tłokowymi. Obecne źródła obejmują GA,
turbośmigłowe, odrzutowce biznesowe i transportowe; nie dostarczają wystarczającej
bazy szybowców, motoszybowców i UAV. W ich przypadku UI i raport informują o braku.

Rodziny grupujemy heurystycznie na podstawie nazw źródłowych. Domyślnie rodzina
ma sumaryczną wagę 1 w każdym dopasowaniu (po odrzuceniu brakujących pól);
alternatywnie każdy wariant ma wagę 1. Identyczne nazwy w FAST są deduplikowane.
Rekordów między bazami nie łączymy automatycznie po podobieństwie nazwy.
Należy zbadać wpływ zmiany źródła i ręcznie dobrać niezależne konstrukcje.

Regresje są opisowe, bez obietnicy przyczynowości i bez przedziałów ufności.
R² dla stałego y jest nieokreślone. Stałe x i zbyt mała próba nie dają dopasowania.
Ekstrapolacja poza masy referencyjne lub niefizyczny wynik jest ostrzeżeniem.
Brak liczby w źródle to JSON null, a w UI/raporcie „—”. OEW nie zawsze odpowiada
definicji masy własnej projektu; wyposażenie i warunki katalogowe są różne.

## Jednostki misji

Formularz zachowuje dotychczasowy interfejs SFC:

- napęd śmigłowy: g/(kW·h), przeliczany na kg/(W·s) przez podzielenie przez 3,6·10⁹;
- napęd odrzutowy: 1/h = cT·g, przeliczany na 1/s przez podzielenie przez 3600.

Wzory w PDF podają również kg/(kN·h); nie wolno wstawić ich bez konwersji do
implementacji SI. Iloczyn faz i Mff używają tej samej fazy lądowania. W tabeli P2
masa końcowa nie odejmuje jej ponownie. Wspinanie i zniżanie pozostają przybliżeniem;
nie wprowadzono zmyślonej interpolacji rysunku Corke’a. Rezerwa 1,06 dotyczy
dodatku do paliwa faz; czas krążenia pozostaje jawną, oddzielną fazą.

## UI, raporty i dane

Widok **Baza i analiza trendów** jest w nawigacji bocznej i jest powiązany z P1
trybu semestralnego. Parametry i ręczne identyfikatory próby zapisują się w JSON
projektu, wariantach i pamięci przeglądarki po przeliczeniu. Wyszukiwanie oraz
paginacja zmieniają wyłącznie widoczną tabelę. Własny wybór wymaga przycisku
„Zastosuj zaznaczone”; filtry przywracają automatyczny dobór.

CSV próby zawiera jednostki, lokalizacje i atrybucję. JSON analizy zawiera parametry,
współczynniki, punkty, ograniczenia i źródła. P1 oraz pełny raport korzystają ze
wspólnego szablonu; wykresy są osadzonym SVG i działają offline.

Na wykresach w raportach, analizie i kreatorze punkty o identycznej odciętej
rozsuwa się symetrycznie w poziomie, aby nie tworzyły pionowych kolumn.
Rozsunięcie jest stałe dla danej próby, ograniczone do 12 jednostek SVG
oraz 40% odległości do najbliższej innej odciętej. Dotyczy wyłącznie położenia
znacznika; rzędne, opisy punktów, dane eksportowane, regresja i punkty odczytu
pozostają oparte na wartościach źródłowych. Informacja o rozsunięciu jest częścią
SVG, więc zachowuje się także w wydruku i eksporcie wykresu.

Pochodzenie, licencje, przypięta rewizja i odtworzenie importu:
[data/aircraft/README.md](../data/aircraft/README.md).

## Weryfikacja

```sh
work/venv/bin/python -m pytest tests -q
node tests/studio_core.test.mjs
python tests/browser_trends.py --base-url http://127.0.0.1:5003 --browser-path /usr/bin/chromium
python tests/browser_studio.py --base-url http://127.0.0.1:5003 --browser-path /usr/bin/chromium
```

Testy sprawdzają dane i konwersje jednostek, niezależne rozwiązania regresji,
wpływ ważenia rodzin, dobór próby, brak zmyślonych dat, prognozę +5 lat,
degenerację modelu, wzory optymalnych Cz, warunki zakrętu i domknięcie misji.
Testy przeglądarkowe obejmują filtry, wybór ręczny, zapis, eksporty i responsywność.
