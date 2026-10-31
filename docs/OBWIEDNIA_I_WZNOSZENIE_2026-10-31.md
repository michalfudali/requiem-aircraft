# Obwiednia V–n i wykres prędkości pionowej — 31.10.2026

Zmiany od `7a1a854`, w osobnym worktree `bipol-envelope-20261031`,
na gałęzi `fix/vn-envelope-20261031`.

## Podstawa modelu

Dla CS-22 domyślnie zastosowano współczynnik z Amendment 3,
§22.341. Wybór starszej metody Pratta z Amendment 2 pozostaje dostępny
w formularzu i jest zapisywany w projekcie. Import pliku bez tego pola
ustawia jawnie Amendment 3, także po wcześniejszym użyciu Pratta.

Źródła: [EASA CS-22 Amdt 3](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf),
drukowane strony 36–39 (§22.333–22.341), oraz
[CS-22 Amdt 2](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%202.pdf).
Wzory, diagramy i pierwiastek sześcienny w regule VD sprawdzono na
renderowanych stronach PDF; samo wydobycie tekstu gubi układ wzorów.

Przy `c = S/b` i `mu = 2(m/S)/(rho0*c*a)` nowy wariant liczy:

```text
H/c = 12.17 + 0.191*mu
r = mu/(H/c)
k = 0.96*r/(0.475+r)
```

Wariant Pratta zachowuje `k = 0.88*mu/(5.3+mu)`. Przyrost liniowy
`dn = rho0*V*a*k*U/(2*W/S)` ogranicza się dla CS-22 osobno:

```text
n_positive = min(1 + dn,  1.25*(V/VS1)^2)
n_negative = max(1 - dn, -1.25*(V/VS1)^2)
```

Przy ograniczeniu dodatniej gałęzi przyrosty względem 1 g nie muszą
być równe. Poprzednie użycie dodatniego ograniczenia także dla gałęzi
ujemnej mogło zaniżać jej obciążenie. Arkusz P6 pokazuje teraz obie
wartości, wzór H/c i źródło wybranego modelu.

## Spójność obliczeń i prezentacji

Wcześniejsza obwiednia wypadkowa szybowca utrzymywała granice manewrowe
do VD i korzystała tam z podmuchu 15 m/s, mimo że podstawowy diagram
oraz tabela podawały odpowiednio pochyłe odcinki i 7,5 m/s. Ponownie
przycięta statyczną parabolą gubiła też część obciążeń podmuchowych.

Obecnie gałęzie manewrowe szybowca biegną A–D oraz G–E. Obwiednia
wypadkowa jest zewnętrzną granicą osobnych przypadków, bez dodawania
obciążeń manewru i podmuchu. Linie podmuchów łączą ich obliczone wartości
w prędkościach charakterystycznych. Próbowanie uwzględnia dokładne
wierzchołki, dzięki czemu wykres zawiera obciążenia wymiarujące.

Prędkość przeciągnięcia i przeliczenie TAS→EAS korzystają z wartości
niezaokrąglonych. Wykresy oraz raporty oznaczają EAS, pokazują granicę
wypadkową i osobną pętlę klap. Skala obejmuje wszystkie rysowane serie.
Wartość przeciążenia klap w panelu P6 pochodzi z wybranej kategorii,
zamiast stałego +2 dla szybowca, który w tym modelu ma +4.
Przebieg klapowy ma paraboliczną granicę przeciągnięcia i początek
w (0, 0); cztery charakterystyczne wiersze tabeli zachowano oddzielnie.
Raport określa zakres tej pętli jako manewrowy. Dodatkowe przypadki
podmuchów z klapami wymagają osobnego modelu i nie są wykazywane jako
policzone.

Wykres prędkości pionowej zachowuje ujemne wartości, zamiast obcinać
je do zera. Oś TAS i opis dostępności wyjaśniają wynik; dla testowego
samolotu z mocą 0,001 kW maksimum wynosi −2,47 m/s. Krzywa oraz punkt
maksimum mieszczą się w skali.

To obliczenia wstępne, dla przyjętych współczynników aerodynamicznych
i odniesienia ISA na poziomie morza. Model nie jest analizą dynamiczną
całego płatowca. Dla CS-23 zachowano metodę Amdt 4, a dla CS-25
uproszczenie Pratta. Współczesna
[CS-23 Amdt 6, AMC2 23.2200](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-normal-category-CS-6-AMC-GM-5?erules-id=ERULES-1963177438-6854)
również odwołuje się do Amdt 4 jako środka spełnienia; sam wykres nie
wykazuje pełnej zgodności certyfikacyjnej.

## Weryfikacja

```powershell
python -m pytest -q
python tests/browser_envelope_consistency.py
python tests/browser_design_integrity.py --in-process
```

Nowe 17 przypadków Python obejmuje niezależne podstawienie obu modeli,
asymetrię ograniczeń, wszystkie 10 presetów, obciążenia przy VD, obecność
skrajnych obciążeń w wielokącie, zgodność arkusza i walidację wejścia.

Nowy test Chrome wykonuje rzeczywisty import i edycję, przełączenie
modelu, odświeżenie, import starszego projektu, widok mobilny 390 px
i eksport dwóch raportów HTML/PDF działających offline. Obserwuje
wywołania rysowania bez zmieniania danych aplikacji: sprawdza jednostki,
widoczność wszystkich gałęzi (także przy podmuchach daleko przekraczających
obciążenia manewrowe) oraz niepłaską krzywą z ujemnymi wartościami.
Oba raporty PDF mają po osiem stron A4, wszystkie z tekstem; brak błędów
składu wzorów i błędów JavaScript. Artefakty etapu zapisano w ignorowanym
`work/envelope-20261031/`.

Pełny zestaw: **1301 testów Python**, 278,93 s, bez błędów i pominięć;
**36 testów JavaScript** oraz **5 nowych scenariuszy Chrome** przeszło.
Dodatkowo przeszło **13 pełnych scenariuszy oficjalnych tematów**, po
jednym z każdej z 13 grup: tematy 7, 17, 20, 28, 32, 42, 43, 63, 68,
82, 94, 95 i 101. Każdy obejmował kreator, wszystkie moduły projektu,
edycję i ponowne obliczenie, odświeżenie, HTML/PDF/DOCX/JSON/CSV oraz
widoki 320 i 390 px. Brak błędów JavaScript, HTTP i kontrolowanych
niezgodności bilansu masy, sił oraz momentów. Łącznie **18 scenariuszy
Chrome**. Artefakty pełnych scenariuszy znajdują się w
`work/design-integrity-20261030/` (nazwa katalogu istniejącego testu),
a ich zbiorcze potwierdzenie w `work/envelope-20261031/validation-summary.json`.
