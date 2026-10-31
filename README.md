# BiPOL Requiem - System Wstępnego Projektowania Samolotów (MEiL PW)

Kompletne środowisko projektowo-obliczeniowe wspierające przedmioty **BIPOL I** (NK307 *Budowa i Projektowanie Obiektów Latających I*) w **Zakładzie Samolotów i Śmigłowców (ZSiS)** oraz **Mechanika Lotu I** (ML.NK472) w **Zakładzie Mechaniki (ZM)** na **Wydziale Mechanicznym Energetyki i Lotnictwa Politechniki Warszawskiej (MEiL PW)**.

---

## Uruchomienie i sprawdzenie zmian

Wdrożenie internetowe w Google Cloud (Docker, Gunicorn, trwała baza SQLite i HTTPS):
[`docs/WDROZENIE_GCP.md`](docs/WDROZENIE_GCP.md).

Python 3.11 lub nowszy:

Na systemie Windows serwer uruchamia się bezpośrednio skryptem:
```bat
run.bat
```
Zależności instaluje się jednorazowo:
```sh
py -3.11 -m pip install -r requirements.txt
```

Serwer nasłuchuje domyślnie tylko na `127.0.0.1:5000`. Zmienne środowiskowe:
`PORT` (port), `HOST` (np. `0.0.0.0`, aby udostępnić aplikację w sieci) oraz
`FLASK_DEBUG=1` (debugger Werkzeuga). Debuggera nie włączaj razem z `HOST=0.0.0.0`,
bo pozwala on wykonać dowolny kod na komputerze z serwerem.

Testy regresji: `py -3.11 -m pip install -r requirements-dev.txt`, potem `py -3.11 -m pytest tests -q`.
Testy narzędzi pracowni: `node --test tests/studio_core.test.mjs tests/aircraft_project.test.mjs`
(Node 20, bez zależności npm). Oba zestawy uruchamia GitHub Actions (`.github/workflows/tests.yml`).
Raporty są dokumentami HTML, które można wydrukować do PDF w przeglądarce.

Raport zbiorczy i osobne sprawozdania P1–P6 mają wspólny skład A4: stronę
tytułową, opis metody, wyniki, wnioski zależne od obliczeń oraz bibliografię.
Tabele, rysunki i wzory są numerowane. Próba porównawcza trafia do załącznika.
Dane autora uzupełnia się w widoku raportów lub przed wydrukiem; program nie
wstawia przykładowej tożsamości. Datę i rok akademicki można zmienić.
Wzory, fonty i wykresy pozostają dostępne w pobranym HTML bez internetu.

Test wydruków i raportów offline (wymaga Chromium, `requirements-browser.txt`
i narzędzia `pdftotext`):
`python tests/browser_reports.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium`.

Pracownia zawiera kokpit z nawigacją boczną, porównanie do ośmiu zapisanych
wariantów, eksport CSV/SVG, raport z wyborem etapów P1–P6, dane i wnioski autora
oraz dokładną biegunową lotu szybowego. Raport można pobrać jako samodzielny HTML.
Szczegóły integracji i testów są w `docs/INTEGRACJA_STUDIO.md`.

Interfejs otwiera od razu zapisany projekt. Założenia mają osobny widok, analizy
pokazują szczegóły na żądanie, a w trendach widoczny jest jeden wybrany wykres.
Układ, dostępność i testy opisuje [`docs/INTERFEJS.md`](docs/INTERFEJS.md).

Kreator pozwala wybrać temat i niezależne założenia: rozpiętość, powierzchnię lub
wydłużenie skrzydła, masę płatną, liczbę pasażerów i dostępną moc. Parametry
zależne są tylko do odczytu. Motoszybowce powyżej 20 m otrzymują spójną geometrię.
Szczegóły i testy: [`docs/ZALOZENIA_PROJEKTU.md`](docs/ZALOZENIA_PROJEKTU.md).

Wytyczne z zajęć: sześć wykresów P1, kontrola minimum ośmiu konstrukcji,
K przelotu = 0,94 Kmax, pełne długości startu/lądowania, masa pasażera z bagażem
115 kg i arkusze A4 do rysunków. Brakujące dane katalogowe można uzupełnić
przez CSV ze źródłem. Odczyt wszystkich pięciu fotografii, zakres wdrożenia
i niejednoznaczne dopiski: [`docs/WYTYCZNE_PROWADZACEGO.md`](docs/WYTYCZNE_PROWADZACEGO.md).

Widok **Baza i analiza trendów** korzysta z bazy SQLite `data/aircraft/aircraft.sqlite3`
(**872 konstrukcje i warianty** z FAST Aerobase, ENAC CADO, zestawienia motoszybowców
i geometrii): filtry i ręczny dobór próby, regresję udziału masy pustej,
trendy czasowe z prognozą +5 lat, zależności osiągów i eksport danych ze źródłami.
Daty certyfikacji są jawnie odróżnione od lat produkcji, a brakujące dane pozostają
oznaczone. Wdrożenie obu materiałów P1 i ograniczenia metod opisuje
[`docs/ANALIZA_TRENDOW.md`](docs/ANALIZA_TRENDOW.md), a strukturę bazy, pochodzenie
i licencje danych [`data/aircraft/README.md`](data/aircraft/README.md).

Model służy do obliczeń dydaktycznych. Sprawdza wybrane warunki i nie stanowi
potwierdzenia certyfikacji. Wszystkie poziomy CS-23 1–4 obejmuje limit 8618 kg
i maksymalnie 19 miejsc pasażerskich. Poziomu osiągów nie określa się z Vcr TAS;
wymagane są VMO/VNO KCAS oraz MMO. Kategorie operacji UAS wynikają z oceny
ryzyka, a nie z podziału na masy poniżej i powyżej 600 kg.

Źródła: [EASA CS 23.2005](https://www.easa.europa.eu/en/downloads/22283/en),
[EASA: kategorie operacji UAS](https://www.easa.europa.eu/en/domains/drones-air-mobility/operating-drone).

Podział na poziomy pochodzi z obowiązującej CS-23 Amdt 5 (CS 23.2005). Obwiednia V-n
i współczynniki przeciążeń są liczone **metodą wg CS-23 Amdt 4 (§23.333–23.345) i
Danileckiego**. Amdt 5 usunęła te paragrafy i przeniosła ich treść do środków spełnienia
wymagań (AMC, normy ASTM), więc w sprawozdaniu należy je opisywać jako metodę, a nie
obowiązujący przepis. Podmuch 66 ft/s przy VB jest liczony tylko dla kategorii commuter;
dla CS-25 linie podmuchu Pratta są uproszczeniem (CS-25.341 stosuje podmuch dyskretny 1-cos).
Klasyfikacja krajowa: rozporządzenie Ministra Infrastruktury w sprawie klasyfikacji
statków powietrznych (t.j. Dz. U. z 2025 r. poz. 1137).

---

## 🌐 Adresy uruchomionej aplikacji

- **Główny kokpit projektowy:** 👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
- **Podgląd sprawozdania i wydruk PDF:** **[http://127.0.0.1:5000/report](http://127.0.0.1:5000/report)**
- **API oficjalnych tematów wydziałowych:** `http://127.0.0.1:5000/api/topics`
- **API odnośników do materiałów dydaktycznych:** `http://127.0.0.1:5000/api/scraped-files`

---

## Funkcje

Widok **Plan na 5,0** łączy plan punktów z przeglądem wszystkich 21 podpunktów
P1–P6. Według lokalnego regulaminu 2026/27 ocena 5,0 wymaga 191–200 pkt
łącznie z projektów i zejściówek oraz spełnienia osobnych warunków zaliczenia.
Można zapisać odniesienia do własnych opracowań, sprawdzić ich aktualność po
zmianie wariantu i utworzyć nowy projekt z biegunową P4 przeniesioną do P2.
Raport zawiera przegląd braków i opracowań dla wybranego zakresu.
Wyniki audytu i ograniczenia: [Audyt na 5,0](docs/AUDYT_NA_5_2026-10-24.md).

### 1. Baza 110 tematów projektowych z wydziałowej listy BIPOL I:
Aplikacja zawiera wszystkie **110 tematów** podzielonych na **13 kategorii**:
1. **Motoszybowce** (1- i 2-miejscowe; rozpiętości 13,5m, 15m, >20m; silnik ciągnący, pchający, chowany)
2. **Samoloty ultralekkie (ULM / LSA)** (1- i 2-miejscowe, dolnopłaty i górnopłaty, układ tandem / obok siebie)
3. **Odrzutowe samoloty rekreacyjne** (1- i 2-miejscowe, 1 lub 2 silniki odrzutowe)
4. **Samoloty wyścigowe i akrobacyjne** (Formuła 1, klasa Sport, Red Bull Air Race, akrobacyjne)
5. **Samoloty szkolne i szkolno-treningowe** (do 100 kW, do 200 kW, turbośmigłowe, odrzutowe)
6. **Samoloty turystyczne i STOL** (2- i 4-miejscowe, daleka turystyka)
7. **Samoloty medyczne i sanitarne** (pilot, lekarz, chory leżący, STOL, 1- i 2-silnikowe)
8. **Samoloty dyspozycyjne (Business Jets & Turboprops)** (4-, 6-, 8-, 10-, 15-, 20-miejscowe, zasięgi 500 – 3000 km)
9. **Samoloty transportowe STOL** (ładunek użyteczny 1300 kg – 23 000 kg z rampą załadunkową)
10. **Samoloty pasażerskie** (40, 70, 100, 200 miejsc; turbośmigłowe i odrzutowe; dolnopłaty i górnopłaty)
11. **Samoloty rolnicze i pożarnicze** (zbiorniki chemikaliów i wody 500 – 6000 kg)
12. **Wodnosamoloty i łodzie latające** (turystyczne 4-miejscowe i transportowe 1000 – 3000 kg)
13. **Samoloty szturmowe i specjalne** (1- i 2-miejscowe, turbośmigłowe i odrzutowe)

### 2. Pełna swoboda wpisywania i dostosowywania parametrów przez użytkownika:
- **Wymagana rozpiętość $b$ [m]:** możliwość narzucenia dokładnej rozpiętości (np. 13.5m, 15m dla motoszybowca) lub wpisania `0` dla doboru automatycznego z optymalnego wydłużenia $\Lambda$ i powierzchni nośnej $S$.
- **Zasięg $R$ [km]** oraz wysokość przelotu $H$ [m].
- **Masa płatna:** liczba pasażerów, masa załogi, ładunek cargo $m_{cargo}$ [kg].
- **Rodzaj napędu:** tłokowy (piston), turbośmigłowy (turboprop), odrzutowy (turbofan/turbojet).
- **Położenie zespołu napędowego:** dziób (ciągnący), skrzydła (gondole wielosilnikowe), tył kadłuba (pchający), chowany w kadłubie.
- **Konfiguracja płatowca:** dolnopłat, górnopłat (np. STOL), średniopłat; skos skrzydła $\chi_{25\%}$, wznos $\Gamma$.

### 3. Materiały wydziałowe
Repozytorium nie zawiera materiałów dydaktycznych wydziału ani podręczników. Zakładka
**„📥 Materiały z Wydziału”** odsyła do stron źródłowych (BIPOL I w ZSiS, Mechanika Lotu I
w ZM, Zapis Konstrukcji CAD I w ZPK, podręcznik Danileckiego w DBC, monografia Galińskiego
w Łukasiewicz – ILOT). Materiały chronione hasłem pobiera się po zalogowaniu danymi od
prowadzącego.

Własne kopie można trzymać w katalogu `scraped_materials/` (ignorowanym przez git):
aplikacja wyświetli je wtedy w tej samej zakładce, tylko na Twoim komputerze. Skrypty
`scrape_*.py` też są ignorowane, a dane logowania przyjmują wyłącznie ze zmiennych
środowiskowych (`BIPOL_USER`, `BIPOL_PASSWORD`, `ML1_LOGIN`, `ML1_PASSWORD`).

---

## 📊 Wykresy inżynierskie i schematy (Renderowane Standalone)

1. **Diagram doboru parametrów (Matching Chart):** Ograniczenia $W/S$ vs $T/W$ lub $P/W$ z zaznaczonym punktem projektowym.
2. **Biegunowa aerodynamiczna $C_z(C_x)$:** Konfiguracja gładka, startowa oraz z klapami do lądowania i wysuniętym podwoziem.
3. **Rozkład siły nośnej wg Schrenka:** Wykres obciążenia trapezowego, eliptycznego i wypadkowego rozkładu Schrenka wzdłuż rozpiętości.
4. **Krzywa prędkości wznoszenia $w_y(V)$:** Biegunowa prędkości i punkt maksymalnego wznoszenia $w_{y,max}$.
5. **Obwiednia obciążeń dopuszczalnych $V-n$:** Obwiednia manewrowa i linie podmuchów pionowych metodą wg CS-23 Amdt 4 i Danileckiego (dla CS-25 uproszczenie Pratta).
6. **Diagram wyważenia:** Osobne punkty dla stanów załadowania, obliczony zakres środka masy i granica minimalnego zapasu stateczności 5% ŚDA. Tabele P3/P6 korzystają z tej samej oceny co obliczenia; samolot pusty jest stanem naziemnym. Raport P3 podaje też sumę momentów mas i zapas stateczności każdego stanu w locie.
7. **Rysunek zestawieniowy 3-widokowy SVG (CAD):** Parametryczny rzut z góry, z przodu i z boku uwzględniający górnopłat/dolnopłat, rozpiętość, kadłub i usterzenia.
