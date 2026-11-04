# Interfejs pracowni

Zmiany uwzględniają commit `76d212d`, w tym blokady parametrów, nowe obrysy,
bazę geometryczną, motoszybowce i metodykę Paturskiego.

## Widoki

- Kreator projektu jest główną, domyślnie otwieraną zakładką. Ma pięć etapów:
  temat i założenia, misję, napęd, aerodynamikę oraz weryfikację przed obliczeniem.
  Można swobodnie przechodzić między etapami. Nawigacja przyciskami i klawiaturą
  przewija do nagłówka nowego etapu, z uwzględnieniem górnego paska.
  Niezastosowany szkic jest przechowywany osobno dla każdego projektu i przetrwa
  zmianę zakładki oraz ponowne otwarcie strony. Projekt i jego wyniki zmieniają się
  po udanym przeliczeniu; można też wczytać zapisane założenia.
- W etapie aerodynamiki wybiera się podanie C_D0 całego samolotu albo S_wet/S
  z własnego pomiaru lub przykładowego układu. Druga metoda pozwala wyznaczyć
  doskonałość z wykresu Raymera lub podać własny odczyt. Podgląd pokazuje drogę
  obliczeń i wynik biegunowej. Nieaktywne pola nie blokują zapisu. Współczynnik
  Oswalda i opis źródła danych są wspólne dla obu metod; zapis i ponowna edycja
  zachowują wybraną metodę.
- Przegląd pokazuje cztery główne wskaźniki, rysunek i bilans masy.
- Drzewo obliczeń prowadzi od niezależnych założeń przez kolejne poziomy wyników.
  Pokazuje wartości, wzory i główne zależności bieżącego projektu. Uwzględnia wybrany
  tryb skrzydła, masy płatnej i napędu; nawigacja po poprzednikach otwiera również
  schowane założenia. Edycja danych oznacza widoczne wyniki jako wymagające przeliczenia.
- Założenia mają własną stronę; formularz nie poprzedza analiz na telefonie.
  Główna grupa misji jest rozwinięta, pozostałe grupy otwiera użytkownik.
  Tryb zaawansowany, blokady i sugerowane ograniczenia pozostają dostępne.
- Analizy szczegółowe są w rozwijanej grupie nawigacji. Pierwsza sekcja wyniku
  jest otwarta; dalsze tabele i wykresy otwiera użytkownik. Wzory są pod osobnym
  rozwinięciem. Opisy kolumn można włączyć przyciskiem „Objaśnienia”.
- Trendy mają zakładki Wyniki, Dobór samolotów oraz Metoda i źródła.
  W wynikach wybiera się jeden wykres; w doborze działają te same filtry,
  ręczna próba, wyszukiwanie i eksporty. Uwagi pozostają dostępne pod wyraźnym
  rozwinięciem z liczbą komunikatów.
- Opcje projektu zbierają nowy projekt, menedżer, kopię i eksport JSON.
  Raporty oddzielają zakres od danych autora, notatek i dodatkowych formatów.

Kontekstowe objaśnienia i źródła pozostają dostępne, bez powtarzania wszystkich
opisów na każdym ekranie. Zmiany układu nie ograniczają danych w eksporcie.

## Dostępność i błędy

W widoku **Baza i trendy** przycisk **Otwórz edytor bazy samolotów** prowadzi do
wyszukiwania katalogu. Wybór **Cała baza — wszystkie klasy** umożliwia przeglądanie
także konstrukcji spoza klasy projektu. **Parametry / edytuj** otwiera formularz
z grupami danych i podglądem wydłużenia, udziału masy pustej oraz obciążeń.
Puste pole oznacza brak danych; opcjonalne wartości można wyczyścić.
**Sprawdź dane** waliduje rekord bez zapisu. **Zapisz we wspólnej bazie** zapisuje
zmiany lokalnie, dla wszystkich projektów, i odświeża analizę trendów.

Dla zbioru **Dokumentacja producentów i TCDS** edytor udostępnia odczyty z oryginalnymi
jednostkami, wartości przeliczone w bazie, odnośniki do publikacji, warunki i pominięte
obserwacje. Zmiana rekordu w bazie jest oznaczana jako różnica względem zestawienia
źródłowego. Pełne zestawienie można pobrać jako JSON.

**Użyj jako punkt startowy projektu** otwiera kreator z dostępnymi danymi
katalogowymi. Brakujące założenia pochodzą z profilu klasy i wymagają przeglądu.
Katalogowe MTOW i OEW pozostają danymi porównawczymi; projekt jest zapisywany
dopiero po zatwierdzeniu kreatora i udanym przeliczeniu. Okno edytora obsługuje
klawiaturę, ogranicza fokus do swoich kontrolek i przy zamknięciu przywraca go
do przycisku otwierającego.

Akordeony formularza obsługują Enter i Spację. Zakładki trendów obsługują strzałki,
Home i End, mają role tab/tabpanel i właściwe aria-selected. Stan blokady jest
ogłaszany przez aria-pressed. Menu mobilne obejmuje fokusem widoczne elementy
i zamyka się Escape; okna projektu przywracają fokus na widoczne opcje.

Błąd obliczeń pojawia się również poza edytorem. „Sprawdź założenia” otwiera
edytor, odpowiednią grupę i nieprawidłowe pole. Stare wyniki pozostają oznaczone
jako nieaktualne. Brak krzywej wznoszenia szybowca daje komunikat zamiast błędu JS.

## Raporty

KaTeX 0.16.9 wraz z fontami jest dołączony lokalnie. Raport zawiera dane fontów,
CSS i JavaScript, więc skład wzorów działa bez CDN i bez połączenia z aplikacją.
Poprawiono uszkodzone sekwencje TeX w szablonach oraz podwójne indeksy.
Najdłuższe porównania podzielono na krótsze wzory i tekstowe statystyki.

Precyzja danych biegunowej szybowania pozostaje pełna; zaokrąglenia dotyczą
prezentacji. Testy zachowują nowy model wydłużenia efektywnego oraz rozszerzone
zbiory referencyjne z `76d212d`.

## Symbole i indeksy

`static/js/symbols.js` składa indeksy dolne i górne w aplikacji i w raportach,
również w komunikatach z backendu. W tekstach źródłowych symbole zapisuje się
jawnie: `V_S0`, `C_x,szk`, `(W/S)_max`, `m_0^C`, `C_{x0}`. Moduł rozpoznaje też
zapisy łączne, np. `VS0`, `Vs1`, `Cz max`, `Cx₀` i `Kmax`. Skróty `wy`, `Sto`
i `me` trzeba pisać jako `w_y`, `S_to` i `m_e`, bo nie da się ich odróżnić od słów.

- Etykiety wykresów canvas rysuje `BipolSymbols.fillText(ctx, …)`.
- Tekst z indeksami kopiuje się przez `BipolSymbols.source(el)`. `textContent`
  zamienia w<sub>y</sub> na „wy”.
- `<option>`, `title` i `aria-label` nie mogą zawierać indeksów. Listy wyboru
  podają nazwę wielkości bez symbolu; symbol pokazuje wykres.
- Wzory `\( … \)` w aplikacji składa ten sam lokalny KaTeX co w raportach.

## Weryfikacja

```sh
work/venv/bin/python -m pytest tests -q
node tests/studio_core.test.mjs
python tests/browser_workspace.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
python tests/browser_studio.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
python tests/browser_trends.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
```

Testy przeglądarkowe wymagają `requirements-browser.txt` i uruchomionej aplikacji.
Obejmują edycję i blokady, objaśnienia, odzyskiwanie po błędzie, wybór próby,
warianty, eksporty, tryb semestralny, zapis, niedostępną pamięć oraz szerokości
320–1600 px. Raporty P1–P6 sprawdzono pod kątem poprawnego renderowania matematyki.
