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
| Podwozie | Z kółkiem ogonowym, stałe, oś kadłuba 1,03 m nad ziemią | Układ klasy; wysokość z prześwitu śmigła 1,70 m |

## Wyniki

| Wielkość | Wartość |
|---|---|
| Masa startowa / własna / paliwo / pilot | 685,7 / 524,8 / 51,0 / 110 kg |
| W/S, W/b² | 43,5 kg/m², 1,55 kg/m² |
| Kadłub, usterzenia | l = 8,5 m, S_H = 1,36 m², S_V = 1,66 m², ramię 4,99 m |
| Biegunowa P4 | C_x0 = 0,0154, k = 0,0176, K_max = 30,4 |
| Prędkości | VS1 78,9, VS0 69,9, VA 181,7, VF 139,7, VD 316,6, Vmax 234,5 km/h |
| Wznoszenie, start, lądowanie | 6,11 m/s, 209 m, 353 m |
| Środek masy, zapas stateczności | 25,0–29,3% ŚCA, 12,7% ŚCA |
| Obciążenia | n = +5,30 / −3,15, niszczące +7,95 / −4,72 |
| Flatter, dywergencja, rewers lotek | 429 km/h (1,36 VD), 504 km/h, 413 km/h |

Aktualizacja 08.11.2026: program zalicza 32 z 32 kontroli raportu i 10 z 11 kontroli
audytu inżynierskiego. Otwartą kontrolą jest masa kompletnej zabudowy napędu.
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

## Otwarte sprawy

- **Szkic odręczny i uzgodnienie misji.** Wymaga ich BIPOL_1 i może je dostarczyć tylko autor.
  Pola `sketch_reference` i `mission_approval_reference` pozostają puste, więc lista BIPOL_1 ma 11 z 13 pozycji.
- **Profil.** Tabela profili w P2 jest pusta. Program zawiera dane tunelowe tylko NACA 23012, a dane
  kandydatów wpisuje autor z katalogu (pole `airfoil_comparison`). Korzyści wybranego profilu trzeba wykazać danymi dla warunków tego projektu.
- **Rotax 912 UL jest przewymiarowany.** Potrzeba 34,6 kW, dostępne 58 kW. Nadmiar podnosi Vmax, a przez
  VD ≥ 1,35 VH także VD do 317 km/h. Lżejszy silnik wymaga danych zużycia i mocy ciągłej.
  [Hirth publikuje](https://hirthengines.com/2301-air-cooled-two-stroke-boxer-engine-for-light-aviation-devices/)
  dla F23E punkt 660 g/(kW h) przy 6500 obr/min oraz moce opisane jako zmierzone.
  Ten zapis nie potwierdza mocy ciągłej potrzebnej do doboru w tym projekcie.
- **Zakres stosowalności modelu mas.** Wzory Raymera dotyczą samolotów lekkich: 525 kg wobec 430 kg dla ASH 31 Mi
  (21 m, silnik 41 kW). Wzory dają między innymi 36 kg instalacji elektrycznej i 53 kg podwozia, czyli wartości samolotów
  cięższych. Wyższa masa z korelacji nie dowodzi zachowawczości obciążeń ani wytrzymałości. Rozmieszczenie i rzeczywiste masy zespołów wymagają walidacji.
- **Koszty.** Metoda Corke’a daje 1,27 mln USD za egzemplarz, wielokrotnie więcej niż ceny rynkowe tej klasy,
  bo współczynniki pochodzą z dużych samolotów.
- **Ułamki startu i lądowania.** Po 2,5% masy daje 33 kg paliwa, dwie trzecie całości. To wartość z przewodnika,
  a nie pomiar zużycia motoszybowca.

- **Masa kompletnej instalacji silnika.** Producent Rotax podaje 55,4 kg dla silnika z przekładnią;
  ta masa jest chroniona w P3. Wydech, śmigło, chłodzenie, mocowanie, osprzęt i płyny muszą
  zostać objęte zestawieniem konkretnej zabudowy. Pole takiej masy i jej źródła jest dostępne
  w panelu silnika; nie wpisano przykładowej masy jako rzekomych danych producenta.
- **Materiał aeroelastyczny.** Ten wariant deklaruje kompozyt przez `technology`, lecz moduł
  aeroelastyczny odczytuje osobne `structure_material` i obecnie wybiera domyślne aluminium.
  Podane wyżej prędkości aeroelastyczne są wynikiem tego zastępczego modelu. Nie stanowią
  potwierdzenia właściwości kompozytowego skrzydła. Trzeba uzgodnić materiał, EI, GJ,
  rozkład mas, oś sprężystą oraz dane dynamiczne przed oceną rzeczywistego marginesu.
