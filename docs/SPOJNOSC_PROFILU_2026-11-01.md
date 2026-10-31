# Spójność profilu skrzydła — 01.11.2026

Osobny worktree `bipol-profile-state-20261031`, gałąź
`fix/airfoil-project-state-20261031`, początek od `eeb2de0`.
Dołączono aktualizację `master` z `f098bc9`, zachowując niezależne
zmiany drugiego agenta dotyczące hałasu szybowców i motoszybowców.

## Potwierdzone problemy

Przed zmianą odtworzono w rzeczywistym Chrome:

- po ręcznym wyznaczeniu NACA 23012 import projektu z NACA 0012
  aktualizował wynik obliczeń, ale pozostawiał stary rysunek i tabelę;
- starszy plik bez pól profilu dziedziczył nazwę i rzędne z formularza
  poprzedniego projektu, zmieniając w ten sposób przyjęte dane;
- nieudana próba wyznaczenia innego profilu pozostawiała poprzedni SVG
  i aktywne przyciski jego drukowania oraz pobierania;
- zwykły przycisk pomijał wklejone rzędne, choć obliczenia i raport
  dawały im pierwszeństwo;
- wklejone rzędne z nagłówkiem, przy pustym polu nazwy, otrzymywały
  w projekcie etykietę domyślnego NACA zamiast nazwy z nagłówka.

Pierwsze odtworzenie zapisano w `work/profile-state-20261031/before.json`.

## Zmiana

Projekt, osobne API profilu i raport korzystają z tej samej procedury
`airfoil_200mm`. Geometria powstaje raz podczas obliczenia projektu;
P3 zawiera teraz niewielki zestaw metadanych: nazwę, pochodzenie,
cięciwę, grubość względną i jej położenie. Tabeli oraz SVG nie dublowano
w tym zestawie. Panel zawsze aktualizuje się z przyjętego wyniku.

Rzędne mają pierwszeństwo także po użyciu zwykłego przycisku. Przy pustej
nazwie wykorzystuje się nagłówek rzędnych, a bez nagłówka opis danych
wklejonych. Nazwy są normalizowane wspólnie dla API i projektu.
Wybranie przycisku skalowania bez rzędnych zgłasza brak danych.

Zmiana projektu resetuje pominięte pola i unieważnia poprzedni podgląd.
Edycja profilu albo rzędnych usuwa stary rysunek i tabelę oraz wyłącza
drukowanie i pobieranie. Pola P3 oznaczają również wynik projektu jako
wymagający przeliczenia, więc eksport raportu uwzględnia bieżące dane.

Każde zapytanie o profil ma numer i przypisany projekt oraz dane wejściowe.
Nowa edycja lub zmiana projektu anuluje poprzednie zapytanie. Spóźniona
odpowiedź ani spóźniony błąd nie mogą nadpisać aktualnego podglądu.
Eksport sprawdza dodatkowo zgodność danych wyświetlonego profilu
z aktualnym formularzem. Nazwa pobieranego pliku pochodzi z tego profilu.

Nazwy użytkownika są kodowane także w atrybutach SVG, z uwzględnieniem
cudzysłowów. Pozostają tekstem, zamiast tworzyć dodatkowe atrybuty.
Karta profilu na małym ekranie układa się w jednej kolumnie, zapewniając
czytelną szerokość pól i rysunku.

Zmiana dotyczy geometrii i jej pochodzenia. Wybór nazwy lub wklejenie
rzędnych nie wyznacza biegunowej aerodynamicznej dla danego Re;
zakres charakterystyk Paturskiego opisano w raporcie P3.

## Weryfikacja

```powershell
python -m pytest -q
python tests/browser_airfoil_state.py
python tests/browser_airfoil.py --in-process
python tests/browser_design_integrity.py --in-process
```

13 nowych przypadków Python porównuje dane projektu, osobnego API
i raportu: profile NACA, rzędne z etykietą autora i bez niej, nagłówek,
brak nagłówka, normalizację nazwy, błędne dane i kodowanie SVG.

Nowy test Chrome obejmuje 17 scenariuszy, w tym trzy kontrolowane
opóźnienia odpowiedzi, przełączanie projektów, import starszego pliku,
utrzymanie źródła rzędnych, raport po nieprawidłowej edycji, odzyskanie
poprawnego profilu, widok 390 px, odświeżenie oraz pobranie i druk
aktualnego SVG. Otwiera też dwa raporty P3 offline i zapisuje PDF.
Artefakty: `work/profile-state-20261031/`.

Końcowy pełny przebieg: **1367 testów Python**, 297,09 s, bez błędów
i pominięć. Przeszło **36 testów JavaScript** oraz **31 scenariuszy
Chrome**: 17 nowych, dotychczasowy przebieg karty profilu i 13 pełnych
procesów projektowych, po jednym z każdej kategorii oficjalnych tematów.
Procesy kategorii obejmują kreator, moduły, edycję, zapis, odświeżenie,
HTML/PDF/DOCX/JSON/CSV oraz szerokości 320 i 390 px. Ich artefakty
pozostają w `work/design-integrity-20261030/`, zgodnie z istniejącym testem.

PDF raportu poprawnego ma 19 stron A4, w tym stronę poziomą z profilem;
raport błędnych rzędnych ma 17 stron A4 i nie zawiera rysunku profilu.
Osobny wydruk ma jedną poziomą stronę A4. W jego ścieżkach wektorowych
sprawdzono fizyczną długość cięciwy 200 mm i odcinka kontrolnego 100 mm,
z tolerancją 0,5 punktu PDF. Wszystkie strony zawierają tekst.

Po pełnym przebiegu dołączono również `114fd01`: niezależne zmiany
wydruku kolokwium i kartotek z `master`, bez zmian kodu obliczeniowego
Pythona. Zachowano oba zestawy aktualnych skryptów. Ponownie przeszły
17 nowych scenariuszy, test panelu kolokwium przy 1400/390 px i wszystkie
36 testów JavaScript.
