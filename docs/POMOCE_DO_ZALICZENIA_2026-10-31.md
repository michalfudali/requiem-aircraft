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

Nie wdrożono rozwiązania `zadanie_kolokwialne_2.pdf` (usterzenie poziome): zapis wzorów
punktu neutralnego sterowności w wykładzie 10 jest w tekście PDF niejednoznaczny, a
rozwiązanie inną metodą niż prowadzącego mogłoby wprowadzać w błąd.

## Terminy oddania (Plan na 5,0)

`SCHEDULE` w `calculations/coursework.py` z regulaminu 2026/27, slajd 8: P1 tydzień 3
(21/23.10), P2 tydzień 5 (4/6.11), P3 tydzień 8 (25/27.11), P4 tydzień 10 (9/11.12),
P5 tydzień 11 (16/18.12), P6 tydzień 14 (20/22.01.2027). Grupy 1, 7 i 8 oddają w środę,
2–6 w piątek. Karta pokazuje liczbę dni do terminu i zasady spóźnień; punktów nie
obniża automatycznie.

## Zejściówki (Materiały i zaliczenie → Zejściówki)

`calculations/lecture_quiz.py`: 103 pytania z 15 wykładów, każde z odpowiedzią wzorcową
i stroną materiału. Symulacja losuje 1–3 pytania z wybranych wykładów (najpierw
„Do powtórki” i nieocenione) i odmierza 15 minut. Samoocena i wybór wykładów zapisują
się tylko w przeglądarce.

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
