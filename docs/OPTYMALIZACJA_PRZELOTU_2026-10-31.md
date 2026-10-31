# Ciągła optymalizacja przelotu — 31.10.2026

Praca od `bd606f0`, na gałęzi `improve/cruise-optima-20261031`, w osobnym
worktree `bipol-cruise-20261031`.

## Zmiana merytoryczna

Poprzedni program wskazywał maksimum z około dziesięciu punktów tabeli,
wybierając według wartości zaokrąglonych do 0,01 h lub 0,1 km. Nie było to
optimum ciągłej charakterystyki. Granice tabeli na trzech wysokościach
pochodziły dodatkowo z wykresu ofertowego dla MTOW, zamiast z masy na
początku przelotu.

Nowy moduł `cruise_optimization.py` wyznacza osobno największy zasięg
i długotrwałość przy stałej wysokości i TAS. Wykorzystuje całkę arctan
ze wspólnego modelu `mission_cruise.py`, z malejącą masą podczas spalania
paliwa. Granice prędkości wynikają z równowagi siły nośnej i dostępnej
mocy/ciągu przy masie początku odcinka. Dla obu jednomodalnych funkcji
przeszukiwanie złotego podziału uwzględnia również końce przedziału.

To optima paliwa przydzielonego do **pierwszego przelotu**, z zachowaniem
masy pozostałego paliwa. Nie zużywają paliwa powrotu, zadania ani rezerwy.
Warunki porównania pozostają jawne: paraboliczna biegunowa bez oporu
falowego, stałe SFC i sprawność śmigła. Przedział modelowy obejmuje granicę
przeciągnięcia i nie jest zatwierdzonym zakresem użytkowania VMO/VNE ani
zaleconą prędkością operacyjną z zapasem do przeciągnięcia.

Ogólne relacje między siłą nośną, oporem, paliwem, czasem i zasięgiem
opisuje [NASA — Range Summary](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/range-summary/).
Nowy model uwzględnia zmienną masę i przydział paliwa z bilansu misji,
zamiast zakładać niezmienny ciężar.

## Wyniki i interfejs

Wynik `range_endurance_6_5.optimization` podaje status, masy, przedział
osiągalnego TAS i dwa punkty optymalne. Każdy punkt zawiera prędkość,
zasięg, czas, CL początku/końca odcinka oraz nadwyżkę mocy na początku.
Zbiorcze pola maksimum i tabela trzech wysokości korzystają z tego modelu.

Tabela 6.3 zachowuje porównanie idealnych modeli Bregueta. Jej wiersze
przechowują osobno wartości prezentacyjne i niezaokrąglone. Punkt zadanej
prędkości jest oznaczony jawnie; nie wybiera się go przez porównywanie
zaokrąglonych prędkości. Porównania metod i arkusz korzystają z tego punktu.

Brak osiągalnego lotu, paliwa przelotowego lub napędu daje brak optimum
(`null`) z przyczyną, zamiast fikcyjnego maksimum 0 km przy 0 km/h.
Panel P5 czyści poprzedni wynik przy zmianie projektu. Podpisy i raport
określają TAS, zakres modelu i paliwo pierwszego odcinka.

## Sprawdzenie

```powershell
python -m pytest -q tests/test_cruise_optimization.py
python -m pytest -q
python tests/browser_cruise_optima.py
```

20 regresji obejmuje:

- niezależne optimum analityczne przy skończonym ubytku paliwa: dla zasięgu
  śmigłowego i długotrwałości odrzutowej CL przy średniej geometrycznej mas
  wynosi `sqrt(CD0/k)`;
- porównanie z niezależnym przeglądem 2001 prędkości;
- optima na granicy przeciągnięcia i dostępnej mocy;
- brak napędu, brak paliwa i niewystarczającą moc;
- wszystkie 10 presetów, przewagę nad próbkami tabeli i prawidłowy punkt
  zadanej prędkości.

Chrome importuje kolejno samolot szkolny, wariant z mocą 0,001 kW,
szybowiec i odrzutowiec, sprawdza widoczny wynik P5 oraz eksport HTML/PDF.
Artefakty: `work/cruise-optima-20261031/`.

Walidacja: pełny przebieg **1283 testów Python** w 250,04 s, bez błędów
i pominięć; osobno komplet **20 regresji optymalizacji**, obejmujący także
ostatni test granicy dostępnej mocy. **36 testów JavaScript** i cztery
scenariusze Chrome przeszły. Sprawdzony raport PDF ma 16 stron A4,
wszystkie z tekstem; brak błędów JavaScript i składu wzorów.
