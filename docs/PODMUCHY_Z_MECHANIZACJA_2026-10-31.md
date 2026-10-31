# Podmuchy z wychyloną mechanizacją — 31.10.2026

Praca w osobnym worktree `bipol-flaps-20261031`, na gałęzi
`fix/flap-gust-loads-20261031`. Początek: `ed62a3e`; dołączono późniejszy
`master` z `6698605`, zachowując zmiany drugiego agenta dotyczące profili,
audytu i pomocy dydaktycznych.

## Wymagania i model

[CS-22 Amdt 3, §22.345(b)(1)](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf),
strona 40, wymaga rozpatrzenia konfiguracji klap do lądowania, manewru
do +4 i podmuchów obu znaków 7,5 m/s do VF. Dla metody
[CS-23 Amdt 4, §23.345](https://www.easa.europa.eu/sites/default/files/dfu/CS-23%20Amendment%204_0.pdf),
strona 81, odpowiadające wartości wynoszą +2 i 7,62 m/s.
W obu dokumentach cecha masowa używa średniej cięciwy geometrycznej
`S/b` (§22.341, strona 39; §23.341, strona 79), co poprawiono także
dla obwiedni czystej. Formuły sprawdzono na renderowanych stronach PDF.

Nowy `flap_envelope.py` liczy osobne przypadki przy masie startowej,
na poziomie morza ISA, w EAS:

```text
delta_n = rho0 * VF * a * k * U / (2 * W/S)
n_gust_positive = 1 + delta_n
n_gust_negative = 1 - delta_n
n_limit_positive = max(n_manoeuvre, n_gust_positive)
n_limit_negative = min(0, n_gust_negative)
n_ultimate = 1.5 * n_limit
```

W konfiguracji do lądowania nie zastosowano redukcji podmuchu przez
statyczną granicę przeciągnięcia. To jawne, liniowe oszacowanie.
Model przyrostu Cz od mechanizacji przesuwa charakterystykę o stałą
wartość, dlatego wykorzystuje tę samą pochodną `a` co dla płata czystego.
Dla CS-22 wybór Amendment 3 lub starszego Pratta obejmuje także nowe
przypadki klapowe.

Podmuchy i manewry nie sumują się. Wielokąt wypadkowy obejmuje ich
zewnętrzną granicę, z dokładnymi wierzchołkami przy VS0, VAf i VF.
Gałąź manewrowa zachowuje paraboliczną granicę przeciągnięcia.
Wielkości wymiarujące i niszczące pozostają niezaokrąglone aż do
prezentacji.

## Wyniki i interfejs

`envelope.flap` podaje stosowalność, podstawę, założenia, oba znaki
podmuchu przy VF, krzywe, granicę wypadkową i obciążenia do wymiarowania.
`envelope.configuration_limits` porównuje osobne konfiguracje czystą
i do lądowania, wskazując przypadek decydujący dla każdego znaku.
Dotychczasowe `envelope.limits` opisują konfigurację czystą.

Nowy wykres SVG, tabelę obciążeń i podsumowanie dodano do panelu P6
oraz raportu. Arkusz pokazuje wzór z podstawieniem, oba znaki podmuchu,
porównanie z manewrem, mnożnik 1,5 i porównanie konfiguracji. Wykresy SVG
mają odrębne identyfikatory przycinania, także gdy oba panele korzystają
z tego samego rodzaju wykresu.

Opcja „Brak klap” jest dostępna w formularzu. Po jej wyborze geometria
ma zerową powierzchnię klap, zachowując położenie lotek; karta dydaktyczna
nie opisuje już klapy szczelinowej. Bez ruchomej mechanizacji natarcia
nie ma obwiedni konfiguracji do lądowania: VF i obciążenia są `null`,
krzywe i tabela puste. Poprzednie wyniki są usuwane także po przełączeniu
projektu i odświeżeniu. Stały slot nie jest traktowany jak wychylane
urządzenie; ruchomy slot i klapa Kruegera uruchamiają osobny przypadek.

## Zakres

To model obciążeń wstępnych płata, a nie obliczenie lokalnych sił klap,
momentów zawiasowych, strugi śmigła ani wszystkich ustawień przelotowych.
Dla transportowych zachowano jawnie nazwane oszacowanie Pratta i
dydaktyczną regułę VF; nie zastępują one analizy dynamicznej wymaganej
przez [CS-25.345](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-large-aeroplanes-cs-25?page=15).
Raport nie przypisuje temu uproszczeniu zgodności certyfikacyjnej.

## Weryfikacja

```powershell
python -m pytest -q
python tests/browser_flap_gust.py
python tests/browser_envelope_consistency.py
python tests/browser_airfoil.py --in-process
python tests/browser_design_integrity.py --in-process
```

22 nowe przypadki Python obejmują niezależne podstawienia obu metod
CS-22, CS-23 i oszacowania transportowego, rozróżnienie S/b i ŚCA,
oba znaki obciążenia, pełną precyzję, przypadek decydujący, 10 presetów,
brak klap, stały slot, ruchomą mechanizację natarcia oraz raport P6.

Nowy Chrome przechodzi siedem scenariuszy: oba modele CS-22, samolot
szkolny, usunięcie klap, samą klapę Kruegera, przywrócenie klap i samolot
transportowy. Sprawdza rzeczywiste kontrolki, geometrię, podpisy, oba
panele, brak starych wyników, odświeżenie, szerokość 390 px i trzy raporty
HTML/PDF otwierane offline. Artefakty: `work/flap-gust-20261031/`.
