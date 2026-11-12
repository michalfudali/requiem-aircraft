# Temat 7 — audyt i odtwarzalne studium P1–P6

> Stan z 08.11.2026: zachowano dwa odtwarzalne warianty. Poniższe studium dotyczy misji
> 140 km/h i prawa masy P1; wariant 115 km/h z domknięciem P3→P2 opisuje
> [PROJEKT_TEMAT_7_2026-11-06.md](PROJEKT_TEMAT_7_2026-11-06.md). Oba używają bieżących obliczeń.

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

Trzynaście niezależnych kontroli sprawdza konfigurację tematu, sumę mas,
geometrię AR = b²/S, ciągłość mas faz misji, zapas stateczności,
kinematykę końcówki śmigła, wybrany punkt danych silnika oraz przeliczenie
obrotów silnika przez nominalną przekładnię. Kontrole analizy masowej obejmują
zgodność wejść z obliczoną geometrią, paliwem i mocą, obciążenie niszczące
z końcowej obwiedni oraz sumy niezależnych i przeskalowanych mas zespołów.
Osobna kontrola sprawdza 55,4 kg masy bazowej Rotax 912 UL i ochronę tego minimum.
SFC jest sprawdzane niezależnie z danych punktu ciągłego lub przepływu przy 75% mocy.
Ich przejście potwierdza spójność tych obliczeń. Nie potwierdza wytrzymałości,
charakterystyk rzeczywistego profilu ani zgodności certyfikacyjnej.

## Ustalenia i otwarte wymagania

| Obszar | Ustalenie | Co pozostaje do wykazania |
|---|---|---|
| P1, koncepcja i misja | Właściwy temat, rzeczywisty silnik i źródło SFC; raport z analizą porównawczą | Własny szkic i konsultacja misji; uzasadnienie wstępnej biegunowej |
| P2, dobór | 58 kW dostępne; moc wymagana jest dużo mniejsza | Dobór lżejszej lub lepiej dopasowanej instalacji i konkretnego śmigła; uzasadnienie punktu przelotu |
| P3, masy | P1 daje ok. 213 kg masy pustej, niezależny model zespołów ok. 500 kg po użyciu rzeczywistej geometrii, obwiedni i rozszerzonej bazy porównawczej | Zweryfikowanie stosowalności modelu Raymera GA do motoszybowca oraz mas struktury i rzeczywistej instalacji. Normalizacja procentów nie rozwiązuje sprzeczności |
| P3, geometria | Zakres ŚC mieści się w założeniach kursowych; audyt wykazuje za mały kąt ochrony ogona i za duży kąt przewrotki bocznej | Rzeczywista geometria podwozia, ugięcia i punkty kontaktu; ponowna kontrola rysunku |
| P3/P4, profil i przeciągnięcie | Aktualne t/c = 0,12 jest założeniem, nie zatwierdzonym profilem; oderwanie wypada w obszarze klapolotki | Wybór i porównanie profili, dane dla właściwego Re/Macha, zwichrzenie i skuteczność lotek |
| P4/P5, śmigło | Wspólna średnica i obroty z wyboru użytkownika albo doboru wstępnego | Mapa konkretnego śmigła; wstępny model sprawności nie jest pomiarem |
| P5, osiągi i paliwo | Pełne drogi startu/lądowania oraz bilans misji są obliczane | Mapa silnika poza punktem źródłowym, rzeczywista instalacja i pojemność paliwa. Kursowe ubytki startu/lądowania po 2,5% nie są pomiarem spalania w czasie tych faz |
| P6, obciążenia | Raport obejmuje punkty krytyczne i konfiguracje; moc rzeczywistego silnika podnosi prędkości obwiedni | Uzgodnienie prędkości projektowych z konstrukcją; wykazanie marginesu aeroelastycznego. Szacunek flatteru nie zastępuje analizy i prób |
| Dynamika | Dla studium ζ ≈ 2,25: to ruch aperiodyczny. Level 3 wynika ze wspólnej oceny CAP i tłumienia | Walidacja pochodnych aerodynamicznych i momentów bezwładności; pełna analiza dynamiczna |
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
Przykładowo [producent Rotax 912 UL](https://www.flyrotax.com/products/912-ul-a-f)
podaje 55,4 kg dla silnika z przekładnią; wydech i pozostałe elementy instalacji
są wymienione osobno. Masa bazowa jest teraz chroniona przed skalowaniem.
W panelu silnika można podać masę całej instalacji na jeden silnik, jej źródło
oraz zakres elementów i płynów. Wpisana masa nie jest skalowana; pole mniejsze
od znanego minimum zostaje odrzucone. Brak pełnej masy zabudowy pozostaje
otwartą kontrolą audytu, nawet gdy dane paliwowe są udokumentowane.
Rozdział pozostałego budżetu ma postać:

`m_i,CG = m_i,znane + k_m (m_i,II − m_i,znane)`.

Wzory, podstawienia i zależności od tych mas są dostępne w drzewie obliczeń.
Dane masy bazowej pochodzą z obserwacji
`data/aircraft/research/engine_hardware.json`, importowanej atomowo do SQLite
przez `python tools/import_engine_hardware.py`. Katalog silników pozostaje
jedynym źródłem danych używanym przez obliczenia.
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

## Weryfikacja implementacji — 6 listopada 2026

Po scaleniu rozszerzonej bazy porównawczej z `origin/master`:

- Pełny zestaw backendu: **2401 zaliczonych, 8 pominiętych**; osiem pominięć
  dotyczy biblioteki natywnej OpenVSP niedostępnej w interpreterze Python 3.11.
- OpenVSP 3.55 w osobnym środowisku Python 3.13: **9 zaliczonych**.
- JavaScript: **54 zaliczone**.
- Chromium: **37 różnych scenariuszy** obejmujących kreator, siedem klas
  samolotów, źródła danych, zapis i otwieranie, wyważenie oraz widok mobilny.
  Po poprawce nagłówka i walidacji edytora ponowiono odpowiednie scenariusze.
- Bazy SQLite: zgodny schemat, integralność i klucze obce; testy nie zmieniły
  dostarczonych baz.
- Studium tematu 7: **12/12 kontroli liczbowych**, 19 wpisów otwartych uwag
  projektowych. Wszystkie sześć aktualnych raportów otwarto offline w Chromium;
  wzory i wykresy renderują się bez błędów JavaScript i KaTeX. Zapisano także
  model OpenVSP z siedmioma elementami geometrii.

Wyniki testów dotyczą implementacji i wskazanych kontroli spójności. Otwarte
wymagania konstrukcyjne z tabeli powyżej pozostają częścią audytu.

## Weryfikacja implementacji — 8 listopada 2026

Po scaleniu wariantu z domknięciem P3→P2 i ochroną mas sprzętu:

- Pełny backend: **2433 zaliczone, 12 pominiętych**; pokrycie kodu **94,30%**
  przy wymaganym progu 90%. Pominięcia dotyczą biblioteki natywnej OpenVSP.
- Natywny OpenVSP 3.55 / Python 3.13: **13 zaliczonych**, w tym rozmiar śmigła
  pchającego oraz środki i kontakt z ziemią brył podwozia przedniego i ogonowego.
- JavaScript: **55 zaliczonych**; wszystkie scenariusze Chromium: **45 zaliczonych**.
- Oba warianty: **13/13 niezależnych kontroli liczbowych**. Dwanaście aktualnych
  raportów P1–P6 otwarto offline bez błędów JavaScript i KaTeX. Sumy kontrolne
  wiążą modele `.vsp3` z zapisanymi wynikami obliczeń.
- Dla wariantu 115 km/h zapisano także pełny raport HTML i PDF: **89 stron**,
  bez pustych stron. Pliki robocze znajdują się w `work/topic7-projekt/`;
  są przeznaczone do przeglądu i dalszego uzupełniania projektu.

Zaliczenie testów nie usuwa wskazanych braków danych konstrukcyjnych, profilu,
masy kompletnej instalacji ani potwierdzeń autora. Szczególnego sprawdzenia
wymaga rozbieżność między technologią kompozytową a materiałem używanym przez
ówczesny moduł aeroelastyczny, opisana w dokumencie wariantu 21 m.

## Aktualizacja — 12 listopada 2026

Scalono zmiany kursowe z `origin/master`, w tym charakterystyki FX 61-163,
domknięcie osiągów i momenty bezwładności względem 1/4 ŚCA. Rozwiązano rozbieżność
materiału w aeroelastyczności: kompozyt nie dostaje już domyślnie aluminium.
Wprowadzono osobny wybór materiału skrzydła i kompletu parametrów zastępczego
przekroju ze źródłem. Założenia, wzory i podstawienia są w drzewie i w P3.

Usunięto nieuzasadnione wyznaczanie rewersu lotek jako 0,82 prędkości dywergencji
oraz uniwersalne przypisywanie 1,20 VD wszystkim kategoriom. Brak rozwiązania
flatteru daje wynik nierozstrzygający. Kontrola `aeroelastic_substantiation`
pozostaje otwarta; szczegóły i źródła: [AEROELASTYCZNOSC.md](AEROELASTYCZNOSC.md).

Oba warianty ponownie spełniają 13/13 niezależnych kontroli rachunkowych. Dla
wariantu 21 m / 115 km/h masa startowa wynosi 655,4 kg, pusta 496,8 kg, paliwo
48,6 kg. Wszystkie 32 kontrole raportu są zaliczone, ale audyt ma dwie otwarte
pozycje: kompletna instalacja napędu i potwierdzenie aeroelastyczne. Uzgodnienie
misji i szkic nadal wymagają danych autora.

Ponownie otwarto offline 12 raportów P1–P6 i raport zbiorczy bez błędów JS/KaTeX.
Aktualny PDF ma 93 strony i nie zawiera pustych stron. Model OpenVSP wariantu
21 m ma siedem brył; położenia kół i kontakt z ziemią zweryfikowano względem P3.
Sumy kontrolne w `work/topic7-projekt/` wiążą bieżące wejścia, raporty i model.

Przegląd spójności katalogu ujawnił osobny otwarty problem: `course_seed.json`
zawiera nowszy wariant tematu 7 niż dostarczony `projects.sqlite3`. Import pliku
`topic7_motoszybowiec_21m.json` daje opisany wyżej wariant; wybór tematu ze starszego
katalogu nadal daje poprzednie parametry. Ujednolicenie katalogu musi zachować
projekty i świadome zmiany użytkownika. Również OpenVSP odtwarza obecnie profil
przybliżeniem NACA 4-cyfrowym, zamiast używać pełnych rzędnych FX 61-163; model
pozostaje geometrią koncepcyjną.

Końcowa weryfikacja implementacji tej aktualizacji:

- Python 3.11: **2472 zaliczone, 12 pominiętych**, bez błędów i niezaliczonych testów
  (`work/aeroelastic-verified-full.xml`). Pominięto natywne wywołania OpenVSP dla tego interpretera.
- Pokrycie **94,29%**; pomiar pełnego kodu uzupełniono o poprawione testy adaptera
  i regresję numeryczną (`work/aeroelastic-final-coverage.xml`).
- Chromium: **48 scenariuszy**, w tym siedem klas, kreator, zapis i raporty;
  dodatkowo powtórzono trzy scenariusze panelu aeroelastycznego po poprawce wyróżnika.
  Weryfikują również zachowanie precyzji wpisanych danych i prezentację wyniku nierozstrzygającego.
- JavaScript: **55 zaliczonych**. Python 3.13 z OpenVSP 3.55: **13 natywnych + 14 adaptera** zaliczonych.
- Integralność obu baz SQLite i ich niezmienność po testach potwierdzone.

Pełny zestaw obejmuje także regresję CS-22: podmuch 7,5 m/s przy VD oraz malejące
granice manewrowe są uwzględnione w obwiedni zbiorczej. Testy nie oznaczają zamknięcia
otwartych pozycji konstrukcyjnych ani potwierdzeń wymaganych od autora.
