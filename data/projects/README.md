`course_seed.json` zawiera wyłącznie publiczny katalog 110 tematów i 10 przykładów
projektowych, wydzielony z dotychczasowej bazy. Nie zawiera projektów użytkownika.

Przy pierwszym uruchomieniu aplikacja tworzy z tego katalogu lokalną bazę
`projects.sqlite3`, pomijaną przez Git. Ten sam mechanizm działa w produkcji,
testach i kontroli `tools/check_databases.py`. Istniejąca baza jest zachowywana;
katalog początkowy nie zastępuje zmian użytkownika ani uszkodzonej bazy.

Przy odczycie tematów rozpoznane, **niezmienione** dawne wpisy katalogowe są
aktualizowane do bieżącego `course_seed.json`. `topic_history.json` zawiera dokładne
publiczne rekordy i identyfikatory commitów, z których pochodzą. Porównuje się cały
rekord, więc ręczna zmiana parametrów, tytułu, wymagań lub dodatkowych pól blokuje
automatyczne zastąpienie tego tematu. Zapisane projekty samolotów nie są zmieniane.
Aktualizacja jest atomowa i powtórny odczyt aktualnego katalogu nie zapisuje bazy.

Katalog nie ustala obszaru ważności korelacji dla dowolnej nowej konstrukcji.
Solver odrzuca pierwiastek bilansu powyżej dziesięciokrotności górnej masy
próby kalibracyjnej. To jawna granica poszukiwania numerycznego, a nie przepis
zdatności ani potwierdzenie wiarygodności ekstrapolacji w pozostałym zakresie.
