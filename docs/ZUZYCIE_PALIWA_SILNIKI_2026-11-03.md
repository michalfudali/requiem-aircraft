# Rzeczywista propozycja silnika jako podstawa bilansu paliwa

## Zmiana zachowania

W zakładce „Masy i napęd” wybiera się rzeczywisty model i wariant silnika oraz punkt
zużycia paliwa z jego dokumentacji. Alternatywnie autor podaje własny rzeczywisty
silnik, moc ciągłą / ciąg jednego silnika, SFC, dokument i warunki odczytu. Dane
autora mają osobny status: nie oznaczają niezależnego sprawdzenia dokumentu.

Przyjęty silnik ustala dostępną moc lub ciąg. Wymaganie z diagramu doboru, końcowej
biegunowej i modelu startu pozostaje oddzielną wielkością. Zbyt mały silnik nie
„rośnie” do wymaganego ciągu; warunek doboru jest niespełniony.

Stary projekt bez danych silnika można nadal liczyć jako oszacowanie robocze.
Nie uzyskuje jednak potwierdzenia podstawy paliwowej: niespełniony warunek weryfikacji,
brak danych w przeglądzie BIPOL 1 i blokada gotowości podpunktu bilansu P2.1.
Raporty P2, P4 i P5 pokazują wprost brak udokumentowanego silnika. Szybowiec bez
napędu nie wymaga fikcyjnej propozycji silnika.

## Dane źródłowe sprawdzone 3 listopada 2026

Katalog silników (tabela `engines` w `data/aircraft/aircraft.sqlite3`) zawiera odczytane wielkości, lokalizatory i adresy
dokumentów, bez kopii podręczników producentów.

| Silnik | Dane zużycia używane domyślnie | Dokument |
| --- | --- | --- |
| Rotax 912 UL | 16,2 l/h przy 75% maksymalnej mocy ciągłej 58 kW | [BRP-Rotax OM-912, Ed.4 Rev.1, §2.1 i §5.2, s. 5-8](https://www.rotax-owner.com/pdf/OM_912-Series_ED4_R1.pdf) |
| Rotax 912 ULS | 18,5 l/h przy 75% maksymalnej mocy ciągłej 69 kW | Ten sam dokument, §2.2 i §5.2 |
| Lycoming O-360-A1A | 10,5 US gal/h przy 135 HP, 2450 obr/min | [Lycoming 60297-12, §3, s. 3-12](https://www.lycoming.com/sites/default/files/file/2025-11/60297-12%20-%20O-360%2C%20HO-360%2C%20IO-360%2C%20AIO-360%2C%20HIO-360%2C%20and%20TIO-360%20Series.pdf) |
| Lycoming IO-360-A1A | 12,3 US gal/h przy 150 HP, 2450 obr/min | Ten sam dokument, s. 3-13 |
| Hirth 4103 | 517 g/(kW·h), 6500 obr/min | [Hirth, specyfikacja 4103](https://hirthengines.com/4103-engine-air-cooled-two-stroke-engine/) |
| PBS TP100 | 0,548 kg/(kW·h); warunki punktu nieokreślone w broszurze | [PBS Turbine Engine Portfolio, s. 12](https://www.pbs.cz/api/document-files-en/file/PBS_Brochure_Turbine_Engines.pdf) |
| PBS TJ100 | 0,118 kg/(N·h); warunki punktu nieokreślone w broszurze | Ten sam dokument, s. 7, tabela SI |

Rotax ma także punkty maksymalnej mocy ciągłej i startowej. Użycie mocy startowej
przez ponad 5 minut i żądanie mocy większej od opublikowanej są odrzucane.
Własne SFC zadania na maksymalnym ustawieniu wymaga osobnego odniesienia do
dokumentu i warunków. Sam punkt przelotowy nie dokumentuje zadania maksymalnego.

Hirth 4103 przeznaczony jest do UAV. Jego moc 4,97 kW jest opisana jako zmierzona.
TP100 ma opublikowaną maksymalną moc 180 kW, bez potwierdzenia mocy ciągłej w tym
źródle. Nie przypisano punktowi SFC arbitralnie mocy 180 kW. Użycie takiej mocy
w modelu osiągów oznaczono jako górne oszacowanie wymagające instrukcji wariantu.
TJ100 reprezentuje rodzinę o zakresie 1100–1250 N: do wstępnej oceny przyjęto dolną
granicę, a konieczność wskazania wariantu pozostaje widoczna. To nie katalog
silników do wszystkich klas samolotów; dla innych napędów potrzebne jest własne źródło.

## Jednostki i tok obliczeń

Dla silnika śmigłowego o znanym zużyciu objętościowym:

\[
c_P[\mathrm{g/(kW\,h)}]
=\frac{1000\rho_f[\mathrm{kg/l}]\dot V_f[\mathrm{l/h}]}{P_{ref}[\mathrm{kW}]}.
\]

Gęstość 0,72 kg/l jest jawnym, edytowalnym założeniem przeliczenia. Nie jest
podawana jako pomiar producenta. Moc odniesienia odpowiada temu samemu punktowi
co przepływ. Dla Rotaxa UL: 75% × 58 = 43,5 kW, stąd
16,2 × 0,72 × 1000 / 43,5 = 268,137931 g/(kW·h).

1 US gal = 3,785411784 l; 1 HP mechaniczny = 0,7456998715822702 kW.
Nie używa się galona imperialnego ani polskiego KM do przeliczenia tabel Lycominga.

Dla silnika odrzutowego model BIPOL stosuje zużycie względem ciężaru:

\[
(c_Tg)[\mathrm{h^{-1}}]=c_T[\mathrm{kg/(N\,h)}]\,g_0,
\qquad g_0=9{,}80665\ \mathrm{m/s^2}.
\]

Dla TJ100 daje to 0,118 × 9,80665 = 1,1571847 h⁻¹. Liczba silników skaluje
łączny ciąg lub moc, nie skaluje SFC. Ponowne otwarcie projektu nie może ponownie
mnożyć SFC przez g ani liczbę silników.

Arkusz i drzewo obliczeń zawierają dane producenta, moc punktu, gęstość oraz
przeliczenie. Wymiarowanie napędu ma oddzielny łańcuch: moc/ciąg jednego silnika
× liczba silników → dostępna moc/ciąg → osiągi. Raport wymienia źródło i warunki.
Metadane źródłowe przysłane jako `_engine_fuel` nie są zaufane: serwer odbudowuje
je z rzeczywistego wyboru i katalogu.

## Granice modelu

Stałe SFC z wybranego punktu jest przybliżeniem poza jego mocą, obrotami, wysokością
i prędkością. Nie jest pełną mapą silnika. Statystyczne ułamki masy w fazach misji,
np. startu i lądowania, pozostają metodą przewodnika BIPOL; nie przedstawia się ich
jako zmierzonego spalania wybranego silnika. Ocena wystarczalności mocy/ciągu nie
jest potwierdzeniem dopuszczenia zabudowy.

## Powtarzalna weryfikacja

```powershell
python -m pytest -q -p no:cacheprovider
python tests/browser_engine_fuel.py --base-url http://127.0.0.1:5017
python tests/browser_unified_trends.py --base-url http://127.0.0.1:5017
```

Pierwszy skrypt przeglądarkowy sprawdza rzeczywiste wybieranie silnika, zmianę
gęstości i masy paliwa, brak źródła, własne dane, zapis i odświeżenie projektu,
widok mobilny oraz 21 raportów P2/P4/P5 dla siedmiu propozycji. Drugi sprawdza
42 raporty P1–P6 dla siedmiu klas konstrukcyjnych. W obu przypadkach wzory
renderowane są offline i sprawdzane pod kątem błędów KaTeX oraz szerokości A4.
Artefakty kontroli znajdują się lokalnie w ignorowanym katalogu `work/engine-fuel-qa`.

Wynik weryfikacji: pełna regresja 2016 testów Python, następnie 176 testów dla
końcowych zmian; 51 testów JavaScript; 63 raporty offline i opisane wyżej
interakcje w Chromium bez błędów.
