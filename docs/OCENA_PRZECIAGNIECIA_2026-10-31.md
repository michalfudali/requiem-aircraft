# Ocena prędkości przeciągnięcia w P4 — 31.10.2026

Zmiana na gałęzi `fix/p4-stall-assessment-20261031`, w osobnym worktree
`bipol-stall-20261031`, od `97a220e`.

## Przyczyna

Panel P4 nazywał sprawdzenie zadanego `v_stall_kmh` zgodnością z CS-23.
Tabela klap zawsze otrzymywała zieloną etykietę „Zgodne CS-23.49 / CS-22”,
niezależnie od wyniku. Sprawdzenie prędkości w P4 i głównej liście wymagań
dopuszczało przekroczenie limitu projektu o 1 km/h, korzystając z uprzednio
zaokrąglonej prędkości.

W [aktualnych CS-23, CS 23.2110 i powiązanych AMC](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-normal-category-CS-6-AMC-GM-5?erules-id=ERULES-1963177438-6979)
wyznaczenie prędkości dotyczy różnych konfiguracji i niekorzystnych warunków.
Sama zadana wartość projektowa i uproszczony model przyrostu nośności nie
wykazują spełnienia takiego zestawu wymagań.

## Zachowanie po zmianie

Wspólna funkcja `stall_requirement()` pobiera niezaokrągloną prędkość
z równowagi siły nośnej: `VS = sqrt(2·m0·g/(rho0·S·CLmax,landing))`.
Warunek projektu to bezpośrednio `VS ≤ v_stall_kmh`. Zapas jest różnicą
limitu i wyniku, bez ukrytej tolerancji. Wynik określa modelową EAS dla
konfiguracji do lądowania przy MTOW, na poziomie morza.

Główna lista wymagań, panel P4 i raport P4 korzystają z tej samej oceny.
Raport podaje limit, wynik i zapas. Tabela klap wskazuje oszacowanie przyrostu
nośności; wynik lotek opisuje spełnienie wstępnego kryterium skuteczności.
Rozkład Schrenka opisano jako ocenę wstępną. Nagłówki odpowiadają zakresowi
tych obliczeń.

W JSON wyniku `bipol_projects.p4.high_lift.stall_requirement` zawiera pola
`actual_kmh`, `limit_kmh`, `margin_kmh`, `passed`, podstawę masy i prędkości
oraz `certification_verified=false`. Usunięto mylące pola
`is_cs23_compliant` i `cs23_stall_limit_kmh`; klient korzysta z nowego obiektu.
Zwiększono wersję zasobu aplikacji, aby przeglądarka pobrała aktualny kod.

## Sprawdzenie

```powershell
python -m pytest -q tests/test_stall_requirement.py
python -m pytest -q
python tests/browser_stall_requirement.py
```

20 nowych testów obejmuje próg wymagania, niepoprawne wartości fizyczne,
wszystkie 10 presetów, niezależną równowagę siły nośnej, zgodność panelu
z główną listą wymagań oraz eksport P4. Wariant ze stałym skrzydłem 20 m²
przekracza zadany limit o 0,04 km/h i musi otrzymać ocenę negatywną.

Chrome sprawdza wariant szkolny, wariant przekraczający limit i regionalny
samolot CS-25. Test korzysta z importu projektu, widocznej tabeli P4,
eksportu HTML/PDF i edycji limitu przez formularz. Po podniesieniu limitu
ocena wariantu niespełniającego wymagania zmienia się na pozytywną.

Surowe artefakty pozostają w `work/p4-stall-20261031/`.

Po integracji z `master` (`6c3c778`, obejmującym nowy moduł zadań kolokwialnych)
pełny zestaw zaliczył **1244 testy Python** w 278,66 s, bez pominięć i błędów.
**36 testów JavaScript** oraz trzy scenariusze Chrome P4 przeszły.
Sprawdzono również P4 przy szerokości 390 px bez przewijania całej strony
w poziomie oraz panel kolokwium, terminy i zejściówki przy 1400 i 390 px.
Trzy raporty PDF mają po 15 stron A4, wszystkie z tekstem.
