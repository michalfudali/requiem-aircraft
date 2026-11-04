# Scalenie M1, analizy trendów i danych silników

Scalono lokalny `583d472` z opublikowanym `36ede72`, rozwiązując konflikty w 25
plikach. Zachowano lokalne raporty M1, wyważenie i balast oraz opublikowane źródła
zużycia paliwa, pełne obliczenia trendów i wspólną próbę porównawczą.

Obie gałęzie nadawały zawężaniu próby inną interpretację. W „Samolotach i trendach”
dostępny jest jawny wybór `trend_reference_mode`:

- `initial`: najbliższe samoloty względem założonej `mass_initial_guess`; zachowuje
  zachowanie opublikowanych projektów i API.
- `design`: lokalna metoda iteracyjna, w której odniesienie wynika z bilansu masy
  tej samej próby. Uwzględnia cykle doboru i poszerzanie próby przy braku rozwiązania.

Oficjalne tematy BIPOL zachowują metodę `design` i równanie (1) własnej próby.
Projekty własne zachowują jawnie wybrany model masy; automatyczny dobór nadal
ocenia jakość regresji. Stare lokalne projekty zawierające `_reference` migrują
wybór metody do `design`, ale wszystkie zapisane liczby odniesienia są odrzucane
i obliczane ponownie. Jawny wybór `initial` ma pierwszeństwo przed migracją.

API propozycji parametrów otrzymuje pełną misję dla metody `design`; propozycje,
bilans i raport P1 korzystają z identycznej próby. Arkusz P2 wskazuje współczynniki
linii P1 przy modelu `trend`, a dla korelacji klasy pokazuje jej własne
współczynniki, poprawki i ograniczenia. Zależności nie są mieszane między modelami.

Poprawiono również przedwczesne zaokrąglenie przeciążenia w arkuszu zakrętu.
Podstawienia używają pełnej wartości obliczeniowej, zgodnej z obliczeniem kąta.
Kontrola interpunkcji raportu zachowuje miejsce wzoru podczas analizy prozy,
żeby poprawny zapis „..., \(R^2\geq0{,}2\), ...” nie dawał fałszywego błędu.

Testy integracyjne obu metod, migracji i źródeł silnika:
`tests/test_merge_sample_modes.py`. Kopia stanu sprzed rozwiązania konfliktów,
indeksu i różnic znajduje się lokalnie w ignorowanym
`work/merge-recovery-20261104/`.

Końcowa weryfikacja: 2189 testów Python i 51 testów JavaScript zakończonych
powodzeniem. W Chromium sprawdzono 63 raporty P1–P6 / P2–P5 offline, wzory
KaTeX, szerokość A4, wybór danych silnika, obie metody próby, starsze projekty,
zapis i ponowne otwarcie oraz układ i nawigację przy szerokościach 320–1600 px.
Log końcowej regresji: `work/merge-recovery-20261104/pytest-final.log`;
wynik JUnit: `work/merge-recovery-20261104/pytest-final.xml`.
