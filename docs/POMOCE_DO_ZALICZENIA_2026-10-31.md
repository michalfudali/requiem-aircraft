# Pomoce do zaliczenia BIPOL I — 31.10.2026

Źródła: strona przedmiotu BIPOL-I i lokalne kopie materiałów w `scraped_materials/bipol/`.
Wykłady `okBIPOL_1_handout_*.pdf` są zaszyfrowane hasłem przedmiotu; do opracowania
pytań odczytano je lokalnie. Treść wykładów nie jest kopiowana do programu: pytania
i odpowiedzi wzorcowe są własnym opracowaniem z odnośnikiem do strony materiału.

## Zadanie kolokwialne (Materiały i zaliczenie → Zadanie kolokwialne)

Treść: `zadanie_kolokwialne_1.pdf`. Dane zależą od liczby liter imienia (X) i nazwiska (Y);
liczy je przeglądarka, a do serwera trafiają tylko X i Y. Moduł
`calculations/exam_wing.py`, API `POST /api/exam/wing-loads`.

| Część | Metoda |
|---|---|
| Geometria | S z V_S0 = 61 kt (JAR-23.49(c)) i C_z,max = 2,0; b = √(ΛS); c_r, c_k, c_g, SCA i jej położenie dla płata trapezowego. |
| Obwiednia | JAR-23 §23.321–23.341 dla kategorii normalnej, commuter, użytkowej i akrobacyjnej: n₁ i n₂, V_A, V_G, V_C = max(V_C,min; V_A), V_D, podmuchy 66/50/25 ft/s z K_g, a = a∞/(1 + a∞/(πeΛ)). Punkt B (commuter) ograniczony linią C_z,max. Ujemna gałąź przy V_D: 0 lub −1 wg §23.333(b)(3). |
| Rozkład C_z | Schrenk na czterech paskach półrozpiętości dokładnie jak w arkuszach `Wing_load_taper_*.pdf` (test odtwarza trzy arkusze co do 0,01 N). |
| Momenty i siły tnące | P_i = n[L_i − g(m_str,i + m_p,i)], sumy od końcówki do wewnętrznej krawędzi paska; struktura proporcjonalnie do pola paska, paliwo w części 0,25–0,75 półrozpiętości. Dodatkowo przypadek bez paliwa, który dla danych zadania zawsze wymiaruje moment u nasady. |

Każdy krok ma wzór, podstawienie i wynik (arkusz `Sheet`), a test sprawdza każdy wynik
niezależnym wzorem dla 1600 kombinacji X, Y. Formularz „Sprawdź swoje wyniki” porównuje
wartości studenta z tolerancją 2% (współczynniki obciążeń: 0,02).

Nie wdrożono rozwiązania `zadanie_kolokwialne_2.pdf` (usterzenie poziome). Wykład 10 (s. 9)
podaje tłumienie pochylania od usterzenia jako C_mq,H = −((x_H − x_N)/C_a)·(S_H/S)·(V_H/V)²·a₁,
a wyprowadzenie dla q̂ = q·C_a/V (np. Etkin, Cook) daje kwadrat ramienia ((x_H − x_N)/C_a)².
Położenie punktu neutralnego sterowności, a z nim przednie położenie ŚC z kryterium dδ_H/dn,
zależy od tego wyboru — warto go wyjaśnić z prowadzącym, zanim program poda rozwiązanie.

## Terminy oddania (Plan na 5,0)

`SCHEDULE` w `calculations/coursework.py` z regulaminu 2026/27, slajd 8: P1 tydzień 3
(21/23.10), P2 tydzień 5 (4/6.11), P3 tydzień 8 (25/27.11), P4 tydzień 10 (9/11.12),
P5 tydzień 11 (16/18.12), P6 tydzień 14 (20/22.01.2027). Grupy 1, 7 i 8 oddają w środę,
2–6 w piątek. Karta pokazuje liczbę dni do terminu i zasady spóźnień; punktów nie
obniża automatycznie.
Strona przeglądu pokazuje najbliższy termin (dla wybranej grupy albo oba dni).

## Zejściówki (Materiały i zaliczenie → Zejściówki)

`calculations/lecture_quiz.py`: 103 pytania z 15 wykładów, każde z odpowiedzią wzorcową
i stroną materiału. Symulacja losuje 1–3 pytania z wybranych wykładów (najpierw
„Do powtórki” i nieocenione) i odmierza 15 minut. Samoocena i wybór wykładów zapisują
się tylko w przeglądarce.
Przycisk „Drukuj pytania” tworzy arkusz A4 z pytaniami wybranych wykładów i odpowiedziami
wzorcowymi od nowej strony. W zadaniu kolokwialnym „Losowe dane” pozwalają ćwiczyć inne warianty X, Y.

## Poprawka obwiedni P6

`calculations/envelope.py`: dla kategorii akrobacyjnej ujemna gałąź obwiedni manewrowej
kończy się przy V_D na n = −1, a nie na 0 (CS-23 Amdt 4 / JAR-23 §23.333(b)(3));
dla kategorii normalnej i commuter pozostaje 0. Raport P6 podaje tę wartość.

## Sprawdzenie

- `py -3.11 -m pytest tests -q` — nowe testy: `tests/test_exam_wing.py`,
  `tests/test_lecture_quiz.py`, terminy w `tests/test_coursework.py`, obwiednia
  akrobacyjna w `tests/test_aeronautical_audit.py`.
- `python tests/browser_exam.py --in-process --base-url http://bipol.test` — Chrome,
  1400 i 390 px, ustalona data 31.10.2026.

## Profil o cięciwie 200 mm (P3) — poprawka

Opis projektu 3 wymaga rysunku wybranego profilu o cięciwie 200 mm na arkuszu z samolotem.
Poprzedni generator dawał błędne rzędne:

| Profil | Było | Jest |
|---|---|---|
| NACA 23012 | ugięcie 41,6% cięciwy (stała k₁ = 361,4 linii 210 przy r = 0,2025 linii 230), górna powierzchnia 94 mm nad cięciwą | ugięcie 1,84% przy 15%, grubość 12% przy 30%; rzędne zgodne z tabelą Abbotta i von Doenhoffa do 0,15% cięciwy |
| Wortmann FX 61-163, NASA SC(2)-0412 | rzędne wpisane ręcznie (grubość 18,6% i 14,3% zamiast 16,3% i 12%) | brak wzoru — autor wkleja rzędne z katalogu (.dat, format Seliga lub Lednicera) |
| Inny profil | po cichu rysowano NACA 24xx | komunikat z listą katalogów; nic nie jest podstawiane |

`calculations/airfoils.py` liczy analitycznie każdy profil NACA 4-cyfrowy i 5-cyfrowy
(linie szkieletowe 210–250 bez odgięcia, skalowane pierwszą cyfrą). Tabela podaje osobno x
górnej i dolnej powierzchni, bo grubość odkłada się prostopadle do linii szkieletowej.
Rysunek SVG ma wymiary w milimetrach i odcinek kontrolny 100 mm; przycisk „Drukuj w skali 1:1”
otwiera stronę A4 poziomo do wydruku w skali 100%. API: `GET /api/airfoil/200mm?airfoil=NACA 23012`
lub `POST /api/airfoil/200mm` z polami `airfoil` i `coordinates`.
Dla profilu NACA wybranego w P2 raport P3 zawiera tabelę rzędnych i osobną stronę A4 poziomo
z rysunkiem 1:1 (sprawdzone w PDF z Chrome: cięciwa 200,3 mm, odcinek kontrolny 99,9 mm).
Oznaczenie profilu (`airfoil`) i wklejone rzędne (`airfoil_coordinates`) zapisują się w projekcie:
profil autora zastępuje roboczego kandydata P2 i trafia do raportów P2 i P3 (także rysunek 1:1
profilu z katalogu). Raport zaznacza, że charakterystyki profilu w obliczeniach płata pochodzą
z przykładowej tabeli 2.1 przewodnika, jeśli wybrano inny profil niż NACA 23012.

Uwaga do modelu P2/P4: charakterystyki profilu (C_m,SA = −0,065, a = 6,18 1/rad, α₀ = −1,8°)
pochodzą z tabeli 2.1 przewodnika Paturskiego, który sam zaznacza, że są przykładowe. Dla
NACA 23012 „Theory of Wing Sections” podaje moment względem środka aerodynamicznego bliski
zera (ok. −0,01); w opracowaniu warto użyć danych wybranego profilu.
Dla profili NACA program podaje też wynik teorii cienkiego profilu (α₀, c_m,c/4; test odtwarza
przykład Andersona dla NACA 2412: −2,077° i −0,053); dla NACA 23012 daje to c_m,c/4 = −0,013.

## Audyt inżynierski i pytania na obronę — poprawki

- Początek przeciągnięcia porównuje się z rzeczywistą wewnętrzną krawędzią lotki
  (η = 1 − prześwit końcówki − rozpiętość lotki), a nie ze stałym progiem 0,65.
  Zalecenie „zmniejsz zbieżność” zastąpiono jednoznacznym „zwiększ λ (skrzydło mniej
  zbieżne)” — mniejsze λ przesuwa maksimum c_z/C_z ku końcówce.
- Wzorcowa odpowiedź o miejscu przeciągnięcia nie twierdzi już, że przy umiarkowanej
  zbieżności maksimum wypada przy kadłubie (tak jest tylko dla płata prostokątnego);
  podaje η projektu i ocenę względem lotek.
- Pytanie o punkt projektowy nazywa rzeczywiste ograniczenia aktywne; szybowiec bez napędu
  dostaje pytania o W/S i o prędkości najmniejszego opadania i największej doskonałości
  zamiast o moc i V_x/V_y.
- Kąt przewrócenia na bok: wymaganie z wykładu 4 (< 60°), zalecenie Torenbeeka ≤ 55°
  (wcześniej 55° przypisywano Raymerowi, który dopuszcza 63°).
- Próg Kn ≥ 5% ŚDA opisano jako przyjęty w programie, a nie „wymóg regulaminu”.

## Własności lotne — ruch spiralny

`calculations/flying_qualities.py` liczył wartość własną spirali ze złym znakiem:
λ_s = +(g/V)(C_lβ·C_nr − C_lr·C_nβ)/(−C_lp·C_nβ). Według kryterium stateczności spiralnej
(Nelson, Cook) spirala jest stateczna, gdy C_lβ·C_nr > C_lr·C_nβ, więc λ_s = −(g/V)(…)/(…).
Dla samolotu Navion (dane z podręcznika Nelsona) poprzedni wzór dawał λ_s = +0,0104 (niestateczna),
poprawiony −0,0091 (stateczna), w zgodzie z kryterium. Efekt wzniosu −0,15·Γ zastąpiono teorią
pasową −(a·Γ/6)(1 + 2λ)/(1 + λ) z poprawką na położenie płata (±1,5°); wcześniejsza wartość była
ok. 8 razy za mała. Presety mają teraz łagodnie niestateczną spiralę (czas podwojenia 11–435 s),
jak większość samolotów lekkich; test sprawdza, że większy wznios ją stabilizuje.

## Aerosprężystość

Prędkość rozbieżności skrętnej liczy się z klasycznego wyniku dla prostego skrzydła
wspornikowego, q_D = π²·GJ/(4·e·c·a·l²); poprzednio w mianowniku było 8, więc V_D,div była
o √2 za mała (a z nią prędkość rewersu lotek, przyjmowana jako 0,82 V_div).

Do decyzji: model flatteru (`v_flutter = 0,88·b·ω_α·√μ·…` z częstościami skalowanymi umownie,
np. GJ/50 000) daje dla presetów wartości rzędu 10 000–40 000 km/h, czyli bez znaczenia
fizycznego. BIPOL I nie wymaga analizy flatteru; rzetelne oszacowanie potrzebuje częstości
giętnej i skrętnej skrzydła oraz położeń osi sprężystej i środka masy przekroju.
