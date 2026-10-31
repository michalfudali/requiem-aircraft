# Wyważenie i ocena stanów załadowania — 31.10.2026

Zmiany powstały w worktree `bipol-loading-20261031`, na gałęzi
`improve/loading-envelope-20261031`, od commitu `822956f`.

## Podstawa i znalezione błędy

[Materiały BIPOL-I](https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/BIPOL/BIPOL-I)
odsyłają do [instrukcji projektu P3](https://itlims-zsis.meil.pw.edu.pl/pomoce/BIPOL/BIPOL_3_2010.pdf).
Analiza masowa na stronach 3–4 wymaga bilansu momentów, różnych stanów
załadowania i kontroli położenia środka masy. Stosowane w aplikacji dodatkowe
kryterium zapasu 5% ŚDA jest kryterium projektu wstępnego, a nie uniwersalnym
progiem certyfikacyjnym.

- Masy zespołów i ramiona były zaokrąglane przed obliczeniem momentów.
  Wpływało to na środek masy, dobór położenia skrzydła i ocenę stateczności.
- Zaokrąglanie zapasu mogło uznać 4,96% za spełniające próg 5%.
- Tabela semestralna P3 stosowała własny przedział 18–38% ŚDA, niezależny
  od kryteriów obliczeniowych. Tabela P6 zawsze pokazywała dopuszczalność.
- Zakres wędrówki środka masy w P6 odczytywano z nieistniejącego pola,
  przez co wyświetlał się jako zero.
- Dane wyważenia P3 i model momentu pochylającego P4 traciły precyzję
  na kolejnych etapach przekazywania wyników.

## Zmiana

Masy, ramiona, momenty i współczynniki modelu momentu pozostają niezaokrąglone
w obliczeniach. Formatowanie liczb odbywa się w widokach. Każdy stan otrzymuje
sumę momentów względem nosa, zapas stateczności oraz osobną ocenę wyważenia
i minimalnego zapasu. Stan pusty nie otrzymuje oceny kryteriów w locie.

Tabele P3/P6 i eksport P3 korzystają z tych samych wyników. Raport zawiera
moment w kg·m oraz zapas Kn w procentach ŚDA. Wykres pokazuje niezależne
przypadki załadowania i granicę zapasu 5%; nie łączy przypadków arbitralną
linią sugerującą kolejność załadunku. Obliczony zakres nie jest oznaczany
jako zatwierdzona obwiednia użytkowania.

Pozostaje to model skupionych mas z przyjętymi ramionami. Szczegółowe
rozmieszczenie foteli, kolejność opróżniania wielu zbiorników i wpływ ruchu
podwozia wymagają dalszego rozwoju modelu.

## Odtworzenie sprawdzeń

```powershell
python -m pytest -q
python -m pytest -q tests/test_balance_precision.py
python tests/browser_balance_precision.py
```

Nowe 23 przypadki regresyjne obejmują wszystkie 10 presetów: zachowanie
masy i pierwszego momentu, niezmienność względnego wyważenia przy zmianie
skali geometrii, zgodność P3/P4, próg 4,96/5,04% oraz bilans zrzutu 70 kg.

Scenariusze Chrome importują projekt, korzystają z obu tabel i eksportują
raport P3 do HTML/PDF: samolot szkolny, wariant z zablokowaną cechą
usterzenia V_H=0,4 oraz UAV. Wariant małego usterzenia ma dodatni, lecz
niewystarczający zapas i musi otrzymać czerwone oznaczenie. Sprawdzany jest
też rzeczywisty zakres wyważenia, stan naziemny i brak błędów JavaScript.

Artefakty lokalne: `work/balance-precision-20261031/` — wyniki testów,
zrzuty ekranu, zaimportowane projekty oraz raporty HTML/PDF.

Wynik końcowy: **1196 testów Python zaliczonych** (281,96 s, bez pominięć),
w tym istniejące kontrole całego katalogu 110 tematów; **36 testów JavaScript
zaliczonych**; **3 scenariusze Chrome zaliczone**, bez błędów strony.
PDF-y mają odpowiednio 17, 17 i 16 stron; wszystkie strony są A4 i zawierają
tekst. Sprawdzono również wizualnie tabelę wariantu niespełniającego kryterium.
