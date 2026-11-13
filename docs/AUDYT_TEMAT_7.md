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

Przegląd spójności katalogu ujawnił starsze parametry w istniejącej lokalnej bazie
SQLite. Baza ta jest pomijana przez Git; nowe instalacje korzystały już z bieżącego
`course_seed.json`. Dodano aktualizację wyłącznie dokładnie rozpoznanych dawnych
wpisów katalogowych. Zachowuje ona zapisane projekty i zmodyfikowane przez autora
tematy. Nowy temat 7 w kreatorze ma teraz aktualny profil i geometrię.

Obie ścieżki budowy OpenVSP korzystają już z pełnych rzędnych FX 61-163, a przycisk
synchronizacji przekazuje aktywny projekt. Wcześniej błędne odwołanie JavaScript
mogło powodować budowę samolotu domyślnego. Model nadal pozostaje geometrią
koncepcyjną; szczegóły i granice testów: [KATALOG_I_PROFILE_OPENVSP.md](KATALOG_I_PROFILE_OPENVSP.md).

Weryfikacja wcześniejszego etapu aeroelastycznego, przed poprawkami katalogu i OpenVSP:

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

## Weryfikacja katalogu i zachowania profilu — 12 listopada 2026

Po bezpiecznej aktualizacji rozpoznanych dawnych wpisów katalogu, przekazaniu
pełnych rzędnych profilu do obu adapterów OpenVSP i poprawce wysokości podwozia:

- Pełny backend: **2491 zaliczonych, 28 pominiętych**, **94,33% pokrycia**,
  bez błędów (`work/catalog-profile-final-full.xml`,
  `work/catalog-profile-final-coverage.xml`). Pominięcia dotyczą SDK OpenVSP
  niedostępnego w interpreterze Python 3.11.
- Python 3.13 / OpenVSP 3.55: **29 testów Studio, w tym kontrola UI, oraz 14
  testów adaptera** zaliczonych (`work/catalog-profile-final-native.xml`).
- Chromium: **52 zaliczone scenariusze**, z dwoma testami rzeczywistego
  backendu natywnego; JavaScript: **55 zaliczonych**.
- Oba studia: **13/13 niezależnych kontroli liczbowych**, aktualne modele
  `.vsp3` z kontrolą po ponownym otwarciu i 13 raportów HTML bez błędów JS/KaTeX.
  Raport zbiorczy PDF nadal ma 93 strony bez pustych stron.

Szczegółowy zakres testów i ochrona zapisanych projektów:
[KATALOG_I_PROFILE_OPENVSP.md](KATALOG_I_PROFILE_OPENVSP.md). W kolejnym etapie
rozbieżności obrysu eliptycznego i rzutu rozpiętości usunięto;
[opis geometrii i kontroli](OBRYS_OPENVSP.md).
Sprawdzenie implementacji nie jest zamknięciem wymagań dotyczących rzeczywistej
struktury, kompletnej zabudowy napędu ani uzgodnień autora.

## Ujednolicenie obrysu OpenVSP — 12 listopada 2026

Oba generatory zachowują teraz rzut rozpiętości, powierzchnię i skos ćwierćcięciw
P3 przy wzniosie. Zastąpiono różne zgrubne obrysy eliptyczne wspólnymi 32
segmentami z zachowaniem powierzchni. Natywna kontrola całkuje rzeczywisty
obrys, a nie tylko odczytuje deklarowane pola sekcji. Macierz testów obejmuje
pięć obrysów i trzy wzniosy w obu generatorach.

Odświeżono oba modele tematu 7. Dla wariantu 115 km/h po ponownym otwarciu
`.vsp3` otrzymano rzut b = 21 m i S = 15,75 m², zachowując 98 rzędnych FX
61-163 oraz położenia kół. Ponowne obliczenie obu oryginalnych plików studiów
daje identyczny zapis wyników JSON i nadal spełnia 13/13 niezależnych kontroli.
Raporty liczbowe pozostają aktualne.

Naprawiono również możliwość zawieszenia po błędzie SDK. Opróżnianie kolejki
używa jej długości; test z natywnym błędem i limitem czasu sprawdza także
ponowny odczyt pustej kolejki. Dane niezgodnego obrysu nie usuwają istniejącego
modelu. Szczegóły: [OBRYS_OPENVSP.md](OBRYS_OPENVSP.md).

Końcowy przebieg dla etapu obrysu: **2506 zaliczonych testów backendu, 61
pominiętych wywołań natywnego SDK w Pythonie 3.11, pokrycie 94,33%**.
Cała przeglądarka zaliczyła **54 scenariusze**, JavaScript **55**.
Zestaw środowiska OpenVSP 3.55 / Python 3.13 zaliczył **76 testów Studio i adaptera**.

Dalsza kontrola przekazywania parametrów napędu wykazała brak śmigła w adapterze
dla kanonicznego typu `prop` i użycie starszej nazwy pola liczby silników w Studio.
Oba błędy poprawiono, ujednolicając również liczbę łopat. Siedem klas sprawdzono
w obu generatorach. Zestaw natywny i adaptera zaliczył 90 testów oraz cztery
dodatkowe przypadki domyślnej liczby łopat; ponowiono sześć scenariuszy Chromium.
Zakres i pozostające ograniczenia rozmieszczenia napędu: [NAPED_OPENVSP.md](NAPED_OPENVSP.md).
Odświeżony model wariantu 21 m ma śmigło o średnicy 1,7 m i dwóch łopatach;
manifest wiąże go z rewizją kodu oraz wejściami i wynikami projektu.

## Korekta prześwitu śmigła — 12 listopada 2026

Sprawdzenie tekstu CS-22.925(a) wykazało odwrócenie wartości w kodzie i dawnych
testach: właściwe minimum wynosi 180 mm przy kole przednim i 230 mm przy kółku
ogonowym. Regułę ujednolicono w wymiarowaniu i obu kalkulatorach, a zaokrąglenie
nie może już zamienić zbyt małego prześwitu w zaliczony warunek.

Wariant 21 m / 115 km/h ma teraz oś 1,08 m nad ziemią i 0,23 m prześwitu przy
poziomym położeniu. W raporcie, drzewie i UI dostępne są wzór, wartości i zakres
tego obliczenia. Pozostałe warunki zabudowy wymagają pełnej geometrii i danych
ugięć; program nie potwierdza ich na podstawie samego wymiaru poziomego.

Oba studia ponownie spełniają 13/13 niezależnych kontroli rachunkowych.
Średnica śmigła i rzędne profilu pozostają zachowane, a aktualny model `.vsp3`
sprawdzono po ponownym otwarciu. Źródła i szczegółowy zakres:
[PRZESWIT_SMIGLA.md](PRZESWIT_SMIGLA.md).

Weryfikacja końcowa 13.11.2026 po scaleniu z nowym kreatorem: **2534 testy
backendu zaliczone, 81 pominiętych wywołań SDK w Pythonie 3.11, pokrycie
94,44%**. Środowisko natywne zaliczyło **96 testów**, JavaScript **55**.
Zbiorczo zaliczono **63 różne scenariusze Chromium**, w tym cztery z natywnym
backendem; jeden limit czasu nawigacji z pierwszego przebiegu sprawdzono
ponownie z wynikiem pozytywnym. Wszystkie 13 odświeżonych raportów HTML
działa offline, a PDF ma 95 stron bez pustych stron. Szczegółowe ślady i
rozróżnienie kontroli wymiaru od pełnej oceny zabudowy są w opisie prześwitu.

## Bilans energii wznoszenia — dalsza weryfikacja 13.11.2026

Powyższe wyniki dotyczą etapu poprawy prześwitu. Kolejna rewizja usuwa
zerowe paliwo wznoszenia wynikające z obcięcia wykresu Corke’a poniżej M=0,1.
Wariant 21 m / 115 km/h ma po tej zmianie MTOW **658,658 kg**, masę własną
**498,188 kg** i paliwo **50,469 kg**. Wznoszenie 0–2000 m przy 3 m/s wymaga
**1,567 kg paliwa** według przyjętego modelu i wybranego punktu SFC silnika.
Oba studia spełniają **14/14 niezależnych kontroli rachunkowych**. Pozostaje
odpowiednio 10 i 19 otwartych kontroli projektowych; ich lista nie jest
zastępowana pozytywnym wynikiem obliczeń ani testów aplikacji.

Wyniki, równania, źródła i ograniczenia:
[WZNOSZENIE_I_PALIWO.md](WZNOSZENIE_I_PALIWO.md).
