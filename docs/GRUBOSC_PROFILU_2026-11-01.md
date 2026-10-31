# Grubość wybranego profilu i regresja obwiedni — 01.11.2026

Prace w osobnym worktree `bipol-profile-thickness-20261101`, na gałęzi
`fix/profile-thickness-20261101`, od `39264f0`. Zmiany równoległego agenta
na `master` zostają zachowane przy integracji.

## Problem i zachowanie

Oznaczenie NACA 0015 pozwalało narysować profil o nominalnej grubości 15%,
podczas gdy geometria skrzydła, oszacowanie oporu i sztywności korzystały
z niezależnego domyślnego `t/c = 0,12`. Teraz źródło grubości jest jawne:

- `profile_thickness_mode=auto`: jawnie wybrany profil NACA 4/5-cyfrowy
  dostarcza nominalne t/c z oznaczenia; wklejone rzędne mają pierwszeństwo
  przed nazwą i dostarczają maksimum różnicy powierzchni przy tym samym x.
- `profile_thickness_mode=assumed`: autor podaje grubość niezależnie od
  rysunku. Rozbieżność z geometrią pojawia się w panelu i raportach P3/P4.
- Bez jawnie wybranego profilu pozostaje założenie t/c (domyślnie 0,12).
  Roboczy kandydat P2 nie staje się automatycznie zatwierdzonym profilem.
  Nieznane oznaczenie lub niepoprawne rzędne również pozostawiają założenie,
  z opisem brakujących danych; program nie tworzy zastępczej geometrii.
- Automatyczna grubość poza zakresem modelu skrzydła 0,04–0,30 powoduje
  błąd z wyjaśnieniem. Sprzeczna blokada t/c wymaga odblokowania parametru
  albo świadomego wyboru ręcznego założenia.

Rozstrzygnięcie następuje przed wymiarowaniem. Wynik trafia do powierzchni
omywanej, współczynnika kształtu, korelacji ściśliwości oraz wstępnego
oszacowania sztywności kesonu. Źródło podano także w arkuszu obliczeń.
Usunięto również ukryte zastępowanie t/c przez granice 0,06–0,24 w modelu
ściśliwości: korzysta on z wartości zaakceptowanej dla skrzydła, podanej
teraz także w jego wynikach. Korelacja pozostaje oszacowaniem wstępnym.
Wartość wynikowa jest nieedytowalna w formularzu; przejście do ręcznego
trybu przywraca edycję. Import starszego projektu ustawia domyślne wartości
niezapisanych pól trybu i t/c, zamiast dziedziczyć je po poprzednio
otwartym projekcie; jawnie zapisane wartości pozostają zachowane.

Maksimum grubości wklejonego konturu liczy się w sumie węzłów obu
łamanych. Różnica dwóch interpolacji liniowych jest na każdym odcinku
liniowa, więc próbkowanie co 0,5% cięciwy mogło pomijać maksimum.
Obliczenia zachowują pełną precyzję rzędnych, a zaokrąglenia dotyczą
tabeli, rysunku i pola formularza. Odrzucane są nieskończone rzędne,
zerowa grubość i przecinające się powierzchnie.

Nominalne t/c NACA i pionowa różnica rzędnych narysowanego, dyskretyzowanego
profilu wygiętego są rozróżniane. Definicje oparto na
[dokumencie NASA opisującym oznaczenia NACA](https://ntrs.nasa.gov/api/citations/19860021221/downloads/19860021221.pdf)
oraz [opisie geometrii skrzydła NASA](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/wing-geometry/).

Sama geometria nie dostarcza charakterystyk aerodynamicznych wybranego
profilu. Referencyjna tabela Paturskiego nadal dotyczy NACA 23012;
raport wymaga właściwych danych dla Re i Macha. Model sztywności jest
wstępny i używa jednego t/c dla całej rozpiętości. Nie stanowi analizy
rzeczywistego dźwigara ani potwierdzenia odporności na flatter.

## Wskazana wcześniej obwiednia szybowca

Poprawka obwiedni była już opublikowana w `ed62a3e`. Dodano osobną regresję
odtwarzającą wskazane zagrożenie: VD używa 7,5 m/s, a granice manewrowe
kategorii U przy VD wynoszą +4/−1,5, w porównaniu z +5,3/−2,65 przy A/G.
Wielokąt zbiorczy uwzględnia zewnętrzną granicę obu osobnych przypadków.
Test obejmuje przypadek z dominującym manewrem oraz z dominującym podmuchem,
z przyrostem obliczonym niezależnie od tabeli wynikowej programu.

Podstawa: [EASA CS-22 Amendment 3](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf),
§22.333(c), §22.337 i §22.341. Test Chrome sprawdza także wykres i raport P6.

## Weryfikacja

Polecenia i szczegółowe wyniki zapisano w ignorowanym katalogu
`work/profile-thickness-20261101/`. Nowe testy obejmują propagację t/c,
precyzję maksimum między dawnymi punktami próbkowania, pierwszeństwo
rzędnych, blokady, zakres modelu, brak geometrii i źródło w raportach.
Każdy preset przechodzi obliczenia z NACA 0015 i kontrolę podstawień
arkusza. Chrome sprawdza tryby grubości, raport P3/P4 bez sieci,
telefon 390 px, przeładowanie i import starszego projektu.

Wyniki:

| Zakres | Wynik |
| --- | --- |
| Pełny `pytest -q` po integracji `7aeffac` | 1407 zaliczonych, 314,19 s |
| Końcowa integracja `60788a7`: profil, ściśliwość, arkusz, obwiednia, klapy, koszty, pytania i podstawa projektu | 229 zaliczonych, 36,60 s |
| Testy JavaScript po końcowej integracji | 36/36 |
| Chrome: projektowanie 13 kategorii, tematy 7, 17, 20, 28, 32, 42, 43, 63, 68, 82, 94, 95, 101 | 13/13 |
| Chrome: nowe scenariusze grubości i raporty P3/P4 | 8/8, powtórzone po końcowym scaleniu |
| Chrome: izolacja profilu, opóźnione odpowiedzi, wydruk i eksport | 17/17 |
| Chrome: obwiednia, metody CS-22 i raport P6 | 5/5 |
| Chrome: kolokwium i pytania | zaliczone przy 1400 i 390 px |
| Chrome: kosztorys, zapis i przeładowanie | zaliczone po końcowym scaleniu |

Przebieg wszystkich kategorii obejmował kreator, P1–P6, zgodność, edycję,
ponowne obliczenie, zapis, przeładowanie, eksport HTML/JSON/CSV/DOCX,
PDF raportu bez sieci oraz widoki 320/390 px. Zapisane kontrole fizyczne
nie wykazały rozbieżności. PDF P3/P4 obejrzano po renderowaniu; opis
rozbieżności występuje w obu częściach i mieści się na stronie.

Po pełnej regresji dołączono nowszy `master` (`bb5dde9`): parametry
kosztorysu i dodatkowe pytania. Konflikt w `loadProjectIntoForm` rozwiązano
z zachowaniem domyślnych pól profilu oraz kosztów. Zwiększono wersję
`app.js` do 36. Końcowe 229 testów oraz Chrome profilu i kosztów dotyczą
już tego połączenia; pełny przebieg 13 kategorii wykonano przed tym
ostatnim dołączeniem. Logi: `pytest-integrated.txt`, `pytest-final-merge.txt`,
`node-final.txt`, `browser-all-categories.txt`, `browser-final-thickness.txt`,
`browser-integrated-state.txt`, `browser-envelope.txt`,
`browser-integrated-exam.txt`, `browser-final-costs.txt`.
