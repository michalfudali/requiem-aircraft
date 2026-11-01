# Przydatne elementy przykładowego projektu motoszybowca

Przejrzano lokalne PDF i DOCX etapów BIPOL I 1–6 oraz dostępne opracowania BIPOL II 6, 7, 9 i 10; odczytano także formuły arkuszy XLSX i sprawdzono strukturę eksportów XFLR5 oraz XML skrzydła w folderze `scraped_materials/barnaba`. Pliki XFL są binarnymi projektami programu; ich solver nie został uruchomiony. Dokumenty studenta i jego dane osobowe nie są kopiowane do repozytorium.

## Wdrożona analiza załadowania

Wartościowym pomysłem z P3 i kolejnych opracowań jest pokazanie wpływu masy pilota na wyważenie i stateczność. Aplikacja miała już dwa warianty 55/110 kg oraz biegunowe dla skrajnych ŚC. Rozszerzono tę analizę o:

- ciągłą zmianę masy każdej osoby załogi przy stałym płatowcu;
- osobne krzywe ŚC dla wszystkich istniejących stanów załadowania, w tym lądowania i zrzutu, jeżeli dotyczy;
- ocenę masy całkowitej, kryterium ŚC P3 oraz zapasu stateczności przy każdym ustawieniu suwaka;
- dokładne przedziały spełnienia kryteriów każdego stanu i ich wspólne przecięcie;
- czułość ŚC na zmianę masy osoby, pełne podstawienia w arkuszu, raport P3 i przejście do odpowiednich wzorów w drzewie.

Nie zmienia się położenia skrzydła przy przesuwaniu suwaka. Pozostałe masy i ramiona danego stanu są zamrożone na wartościach z obliczonego projektu. Dla załogi wieloosobowej masa wszystkich członków zmienia się jednocześnie, przy zastępczym ramieniu załogi używanym już w P3. Dla UAV panel nie występuje.

Dla masy płatowca i załadowania bez załogi `m_b`, ich momentu `M_b`, liczby członków załogi `n`, ramienia załogi `x_z` i masy jednej osoby `p`:

\[
m=m_b+np,\qquad M=M_b+npx_z,\qquad x_{CG}=\frac{M_b+npx_z}{m_b+np}.
\]

\[
\frac{d\bar x_{CG}}{dp}=\frac{100n(x_zm_b-M_b)}{\bar c(m_b+np)^2}.
\]

Warunki masy, przedniego i tylnego ŚC oraz zapasu stateczności sprowadza się do nierówności `a_i p + b_i ≥ 0`, ponieważ masa całkowita jest dodatnia. Przedział wyznacza się algebraicznie, bez zaokrąglania decyzji i bez odczytu z dyskretnych punktów wykresu. Współczynniki nierówności są dostępne w panelu i raporcie. Przecięcie może być puste lub zawierać jeden punkt.

Metodę bilansu momentów zweryfikowano w [FAA-H-8083-1B, rozdział 2](https://www.faa.gov/sites/faa.gov/files/2023-09/Weight_Balance_Handbook.pdf). Kryterium 25–35% ŚDA z wyjątkiem szerszego zakresu oraz minimalny zapas 5% pozostają kryteriami modelu BIPOL. Nie są certyfikowanymi granicami eksploatacyjnymi ani oceną sterowności.

W [CS-22 Amendment 3, CS 22.23 i 22.25](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf) rozróżniono analizę położeń ŚC dla 70–110 kg na osobę ze spadochronem bez balastu oraz przypadek masy minimalnej z osobą 55 kg, gdzie przewidziano możliwość balastu. Interfejs i raport wyjaśniają tę różnicę. Badanie 55–110 kg nie jest samo w sobie deklaracją zgodności z CS-22.

## Pozostałe metody i decyzje

| Element przykładu | Ocena i decyzja |
|---|---|
| Porównanie profili przy wymaganym Cz i Re | Słuszna metoda; aplikacja ma już porównanie profili i identyfikację źródła danych. Nie przypisano NACA 63-212 ani jego charakterystyk wszystkim motoszybowcom. |
| Biegunowa płata i samolotu, moment dla różnych ŚC | Obecne modele Paturskiego i wykresy skrajnych ŚC realizują ten cel. Wynik VLM konkretnej geometrii nie zastępuje automatycznie biegunowej innego projektu. |
| Schrenk i momenty bezwładności | Już dostępne w P3; utrzymano istniejące bilanse masy i momentów. |
| Wykres mocy i wykres ofertowy | Już dostępne w P4/P5 i ML1; nie przeniesiono odczytów prędkości z przykładowego napędu. |
| Punktowe obliczenia podmuchów | Nie zastępują wspólnego modelu obwiedni; pozostawiono istniejące sprawdzanie właściwych prędkości, podmuchów i granic manewrowych. |
| Stateczność boczna, stery i lotki | Przykładowe pochodne zależą od geometrii i warunków analizy; nie przeniesiono ich jako uniwersalnych stałych. |
| Obciążenia usterzenia i kadłuba BIPOL II | Temat wartościowy, ale wyniki przykładu nie stanowią zweryfikowanego modelu konstrukcyjnego. Nie dodano na ich podstawie pozornie gotowej analizy wytrzymałościowej. |
| Napęd elektryczny i akumulator | Potrzebny byłby osobny model energii, sprawności i pakietu. Nie podstawiono akumulatora w miejsce zużywanego paliwa w obecnym modelu masy. |

## Stwierdzone niespójności przykładu

To projekt dydaktyczny, nie wzorzec zatwierdzonych obliczeń. Przykłady powodów, dla których nie kopiowano jego wyników:

- W P2 zapis `14 000 W × 1,25 h = 14 950 Wh` jest niespójny; iloczyn wynosi 17 500 Wh. Kolejne zapisy energii startu i wznoszenia również mają różne wartości czasu i energii. Masa pakietu wymaga ponownego bilansu.
- W arkuszu śmigła `p5bipol.xlsx` prędkość projektowa zawiera `160/2.6`, mimo opisu w m/s. Przeliczenie km/h na m/s wymaga dzielenia przez 3,6. Moc zapisana jako 20 000 jest opisana jednostką kW, choć w dalszych działaniach odpowiada watom.
- W P9 pojawiają się obciążenia usterzenia rzędu 81–266 kN dla statku o masie około 261 kg, bez wiarygodnego uzasadnienia tak dużych sił. Są też różne wartości i znaki w tabelach. Nie przyjęto ich do wymiarowania.
- W P10 moment wyznaczono z bezwładności i rozpędzania wirnika. Nie zastępuje on momentu przekazującego moc na śmigło: przy 20 kW i 4000 obr/min samo `P/ω` wynosi około 47,75 Nm. Obciążenie łoża wymaga pełnego zestawu przypadków, właściwej bezwładności zespołu i kombinacji obciążeń.

## Testy

Nowe testy obejmują niezależny liczbowy przykład dźwigni, przeciążenie masowe przy ciężkim pilocie, dokładne i zdegenerowane przedziały, zgodność z istniejącymi wariantami dla wszystkich presetów, pochodną sprawdzoną różnicą skończoną, brak mutacji projektu i brak analizy pilota w UAV. Test Chrome sprawdza suwak, wybór stanu, wynik ŚC, sygnalizację przekroczenia masy, przejście do grafu oraz raport offline.
