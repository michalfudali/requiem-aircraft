# Drzewo obliczeń

Widok „Drzewo obliczeń” przedstawia zależności rzeczywistych obliczeń bieżącego projektu P1–P6. Korzysta z tego samego wyniku i arkusza `calc_sheet`, co raporty. Nie uruchamia odrębnego modelu fizycznego.

## Poruszanie się

- Przeciągnięcie lewym przyciskiem myszy lub jednym palcem przesuwa graf, również po rozpoczęciu gestu nad kartą.
- Kółko myszy powiększa wokół kursora; na ekranie dotykowym działa rozsuwanie dwóch palców.
- Przyciski `+`, `−`, dopasowanie i minimapa pozwalają wrócić do interesującego obszaru. Po ustawieniu fokusu na obszarze grafu działają strzałki, `+`, `−` i `Home`.
- Przegląd pokazuje etapy P1–P6 i ich główne wyniki. Kliknięcie etapu odsłania jego obliczenia. Lista widoków pozwala wybrać również wszystkie wielkości.
- Wyszukiwanie rozpoznaje nazwę, klucz i symbol; nie wymaga polskich znaków. Wybór wyniku otwiera jego ścieżkę zależności.
- Panel wielkości zawiera wzór ogólny, podstawienie liczb, wynik z jednostką, źródło oraz odnośniki do poprzedników i dalszych zastosowań.
- Węzły procedur iteracyjnych zawierają pełne obliczenia każdej faktycznie wykonanej iteracji obu metod bilansu masy.
- Eksport `.tex` obejmuje wybrane obliczenie i jego poprzedników albo bieżący widok. Zmiana danych blokuje eksport do następnego udanego przeliczenia.

## Znaczenie zależności

Strzałki wynikają z odwołań w arkuszu. Dane i założenia modelu są grupowane osobno od obliczeń; wartość oznaczona „Dana/model” może być przyjętym współczynnikiem lub wynikiem procedury numerycznej. Nie oznacza to, że jest niezależnym pomiarem.

Graf zachowuje cykle masy, geometrii i aerodynamiki. Silnie spójne składowe tworzą grupy sprzężeń; nie usuwa się ich strzałek, aby uzyskać pozorne drzewo. W panelu można przejrzeć wszystkie wielkości takiej grupy. Ścieżka obliczenia zawiera komplet jego poprzedników, także we wspólnej grupie sprzężeń.

Wzory tabelaryczne wskazują sposób obliczania tabel; ich pełne tabele pozostają w odpowiednich częściach projektu i raportu. Graf obejmuje wielkości z arkusza raportowego, a nie każdy wewnętrzny krok wszystkich funkcji programu. Nowa analiza masy załogi ma w grafie osobne obliczenia przypadków 55 i 110 kg, czułości ŚC i granic wspólnego przedziału, jeżeli taki istnieje.

## Weryfikacja

Testy obejmują zgodność wszystkich węzłów z arkuszem dla każdego presetu, wszystkie kroki iteracji, pełne zachowanie cykli i zależności, matematykę kamery i bezpieczny eksport tekstu do LaTeX. Test Chrome sprawdza faktyczne gesty myszy i dotyku, minimapę, wyszukiwanie, wszystkie etapy, renderowanie wzorów przez KaTeX, pobranie pliku, zmianę projektu i nieaktualność wyników.

Wyniki z 1 listopada 2026: pełny zestaw Pythona 1657/1657, testy modelu grafu JavaScript 8/8, oba scenariusze Chrome (`browser_calculation_graph.py`, `browser_pilot_loading.py`) zaliczone. Po końcowych zmianach zapisu wzorów sprawdzono również 142 testy arkusza/grafu/załadowania oraz 72 testy grafu/załadowania z ostrzeżeniami deprecjacji traktowanymi jako błędy. Raport P3 wygenerowano i otwarto offline; sprawdzono zgodność liczb z widokiem projektu. Eksport `.tex` sprawdzono jako pobrany plik; kompilatora TeX nie ma w tym środowisku, więc nie wykonano kompilacji tego pliku.
