# Studium wykonalności P2: decyzje dostępne w interfejsie

Wejdź w **Analizy szczegółowe → Studium wykonalności P2**. Ten sam zestaw pól
działa w trybie **Projekty semestralne → P2**; edytor profilu jest też dostępny
w P3. Widoki przenoszą wspólne kontrolki, więc przełączanie trybu nie tworzy
drugiej, rozbieżnej kopii założeń. Zmiany zapisuje przeliczenie projektu.
Wyszukiwarka parametrów prowadzi także do pól w zamkniętych sekcjach P2.

Przegląd wykonano na podstawie lokalnego materiału C. Galińskiego
`scraped_materials/bipol/BIPOL_2.pdf` (10 stron). Materiał dydaktyczny pozostaje
lokalny. Poniższa tabela wskazuje drogę od wymagania do decyzji i wyniku.

| Materiał | Decyzja w UI | Wynik / kontrola |
|---|---|---|
| s. 1–2, obszar dopuszczalny, punkty A/B | Założenia skrzydła: dobór z obciążenia; w P2 wybór granicy W/S, punktu A lub B | Wykres, powierzchnia, wymagana moc/ciąg, opis przyjętej decyzji w raporcie i drzewie obliczeń |
| s. 2, wzory (1)–(2), start na 15 m | Pełna długość startu; silnik i liczba silników w module napędu; sprawność śmigła w locie i osobno przy starcie | Krzywa startu, moc/ciąg zespołu, wzory z podstawieniem; dobór rzeczywistego silnika i danych zużycia paliwa w panelu napędu |
| s. 2–4, rys. 2–3, mechanizacja | Profil, tryb grubości, t/c; klapy, przedskrzydła, względna powierzchnia objęta mechanizacją | Cz max gładkie / start / lądowanie; konfiguracja geometryczna. Wychylenia 20°/40° pozostają założeniem z zajęć |
| s. 4–5, wzory (3)–(5), lądowanie | Pełna długość lądowania; wysokość lotniska i odchyłka temperatury od ISA w P2 | Ograniczenie W/S przeliczone z masy do lądowania na startową; rzeczywista sigma lotniska w arkuszu |
| s. 5–6, wzory (6)–(9), wznoszenie | Wymagane wznoszenie, prędkości minimalna i przelotowa; dodatkowo pułap praktyczny i wznoszenie na pułapie | Krzywa wznoszenia i dolna granica; aktywne dodatkowe krzywe pułapu, Vmax i holowania |
| s. 6, wzór (10), prędkość minimalna | VS0 oraz mechanizacja i Cz max w założeniach skrzydła | Pionowa granica W/S uwzględniająca Cz max / 1,1 |
| s. 6–7, wzory (11)–(12), zasięg | Prędkość i wysokość przelotu, AR, Oswald, biegunowa, profil misji; wybór punktu B | Optimum dla śmigła lub odrzutu, masa w połowie przelotu i przeliczenie na masę startową; konflikt z granicą W/S pokazany w opisie |
| s. 7–10, wzory (13)–(21), 5.10 | Liczba prototypów RDT&E, seria produkcyjna, liczba amortyzowanych egzemplarzy, rok, tempo obu faz, zysk, kontrola jakości, ceny silnika i awioniki, kurs USD/PLN | Oddzielne fazy RDT&E i produkcji; ekstrapolacja roboczogodzin i stawek; cena minimalna i cena z zyskiem; pełny raport |
| wzór (15), koszt silnika odrzutowego | Liczba silników, dwuprzepływowość, temperatura przed turbiną w K; zalecana cena z oferty | Automatyczne przeliczenie K na °R; niedodatni wynik modelu wymaga ceny z oferty |

Punkt A minimalizuje obwiednię wstępnego wykresu P2. Procedura obejmuje siatkę
201 punktów i 60 kroków złotego podziału wokół najlepszego punktu. Późniejsze
uściślenie osiągów może zwiększyć wymaganą moc. Punkt B jest ograniczony
warunkami VS0 i lądowania. Z góry zadana powierzchnia lub rozpiętość z AR ma
pierwszeństwo przed doborem A/B. Szybowiec nie otrzymuje fikcyjnej mocy.
Domyślny wybór granicy W/S zachowuje dotychczasowy sposób wymiarowania.

Gęstość lotniska wpływa na ograniczenia startu i lądowania wykresu P2; także
poniżej poziomu morza stosuje się równanie warstwy troposferycznej, do −500 m.
Model atmosfery: [NASA, U.S. Standard Atmosphere 1976](https://ntrs.nasa.gov/citations/19770009539).
Uściślony model długości startu/lądowania P5 nadal zakłada ISA na poziomie morza.

## Profil i dane źródłowe

Lista obejmuje geometrię analityczną przykładowych profili NACA, kandydatów
z porównania katalogowego i własne oznaczenie. Inny profil można wczytać
z pliku `.dat` / `.txt` albo wkleić rzędne. Rysunek ma cięciwę 200 mm.
Pole źródła zapisuje się razem z projektem i trafia do raportów P2/P3.
Zmiana profilu nie przenosi automatycznie rzędnych i źródła poprzedniego;
w obrębie otwartego projektu można powrócić do jego szkicu.

**Geometria profilu nie jest jego biegunową.** Import rzędnych nie jest pomiarem
Cx ani Cz max. Dane porównawcze dla projektowych Re i Macha wpisuje się w tabeli
kandydatów (3–4 profile, kryterium przelotowe lub maksymalna siła nośna).
Model aerodynamiczny BIPOL P3/P4 nadal korzysta z referencyjnych badań NACA 23012;
UI i raporty ujawniają to ograniczenie, bez twierdzenia o równoważności z innym
profilem. Własne zestawy biegunowych przy kilku Re przyjmuje osobny zeszyt `/ml1`.

## Audyt dostępności obliczeń

Dodano 30 opcjonalnych pól liczbowych: warunki lotniska, pułap i Vmax, czas
oczekiwania, początek iteracji masy, holowanie, proporcje usterzenia i sterów,
gęstość ładunku, sprawność startowa oraz parametry modelu kosztów.
Masa osoby załogi ma wspólne pole w założeniach podstawowych. Dostępne są oba
tryby bilansu: wstępny P1/P2 i sprzężony P2 ↔ P4. Puste pole opcjonalne usuwa
własną wartość i przywraca założenie metody.

Test kontraktowy porównuje **każdy** klucz `NUMERIC_LIMITS` z rzeczywiście
wyrenderowanymi kontrolkami. 22 klucze mają jawny, uzasadniony wyjątek w
`tests/test_p2_choices.py`: aliasy, wyniki pochodne, parametry wycofanej metody
masy lub stałe z zajęć. Nie powstają osobne suwaki do zmiany wyników pochodnych.
Drugi test porównuje wszystkie opcje `ENUM_CHOICES` z opcjami formularzy;
starszy model faz misji jest jedynym celowym wyjątkiem (normalizowany do modelu
Galińskiego). Test wykrywa też powielone identyfikatory kontrolek.

Przejrzane akcje serwerowe mają odpowiadające im widoki: zarządzanie projektem,
import/CRUD katalogu samolotów, trendy i źródła, dobór silnika, przeliczanie,
kontrola zaliczenia, iteracja biegunowej, profil 200 mm, raporty HTML/DOCX,
katalog parametrów i materiały źródłowe. Metody ML1 mają własny widok `/ml1`.
OpenVSP ma osobny panel; wymaga zgodnej instalacji natywnego API. Bez niej
pozostała aplikacja działa, a panel wyjaśnia niedostępność i blokuje jego akcje.
Metody pomocnicze i wewnętrzne wyniki nie są osobnymi decyzjami projektanta.

Operacje wodne nadal wymagają odrębnej analizy hydrodynamicznej. Metody wstępne
i ekstrapolowane koszty służą studium dydaktycznemu, nie dowodowi certyfikacji.

## Sprawdzenie

`tests/test_p2_choices.py` sprawdza m.in. niezależne analityczne optimum,
obwiednię wykresu, pierwszeństwo geometrii, ograniczenia punktu B, walidację,
formuły raportu dla A/B i lotniska hot-and-high oraz pokrycie kontrolek.
`tests/test_browser_p2.py` wykonuje wybór/import profilu, przejścia P2/P3,
zapis i przeładowanie, zmianę założeń, czyszczenie wartości opcjonalnej,
wyszukiwanie parametru i kontrolę pól kosztowych przy szerokości 320–1440 px.
Zestaw akceptacyjny obejmuje ponadto siedem klas statków powietrznych.
