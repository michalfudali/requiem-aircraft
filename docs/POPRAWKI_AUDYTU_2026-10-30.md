# Poprawki po audycie projektowania — 30.10.2026

## Zakres i izolacja

Zmiany przygotowano w osobnym worktree `bipol-fixes-20261030`, na gałęzi
`fix/aircraft-design-integrity-20261030`, początkowo względem `a4ea38e`.
Nie nadpisywano roboczych plików równolegle działającego agenta.
Na życzenie użytkownika gałąź jest integrowana z aktualnym `master`.

To naprawa spójności narzędzia projektowania wstępnego. Spełnienie zasięgu
i zbieżność numeryczna nie oznaczają spełnienia wszystkich wymagań samolotu.
Niezgodności i brakujące analizy mają pozostać widoczne.

## Usunięte przyczyny błędnych wyników

| Obszar | Zmiana i uzasadnienie |
|---|---|
| Liczba silników | Wybór tematu resetuje liczbę silników; podgląd rysuje zadaną liczbę zamiast zakładać dwa silniki pod skrzydłami. |
| Wymagania tematu | Kontrole pochodzą z katalogu serwera: pasażerowie, napęd, układ, akrobacja, ładunek i limit mocy. Dane przesłane przez klienta nie mogą podmienić tych wymagań. |
| Akrobacja | Zachowano właściwe domyślne przeznaczenie i obciążenia +6/−3; zmiana kategorii ujawnia odstępstwo od tematu. |
| Limit 100 kW | Wariant z silnikiem 180 kW pozostaje dostępny do analizy, ale jednoznacznie nie spełnia ograniczenia tematu 32. Program nie podmienia wybranego silnika. |
| Łódź turystyczna | Zachowano poprawiony napęd tłokowy i brak wymyślonego dodatkowego cargo 1000 kg. |
| Masa–aerodynamika–paliwo | Nowe tematy domyślnie domykają bilans z biegunową P4 przy zadanej TAS i wysokości. Wstępny wariant 0,94 Kmax pozostaje jawną opcją studium. |
| Zmiana założeń | Biegunowa misji jest liczona ponownie. Relaksacja współczynników oporu usuwa skok na niestabilną gałąź masy po zmianie zasięgu odrzutowca 1200 → 1210 km. |
| Moc/ciąg | Automatyczny dobór sprawdza końcową biegunową, spadek osiągów z wysokością, masę początku przelotu i wznoszenie. Zadana moc silnika pozostaje niezmieniona, także gdy jest niewystarczająca. |
| Powrót i rezerwa | Dolot i powrót mają osobne masy i przydziały paliwa. Paliwo zadania i rezerwy nie jest ponownie zużywane do wykazania zasięgu. |
| Precyzja | Usunięto przedwczesne zaokrąglenia wymiarów i biegunowej powodujące oscylacje iteracji. Tabele nadal formatują wartości do czytelnej liczby cyfr. |
| Kopiowanie P4 | Nowy wariant nie dolicza po raz drugi oporu zastrzałów, klap Junkersa ani stałych szczelin, gdy skopiowana biegunowa już go obejmuje. Projekt źródłowy jest zachowany. |
| Ładownia | Jawne wymiary użytkowe wpływają na obwiednię kadłuba. Tematy 71 i 74 mają roboczą ładownię 8,5 × 3,2 × 3,2 m zamiast pustej kabiny pasażerskiej. To założenie projektu, nie dowód zabudowy konkretnej wersji pojazdu. |
| Woda | Wyłączono lądowe ograniczenie startu i wyniki tarcia/hamowania kół. Drogi wodne są nieobliczone, a nie zerowe. Dodano kontrolę zadanej objętości wypornościowej i jawne braki analizy hydrodynamicznej. |
| Prędkości i wzory | Poprawiono opis VLOF na 1,15 VsTO, wskazano masę lądowania przy Vapp i poprawiono zapis dokładnej równowagi lotu ślizgowego. |
| CS-23 | Obliczeniowe VC w EAS nie ustanawia operacyjnych VMO/VNO w CAS ani MMO. Bez tych danych poziom osiągów pozostaje nieokreślony. |

## Model bilansu przelotu

Dla stałych TAS i wysokości, biegunowej parabolicznej i zmiennej masy:

```text
q = ρV²/2
D = qS CD0 + k (mg)²/(qS) = a + b m²
dm/dx = −c (a + b m²)
m_k = √(a/b) tan[atan(m_p √(b/a)) − R c √(ab)]
```

`c = BSFC/(3,6·10⁹ η)` dla silnika śmigłowego przy BSFC w g/(kW·h).
Dla wejściowego odrzutowego TSFC w 1/h: `c = TSFC/(3600 g V)`.
Obliczenia używają SI. W raporcie zapisano współczynniki, masy faz,
przeliczniki jednostek i oba odcinki misji.

Tolerancja zewnętrznej iteracji wynosi 0,05%; sprawdzana jest również różnica
między biegunową używaną przez bilans a nowo obliczoną. Jawny narzut długości
trasy wynosi 0,1%. To margines numeryczny, oddzielny od rezerwy paliwa.
Brak zbieżności lub osiągalności lotu daje negatywną kontrolę zgodności.
Niezależny test RK4 sprawdza całkę paliwa dla obu rodzajów napędu.

Wstępne wymiarowanie kadłuba z ładownią przyjmuje kołową obwiednię prostokąta:
`D ≥ √(w²+h²)+0,30 m`, `L ≥ l_ładowni+4D`, zachowując większe wymiary
wynikające z układu kabiny. Naddatek 0,30 m i długość nosa/ogona są jawnymi
założeniami geometrycznymi; nie stanowią obliczenia konstrukcji.

## Zakres, którego wynik liczbowy nie zastępuje

- Operacje wodne wymagają oporu hydrodynamicznego, stateczności i podziału
  kadłuba/pływaków, także przy zalaniu. Kryterium 1,8·MTOW pochodzi z CS 23.2310(a).
  Poza zakresem CS-23 jest opisane jako wstępne odniesienie, bez potwierdzenia
  właściwej podstawy certyfikacji.
- Ładownia wymaga sprawdzenia prześwitów, rampy, nacisków, podłogi i mocowań;
  ambulans — noszy, dostępu i ewakuacji; samolot pożarniczy — zbiorników i zrzutu.
- Utrzymano kontrole przekroczenia limitów masy klasy i pozostałe niespełnione
  wymagania. Nie zmieniano prawa ani korelacji tylko po to, aby uzyskać zielony wynik.
- Schemat 3D nie jest modelem wykonawczym kadłuba łodzi, konstrukcji ani instalacji.

## Sprawdzenie

Przed integracją z nowszym `master`: **1127 testów Pythona i 36 testów JavaScript
zakończonych powodzeniem**. Test katalogu obejmuje wszystkie 110 tematów.
Pełne ścieżki Chrome obejmują 13 kategorii: tematy 7, 17, 20, 28, 32, 42, 43,
63, 68, 82, 94, 95, 101. Testy kontrolują równania, zbieżność i zasięg również
po edycji i ponownym otwarciu projektu, zakładki P1–P6, raport offline, eksport
HTML/PDF/DOCX/CSV/JSON oraz szerokości 320 i 390 px.

Polecenia odtworzenia:

```powershell
python -m pytest -q
node --test tests/*.test.mjs
python tests/browser_design_integrity.py --serve
python tests/browser_design_requirements.py
python tests/browser_didactic_card.py --in-process
python tests/browser_didactic_and_engineering.py --in-process
```

Testy przeglądarkowe wymagają Playwright oraz Chrome pod ścieżką wskazaną
w skryptach. Używają osobnych baz w ignorowanym `work/design-integrity-20261030`.
W tym katalogu pozostają logi, JSON wyników, raporty i zrzuty ekranu.
Test importu korzysta z aplikacji Flask w tym samym procesie, przez przekierowanie
żądań Playwright. Chroni to przed trafieniem do innej wersji serwera na porcie
używanym równolegle przez innego agenta. Pełny test 13 kategorii używa osobnego
serwera HTTP; opcja `--in-process` umożliwia również jego izolowane odtworzenie.

## Integracja z master

Połączono zmiany z `master` do `7af59a6`, zachowując nowe moduły profili,
kartotek parametrów, audytu inżynierskiego, aeroelastyczności i akustyki oraz
dobór dla holowania, prędkości wyścigowej i stateczności podłużnej.
Zamiast dwóch konkurencyjnych pętli bilansu API `refine_bipol_project` korzysta
ze wspólnego solvera masy, geometrii i całki paliwa. Zachowano jego interfejs
i historię iteracji zwracaną do przeglądarki.

Wymiarowanie ładowni z założonej gęstości ładunku pozostaje dostępnym
oszacowaniem. Podane wymiary użytkowe mają pierwszeństwo. Raport pokazuje
faktycznie użyty przekrój i długość oraz dodatkowe ograniczenia napędu;
te same równania przechodzą automatyczne sprawdzenie spójności arkusza.
Testy starszego trybu wstępnego jawnie wybierają `preliminary`, ponieważ nowe
tematy domyślnie używają domkniętego bilansu.

Wspólny wynik: **1173 testy Pythona i 36 testów JavaScript — wszystkie zaliczone**.
W przeglądarce sprawdzono ponownie 13 kategorii i dodatkowo ciężkie
transportowce 71 i 74. Osobno sprawdzono 189 kartotek dydaktycznych, przełączniki
trybów, generator profilu 200 mm, wykres doboru i panel nowego audytu.
Import oraz tworzenie nowych wariantów kontrolują zachowanie projektu źródłowego.
Wszystkie 15 pełnych scenariuszy zakończyło się powodzeniem: 480 kontroli
równań przed i po edycji, brak błędów JavaScript i przepełnienia przy 320/390 px.
Import i ponowny wariant przeszły dla wszystkich 13 kategorii. Raporty HTML
otwarto bez sieci i wydrukowano do PDF; sprawdzono również struktury DOCX.
Zwięzłe dane wynikowe zapisano w [WYNIKI_TESTOW_PROJEKTOWANIA_2026-10-30.json](WYNIKI_TESTOW_PROJEKTOWANIA_2026-10-30.json).

Spełnienie zasięgu potwierdzono w modelu dla wszystkich 110 tematów; pozostałe
kontrole zgodności nadal mogą wymagać zmian projektu i danych szczegółowych.

## Podstawy merytoryczne

- [EASA CS-23, aktualna publikacja zbiorcza](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-normal-category-CS-6-AMC-GM-5?erules-id=ERULES-1963177438-15191): zakres kategorii i poziom osiągów CS 23.2005.
- [EASA CS 23.2310, treść wymagania wyporności](https://www.easa.europa.eu/en/downloads/138114/en): nadmiar wyporności i osobne wymaganie odporności na zalanie.
- [NASA — Range Summary](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/range-summary/): zależność zasięgu od paliwa, sprawności i aerodynamiki.
- [NASA — Lift-to-Drag Ratio](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/lift-to-drag-ratio/): równowaga sił i biegunowa aerodynamiczna.
- [Lockheed Martin — C-130J Pocket Guide](https://www.lockheedmartin.com/content/dam/lockheed-martin/aero/documents/C-130J/C130JPocketGuide.pdf): przekroje ładowni jako odniesienie do analizy zabudowy, bez utożsamiania wymiarów badanego projektu z C-130J.
- Lokalne materiały BIPOL_1, BIPOL_2 i przewodnik Z. Paturskiego: etapowe bilanse,
  korelacje i metoda osiągów. Raport zachowuje rozróżnienie metod kursowych
  od sprawdzenia końcowej biegunowej przy wymaganym punkcie lotu.
