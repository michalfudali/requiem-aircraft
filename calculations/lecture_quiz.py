"""Pytania powtórkowe do zejściówek BIPOL I (regulamin: 1–3 pytania z wykładu, 15 minut).

Pytania i odpowiedzi wzorcowe są własnym opracowaniem na podstawie wykładów
okBIPOL_1_handout_*.pdf ze strony przedmiotu; `slide` wskazuje stronę materiału,
na której jest omawiane zagadnienie. Odpowiedź wzorcowa podaje to, co trzeba umieć
powiedzieć lub napisać, a nie pełną treść wykładu.
"""

LECTURES = (
    ('w01', 1, 'Wprowadzenie', 'okBIPOL_1_handout_1.pdf'),
    ('w02', 2, 'Oszacowanie podstawowych parametrów samolotu', 'okBIPOL_1_handout_2.pdf'),
    ('w03', 3, 'Kadłuby', 'okBIPOL_1_handout_3.pdf'),
    ('w04', 4, 'Podwozia', 'okBIPOL_1_handout_4.pdf'),
    ('w05', 5, 'Integracja zespołów napędowych', 'okBIPOL_1_handout_5.pdf'),
    ('w06', 6, 'Usterzenia', 'okBIPOL_1_handout_6.pdf'),
    ('w07', 7, 'Przykład projektu: samolot szkolny', 'okBIPOL_1_handout_7.pdf'),
    ('w08', 8, 'Płaty', 'okBIPOL_1_handout_8.pdf'),
    ('w09', 9, 'Mechanizacja płata i sterownice', 'okBIPOL_1_handout_9.pdf'),
    ('w10', 10, 'Stateczność statyczna i dynamiczna', 'okBIPOL_1_handout_10.pdf'),
    ('w11', 11, 'Kryteria oceny własności lotnych', 'okBIPOL_1_handout_11_1.pdf, okBIPOL_1_handout_11_2.pdf'),
    ('w12', 12, 'Obciążenia i obwiednia obciążeń', 'okBIPOL_1_handout_12.pdf'),
    ('w13', 13, 'Obciążenia usterzenia', 'okBIPOL_1_handout_13.pdf'),
    ('w14', 14, 'Obciążenia kadłuba', 'okBIPOL_1_handout_14.pdf'),
    ('w15', 15, 'Obciążenia podwozia', 'okBIPOL_1_handout_15.pdf'),
)

# (wykład, strona materiału, pytanie, odpowiedź wzorcowa[, plik, gdy wykład ma kilka])
_Q = (
    # -- 1. Wprowadzenie --------------------------------------------------------------------------------
    ('w01', 1, 'Co faktycznie kupuje klient, kupując samolot, i jaki wniosek wynika z tego dla projektanta?',
     'Klient kupuje możliwość wykonania określonej misji. Z misji wynikają wymagania, więc samolot musi spełniać '
     'wymagania misji zaplanowanej przez klienta. Nawet bardzo dobry samolot, niedopasowany do misji, nie spełni oczekiwań klienta.'),
    ('w01', 2, 'Wymień typowe wymagania stawiane projektowanemu samolotowi i źródła, z których pochodzą.',
     'Typowe wymagania: ładunek płatny, prędkości, pułap, zasięg, długotrwałość, start, lądowanie, koszt zakupu i przepisy '
     '(europejskie CS, dawniej JAR; amerykańskie FAR). Źródła: warunki techniczne, zawody, konkursy i rekordy, '
     'wyniki analiz ekonomicznych, projekty badawcze.'),
    ('w01', 3, 'Których przepisów CS używa się dla szybowców, samolotów lekkich, dużych samolotów i bardzo lekkich samolotów?',
     'CS-22 — szybowce i motoszybowce; CS-23 — samoloty normalne, użytkowe, akrobacyjne i dyspozycyjne (commuter); '
     'CS-25 — duże samoloty (odpowiednik FAR 25, samoloty transportowe); CS-VLA — bardzo lekkie samoloty. '
     'CS-21 opisuje procedury certyfikacji, a CS-27 i CS-29 — śmigłowce.'),
    ('w01', 3, 'Wymień etapy powstawania samolotu. Jak w kolejnych etapach zmieniają się elastyczność projektu i koszt?',
     'Badania rynku i koncepcja, wymagania, projekt koncepcyjny, projekt wstępny, konstrukcja, budowa prototypu, próby, '
     'produkcja. Na początku łatwo zmienić projekt, a zmiany kosztują mało; z każdym etapem elastyczność maleje, '
     'a koszt rośnie. Dlatego decyzje z wczesnych etapów są najważniejsze.'),
    ('w01', 4, 'Kiedy kończy się projektowanie samolotu?',
     'Według prof. Sołtyka — gdy ostatni egzemplarz zejdzie z linii produkcyjnej. Obecnie przyjmuje się, '
     'że dopiero wtedy, gdy ostatni egzemplarz zostanie złomowany, bo przez cały okres eksploatacji konstrukcję się '
     'nadzoruje i modyfikuje.'),
    ('w01', 6, 'Jakie wielkości wyznacza się w analizie trendów oprócz zależności masy pustej od masy startowej?',
     'Cechy objętościowe usterzenia poziomego i pionowego, część rozpiętości zajętą przez lotki, względne cięciwy lotek, '
     'steru wysokości i steru kierunku oraz kąt wzniosu. Dane zbiera się dla podobnych samolotów, np. z Jane\'s All the World\'s Aircraft.'),
    ('w01', 7, 'Wymień składniki ceny samolotu w metodzie RAND (Corke). Jak liczy się koszt rozwoju konstrukcji?',
     'Rozwój konstrukcji, wsparcie rozwoju, materiały, silniki i awionika, robocizna, narzędzia, zapewnienie jakości, '
     'próby w locie i zysk. Koszt rozwoju to liczba roboczogodzin razy stawka godzinowa (C_E = H_E·S_E); '
     'wartości z różnych lat trzeba przeliczyć z uwzględnieniem inflacji.'),
    # -- 2. Oszacowanie parametrów -----------------------------------------------------------------------
    ('w02', 2, 'Z jakich składników składa się ciężar startowy samolotu?',
     'W_TO = W_c + W_f + W_p + W_e: załoga, paliwo, ładunek płatny i samolot pusty. Ładunek płatny dzieli się na zrzucany '
     'w locie (W_exp) i niezrzucany (W_nexp).'),
    ('w02', 2, 'Opisz iteracyjną metodę wyznaczania masy startowej.',
     'Zakłada się masę startową i liczy kolejno masę po starcie, wznoszeniu, dolocie, wykonaniu zadania (z ewentualnym zrzutem '
     'ładunku), powrocie, oczekiwaniu i lądowaniu — masa na początku fazy równa się masie na końcu poprzedniej. '
     'Masa pustego = masa po lądowaniu minus ładunek, rezerwa paliwa i paliwo niezużywalne. Porównuje się ją z realistyczną '
     'masą pustą (np. z trendu) i poprawia masę startową aż do zgodności.'),
    ('w02', 2, 'Co obejmuje faza „startu” w bilansie paliwa i jaki ułamek masy się dla niej przyjmuje?',
     'Uruchomienie i próbę silnika, kołowanie, rozbieg i wznoszenie do przepisowej wysokości. Stosunek masy po starcie do masy '
     'startowej przyjmuje się 0,970–0,975; tyle samo dla lądowania.'),
    ('w02', 3, 'Napisz wzory Bregueta na zasięg samolotu śmigłowego i odrzutowego.',
     'Śmigłowy: R = η/(C·g)·(C_z/C_x)·ln(W_n/W_n+1). Odrzutowy: R = V/(C·g)·(C_z/C_x)·ln(W_n/W_n+1). '
     'C — jednostkowe zużycie paliwa (na jednostkę mocy dla śmigłowego, na jednostkę ciągu dla odrzutowego), η — sprawność śmigła.'),
    ('w02', 10, 'Przy jakim C_z samolot śmigłowy osiąga największy zasięg, a przy jakim odrzutowy?',
     'Śmigłowy — przy największej doskonałości: C_z = √(π·A·e·C_x0), czyli W/S = q·√(C_x0·π·A·e). '
     'Odrzutowy — przy największym iloczynie V·C_z/C_x, czyli przy maksimum √C_z/C_x: C_z = √(π·A·e·C_x0/3).'),
    ('w02', 4, 'Jak według Raymera przyjmuje się sprawność śmigła i doskonałość w przelocie przy szacowaniu paliwa?',
     'Sprawność śmigła η ≈ 0,8, a doskonałość w przelocie C_z/C_x ≈ 0,94·(C_z/C_x)max. Doskonałość maksymalną szacuje się '
     'z wydłużenia zwilżonego A·S_ref/S_wet.'),
    ('w02', 5, 'Jak liczy się zużycie paliwa w fazie lotu z maksymalnym ciągiem (np. przechwycenie)?',
     'Masa maleje o iloczyn jednostkowego zużycia paliwa, ciągu maksymalnego i czasu: W_n+1 = W_n − C·T_max·t, '
     'więc W_n+1/W_n = 1 − C·T_max·t/W_n.'),
    ('w02', 7, 'Jak z ułamków masowych faz lotu wyznacza się masę paliwa? Skąd współczynnik 1,06?',
     'Stosunek masy przy lądowaniu do startowej to iloczyn ułamków masowych wszystkich faz: W_L/W_TO = Π(W_n+1/W_n). '
     'Paliwo: W_F/W_TO = 1,06·(1 − W_L/W_TO). Współczynnik 1,06 dodaje 6% na rezerwę i paliwo niezużywalne.'),
    ('w02', 8, 'Jak według wykładu szacuje się długość startu i lądowania i jakie ograniczenie obciążenia powierzchni z tego wynika?',
     'Start zależy od parametru TOP = (W/S)/(σ·C_z,max,TO·(T/W)): s_TO = 20,9·TOP + 87·√(TOP·(T/W)) [ft]. '
     'Lądowanie: s_L = 118·(W/S)/(σ·C_z,max) + 400 [ft]. Z wymaganej długości lądowania wynika największe dopuszczalne W/S, '
     'a ze startu — wymagany stosunek T/W przy danym W/S.'),
    ('w02', 9, 'Jaki warunek na stosunek ciągu do ciężaru wynika z wymaganego gradientu wznoszenia?',
     'T/W = G + q·C_x0/(W/S) + (W/S)/(q·π·A·e), gdzie G = sin γ = w/V to gradient wznoszenia. '
     'Wynika to z równowagi sił wzdłuż toru: nadmiar ciągu nad oporem zużywa się na wznoszenie.'),
    ('w02', 11, 'Co to jest zakręt prawidłowy? Jak zależą od przechylenia współczynnik obciążenia i prędkość kątowa zakrętu?',
     'Zakręt bez ślizgu i bez zmiany wysokości: L·cos φ = W, a ciąg równoważy opór. Współczynnik obciążenia n = 1/cos φ, '
     'prędkość kątowa zakrętu ψ̇ = g·√(n² − 1)/V.'),
    ('w02', 12, 'Jak wyznacza się pułap maksymalny przy szacowaniu parametrów?',
     'Na pułapie maksymalnym lot poziomy (n = 1) jest możliwy już tylko na granicy przeciągnięcia: '
     'W/S = q·C_z,max = ½·ρ_h·V²·C_z,max, a ciąg (moc) musi jeszcze zrównoważyć opór. Z tych warunków wyznacza się '
     'gęstość ρ_h, a z niej wysokość.'),
    # -- 3. Kadłuby -------------------------------------------------------------------------------------
    ('w03', 5, 'Jakie są wymagane kąty widoczności pilota do przodu w dół (α_F) i w bok w dół (α_S)?',
     'α_F: samoloty lekkie 5–10°, myśliwskie 11–15°, pasażerskie 11–20°, transportowe 17–20°. '
     'Najmniejsze α_S: lekkie 35°, pasażerskie 35°, myśliwskie 40°, transportowe 45°. Kąty te decydują o kształcie '
     'przodu kadłuba i położeniu oczu pilota.'),
    ('w03', 6, 'Podaj typowe wymiary kabiny pasażerskiej przyjmowane przy projektowaniu kadłuba.',
     'Szerokość siedzenia ok. 0,43–0,71 m na trasach dalekich i 0,41–0,46 m na krótkich; odstęp rzędów 0,86–1,02 m '
     'i 0,76–0,81 m; szerokość przejścia 0,51–0,71 m (0,38 m w małych); wysokość przejścia 1,93 m (1,52 m w małych). '
     'Liczbę toalet, objętość kuchni i bagaż osobisty dobiera się na pasażera.'),
    ('w03', 7, 'Do czego służą kontenery typu LD i jak wpływają na przekrój kadłuba?',
     'To znormalizowane kontenery bagażowo-towarowe (np. LD-3: wysokość 1,63 m, szerokość 2,01 m, głębokość 1,53 m, ok. 4,4 m³). '
     'Przekrój kadłuba dobiera się tak, by pod podłogą kabiny zmieściły się kontenery właściwego typu.'),
    ('w03', 18, 'Skrzydło wolnonośne czy zastrzałowe — porównaj.',
     'Zastrzał zmniejsza moment gnący przy nasadzie, więc skrzydło jest lżejsze i cieńsze, ale zastrzał wyraźnie zwiększa '
     'opór (C_x0 układu zastrzałowego jest dużo większe). Opłaca się w samolotach wolnych; przy większych prędkościach '
     'stosuje się skrzydło wolnonośne.'),
    # -- 4. Podwozia ------------------------------------------------------------------------------------
    ('w04', 1, 'Wymień zadania i wymagania stawiane podwoziu.',
     'Pochłonąć energię opadania przy przyziemieniu i uderzeń przy toczeniu, w dużej części nieodwracalnie (tłumienie); '
     'zapewnić małe opory toczenia i skuteczne, różnicowe hamowanie; zapewnić stateczność, sterowność i zwrotność na ziemi '
     'oraz chronić przed przewróceniem. Przy pełnym ugięciu tylko koła mogą dotykać ziemi. Podwozie ma być wytrzymałe, '
     'ale nie nadmiernie — po przekroczeniu obciążeń powinno ulec jako pierwsze i chronić płatowiec.'),
    ('w04', 9, 'Porównaj podwozie z kółkiem przednim i z kółkiem ogonowym.',
     'Kółko przednie: odporność na kapotaż i kangurowanie, lepsza stateczność kołowania, łatwiejszy start, załadunek '
     'i lepsza widoczność, stateczne lądowanie z wiatrem bocznym; wady — większe opory i masa, trudniejsze chowanie. '
     'Kółko ogonowe: lżejsze, mniejszy opór, łatwiejsze chowanie, lepsze na grząskim terenie, ale skłonne do kapotażu, '
     'kangurowania i niestateczne podczas kołowania.'),
    ('w04', 5, 'Jakie warunki geometryczne decydują o rozmieszczeniu podwozia?',
     'Przy kółku przednim kąt między pionem przez koła główne a prostą do ŚC powinien być nie mniejszy niż kąt natarcia dla '
     '0,9·C_z,max powiększony o 3°, a kąt prześwitu ogona powinien pozwolić osiągnąć kąt natarcia dla C_z,max. '
     'Przy kółku ogonowym kąt postojowy 10–15° odpowiada kątowi natarcia dla C_z ≈ 0,9·C_z,max (lądowanie na trzy punkty). '
     'W obu układach kąt przewrócenia na bok ma być mniejszy niż 60°.'),
    ('w04', 5, 'Jak szacuje się wymiary kół podwozia głównego?',
     'Ze wzorów statystycznych d = A·W_m^B i w = A·W_m^B (średnica i szerokość), gdzie W_m ≈ 0,9·W_TO/N to obciążenie '
     'jednego koła głównego (N — liczba kół głównych), a A i B zależą od klasy samolotu (np. lekkie: dla średnicy 1,51 i 0,349).'),
    ('w04', 11, 'Jakie wymagania dotyczą chowania podwozia?',
     'Czas chowania w samolotach lekkich 6–12 s, wypuszczania jeszcze krótszy; awaryjny układ wypuszczania; blokada '
     '(najlepiej mechaniczna) w obu skrajnych położeniach i zabezpieczenie przed złożeniem na ziemi; sygnalizacja położenia.'),
    ('w04', 8, 'Co to jest kangurowanie i kapotaż i z którym układem podwozia są związane?',
     'Kangurowanie to odbicie samolotu od ziemi po przyziemieniu z nadmierną prędkością — w układzie z kółkiem ogonowym '
     'uderzenie kół głównych zwiększa kąt natarcia i siłę nośną. Kapotaż to przewrócenie na nos, np. przy gwałtownym '
     'hamowaniu — groźny w układzie z kółkiem ogonowym, bo koła główne są przed ŚC.'),
    # -- 5. Napędy --------------------------------------------------------------------------------------
    ('w05', 5, 'Wymień rodzaje napędów lotniczych w kolejności rosnących prędkości lotu, w których się je stosuje.',
     'Silniki tłokowe; tłokowe z doładowaniem i turbośmigłowe; turbowentylatorowe; turboodrzutowe jedno- i dwuprzepływowe; '
     'z dopalaczem; strumieniowe (w granicach atmosfery); rakietowe (bez ograniczeń).'),
    ('w05', 6, 'Co to jest APU i RAT?',
     'APU — pomocnicza jednostka napędowa: dostarcza energii elektrycznej i sprężonego powietrza na ziemi, służy do rozruchu '
     'silników i jako źródło awaryjne. RAT — turbina wiatrakowa wysuwana w strumień powietrza, awaryjne źródło energii '
     'hydraulicznej lub elektrycznej po utracie zasilania z silników.'),
    ('w05', 7, 'Porównaj śmigło ciągnące i pchające.',
     'Ciągnące pracuje w niezaburzonym strumieniu i wspomaga chłodzenie silnika, ale strumień zaśmigłowy zaburza opływ '
     'kadłuba i skrzydła. Pchające zostawia czysty opływ przed sobą i ciszę w kabinie, ale pracuje w strumieniu zaburzonym '
     'przez płatowiec (drgania, hałas, gorsza sprawność), utrudnia chłodzenie i wymaga prześwitu śmigła przy obrocie.'),
    ('w05', 13, 'Do czego służy łoże silnikowe i jakie obciążenia przenosi?',
     'Mocuje silnik do płatowca i przenosi ciąg, moment obrotowy, moment żyroskopowy oraz siły masowe silnika; zwykle tłumi '
     'drgania (amortyzatory gumowe) i umożliwia dostęp do silnika oraz jego demontaż.'),
    ('w05', 19, 'Dlaczego chłodzenie trzeba uwzględnić przy integracji zespołu napędowego?',
     'Silnik oddaje dużą część energii paliwa jako ciepło. Wloty, kanały i wyloty powietrza chłodzącego oraz chłodnice '
     'oleju trzeba zmieścić w osłonie; źle zaprojektowane chłodzenie dodaje opór i grozi przegrzaniem, zwłaszcza przy '
     'małej prędkości i dużej mocy (wznoszenie).'),
    # -- 6. Usterzenia ----------------------------------------------------------------------------------
    ('w06', 1, 'Zdefiniuj cechy objętościowe usterzenia poziomego i pionowego.',
     'κ_H = S_H·L_H/(S·c_a) — L_H to odległość od 1/4 SCA płata do 1/4 SCA usterzenia poziomego; '
     'κ_V = S_V·L_V/(S·b) — L_V do 1/4 SCA usterzenia pionowego, b to rozpiętość.'),
    ('w06', 2, 'Podaj typowe cechy objętościowe usterzeń dla kilku klas samolotów.',
     'κ_V / κ_H: szybowce 0,02 / 0,5; lekkie jednosilnikowe 0,04 / 0,7; lekkie dwusilnikowe 0,07 / 0,8; '
     'turbośmigłowe dwusilnikowe 0,08 / 0,9; szkolne odrzutowe 0,06 / 0,7; myśliwce 0,07 / 0,4; transportowe '
     'i pasażerskie 0,08–0,09 / 1,0.'),
    ('w06', 3, 'Jak sprawdza się, czy usterzenie umożliwi wyprowadzenie z korkociągu?',
     'Usterzenie poziome tworzy w korkociągu cień aerodynamiczny wyznaczony liniami poprowadzonymi pod kątem 30–45° od jego '
     'krawędzi. Odpowiednio duża część steru kierunku musi leżeć poza tym cieniem, w niezaburzonym strumieniu; '
     'w przeciwnym razie ster kierunku jest nieskuteczny.'),
    ('w06', 5, 'Jak położenie usterzenia poziomego względem płata wpływa na jego działanie?',
     'Zalecane jest usterzenie nisko, poniżej płaszczyzny płata. Nieco powyżej jest dopuszczalne dla samolotów poddźwiękowych. '
     'Na średniej wysokości nad płatem lepiej go nie umieszczać, bo przy dużych kątach natarcia wchodzi w ślad płata (pitch-up, '
     'głębokie przeciągnięcie). Wysoko (T) — tylko przy dobrze zaprojektowanym płacie.'),
    ('w06', 11, 'Na czym polega układ kaczki i jaki problem tworzy wir brzegowy przedniego płata?',
     'Usterzenie poziome (płat przedni) jest przed skrzydłem i przenosi dodatnią siłę nośną. Wiry brzegowe płata przedniego '
     'zmieniają kąt natarcia na płacie tylnym — zmniejszają go za płatem przednim i zwiększają na zewnątrz od jego końcówek — '
     'co trzeba uwzględnić przy doborze rozpiętości obu płatów.'),
    # -- 7. Przykład: samolot szkolny -------------------------------------------------------------------
    ('w07', 4, 'W jakim zakresie SCA ma leżeć środek ciężkości i jak wstępnie umieszcza się skrzydło względem mas?',
     'Środek ciężkości całego samolotu ma leżeć w 25–35% SCA. Jeżeli większość struktury jest za ŚC, SCA rysuje się tak, '
     'by ŚC podstawowych mas (silnik, pilot, ładunek) był w 0–25% SCA; jeśli przed — w 30–45% SCA. Można przyjąć '
     'początkowo ok. 20% SCA, bo masa usterzeń przesunie ŚC do tyłu.'),
    ('w07', 3, 'Jakie ograniczenie dotyczy prędkości końca łopaty śmigła i dlaczego?',
     'Wypadkowa prędkość końcówki √(V_max² + (ω·r)²) powinna być mniejsza od ok. 0,85 prędkości dźwięku. '
     'Przy większej pojawiają się straty falowe, rośnie hałas i spada sprawność śmigła.'),
    ('w07', 6, 'Gdzie typowo leżą środki ciężkości skrzydła i usterzeń?',
     'Środek ciężkości skrzydła leży ok. 37–42% SCA płata, a usterzeń poziomego i pionowego ok. 30% ich SCA. '
     'Te położenia przyjmuje się w pierwszej analizie masowej, zanim powstanie konstrukcja.'),
    ('w07', 7, 'Jak z tabeli mas wyznacza się położenie środka ciężkości w procentach SCA i momenty bezwładności?',
     'x_SC = Σ m_i·x_i / Σ m_i (analogicznie y i z). Położenie w % SCA: 100·(x_SC − (x_A − 0,25·c_a))/c_a, gdzie A to punkt '
     '1/4 SCA. Momenty bezwładności: J_X = Σ m_i(y_i² + z_i²) itd., momenty dewiacyjne J_XY = Σ m_i·x_i·y_i itd. '
     'Liczy się je dla stanów: pusty, bez paliwa, maksymalna masa startowa, bez ładunku płatnego.'),
    ('w07', 4, 'Jak dobiera się wstępnie powierzchnie usterzeń w przykładzie projektu?',
     'Z cech objętościowych z analizy trendów: S_H = κ_H·S·c_a/L_H oraz S_V = κ_V·S·b/L_V, '
     'przy ramionach usterzeń wynikających z długości kadłuba.'),
    # -- 8. Płaty ---------------------------------------------------------------------------------------
    ('w08', 1, 'Według jakich kryteriów wybiera się profil płata?',
     'Aerodynamicznych: doskonałość (K_max) i opór przy projektowym C_z, C_z,max, charakter przeciągnięcia, współczynnik momentu. '
     'Konstrukcyjnych: grubość względna — miejsce na dźwigar i paliwo, masa i sztywność skrzydła.'),
    ('w08', 13, 'Opisz procedurę doboru profilu.',
     'Obliczyć Re i M dla prędkości projektowej i znaleźć charakterystyki dla tych warunków; obliczyć projektowe C_z; '
     'porównać C_x przy tym C_z i wybrać kilka najlepszych profili; porównać ich C_z,max, charakter oderwania i C_m; '
     'wybrać ten, który najlepiej pasuje do przeznaczenia samolotu. Katalogi: Re > 3·10⁶ — Abbott i von Doenhoff (NACA 824); '
     '5·10⁵–3·10⁶ — Wortmann (Stuttgarter Profilkatalog); poniżej — Selig. Dla M > 0,75 profile nadkrytyczne (NASA SC(2)).'),
    ('w08', 4, 'Co mówi znak pochodnej dC_m/dC_z profilu?',
     'O stateczności podłużnej: znak ujemny oznacza obiekt stateczny, dodatni — niestateczny.'),
    ('w08', 4, 'Jak grubość względna profilu wpływa na jego charakterystyki?',
     'Do pewnej grubości (ok. 12–15%) rośnie C_z,max, potem maleje; rośnie opór, a maleje krytyczna liczba Macha. '
     'Grubszy profil daje wyższy dźwigar — lżejszą i sztywniejszą konstrukcję oraz więcej miejsca na paliwo.'),
    ('w08', 6, 'Jak ugięcie szkieletowej wpływa na charakterystyki profilu?',
     'Większe ugięcie zwiększa siłę nośną przy danym kącie natarcia i C_z,max oraz przesuwa minimum oporu ku większym C_z, '
     'ale zwiększa ujemny moment pochylający (trzeba go zrównoważyć usterzeniem).'),
    ('w08', 8, 'Co to są profile laminarne i jaka jest ich wada?',
     'Profile z maksymalną grubością przesuniętą do tyłu, na których warstwa przyścienna długo pozostaje laminarna — '
     'mają mały opór w wąskim zakresie C_z („kubełek laminarny”). Są wrażliwe na zabrudzenie i nierówności powierzchni, '
     'a poza zakresem projektowym opór gwałtownie rośnie.'),
    ('w08', 17, 'Jak skos płata wpływa na efektywną liczbę Macha i inne charakterystyki?',
     'O zjawiskach falowych decyduje składowa prostopadła do krawędzi: M_eff = M∞·cos Λ, więc rośnie krytyczna liczba Macha. '
     'Skos zmniejsza gradient dC_z/dα, a oderwanie zaczyna się na końcówkach (ryzyko wyrwania nosa w górę); '
     'zwiększa też masę skrzydła.'),
    ('w08', 14, 'Jakie zbieżności mają typowo skrzydła i jak oblicza się średnią cięciwę aerodynamiczną płata trapezowego?',
     'Skrzydła o małym skosie λ = 0,4–0,5, o dużym skosie 0,2–0,3; c_k = λ·c_r. '
     'SCA = (2/3)·c_r·(1 + λ + λ²)/(1 + λ); jej położenie od osi: y = (b/6)·(1 + 2λ)/(1 + λ).'),
    ('w08', 16, 'Podaj typowe kąty wzniosu w zależności od położenia płata.',
     'Płaty proste: dolnopłat 5–7°, średniopłat 2–4°, górnopłat 0–2°. Skośne poddźwiękowe: 3–7°, −2–2°, −5 do −2°. '
     'Górnopłat ma mniejszy wznios, bo samo położenie płata nad ŚC działa jak dodatkowy wznios, a skos do tyłu też zwiększa '
     'efektywny wznios.'),
    ('w08', 18, 'Czym różni się zwichrzenie geometryczne od aerodynamicznego i po co się je stosuje?',
     'Geometryczne — kąt zaklinowania cięciw zmienia się wzdłuż rozpiętości (końcówki mają mniejszy). Aerodynamiczne — '
     'wzdłuż rozpiętości zmienia się profil (inny kąt zerowej siły nośnej). Cel: przeciągnięcie zaczyna się przy kadłubie, '
     'a lotki pozostają skuteczne; zmienia się też rozkład siły nośnej.'),
    ('w08', 14, 'Co to jest kąt zaklinowania płata?',
     'Kąt między cięciwą przykadłubową płata a osią podłużną kadłuba. Dobiera się go tak, by w przelocie kadłub leciał '
     'z najmniejszym oporem.'),
    ('w08', 16, 'Jak przeliczyć skos krawędzi natarcia na skos linii 25% cięciw?',
     'tan Λ_LE = tan Λ_c/4 + (1 − λ)/(A·(1 + λ)). Linia 1/4 cięciw łączy punkty 25% cięciw wzdłuż rozpiętości.'),
    # -- 9. Mechanizacja i sterownice -------------------------------------------------------------------
    ('w09', 1, 'Wymień rodzaje klap i urządzeń zwiększających siłę nośną na krawędzi natarcia.',
     'Klapy: zwykła (wysklepiająca), krokodylowa, szczelinowa, dwuszczelinowa, Junkersa, Fowlera. Krawędź natarcia: '
     'slot stały, slot ruchomy, klapa Kruegera, klapa przednia (opuszczany nosek).'),
    ('w09', 3, 'Jak klapa i slot zmieniają przebieg C_z(α)?',
     'Klapa przesuwa krzywą w górę: większy C_z przy danym α, większy C_z,max, ujemny przyrost kąta zerowej siły nośnej, '
     'krytyczny kąt natarcia nieco mniejszy. Slot przedłuża krzywą: zwiększa krytyczny kąt natarcia i C_z,max, '
     'prawie bez zmian przy małych kątach.'),
    ('w09', 3, 'Do czego służą spoilery (przerywacze)?',
     'Zmniejszają siłę nośną i zwiększają opór: hamowanie aerodynamiczne, stromsze zniżanie, docisk kół i skuteczniejsze '
     'hamowanie po przyziemieniu; wychylane niesymetrycznie wspomagają sterowanie poprzeczne.'),
    ('w09', 5, 'Co to jest moment odchylający (oporowy) lotek i jak mu się przeciwdziała?',
     'Lotka wychylona w dół zwiększa siłę nośną i opór indukowany swojego skrzydła, więc samolot odchyla się przeciwnie '
     'do zamierzonego zakrętu. Przeciwdziała się różnicowym wychyleniem lotek (więcej w górę niż w dół), lotkami Friese '
     'i skoordynowanym użyciem steru kierunku.'),
    ('w09', 8, 'Jakie są sposoby odciążenia aerodynamicznego sterownic?',
     'Odciążenie osiowe (oś obrotu przesunięta do tyłu od krawędzi natarcia steru), rogowe, wewnętrzne (Irvinga), lotki Friese '
     'oraz klapka odciążająca (Flettnera) wychylana przeciwnie do steru. Klapka dociążająca robi odwrotnie — zwiększa siły.'),
    ('w09', 9, 'Jak można wytrymować samolot?',
     'Przestawialnym statecznikiem, stałą klapką wyważającą (ustawianą na ziemi), ruchomą klapką wyważającą (trymerem) '
     'sterowaną z kabiny albo klapką odciążająco-wyważającą.'),
    # -- 10. Stateczność --------------------------------------------------------------------------------
    ('w10', 1, 'Do czego służy usterzenie?',
     'Zapewnia równowagę momentów (wyważenie) i stateczność, a sterami — sterowność.'),
    ('w10', 2, 'Napisz równanie równowagi momentów względem środka ciężkości dla układu klasycznego.',
     'M_Y + P_Z·x_SC − P_ZH·(x_H − x_SC) = 0: moment aerodynamiczny płata z kadłubem, moment siły nośnej płata '
     'na ramieniu x_SC i moment siły na usterzeniu poziomym na ramieniu (x_H − x_SC).'),
    ('w10', 3, 'Co to jest punkt neutralny ze sterem trzymanym i od czego zależy jego położenie?',
     'To położenie ŚC, przy którym ∂C_m/∂C_z = 0. Leży tym dalej z tyłu, im większe są S_H, ramię x_H, gradient a₁ usterzenia, '
     'stosunek (V_H/V)² i im mniejsze ∂ε/∂α; destabilizujący wpływ kadłuba (∂C_mbH/∂C_z) przesuwa go do przodu. '
     'ŚC przed punktem neutralnym oznacza stateczność statyczną; odległość to zapas stateczności.'),
    ('w10', 4, 'Jak zmienia się punkt neutralny przy puszczonym sterze i jak można poprawić stateczność?',
     'Puszczony ster ustawia się tak, by moment zawiasowy był zerowy (b₁α_H + b₂δ_H = 0), co zmniejsza skuteczny gradient '
     'usterzenia do a₁\' = a₁(1 − a₂b₁/(a₁b₂)), więc punkt neutralny przesuwa się do przodu. Poprawa: zwiększyć a₁ i b₂, '
     'zmniejszyć a₂ i b₁ (zmniejszanie a₂ grozi kłopotami ze sterowaniem, a zwiększanie b₂ zwykle zwiększa też b₁).'),
    ('w10', 7, 'Czym różni się stateczność z puszczonym sterem w układzie kaczki od układu klasycznego?',
     'Układ kaczki jest „bardziej stateczny” z puszczonym sterem, odwrotnie niż układ klasyczny.'),
    ('w10', 9, 'Co to jest punkt neutralny sterowności (manewrowy)?',
     'Położenie ŚC, przy którym ∂C_m/∂n = 0 — do zmiany przeciążenia nie trzeba wychylać steru. Leży za punktem neutralnym '
     'stateczności, bo w krzywoliniowym ruchu (q = g(n − 1)/V) usterzenie tłumi pochylanie (C_mq pochodzi głównie od usterzenia).'),
    ('w10', 13, 'Wymień postacie ruchu własnego samolotu w ruchu podłużnym i bocznym.',
     'Podłużne: oscylacje szybkie (krótkookresowe — kąt natarcia i pochylanie) i fugoida (długookresowa — wymiana energii '
     'kinetycznej i potencjalnej przy prawie stałym kącie natarcia). Boczne: przechylanie (aperiodyczne, szybko tłumione), '
     'spirala (aperiodyczna, powolna, może być niestateczna) i holendrowanie (oscylacje odchylania z przechylaniem).'),
    ('w10', 18, 'Jak norma MIL-F-8785C klasyfikuje samoloty, fazy lotu i poziomy akceptowalności?',
     'Klasy: I — małe lekkie (do 5000 kg); II — średnie (5000–30 000 kg), umiarkowanie manewrowe; III — duże i ciężkie '
     '(powyżej 30 000 kg); IV — średnie, bardzo manewrowe. Fazy: A — precyzyjne manewry (walka, akrobacja, lot w szyku), '
     'B — przelot, wznoszenie, zniżanie, C — start, lądowanie, podejście. Poziomy: 1 — bardzo dobre, 2 — wystarczające '
     'z dodatkowym obciążeniem pilota, 3 — samolot sterowny, ale zadanie wykonywane z trudem.'),
    # -- 11. Kryteria własności lotnych -----------------------------------------------------------------
    ('w11', 2, 'Jak z wartości własnej λ = ξ + iη wyznaczyć okres, czas zaniku do połowy, częstość nietłumioną i współczynnik tłumienia?',
     'Okres T = 2π/η; czas zaniku amplitudy do połowy T₁/₂ = −ln 2/ξ (dla ξ < 0), czas podwojenia T₂ = ln 2/ξ (dla ξ > 0); '
     'częstość nietłumiona ω_n = √(ξ² + η²); współczynnik tłumienia ζ = −ξ/ω_n.'),
    ('w11', 3, 'Jakie są wymagania dotyczące tłumienia fugoidy?',
     'Poziom 1: ζ ≥ 0,04; poziom 2: ζ ≥ 0; poziom 3 dopuszcza niestateczną fugoidę, jeśli okres oscylacji jest nie krótszy '
     'niż 55 s. Wymagania dotyczą sytuacji, gdy częstość oscylacji szybkich jest co najmniej 10 razy większa od fugoidalnej.'),
    ('w11', 5, 'Co to jest parametr CAP?',
     'Control Anticipation Parameter: stosunek początkowego przyspieszenia kątowego pochylania do ustalonego przyrostu '
     'przeciążenia po wychyleniu steru, q̇(0)/Δn_z(∞) [rad/s²/g]; w przybliżeniu ω_sp²/n_zα. Mówi, czy pilot może przewidzieć '
     'końcową reakcję samolotu z jego pierwszej reakcji (np. faza B, poziom 1: 0,085–3,6).'),
    ('w11', 6, 'Czego dotyczy kryterium C*?',
     'Oceny przebiegu przejściowego ruchu pochylania po skokowym wychyleniu sterownicy. C* łączy przyrost przeciążenia '
     'odczuwalnego przez pilota (z uwzględnieniem jego odległości od ŚC) z prędkością kątową pochylania; unormowany przebieg '
     'C*(t) musi zmieścić się w zalecanym korytarzu.'),
    ('w11', 7, 'Czemu służy kryterium nachylenia charakterystyki fazowej (Gibsona)?',
     'Ograniczeniu oscylacji indukowanych przez pilota (PIO). Ocenia się częstotliwość przy przesunięciu fazy o 180° '
     '(optymalnie 1–1,4 Hz) i nachylenie charakterystyki fazowej (optymalnie 60–90°/Hz).'),
    ('w11', 7, 'Jaki gradient siły na sterownicy na jednostkę przeciążenia zaleca norma?',
     'Gradient siły w N/g w przedziale od A_min/(n_z,max − 1) do A_max/(n_z,max − 1), gdzie n_z,max to największe dopuszczalne '
     'przeciążenie, a A zależy od sterownicy: drążek 93–250, wolant 133–370.'),
    ('w11', 2, 'Co to jest stała czasowa przechylania i jakie są jej dopuszczalne wartości?',
     'Czas, po którym prędkość kątowa przechylania osiąga 63% wartości ustalonej po skokowym wychyleniu lotek '
     '(człon inercyjny I rzędu). Poziom 1: faza A dla klas I i IV — do 1,0 s, dla klas II i III — do 1,4 s; faza B — do 1,4 s.', 'okBIPOL_1_handout_11_2.pdf'),
    ('w11', 3, 'Jakie wymagania stawia się stateczności spiralnej?',
     'Dopuszcza się niestateczność spiralną, ale kąt przechylenia nie może podwoić się zbyt szybko: poziom 1 — co najmniej '
     '12 s w fazach A i C oraz 20 s w fazie B; poziom 2 — 8 s; poziom 3 — 5 s. Mierzy się to z oswobodzonymi sterami '
     'po zaburzeniu przechylenia do 20°.', 'okBIPOL_1_handout_11_2.pdf'),
    ('w11', 5, 'Jakie wymaganie dotyczące holendrowania stawiają przepisy JAR/FAR 23 i 25?',
     'Oscylacje holendrowania muszą zostać stłumione do 1/10 amplitudy w ciągu najwyżej 7 cykli. '
     'Stąd kryterium −ξ/η ≥ ln 10/(14π) ≈ 0,0523.', 'okBIPOL_1_handout_11_2.pdf'),
    # -- 12. Obciążenia i obwiednia ---------------------------------------------------------------------
    ('w12', 2, 'Zdefiniuj współczynnik obciążenia. Ile wynosi w locie poziomym, w zakręcie prawidłowym i przy C_z,max?',
     'n = P_z/Q = L/W. W locie poziomym n = 1, w zakręcie prawidłowym n = 1/cos φ, a największy możliwy przy danej '
     'prędkości: n = ρV²S·C_z,max/(2W).'),
    ('w12', 2, 'Na jakie grupy przepisy dzielą obciążenia w locie i co to jest obwiednia obciążeń?',
     'Obciążenia od sterowania (manewrowe) i od podmuchów (burzliwej atmosfery). Obwiednia to wykres n(V) ograniczający '
     'obszar dopuszczalnych kombinacji prędkości i współczynnika obciążenia; każdy punkt jej brzegu jest przypadkiem obliczeniowym.'),
    ('w12', 7, 'Wyprowadź przyrost współczynnika obciążenia od podmuchu pionowego.',
     'Podmuch u zmienia kąt natarcia o Δα ≈ u/V, więc ΔL = ½ρV²S·C_Lα·u/V = ½ρVS·C_Lα·u, a Δn = ρ·u·V·C_Lα/(2·W/S). '
     'n = 1 ± Δn; przepisy mnożą przyrost przez współczynnik złagodzenia podmuchu K_g.'),
    ('w12', 10, 'Ile wynosi współczynnik bezpieczeństwa i co oznaczają obciążenia dopuszczalne i niszczące?',
     'Współczynnik bezpieczeństwa 1,5 (JAR-23.303). Obciążenia dopuszczalne to największe spodziewane w eksploatacji; '
     'obciążenia niszczące (obliczeniowe) = 1,5 × dopuszczalne — konstrukcja ma je przenieść bez zniszczenia.'),
    ('w12', 11, 'Jak wyznacza się rozkład siły nośnej metodą Schrenka?',
     'Jako średnią rozkładu proporcjonalnego do cięciw płata i rozkładu eliptycznego płata o tej samej powierzchni i rozpiętości: '
     'c_S(y) = [c(y) + c_e(y)]/2, gdzie c_e(y) = (4S/(πb))·√(1 − (2y/b)²). Lokalne c_z/C_z = c_S/c pokazuje, '
     'gdzie zacznie się przeciągnięcie.'),
    ('w12', 13, 'Jak z obciążenia płata wyznacza się siłę tnącą i moment gnący?',
     'Obciążenie jednostkowe W = dV/dy, siła tnąca V = dM/dy. W przybliżeniu sumuje się od końcówki: V_i = V_i−1 + W_i·Δy, '
     'M_i = M_i−1 + V_i·Δy. Dla nieważkiego płata wolnonośnego siła tnąca u nasady ≈ ½·n·Q.'),
    ('w12', 14, 'Które elementy dźwigara przenoszą moment gnący, a które siłę tnącą?',
     'Pasy dźwigara przenoszą moment gnący (jeden pas ściskany, drugi rozciągany), a ścianka — siłę tnącą (ścinanie).'),
    ('w12', 11, 'Dlaczego masy umieszczone w skrzydle (paliwo, struktura) zmniejszają moment gnący u nasady?',
     'W locie z przeciążeniem n działają na nie siły masowe n·m·g skierowane przeciwnie do siły nośnej, więc odciążają płat. '
     'Paliwo daleko od kadłuba odciąża bardziej — dlatego przypadek bez paliwa bywa wymiarujący dla zginania.'),
    # -- 13. Obciążenia usterzenia ----------------------------------------------------------------------
    ('w13', 5, 'Jakie źródła obciążeń usterzenia poziomego uwzględnia się przy szukaniu przypadku wymiarującego?',
     'Obciążenia od równowagi, od sterowania (manewrowe), od podmuchów oraz niesymetryczne (ślizg, strumień zaśmigłowy). '
     'Sposób ich wyznaczenia zależy od przepisów i kategorii samolotu.'),
    ('w13', 5, 'Co to jest obciążenie usterzenia od równowagi i dla jakich prędkości się je wyznacza?',
     'Obciążenie potrzebne do utrzymania równowagi momentów bez przyspieszeń pochylających. Wyznacza się je dla punktów '
     'charakterystycznych obwiedni, w szczególności V_A, V_F, V_C i V_D: kąt natarcia usterzenia α_H, wychylenie steru δ_H, '
     'a₁α_H i a₂δ_H. To obciążenie początkowe, do którego dodaje się pozostałe.'),
    ('w13', 5, 'Czy przypadek wymiarujący całe usterzenie poziome jest zawsze wymiarujący dla steru wysokości?',
     'Nie. Przypadek wymiarujący część stałą usterzenia i okucia główne nie musi wymiarować steru wysokości, '
     'więc ster sprawdza się osobno.'),
    ('w13', 4, 'Do czego nie nadaje się metoda zlinearyzowanego rozkładu ciśnienia na usterzeniu?',
     'Do obliczania momentów zawiasowych: w rzeczywistości wypadkowa siła na sterze leży bliżej osi obrotu, niż wynika '
     'z tej metody. Wyznaczony moment skręcający ster jest nieco za duży, co daje tylko niewielkie przewymiarowanie.'),
    ('w13', 6, 'Jak wyznacza się obciążenia usterzenia od sterowania?',
     'Według kryteriów przepisów: największych sił na organach sterowania (drążek, wolant) lub największych przyspieszeń '
     'kątowych. Przyrosty sił i momentów zawiasowych liczy się dla wychyleń steru w górę i w dół, w punktach charakterystycznych obwiedni.'),
    # -- 14. Obciążenia kadłuba -------------------------------------------------------------------------
    ('w14', 1, 'Wymień źródła obciążeń kadłuba.',
     'Reakcje zespołów mocowanych do kadłuba (usterzenia, podwozie, masy skupione, ładunek, urządzenia); obciążenia '
     'aerodynamiczne (istotne przy M > 0,5 lub kadłubach nośnych); masa własna w polu przyspieszeń; różnica ciśnień '
     'w kabinach hermetyzowanych; zespoły napędowe i instalacje siłowe (np. zaczep holowniczy).'),
    ('w14', 2, 'Jaki model obliczeniowy przyjmuje się dla kadłuba i jakie rodzaje obciążeń się w nim rozpatruje?',
     'Belkę podpartą na dwóch podporach — okuciach głównych skrzydło–kadłub. Rozpatruje się zginanie pionowe, '
     'zginanie poziome i skręcanie.'),
    ('w14', 3, 'Jakie przyspieszenie działa na masę i-tą kadłuba, gdy na samolot działa siła zewnętrzna, np. na kółku przednim?',
     'Suma przyspieszenia od przeciążenia n·g, liniowego od siły P/m (oba stałe wzdłuż kadłuba) i liniowego od przyspieszenia '
     'kątowego ε = P·r/J_y, zmieniającego się liniowo z odległością od ŚC: a_i = a_n + a_p + ε·(x_SC − x_i).'),
    ('w14', 7, 'Jakie przypadki obciążeń jednostkowych stosuje się w analizie kadłuba i jak się je łączy?',
     'Masy przy n = 1, masy przy przyspieszeniu kątowym wywołanym jednostkową siłą na usterzeniu (P_ZHε = 1 kN) '
     'oraz aerodynamiczną siłę P_ZH = 1 kN na usterzeniu. Dowolny przypadek to suma wykresów jednostkowych przeskalowanych '
     'przez rzeczywiste n, P_ZHε i P_ZH (superpozycja).'),
    ('w14', 6, 'Skąd pochodzi skręcanie kadłuba?',
     'Od siły bocznej na usterzeniu pionowym działającej nad osią kadłuba (M_s = P_poz·h) oraz od niesymetrii opływu '
     'usterzenia poziomego (M_s = (P_H1 − P_H2)·a_H).'),
    # -- 15. Obciążenia podwozia ------------------------------------------------------------------------
    ('w15', 2, 'Jaką energię musi pochłonąć podwozie przy lądowaniu?',
     'Energię kinetyczną opadania i energię potencjalną obniżenia środka masy przy ugięciu, pomniejszoną o pracę siły nośnej: '
     'E = m·w²/2 + (m·g − P_z)·h. Pracę tę wykonuje podwozie główne.'),
    ('w15', 3, 'Jakie założenia przyjmuje się co do siły nośnej w chwili przyziemienia?',
     'Dwa skrajne: siła nośna równa ciężarowi albo równa zeru; rzeczywistość leży pomiędzy. Przepisy (JAR-23.473) pozwalają '
     'przyjąć siłę nośną nie większą niż 2/3 ciężaru samolotu.'),
    ('w15', 5, 'Co to jest współczynnik pełnoty pracy amortyzatora? Podaj typowe wartości.',
     'Stosunek pracy rzeczywistego amortyzatora do pracy amortyzatora idealnego o stałej sile Z na całym skoku (Z·h_a). '
     'Sprężyna: 0,5; pneumatyk: ok. 0,45; amortyzator cieczowo-gazowy: ok. 0,8 i więcej.'),
    ('w15', 5, 'Dlaczego amortyzator sprężynowy prowadzi do kozłowania, a cieczowo-gazowy nie?',
     'Sprężyna zwraca prawie całą zgromadzoną energię (brak histerezy), co daje gwałtowny odbój i podskoki. '
     'W amortyzatorze cieczowo-gazowym znaczna część energii jest bezpowrotnie rozpraszana w przepływie cieczy przez dławiki.'),
    ('w15', 4, 'Jak wyznacza się siłę poziomą na kole przy lądowaniu i gdzie się ją przykłada?',
     'X = μ·Z, więc współczynnik obciążenia wzdłuż osi x to n_x = μ·n_L. Siłę przykłada się do osi koła (chyba że koło jest '
     'zahamowane); wynika ona z rozkręcania koła, dlatego duże koła rozpędza się przed przyziemieniem.'),
    ('w15', 6, 'Ile trwa maksymalne ugięcie amortyzatora podczas lądowania i co się dzieje przy zbyt szybkim wciskaniu tłoka?',
     'Nie dłużej niż ok. 0,5 s. Przy zbyt dużej prędkości wciskania tłoka siła reakcji Z gwałtownie rośnie, '
     'a współczynnik pełnoty pracy maleje.'),
)

_FILES = {key: source.split(', ')[0] for key, _, _, source in LECTURES}
QUESTIONS = tuple(dict(id=f'{item[0]}_{i:02d}', lecture=item[0], slide=item[1], question=item[2], answer=item[3],
                       source=item[4] if len(item) > 4 else _FILES[item[0]])
                  for i, item in enumerate(_Q, 1))


def lectures_with_questions():
    """Wykłady z listą ich pytań (do szablonu panelu)."""
    return [dict(key=key, number=number, title=title, source=source,
                 questions=[q for q in QUESTIONS if q['lecture'] == key])
            for key, number, title, source in LECTURES]
