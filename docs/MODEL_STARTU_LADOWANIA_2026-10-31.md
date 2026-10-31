# Spójność modelu startu i lądowania — 31.10.2026

Praca w worktree `bipol-runway-20261031`, gałąź
`fix/runway-model-consistency-20261031`, od `b95eb0e`.

## Start

Dobór napędu wywoływał model rozbiegu z domyślnym tarciem 0,030,
podczas gdy wynik osiągów używał dla trawy 0,055. Wspólna funkcja
`rolling_coefficient()` przekazuje tę samą wartość do obu obliczeń.
Jawne `mu_ground` w projekcie ma pierwszeństwo nad założeniem nawierzchni.
Dodano walidację współczynnika i wyboru `paved` / `grass`.

Formularz zawiera wybór nawierzchni rozbiegu. Wczytanie starszego projektu
bez tego pola resetuje wybór do nawierzchni utwardzonej, zamiast przejmować
trawę z poprzednio otwartego projektu. Wybrana nawierzchnia pozostaje po
zapisie i przeładowaniu strony.

Wartości 0,030 i 0,055 są zachowanymi roboczymi założeniami modelu.
Nie opisują wszystkich stanów wilgotności, długości trawy ani podłoża.
Współczynnik hamowania podczas lądowania pozostaje osobnym założeniem 0,40,
co wskazano w formularzu i raporcie. Wybór trawy nie stanowi wyznaczenia
przyczepności do hamowania ani operacyjnych danych AFM.
Znaczenie oporów podłoża i właściwych danych osiągowych opisują
[FAA — Takeoffs and Departure Climbs](https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/airplane_handbook)
oraz [FAA — Airport Operations](https://www.faa.gov/air_traffic/publications/aim_html/chap4_section_3.html).

## Geometria lądowania

Usunięto arbitralne ograniczenia wysokości wyrównania do 12 m i odcinka
powietrznego do co najmniej 20 m. Dla stałej prędkości podejścia i promienia
`R = Vapp²/[g·(n−1)]`, przy roboczym `n=1,15`, pełna wysokość łuku wynosi
`h = R·(1−cos γ)`. Przy przeszkodzie 15 m:

- jeśli `h ≤ 15`, odcinek powietrzny to `(15−h)/tan γ + R·sin γ`;
- jeśli `h > 15`, przeszkoda leży wewnątrz łuku: `θ = 2 asin sqrt[15/(2R)]`,
  a odcinek wynosi `R·sin θ`, bez ujemnej prostej ścieżki.

Tor jest ciągły na granicy obu przypadków. Raport P5 pokazuje rzeczywiście
użytą gałąź wzoru. Wynik zawiera osobno prostą ścieżkę i poziomy rzut łuku.
Operacje na wodzie zachowują brak wyznaczonej drogi lądowania.
To idealizowana geometria podejścia i wyrównania, nie model kompletnego
manewru z dynamiką pilota, wiatrem i zmienną prędkością.

## Precyzja raportu

Przypadek szybkiego lądowania ujawnił dodatkowo obliczanie zasięgu w arkuszu
z czasu wcześniej zaokrąglonego do 0,01 h. W tabeli porównawczej zachowano
dotychczasowe wartości prezentacyjne, dodając niezaokrąglone czas i zasięg
do dalszych obliczeń. Arkusz wykorzystuje je i drukuje czas z pięcioma
miejscami po przecinku. Wykryty przypadek daje teraz zgodny cały arkusz,
łącznie z `L=3,6·V·t`.

## Sprawdzenie

```powershell
python -m pytest -q tests/test_runway_consistency.py
python -m pytest -q
python tests/browser_runway.py
```

20 nowych regresji obejmuje niezależne równanie okręgu, ciągłość toru,
zachowanie wysokości przeszkody, dobór mocy na trawie, walidację i raport
szybkiego lądowania z przeszkodą wewnątrz łuku.

Chrome zmienia nawierzchnię widocznym formularzem, przelicza napęd,
przeładowuje stronę, eksportuje P5 do HTML/PDF i ponownie importuje starszy
projekt. W badanym wariancie moc wzrasta z 162,681 do 173,671 kW, a modelowa
droga startu na trawie wynosi 285,4 m przy wymaganiu 300 m.

Artefakty: `work/runway-20261031/`.

Wynik końcowy: **1264 testy Python zaliczone** w 273,14 s, bez błędów
i pominięć; **36 testów JavaScript zaliczonych**. Scenariusz Chrome przeszedł
bez błędów strony; eksport PDF ma 16 stron A4 i nie zawiera pustych stron.
