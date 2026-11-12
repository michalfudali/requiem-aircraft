# Dane napędu w natywnym modelu

Aktualizacja 12.11.2026 usuwa rozbieżności między kanonicznymi parametrami
projektu a dwoma generatorami OpenVSP.

| Dane projektu | Poprzedni skutek | Zmiana |
| --- | --- | --- |
| `n_engines = 2` w Studio | Odczytywano `engine_count`; odrzutowy samolot dwusilnikowy mógł mieć jedną gondolę | Odczyt kanonicznego `n_engines`, z obsługą dawnego pola tylko przy jego braku |
| `engine_type = prop` w adapterze analiz | Warunek rozpoznawał tylko `piston`, `turboprop`, `electric`; pomijał śmigło rzeczywistego projektu BIPOL | Rozpoznanie kanonicznego typu `prop` |
| `blade_count` | Adapter czytał inne pole, a domyślne liczby łopat generatorów różniły się | Pierwszeństwo `blade_count`, następnie dawne `propeller_blades`; wspólny domyślny wybór dwóch łopat lub czterech dla klasy regionalnej turbośmigłowej |

Średnica śmigła pozostaje związana z końcowym wynikiem P4. Regresje porównują
natywny odczyt `Diameter` i `NumBlade` z danymi projektu. Dla jednego i dwóch
silników liczą również fizyczne kopie brył z uwzględnieniem symetrii. W testach
stare pola mają celowo inne wartości, aby nie mogły zastąpić danych kanonicznych.

Macierz obejmuje oba generatory oraz siedem klas: tłokowy GA, regionalny
turbośmigłowy, odrzutowy dyspozycyjny, transportowy, motoszybowiec, szybowiec
i UAV. Szybowiec nie otrzymuje śmigła ani gondoli silnika.

W osobnym worktree po poprawce zaliczono 90 testów natywnego Studio i adaptera
(w tym 14 nowych kombinacji klasy i generatora), następnie cztery dodatkowe
kontrole domyślnej liczby łopat. Zestaw danych i makiet adaptera zaliczył 35
kontroli, a ponowione scenariusze Chromium katalogu i rzeczywistego modelu
tematu 7 — sześć. Dane natywne nie wymagają makiet w scenariuszach przeglądarki.
Dowody: `work/propulsion-native.xml`, `work/propulsion-defaults.xml`,
`work/propulsion-adapter.xml`, `work/propulsion-browser.xml` w worktree poprawki.

Pełny backend i pełną przeglądarkę etapu obrysu sprawdzono przed tą poprawką
parametrów natywnego napędu; opis i identyfikator rewizji: [OBRYS_OPENVSP.md](OBRYS_OPENVSP.md).

Zakres tej poprawki dotyczy przekazywania typu, liczby napędów, średnicy i liczby
łopat. Nie potwierdza konkretnych miejsc mocowania, masy kompletnej zabudowy
ani prześwitów wszystkich konfiguracji. Geometria rozmieszczenia nadal ma
charakter koncepcyjny; układy powyżej dwóch silników wymagają osobnego rozszerzenia
i sprawdzenia. Otwarte wymagania projektu tematu 7 pozostają w jego audycie.
