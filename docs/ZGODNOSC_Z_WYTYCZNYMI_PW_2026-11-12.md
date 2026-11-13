# Zgodność programu z wytycznymi PW (materiały w `scraped_materials/bipol`)

Stan: 12.11.2026. Porównanie wykonano z dokumentami: *Opis projektów* (BIPOL1_Opis_Projektow.pdf), *Ogólne wymagania
dotyczące wykonywania projektów* (Wymagania.pdf), *Schemat postępowania przy rysowaniu kadłuba* (Schemat_projektu.pdf),
BIPOL_1–BIPOL_5, *Analiza masowa*, *Pomoce do wymiarowania usterzeń*, wykłady 4 i 7. Przykładem jest projekt tematu 7
(`data/design_cases/topic7_motoszybowiec_21m.json`). Zgodność z BIPOL_1 opisuje osobno `ZGODNOSC_BIPOL_1.md`.

Oznaczenia: **jest** — program to robi; **autor** — wymaga pracy własnej studenta, program daje dane; **luka** — brak.

## Opis projektów — zakres P1–P6

| Projekt | Wymaganie | Stan | Gdzie |
|---|---|---|---|
| P1 | Opis koncepcji, cechy geometryczne, aerodynamiczne, osiągowe | jest | raport P1, „Koncepcja samolotu” |
| P1 | Rysunek koncepcyjny, szkice ręczne | autor | wzór arkusza A4; pole `sketch_reference` |
| P1 | Analiza trendów (opcjonalna) albo uzasadnienie parametrów | jest | P1, sześć wykresów, osiem średnich |
| P1 | Tabela wyników do kolejnych projektów | jest | „Wyniki projektu 1…” |
| P2 | Profil misji, masa startowa i własna, wybór metody | jest | P2; metoda proporcji lub iteracyjna |
| P2 | Dobór profilu: co najmniej trzy profile, kryteria, uzasadnienie | jest dla tematu 7; autor dla pozostałych | pole `airfoil_comparison`; tabela profili |
| P2 | Analiza wrażliwości masy | jest | tabela wrażliwości |
| P2 | Wykres obciążenia ciągu od obciążenia powierzchni z punktem | jest | wykres doboru |
| P2 | Analiza kosztów | jest | metoda Corke’a; zastrzeżenie dla klas lekkich |
| P3 | Rysunek w trzech rzutach na papierze milimetrowym A2, profil 200 mm | autor | program daje wymiary, wzory A4 i A2 z siatką oraz profil 1:1 |
| P3 | Analiza masowa, skrajne położenia ŚC w funkcji załadunku | jest | tabela mas, stany załadowania, pilot 55/110 kg |
| P3 | Charakterystyki płata Cz(α), Cm(α), Cx(Cz) | jest | P3; dane wybranego profilu (`airfoil_model`) |
| P3 | Rozkład Schrenka dla Cz = 1 i szacunek Cz,max | jest | P3 |
| P4 | Cz(α), Cm(α), Cz(Cx), K i E w funkcji α i Cz | jest | P4, tabela i wykresy |
| P4 | Biegunowa prędkości dla dwóch skrajnych ŚC, V_ek, V_opt | jest | P4 |
| P4 | Mechanizacja płata | jest | P4, klapy 20°/40° |
| P4 | Charakterystyka wysokościowa i prędkościowa napędu, dobór śmigła | jest | P4 |
| P5 | Wykres ofertowy: w, γ, Vmin, Vγ, Vw, Vmax, pułapy | jest | P5; od 12.11 także czas wznoszenia (BIPOL_5, rys. 5.1) |
| P5 | Zasięg i długotrwałość dla h = 0 lub wysokości przelotowej | jest | P5, trzy wysokości, trzy metody |
| P5 | Długość i czas startu | jest | P5 |
| P5 | Porównanie osiągów założonych z obliczonymi i krytyczna ocena z elementami do poprawy | jest | od 12.11 lista „Krytyczna ocena projektu” zawsze, nie tylko przy niespełnionych wymaganiach |
| P6 | Obwiednia wg przepisów wybranych w P1, punkty wyliczone lub założone z uzasadnieniem | jest | P6, paragrafy JAR przy każdej wartości |
| P6 | Obwiednia od mechanizacji na tle obwiedni samolotu, tabela prędkości i współczynników | jest | P6 |

## Ogólne wymagania dotyczące wykonywania projektów

| Pkt | Wymaganie | Stan |
|---|---|---|
| 2 | Raport A4, strona tytułowa: autor, grupa, prowadzący, numer i tytuł projektu, data, pole oceny | jest (dane wpisuje autor) |
| 3 | Obliczenia powtarzalne w tabelach; niepowtarzalne ze wzorem, źródłem, danymi i wynikiem | jest (arkusz obliczeń z podstawieniami) |
| 3 | Symbole zdefiniowane przy pierwszym wystąpieniu albo w spisie oznaczeń; jednostki przy wzorach anglosaskich | jest; od 12.11 „Spis ważniejszych oznaczeń” we wstępie |
| 4 | Osie wykresów z wielkością i jednostką; źródło danych z literatury | jest |
| 5 | Rysunki zgodne z zasadami rysunku technicznego, z podaną skalą | autor; arkusze programu mają skalę liniową |
| 7 | Numeracja stron, tabel, rysunków | jest (numeracja stron przy wydruku) |
| 8 | Teczka z opisem | jest (okładka teczki `/report/project/folder_cover`) |

## Schemat postępowania przy rysowaniu kadłuba i BIPOL_3

Od 12.11 raport P3 zawiera tabelę „Kontrola rysunku według schematu postępowania” (`calculations/drawing_checks.py`).

| Krok | Wymaganie | Stan |
|---|---|---|
| 1–6 | Załoga, kąt widoczności, kabina, ładunek, silnik pod linią widoczności, osłona | autor; program podaje wymagany kąt widoczności |
| 7 | Średnica śmigła, M końcówki ≤ 0,85 | jest |
| 8–9 | ŚC załogi, ładunku i napędu; położenie ŚCA | jest (dobór położenia skrzydła, zakres 25–35% ŚCA) |
| 10 | Koła główne: kąt między pionem przez ŚC a punktem styku; odległość śmigła od podłoża | jest; od 12.11 wysokość podwozia wynika ze śmigła dobranego w P4 także w układzie z kołem przednim |
| 11 | Prosta podłoża na postoju (kółko tylne) lub kąt natarcia przy starcie (koło przednie) | jest |
| 12, 14 | Zachowanie cech objętościowych usterzeń | jest |
| 14 | Kryterium wyjścia z korkociągu | jest od 12.11 (część steru kierunku poza cieniem usterzenia poziomego ≥ 30%) |
| BIPOL_3 pkt 7 | Rzut ŚC między kołami, także dla samolotu pustego | jest |
| BIPOL_3 pkt 9 | Momenty bezwładności | jest |

## BIPOL_4 i BIPOL_5

| Wymaganie | Stan |
|---|---|
| Jakość dopasowania funkcji aproksymującej biegunową | jest od 12.11: R² i największe odchylenie w P4 |
| Sprawdzenie prędkości minimalnej w konfiguracji do lądowania z wymaganiem i przepisem | jest |
| Charakterystyki napędu wg przewodnika ML | jest |
| Osiągi w funkcji wysokości i wykres ofertowy z czasem wznoszenia | jest |
| Zasięg i długotrwałość trzema metodami, zakres prędkości z wykresu ofertowego | jest |
| Obwiednia wg rozdziałów C przepisów JAR | jest |

## Pozycje „autor” wynikają z samych wytycznych

Pozycje oznaczone „autor” nie są brakami programu, które dałoby się usunąć. Wytyczne przypisują je studentowi:

- Opis projektów, P1: „szkice ręczne”.
- Opis projektów, P3: rysunek „na papierze milimetrowym”.
- BIPOL_1: uzgodnienie misji z prowadzącym.
- BIPOL_3: dobór profilu z katalogu.
- Wymagania, pkt 6: samodzielność pracy.

Program, który wykonałby te czynności za studenta, naruszyłby wytyczne. Zgodność polega na tym, że program
dostarcza dane, wzory arkuszy i miejsca na odniesienia (`sketch_reference`, `mission_approval_reference`,
`airfoil_comparison`).

Stan 13.11.2026 dla tematu 7:

- `engine_installation_mass` jest zaliczona. Masę zabudowy Rotax 912 UL (83,15 kg) zestawiono z danych producenta,
  zważonej zabudowy i masy śmigła. Szczegóły: `PROJEKT_TEMAT_7_2026-11-06.md`, „Otwarte sprawy”.
- Jedyna otwarta kontrola audytu to `aeroelastic_substantiation`. Przewodniki PW jej nie wymagają.
  Jest zawsze otwarta, bo potwierdzenie wymaga modelu konstrukcji, badań drgań i prób w locie.

## Luki i sprawy poza programem

- **Rysunek A2 na papierze milimetrowym** wykonuje autor; program daje od 12.11 wzór A2 z siatką w skali dwukrotnie większej niż A4.
- **Szkic odręczny i uzgodnienie misji z prowadzącym**: wyłącznie autor.
- **Dobór profilu dla tematów innych niż 7**: autor wpisuje dane co najmniej trzech profili ze źródłem.
- **Samodzielność pracy** (Wymagania, pkt 6): raport z programu jest pomocą obliczeniową; projekt oddaje student.
