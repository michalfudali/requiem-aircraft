# Diagnostyka ściśliwości — 01.11.2026

Osobny worktree `bipol-compressibility-20261101`, od `8388289`.

## Poprawione rozbieżności

- Cyfra 6 wewnątrz oznaczenia NACA 0016, 2416 czy 23016 nadawała profilowi
  rodzinę laminarną i zwiększała κ_A. Rozpoznawanie obejmuje teraz całe
  oznaczenie. Dla klasycznych i nierozpoznanych profili κ_A = 0,87 jest
  jawnym założeniem wymagającym kalibracji. NACA serii 6 otrzymuje wartość
  referencyjną 0,87, NASA SC(2) — 0,95.
- Zastąpiono nieudokumentowany odstęp M_dd−M_kr i rozdzielony wzór oporu
  metodą Korna/Locka. Zachowano ciągłość krzywej i jej pochodnej.
- Kryteria i przyrost oporu korzystają z wartości niezaokrąglonych.
  Nie ma ukrytych ograniczeń M_dd do 0,4–0,98 ani M_kr do co najmniej 0,35.
- Diagnostyka przelotu używa Cz z równowagi siły nośnej przy MTOW, zadanym
  TAS i wysokości ISA, zamiast Cz największej doskonałości.
- Skos dotyczy linii połówek cięciw. Wyznaczono jej sieczną z geometrii
  ćwiartek cięciw, cięciwy nasadowej i końcowej oraz rozpiętości. Dla
  obrysów łamanych i krzywoliniowych pozostaje to jawne przybliżenie.
- Punkty poza zakresem korelacji zachowują wyliczone M_dd/M_kr, mają
  status niedostępnej diagnostyki oporu, a dla M ≥ 1 nie podaje się
  pozornego współczynnika Prandtla–Glauerta.

Podstawa: [W.H. Mason, Configuration Aerodynamics, §7.5.2](https://archive.aoe.vt.edu/mason/Mason_f/ConfigAeroTransonics.pdf),
wzory (7-4)–(7-9):

```text
M_dd = κ_A/cos(χ50) − (t/c)/cos²(χ50) − Cz/(10 cos³(χ50))
M_kr = M_dd − (0,1/80)^(1/3)
ΔCx,wave = 20 max(0, M−M_kr)^4
```

Oznaczenia serii zweryfikowano w
[NACA Report 824, Summary of Airfoil Data](https://ntrs.nasa.gov/api/citations/19930090976/downloads/19930090976.pdf).
Bez separatorów prawidłowe oznaczenie pięciocyfrowe ma pierwszeństwo;
oznaczenia z wewnętrznym separatorem, np. 63-012, są rozróżniane.

## Zakres wyników

Bilans osiągów nadal wykorzystuje referencyjną biegunową Paturskiego.
Korn/Lock stanowi oszacowanie równoważnego skrzydła. Jego wynik wymaga
kalibracji κ_A i analizy lokalnych profili, Cz oraz skosu wzdłuż rozpiętości.
Nie jest automatycznie dodawany jako zweryfikowana korekta całego samolotu.

Przelot powyżej oszacowanego M_kr otrzymuje ostrzeżenie zakresu modelu:
osiągi i zasięg wymagają biegunowej właściwej dla M i Cz. To odrębny warunek
od dodatniego marginesu M_dd−M. Audyt nie nazywa go już marginesem
bezpieczeństwa. Wynik poza zakresem korelacji także wymaga dalszej analizy.
Ocena dotyczy zadanej prędkości i wysokości przelotu przy MTOW, a nie całej
obwiedni prędkości ani wykazania zgodności certyfikacyjnej.

P4 pokazuje źródło, punkt przelotu i ograniczenia. Arkusz zawiera
geometrię skosu, Cz, κ_A, M_dd, M_kr i diagnostyczny przyrost oporu.
Ostrzeżenie pozostaje w raportach częściowych P4 i P5 oraz podsumowaniu
zakresu modelu. Publiczny format zachowuje pola do prezentacji i dodaje
surowe dane w `compressibility.terms`.

## Weryfikacja

- Pełny zestaw: **1451 zaliczonych**, 329,54 s.
- Dodatkowe kontrole korelacji, granic i raportów API: **40 zaliczonych**.
- Arkusze, audyt i dotychczasowe testy profilu: **122 zaliczone**.
- JavaScript: **36/36**.
- Chrome: **9/9**, bez błędów JavaScript; raporty P4/P5 bez sieci,
  widok 390 px, korekta prędkości i import spoza zakresu formularza.

Test niezależnego przykładu daje M_dd = 0,71 i M_kr = 0,6022782654984058
przy Cz = 0,4, t/c = 0,12 i zerowym skosie. Różniczkowanie numeryczne
potwierdza dCx/dM = 0,1 przy M_dd. Przypadki po obu stronach granic
różnią się o 10⁻⁸/10⁻⁹, mimo identycznego zaokrąglonego opisu.

Surowe logi i artefakty: ignorowany `work/compressibility-20261101/`.
Materiały kolejnego zadania ML1 są osobno w `work/ml1-20261101/`.
