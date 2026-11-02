# Testy projektu w przeglądarce — 2 listopada 2026

Pracę wykonano w osobnym worktree `bipol-headless-20261102`, na gałęzi `audit/headless-bipol-20261102`. Scenariusze korzystają z rzeczywistego serwera HTTP Flask na wolnym porcie, osobnej kopii bazy katalogowej i Chromium headless z Playwright. Dane wpisywano przez kontrolki aplikacji, kreator i import pliku. Odczyt JavaScript służył do porównania wyników i stanu interfejsu.

Naprawione błędy:

- Paleta Ctrl+K wskazywała nieistniejące identyfikatory. Teraz odsłania właściwe pole, także w zwiniętej grupie, trybie rozszerzonym i arkuszu semestralnym. Rozdzielono pasażerów od załogi oraz poprawiono symbole i jednostki. Profil i koszty można otworzyć w ich właściwych arkuszach.
- Polecenie raportu otwierało `/report` bez parametrów projektu. Teraz prowadzi do raportu bieżącego projektu; pobrany dokument sprawdzono offline z odrębną nazwą samolotu.
- Ctrl+Enter potwierdzał aktualność po błędzie walidacji lub awarii serwera. Status korzysta teraz z rzeczywistego stanu obliczeń. Odpowiedź dotycząca poprzednich danych pozostawia wyniki nieaktualne.
- Zdarzenie `change` wysyłane dopiero przy opuszczeniu pola unieważniało wynik już przeliczony skrótem. Porównanie z wartościami kontrolek po obliczeniu zapobiega temu w pracowni, drzewie, analizie załadowania, trendach i zaliczeniu. Wyszukiwanie i obracanie modelu nie zmieniają podstawy obliczeń.
- Przycisk pomocy przełączał motyw i otrzymywał ikonę księżyca. Oddzielono obsługę pomocy i motywu; zmiana motywu odświeża wykresy i podgląd samolotu.
- W rysunku CAD zerowa masa napędu szybowca była zastępowana przez 100 kg. Zera są zachowane, brak danych jest jawny, a sześć grup mas w tabeli i SVG odpowiada bilansowi P2/P3, łącznie z instalacjami. Usunięto niezależny podział usterzenia 60/40 i automatycznie wpisywane zatwierdzenie. Wysokość oznaczono jako szacunek z proporcji rysunku, a MTOW jako MTOW. Wznios 0° pozostaje zerowy.
- Po zapisaniu i odtworzeniu projektu automatycznie dobrana moc stawała się wejściem do podziału mas, zmieniając wyważenie i dalszą iterację. W trybie automatycznym jest wynikiem; podana moc wpływa jako założenie w trybie stałej mocy. Test ponownego obliczenia tematów 1, 7 i 32 wymaga identycznych mas, podziału mas, geometrii, oporu i zakresu ŚM.

Pełna ścieżka kreator → P1/P2 → P3 → P4 → P5 → P6 → zgodność → edycja → zapis i ponowne otwarcie → HTML/DOCX/CSV/JSON → raport offline/PDF → widok 390 i 320 px przeszła dla 13 kategorii:

| Temat | Kategoria |
|---:|---|
| 7 | Motoszybowce |
| 17 | Ultralekkie |
| 20 | Odrzutowe rekreacyjne |
| 28 | Wyścigowe i akrobacyjne |
| 32 | Szkolne |
| 42 | Turystyczne |
| 43 | Medyczne |
| 63 | Dyspozycyjne |
| 68 | Transportowe |
| 82 | Pasażerskie |
| 94 | Rolnicze i pożarnicze |
| 95 | Łodzie latające |
| 101 | Szturmowe |

Niezależne kontrole fizyczne obejmują sumę mas, `AR = b²/S`, trzy prędkości przeciągnięcia, wznoszenie z nadmiaru mocy, ŚM z sumy momentów, ciągłość masy pomiędzy fazami misji i składniki długości startu/lądowania. Dla operacji na wodzie aplikacja zachowuje informację o braku modelu hydrodynamicznego.

Dodatkowo przetestowano wszystkie siedem typów płatowców: tłokowy GA, turbośmigłowy, odrzutowiec biznesowy, motoszybowiec, szybowiec, UAV i odrzutowiec transportowy. Dla każdego porównano masy CAD z bilansem i odczytano P1–P6 oraz lot szybowy. Dla UAV zweryfikowano brak załogi, a dla szybowca brak paliwa, napędu i startu samodzielnego.

Obwiednię CS-22 sprawdzono dla Amdt 3 i modelu Pratta Amdt 2: tabela i wielokąt używają 7,5 m/s przy VD oraz właściwych granic manewrowych. Sprawdzono również silny podmuch, skalę wykresu i ujemne wznoszenie samolotu z niedostateczną mocą. Podstawa: [EASA CS-22 Amendment 3, §§22.333, 22.337, 22.341](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf).

Drzewo obliczeń przeszło przeciąganie myszą, kółko, klawiaturę, minimapę, wyszukiwanie, wszystkie zakresy projektów, rzeczywiste podstawienia liczbowe i eksport pełnych iteracji LaTeX. Na telefonie sprawdzono przesuwanie i powiększanie dwoma palcami. Po zmianie projektu stare wartości i eksporty są blokowane.

ML1 sprawdzono w czterech kompletnych arkuszach: szybowiec, śmigłowy, dane pomierzone i odrzutowiec. Zweryfikowano wykresy, JSON, raport offline, lokalny zapis, import CSV dla trzech liczb Reynoldsa z ujemnym CL, błąd dziedziny poprawki Prandtla–Glauerta przy M = 1 oraz obliczenia mobilne.

Studium motoszybowca z tematu 1 zachowuje rozpiętość 13,5 m. Oba warianty spełniły sprawdzane wymagania modelu:

| Wielkość | Bazowy AR = 18 | Wariant AR = 19,8 |
|---|---:|---:|
| Powierzchnia [m²] | 10,125 | 9,205 |
| MTOW [kg] | 370,420 | 378,116 |
| Paliwo [kg] | 31,120 | 31,142 |
| Doskonałość | 23,352 | 23,776 |
| Minimalne opadanie [m/s] | 1,076 | 1,096 |
| Dobierana moc [kW] | 19,057 | 19,561 |

Wariant bazowy jest korzystniejszy pod względem masy, mocy i minimalnego opadania; większe wydłużenie daje lepszą doskonałość. Zapis bazowy pozostał niezależny od edycji wariantu. Przywrócono go jako osobny projekt, wyeksportowano przez interfejs i ponownie zaimportowano, sprawdzając tę samą masę z dokładnością 0,001 kg.

Zaliczenie scenariusza potwierdza działanie aplikacji i spójność obliczeń. Nie oznacza spełnienia wszystkich wymagań przez każdy zestaw przykładowych założeń. Ostrzeżenia o MTOM wybranej klasy, gabarytach ładowni, zakresie modelu dla dużych liczb Macha i ocenie operacji UAV pozostają widoczne.

Uruchomienie testów:

```powershell
python -m pytest -q
node --test tests/*.test.mjs
python tests/browser_modern_ui.py
python tests/browser_design_integrity.py --serve
python tests/browser_engineering_design.py
python tests/browser_envelope_consistency.py
python tests/browser_calculation_graph.py
python tests/browser_ml1.py
```

Artefakty lokalne znajdują się w ignorowanych katalogach `work/headless-*`: wyniki JSON, zrzuty, rysunki SVG, raporty HTML/DOCX/PDF oraz plik `headless-engineering/motoglider-13_5m-baseline.bipol.json`. Skrócony zapis wyników zawiera [WYNIKI_TESTOW_HEADLESS_2026-11-02.json](WYNIKI_TESTOW_HEADLESS_2026-11-02.json).
