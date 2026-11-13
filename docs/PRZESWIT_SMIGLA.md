# Prześwit śmigła i układ podwozia

Aktualizacja 12.11.2026. W trzech miejscach kodu i w części dawnych testów
odwrócono przypisanie wartości do układów podwozia. Poprawiono wspólną regułę
na podstawie dokumentu źródłowego; dawne oczekiwania testów nie stanowiły
niezależnej kontroli tego wymagania.

## Podstawa wymiaru

[CS-22 Amendment 3, strona 80, CS 22.925(a)](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf)
podaje co najmniej:

| Układ | Prześwit śmigła od ziemi |
| --- | --- |
| Koło przednie | 180 mm |
| Kółko ogonowe | 230 mm |

Wymiar dotyczy podwozia ugiętego statycznie, najbardziej niekorzystnej kombinacji
masy, środka ciężkości i ustawienia łopat oraz krytycznego położenia podczas
startu, kołowania i postoju poziomego. CS-22 wymaga ponadto dodatniego prześwitu
w opisanych w przepisie przypadkach opony bez ciśnienia i dobicia goleni.
Sam wymiar poziomy nie wykazuje spełnienia całego paragrafu.

Takie samo przypisanie 180/230 mm znajduje się w klasycznym
[CS-23 Amendment 1, CS 23.925(a), strona 83 PDF](https://www.easa.europa.eu/sites/default/files/dfu/CS-23%20Amdt%201%20Combined.pdf).
Warunki szczególne tego wydania CS-23, w tym resor płaski oraz śmigło z tyłu,
wymagają osobnego sprawdzenia. Przywołanie wymiarów nie jest potwierdzeniem
zastosowania tej podstawy certyfikacji do każdej kategorii projektu.

W rejestrze źródeł ujęto również [CS-25 Amendment 15, CS 25.925(a), strona
125 PDF](https://www.easa.europa.eu/sites/default/files/dfu/CS-25%20Amendment%2015.pdf).
Wartości 18/23 cm są takie same, lecz jego dodatkowy przypadek dotyczy opony
bez ciśnienia i dobitej goleni jednocześnie. P3 wybiera odpowiedni paragraf
według kategorii; raport zapisuje go jako źródło przepisu, wraz z dokumentem.

## Obliczenia i dane autora

`calculations/propeller_clearance.py` jest wspólnym źródłem reguły dla geometrii,
kalkulatora napędu i kalkulatora podwozia. Pole `landing_gear_type` ma
pierwszeństwo przed dawnym użyciem `gear_type` jako nazwy układu. W głównym
projekcie `gear_type` określa bowiem podwozie stałe lub chowane.

Wstępny dobór wysokości osi pojedynczego śmigła ciągnącego w nosie:

```math
H_{osi}=\max\left(0{,}8D_{kad},\;D_P/2+h_{min},\;H_{min,autor}\right).
```

Wysokość jest przyjętym wymiarem roboczym przy statycznym obciążeniu podwozia,
a nie obliczonym ugięciem konkretnej goleni. Pole w kreatorze i założeniach
jest opisane jako **minimalna wysokość osi**; wynik może być większy od
wpisanej wartości ze względu na średnicę śmigła.

Prześwit poziomy i jego zapas:

```math
h_P=H_{osi}-D_P/2,\qquad \Delta h_P=h_P-h_{min}.
```

P3, raport oraz drzewo obliczeń pokazują dane, odejmowanie promienia śmigła
i porównanie z odpowiednim minimum. Wynik `nominal_passed` dotyczy tego
warunku wymiarowego, a `certification_compliant` pozostaje `null`.
Arkusz rozwija również maksimum wyznaczające wysokość osi, pokazując średnicę
kadłuba, roboczą proporcję 0,8, średnicę śmigła i dodatkowe minimum autora.
Każda wielkość wejściowa ma opis pochodzenia. Kontrola niezależnego
podstawienia obejmuje także tę wysokość, a nie tylko końcowe odejmowanie.

Kalkulator napędu odejmuje zadane ugięcie od podanej wysokości osi. Kalkulator
podwozia zachowuje konserwatywne oszacowanie skoku goleni wraz z ugięciem opony;
metadane wskazują tę podstawę. Skok dynamiczny nie jest pomiarem ugięcia
statycznego. Wyniki tych kalkulatorów także nie są pełnym wykazaniem zgodności.

Porównanie wykorzystuje wartości przed zaokrągleniem. Prześwit 0,2299 m
przy wymaganych 0,230 m nie jest zaliczany, mimo że zapis do trzech miejsc
po przecinku wygląda tak samo. Tolerancja 10⁻¹² m usuwa jedynie błąd arytmetyki
zmiennoprzecinkowej, a nie rzeczywisty niedobór wymiaru.

Dla wielu śmigieł i zabudowy innej niż pojedyncze śmigło w nosie wynik głównego
projektu pozostaje nierozstrzygnięty do ustalenia wysokości osi. Dla operacji
z wody wymagana jest linia wodna i geometria zabudowy; ocena naziemna nie jest
podstawiana jako wynik nad wodą. Samolot bez śmigła nie dostaje fikcyjnego
prześwitu 0,50 m ani zaliczonego sprawdzenia śmigła.

## Temat 7

W wariancie 21 m / 115 km/h śmigło ma średnicę 1,70 m i znajduje się w nosie,
a podwozie ma kółko ogonowe. Wysokość osi wzrosła z błędnych 1,03 m do 1,08 m:

```math
h_P=1{,}08-1{,}70/2=0{,}23\;\mathrm{m}.
```

Po ponownym domknięciu P3→P2 masa startowa wynosi 655,4 kg, pusta 496,8 kg,
paliwo 48,6 kg. Położenie środka masy pozostaje w zakresie 25,0–29,5% ŚCA,
a zapas stateczności przy tylnym ŚC wynosi 12,5% ŚCA. Oba warianty studium
ponownie zaliczają 13/13 niezależnych kontroli liczbowych. Uzgodnienie misji,
szkic, kompletna zabudowa napędu i potwierdzenie konstrukcji pozostają otwarte.

Regresja natywna otwiera ponownie `.vsp3` i odczytuje poziom ziemi z bryły
podwozia oraz wysokość osi i średnicę z bryły śmigła. Kontrola używa promienia
tarczy, aby uwzględnić najbardziej niekorzystny azymut łopaty. Nie ogranicza
się do porównania pola prześwitu zwróconego przez ten sam moduł.

Wstępne kontrole: 179 testów obliczeń i arkusza oraz cztery scenariusze
Chromium, następnie rozszerzony zestaw 25 kontroli reguły i braku fałszywych
wyników; środowisko OpenVSP zaliczyło 96 testów. Ślady wykonania i aktualne
studia są lokalnie w `work/clearance-*.xml`, `work/topic7-audit/`
i `work/topic7-projekt/` worktree tej poprawki.

## Końcowa weryfikacja — 13.11.2026

- Pełny backend: **2534 zaliczone, 81 pominiętych** z powodu braku SDK w
  Pythonie 3.11; pokrycie **94,44%** (`clearance-verified-full.xml`).
- Python 3.13 / OpenVSP 3.55: **96 zaliczonych**, obejmujących pominięte
  przypadki SDK oraz oba generatory (`clearance-verified-native.xml`).
- Chromium: **63 różne scenariusze zaliczone**. Pierwszy pełny przebieg miał
  58 zaliczeń, limit czasu podczas kliknięcia nawigacji w jednym scenariuszu
  i cztery pominięcia wymagające natywnego backendu. Ponowiony scenariusz
  nawigacji oraz wszystkie przypadki katalogu i natywnego backendu zaliczyły
  siedem testów; wynik zbiorczy nie dubluje powtórzonych przypadków.
- JavaScript: **55 zaliczonych**; obie bazy SQLite mają poprawną integralność.
- Oba studia nadal spełniają **13/13 niezależnych kontroli**. Zapisane modele
  otwarto ponownie i porównano tarczę śmigła z rzeczywistą dolną granicą kół.
- Odświeżono 13 raportów HTML, sprawdzonych offline bez błędów JS i KaTeX.
  Zbiorczy PDF ma **95 stron**, bez pustych stron; wzory obejmują pełny dobór
  wysokości osi i przypisy do odpowiedniego dokumentu.

Dowody, sumy plików i wynik po połączeniu dwóch przebiegów przeglądarki:
`work/clearance-verified-summary.json`, `work/clearance-verified-*.xml`,
`work/topic7-projekt/combined_report_checks.json`. Weryfikowany kod po scaleniu
z kreatorem: `e6602b6`. Te kontrole nie zamykają pozostałych wymagań konstrukcyjnych.
