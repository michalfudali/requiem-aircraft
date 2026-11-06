# Temat 7 — audyt i odtwarzalne studium P1–P6

## Wymaganie i stan projektu

`BIPOL1_samoloty.pdf`, temat 7: motoszybowiec **jednomiejscowy**, rozpiętość
**większa niż 20 m**, **stały napęd ciągnący**. Kontrola tematu obejmuje teraz
liczbę wszystkich osób i lokalizację napędu. Sam brak pasażerów nie wystarcza:
dwóch pilotów również narusza temat. Błędnych wyborów nie nadpisuje się w tle.

Plik [topic7_source_engine.json](../data/design_cases/topic7_source_engine.json)
jest importowalnym studium roboczym. Zachowuje dotychczasową misję: 600 km,
140 km/h TAS na 2000 m, rozpiętość 21 m i AR = 24. Misja wymaga konsultacji;
nie wpisano fikcyjnego potwierdzenia prowadzącego ani akceptacji szkicu.
Przyjęto projektowego pilota 110 kg i rzeczywistą propozycję napędu:
Rotax 912 UL, 58 kW mocy ciągłej, SFC 285 g/(kW·h).

Podstawa napędu: [BRP-Rotax OM-912, Ed.4 Rev.1, 01.01.2023](https://www.rotax-owner.com/pdf/OM_912-Series_ED4_R1.pdf),
§2.1 oraz §5.2, s.5-8. Punkt SFC dotyczy maksymalnej mocy ciągłej przy
5500 obr/min silnika. Nie jest mapą zużycia przy dowolnym obciążeniu.
Obroty silnika i wału śmigła są różnymi wielkościami.
Do studium przyjęto standardowe nominalne przełożenie 2,27:1 z §7.6
tej instrukcji. Obliczeniowe obroty śmigła w punkcie odniesienia wynoszą
5500/2,27 ≈ 2423 obr/min. Nominalna wartość z dokumentacji nie określa
tolerancji wykonania ani pełnej mapy silnika.

## Odtworzenie wyników

W środowisku z zależnościami aplikacji uruchom:

```powershell
python tools/audit_topic7.py --output work/topic7-audit
```

Skrypt używa osobnych baz tymczasowych. Zapisuje wejścia, pełne wyniki,
`audit.json` oraz sześć samodzielnych raportów `P1.html`–`P6.html`.
Kod wyjścia **1 jest oczekiwany przy otwartych kontrolach projektu**; raporty
zostają zapisane. Opcja `--no-reports` pomija wyłącznie generowanie HTML.

Dwanaście niezależnych kontroli sprawdza konfigurację tematu, sumę mas,
geometrię AR = b²/S, ciągłość mas faz misji, zapas stateczności,
kinematykę końcówki śmigła, wybrany punkt danych silnika oraz przeliczenie
obrotów silnika przez nominalną przekładnię. Kontrole analizy masowej obejmują
zgodność wejść z obliczoną geometrią, paliwem i mocą, obciążenie niszczące
z końcowej obwiedni oraz sumy niezależnych i przeskalowanych mas zespołów.
Ich przejście potwierdza spójność tych obliczeń. Nie potwierdza wytrzymałości,
charakterystyk rzeczywistego profilu ani zgodności certyfikacyjnej.

## Ustalenia i otwarte wymagania

| Obszar | Ustalenie | Co pozostaje do wykazania |
|---|---|---|
| P1, koncepcja i misja | Właściwy temat, rzeczywisty silnik i źródło SFC; raport z analizą porównawczą | Własny szkic i konsultacja misji; uzasadnienie wstępnej biegunowej |
| P2, dobór | 58 kW dostępne; moc wymagana jest dużo mniejsza | Dobór lżejszej lub lepiej dopasowanej instalacji i konkretnego śmigła; uzasadnienie punktu przelotu |
| P3, masy | P1 daje ok. 215 kg masy pustej, niezależny model zespołów ok. 562 kg po użyciu rzeczywistej geometrii i obwiedni | Zweryfikowanie stosowalności modelu Raymera GA do motoszybowca oraz mas struktury i rzeczywistej instalacji. Normalizacja procentów nie rozwiązuje sprzeczności |
| P3, geometria | Zakres ŚC mieści się w założeniach kursowych; audyt wykazuje za mały kąt ochrony ogona i kąt podwozia za ŚC | Rzeczywista geometria podwozia, ugięcia i punkty kontaktu; ponowna kontrola rysunku |
| P3/P4, profil i przeciągnięcie | Aktualne t/c = 0,12 jest założeniem, nie zatwierdzonym profilem; oderwanie wypada w obszarze klapolotki | Wybór i porównanie profili, dane dla właściwego Re/Macha, zwichrzenie i skuteczność lotek |
| P4/P5, śmigło | Wspólna średnica i obroty z wyboru użytkownika albo doboru wstępnego | Mapa konkretnego śmigła; wstępny model sprawności nie jest pomiarem |
| P5, osiągi i paliwo | Pełne drogi startu/lądowania oraz bilans misji są obliczane | Mapa silnika poza punktem źródłowym, rzeczywista instalacja i pojemność paliwa. Kursowe ubytki startu/lądowania po 2,5% nie są pomiarem spalania w czasie tych faz |
| P6, obciążenia | Raport obejmuje punkty krytyczne i konfiguracje; moc rzeczywistego silnika podnosi prędkości obwiedni | Uzgodnienie prędkości projektowych z konstrukcją; wykazanie marginesu aeroelastycznego. Szacunek flatteru nie zastępuje analizy i prób |
| Dynamika | Dla studium ζ ≈ 2,29: to ruch aperiodyczny. Level 3 wynika ze wspólnej oceny CAP i tłumienia | Walidacja pochodnych aerodynamicznych i momentów bezwładności; pełna analiza dynamiczna |
| Akustyka | M_tip wynika ze średnicy P4/P5, obrotów i ruchu postępowego; wynik jest porównaniem wstępnym | Dane widmowe, kierunkowość, wydech i procedura dla rzeczywistego samolotu; brak podstaw do świadectwa hałasu |

Wyniki liczbowe są wartościami bieżącego modelu, nie zatwierdzonymi
parametrami gotowego samolotu. `audit.json` zachowuje także niezaliczone
kontrole i ich ścieżki, nawet gdy ta sama uwaga pojawia się w kilku częściach.

## Poprawione obliczenia

Model mas zespołów otrzymuje końcowe t/c, skos i zbieżność skrzydła,
ramię usterzenia, wymiary kadłuba, paliwo misji oraz dobraną moc zamiast
wartości zastępczych. Współczynnik obciążenia niszczącego pochodzi z obwiedni;
współczynnika bezpieczeństwa nie mnoży się powtórnie. Gęstość paliwa służy
do przeliczenia masy na galony US wymagane przez korelację instalacji.
Definicje i jednostki: `Analiza_masowa.pdf`, s.5–7.

Zakładka P3 i raport rozdzielają niezależne masy zespołów od ich rozkładu
przeskalowanego do masy pustej P1. Rozkład do wyważenia zachowuje proporcje
poszczególnych usterzeń i instalacji. Nadal jest warunkowym oszacowaniem;
nie zastępuje rzeczywistych mas ani ich rozmieszczenia w konstrukcji.
Audyt informuje też, gdy wykładnik prawa masy P1 narzucono z założenia klasy,
ponieważ regresja próby nie dała malejącego udziału masy pustej. Raportowany
surowy wykładnik pozostaje dostępny, a taki model wymaga uzasadnienia.

Hałas nie korzysta już z niezależnej, stałej średnicy 1,85 m. Współdzieli
średnicę P4/P5, a śrubowa liczba Macha wynosi:

`M_tip = sqrt((π D RPM/60)² + V²) / a`.

To kinematyka bez prędkości indukowanej przez tarczę. Definicję sumy składowej
osiowej i obrotowej podaje [NASA, analiza hałasu śmigieł, 19780005911](https://ntrs.nasa.gov/api/citations/19780005911/downloads/19780005911.pdf).
Małe M_tip nie gwarantuje dotrzymania limitu hałasu. Pole `compliant` zachowuje
historyczne znaczenie porównania szacunku z limitem; jednoznaczne pola to
`estimate_within_limit`, `assessment_scope` i `certification_compliant`.
Ostatnie pozostaje `null`: model nie wydaje oceny certyfikacyjnej.

Średnicę i obroty można wpisać w kroku 3 kreatora oraz w panelu doboru
silnika w założeniach projektu. Puste pola przywracają dobór automatyczny.
Średnica jest wspólna także dla podglądu samolotu i obu generatorów OpenVSP;
nie jest dobierana ponownie z innej proporcji rozpiętości.

Dla ruchu krótkookresowego pierwiastki równania drugiego rzędu wynoszą
`s = -ζω_n ± ω_n sqrt(ζ²−1)`. Gdy ζ > 1, o zaniku dominującego modu
decyduje wolniejszy rzeczywisty pierwiastek, a nie średnia obu pierwiastków
`-ζω_n`. Obecny moduł zwraca oba pierwiastki i podstawę czasu połowicznego
zaniku. Tego czasu nie należy utożsamiać z zanikiem całej odpowiedzi dla
dowolnych warunków początkowych. Podstawa: [MIT 2.14, Pole and Zero Locations](https://web.mit.edu/2.14/www/Handouts/PoleZero.pdf).
