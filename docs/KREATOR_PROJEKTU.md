# Kreator projektu

Kreator jest domyślną zakładką pracowni. Pięć etapów prowadzi od tematu
i wymagań, przez misję oraz napęd, do aerodynamiki i przeglądu założeń.
Można wracać do dowolnego etapu bez zamykania formularza.

W etapie **Płat i aerodynamika** wybierz podstawę biegunowej:

- **Znam opór zerowy C_D0**: wpisz współczynnik całego samolotu w konfiguracji
  gładkiej, odniesiony do powierzchni skrzydła. Nie zastępuj go oporem profilu
  dwuwymiarowego. W tej ścieżce program nie dodaje ponownie poprawek za
  zabudowę, które powinny być zawarte w podanym współczynniku.
- **Znam stosunek S_wet/S**: wybierz analogię z materiału BIPOL_1 albo opcję
  **Wpiszę własny stosunek S_wet/S**. Wydłużenie omywane wynosi
  `Λ_wet = Λ/(S_wet/S)`. Doskonałość pochodzi z wykresu Raymera lub własnego,
  udokumentowanego odczytu. Następnie `C_D0 = πΛe/(4K_max²)`.

Podgląd używa tej samej funkcji biegunowej P1 co obliczenia projektu.
Wyświetla `C_D0`, `K_max`, `k = 1/(πΛe)` i `C_L,opt = sqrt(C_D0/k)`.
Na wykresie `C_D = C_D0 + k C_L²` suwak wybiera punkt i pokazuje jego `C_D`
oraz `K = C_L/C_D`. Suwak służy do odczytu wykresu; nie zmienia założeń
projektu. Wzory z podstawieniem są dostępne pod wykresem.

To model wstępny. Punkt maksymalnej doskonałości nie uwzględnia ograniczenia
przeciągnięciem, a wykres nie jest modelem trymowania ani oporu falowego.
W trybie domknięcia P2–P4 późniejsze obliczenia mogą uściślić biegunową
na podstawie geometrii. Odczyt Raymera poza zakresem krzywej jest oznaczany
jako ekstrapolacja w opisie biegunowej.

Pasek u góry i oznaczenia etapów sprawdzają obecność oraz zakres pól
liczbowych. Nie potwierdzają wykonalności ani zgodności konstrukcji
z przepisami. **Przejrzyj założenia** otwiera etap 5 z listą niepoprawnych
pól; każda pozycja prowadzi do odpowiedniego pola. Pola nieaktywnej metody
oporu nie blokują przeliczenia.

Szkic zapisuje się lokalnie w przeglądarce, osobno dla każdego projektu.
Przełączanie zakładek i ponowne otwarcie strony zachowują niezastosowane
zmiany. **Oblicz i zapisz projekt** lub **Ctrl+Enter** sprawdza dane,
przelicza projekt i dopiero wtedy aktualizuje zapisane wyniki.
**Wczytaj zapisane założenia** przywraca ostatnią obliczoną wersję.

Na szerokim ekranie biegunowa pozostaje obok formularza; na węższym
jest umieszczana przy polach oporu. Nawigacja działa myszą i klawiaturą,
a podgląd obsługuje jasny oraz ciemny motyw.
