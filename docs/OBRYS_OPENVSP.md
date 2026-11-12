# Obrys skrzydła P3 i geometria OpenVSP

Stan: 12.11.2026. Oba generatory — Studio oraz adapter analiz — korzystają ze
wspólnej definicji obrysu w `calculations/vsp_wing.py`.

## Wznios i skos

W P3 i podglądzie aplikacji `b` oraz `S` opisują rzut skrzydła na płaszczyznę
poziomą. W OpenVSP parametr sekcji `Span` jest rozpiętością przed rzutowaniem
przez wznios. Potwierdzają to obliczenia przesunięć `ty`, `tz`, `toff` oraz
`ComputeTotalProjSpan` w [kodzie OpenVSP 3.55](https://github.com/OpenVSP/OpenVSP/blob/OpenVSP_3.55.0/src/geom_core/WingGeom.cpp).

Dla stałego wzniosu Γ i skosu ćwierćcięciw Λ w rzucie:

```math
\Delta s = \frac{\Delta y}{\cos\Gamma},\qquad
\Lambda_{\mathrm{SDK}}=\arctan(\tan\Lambda\cos\Gamma).
```

Drugi wzór jest konieczny: samo wydłużenie sekcji przesuwałoby linię
ćwierćcięciw do tyłu. Cięciwy pozostają zgodne z P3. Każda sekcja używa jawnie
sterowania przez rozpiętość, cięciwę początkową i końcową. Wznios jest absolutny,
więc kolejne segmenty nie dodają go do poprzednich.

Zachodzą zależności:

```math
b_{\mathrm{SDK}}=b/\cos\Gamma,\qquad
S_{\mathrm{SDK}}=S/\cos\Gamma,\qquad
b_{\mathrm{SDK,projected}}=b.
```

OpenVSP oblicza `TotalAR` jako kwadrat `TotalProjectedSpan` podzielony przez
`TotalArea`, co daje AR·cos Γ przy tych definicjach. Nie zmieniamy cięciw ani
powierzchni rzutu, aby sztucznie zrównać ten parametr z AR w P3. Analizy
aerodynamiczne nadal otrzymują powierzchnię odniesienia P3.

Dla tematu 7: b = 21 m, S = 15,75 m², Γ = 3,5°. Po zapisie i ponownym otwarciu
modelu odczytano `TotalProjectedSpan` = 21 m, `TotalSpan` = 21,039242 m,
`TotalArea` = 15,779432 m²; przemnożenie ostatniej wielkości przez cos Γ daje 15,75 m².
Modele zachowują profil FX 61-163 i sprawdzone wcześniej położenia podwozia.

## Obrys eliptyczny i złożony

Poprzednie dwa segmenty Studio zaniżały powierzchnię elipsy o około 5,3%.
Adapter analiz miał inną, pięciosegmentową aproksymację. Obecnie oba używają
32 segmentów o stacjach:

```math
y_i=\frac b2\sin\theta_i,\qquad
c_i=c_0\cos\theta_i,\qquad
\theta_i=\frac{i\pi}{64},\quad i=0,\ldots,32.
```

Cięciwa u nasady oraz zerowa cięciwa końcówki pozostają dokładne. Cięciwy
pośrednie otrzymują wspólny mnożnik 1,0004146665, wyznaczony z warunku zachowania
analitycznej powierzchni elipsy. Korekta poniżej 0,042% dotyczy rzędnych w stacjach;
nie jest granicą błędu obrysu między stacjami. To jawna aproksymacja segmentowa.
Średnia cięciwa aerodynamiczna obliczona z segmentów jest sprawdzana względem
analitycznej elipsy z tolerancją względną 0,1%.

W obrysie złożonym usunięto zaokrąglanie położenia załamania do centymetrów.
Skos ćwierćcięciw jest zgodny z P3 również w centropłacie. Po zmianie wymiarów
każda sekcja jest aktualizowana osobno: SDK przelicza wtedy zależne pola
`Area` i `Aspect`. Jedna aktualizacja po ustawieniu wszystkich sekcji pozostawiała
niektóre wartości z wcześniejszej geometrii.

## Kontrola rzeczywistej geometrii i błędów SDK

Testy odczytują natywne parametry i całkują obrys uzyskany z `CompVecPnt01`
na 2049 stacjach. Sprawdzają pole rzutu z tolerancją względną 10⁻⁵, rozpiętość,
cięciwy, skos ćwierćcięciw i średnią cięciwę aerodynamiczną. Macierz obejmuje
pięć obrysów, dwa generatory i wznios 0°, +12° oraz −6°.

Nie używa się samego `CurvedArea` jako dowodu pola: dla nierównomiernych sekcji
elipsy w lokalnym SDK 3.55 odczyt tego parametru różni się od bezpośredniego
całkowania powierzchni. W próbie b = 13,73 m, S = 24,1683205 m², Γ = 0°
`CurvedArea` wyniosło 24,0237688 m², a niezależne całkowanie obrysu na 2049
stacjach dało 24,1683179 m². Błędny odczyt nie jest kompensowany zmianą poprawnej bryły.

Naprawiono też opróżnianie kolejki błędów. `GetErrorLastCallFlag` pozostaje
ustawione po ostatnim `PopLastError`; nie jest licznikiem kolejki. Pętle sprawdzają
teraz `GetNumTotalErrors`. Regresja z rzeczywistym błędem SDK działa w procesie
z limitem czasu, więc wykryje również ponowne zawieszenie. Niepoprawny obrys jest
odrzucany przed usunięciem istniejącego modelu.

Panel pokazuje obrys i wymiary rzutu **przy budowie** modelu oraz informację o
aproksymacji elipsy. Ręczne modyfikacje CAD mogą zmienić geometrię względem P3.

## Weryfikacja

- Pełny backend dla etapu obrysu (`5b5faed`): **2506 zaliczonych, 61 pominiętych**,
  bez błędów. Pokrycie **94,33%** (13 499 z 14 311 linii). Pominięcia dotyczą
  natywnego SDK niedostępnego dla Pythona 3.11; te przypadki sprawdzono w 3.13.
- Pełny zestaw Chromium po tej zmianie: **54 zaliczone scenariusze**,
  w tym cztery z rzeczywistym backendem OpenVSP.
- 76 zaliczonych testów natywnych i adaptera, w tym 30 kombinacji obrysu,
  generatora i wzniosu oraz zachowanie profili po zapisie `.vsp3`.
- 35 zaliczonych kontroli danych obrysu, adaptera i przekazywania błędów profilu.
- Sześć zaliczonych scenariuszy Chromium: katalog oraz temat 7 z profilem FX
  w obrysie trapezowym i eliptycznym przy szerokości 390 i 1440 px.
- 55 zaliczonych testów JavaScript.

Dowody lokalne: `work/planform-full.xml`, `work/planform-full-coverage.xml`,
`work/planform-all-browser.xml`, `work/planform-native-final.xml`, `work/planform-data-final.xml`,
`work/planform-browser-final.xml`, `work/planform-js.log`. Bieżące modele i
manifesty: `work/topic7-audit/` oraz `work/topic7-projekt/`.
