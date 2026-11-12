# Podstawa wstępnego modelu aeroelastycznego

Stan: 12.11.2026. Moduł nie wykazuje zgodności rzeczywistego płatowca. Obejmuje
jednorodną belkę wspornikową i przekrój typowy o dwóch stopniach swobody.
Nie oblicza tłumienia. Wszystkie prędkości są równoważne (EAS, odniesienie ρ₀).

## Materiał i dane konstrukcji

`wing_structure_material` określa materiał skrzydła. Przy wyborze automatycznym
uwzględnia się `technology=metallic/composite`, następnie starsze parametry
`structure_material` / `structural_material`. Sprzeczność starszego parametru
jest widoczna w ograniczeniach. Drewniany lub rurowy kadłub nie określa materiału płata.

W trybie **założeń kesonu** przyjmuje się umowne E i G, grubość pokrycia zależną
od oszacowanej masy skrzydła, oś sprężystą w 40% c, środek masy w 45% c i
r/(c/2) = 0,50. Nominalne E/G nie są certyfikowanymi właściwościami stopu,
gatunku drewna ani laminatu. Nie wolno traktować wyboru „kompozyt” jako
określenia sztywności rzeczywistego laminatu. Wpływ orientacji włókien i sprzężeń
ilustruje [NASA/TM–2014-218517, Aeroelastic Tailoring via Tow Steered Composites](https://ntrs.nasa.gov/api/citations/20140012777/downloads/20140012777.pdf).

W trybie **własnych danych ze źródłem** trzeba podać wszystkie wielkości:

| Parametr | Znaczenie |
|---|---|
| `wing_bending_stiffness_nm2` | zastępcza sztywność giętna EI [N·m²] |
| `wing_torsional_stiffness_nm2` | zastępcza sztywność skrętna GJ [N·m²] |
| `wing_mass_per_length_kg_m` | masa na metr rozpiętości m′ [kg/m] |
| `wing_elastic_axis_ratio` | xEA/c, od noska |
| `wing_section_cg_ratio` | xCG/c, od noska |
| `wing_radius_gyration_ratio` | promień bezwładności względem EA, podzielony przez **połowę cięciwy** |
| `aeroelastic_data_source` | dokument, wydanie i lokalizacja danych |
| `aeroelastic_data_conditions` | konfiguracja i sposób wyznaczenia parametrów zastępczych |

Macierz mas musi być dodatnio określona: r/(c/2) > 2|xCG/c − xEA/c|. Wprowadzone
dane nie zmieniają automatycznie bilansu mas P3. Samo zadeklarowanie źródła nie
oznacza jego niezależnego potwierdzenia. Nadal pomija się rozkłady parametrów,
sprzężenia laminatu, luzy i podatność sterowania, drgania napędu i usterzenia.

## Zakresy porównania

- **CS-22:** §22.629(a) wymaga braku niestateczności do co najmniej VD i odpowiedniego
  tłumienia. §22.629(b)(1)(i) dotyczy analizy prędkości krytycznych do 1,2 VD,
  w połączeniu z badaniami drgań, a (b)(2) dotyczy prób w locie do VDF.
  [EASA, Easy Access Rules CS-22, s. 82–83](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%201.pdf).
  Treść §22.629 potwierdzono także w [Amendment 3, s. 63–64](https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf).
- **JAR-23 / VLA:** zakres 1,2 VD dotyczy wybranej drogi analizy racjonalnej;
  nie jest uniwersalnym opisem wszystkich metod wykazania zgodności.
  [Materiały WTLK, wyjątki JAR](https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/WTLK/Wyjatki-z-przepisow),
  [EASA CS-VLA 629(b), s. 70](https://www.easa.europa.eu/sites/default/files/dfu/Easy%20Access%20Rules%20CS-VLA%20%28Amendment%201%29.pdf).
- **CS-25:** §25.629(b)(1) obejmuje obwiednię VD/MD powiększoną o **15% EAS**
  przy stałych M i wysokości w warunkach bez uszkodzeń. Pojedyncze porównanie
  1,15 VD nie odwzorowuje całej tej obwiedni ani przypadków uszkodzeń.
  [EASA CS-25 Amendment 2, s. 1-D-4](https://www.easa.europa.eu/sites/default/files/dfu/CS-25%20Consolidated%20version.pdf),
  [tekst JAR 25.629 w załączniku EASA A340](https://www.easa.europa.eu/sites/default/files/dfu/A340_TCDS_EASA.A.015_-_Issue_25_-_Annex_Issue_2.pdf).
- **Pozostałe kategorie:** 1,2 VD jest jawnym celem porównawczym przyjętym w
  aplikacji; moduł nie ustala dla nich kompletnej podstawy zdatności.

Zakres analizy nie jest pozwoleniem na przekraczanie ograniczeń prędkości w locie.

## Wyniki i granice interpretacji

Dywergencję prostego skrzydła wyznacza teoria pasowa:
qD = π²GJ/(4e·c·a·l²), e = (xEA/c − 0,25)c, l = b/2.
Usunięto sztuczne ograniczenie qD od dołu do 100 Pa. Oś na lub przed 25% c
nie daje dodatniej prędkości dywergencji w tym modelu. Poprawka wpływu skosu jest
tylko jakościowa, bez rozwiązania sprzężonego gięcia i skręcania.

Flatter szacuje zbiegnięcie częstości przekroju 2DOF z aerodynamiką quasi-stacjonarną.
Uwzględnia się tylko dodatnie ω² i dodatnio określoną macierz mas. Brak zbiegnięcia
nie dowodzi braku flatteru: prędkość i wynik porównania mają wtedy wartość `null`.

**Rewers lotek pozostaje nieobliczony.** Usunięto nieuzasadnione V_rev = 0,82 V_div
oraz osobny mnożnik „wymagania” 1,15 VD. Potrzebne są pochodne aerodynamiczne,
położenie i rozpiętość lotki oraz podatność i rozkłady skrzydła.

`flutter_safe` i `divergence_safe` zachowano jako aliasy porównania liczbowego
dla zgodności formatu. `assessment_scope=preliminary` i
`certification_compliant=null` obowiązują także po podaniu danych ze źródłem.
Otwarta kontrola `aeroelastic_substantiation` zapobiega przedstawianiu tego modelu
jako pełnego potwierdzenia konstrukcji. Wzory belki, podstawienia i wyniki są
dostępne w drzewie obliczeń i w raporcie P3; dane można zmieniać w Weryfikacji.
