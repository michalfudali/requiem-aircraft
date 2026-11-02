# Dobór balastu korekcyjnego

Analiza jest dostępna w głównej nawigacji: **Analizy szczegółowe → Geometria i wyważenie → Wyważenie przy zmiennej masie załogi i dobór balastu**. Rozwinięcie „Dobór balastu korekcyjnego” wykorzystuje masę osoby ustawioną suwakiem. Pokazuje minimum dla całej długości kadłuba i wynik dla samodzielnie wybranego miejsca. Można pobrać pełne obliczenia w LaTeX i przejść do warunków przypadku 55 kg w drzewie obliczeń.

## Źródła i zakres

- Lokalny `scraped_materials/bipol/BIPOL_3_2010.pdf`, s. 3, wzór (3.1), pkt 3–8 oraz s. 4: bilans momentów, warianty załadowania, granice 25–35% ŚCA z wyjątkiem dla szerszej wędrówki ŚC i warianty osób 55/110 kg.
- Lokalny `scraped_materials/mechanika_lotu/Projekt_3.pdf`: równowaga momentów całego samolotu i zależność wyważonej aerodynamiki od położenia środka masy. Z tego powodu pomoc w doborze balastu nie zastępuje ponownego przeliczenia biegunowej po zmianie projektu.
- [FAA-H-8083-1B, rozdział 7](https://www.faa.gov/sites/faa.gov/files/2023-09/Weight_Balance_Handbook.pdf): dobór balastu z bilansu momentów. Przykład 1876 lb, ŚC 32,2 in, cel 33 in i stacja balastu 228 in odtworzono w teście po przeliczeniu na SI.
- [CS-22 Amendment 3, § 22.31](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf): rozróżnienie balastu stałego, zrzucanego i wyjmowanego. Tutaj wybrany balast zachowuje masę i położenie podczas całego rozpatrywanego lotu.

Obliczenia korzystają z obecnych stanów wyważenia, geometrii i punktu neutralnego projektu. Granice położenia ŚC są kryteriami modelu P3 z projektu bazowego. Analiza jest pomocą w wyborze zmiany; nie dopisuje balastu do masy własnej, nie przelicza osiągów, podwozia, bezwładności ani konstrukcji jego mocowania. Po wprowadzeniu zmiany do projektu trzeba powtórzyć te obliczenia, w tym ocenę zakresu ŚC. Badany przedział 0–długość kadłuba nie oznacza, że każdy jego punkt nadaje się do mocowania masy. Oddzielne przypadki 55 i 110 kg mogą wymagać różnych rozwiązań.

## Obliczenia

Dla stanu i przed dodaniem balastu: masa m_i, moment M_i względem nosa. Po dodaniu masy w w położeniu x_B:

\[
m_i'=m_i+w,\qquad M_i'=M_i+wx_B,\qquad x_{CG,i}'=\frac{M_i+wx_B}{m_i+w}.
\]

Z pojedynczej granicy x_lim wynika klasyczny wzór:

\[
w=\frac{m_i(x_{lim}-x_{CG,i})}{x_B-x_{lim}}.
\]

Nie wystarcza jednak wyznaczyć tej masy dla jednego stanu: inne stany mogą przekroczyć przeciwną granicę lub MTOW. Solver uwzględnia wszystkie istniejące stany w locie i jednocześnie sprawdza dolną i górną granicę ŚC, minimalny zapas stateczności oraz masę projektową.

Wprowadzono Z = w·x_B. Wtedy dla każdego stanu:

\[
m_0-m_i-w\geq0,
\quad M_i+Z-x_{min}(m_i+w)\geq0,
\quad x_{max}(m_i+w)-M_i-Z\geq0.
\]

Warunek zapasu stateczności ma postać ostatniej nierówności z granicą x_N − 0,05·MAC. Dolna granica ŚC jest używana wtedy, gdy występuje w bazowej ocenie P3. Dołączono w ≥ 0 oraz x_B,min·w ≤ Z ≤ x_B,max·w. Wszystkie warunki są liniowe w (w,Z), więc tworzą wypukły wielokąt. Minimum w znajduje się w jego wierzchołku. Dla narzuconej stacji x_B dopuszczalne punkty leżą na prostej Z = x_B·w. Solver zachowuje także rozwiązania zdegenerowane do odcinka lub punktu.

Optimum może leżeć wewnątrz kadłuba, a nie na jego końcu. Test dwóch stanów wymaga jednocześnie Z ≥ 2,4w + 40 i Z ≤ 2,6w − 80. Minimum wynosi w = 600 kg przy Z = 1480 kg·m, czyli x_B = 2,466666… m. Ten celowo syntetyczny przypadek weryfikuje algorytm, nie jest propozycją balastu dla motoszybowca.

## Zachowanie i weryfikacja

- Już poprawnie wyważony projekt otrzymuje 0 kg balastu.
- Przekroczenie masy projektowej daje brak rozwiązania, ponieważ dodanie masy nie zmniejsza przeciążenia masowego.
- Złe miejsce balastu lub położenie dokładnie na naruszonej granicy ŚC nie generuje ujemnej ani nieskończonej masy.
- Jeden balast musi spełniać warunki każdego stanu, w tym lądowania i stanów przed/po zrzucie, jeżeli model je zawiera.
- Raport P3 zawiera przypadki odniesienia 55/110 kg, współczynniki wszystkich nierówności, stany przed i po korekcie oraz wzory. Eksport LaTeX z interfejsu zawiera bieżącą masę osoby, wybrane miejsce balastu i odpowiadające im obliczenia.
- Dane fizyczne nierówności powstają w Pythonie. Przeglądarka korzysta z tych samych współczynników, a zgodność wyników obu solverów sprawdza test przeglądarkowy.
- Testy obejmują przykład FAA, optimum wewnętrzne, pojedynczy punkt na MTOW, niewykonalne korekty, zmianę skali i początku współrzędnych, zachowanie masy i momentu oraz 150 losowych układów ze znanym wykonalnym balastem.

Prace wykonano w oddzielnym worktree `bipol-ballast-20261101`. Włączono opublikowane zmiany masy, raportów i interfejsu z lokalnego `master`; niezapisane zmiany innych agentów pozostały w ich katalogu roboczym.

Weryfikacja końcowa: **1759 testów Pythona** (pełny zestaw, 385,59 s), **50 testów JavaScript**, scenariusze przeglądarkowe `browser_ballast.py`, `browser_pilot_loading.py` i `browser_calculation_graph.py` — wszystkie zaliczone. Sprawdzono rzeczywiste użycie suwaków i klawiatury, dotyk i powiększanie grafu, ekran telefonu, niewykonalną korektę, blokadę nieaktualnych danych, pobranie pliku `.tex` oraz zgodność wartości z raportem P3 otwartym offline i zapisanym jako PDF. Wzory zweryfikowano przez KaTeX; samodzielnego pliku `.tex` nie kompilowano, ponieważ środowisko nie zawiera kompilatora TeX.
