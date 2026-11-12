# Kreator projektu

Kreator jest domyślną zakładką pracowni. Pięć etapów prowadzi od tematu
i wymagań, przez misję oraz napęd, do aerodynamiki i przeglądu założeń.
Można wracać do dowolnego etapu bez zamykania formularza.

Pole **Znajdź założenie** przeszukuje wszystkie etapy aktualnej konfiguracji.
Rozpoznaje nazwy parametrów i ich identyfikatory, również bez polskich znaków.
Wynik pokazuje wartość, etap i oznaczenie wielkości zależnej. Wybór wyniku
otwiera etap, rozwija potrzebną sekcję formularza i ustawia fokus w polu.
Strzałki w górę i w dół przechodzą po wynikach, Enter wybiera pole,
a Escape czyści frazę. Wyszukiwanie nie zmienia projektu ani szkicu.
Pola nieaktywnej metody są pomijane; wielkości zależne zachowują blokadę edycji.

W etapie **Płat i aerodynamika** wybierz podstawę biegunowej:

- **Znam opór zerowy C_D0**: wpisz współczynnik całego samolotu w konfiguracji
  gładkiej, odniesiony do powierzchni skrzydła. Nie zastępuj go oporem profilu
  dwuwymiarowego. W tej ścieżce program nie dodaje ponownie poprawek za
  zabudowę, które powinny być zawarte w podanym współczynniku.
- **Znam stosunek S_wet/S**: wybierz analogię z materiału BIPOL_1 albo opcję
  **Wpiszę własny stosunek S_wet/S**. Wydłużenie omywane wynosi
  `Λ_wet = Λ/(S_wet/S)`. Doskonałość pochodzi z wykresu Raymera lub własnego,
  udokumentowanego odczytu. Następnie `C_D0 = πΛe/(4K_max²)`.

Karta **Punkt wyjścia aerodynamiki** u góry kreatora pokazuje bieżącą metodę
i prowadzi do jej wyboru w etapie 4. Przycisk **Wpisz własny stosunek S_wet/S**
od razu udostępnia pomiar ze szkicu. Można przełączać metody podczas edycji
bez tracenia wpisanej wcześniej wartości. Trzy karty pod polami przedstawiają
łańcuch od danych wejściowych do wyniku; niepoprawne dane usuwają stary podgląd.

Etap 4 dzieli formularz na podstawę obliczeń oporu, geometrię i zabudowę oraz
mechanizację i sterowanie. Szeroki widok od 1400 px utrzymuje biegunową obok
założeń. Telefon ma krótszy nagłówek i podgląd bezpośrednio przy polach oporu.

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

Scenariusze akceptacyjne znajdują się w `tests/test_browser_wizard_workspace.py`,
`tests/test_browser_wizard_wetted.py` i `tests/test_browser_wizard_navigation.py`.
Uruchom je poleceniem `python -m pytest --browser` ze wskazanymi plikami.
Współczynnik i równoważność obu ścieżek sprawdza `tests/test_wizard_polar.py`.

Weryfikacja 12.11.2026: 22 scenariusze kreatora w Chromium, 82 testy backendu
(biegunowa, misja, przepływy projektowe, trendy i dobór próby) oraz 55 testów
JavaScript zakończyły się powodzeniem. Scenariusze obejmują obliczenie i zapis
obu metod, ponowne otwarcie projektu, niezastosowane szkice, klawiaturę,
niepoprawne dane, spóźnione odpowiedzi API, motywy i szerokości 320–1680 px.
