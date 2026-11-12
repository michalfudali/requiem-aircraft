# Temat 7 — projekt motoszybowca 21 m (P1–P6)

Temat z `BIPOL1_samoloty.pdf`: motoszybowiec jednomiejscowy, rozpiętość większa niż 20 m,
zespół napędowy stały, ciągnący. Dane wejściowe są w pliku
[topic7_motoszybowiec_21m.json](../data/design_cases/topic7_motoszybowiec_21m.json), który wczytuje się
przyciskiem importu projektu. Pełne sprawozdanie P1–P6 odtwarza polecenie:

```powershell
py -3.11 tools/audit_topic7.py --input data/design_cases/topic7_motoszybowiec_21m.json --output work/topic7-projekt
```

Temat nie podaje misji. Liczby misji są założeniami autora i wymagają uzgodnienia z prowadzącym.

## Decyzje projektowe

| Decyzja | Wartość | Uzasadnienie |
|---|---|---|
| Rozpiętość, wydłużenie | b = 21 m, Λ = 28, S = 15,75 m² | Λ = 28 odpowiada konstrukcjom o dużej rozpiętości z bazy (Stemme S10: 28,3); VS0 mieści się w założonych 72 km/h |
| Prędkość przelotowa | 115 km/h TAS na 2000 m | Notatki prowadzącego przyjmują K_przelot = 0,94 K_max; przy 140 km/h Cz wynosiłoby około 0,6 Cz,opt i założenie nie byłoby spełnione |
| Zasięg | 600 km, 60 min oczekiwania | Zachowano założenia wcześniejszego studium |
| Próba porównawcza | 17 rodzin motoszybowców bez balastu wodnego, z napędem w kadłubie | MTOM konstrukcji z balastem wodnym zawiera balast, a tego samolot jednomiejscowy nie przewozi. Dopasowanie daje C = −0,128 bez wymuszania znaku, R² = 0,25 |
| Masa własna | Domknięta sumą mas zespołów, K_P3 = 1,103 | BIPOL_3: wynik analizy masowej może wymagać powtórzenia projektu |
| Struktura | Kompozyt (Raymer, tab. 15.4) | Typowa dla klasy |
| Silnik | Rotax 912 UL, 58 kW, 268 g/(kW h) w punkcie 75% mocy | Wybrana propozycja z dokumentacją; większa moc 912 ULS nie usuwa przewymiarowania |
| Mechanizacja | Klapy zwykłe, lotki zewnętrzne (η ≥ 0,67) | Przy klapolotkach na całej rozpiętości oderwanie zaczyna się w strefie lotek |
| Podwozie | Z kółkiem ogonowym, stałe, oś kadłuba 1,08 m nad ziemią | Śmigło 1,70 m; poziomy prześwit 230 mm wg CS-22.925(a) |

## Wyniki

| Wielkość | Wartość |
|---|---|
| Masa startowa / własna / paliwo / pilot | 655,4 / 496,8 / 48,6 / 110 kg |
| W/S, W/b² | 41,6 kg/m², 1,49 kg/m² |
| Kadłub, usterzenia | l = 8,5 m, S_H = 1,36 m², S_V = 1,65 m², ramię 5,02 m |
| Biegunowa P4 | C_x0 = 0,01704, k = 0,01470, K_max = 31,59 |
| Prędkości | VS1 77,4, VS0 68,5, VA 178,3, VF 137,0, VD 308,5, Vmax 228,5 km/h |
| Wznoszenie, start, lądowanie | 6,48 m/s, 196 m, 350 m |
| Środek masy, zapas stateczności | 25,0–29,5% ŚCA, 12,5% ŚCA |
| Obciążenia | n = +5,43 / −3,43, niszczące +8,14 / −5,14 (podmuchy) |
| Flatter, dywergencja, rewers lotek | 515 km/h (1,67 VD), 605 km/h, rewers nieobliczony; model zastępczy |

Aktualizacja 12.11.2026: program zalicza 32 z 32 kontroli raportu i 10 z 12 kontroli
audytu inżynierskiego. Otwarte są masa kompletnej zabudowy napędu i potwierdzenie aeroelastyczne konstrukcji.
Samo zaliczenie kontroli modelu wstępnego nie zastępuje analizy wytrzymałościowej
ani wykazania zgodności. Poniżej wskazano także ograniczenia materiałowe aeroelastyczności.

Główne wielkości sprawdza rachunkiem niezależnym od modułów obliczeniowych test
[test_topic7_design.py](../tests/test_topic7_design.py): sumę mas, przeciągnięcie, paliwo przelotu
całkowane krokami 1 km, masę skrzydła ze wzoru Raymera, prędkości JAR 22.335 i położenie ŚC z tabeli mas.

## Poprawki aplikacji wynikłe z tego projektu

| Moduł | Błąd | Poprawka |
|---|---|---|
| Masy zespołów | Silnik nie zależał od przeliczenia masy pustej i przy skalowaniu tracił masę | Masa bazowa ze źródła lub udokumentowana masa pełnej instalacji nie są pomniejszane; część szacowana dzieli pozostały budżet, a instalacja paliwowa jest w grupie instalacji |
| Masy zespołów | Silnik turbinowy liczony wskaźnikiem tłokowego 0,94 kg/kW | 0,35 kg/kW dla klas turbinowych |
| Bilans masy | Brak drogi od sumy mas zespołów do masy własnej | Opcja domknięcia P3 → P2 ze współczynnikiem K_P3 pokazanym w raporcie |
| Misja | Oczekiwanie liczone z K_max szacunkowym, przelot z biegunowej P4 | Oba odcinki korzystają z biegunowej P4 |
| Wrażliwość | Zmiana K o 10% nie zmieniała masy | Zmiana działa przez biegunową bilansu |
| Osiągi P5 | Stała sprawność śmigła, sprzeczna z charakterystyką P4 | η(V) z tej samej krzywej co tabela P4; dotyczy też Vmax i VD |
| Podwozie | Rozstaw 0,24 b dawał 5 m przy mocowaniu do kadłuba | Ograniczenie średnicą kadłuba; wysokość z prześwitu śmigła |
| Podwozie | Koła główne stały w 45% ŚCA niezależnie od kryterium z wykładu 7 | Położenie z warunku kąta α przy 0,9 Cz,max + 3°; kontrola 118 projektów przestała zgłaszać błąd |
| Podwozie | Brak układu z kółkiem ogonowym | Nowa opcja z kryteriami wykładu 4: 13° i 20° dla ŚC, kąt postojowy |
| Wyważenie | Brak kontroli BIPOL_3, pkt 7 | Rzut ŚC między kołami, także dla samolotu pustego |
| Kadłub | 9,45 m przy b = 21 m oraz 8,4 m przy b = 36,6 m bez pasażerów (usterzenie 183 m²) | Szybowce do 8,5 m; samoloty turbinowe co najmniej 0,6 b |
| Przepisy | Paliwo na 0,5 h z JAR 22.25(a)(2) tylko w opisie | Kontrola w raporcie |
| Tematy | Kategoria akrobacyjna niezgodna po przejściu na klucze JAR; temat 25 bez układu tandem | Porównanie po kategorii, poprawka katalogu |
| Raport | Założenia misji opisane jako wymagania tematu; brak kropek mnożenia; `prop`, `land`; opis klap przy klapolotkach | Etykieta „Założenie misji”, poprawione wzory i nazwy |
| Import | Plik samych parametrów odrzucany mimo opisu „importowalny” | Import przyjmuje taki plik |
| Profil | P3 liczył płat zawsze danymi NACA 23012 | Opcja `airfoil_model` z danymi wybranego profilu: gradient, α₀, Cm i parabola oporu |
| JAR 25.121 | Gradient z jednym silnikiem niepracującym nie był liczony | Liczony z biegunowej startowej P4 przy V2; dobór mocy i ciągu go uwzględnia |
| Dobór napędu | Wymagana Vmax nie wchodziła do mocy z biegunowej P4 | Wchodzi; tematy wyścigowe osiągają wymaganą prędkość |
| Przykłady | Presety bez domknięcia z biegunową P4 i bez przejścia do właściwej kategorii | Otwierane w aplikacji działają jak tematy oficjalne |
| Próba | Samoloty ultralekkie porównywane z cięższymi tej samej klasy | Próba ograniczona do 660 kg, gdy jest co najmniej 8 rodzin |

## Otwarte sprawy

Korekta prześwitu 12.11.2026: kod odwracał minima dla układów podwozia.
CS-22.925(a) wymaga 180 mm przy kole przednim i 230 mm przy kółku ogonowym.
Aktualna wysokość osi w tym wariancie wynosi 1,08 m. Obliczenie poziome nie
potwierdza wszystkich położeń i przypadków ugięcia wymaganych przepisem;
[źródło, wzory i zakres oceny](PRZESWIT_SMIGLA.md).

Aktualizacja geometrii 12.11.2026: OpenVSP zachowuje teraz pełne 98 rzędnych
FX 61-163 we wszystkich przekrojach skrzydła. Testy potwierdzają ich zachowanie
po zapisie i ponownym otwarciu `.vsp3`. Aktualny katalog kreatora i zapisane
wcześniej projekty są obsługiwane oddzielnie; [opis aktualizacji](KATALOG_I_PROFILE_OPENVSP.md).

- **Szkic odręczny i uzgodnienie misji.** Wymaga ich BIPOL_1 i może je dostarczyć tylko autor.
  Pola `sketch_reference` i `mission_approval_reference` pozostają puste, więc lista BIPOL_1 ma 11 z 13 pozycji.
- **Profil.** Wybrano FX 61-163, porównując cztery profile na podstawie biegunowych XFOIL
  przy Re = 10⁶. To dane obliczeniowe; potrzebne są dane doświadczalne dla warunków projektu
  i ocena przejścia laminarnego, zabrudzenia oraz rozkładu Re po rozpiętości.
- **Dobór silnika.** Dostępne 58 kW daje Vmax = 228,5 km/h, a warunek
  VD ≥ 1,35 VH podnosi VD do 308,5 km/h. Lżejszy silnik wymaga danych zużycia i mocy ciągłej.
  [Hirth publikuje](https://hirthengines.com/2301-air-cooled-two-stroke-boxer-engine-for-light-aviation-devices/)
  dla F23E punkt 660 g/(kW h) przy 6500 obr/min oraz moce opisane jako zmierzone.
  Ten zapis nie potwierdza mocy ciągłej potrzebnej do doboru w tym projekcie.
- **Zakres stosowalności modelu mas.** Kontrola na 21 konstrukcjach z bazy daje rozrzut korelacji
  około −14%…+20%; zgodność sum mas nie potwierdza poprawności każdej grupy ani konstrukcji nowego skrzydła.
  Rozmieszczenie i rzeczywiste masy zespołów wymagają walidacji.
- **Koszty.** Korelacje Corke’a wymagają walidacji dla tej klasy i wielkości serii.
  Wyniku dydaktycznego nie można traktować jako aktualnej oferty produkcyjnej.
- **Ułamki startu i lądowania.** Po 2,5% masy daje około 32 kg paliwa, dwie trzecie całości. To wartość z przewodnika,
  a nie pomiar zużycia motoszybowca.

- **Masa kompletnej instalacji silnika.** Producent Rotax podaje 55,4 kg dla silnika z przekładnią;
  ta masa jest chroniona w P3. Wydech, śmigło, chłodzenie, mocowanie, osprzęt i płyny muszą
  zostać objęte zestawieniem konkretnej zabudowy. Pole takiej masy i jej źródła jest dostępne
  w panelu silnika; nie wpisano przykładowej masy jako rzekomych danych producenta.
- **Aeroelastyczność.** Moduł uwzględnia teraz `technology=composite`; materiał skrzydła można
  określić osobno. EI = 271 324 N·m² i GJ = 438 710 N·m² pozostają szacunkiem umownego kesonu.
  W zakładce Weryfikacja można podać źródłowe EI/GJ, masę liniową, osie i promień bezwładności.
  Program nie oblicza rewersu lotek bez ich modelu; usunięto proporcję 0,82 V_div.
  Potrzebne są rzeczywista struktura laminatu, rozkłady mas i sztywności oraz analiza niestacjonarna
  i badania. Szczegóły: [podstawa modelu](AEROELASTYCZNOSC.md).
