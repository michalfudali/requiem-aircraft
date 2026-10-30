/**
 * BiPOL Requiem — tryb dydaktyczny i konstrukcyjny.
 * 1. Uzupełnia PARAMETER_ENCYCLOPEDIA o brakujące parametry.
 * 2. Każdemu parametrowi dodaje objaśnienie „prosto mówiąc”.
 * 3. Dokleja ikonkę (i) i objaśnienie pod każdym polem formularza, kreatora,
 *    panelu BIPOL I i analizy trendów.
 * 4. Przełącza tryb: 🎓 dydaktyczny (objaśnienia widoczne) / 🛠️ konstrukcyjny (zwarty).
 */
(function () {
  if (typeof PARAMETER_ENCYCLOPEDIA === 'undefined') return;

  const E = (symbol, title, plain, more, typ, extra = {}) => ({
    symbol, title, short_desc: plain, plain, more, typical_ranges: typ,
    full_definition: extra.def || '', formula: extra.formula || '—',
    effect_increase: more, galinski_note: extra.note || '—'
  });

  // ---- Brakujące parametry ----
  Object.assign(PARAMETER_ENCYCLOPEDIA, {
    name: E('Nazwa', 'Nazwa projektu samolotu',
      'Własna nazwa projektowanego statku powietrznego lub oficjalne oznaczenie konstrukcyjne (np. PZL-102 Kos, SZD-56 Diana 3).',
      'Pojawia się na stronie tytułowej sprawozdania, rysunku technicznym A3Z i liście zapisanych projektów.',
      'Dowolny czytelny identyfikator, np. nazwa modelu lub akronim.'),
    topic: E('Temat', 'Oficjalny temat projektu BIPOL I',
      'Numer i pełna treść jednego ze 110 tematów wydziałowych ZSiS MEiL PW. Wybór tematu automatycznie ustawia parametry wyjściowe samolotu.',
      'Zmiana tematu przestawia sugerowane osiągi, konfigurację płata i zespół napędowy.',
      'Tematy 1–110 z wydziałowej listy BIPOL I.'),
    student_name: E('Autor', 'Imię i nazwisko studenta-konstruktora',
      'Dane autora projektu. Trafiają na stronę tytułową sprawozdania (Projekt 1–6) oraz do tabliczki rysunku technicznego.',
      'Uzupełnij, aby wygenerować kompletne sprawozdanie do oddania prowadzącemu.',
      'Jan Kowalski'),
    album_no: E('Nr albumu', 'Numer albumu (indeksu)',
      'Sześciocyfrowy numer indeksu na Politechnice Warszawskiej, identyfikujący projektanta.',
      'Drukowany w nagłówkach obliczeń i na okładce teczki projektu.',
      'Np. 123456'),
    group_no: E('Grupa', 'Numer grupy dziekańskiej lub projektowej',
      'Oznaczenie grupy ćwiczeniowej / projektowej na Wydziale MEiL PW.',
      'Ułatwia prowadzącemu identyfikację terminu zajęć i wpis oceny.',
      'Np. G1, D1, L2'),
    supervisor: E('Prowadzący', 'Imię i nazwisko prowadzącego projekt',
      'Tytuł i nazwisko nauczyciela akademickiego oceniającego projekt (np. dr inż. / prof. PW).',
      'Trafi do metryczki formalnej sprawozdań semestralnych P1–P6.',
      'Np. dr inż. Jan Nowak'),
    submission_date: E('Data', 'Data oddania projektu do oceny',
      'Data złożenia projektu lub wygenerowania sprawozdania semestralnego.',
      'Drukowana na stronie tytułowej i w nagłówkach wydruku.',
      'Format DD.MM.RRRR, np. 30.10.2026'),
    academic_year: E('Rok akad.', 'Rok akademicki realizacji',
      'Rok akademicki studiów, w którym realizowany jest przedmiot BIPOL I.',
      'Umieszczany w stopce wydziałowej strony tytułowej.',
      'Np. 2026/2027'),
    m_payload: E('m_płatna [kg]', 'Ładunek płatny łącznie',
      'Wszystko, za co ktoś „płaci” za przewiezienie: pasażerowie z bagażem plus towar. Załoga i paliwo się tu nie liczą.',
      'Każdy dodatkowy kilogram ładunku podnosi masę startową o 2–3 kg (bo trzeba większego skrzydła, silnika i więcej paliwa).',
      'Szkolny 2-os.: 90–200 kg | Turystyczny 4-os.: 300–450 kg | Dyspozycyjny: 600–1500 kg.',
      { formula: 'm_płatna = n_pax · m_os + m_cargo' }),
    wing_area_m2: E('S [m²]', 'Powierzchnia skrzydła',
      'Ile metrów kwadratowych ma skrzydło widziane z góry (razem z kawałkiem „schowanym” w kadłubie). To ono nosi samolot.',
      'Większe skrzydło = wolniejsze, bezpieczniejsze lądowanie i krótszy start, ale większy opór i masa w przelocie.',
      'ULM: 9–13 m² | Cessna 172: 16,2 m² | Szybowiec 15 m: 9–11 m² | ATR 42: 54,5 m².',
      { formula: 'S = m₀·g / (W/S)' }),
    wing_planform: E('Obrys', 'Kształt skrzydła w rzucie z góry',
      'Jak wygląda skrzydło z góry: prostokąt (najprostszy w budowie), trapez (lżejszy, lepszy aerodynamicznie) albo prostokąt przechodzący w trapez.',
      'Bardziej zbieżny obrys zmniejsza opór i masę, ale komplikuje produkcję (każde żebro inne).',
      'Szkolne/ULM: prostokątne | GA: prostokątno-trapezowe | Szybowce i odrzutowce: trapezowe.'),
    break_span_ratio: E('η_zał [-]', 'Miejsce załamania obrysu',
      'W skrzydle prostokątno-trapezowym: w którym miejscu rozpiętości (ułamek połowy rozpiętości) kończy się część prostokątna i zaczyna trapez.',
      'Większa wartość = dłuższa część prostokątna: prostsza produkcja, ale trochę większy opór indukowany.',
      'Typowo 0,35–0,60 (np. Piper PA-28 ≈ 0,5).'),
    gear_attachment: E('Podwozie', 'Mocowanie podwozia głównego',
      'Gdzie przykręcone są główne koła: do skrzydła czy do kadłuba. Zmienia rozstaw kół, masę goleni i rysunek trzech rzutów.',
      'Mocowanie do skrzydła daje szeroki, stabilny rozstaw kół; do kadłuba — krótsze, lżejsze golenie, ale węższy rozstaw.',
      'Dolnopłaty: zwykle skrzydło | Górnopłaty: zwykle kadłub lub owiewki przykadłubowe.'),
    gear_retraction: E('Chowanie', 'Podwozie stałe czy chowane',
      'Czy koła zostają cały czas na zewnątrz (stałe), czy chowają się w locie (chowane).',
      'Chowane podwozie zmniejsza opór (ok. 15–25 % oporu szkodliwego), ale dodaje 2–4 % masy i komplikację.',
      'Poniżej ~250 km/h: stałe | Powyżej ~250 km/h: chowane.'),
    takeoff_distance_m: E('S_TO,15 [m]', 'Całkowita droga startu do 15 m',
      'Odległość od ruszenia z miejsca do chwili, gdy samolot jest 15 m (50 ft) nad pasem. Obejmuje rozbieg i początek wznoszenia.',
      'Większa dopuszczalna droga = można dać słabszy silnik i mniejsze skrzydło.',
      'STOL: 150–300 m | GA: 400–700 m | Regionalne: 1000–1400 m | Odrzutowe: 1500–2500 m.'),
    landing_distance_m: E('S_LDG,15 [m]', 'Całkowita droga lądowania z 15 m',
      'Odległość od przelotu nad przeszkodą 15 m do całkowitego zatrzymania na pasie.',
      'Krótsza wymagana droga = trzeba niższej prędkości lądowania, czyli większego skrzydła lub lepszych klap.',
      'STOL: 150–300 m | GA: 400–650 m | Regionalne: 900–1200 m | Odrzutowe: 1200–2000 m.'),
    n_engines: E('n_s [-]', 'Liczba silników',
      'Ile silników ma samolot. Jeden — prościej i taniej; dwa — samolot może bezpiecznie lecieć dalej, gdy jeden zgaśnie.',
      'Więcej silników = większa niezawodność, ale wyższa masa, koszt i opór gondoli.',
      'Szkolne/turystyczne: 1 | Dyspozycyjne i regionalne: 2 | Ciężkie transportowe: 2–4.'),
    engine_power_kw: E('P [kW]', 'Moc silnika (zadana)',
      'Ile kilowatów daje silnik na wale. 1 kW ≈ 1,36 KM. Wpisz, jeśli temat narzuca konkretny silnik; inaczej program dobierze moc sam.',
      'Większa moc = krótszy start, lepsze wznoszenie i wyższa prędkość, ale cięższy silnik i większe zużycie paliwa.',
      'Rotax 912: 59–73 kW | Lycoming O-360: 134 kW | PT6A: 450–1100 kW.'),
    power_input_mode: E('Tryb mocy', 'Skąd bierze się moc silnika',
      '„Dobierana” — program sam liczy, ile mocy potrzeba do spełnienia wymagań. „Zadana” — Ty wpisujesz moc konkretnego silnika, a program sprawdza, czy wystarczy.',
      'Moc zadana jest wygodna, gdy temat lub katalog silników narzuca jednostkę napędową.',
      'Na początku projektu: dobierana | Po wyborze silnika z katalogu: zadana.'),
    wing_input_mode: E('Dane skrzydła', 'Które wymiary skrzydła podajesz sam',
      'Skrzydło opisują trzy powiązane liczby: rozpiętość b, powierzchnia S i wydłużenie Λ = b²/S. Wystarczy podać dwie — trzecią program wyliczy. W trybie „z obciążenia” podajesz tylko Λ, a S wynika z masy i prędkości lądowania.',
      'Wybierz tryb zgodny z tematem: jeśli temat narzuca rozpiętość (np. 15 m), podaj b i Λ.',
      'Brak ograniczeń: z obciążenia | Narzucona rozpiętość: b + Λ.'),
    payload_input_mode: E('Ładunek', 'Jak podajesz ładunek',
      '„Miejsca” — podajesz liczbę osób i masę jednej osoby. „Masa” — podajesz od razu łączną masę ładunku płatnego.',
      'Dla samolotów pasażerskich wygodniej podać miejsca, dla transportowych i rolniczych — masę.',
      'Pasażerskie: miejsca | Cargo, rolnicze, pożarnicze: masa.'),
    v_h: E('V_H [-]', 'Współczynnik objętości usterzenia poziomego',
      'Miara „siły” statecznika poziomego: jego powierzchnia razy odległość od skrzydła, podzielone przez powierzchnię i cięciwę skrzydła.',
      'Większy V_H = samolot stateczniejszy podłużnie, ale cięższy usterzeniem i z większym oporem.',
      'GA: 0,6–0,8 | Szybowce: 0,5–0,7 | Komunikacyjne: 0,9–1,1.'),
    v_v: E('V_V [-]', 'Współczynnik objętości usterzenia pionowego',
      'To samo co V_H, ale dla statecznika pionowego (kierunkowego). Mówi, jak mocno samolot „trzyma kierunek”.',
      'Większy V_V = lepsza stateczność kierunkowa, ważna przy awarii silnika w dwusilnikowcu.',
      'GA: 0,035–0,05 | Dwusilnikowe: 0,06–0,08 | Szybowce: 0,02–0,03.'),
    mass_method: E('Metoda masy', 'Jak liczony jest bilans masy (P2)',
      'Metoda proporcji mnoży ułamki masy kolejnych faz lotu (m_k/m_p) i od razu daje paliwo. Metoda iteracyjna liczy lot faza po fazie — jest potrzebna, gdy w locie zrzucany jest ładunek, bo wtedy ułamków faz nie można po prostu wymnożyć. „Automatycznie” wybiera iteracyjną tylko przy zrzucie.',
      'Bez zrzutu obie metody dają ten sam wynik; ze zrzutem poprawna jest tylko iteracyjna.',
      'Misja bez zrzutu: proporcji | Rolnicza, pożarnicza, desantowa: iteracyjna.'),
    empty_mass_model: E('Model m_e', 'Prawo masy pustej',
      'Wzór, który mówi, jaką część masy startowej stanowi pusty samolot (bez paliwa, ludzi i ładunku). Pochodzi z danych podobnych samolotów.',
      'Model z własnej bazy trendów jest najbardziej „Twój”; model z literatury — najszybszy.',
      'Typowo m_e/m₀ = 0,55–0,70 dla GA, 0,60–0,70 dla szybowców.'),
    mass_initial_guess: E('m₀,odn [kg]', 'Masa odniesienia do doboru próby',
      'Masa, wokół której program wybiera najbliższe samoloty z bazy do regresji masy pustej. Działa tylko w modelu „Regresja wybranych samolotów”.',
      'Inna masa odniesienia = inne samoloty w próbie, czyli inne A i C. Najlepiej, żeby była bliska wynikowej m₀.',
      'Masa startowa podobnego samolotu z bazy albo m₀ z poprzedniego bilansu.'),
    empty_mass_a: E('A [-]', 'Współczynnik A prawa masy pustej',
      'Mnożnik we wzorze m_e/m₀ = A·m₀^C. Ustala „poziom” krzywej: ile waży pusty samolot danej klasy.',
      'Większe A = cięższa konstrukcja, większa masa startowa.',
      'Raymer, lotnictwo ogólne: A ≈ 1,5–2,4.', { formula: 'm_e/m₀ = A · m₀^C' }),
    empty_mass_c: E('C [-]', 'Wykładnik C prawa masy pustej',
      'Wykładnik we wzorze m_e/m₀ = A·m₀^C. Mówi, jak udział masy pustej zmienia się, gdy samolot rośnie (zwykle lekko maleje — C ujemne).',
      'Bardziej ujemne C = duże samoloty są relatywnie lżejsze.',
      'Typowo C = −0,05 … −0,15.', { formula: 'm_e/m₀ = A · m₀^C' }),
    empty_mass_fraction: E('m_e/m₀ [-]', 'Stały udział masy pustej',
      'Jaką część masy startowej stanowi pusty samolot, jeśli przyjmujesz stałą wartość zamiast wzoru.',
      'Większy udział = mniej miejsca na paliwo i ładunek, więc masa startowa szybko rośnie.',
      'Kompozytowe ULM: 0,50–0,58 | GA metalowe: 0,58–0,66 | Szybowce: 0,60–0,70.'),
    return_range_km: E('R_powrót [km]', 'Zasięg drogi powrotnej',
      'Jeśli misja jest „tam i z powrotem” (np. zrzut ładunku), to długość odcinka powrotu.',
      'Dłuższy powrót = więcej paliwa i większa masa startowa.',
      'Misja zwykła: 0 | Rolnicza/pożarnicza: 20–100 km.'),
    payload_drop_kg: E('m_zrzut [kg]', 'Ładunek zrzucany w locie',
      'Ile kilogramów samolot zostawia po drodze (woda gaśnicza, środki ochrony roślin, zasobnik). Po zrzucie leci lżejszy.',
      'Większy zrzut = lżejszy lot powrotny, czyli mniej paliwa na powrót.',
      'Rolniczy: 500–2500 kg | Pożarniczy: 2000–6000 kg.'),
    loiter_speed_kmh: E('V_krąż [km/h]', 'Prędkość krążenia / oczekiwania',
      'Prędkość, z jaką samolot czeka w powietrzu (krąży nad lotniskiem albo patroluje). Zwykle bliska prędkości najmniejszego zużycia paliwa.',
      'Za szybkie krążenie spala więcej paliwa na godzinę.',
      'GA: 130–180 km/h | Regionalne: 250–350 km/h.'),
    max_power_time_min: E('t_Pmax [min]', 'Czas pracy na mocy maksymalnej',
      'Ile minut silnik pracuje na pełnej mocy (start i początek wznoszenia). Potrzebne do policzenia paliwa na start.',
      'Dłuższy czas = więcej paliwa na fazę startu.',
      'Typowo 1–5 min.'),
    max_power_kw: E('P_max [kW]', 'Moc maksymalna do bilansu paliwa',
      'Moc silnika w fazie startu, używana do policzenia, ile paliwa zużyje start.',
      'Większa moc startowa = więcej paliwa w tej fazie.',
      'Zgodnie z kartą katalogową silnika.'),
    max_thrust_kn: E('T_max [kN]', 'Ciąg maksymalny do bilansu paliwa',
      'Ciąg silnika odrzutowego w fazie startu, używany do policzenia paliwa na start.',
      'Większy ciąg = więcej paliwa w fazie startu.',
      'VLJ: 4–8 kN | Biznesowe: 15–40 kN | Regionalne: 60–120 kN.'),
    max_power_sfc: E('c_Pmax', 'Zużycie paliwa na mocy maksymalnej',
      'Ile paliwa spala silnik na jednostkę mocy (lub ciągu), gdy pracuje na pełnej mocy. Zwykle więcej niż w przelocie.',
      'Wyższe zużycie = cięższy bilans paliwa startu.',
      'Tłokowe: 270–320 g/(kW·h) | Odrzutowe: 0,6–0,9 1/h.'),
    climb_fraction_mode: E('Udział wznoszenia', 'Jak liczony jest ułamek masy na wznoszenie i rozpędzanie',
      'Ułamek masy na wznoszenie i rozpędzanie pochodzi z wykresu Corke’a: program odczytuje go z Macha i wysokości na początku i na końcu. Możesz też wpisać własne odczyty rzędnych.',
      '„Tylko wykres” zatrzyma obliczenie, gdy punkt leży poza krzywymi; tryb domyślny liczy wtedy oznaczone przybliżenie.',
      'Domyślnie: wykres z przybliżeniem | Do sprawozdania: własne odczyty rzędnych.',
      { formula: 'm_k/m_p = (W_m/W₀,₁) / (W_p/W₀,₁)' }),
    climb_start_altitude_m: E('H_0 [m]', 'Wysokość początku wznoszenia',
      'Wysokość lotniska, z którego samolot startuje (nad poziomem morza).',
      'Wyższa wysokość początkowa = mniej wysokości do nabrania, więc mniejszy ułamek paliwa na wznoszenie.',
      'Typowo 0–500 m.'),
    climb_start_speed_kmh: E('V_0 [km/h]', 'Prędkość początku wznoszenia',
      'Prędkość, od której liczymy wznoszenie na wykresie energii (zwykle prędkość tuż po starcie).',
      'Wyższa prędkość początkowa = mniej energii do zdobycia, więc mniej paliwa na wznoszenie i rozpędzanie.',
      'Ok. 1,2–1,3 × prędkość przeciągnięcia.'),
    corke_start_ordinate: E('Odczyt 1', 'Rzędna początkowa z wykresu Corke’a',
      'Wartość odczytana z wykresu dla stanu na początku wznoszenia.',
      'Wyższa rzędna początkowa = mniejszy iloraz rzędnych, czyli więcej paliwa na wznoszenie.',
      'Odczytaj z wykresu dla H_0 i V_0.'),
    corke_end_ordinate: E('Odczyt 2', 'Rzędna końcowa z wykresu Corke’a',
      'Wartość odczytana z wykresu dla stanu na wysokości przelotu.',
      'Wyższa rzędna końcowa = większy iloraz rzędnych, czyli mniej paliwa na wznoszenie.',
      'Odczytaj z wykresu dla H i V_cr.'),
    preliminary_polar_mode: E('Biegunowa wstępna', 'Skąd bierzemy wstępną biegunową',
      'Biegunowa to związek siły nośnej z oporem. Na początku projektu bierzemy C_x0 z założeń, odczytujemy K_max z wykresu Raymera (z wydłużenia i S_wet/S ze szkicu) albo wpisujemy własny odczyt K_max.',
      'Wykres Raymera wiąże biegunową z Twoim szkicem; C_x0 z założeń to tylko robocze oszacowanie.',
      'P1/P2: wykres Raymera ze szkicu | Później: biegunowa z P4.',
      { formula: 'C_x0 = π·Λ·e / (4·K_max²)' }),
    sketch_swet_ratio: E('S_wet/S [-]', 'Stosunek powierzchni omywanej do powierzchni skrzydła',
      'Ile razy cała zewnętrzna „skóra” samolotu (owiewana powietrzem) jest większa od powierzchni skrzydła. Odczytujesz to ze szkicu.',
      'Większy stosunek = więcej tarcia, większy opór szkodliwy, niższa doskonałość.',
      'Szybowce: 3,5–4,5 | GA: 4–5,5 | Komunikacyjne: 5,5–6,5.'),
    raymer_family: E('Rodzina', 'Rodzina samolotów wg Raymera',
      'Grupa samolotów, z której Raymer podaje typową doskonałość i opór. Wybierz najbardziej podobną do Twojej.',
      'Zła rodzina da zbyt optymistyczną lub pesymistyczną doskonałość.',
      'Np. GA jednosilnikowe, szybowce, odrzutowce biznesowe.'),
    raymer_kmax: E('K_max [-]', 'Doskonałość maksymalna z Raymera',
      'Ile metrów samolot przeleci do przodu, tracąc 1 m wysokości przy najlepszej prędkości — wg danych Raymera.',
      'Wyższa doskonałość = mniej paliwa na trasę, mniejsza masa startowa.',
      'GA: 10–14 | Szybowce: 35–60 | Komunikacyjne: 15–20.'),
    cx0_reference_class: E('Klasa C_x0', 'Klasa porównawcza oporu szkodliwego',
      'Grupa samolotów, z której bierzemy typową wartość oporu szkodliwego C_x0 (tabele A, B, C Paturskiego).',
      'Bardziej „czysta” klasa = niższy opór, wyższa prędkość, mniejsza moc.',
      'Chowane podwozie: 0,020–0,025 | Stałe: 0,027–0,036.'),
    trend_year_basis: E('Daty', 'Znaczenie dat w analizie trendów',
      'Którą datę samolotu bierzemy w trendach: rok certyfikacji wariantu (obecna baza) czy rok produkcji (jak w materiałach BIPOL_1).',
      'Zmiana przesuwa samoloty na osi czasu i może zmienić, które z nich mieszczą się w filtrze lat.',
      'Certyfikacja — obecna baza | Produkcja — według BIPOL_1.'),
    trend_source: E('Źródło', 'Skąd biorą się samoloty do trendu',
      'Zbiór samolotów porównawczych: wbudowana baza, własne dane lub oba naraz.',
      'Więcej podobnych samolotów = wiarygodniejszy trend.',
      'Minimum 6–10 samolotów podobnej klasy.'),
    trend_count: E('Liczba', 'Ile samolotów bierzemy do trendu',
      'Ilu najbardziej podobnych samolotów program użyje do wyliczenia linii trendu.',
      'Za mało — przypadkowy wynik; za dużo — wchodzą samoloty niepodobne.',
      'Typowo 8–20.'),
    trend_engine_count: E('Silniki', 'Filtr liczby silników',
      'Bierzemy do porównania tylko samoloty z taką samą liczbą silników jak Twój.',
      'Filtr zwiększa podobieństwo, ale zmniejsza liczbę samolotów.',
      '1 lub 2.'),
    trend_year_min: E('Od roku', 'Najstarszy rocznik w trendzie',
      'Samoloty starsze niż ten rok są pomijane.',
      'Wyższa wartość = trend opisuje tylko nowsze konstrukcje.',
      'Np. 1970–2000.'),
    trend_year_max: E('Do roku', 'Najnowszy rocznik w trendzie',
      'Samoloty nowsze niż ten rok są pomijane.',
      'Wyższy rok = do trendu wchodzą też najnowsze konstrukcje.',
      'Bieżący rok.'),
    trend_weighting: E('Wagi', 'Jak ważone są samoloty w trendzie',
      'Czy każdy samolot liczy się tak samo, czy bardziej podobne (lub nowsze) mają większy wpływ na linię trendu.',
      'Ważenie podobieństwem daje wynik bliższy Twojemu projektowi.',
      'Równe lub wg podobieństwa.'),
    trend_variable_sweep: E('Przegląd', 'Którą zależność badasz',
      'Para wielkości (np. masa pusta od masy startowej), dla której rysowany jest wykres i dopasowywana linia trendu.',
      'Zmień, aby zobaczyć inne zależności z bazy.',
      'm_e(m₀), S(m₀), P(m₀) itp.'),
    mission_phase_model: E('Fazy misji', 'Model profilu lotu',
      'Z jakich etapów składa się lot (start, wznoszenie, przelot, krążenie, lądowanie). Każdy etap „zjada” część paliwa.',
      'Więcej faz = dokładniejszy bilans paliwa.',
      'Standard BIPOL: 6–7 faz.'),
    fuel_reserve_factor: E('Rezerwa [-]', 'Zapas paliwa',
      'O ile więcej paliwa zabieramy niż potrzeba na samą trasę (na objście burzy, lotnisko zapasowe, błędy).',
      'Większa rezerwa = bezpieczniej, ale cięższy samolot.',
      'Typowo 1,05–1,10 (5–10 %) lub 45 min lotu.'),
    mission_ld_factor: E('K_misji/K_max', 'Doskonałość w misji względem maksymalnej',
      'W prawdziwym przelocie samolot rzadko leci z najlepszą doskonałością. Ten współczynnik mówi, jaką jej część faktycznie osiąga.',
      'Wyższy współczynnik = mniej paliwa w obliczeniach.',
      'Śmigłowe: 0,85–1,0 | Odrzutowe: 0,85–0,95.'),
    // ---- BIPOL 1: prawo masy z dwóch punktów i źródła ----
    mass_point_x1: E('x [kg]', 'Punkt linii trendu: masa startowa',
      'Masa startowa odczytana z wykresu m_e/m₀ = f(m₀) w miejscu, przez które przechodzi linia trendu. Dwa punkty (x₁, y₁) i (x₂, y₂) wyznaczają prostą na wykresie logarytmicznym.',
      'Punkty dalej od siebie = pewniejsze nachylenie C. Prawo obowiązuje tylko między x₁ a x₂.',
      'Punkty po obu stronach spodziewanej m₀, np. 600 i 1500 kg dla małego GA.',
      { formula: 'C = ln(y₁/y₂) / ln(x₁/x₂),   A = y₁ / x₁^C' }),
    mass_point_y1: E('y = m_e/m₀ [-]', 'Punkt linii trendu: udział masy pustej',
      'Jaką część masy startowej stanowi pusty samolot w punkcie odczytanym z linii trendu (np. 0,60 = 60 %).',
      'Wyższy udział = cięższa konstrukcja, mniej masy na paliwo i ładunek, więc m₀ rośnie.',
      'UL: 0,48–0,55 | GA: 0,58–0,68 | Turbośmigłowe: 0,55–0,62 | Odrzutowe komunikacyjne: 0,50–0,56.',
      { formula: 'm_e/m₀ = A · m₀^C' }),
    mass_law_source: E('Źródło', 'Źródło prawa masy pustej',
      'Skąd pochodzi zależność m_e/m₀ = A·m₀^C: dokument, strona, próba samolotów i co obejmuje masa pusta (np. z paliwem niezużywalnym, bez załogi).',
      'Prowadzący sprawdza na tej podstawie odczyt; bez źródła prawa masy nie da się obronić.',
      'Np. „Raymer, tab. 3.1, GA jednosilnikowe” albo „regresja 12 samolotów z bazy, certyfikacja 1990–2020”.'),
    graph_source: E('Źródło', 'Źródło odczytów z wykresów',
      'Z jakiego rysunku i krzywej odczytano S_wet/S i K_max oraz skąd wzięto powierzchnie ze szkicu.',
      'Pozwala odtworzyć odczyt i sprawdzić, czy krzywa pasuje do klasy samolotu.',
      'Np. „Raymer, krzywa: śmigłowe z podwoziem stałym; S_wet ze szkicu z 12.10”.'),
    sketch_reference: E('Szkic', 'Uzgodniony szkic odręczny',
      'Nazwa pliku lub arkusza ze szkicem samolotu, który prowadzący zaakceptował, i data uzgodnienia. Z tego szkicu pochodzi S_wet/S.',
      'Wiąże obliczenia z konkretną wersją szkicu — po zmianie szkicu trzeba powtórzyć odczyty.',
      'Np. „szkic_v2.pdf, uzgodniony 15.10.2026”.'),
    mission_approval_reference: E('Misja', 'Uzgodnienie misji z prowadzącym',
      'Kiedy i w jakim zakresie prowadzący zatwierdził profil misji i wymagania: zasięg, prędkości, ładunek, zrzut, krążenie.',
      'Misja jest podstawą bilansu paliwa; zmiana po uzgodnieniu wymaga nowej akceptacji.',
      'Np. „misja i wymagania zatwierdzone na konsultacjach 8.10.2026”.'),
    // ---- Edytor wspólnej bazy samolotów (pola ac_*) ----
    ac_model: E('Model', 'Oznaczenie wariantu w bazie',
      'Nazwa wariantu tak, jak w źródle (np. Cessna 172S, ATR 72-600). Każdy wariant to osobny rekord, bo masy i osiągi wersji się różnią.',
      'Podpisuje punkt na wykresach trendów i w wynikach wyszukiwania.',
      'Np. PZL-104 Wilga 35A, Diamond DA40 NG.'),
    ac_manufacturer: E('Producent', 'Producent lub posiadacz certyfikatu typu',
      'Firma, która zbudowała samolot albo posiada jego certyfikat typu.',
      'Ułatwia odróżnienie wariantów i znalezienie karty danych typu (TCDS).',
      'Np. PZL Warszawa-Okęcie, Diamond Aircraft.'),
    ac_family: E('Rodzina', 'Rodzina konstrukcji',
      'Wspólna nazwa wariantów jednego płatowca (np. „Cessna 172” dla wersji R i S).',
      'Przy ważeniu „wg rodzin” warianty jednej rodziny liczą się razem — rodzina z wieloma wersjami nie zdominuje trendu.',
      'Np. Cessna 172, PZL-104 Wilga.'),
    ac_year: E('Rok', 'Rok według źródła',
      'Rok certyfikacji wariantu albo rok produkcji — zależnie od pola „Znaczenie daty”.',
      'Decyduje, czy samolot zmieści się w filtrze lat i gdzie stanie na wykresie w czasie.',
      'Rok czterocyfrowy, np. 1996.'),
    ac_year_basis: E('Data', 'Znaczenie podanego roku',
      'Czy rok to data certyfikacji wariantu, czy rok produkcji (jak w materiałach BIPOL_1).',
      'Musi być zgodne ze źródłem; pomylenie dat przesuwa samolot na osi czasu nawet o kilkanaście lat.',
      'Certyfikacja — obecna baza | Produkcja — dane z BIPOL_1.'),
    ac_m0: E('m₀ [kg]', 'Maksymalna masa startowa samolotu z bazy',
      'Największa masa, z jaką samolot może wystartować — z karty danych typu (TCDS) albo instrukcji użytkowania w locie.',
      'To oś X większości trendów (m_e/m₀, W/S, P/W); błąd masy przesuwa punkt na wszystkich wykresach.',
      'Szkolne 2-os.: 600–1000 kg | Turystyczne 4-os.: 1100–1600 kg | Regionalne turbośmigłowe: 16–23 t.'),
    ac_me: E('m_e [kg]', 'Masa pusta samolotu z bazy',
      'Masa samolotu bez paliwa użytkowego, załogi i ładunku. Źródła definiują ją różnie (z olejem, z paliwem niezużywalnym, OEW z załogą) — opisz to w „Definicji masy pustej”.',
      'Wyznacza udział m_e/m₀ do prawa masy pustej w P2.',
      'm_e/m₀: UL 0,48–0,55 | GA 0,58–0,68 | Odrzutowe komunikacyjne 0,50–0,56.'),
    ac_p_kw: E('P [kW]', 'Łączna moc startowa silników',
      'Suma maksymalnej mocy startowej wszystkich silników na wale, według TCDS lub karty silnika. 1 kW ≈ 1,36 KM.',
      'Wyznacza obciążenie mocy m₀/P — oś trendu doboru napędu.',
      'Rotax 912 ULS: 73,5 kW | Cessna 172S: 134 kW | King Air 350: 2 × 783 kW.'),
    ac_t_kn: E('T [kN]', 'Łączny ciąg startowy silników',
      'Suma statycznego ciągu startowego wszystkich silników na poziomie morza (ISA).',
      'Wyznacza stosunek ciągu do ciężaru T/W — oś trendu doboru napędu odrzutowców.',
      'VLJ: 8–18 kN | Biznesowe średnie: 30–60 kN | A320: 2 × ok. 120 kN.'),
    ac_prop_diameter_m: E('D [m]', 'Średnica śmigła',
      'Średnica okręgu zakreślanego przez końcówki łopat.',
      'Większe śmigło daje więcej ciągu przy małej prędkości, ale wymaga wyższego podwozia i niższych obrotów (końcówki łopat muszą zostać wyraźnie poniżej prędkości dźwięku).',
      'Rotax 912: 1,6–1,75 m | Cessna 172: 1,9 m | PT6A (King Air): 2,3–2,7 m.'),
    ac_cruise_mach: E('Ma [-]', 'Liczba Macha przelotu',
      'Prędkość przelotowa podzielona przez prędkość dźwięku na wysokości przelotu. Dla odrzutowców źródła podają zwykle Ma, nie km/h.',
      'Wyższe Ma wymaga większego skosu i cieńszego profilu, żeby uniknąć oporu falowego.',
      'Turbośmigłowe: 0,4–0,55 | Biznesowe: 0,7–0,85 | Komunikacyjne: 0,78–0,85.'),
    ac_ld_max: E('K_max [-]', 'Doskonałość maksymalna samolotu z bazy',
      'Największy stosunek siły nośnej do oporu. Mówi, ile metrów samolot przeleci do przodu, tracąc 1 m wysokości.',
      'Służy do porównania z K_max Twojego projektu i do trendu doskonałości.',
      'GA: 9–13 | Odrzutowe komunikacyjne: 16–20 | Szybowce: 35–60.'),
    ac_takeoff_m: E('Start [m]', 'Długość startu podana w źródle',
      'Długość startu w metrach. Co dokładnie oznacza (rozbieg, droga do 15 m, długość pola), wybierasz w polu „Definicja długości startu”.',
      'Krótszy start oznacza zwykle mniejsze obciążenie powierzchni albo większy zapas mocy.',
      'Rozbieg GA: 200–400 m | Do 15 m GA: 400–700 m | Pole startowe odrzutowców: 1200–2500 m.'),
    ac_landing_m: E('Lądowanie [m]', 'Długość lądowania podana w źródle',
      'Długość lądowania w metrach. Co dokładnie oznacza (dobieg, droga znad 15 m, długość pola), wybierasz w polu „Definicja długości lądowania”.',
      'Krótsze lądowanie oznacza zwykle niższą prędkość podejścia, czyli większe skrzydło lub lepsze klapy.',
      'Dobieg GA: 150–300 m | Znad 15 m GA: 350–650 m | Pole do lądowania odrzutowców: 1000–2000 m.'),
    ac_takeoff_basis: E('Definicja', 'Co mierzy podana długość startu',
      'Czy liczba to sam rozbieg, droga do 15 m (50 ft), czy długość pola startowego według przepisów.',
      'Bez definicji liczb nie da się porównać — droga do 15 m bywa 1,6–2 razy dłuższa od rozbiegu.',
      'GA: zwykle do 15 m (50 ft) | Odrzutowe: długość pola startowego.'),
    ac_landing_basis: E('Definicja', 'Co mierzy podana długość lądowania',
      'Czy liczba to sam dobieg, droga znad 15 m (50 ft), czy długość pola do lądowania według przepisów.',
      'Droga znad 15 m bywa około 2 razy dłuższa od dobiegu; pomieszanie definicji psuje trend.',
      'GA: zwykle znad 15 m (50 ft) | Odrzutowe: długość pola do lądowania.'),
    ac_aileron_chord_ratio: E('c_a/c [-]', 'Względna cięciwa lotki',
      'Jaką część cięciwy skrzydła zajmuje lotka w miejscu zamocowania.',
      'Większa cięciwa = skuteczniejsza lotka, ale większe siły na drążku i mniej miejsca za dźwigarem tylnym.',
      'Typowo 0,20–0,30.'),
    ac_elevator_chord_ratio: E('c_SH/c_H [-]', 'Względna cięciwa steru wysokości',
      'Jaką część cięciwy usterzenia poziomego zajmuje ster wysokości.',
      'Większy ster = więcej momentu do wyrównania przy przednim środku masy, ale większe siły sterowe.',
      'Typowo 0,30–0,45 | Usterzenie płytowe (całe ruchome): 1,0.'),
    ac_rudder_chord_ratio: E('c_SV/c_V [-]', 'Względna cięciwa steru kierunku',
      'Jaką część cięciwy statecznika pionowego zajmuje ster kierunku.',
      'Większy ster = łatwiejsze opanowanie bocznego wiatru i niesymetrycznego ciągu, ale większe siły na pedałach.',
      'Typowo 0,25–0,45.'),
    ac_source_locator: E('Lokalizacja', 'Dokument, strona i miejsce danych',
      'Gdzie dokładnie są liczby: dokument, strona, tabela albo adres.',
      'Pozwala innym sprawdzić dane i obronić trend.',
      'Np. „TCDS EASA, sekcja Masses” albo „POH, rozdz. 5, tab. 5-2”.'),
    ac_source_references: E('Źródło', 'Źródło i warunki pomiaru',
      'Skąd są dane i w jakich warunkach je podano: masa, wysokość, atmosfera ISA, ustawienie mocy, rezerwa paliwa.',
      'Bez warunków osiągi z różnych źródeł nie są porównywalne.',
      'Np. „POH, rozdz. 5; zasięg przy 75 % mocy na 2400 m, rezerwa 45 min”.'),
    ac_empty_mass_definition: E('Definicja m_e', 'Co obejmuje podana masa pusta',
      'Czy masa pusta zawiera olej, paliwo niezużywalne, wyposażenie standardowe, a może to OEW razem z załogą.',
      'Różne definicje zmieniają m_e/m₀ o kilka punktów procentowych — opisz je, żeby trend był spójny.',
      'Np. „masa pusta wg TCDS: z paliwem niezużywalnym i pełnym olejem”.')
  });

  // ---- „Prosto mówiąc” dla parametrów już opisanych w encyklopedii ----
  const PLAIN = {
    aircraft_type: ['Jaki to rodzaj maszyny: tłokowy samolot sportowy, motoszybowiec, szybowiec, turbośmigłowiec, odrzutowiec albo dron. Od tego zależą wszystkie statystyki masy i domyślne wartości.', 'Zmiana klasy przestawia współczynniki statystyczne i domyślne osiągi.'],
    category: ['Według jakich przepisów samolot byłby dopuszczony do lotów. Przepisy mówią m.in., ile osób może zabrać i jakie przeciążenia musi wytrzymać.', 'Ostrzejsza kategoria (np. akrobacyjna) = mocniejsza i cięższa konstrukcja.'],
    wingspan_m: ['Odległość od końca lewego do końca prawego skrzydła. Wpisz 0, jeśli program ma ją policzyć sam.', 'Większa rozpiętość = mniejszy opór przy wolnym locie, ale większy moment gnący i cięższe skrzydło.'],
    wing_config: ['Na jakiej wysokości kadłuba jest skrzydło: na dole (dolnopłat), w środku (średniopłat), na górze (górnopłat), na górze z podporami (zastrzałowy).', 'Wpływa na podwozie, miejsce w kabinie, stateczność i opór.'],
    aspect_ratio: ['Jak „smukłe” jest skrzydło: długie i wąskie (duże Λ, jak w szybowcu) czy krótkie i szerokie (małe Λ, jak w akrobacji).', 'Większe Λ = mniejszy opór, lepsze szybowanie i zasięg, ale cięższe, bardziej wiotkie skrzydło.'],
    taper_ratio: ['Ile razy końcówka skrzydła jest węższa od nasady. 1 = prostokąt, 0,5 = końcówka o połowę węższa.', 'Mniejsza wartość = lżejsze skrzydło i mniejszy opór, ale poniżej 0,35 końcówki łatwo przeciągają.'],
    sweep_quarter_deg: ['O ile stopni skrzydło jest „odchylone do tyłu”, jak strzała. Potrzebne dopiero w szybkich odrzutowcach.', 'Większy skos pozwala latać szybciej (blisko prędkości dźwięku), ale pogarsza zachowanie przy małej prędkości.'],
    dihedral_deg: ['Kąt, pod jakim skrzydła są uniesione ku górze (litera V widziana z przodu). Dzięki temu samolot sam wraca do poziomu po przechyleniu.', 'Większy wznios = spokojniejszy, stateczniejszy samolot, ale mniej zwrotny.'],
    range_km: ['Jak daleko samolot ma dolecieć bez tankowania z pełnym ładunkiem.', 'Większy zasięg = więcej paliwa, większy i cięższy samolot.'],
    cruise_altitude_m: ['Na jakiej wysokości samolot leci w przelocie. Wyżej powietrze jest rzadsze.', 'Wyżej = mniejszy opór i szybszy lot, ale silnik tłokowy traci moc, a powyżej ~3 km ludzie potrzebują tlenu.'],
    n_pax: ['Ilu pasażerów zabiera samolot — bez pilotów.', 'Każdy pasażer to ok. 100 kg i miejsce w kabinie, więc samolot rośnie.'],
    m_cargo: ['Masa towaru wożonego oprócz pasażerów (bagaż dodatkowy, ładunek, chemikalia, sprzęt drona).', '100 kg ładunku więcej to zwykle 220–300 kg więcej masy startowej.'],
    n_crew: ['Ilu pilotów i członków załogi musi lecieć. Dron ma 0.', 'Więcej załogi = mniej miejsca i masy dla ładunku.'],
    m_pax: ['Ile liczymy na jedną osobę razem z bagażem.', 'Większa masa osoby = większa masa startowa.'],
    cruise_speed_kmh: ['Z jaką prędkością samolot leci na trasie.', 'Opór rośnie z kwadratem prędkości, a potrzebna moc — z sześcianem: +20 % prędkości to ok. +70 % mocy.'],
    v_stall_kmh: ['Najmniejsza prędkość, przy której samolot z wypuszczonymi klapami jeszcze leci. Poniżej skrzydło traci siłę nośną.', 'Wyższa dopuszczalna = mniejsze skrzydło, ale szybsze i dłuższe lądowanie.'],
    takeoff_run_m: ['Ile metrów pasa samolot przejedzie po ziemi, zanim oderwie koła.', 'Krótszy rozbieg wymaga mocniejszego silnika lub większego skrzydła.'],
    climb_rate_ms: ['Ile metrów na sekundę samolot wznosi się w pionie zaraz po starcie.', 'Szybsze wznoszenie wymaga większego zapasu mocy.'],
    engine_type: ['Czym samolot jest napędzany: śmigłem (silnik tłokowy, elektryczny, turbośmigłowy), silnikiem odrzutowym albo wcale (szybowiec).', 'Śmigło jest oszczędniejsze przy małych prędkościach, odrzut — przy dużych.'],
    engine_location: ['Gdzie jest silnik: w nosie, na skrzydłach, z tyłu kadłuba, czy chowany (motoszybowiec).', 'Silnik jest ciężki, więc jego położenie przesuwa środek ciężkości i miejsce skrzydła.'],
    sfc: ['Ile paliwa silnik spala na godzinę na każdy kilowat mocy (lub na każdy niuton ciągu).', 'Większe zużycie = więcej paliwa na trasę, cięższy samolot.'],
    prop_efficiency: ['Jaka część mocy silnika zamienia się na ciąg śmigła. Reszta „ucieka” w wir i ciepło.', 'Wyższa sprawność = lepsze osiągi przy tej samej mocy.'],
    flap_type: ['Jakie klapy są na tylnej krawędzi skrzydła. Wysuwane przy lądowaniu zwiększają siłę nośną, więc można lądować wolniej.', 'Lepsza klapa (szczelinowa, Fowlera) = mniejsze skrzydło przy tej samej prędkości lądowania, ale cięższy mechanizm.'],
    aileron_type: ['Jakie lotki są na końcach skrzydła. Lotki przechylają samolot na boki (jedna w górę, druga w dół).', 'Lotki różnicowe lub Frise zmniejszają niechciane „zarzucanie” nosem w zakręcie.'],
    slat_type: ['Czy na przedniej krawędzi skrzydła jest slot (szczelina), który pozwala lecieć na większym kącie bez przeciągnięcia.', 'Slot obniża prędkość przeciągnięcia, ale dodaje opór lub mechanizm.'],
    flap_span_ratio: ['Jaką część rozpiętości skrzydła zajmują klapy (reszta zostaje na lotki).', 'Dłuższe klapy = wolniejsze lądowanie, ale krótsze lotki i słabsze sterowanie przechyleniem.'],
    aileron_span_ratio: ['Jaką część rozpiętości skrzydła zajmują lotki.', 'Dłuższe lotki = szybsze przechylanie, ale mniej miejsca na klapy.'],
    cx0: ['Opór samolotu, który istnieje zawsze — nawet gdy skrzydło nie wytwarza siły nośnej (tarcie skóry, kształt kadłuba, podwozie, anteny).', 'Większy opór szkodliwy = niższa prędkość maksymalna i większe zużycie paliwa.'],
    oswald_e: ['Jak blisko ideału (e = 1) jest rozkład siły nośnej na skrzydle. Kadłub, gondole i kształt skrzydła go psują.', 'Wyższe e = mniejszy opór przy wolnym locie, wznoszeniu i zakrętach.'],
    cz_max_clean: ['Największa siła nośna, jaką da skrzydło bez wysuniętych klap, tuż przed przeciągnięciem.', 'Wyższa wartość = niższa prędkość przeciągnięcia bez klap.'],
    cz_max_lnd: ['Największa siła nośna skrzydła z wysuniętymi klapami do lądowania.', 'Wyższa wartość = można zrobić mniejsze skrzydło przy tej samej prędkości lądowania.']
  };
  for (const [k, [plain, more]] of Object.entries(PLAIN)) {
    const e = PARAMETER_ENCYCLOPEDIA[k];
    if (e) { e.plain = plain; e.more = more; }
  }

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // Pola o innym identyfikatorze niż klucz encyklopedii (kreator, metryczka, edytor bazy).
  const ALIAS = {
    ac_s: 'wing_area_m2', ac_b: 'wingspan_m', ac_v_cruise_kmh: 'cruise_speed_kmh',
    ac_aileron_span_fraction: 'aileron_span_ratio', mass_point_x2: 'mass_point_x1', mass_point_y2: 'mass_point_y1'
  };
  const keyFor = id => {
    id = String(id || '');
    if (ALIAS[id] || PARAMETER_ENCYCLOPEDIA[id]) return ALIAS[id] || id;
    return id.replace(/^(wiz_basis_|wiz_|ws_|studioMeta_|ac_)/, '');
  };

  // Ta sama treść trafia pod pole i do kartoteki; etykieta skutku zależy od rodzaju pola.
  const GROUP = '.input-group, .form-group, .wizard-field, .assumption-input-card';
  const EFFECT_LABEL = { number: 'Gdy zwiększysz', choice: 'Gdy zmienisz', text: 'Do czego służy', result: 'Wpływ na projekt' };
  // Pola rekordu bazy opisują istniejący samolot, nie decyzję projektową — skutek „zwiększenia” nie ma sensu.
  const kindOf = field => !field ? 'result' : field.closest('#aircraftEditorFields') ? 'text'
    : field.tagName === 'SELECT' ? 'choice' : ['number', 'range'].includes(field.type) ? 'number' : 'text';
  const plainOf = info => info.plain || info.short_desc || '';
  const effectOf = info => info.more || info.effect_increase || '';
  const blank = s => !s || /^[—–-]$/.test(String(s).trim());

  const hintHtml = (info, kind = 'number') => `<strong>Prosto mówiąc:</strong> ${esc(plainOf(info))}`
    + (effectOf(info) ? `<span class="hint-more"><strong>${EFFECT_LABEL[kind]}:</strong> ${esc(effectOf(info))}</span>` : '')
    + (info.typical_ranges ? `<span class="hint-range">📏 Typowo: ${esc(info.typical_ranges)}</span>` : '');

  function fieldFor(anchor) {
    if (!anchor) return null;
    const label = anchor.closest('label');
    const target = label && label.htmlFor ? document.getElementById(label.htmlFor) : null;
    if (target) return target;
    const scope = anchor.closest(GROUP) || label;
    return scope ? scope.querySelector('input:not([type=checkbox]):not([type=hidden]):not([type=radio]), select, textarea') : null;
  }

  function currentValue(field, info) {
    if (!field) return '';
    if (field.tagName === 'SELECT') return field.selectedOptions[0]?.textContent.trim() || '';
    const value = String(field.value ?? '').trim();
    if (!value || field.type !== 'number') return value.length > 90 ? `${value.slice(0, 87)}…` : value;
    const unit = (String(info.symbol).match(/\[([^\]]+)\]/) || [])[1];
    return value.replace('.', ',') + (!unit || unit === '-' ? '' : unit === '°' ? unit : ` ${unit}`);
  }

  const STATE = { derived: 'wyliczona przez program', locked: 'zablokowane założenie', input: 'wpisana przez Ciebie' };
  function stateOf(key, field) {
    const results = typeof currentResults !== 'undefined' ? currentResults : null;
    const state = field && field.id === key && results?.constraints?.parameter_states?.[key];
    if (!state || !STATE[state.state]) return '';
    return STATE[state.state] + (state.state === 'derived' && state.formula ? ` ze wzoru ${state.formula}` : '');
  }

  function cardHtml(key, anchor) {
    const info = PARAMETER_ENCYCLOPEDIA[key];
    if (!info) return '';
    const field = fieldFor(anchor);
    const effect = effectOf(info);
    const section = (cls, label, text) => text
      ? `<div class="didactic-popover-section ${cls}"><strong>${label}</strong> ${esc(text)}</div>` : '';
    const shown = anchor?.closest('.kpi-card')?.querySelector('.kpi-value')?.textContent.trim() || '';
    const value = currentValue(field, info) || (/\d/.test(shown) ? shown : ''), state = stateOf(key, field);
    const where = anchor?.closest('#aircraftEditorFields') ? 'W rekordzie bazy' : 'W Twoim projekcie';
    const tech = (info.full_definition ? `<p class="didactic-popover-desc">${esc(info.full_definition)}</p>` : '')
      + (blank(info.formula) ? '' : `<div class="didactic-popover-formula">Wzór: ${esc(info.formula)}</div>`)
      + (info.effect_increase && info.effect_increase !== effect ? section('green', '📈 W obliczeniach:', info.effect_increase) : '')
      + (blank(info.galinski_note) ? '' : section('amber', /Rozdz/.test(info.galinski_note)
        ? '💡 Wskazówka konstrukcyjna (rozdziały wg kompendium prof. C. Galińskiego):' : '💡 Wskazówka konstrukcyjna:', info.galinski_note));
    return section('plain', 'Prosto mówiąc:', plainOf(info))
      + section('green', `${EFFECT_LABEL[kindOf(field)]}:`, effect)
      + section('blue', '📏 Typowo:', info.typical_ranges)
      + (value || state ? `<div class="didactic-popover-now"><strong>${where}:</strong> ${esc(value || 'puste')}${state ? ` · ${esc(state)}` : ''}</div>` : '')
      + (tech ? `<div class="didactic-popover-tech"><div class="didactic-popover-tech-title">Dla konstruktora</div>${tech}</div>` : '');
  }
  window.BipolDidactic = { hintHtml, cardHtml, keyFor };

  // Etykieta obejmująca pole: tekst sprzed kontrolki trafia do .label-text, żeby ikonka stała przy nazwie.
  function labelText(label, field) {
    const existing = label.querySelector('.label-text');
    if (existing || !label.contains(field)) return existing || label;
    let control = field;
    while (control.parentElement !== label) control = control.parentElement;
    const text = document.createElement('span');
    text.className = 'label-text';
    while (label.firstChild && label.firstChild !== control) text.appendChild(label.firstChild);
    label.insertBefore(text, control);
    return text;
  }

  const SCOPES = '#designForm, #projectWizardBackdrop, #bipol1Panel, #trendControls, #tab-trends, #aircraftEditorFields, #semesterWorkstation, #tab-reports';

  function decorate() {
    // Ikonki z szablonów: rola przycisku i nazwa dla czytnika; natywny dymek title zasłaniałby kartotekę.
    document.querySelectorAll('.info-circle-icon[data-param]:not([role])').forEach(icon => {
      const info = PARAMETER_ENCYCLOPEDIA[icon.dataset.param];
      icon.setAttribute('role', 'button');
      icon.setAttribute('aria-label', `Objaśnienie: ${info?.title || icon.title || icon.dataset.param}`);
      icon.removeAttribute('title');
      if (!icon.hasAttribute('tabindex')) icon.tabIndex = 0;
    });
    document.querySelectorAll(SCOPES).forEach(scope => {
      scope.querySelectorAll('input[id], select[id], textarea[id]').forEach(field => {
        if (field.type === 'hidden' || field.type === 'checkbox' || field.type === 'file') return;
        const key = keyFor(field.id);
        const info = PARAMETER_ENCYCLOPEDIA[key];
        if (!info) return;
        const group = field.closest(GROUP) || field.closest('label') || field.parentElement;
        if (!group) return;
        // Ikonka (i); wraca także wtedy, gdy skrypt przepisał tekst etykiety.
        let label = document.querySelector(`label[for="${CSS.escape(field.id)}"]`) || group.querySelector('label') || (group.tagName === 'LABEL' ? group : null);
        if (label && !label.querySelector('.info-circle-icon')) {
          const icon = document.createElement('span');
          icon.className = 'info-circle-icon';
          icon.dataset.param = key;
          icon.dataset.dyn = '1';
          icon.tabIndex = 0;
          icon.setAttribute('role', 'button');
          icon.setAttribute('aria-label', `Objaśnienie: ${info.title}`);
          icon.textContent = 'i';
          labelText(label, field).appendChild(icon);
        }
        // Objaśnienie pod polem; zapisywane raz, żeby obserwator zmian nie wpadł w pętlę.
        let hint = group.querySelector('.param-didactic-hint');
        if (!hint) {
          hint = document.createElement('div');
          hint.className = 'param-didactic-hint';
          const anchor = field.parentElement && field.parentElement !== group && (field.parentElement.closest(GROUP) || field.parentElement.closest('label')) === group ? field.parentElement : field;
          anchor.insertAdjacentElement('afterend', hint);
        }
        if (hint.dataset.hintFor !== key) {
          hint.dataset.hintFor = key;
          hint.innerHTML = hintHtml(info, kindOf(field));
        }
      });
    });
  }

  // Delegacja zdarzeń dla dynamicznie dodanych ikonek
  const show = icon => window.showDidacticPopover?.(icon.dataset.param, icon);
  const hide = () => { if (typeof scheduleHideDidacticPopover === 'function') scheduleHideDidacticPopover(); };
  const cardOpen = () => document.getElementById('didacticPopover')?.classList.contains('visible');
  const close = () => { if (typeof hideDidacticPopover === 'function') hideDidacticPopover(); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && cardOpen()) close(); });
  // Na ekranie dotykowym nie ma „zjechania” kursorem: zamyka przycisk × albo dotknięcie poza kartą.
  document.addEventListener('pointerdown', e => {
    if (cardOpen() && !e.target.closest?.('#didacticPopover, .info-circle-icon')) close();
  }, true);
  document.addEventListener('click', e => { if (e.target.closest?.('.didactic-popover-close')) close(); });
  document.addEventListener('mouseover', e => { const i = e.target.closest?.('.info-circle-icon[data-dyn]'); if (i) show(i); });
  document.addEventListener('mouseout', e => { if (e.target.closest?.('.info-circle-icon[data-dyn]')) hide(); });
  document.addEventListener('focusin', e => { const i = e.target.closest?.('.info-circle-icon[data-dyn]'); if (i) show(i); });
  document.addEventListener('focusout', e => { if (e.target.closest?.('.info-circle-icon[data-dyn]')) hide(); });
  document.addEventListener('click', e => {
    const i = e.target.closest?.('.info-circle-icon[data-dyn]');
    if (i) { e.preventDefault(); e.stopPropagation(); show(i); }
  }, true);
  document.addEventListener('keydown', e => {
    const i = e.target.closest?.('.info-circle-icon[data-dyn]');
    if (i && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); show(i); }
  });

  // ---- Tryby pracy ----
  const MODE_KEY = 'bipol_work_mode';
  function setAppWorkMode(mode) {
    mode = mode === 'construction' ? 'construction' : 'didactic';
    document.body.classList.toggle('mode-didactic', mode === 'didactic');
    document.body.classList.toggle('mode-construction', mode === 'construction');
    document.querySelectorAll('[data-work-mode]').forEach(b => {
      const on = b.dataset.workMode === mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', String(on));
    });
    if (mode === 'construction' && typeof setSidebarMode === 'function') setSidebarMode('advanced');
    try { localStorage.setItem(MODE_KEY, mode); } catch (_) {}
  }
  window.setAppWorkMode = setAppWorkMode;

  function injectSwitch() {
    const bar = document.querySelector('.project-bar-right');
    if (!bar || bar.querySelector('.work-mode-switch')) return;
    const box = document.createElement('div');
    box.className = 'work-mode-switch';
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', 'Tryb pracy');
    box.innerHTML = '<button type="button" data-work-mode="didactic" title="Pod każdym polem widać proste objaśnienie: co to jest, co się stanie, gdy zmienisz wartość, i jakie wartości są typowe.">🎓 Tryb dydaktyczny</button>'
      + '<button type="button" data-work-mode="construction" title="Zwarty widok bez objaśnień pod polami i ze wszystkimi parametrami. Objaśnienia nadal są pod ikonką (i).">🛠️ Tryb konstrukcyjny</button>';
    box.addEventListener('click', e => { const b = e.target.closest('[data-work-mode]'); if (b) setAppWorkMode(b.dataset.workMode); });
    bar.insertBefore(box, bar.firstChild);
  }

  document.addEventListener('DOMContentLoaded', () => {
    injectSwitch();
    decorate();
    let saved = null;
    try { saved = localStorage.getItem(MODE_KEY); } catch (_) {}
    setAppWorkMode(saved || 'didactic');
    // Pola dodawane później (kreator, panele ładowane dynamicznie)
    let pending = null;
    new MutationObserver(() => { clearTimeout(pending); pending = setTimeout(decorate, 120); })
      .observe(document.body, { childList: true, subtree: true });
  });
})();
