/**
 * BiPOL Requiem - Kompletna Encyklopedia Dydaktyczna Parametrów i Konstrukcji MEiL PW
 * Opracowana na podstawie:
 * 1. Prof. dr hab. inż. Cezary Galiński: "Wybrane zagadnienia konstrukcji samolotów", OW PW, Warszawa 2020.
 * 2. Materiały dydaktyczne BIPOL I (dr inż. Marcin Figat, prof. C. Galiński - ZSiS MEiL PW).
 * 3. Materiały Mechanika Lotu I (dr M. Lasek, dr Z. Paturski - ZM MEiL PW).
 * 4. Zapis Konstrukcji CAD I (dr inż. Łukasz Lindstedt - ZPK MEiL PW, normy PN-EN ISO 128 / 129 / 5456-2).
 */

const DIDACTIC_DATABASE = {
  // 1. MECHANIZACJA KRAWĘDZI SPŁYWU - KLAPY (Rozdział 16.3, str. 164-171)
  flaps: {
    plain: {
      id: "plain",
      name: "Klapa zwykła (wysklepiająca / Plain Flap)",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.14a, str. 164",
      delta_cz_max: 0.55,
      cz_max_to_rec: 1.65,
      cz_max_lnd_rec: 1.95,
      delta_cx0_lnd: 0.030,
      mass_penalty_pct: 1.0,
      kinematic_complexity: "Niska (1/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,30 Q80,10 140,28 L140,38 Q80,42 10,33 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="140" cy="33" r="3.5" fill="#dc2626"/>
        <path d="M140,33 L190,55 L185,61 L138,38 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <path d="M140,28 Q165,30 192,34" stroke="#64748b" stroke-dasharray="3,3" fill="none"/>
        <text x="12" y="16" font-size="9" fill="#334155" font-weight="bold">Zawias liniowy (brak szczeliny)</text>
      </svg>`,
      pros: [
        "Najprostsza konstrukcja mechaniczna – ruch odbywa się wokół pojedynczej osi obrotu na konwencjonalnych zawiasach liniowych lub punktowych.",
        "Minimalna masa własna – brak skomplikowanych wysięgników podskrzydłowych, szyn i wózków rolkowych.",
        "Czysty obrys profilu w pozycji schowanej – brak wystających pod skrzydłem owiewek węzłów zawieszenia (mniejszy opór Cx0).",
        "Tani i łatwy montaż oraz obsługa eksploatacyjna, idealna do prostych samolotów szkolno-treningowych i ultralekkich (ULM)."
      ],
      cons: [
        "Niska efektywność aerodynamiczna: przyrost współczynnika siły nośnej ΔCz_max wynosi zaledwie 0.45 – 0.60.",
        "Brak szczeliny zasilającej warstwę przyścienną – przy kątach wychylenia powyżej 15–20° następuje gwałtowne oderwanie opływu na górnej powierzchni klapy.",
        "Znaczny przyrost oporu profilowego przy małym przyroście siły nośnej w porównaniu do klap szczelinowych.",
        "Niewystarczająca dla samolotów o dużym obciążeniu powierzchni nośnej (W/S > 1200 N/m²)."
      ],
      galinski_quote: "W najprostszym przypadku klap wysklepiających wystarcza zawieszenie na konwencjonalnych zawiasach liniowych lub punktowych (rys. 16.14a). Pokrycie za dźwigarkiem może być sztywne lub elastyczne, zawsze jednak należy zadbać, aby środek masy znajdował się możliwie blisko lub przed osią obrotu klapy (ochrona przed flatterem).",
      typical_aircraft: "PZL-102B Kos, Piper J-3 Cub, RWD-8, szybowce szkolne i akrobacyjne.",
      recommendation: "Zalecana dla lekkich samolotów szkolnych, motoszybowców i maszyn turystycznych o niskich prędkościach lądowania (Vs0 < 85 km/h)."
    },

    split: {
      id: "split",
      name: "Klapa krokodylowa (Split Flap)",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.14a, str. 164",
      delta_cz_max: 0.75,
      cz_max_to_rec: 1.75,
      cz_max_lnd_rec: 2.15,
      delta_cx0_lnd: 0.055,
      mass_penalty_pct: 1.5,
      kinematic_complexity: "Niska (2/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,30 Q90,10 195,34 L140,38 Q85,42 10,33 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="140" cy="38" r="3.5" fill="#dc2626"/>
        <path d="M140,38 L182,60 L178,64 L136,40 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#334155" font-weight="bold">Odchylana dolna płyta pokrycia</text>
      </svg>`,
      pros: [
        "Górna powierzchnia spływu skrzydła pozostaje całkowicie nienaruszona – brak zaburzenia opływu na górnym pokryciu.",
        "Bardzo duży opór aerodynamiczny w pozycji lądowania – znakomicie pełni rolę hamulca aerodynamicznego, umożliwiając strome podejście bez rozpędzania samolotu.",
        "Zawiasy montowane bezpośrednio do dolnego pasa dźwigarka pomocniczego lub dolnego pokrycia.",
        "Wysoka sztywność konstrukcyjna samej płyty klapy."
      ],
      cons: [
        "Duży ujemny moment pochylający (ΔCm < 0) – silna tendencja do pochylania nosa w dół wymagająca dużego usterzenia poziomego.",
        "Mała przydatność w konfiguracji startowej – duży opór szkodliwy (wir za płytą) pogarsza gradient wznoszenia przy starcie.",
        "Bardzo duże siły zawiasowe przy wyższych prędkościach – wymaga mocnych siłowników lub przekładni.",
        "Brak szczeliny energetyzującej warstwę przyścienną."
      ],
      galinski_quote: "W samolocie Douglas DC-3 (rys. 16.14a) zastosowano klapy krokodylowe zawieszone na zawiasach punktowych na dolnej powierzchni. Płyta dolna odchyla się w dół, tworząc za sobą podciśnienie zwiększające wysklepienie efektywne oraz silny opór hamujący.",
      typical_aircraft: "Douglas DC-3 / C-47 Dakota, Supermarine Spitfire, PZL-37 Łoś, North American T-6 Texan.",
      recommendation: "Doskonała w konstrukcjach historycznych oraz maszynach wymagających stromego kąta schodzenia do lądowania bez osobnych hamulców aerodynamicznych."
    },

    junkers: {
      id: "junkers",
      name: "Klapa zewnętrzna szczelinowa Junkersa",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.14b, str. 164",
      delta_cz_max: 1.05,
      cz_max_to_rec: 1.95,
      cz_max_lnd_rec: 2.40,
      delta_cx0_lnd: 0.045,
      mass_penalty_pct: 2.2,
      kinematic_complexity: "Średnia (2.5/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q80,10 160,30 L155,36 Q80,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <line x1="140" y1="35" x2="155" y2="50" stroke="#dc2626" stroke-width="2.5"/>
        <circle cx="155" cy="50" r="3.5" fill="#dc2626"/>
        <path d="M142,46 Q168,42 192,58 L182,62 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#334155" font-weight="bold">Oś obrotu daleko pod profilem (STOL)</text>
      </svg>`,
      pros: [
        "Oś obrotu znajduje się daleko pod profilem skrzydła – tworzy stałą, wyprofilowaną szczelinę aerodynamiczną energetyzującą warstwę przyścienną.",
        "Możliwość pracy na całej rozpiętości płata jako klapolotka (flaperon) ze sprzężonym sterowaniem różnicowym.",
        "Bardzo wysoka skuteczność przy małych prędkościach lotu – kluczowy układ dla samolotów krótkiego startu i lądowania (STOL).",
        "Prosta konstrukcja głównego kesonu skrzydła (brak podcięć w części spływowej płata)."
      ],
      cons: [
        "Stały opór pasożytniczy – klapa i jej długie wysięgniki znajdują się w strumieniu powietrza nawet w locie przelotowym (wzrost Cx0 o 0.004–0.006).",
        "Spadek prędkości maksymalnej i przelotowej samolotu o 5–10%.",
        "Długie wysięgniki narażone na uszkodzenia mechaniczne na trawiastych lądowiskach przygodnych.",
        "Wrażliwość na oblodzenie szczeliny i wysięgników."
      ],
      galinski_quote: "Już w przypadku klap Junkersa (rys. 16.14b, np. samolot Zenair STOL CH 701) oś obrotu klapy znajduje się daleko pod obrysem profilu płata. Wymaga to przymocowania do żeber w skrzydle długiego wysięgnika z łożyskiem obrotu wystającego w opływ.",
      typical_aircraft: "Zenair STOL CH 701 / CH 750, Junkers Ju 52, Ju 87 Stuka, samoloty buszowe ULM.",
      recommendation: "Idealny wybór dla samolotów krótkiego startu i lądowania (STOL), maszyn rolniczych i patrolowych latających z małą prędkością przelotową."
    },

    single_slotted: {
      id: "single_slotted",
      name: "Klapa jednoszczelinowa (Single Slotted Flap)",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.15-16.16, str. 165",
      delta_cz_max: 1.15,
      cz_max_to_rec: 1.95,
      cz_max_lnd_rec: 2.45,
      delta_cx0_lnd: 0.040,
      mass_penalty_pct: 2.5,
      kinematic_complexity: "Średnia (3/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q80,10 135,28 C138,32 142,36 140,38 Q80,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <line x1="128" y1="38" x2="145" y2="50" stroke="#dc2626" stroke-width="2.5"/>
        <circle cx="145" cy="50" r="3.5" fill="#dc2626"/>
        <path d="M140,38 Q154,32 192,50 L186,55 Q150,45 138,44 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <path d="M128,40 Q137,38 145,33" stroke="#16a34a" stroke-width="2" stroke-dasharray="2,2" fill="none"/>
        <text x="12" y="16" font-size="9" fill="#15803d" font-weight="bold">Strumień szczelinowy zdmuchuje oderwanie</text>
      </svg>`,
      pros: [
        "Strumień powietrza przepływający przez szczelinę z dolnej na górną powierzchnię przyspiesza i regeneruje warstwę przyścienną na klapie.",
        "Opóźnienie oderwania strugi do kątów wychylenia 35–40° – wysoki przyrost ΔCz_max rzędu 1.0 – 1.25.",
        "Bardzo korzystny przyrost doskonałości przy starcie (wychylenie 10–15°), wyraźnie skracający rozbieg S_to.",
        "Umiarkowana masa i wysoka niezawodność – standard współczesnego lotnictwa ogólnego (GA CS-23)."
      ],
      cons: [
        "Wymaga wysuniętej osi obrotu poniżej dolnego pokrycia skrzydła na zewnętrznych wysięgnikach lub czworoboku przegubowym (rys. 16.25).",
        "Wsporniki zawieszenia wymagają owiewek podskrzydłowych (np. w Cirrus SR22 i Partenavia Victor), dających niewielki opór pasożytniczy.",
        "Wymaga wysokiej dokładności wykonania geometrii noska klapy i ścianki przed klapą, aby szczelina miała kształt dyszy zbieżnej.",
        "Większy moment pochylający niż w klapie zwykłej."
      ],
      galinski_quote: "Najprostszym rozwiązaniem dla klap szczelinowych jest przymocowanie do żeber w skrzydle długiego wysięgnika z łożyskiem obrotu klapy oraz drugiego wysięgnika w klapie (rys. 16.15–16.17, np. Cirrus SR22). Można też zastosować czworobok przegubowy (rys. 16.25, szybowiec Breguet 901).",
      typical_aircraft: "Cessna 172 Skyhawk, Cirrus SR22, Piper PA-28, Diamond DA40, Partenavia P.68 Victor.",
      recommendation: "Najbardziej uniwersalny i zalecany wybór dla 80% samolotów turystycznych, szkolnych, dyspozycyjnych i lekkich transportowych."
    },

    fowler: {
      id: "fowler",
      name: "Klapa Fowlera (wysuwana szczelinowa szynowo-rolkowa)",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.23-16.24, str. 169-170",
      delta_cz_max: 1.50,
      cz_max_to_rec: 2.15,
      cz_max_lnd_rec: 2.75,
      delta_cx0_lnd: 0.048,
      mass_penalty_pct: 4.5,
      kinematic_complexity: "Wysoka (4/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q70,10 125,28 C128,34 130,38 125,39 Q70,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <path d="M110,40 Q140,44 172,52" stroke="#475569" stroke-width="3.5" fill="none"/>
        <circle cx="142" cy="45" r="3" fill="#f59e0b"/>
        <circle cx="160" cy="49" r="3" fill="#f59e0b"/>
        <path d="M138,38 Q158,32 202,48 L196,53 Q155,43 135,43 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#b45309" font-weight="bold">Wysuw w tył (+ΔS) + obrót na szynie</text>
      </svg>`,
      pros: [
        "Jednoczesny wysuw do tyłu i obrót w dół – zwiększa nie tylko wysklepienie profilu, ale również fizyczną powierzchnię nośną skrzydła S o 10–15%!",
        "Maksymalny zysk siły nośnej wśród klap jednosegmentowych: ΔCz_max sięga 1.35 – 1.60 (Cz_max_lnd do 2.8).",
        "W pierwszej fazie (startowej) klapa wysuwa się głównie w tył, dając ogromny przyrost siły nośnej przy minimalnym przyroście oporu.",
        "Pozwala zastosować wysokie obciążenie powierzchni W/S (mniejsze skrzydło o małym oporze w locie przelotowym) przy zachowaniu niskiej prędkości lądowania Vs0."
      ],
      cons: [
        "Duża masa i skomplikowanie mechanizmu szynowo-rolkowego napędzanego śrubami pociągowymi (rys. 16.23).",
        "Szyny prowadzące często wystają poza obrys profilu i wymagają dużych owiewek pod skrzydłem.",
        "Wrażliwość na ugięcia skrzydła – zbyt wiotka szyna prowadzi do zablokowania wózków rolkowych pod obciążeniem aerodynamicznym!",
        "Duże przesunięcie środka parcia do tyłu generuje silny ujemny moment pochylający ΔCm (wymaga większej objętości usterzenia poziomego V_H)."
      ],
      galinski_quote: "Zawieszenie szynowo-rolkowe (rys. 16.23 i 16.24, np. samolot PZL-130 Orlik) daje niemal nieograniczone możliwości kształtowania trajektorii klapy Fowlera. Istotnym problemem jest sztywność szyny: jeśli byłaby za mała, klapa zablokowałaby się przy ugięciu skrzydła. Z kolei sztywna szyna bywa ciężka i wystaje poza obrys płata.",
      typical_aircraft: "PZL-130 Orlik, Beechcraft King Air, ATR 42/72, Boeing 737 / 787, Cessna Citation, Lockheed C-130.",
      recommendation: "Zalecana dla szybkich samolotów tłokowych, turbośmigłowych, szkolno-bojowych oraz odrzutowych dyspozycyjnych i komunikacyjnych."
    },

    double_slotted: {
      id: "double_slotted",
      name: "Klapa dwuszczelinowa (Double Slotted Flap)",
      reference: "Galiński, Rozdz. 16.3, Rys. 16.18-16.22, str. 166-169",
      delta_cz_max: 1.85,
      cz_max_to_rec: 2.30,
      cz_max_lnd_rec: 3.10,
      delta_cx0_lnd: 0.065,
      mass_penalty_pct: 6.5,
      kinematic_complexity: "Bardzo wysoka (5/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q65,10 112,28 C115,34 118,38 115,39 Q65,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <path d="M122,35 Q132,32 146,42 L142,45 Q128,39 120,40 Z" fill="#3b82f6" stroke="#1e3a8a" stroke-width="1.5"/>
        <path d="M144,41 Q162,37 202,58 L195,63 Q158,50 140,47 Z" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#1e3a8a" font-weight="bold">2 segmenty + 2 szczeliny (Cz_max > 3.0)</text>
      </svg>`,
      pros: [
        "Najwyższy przyrost współczynnika siły nośnej: dwie szczeliny kaskadowo energetyzują opływ, pozwalając uzyskać Cz_max_lnd = 2.8 – 3.3!",
        "Umożliwia bardzo strome podejście i krótkie lądowanie ciężkich samolotów transportowych i pasażerskich.",
        "W odmianie ze stałym przednim slotem (np. Boeing C-17, BAE Hawk - rys. 16.18–16.20) napęd pozostaje stosunkowo prosty.",
        "W odmianie z niezależnymi siłownikami (np. GAF Nomad - rys. 16.22) pozwala indywidualnie optymalizować wysuw na lądowiskach w buszu."
      ],
      cons: [
        "Bardzo duża masa własna mechanizacji, wsporników i wielosekcyjnych siłowników.",
        "Skomplikowana kinematyka sprzężonych wysięgników (np. L-410 Turbolet - rys. 16.21) wymagająca precyzyjnej regulacji.",
        "Wymaga wygospodarowania obszernej wnęki w spływie skrzydła na schowanie przedniego segmentu (vane).",
        "W samolotach STOL z nadmuchem gazów wylotowych (np. C-17) wymaga zastosowania ciężkich stopów żarowytrzymałych (Inconel, Rene 41) odpornych na pełzanie."
      ],
      galinski_quote: "Dążąc do wysokiej efektywności przy akceptowalnej masie, stosuje się klapy dwuszczelinowe ze stałym slotem (C-17, F-18, BAE Hawk - rys. 16.19-16.20), ze sprzężonym napędem jednym siłownikiem (L-410 Turbolet - rys. 16.21) lub z dwoma niezależnymi siłownikami (GAF Nomad - rys. 16.22).",
      typical_aircraft: "Boeing C-17 Globemaster III, Let L-410 Turbolet, GAF Nomad, Airbus A321, BAE Hawk.",
      recommendation: "Niezbędna dla samolotów komunikacyjnych, regionalnych STOL oraz ciężkich transportowców wojskowych."
    },

    flaperon: {
      id: "flaperon",
      name: "Klapolotka (Flaperon z mikserem różnicowym)",
      reference: "Galiński, Rozdz. 17.3.8, Rys. 17.28, str. 205-207",
      delta_cz_max: 0.85,
      cz_max_to_rec: 1.80,
      cz_max_lnd_rec: 2.15,
      delta_cx0_lnd: 0.035,
      mass_penalty_pct: 1.8,
      kinematic_complexity: "Średnia z mikserem (3.5/5)",
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q75,10 132,28 L130,38 Q75,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="136" cy="33" r="3.5" fill="#7c3aed"/>
        <path d="M136,33 L192,50 L187,56 L134,38 Z" fill="#ddd6fe" stroke="#5b21b6" stroke-width="2"/>
        <path d="M136,33 L192,18" stroke="#7c3aed" stroke-dasharray="3,3" stroke-width="1.5"/>
        <text x="12" y="16" font-size="9" fill="#5b21b6" font-weight="bold">Mikser: Wychylenie klapowe + ruch lotkowy</text>
      </svg>`,
      pros: [
        "Łączy funkcję klapy i lotki na całej rozpiętości skrzydła – maksymalne wykorzystanie krawędzi spływu.",
        "Zmniejsza masę i liczbę oddzielnych powierzchni sterowych (idealne w motoszybowcach i lekkich samolotach kompozytowych).",
        "Umożliwia ustawienie ujemnego kąta klapolotek (-3° do -5°) w locie szybkim, zmniejszając opór profilowy skrzydła.",
        "Poprawia rozkład siły nośnej wzdłuż rozpiętości."
      ],
      cons: [
        "Wymaga mechanicznego miksera sumującego ruchy drążka i dźwigni klap (np. czworobok ze śrubą rzymską - rys. 17.28).",
        "Ryzyko przeciągnięcia końcówki skrzydła przy jednoczesnym pełnym wychyleniu klapowym i wychyleniu lotki w dół!",
        "Zgodnie z zasadą prof. Galińskiego wychylenie klapolotki musi być mniejsze niż klap przykadłubowych, aby oderwanie zaczęło się przy kadłubie.",
        "Podatność na flatter giętno-skrętny – bezwzględny wymóg wyważenia masowego przed osią obrotu."
      ],
      galinski_quote: "Łączne wychylenie klapolotek w dół powinno być mniejsze niż wychylenie konwencjonalnych klap. Większe wychylenie klap wewnętrznych gwarantuje, że przy zmniejszaniu prędkości oderwanie opływu najpierw wystąpi przy kadłubie, zachowując sterowność poprzeczną (rys. 17.28).",
      typical_aircraft: "Motoszybowiec AOS-71 (PW), PZL-104 Wilga, szybowce zawodnicze, F-16, UAV MALE.",
      recommendation: "Wyjątkowo korzystna dla motoszybowców, bezzałogowców MALE oraz samolotów ultralekkich i STOL."
    }
  },

  // 1.1 STEROWANIE POPRZECZNE - LOTKI (Rozdział 17.3, str. 195-207 prof. C. Galiński / Danilecki rozdz. 8)
  ailerons: {
    differential: {
      id: "differential",
      name: "Lotka różnicowa (Differential Aileron - standard GA)",
      reference: "Galiński, Rozdz. 17.3.5, str. 201-203; Danilecki rozdz. 8",
      delta_a_up_deg: 24,
      delta_a_down_deg: 12,
      typical_pb_2v: 0.082,
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,32 Q80,12 140,30 L140,38 Q80,44 10,35 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="140" cy="34" r="3.5" fill="#10b981"/>
        <path d="M140,34 L188,14 L185,8 L138,28 Z" fill="#a7f3d0" stroke="#059669" stroke-width="2"/>
        <path d="M140,34 L188,44 L185,48 L138,38 Z" stroke="#6b7280" stroke-dasharray="3,3" fill="none"/>
        <text x="12" y="16" font-size="9" fill="#065f46" font-weight="bold">Ruch różnicowy: w górę 24° / w dół 12°</text>
      </svg>`,
      pros: [
        "Skuteczna eliminacja niekorzystnego sprzężenia odchylającego (adverse yaw) dzięki większemu wychyleniu w górę niż w dół.",
        "Lotka wychylona w górę generuje większy opór profilowy niż lotka opuszczona, co wspomaga wprowadzanie w zakręt w pożądaną stronę.",
        "Mniejsze ryzyko przeciążenia końcówki skrzydła po stronie ze skrzydłem opadającym.",
        "Prosta realizacja kinematyczna za pomocą niesymetrycznego orczyka lub dźwigni kątowej."
      ],
      cons: [
        "Wymaga starannego trasowania cięgien lub popychaczy w celu zachowania nieliniowej charakterystyki przełożenia.",
        "Przy dużych wychyleniach wzrasta siła na drążku sterowym (wymaga kompensacji rogowej lub klapek odciążających)."
      ],
      galinski_quote: "Ruch różnicowy lotek eliminuje ujemne sprzężenie kierunkowe: lotka unosząca się w górę stawia większy opór niż opuszczana w dół, redukując konieczność kompensacji sterem kierunku.",
      typical_aircraft: "Cessna 172/182, Piper PA-28 Archer, PZL-104 Wilga, SZD-50 Puchacz.",
      recommendation: "Zalecana jako podstawowe rozwiązanie dla wszystkich samolotów szkolnych, turystycznych i motoszybowców."
    },

    frise: {
      id: "frise",
      name: "Lotka Frise ze ściętym noskiem (Aerodynamic Compensation)",
      reference: "Galiński, Rozdz. 17.3.3, Rys. 17.18, str. 198-200",
      delta_a_up_deg: 22,
      delta_a_down_deg: 14,
      typical_pb_2v: 0.085,
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,32 Q80,12 140,30 L140,38 Q80,44 10,35 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="145" cy="34" r="3.5" fill="#0284c7"/>
        <path d="M142,42 L145,34 L190,16 L187,10 L138,30 Z" fill="#bae6fd" stroke="#0284c7" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#0369a1" font-weight="bold">Nosek Frise wystaje w opływ pod skrzydłem</text>
      </svg>`,
      pros: [
        "Dolny zaostrzony nosek lotki wysuwa się pod skrzydło przy jej wychyleniu w górę, tworząc celowy opór aerodynamiczny.",
        "Wyjątkowo skuteczna kompensacja momentu odchylającego bez skomplikowanych układów cięgnowych.",
        "Kompensacja aerodynamiczna zmniejsza siły na drążku sterowym o 30–50%.",
        "Wysoka precyzja i lekkość sterowania poprzecznego."
      ],
      cons: [
        "Większy opór profilowy przy niedokładnym spasowaniu szczeliny noska.",
        "Ryzyko wpadnięcia noska w nadmierną kompensację (nadkompensacja aerodynamiczna) przy bardzo dużych kątach natarcia."
      ],
      galinski_quote: "W lotce Frise oś obrotu jest cofnięta, a nosek wyprofilowany tak, że przy wychyleniu w górę wystaje poniżej dolnego zarysu profilu, generując duży opór hamujący skrzydło po wewnętrznej stronie zakrętu.",
      typical_aircraft: "Supermarine Spitfire, PZL P.11c, Beechcraft Bonanza, samoloty akrobacyjne Extra 300.",
      recommendation: "Idealna dla samolotów akrobacyjnych, szybkich maszyn dyspozycyjnych i zaawansowanych motoszybowców."
    },

    slotted: {
      id: "slotted",
      name: "Lotka szczelinowa (Slotted Aileron)",
      reference: "Galiński, Rozdz. 17.3.4, Rys. 17.20, str. 200-201",
      delta_a_up_deg: 20,
      delta_a_down_deg: 18,
      typical_pb_2v: 0.088,
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,32 Q80,12 136,28 L134,36 Q80,44 10,35 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="144" cy="40" r="3.5" fill="#f59e0b"/>
        <path d="M140,32 L192,48 L188,54 L138,40 Z" fill="#fef3c7" stroke="#d97706" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#b45309" font-weight="bold">Szczelina zasilająca warstwę przyścienną</text>
      </svg>`,
      pros: [
        "Szczelina doprowadza powietrze o wyższej energii z dolnej powierzchni na górną, opóźniając oderwanie strug.",
        "Zachowuje pełną skuteczność sterowania poprzecznego przy bardzo wysokich kątach natarcia (w pobliżu przeciągnięcia).",
        "Wysoki współczynnik zwrotności pb/(2V) w konfiguracji do lądowania."
      ],
      cons: [
        "Wyższy opór szkodliwy w pozycji neutralnej (przepływ przez szczelinę).",
        "Wymaga starannego uszczelnienia krawędzi lub profilowanych fartuchów."
      ],
      galinski_quote: "Szczelina przed lotką działa podobnie jak szczelina klapy jednoszczelinowej: zasilana warstwa przyścienna pozwala na sterowanie przechyleniem nawet wtedy, gdy nasada skrzydła wchodzi w przeciągnięcie.",
      typical_aircraft: "Pilatus PC-6 Porter, Antonow An-2, samoloty STOL krótkiego startu.",
      recommendation: "Zalecana dla samolotów operujących przy niskich prędkościach (STOL, zrzut skoczków, rolnicze)."
    },

    plain: {
      id: "plain",
      name: "Lotka zwykła (Plain Aileron)",
      reference: "Galiński, Rozdz. 17.3.1, str. 196",
      delta_a_up_deg: 20,
      delta_a_down_deg: 18,
      typical_pb_2v: 0.072,
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,32 Q80,12 140,30 L140,38 Q80,44 10,35 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="140" cy="34" r="3.5" fill="#64748b"/>
        <path d="M140,34 L190,50 L186,56 L138,38 Z" fill="#e2e8f0" stroke="#475569" stroke-width="2"/>
        <text x="12" y="16" font-size="9" fill="#334155" font-weight="bold">Zawias liniowy bez szczeliny</text>
      </svg>`,
      pros: [
        "Najprostsza konstrukcja i najniższy koszt wytworzenia.",
        "Brak szczelin noskowych zapewnia minimalny opór profilowy w locie przelotowym.",
        "Idealne przyleganie pokrycia skrzydła (zawias taśmowy lub elastyczny z laminatu)."
      ],
      cons: [
        "Wyraźne zjawisko ujemnego sprzężenia odchylającego (wymaga koordynacji sterem kierunku).",
        "Duże siły na drążku przy większych prędkościach lotu."
      ],
      galinski_quote: "Klasyczna lotka na zawiasach liniowych jest powszechnie stosowana w szybowcach i lekkich samolotach ze względu na czystość aerodynamiczną profilu w położeniu neutralnym.",
      typical_aircraft: "PZL-102 Kos, RWD-8, SZD-9 Bocian, PW-5 Smyk.",
      recommendation: "Zalecana dla prostych konstrukcji ultralekkich i szybowców klubowych."
    },

    flaperon: {
      id: "flaperon",
      name: "Klapolotka (Flaperon ze sprzężeniem)",
      reference: "Galiński, Rozdz. 17.3.8, Rys. 17.28, str. 205-207",
      delta_a_up_deg: 20,
      delta_a_down_deg: 14,
      typical_pb_2v: 0.080,
      svg_icon: `<svg viewBox="0 0 220 70" class="flap-svg">
        <path d="M10,28 Q75,10 132,28 L130,38 Q75,40 10,31 Z" fill="#cbd5e1" stroke="#0f172a" stroke-width="2"/>
        <circle cx="136" cy="33" r="3.5" fill="#7c3aed"/>
        <path d="M136,33 L192,50 L187,56 L134,38 Z" fill="#ddd6fe" stroke="#5b21b6" stroke-width="2"/>
        <path d="M136,33 L192,18" stroke="#7c3aed" stroke-dasharray="3,3" stroke-width="1.5"/>
        <text x="12" y="16" font-size="9" fill="#5b21b6" font-weight="bold">Klapolotka: suma wychylenia klapowego i lotkowego</text>
      </svg>`,
      pros: [
        "Pojedyncza powierzchnia sterowa łączy klapę i lotkę na całej rozpiętości skrzydła.",
        "Maksymalne wykorzystanie powierzchni spływu pociąga za sobą niższą masę płata.",
        "Możliwość wyginania całego spływu w górę (-3° do -5°) do lotu z wysokimi prędkościami przelotowymi."
      ],
      cons: [
        "Wymaga miksera mechanicznego lub elektronicznego sterowania FBW.",
        "Ryzyko przedwczesnego przeciągnięcia końcówki skrzydła przy jednoczesnym wychyleniu klapowym i opuszczeniu lotki."
      ],
      galinski_quote: "Klapolotka wymaga ograniczenia kąta wychylenia w dół na końcówce skrzydła, aby punkt początkowego oderwania strug nie przeniósł się na obszar sterowania poprzecznego.",
      typical_aircraft: "Motoszybowiec AOS-71, Pipistrel Sinus, F-16 Fighting Falcon, Zenith CH-701.",
      recommendation: "Doskonała dla nowoczesnych motoszybowców kompozytowych i samolotów krótkiego startu STOL."
    }
  },

  // 2. MECHANIZACJA KRAWĘDZI NATARCIA - SLOTY I KRUEGERY (Rozdział 16.4, str. 171-182)
  slats: {
    none: {
      id: "none",
      name: "Czysty nos profilu (brak mechanizacji natarcia)",
      reference: "Galiński, Rozdz. 16.4, str. 171",
      delta_cz_max: 0.0,
      alpha_crit_inc_deg: 0,
      pros: [
        "Najmniejsza masa konstrukcji i pełna prostota wykonania kesonu noskowego.",
        "Idealnie gładkie odwzorowanie noska profilu – umożliwia utrzymanie laminarnego opływu i niskiego oporu Cx0.",
        "Cała przestrzeń przed dźwigarem lub w kesonie dostępna na integralne zbiorniki paliwa lub instalację przeciwoblodzeniową."
      ],
      cons: [
        "Standardowy kąt natarcia przeciągnięcia α_kryt (ok. 14–16°).",
        "Brak dodatkowego zabezpieczenia przed oderwaniem strugi na dużych kątach natarcia."
      ],
      galinski_quote: "Sztywne i gładkie pokrycie krawędzi natarcia (np. w kesonie jednoobwodowym rys. 12.16) pozwala na bardzo dobre zachowanie geometrii profilu w najważniejszym z punktu widzenia aerodynamiki miejscu."
    },
    fixed_slot: {
      id: "fixed_slot",
      name: "Slot stały (Fixed Slat - nieruchome przedskrzydło)",
      reference: "Galiński, Rozdz. 16.4.2, Rys. 16.31, str. 175",
      delta_cz_max: 0.45,
      alpha_crit_inc_deg: 7,
      pros: [
        "Całkowity brak części ruchomych, prowadnic i napędów – niezawodność 100% w każdych warunkach.",
        "Przesuwa kąt natarcia przeciągnięcia α_kryt aż do 22–26°, zapewniając niezwykłą odporność na przeciągnięcie i korkociąg.",
        "Proste mocowanie za pomocą stałych wysięgników do żeber siłowych noska (rys. 16.31)."
      ],
      cons: [
        "Stały, wysoki wzrost oporu aerodynamicznego w locie przelotowym – obniża prędkość maksymalną i przelotową o 15–30 km/h!",
        "Zwiększa zużycie paliwa na przelocie (niższa doskonałość K_max).",
        "Wysięgniki muszą przenieść bardzo duże siły podciśnienia działające na slot (wymaga mocnych żeber siłowych)."
      ],
      galinski_quote: "W najprostszym przypadku sloty nie zmieniają swojej pozycji względem krawędzi natarcia (rys. 16.31, np. G-1 Aviation, PZL Wilga). Wewnątrz płata wysięgniki przymocowane są do żeber siłowych, wystarczająco mocnych, by przenieść bardzo duże siły ssące na dźwigar."
    },
    slats_auto: {
      id: "slats_auto",
      name: "Slot ruchomy (wysuwany na szynach lub czworoboku)",
      reference: "Galiński, Rozdz. 16.4.2, Rys. 16.32-16.35, str. 174-178",
      delta_cz_max: 0.60,
      alpha_crit_inc_deg: 9,
      pros: [
        "Wysoki przyrost siły nośnej ΔCz_max (+0.5 do +0.7) oraz wzrost kąta krytycznego α_kryt o 8–10° podczas startu i lądowania.",
        "Po schowaniu w locie przelotowym nie generuje oporu szczelinowego – zachowuje wysoką prędkość przelotową.",
        "Możliwość samoczynnego otwierania pod wpływem podciśnienia na nosku (sloty automatyczne) lub napędu szynowo-rolkowego."
      ],
      cons: [
        "Szyny prowadzące slot muszą chować się w szczelnych puszkach wnikających przez ściankę przedniego dźwigara do wnętrza kesonu (zmniejsza to pojemność integralnych zbiorników paliwa - rys. 16.33!).",
        "W wygiętych w dół puszkach na szyny gromadzi się woda – bez rurek drenażowych woda zamarza na wysokości i blokuje slot!",
        "Bardzo długi i cienki spływ slotu jest zasysany w górę przez podciśnienie (rys. 16.30) – wymaga przekładkowej konstrukcji i zamków dociskających.",
        "Uskok za krawędzią spływu schowanego slotu (> 0.001 mm) całkowicie niszczy przepływ laminarny."
      ],
      galinski_quote: "Ze względu na specyficzny kształt szyn puszki w przednim dźwigarze muszą być zagięte w dół, co prowadzi do gromadzenia wody i korozji. Nieusunięta woda mogłaby zamarznąć, blokując slot – każda puszka musi mieć przewód drenażowy (rys. 16.33)."
    },
    krueger: {
      id: "krueger",
      name: "Klapa Kruegera (wychylana z dolnej powierzchni noska)",
      reference: "Galiński, Rozdz. 16.4.3, Rys. 16.37, str. 178-180",
      delta_cz_max: 0.40,
      alpha_crit_inc_deg: 5,
      pros: [
        "Jedyne rozwiązanie mechanizacji natarcia pozwalające zachować przepływ laminarny na górnej powierzchni skrzydła!",
        "W pozycji schowanej stanowi dolne pokrycie noska – górna powierzchnia skrzydła jest idealnie ciągła i pozbawiona uskoku.",
        "Prostszy i lżejszy mechanizm dźwigniowy lub pantografowy niż w slocie szynowym (nie przebija ścianki przedniego dźwigara)."
      ],
      cons: [
        "Działa skutecznie wyłącznie w swoim skrajnym położeniu otwartym (brak położeń pośrednich).",
        "Mniejsza efektywność aerodynamiczna (mniejszy ΔCz_max) niż konwencjonalny slot szczelinowy.",
        "Powoduje duży przyrost oporu po otwarciu."
      ],
      galinski_quote: "Wszystkie rodzaje slotów mają zasadniczą wadę w postaci uskoku na krawędzi spływu. Zastosowanie slotu w skrzydle laminarnym byłoby możliwe tylko gdyby uskok miał mniej niż 0,001 mm w locie! Chcąc uzyskać opływ laminarny i zwiększyć Cz_max, stosuje się klapę Kruegera (rys. 16.37)."
    }
  },

  // 3. KONFIGURACJA SKRZYDŁA I WĘZŁY KADŁUB-SKRZYDŁO (Rozdziały 13 i 14, str. 99-126)
  wing_config: {
    low: {
      id: "low",
      name: "Dolnopłat wolnonośny (Low-wing)",
      reference: "Galiński, Rozdz. 14, Rys. 14.2, str. 100-101",
      pros: [
        "Dźwigar skrzydła przechodzi pod podłogą kabiny – nie zakłóca przestrzeni ładunkowej ani pasażerskiej w rejonie środka masy!",
        "Krótkie, lekkie i sztywne golenie podwozia głównego chowane bezpośrednio w centropłat lub pod skrzydło.",
        "Struktura centropłata pod kabiną pochłania energię uderzenia podczas awaryjnego lądowania i ułatwia pływanie przy wodowaniu.",
        "Silny wpływ przypowierzchniowy (ekranowania ziemi) ułatwiający łagodne wytrzymanie przy lądowaniu."
      ],
      cons: [
        "Większy opór interferencyjny niż w średniopłacie (wymaga starannego wyprofilowania owiewki przejścia skrzydło-kadłub).",
        "Mniejsza naturalna stateczność poprzeczna – wymaga zastosowania wzniosu konstrukcyjnego skrzydeł (Γ = 4° – 7°).",
        "Gorsza widoczność z kabiny w dół w obszarze skrzydła."
      ],
      galinski_quote: "Zastosowanie konfiguracji dolnopłata (rys. 14.2) pozwala na przeniesienie ogromnych obciążeń gnących przez dźwigarki wewnątrzkadłubowe pod podłogą, bez zakłócania cennej przestrzeni ładunkowej w okolicy środka masy."
    },
    mid: {
      id: "mid",
      name: "Średniopłat (Mid-wing)",
      reference: "Galiński, Rozdz. 14, Rys. 14.1, str. 99-100",
      pros: [
        "Najkorzystniejszy aerodynamicznie układ: minimalny opór interferencyjny (kąt prosty między powierzchnią skrzydła i burtą kadłuba).",
        "Idealna symetria sił aerodynamicznych i masowych – brak niezamierzonych momentów przy figurach akrobacji i manewrach bojowych.",
        "Brak konieczności stosowania dużego wzniosu płata."
      ],
      cons: [
        "Fundamentalny problem konstrukcyjny (Rozdz. 14, str. 99): dźwigarki łączące skrzydła przechodzą przez sam środek kadłuba – dokładnie w okolicy środka ciężkości, gdzie powinien znajdować się zmienny ładunek płatny!",
        "Zastąpienie dźwigarka przelotowego wręgami siłowymi (rys. 14.1b) wymaga bardzo ciężkich i grubych wręg, aby moment gnący nie zdeformował kadłuba.",
        "Utrudnione wsiadanie i załadunek oraz długie podwozie."
      ],
      galinski_quote: "W przypadku układu średniopłata, który jest niezwykle korzystny aerodynamicznie, najcenniejsze miejsce w strukturze kadłuba (w okolicy środka masy) musi być przeznaczone na dźwigarki łączące skrzydła (rys. 14.1a) lub bardzo ciężkie wręgi siłowe (rys. 14.1b)."
    },
    high: {
      id: "high",
      name: "Górnopłat wolnonośny (High-wing)",
      reference: "Galiński, Rozdz. 14, Rys. 14.23, str. 99-115",
      pros: [
        "Całkowicie wolna, nisko położona podłoga kabiny i ładowni – centropłat przebiega w suficie kadłuba.",
        "Naturalna stateczność wahadłowa (środek ciężkości poniżej płata) – samolot samoczynnie wraca do lotu poziomego.",
        "Duży prześwit pod skrzydłami i silnikami – ochrona śmigieł i wlotów przed kamieniami i trawą na lądowiskach polowych.",
        "Wspaniała widoczność w dół dla załogi i pasażerów (idealny do zadań patrolowych i obserwacyjnych)."
      ],
      cons: [
        "Trudne rozmieszczenie podwozia głównego: chowanie w skrzydło wymaga bardzo długich i ciężkich goleni, a chowanie w kadłub daje wąski rozstaw kół i wymaga bąbli przykadłubowych.",
        "Osłabienie górnej części kadłuba dużym wykrojem na keson – w małych samolotach z kabiną pod skrzydłem wymaga zamkniętych profili 'podłokietników' lub słupków (rys. 13.35).",
        "Mniejszy efekt ekranu ziemi przy lądowaniu."
      ],
      galinski_quote: "W górnopłatach z niedzielonym skrzydłem wykrój na keson nad wycięciem kabiny pilota może osłabić kadłub. Rozwiązaniem jest stworzenie zamkniętych obwodów pod kabiną i w przednich słupkach, jak w Cessnie 152 (rys. 13.35)."
    },
    braced_high: {
      id: "braced_high",
      name: "Górnopłat zastrzałowy (Braced High-wing)",
      reference: "Galiński, Rozdz. 14, Rys. 14.6, str. 102",
      pros: [
        "Zastrzał podskrzydłowy przejmuje lwią część momentu gnącego – pozwala zastosować cieńszy profil i znacznie lżejszy dźwigar skrzydła!",
        "Brak konieczności prowadzenia potężnego centropłata przez kadłub – skrzydła mocowane przegubowo do boków wręg lub kratownicy.",
        "Możliwość zastosowania kinematyki składania skrzydeł do tyłu wzdłuż kadłuba wokół wspólnej osi tylnego okucia i zastrzału (jak w RWD-13, rys. 14.6) – ogromna zaleta przy hangarowaniu!"
      ],
      cons: [
        "Znaczny opór szkodliwy zastrzałów i interferencji węzłów (wzrost Cx0 o 0.004–0.007) – nieopłacalny przy prędkościach powyżej 230 km/h.",
        "Zastrzały pracują na rozciąganie w locie normalnym, ale przy przeciążeniach ujemnych (n < 0) oraz podczas twardego lądowania są ściskane i muszą być zabezpieczone przed wyboczeniem!"
      ],
      galinski_quote: "W układzie zastrzałowego górnopłata (rys. 14.6, RWD-13) oś sworznia tylnego okucia dźwigarowego może być współliniowa z osią sworznia mocującego zastrzały do kratownicy. Po wyjęciu przedniego sworznia cały zespół skrzydła i zastrzałów obraca się do tyłu do hangarowania!"
    }
  }
};

/**
 * ENCYKLOPEDIA PARAMETRÓW PROJEKTOWYCH
 * Każdy parametr formularza ma tu szczegółową metrykę dydaktyczną:
 * co oznacza, wzór z BIPOL I, wpływ na projekt oraz typowe wartości.
 */
const PARAMETER_ENCYCLOPEDIA = {
  aileron_type: {
    symbol: "Typ lotki",
    title: "Konstrukcja i Kompensacja Lotek (Projekt P3 / P4)",
    short_desc: "Typ powierzchni sterowania poprzecznego na zewnętrznej części rozpiętości skrzydła.",
    full_definition: "Wybór między lotką różnicową (standard GA), Frise (ze ściętym noskiem kompensacyjnym), szczelinową, zwykłą lub klapolotką (flaperon). Decyduje o sile na drążku, eliminacji adverse yaw oraz wskaźniku zwrotności poprzecznej pb/(2V).",
    formula: "p·b / (2V) = − (C_l,δa / C_l,p) · δa,   wymóg: ≥ 0.07 rad (GA) / ≥ 0.05 rad (motoszybowce)",
    effect_increase: "Lotka różnicowa lub Frise zapobiega oporowi niekorzystnemu i poprawia bezpieczeństwo w zakręcie.",
    typical_ranges: "Cięciwa: ca/c = 18–25% | Rozpiętość: ba/b = 25–35% | Wychylenie: +24° / −12°.",
    galinski_note: "Oderwanie na skrzydle powinno zaczynać się bliżej kadłuba niż wewnętrzna krawędź lotki (η_oderwania < η_lotki, z rozkładu Schrenka) — wtedy lotki działają jeszcze na początku przeciągnięcia."
  },

  flap_span_ratio: {
    symbol: "b_f / b [-]",
    title: "Część Rozpiętości Skrzydła Objęta Klapami (Projekt P3 / P4)",
    short_desc: "Udział rozpiętości krawędzi spływu przeznaczony na klapy wysklepiające (od kadłuba do stacji zewnętrznej klapy).",
    full_definition: "Pozostała część rozpiętości zewnętrznej jest zarezerwowana na lotki sterowania poprzecznego. W samolotach konwencjonalnych bf/b wynosi zazwyczaj 0.55 – 0.70.",
    formula: "b_f/b = η_f,out − η_f,in,   S_flapped/S = (b_f/b) · [c_f,avg / MAC]",
    effect_increase: "Większe bf/b daje wyższy przyrost siły nośnej ΔCz_max do lądowania, lecz pozostawia mniej miejsca na rozpiętość lotek ba/b.",
    typical_ranges: "GA / szkolne: 0.55 – 0.68 | STOL: 0.70 – 0.75 | Klapolotki (flaperon): 0.80 – 0.90.",
    galinski_note: "Rozdział 16.3: Klapy nie powinny sięgać zbyt blisko końcówki skrzydła, aby nie prowokować oderwania strug w rejonie lotek."
  },

  aileron_span_ratio: {
    symbol: "b_a / b [-]",
    title: "Część Rozpiętości Skrzydła Objęta Lotkami (Projekt P3 / P4)",
    short_desc: "Udział rozpiętości krawędzi spływu przeznaczony na lotki sterowania poprzecznego.",
    full_definition: "Odpowiada za zwrotność poprzeczną samolotu. Dla samolotów turystycznych wynosi 0.22 – 0.35 rozpiętości.",
    formula: "b_a/b = η_a,out − η_a,in,   S_a/S ≈ (b_a/b) · (c_a/c)",
    effect_increase: "Większa rozpiętość lotek zwiększa moment przechylający i prędkość kątową przechylenia p, lecz ogranicza rozpiętość klap.",
    typical_ranges: "GA: 0.22 – 0.32 | Akrobacyjne: 0.35 – 0.50 | Szybowce: 0.30 – 0.40.",
    galinski_note: "Rozdział 17.3: Końcówka lotki powinna kończyć się ok. 3–5% przed krawędzią skrzydła (tip clearance), aby uniknąć wpływu wiru brzegowego."
  },

  aircraft_type: {
    symbol: "Klasa statku (EASA)",
    title: "Klasa konstrukcyjno-certyfikacyjna statku powietrznego",
    short_desc: "Określa przeznaczenie statku, współczynniki statystyczne masy pustej Torenbeeka/Roskama (m_e / m_0 = A · m_0^C), charakterystykę napędu oraz wymogi załogowe/bezzałogowe.",
    full_definition: "Klasa statku narzuca bazowe proporcje masowe w bilansie P2 BIPOL oraz właściwe przepisy EASA i polskiego prawa lotniczego (t.j. Dz. U. z 2025 r. poz. 1137). Dostępne klasy: 1) Tłokowy GA (EASA CS-23 L1-L2, CS-VLA, CS-LSA, Annex I Opt-out ULM); 2) Motoszybowiec (EASA CS-22 TMG / Klasa MG • silnik pomocniczy/ciągnący, m/b² ≤ 3.0 kg/m²); 3) Szybowiec (EASA CS-22 / Klasa S • bez napędu, start za wyciągarką/holem); 4) Turbośmigłowy Commuter (EASA CS-23 L3-L4 / Commuter); 5) Odrzutowy Dyspozycyjny (CS-23 High Speed / VLJ / CS-25); 6) Odrzutowy Komunikacyjny (EASA CS-25 Large Aeroplanes); 7) Bezzałogowy Statek Powietrzny EASA UAS (UE 2019/947, CS-LUAS / CS-UAS, bezwzględnie 0 osób na pokładzie).",
    formula: "m₀ = (m_zał + m_płatna) / (1 − m̄_paliwa − m̄_pustego),   gdzie  m̄_pustego = A · m₀^C  (dla UAV: m_zał = 0, m_pax = 0)",
    effect_increase: "Przejście do wyższej klasy podnosi wymagania niezawodnościowe i masę awioniki. Wybór UAV całkowicie eliminuje masę kabiny pasażerskiej i instalacji podtrzymywania życia, a ładunek płatny stanowi wyposażenie zadaniowe (sensory, kamery EO/IR, łącza C2).",
    typical_ranges: "Tłokowy GA: m₀ = 600–3000 kg | Turbośmigłowy Commuter: 4000–12000 kg | Odrzutowy: 4500–80000 kg | UAS: kategoria operacji zależy od ryzyka, nie od progu 600 kg.",
    galinski_note: "Dobór klasy determinuje technologię wykonania: od konstrukcji duralowych i kompozytowych w lekkim GA, przez kratownice ze zdejmowanym pokryciem w rolniczych (Dromader), po struktury skorupowe z integralnymi zbiornikami kesonowymi i kabiną hermetyczną w maszynach komunikacyjnych (Rozdz. 12 i 13)."
  },

  category: {
    symbol: "Certyfikacja EASA / Prawo Lotnicze",
    title: "Specyfikacja certyfikacyjna EASA CS i polskie prawo lotnicze (t.j. Dz. U. z 2025 r. poz. 1137)",
    short_desc: "Określa formalną specyfikację EASA, dopuszczalne przeciążenia manewrowe n_max / n_min na obwiedni V-n (Projekt P6), limity pasażerów oraz wymogi minimalnej załogi.",
    full_definition: "CS 23.2005 obejmuje samoloty do 19 miejsc pasażerskich i MTOM do 8618 kg. Level 1: 0–1 pasażer, Level 2: 2–6, Level 3: 7–9, Level 4: 10–19. Poziom osiągów wymaga granicznych VNO/VMO (KCAS) i MMO; nie wynika z prędkości przelotowej TAS. CS-VLA i CS-LSA mają odrębne ograniczenia masy, miejsc i prędkości przeciągnięcia. Kategorie operacji UAS Open, Specific i Certified zależą od ryzyka i warunków operacji (UE 2019/947), a nie od progu 600 kg. Obciążenia i obwiednia w aplikacji są uproszczonymi założeniami projektowymi; ich obliczenie nie potwierdza certyfikacji.",
    formula: "n_max(CS-23/STANAG) = min(3.8; 2.1 + 24000 / (m₀ [lbs] + 10000)),  n_max(CS-25) = max(2.5; min(3.8; formula)),  n_max(Akro) = +6.0,  n_max(CS-22) = +5.3",
    effect_increase: "Wyższa kategoria przeciążeń (np. Akrobacyjna +6.0g lub CS-22 +5.3g) wymaga grubszych pasów dźwigara i cięższego węzła skrzydło-kadłub, lecz zapewnia bezpieczeństwo manewrowe. Certyfikacja CS-25 wymusza redundancję systemów i min. 2 pilotów.",
    typical_ranges: "CS-23 Normal (L1-L4): +3.8g / -1.52g | Akrobacyjny: +6.0g / -3.0g | CS-22: +5.3g / -2.65g | CS-LSA / ULM: +4.0g / -2.0g | CS-25: +2.5g do +3.8g / -1.0g | UAS: +3.8g / -1.52g.",
    galinski_note: "Pamiętaj (Rozdz. 12.2, str. 32): dodatnie przeciążenia n > 0 ściskają górny pas dźwigara, a ujemne n < 0 — dolny. Ponieważ |n_max| > |n_min|, a pas ściskany może się wyboczyć, górny pas dźwigara ma zwykle większy przekrój od dolnego."
  },

  wingspan_m: {
    symbol: "b [m]",
    title: "Rozpiętość skrzydeł (Wingspan)",
    short_desc: "Odległość od lewej do prawej końcówki płata. Wartość 0 oznacza automatyczne wyliczenie b = √(S · Λ). Wpisz wartość > 0, jeśli temat narzuca wymiar (np. limit hangarowy).",
    full_definition: "Rozpiętość b decyduje o oporze indukowanym (zależnym od rozpiętości obciążenia) oraz o momencie gnącym u nasady skrzydła. W wielu tematach BIPOL I (np. motoszybowce klasy 15 m / 18 m lub samoloty pokładowe) rozpiętość jest sztywno narzucona.",
    formula: "b = √(S · Λ)   ⇔   Λ = b² / S",
    effect_increase: "Większa rozpiętość zmniejsza wiry brzegowe i opór indukowany (poprawia doskonałość K_max i wznoszenie), ale liniowo zwiększa ramię siły nośnej, a więc moment gnący dźwigar i masę skrzydła!",
    typical_ranges: "Samoloty akrobacyjne: 7–9 m | Samoloty lekkie GA: 9.5–12 m | Szybowce i motoszybowce: 15.0 / 18.0 / 20.0 m | Komunikacyjne: 25–36 m (limit ICAO Kod C: 36 m).",
    galinski_note: "Jeśli rozpiętość jest ograniczona wymiarami hangaru lub lotniskowca, konieczne może być zastosowanie mechanizmu składania skrzydeł w żebrze zamykającym (Rozdz. 12.8, rys. 12.60 lub RWD-13 rys. 14.6)."
  },

  wing_config: {
    symbol: "Układ płata",
    title: "Usytuowanie pionowe skrzydła względem kadłuba",
    short_desc: "Wybór między dolnopłatem, średniopłatem, górnopłatem wolnonośnym a górnopłatem zastrzałowym. Decyduje o przejściu dźwigara przez kadłub, długości podwozia i masie skrzydła.",
    full_definition: "Określa sposób połączenia siłowych elementów skrzydła z wręgami kadłuba (Rozdz. 14) oraz charakterystyki interferencji aerodynamicznej i stateczności bocznej.",
    formula: "Opór interferencyjny Cx,int:  Średniopłat (min) < Górnopłat wolnonośny < Dolnopłat < Górnopłat zastrzałowy",
    effect_increase: "Zmiana z dolnopłata na górnopłat uwalnia przestrzeń pod podłogą i poprawia widoczność w dół, ale utrudnia chowanie podwozia głównego. Zastrzał zmniejsza masę skrzydła o ~11%, lecz dodaje opór ΔCx0 ≈ +0.0020.",
    typical_ranges: "Dolnopłat: szkolne, komunikacyjne, akrobacyjne | Górnopłat: STOL, patrolowe, transportowe cargo, ULM | Średniopłat: szybowce, myśliwce, akrobacyjne wyczynowe.",
    galinski_note: "Rozdz. 14 (str. 99): w średniopłacie dźwigary przechodzą przez kadłub na wysokości kabiny, w pobliżu środka masy — zabierają miejsce na załogę lub ładunek."
  },

  aspect_ratio: {
    symbol: "Λ (AR) [-]",
    title: "Wydłużenie skrzydła (Aspect Ratio)",
    short_desc: "Stosunek kwadratu rozpiętości do powierzchni nośnej (Λ = b²/S). Kluczowy parametr określający smukłość płata, opór indukowany i doskonałość K_max.",
    full_definition: "Wydłużenie Λ jest najważniejszym parametrem aerodynamicznym skrzydła w projekcie wstępnym (P3 i P4). Odwrotnie proporcjonalnie kształtuje współczynnik oporu indukowanego k = 1/(π·Λ·e) oraz doskonałość maksymalną K_max.",
    formula: "Λ = b² / S = b / c_śr,   C_xi = C_z² / (π · Λ · e),   K_max = ½ · √(π · Λ · e / C_x0)",
    effect_increase: "Wyższe wydłużenie Λ drastycznie zmniejsza opór indukowany (daje wysokie K_max, małą moc niezbędną do wznoszenia i duży zasięg wg Bregueta), ale zmniejsza cięciwę i wysokość dźwigara, zwiększając masę skrzydła!",
    typical_ranges: "Samoloty bojowe: 2.5–4.5 | Akrobacyjne: 5.5–6.5 | Tłokowe GA: 7.0–9.0 | Turbośmigłowe regionalne: 10–12 | Motoszybowce i UAV MALE: 14–26.",
    galinski_note: "Przy dużym wydłużeniu cięciwy są małe, więc dźwigar jest niski (mała grubość bezwzględna profilu). Skrzydło wychodzi cięższe i wiotkie na skręcanie — rośnie ryzyko rewersu lotek (rys. 16.3) i flatteru."
  },

  taper_ratio: {
    symbol: "η = ct / cr [-]",
    title: "Zbieżność skrzydła (Taper Ratio)",
    short_desc: "Stosunek cięciwy końcowej ct do cięciwy przykadłubowej cr. Pozwala zbliżyć rozkład siły nośnej do idealnej elipsy i odciążyć konstrukcyjnie końcówkę płata.",
    full_definition: "Zbieżność η kształtuje rozkład cięciw wzdłuż rozpiętości (metoda Schrenka w projekcie P3/P4) oraz wielkość i położenie Średniej Cięciwy Aerodynamicznej (ŚDA / MAC).",
    formula: "η = c_t / c_r,   c_r = 2·S / [b·(1 + η)],   ŚDA = (2/3)·c_r·(1 + η + η²) / (1 + η)",
    effect_increase: "Dla η ≈ 0.45 rozkład siły nośnej jest najbliższy eliptycznemu (maksymalny współczynnik Oswalda e) i środek parcia leży bliżej kadłuba (mniejszy moment gnący). Dla η → 1.0 skrzydło jest najtańsze w budowie (identyczne żebra!), ale cięższe.",
    typical_ranges: "Najlepszy kompromis aerodynamiczno-masowy: η = 0.40 – 0.60 | Proste samoloty szkolne/ULM (płat prostokątny): η = 1.0 | Nie zaleca się η < 0.35 (groźba oderwania strugi na końcówkach i utraty skuteczności lotek!).",
    galinski_note: "Mocno zbieżne skrzydło (małe λ, duża cięciwa u nasady) daje więcej miejsca na chowane podwozie przed lub za dźwigarem, bez wycinania kesonu osłabiającego sztywność skrętną (Rozdz. 12.4, rys. 12.33 P-51 Mustang)."
  },

  sweep_quarter_deg: {
    symbol: "χ25% [°]",
    title: "Skos skrzydła w 1/4 cięciwy (Quarter-Chord Sweep)",
    short_desc: "Kąt odchylenia linii 25% cięciw do tyłu. Stosowany w szybkich samolotach (Ma > 0.6) do podniesienia krytycznej liczby Macha lub korekty położenia ŚDA.",
    full_definition: "Skos skrzydła zmniejsza składową prędkości prostopadłą do krawędzi natarcia (V_eff = V · cos χ), opóźniając powstawanie fal uderzeniowych i oporu falowego w samolotach okołodźwiękowych.",
    formula: "tan(χ_0) = tan(χ_25%) + c_r·(1 − η) / (2·b),   Ma_kr(χ) ≈ Ma_kr(0) / cos(χ_25%)",
    effect_increase: "Większy skos pozwala latać z dużymi prędkościami przelotowymi (Vcr > 650 km/h), ale obniża Cz_max, spycha warstwę przyścienną ku końcówkom (przeciągnięcie końcówkowe) i wprowadza dodatkowe skręcanie dźwigara od zginania!",
    typical_ranges: "Samoloty tłokowe i turbośmigłowe (Ma < 0.5): 0° – 3° | Odrzutowe dyspozycyjne (VLJ): 10° – 20° | Komunikacyjne odrzutowe: 24° – 35°.",
    galinski_note: "Skos opóźnia kryzys falowy, bo o oporze falowym decyduje składowa prędkości prostopadła do krawędzi (Ma·cos Λ). Koszt: warstwa przyścienna spływa ku końcówkom, które przeciągają się pierwsze i wywołują wyrywanie nosa w górę (pitch-up). Przeciwdziała się temu skręceniem geometrycznym, zębami lub kierownicami na krawędzi natarcia."
  },

  dihedral_deg: {
    symbol: "Γ [°]",
    title: "Wznios skrzydła (Dihedral Angle)",
    short_desc: "Kąt uniesienia skrzydeł w górę w rzucie z przodu. Zapewnia stateczność poprzeczną samolotu (moment prostujący podczas ślizgu bocznego).",
    full_definition: "Gdy samolot wykonuje ślizg na skrzydło (kąt ślizgu β), skrzydło opuszczone ze wzniosem Γ ma większy efektywny kąt natarcia niż skrzydło podniesione. Powstaje moment przechylający prostujący samolot.",
    formula: "∂C_l / ∂β < 0   (pochodna momentu przechylającego od ślizgu proporcjonalna do −Γ)",
    effect_increase: "Większy wznios poprawia stateczność spiralną i łatwość pilotażu turystycznego, ale zbyt duży wznios utrudnia akrobację i wywołuje kołysanie holenderskie (Dutch roll).",
    typical_ranges: "Akrobacyjne: 0° – 1° | Górnopłaty (mają naturalną stateczność wahadłową): 1° – 2.5° | Dolnopłaty ze skrzydłem prostym: 4° – 6.5° | Dolnopłaty skośne: 3° – 5°.",
    galinski_note: "Wznios efektywny daje nie tylko kąt V: górnopłat zyskuje ok. 1–2° z samego usytuowania skrzydła, dolnopłat podobnie traci, a 10° skosu do tyłu działa jak ok. 1° wzniosu. Dlatego dolnopłaty mają większy kąt wzniosu niż górnopłaty, a skośne skrzydła odrzutowców — mniejszy."
  },

  range_km: {
    symbol: "R [km]",
    title: "Zasięg obliczeniowy samolotu (Design Range)",
    short_desc: "Dystans przelotu z pełnym ładunkiem płatnym (plus 45 min rezerwy nawigacyjnej). Bezpośrednio determinuje ułamek masy paliwa ze wzoru Bregueta (Projekt P2).",
    full_definition: "Zasięg obliczeniowy R wraz z doskonałością aerodynamiczną K i jednostkowym zużyciem paliwa SFC określa ze wzoru całkowego Bregueta, jaką część masy startowej m0 musi stanowić paliwo (m_f / m_0).",
    formula: "Śmigłowy: R = (η_p / (g · c_p)) · K · ln(m₁/m₂)   |   Odrzutowy: R = (V_cr / c_t) · K · ln(m₁/m₂)",
    effect_increase: "Wzrost wymaganego zasięgu wykładniczo zwiększa ułamek paliwa m_f/m_0, co w pętli iteracyjnej silnie powiększa masę startową samolotu m0 i wymaga zbiorników integralnych w kesonie!",
    typical_ranges: "Samoloty szkolne i akrobacyjne: 400–800 km | Samoloty turystyczne i dyspozycyjne GA: 900–1800 km | Regionalne: 1500–2500 km | Dalekiego zasięgu i UAV MALE: 2500–6000 km.",
    galinski_note: "Przy dużym zasięgu konieczne są integralne zbiorniki paliwa w kesonie (Rozdz. 12.3, rys. 12.19). Wymaga to uszczelnienia szwów nitowych, otworów przelewowych w żebrach oraz wzmocnionych wykrojów dostępowych (dublerów - rys. 12.28–12.31)."
  },

  cruise_altitude_m: {
    symbol: "H [m]",
    title: "Wysokość przelotu (Cruise Altitude w atmosferze ISA)",
    short_desc: "Wysokość nad poziomem morza, na której samolot wykonuje przelot. Określa gęstość powietrza ρ(H), temperaturę T(H) i prędkość dźwięku a(H) wg modelu ISA.",
    full_definition: "Wraz ze wzrostem wysokości H spada gęstość powietrza ρ, dzięki czemu przy tej samej prędkości przyrządowej (IAS) samolot leci z wyższą prędkością rzeczywistą (TAS) przy mniejszym oporze aerodynamicznym.",
    formula: "T(H) = 288.15 − 0.0065·H [K],   ρ(H) = 1.225 · (T(H)/288.15)^4.256 [kg/m³]",
    effect_increase: "Lot wyżej pozwala latać szybciej i oszczędniej (szczególnie dla turbopropów i odrzutowców), ale powyżej H = 3000–3500 m wymaga instalacji tlenowej lub ciężkiej kabiny ciśnieniowej z wręgami ciśnieniowymi i zaokrąglonymi oknami!",
    typical_ranges: "Tłokowe bez doładowania (bez kabiny ciśnieniowej): 1500–3000 m | Turbośmigłowe: 5000–7600 m | Odrzutowe: 9000–12000 m.",
    galinski_note: "Uwaga na oblodzenie i ciśnienie! Najgroźniejsze oblodzenie występuje na pułapach 0–5000 m (Rozdz. 16.4.1, str. 171). Z kolei na wysokościach > 4000 m kabina ciśnieniowa wymaga wręg wypukłych i zaokrąglonych narożników okien (lekcja z katastrof DH Comet - Rozdz. 13.3, str. 91)!"
  },

  n_pax: {
    symbol: "n_pax [os.]",
    title: "Liczba pasażerów (Passengers)",
    short_desc: "Liczba miejsc pasażerskich (bez załogi lotniczej). Definiuje masę płatną pasażerską oraz minimalną długość i średnicę kabiny kadłuba.",
    full_definition: "Każdy pasażer wraz z bagażem podręcznym i rejestrowanym wnosi masę jednostkową m_pax (zwykle 95–105 kg wg norm EASA/BIPOL) oraz wymaga odpowiedniej objętości kabiny i liczby rzędów foteli.",
    formula: "m_płatna = n_pax · m_os + m_cargo",
    effect_increase: "Większa liczba pasażerów bezpośrednio zwiększa masę płatną (licznik w równaniu na m0) oraz wymusza szerszy lub dłuższy kadłub (większa powierzchnia omywana = wyższy opór tarcia Cx0).",
    typical_ranges: "Szkolny/Akrobacyjny: 0–1 pasażer (2 miejsca łącznie z pilotem) | Turystyczny GA: 2–3 pasażerów (4 miejsca) | Dyspozycyjny: 4–9 pasażerów | Regionalny: 19–78 pasażerów.",
    galinski_note: "W samolotach 2-miejscowych miejsca w kabinie można ułożyć w tandem (węższy kadłub, mniejszy opór) lub obok siebie (side-by-side: szerszy kadłub, trudniejsze połączenie bagnetowe skrzydeł - Rozdz. 14, rys. 14.37)."
  },

  m_cargo: {
    symbol: "m_cargo [kg]",
    title: "Dodatkowy ładunek cargo / użyteczny (Cargo / Special Payload)",
    short_desc: "Masa ładunku towarowego, chemikaliów (w samolocie rolniczym), wody gaśniczej lub głowicy optoelektronicznej (w UAV) niezależnie od pasażerów.",
    full_definition: "W samolotach transportowych, rolniczych i bezzałogowych stanowi główny składnik masy płatnej. Musi być umieszczony jak najbliżej środka ciężkości (25–30% ŚDA), aby zrzut lub wyładowanie nie rozregulowało wyważenia samolotu!",
    formula: "m₀ = (m_zał + n_pax · m_os + m_cargo) / (1 − m̄_paliwa − m̄_pustego)",
    effect_increase: "Każde dodatkowe 100 kg ładunku cargo podnosi całkowitą masę startową samolotu m0 o około 220–300 kg (współczynnik wzrostu masy wynosi zwykle 2.2 – 3.0).",
    typical_ranges: "Turystyczny: 0–50 kg | Samolot rolniczy / patrolowy: 500–2500 kg | Transportowy: 2000–20000 kg | UAV MALE: 100–400 kg sensorów.",
    galinski_note: "Ładunek zrzucany lub zużywany w locie (chemikalia, woda, desant) zmienia masę w trakcie misji — bilans trzeba liczyć fazami (metoda iteracyjna), a zbiornik lub ładownię umieszcza się blisko środka masy, żeby zrzut nie rozregulował wyważenia (np. zbiornik przed kabiną w PZL M-18 Dromader)."
  },

  n_crew: {
    symbol: "n_zał [os.]",
    title: "Liczba członków załogi (Flight Crew)",
    short_desc: "Liczba pilotów i personelu pokładowego niezbędnego do wykonania lotu (dla UAV wpisz 0).",
    full_definition: "Masa załogi wchodzi do masy stałej operacyjnej. Dla samolotów lekkich CS-23 przyjmuje się 1 pilota, dla samolotów komunikacyjnych CS-25 minimum 2 pilotów + personel pokładowy.",
    formula: "m_zał = n_zał · 90 kg",
    effect_increase: "Zwiększa masę w przedniej części kadłuba (przesuwa środek ciężkości do przodu w stanie bez pasażerów, wymagając odpowiedniego wyważenia w projekcie P6).",
    typical_ranges: "UAV (bezzałogowy): 0 | Samoloty lekkie GA i rolnicze: 1 pilot | Samoloty dyspozycyjne i komunikacyjne: 2–3 osoby załogi.",
    galinski_note: "Minimalną załogę ustala się przy certyfikacji z obciążenia pracą pilotów (CS 25.1523); samoloty komunikacyjne latają z dwoma pilotami. Załoga należy do masy stałej, nie do ładunku płatnego — drugi pilot przy tej samej m₀ odbiera miejsce ładunkowi."
  },

  m_pax: {
    symbol: "m_os [kg]",
    title: "Masa jednostkowa 1 pasażera z bagażem",
    short_desc: "Obliczeniowa masa jednej osoby na pokładzie wraz z jej bagażem (wg wytycznych BIPOL I zazwyczaj 95–105 kg: np. 80 kg pasażer + 20 kg bagaż).",
    full_definition: "Normatywna masa przyjmowana w bilansie masowym P2 oraz w obliczeniach wędrówki środka masy P6.",
    formula: "m_os = m_pasażera + m_bagażu ≈ 80 kg + 20 kg = 100 kg",
    effect_increase: "Zwiększa wymagany udźwig użyteczny oraz moment bezwładności i wędrówkę środka ciężkości przy załadunku kabiny.",
    typical_ranges: "Szybowce/Akrobacyjne (pilot ze spadochronem): 90–100 kg | Lotnictwo ogólne i komunikacyjne z bagażem: 95–105 kg.",
    galinski_note: "W małych samolotach przepisy operacyjne EASA każą liczyć wyższe masy standardowe niż w dużych (np. 104 kg na mężczyznę z bagażem podręcznym przy 1–5 miejscach), bo przy kilku osobach rozrzut mas jest duży. W szybowcach i akrobacji dolicz spadochron."
  },

  cruise_speed_kmh: {
    symbol: "V_cr [km/h]",
    title: "Prędkość przelotowa (Cruise Speed TAS)",
    short_desc: "Wymagana prędkość rzeczywista w locie poziomym na wysokości przelotu H. Wyznacza krzywą wymaganego ciągu/mocy na przelocie w Matching Chart (P2).",
    full_definition: "Prędkość przelotowa Vcr silnie wpływa na wymagane obciążenie mocy (P/W) lub ciągu (T/W), gdyż moc niezbędna do pokonania oporu szkodliwego rośnie z sześcianem prędkości (P_potrz ~ V³)!",
    formula: "(T/W)_cr = (q_cr · C_x0)/(W/S) + k·(W/S)/q_cr,   gdzie  q_cr = ½·ρ(H)·V_cr²",
    effect_increase: "Zwiększenie Vcr o 20% wymaga zwiększenia mocy silnika aż o ok. 73% (1.2³ = 1.728)! Przesuwa też optymalny punkt projektowy na wykresie Matching Chart w stronę większych obciążeń powierzchni W/S.",
    typical_ranges: "ULM i STOL: 130–180 km/h | Tłokowe GA: 190–320 km/h | Turbośmigłowe: 420–600 km/h | Odrzutowe: 680–900 km/h.",
    galinski_note: "Powyżej ok. 250 km/h zwykle opłaca się zrezygnować z zastrzałów i stałego podwozia na rzecz skrzydła wolnonośnego i podwozia chowanego (Rozdz. 12.3 i 12.4) — ich opór rośnie z kwadratem prędkości."
  },

  v_stall_kmh: {
    symbol: "V_s0 [km/h]",
    title: "Maksymalna dopuszczalna prędkość przeciągnięcia w konfiguracji do lądowania",
    short_desc: "Najmniejsza prędkość lotu poziomego z całkowicie wypuszczonymi klapami. Wyznacza pionową linię graniczną maksymalnego obciążenia powierzchni W/S na Matching Chart!",
    full_definition: "Prędkość przeciągnięcia Vs0 jest twardym ograniczeniem bezpieczeństwa (np. przepisy CS-23 wymagają dla samolotów jednosilnikowych Vs0 ≤ 61 węzłów = 113 km/h). Definiuje prędkość podejścia do lądowania V_app = 1.3 · Vs0.",
    formula: "(W/S)_max = ½ · ρ₀ · V_s0² · C_z,max,lnd   ⇔   V_s0 = √[ 2·(W/S) / (ρ₀ · C_z,max,lnd) ]",
    effect_increase: "Wyższa dopuszczalna prędkość Vs0 pozwala zaprojektować znacznie mniejsze i lżejsze skrzydło (większe W/S), ale wydłuża drogę dobiegu (S_lnd ~ V_s0²) i utrudnia operowanie z krótkich lotnisk.",
    typical_ranges: "Samoloty STOL i ULM: 55–75 km/h | Samoloty szkolne i turystyczne GA (limit CS-23): 80–113 km/h | Turbośmigłowe: 130–160 km/h | Komunikacyjne: 180–220 km/h.",
    galinski_note: "Chcesz zmniejszyć prędkość lądowania Vs0 bez powiększania skrzydła? Zastosuj skuteczniejszą mechanizację spływu (klapę Fowlera lub dwuszczelinową) oraz sloty na krawędzi natarcia (Rozdz. 16.3 i 16.4)!"
  },

  takeoff_run_m: {
    symbol: "S_to [m]",
    title: "Wymagana długość drogi rozbiegu (Takeoff Ground Run)",
    short_desc: "Maksymalny dystans rozbiegu na pasie startowym od ruszenia z miejsca do oderwania kół (na poziomie morza ISA). Kształtuje krzywą startu na Matching Chart.",
    full_definition: "Droga rozbiegu zależy od stosunku ciągu do ciężaru (T/W), obciążenia powierzchni nośnej (W/S) oraz współczynnika siły nośnej w konfiguracji startowej Cz_max_to.",
    formula: "S_to = 1.21 · (W/S) / [ ρ₀ · g · C_z,max,to · (T/W − μ) ]",
    effect_increase: "Dłuższy dopuszczalny rozbieg pozwala zastosować słabszy, lżejszy silnik i mniejsze skrzydło. Wymóg bardzo krótkiego rozbiegu (STOL < 200 m) wymusza dużą moc silnika i dużą powierzchnię nośną.",
    typical_ranges: "STOL (Wilga, Zenith CH 701): 30–150 m | Samoloty lekkie GA na lotniska trawiaste: 210–400 m | Dyspozycyjne i regionalne: 600–1100 m | Komunikacyjne: 1400–2400 m.",
    galinski_note: "Rozbieg skracają przede wszystkim mniejsze obciążenie powierzchni W/S, większy stosunek mocy (ciągu) do masy i wyższe Cz,max do startu. Klapy do startu wychyla się mniej niż do lądowania (zwykle 10–20°), bo duże wychylenie dodaje opór, który wydłuża rozbieg i pogarsza wznoszenie."
  },

  climb_rate_ms: {
    symbol: "w_y [m/s]",
    title: "Wymagana maksymalna prędkość wznoszenia przy ziemi (Rate of Climb MSL)",
    short_desc: "Pionowa prędkość wznoszenia na poziomie morza (w_y = dH/dt). Wyznacza wymagany nadmiar mocy ponad moc niezbędną do lotu poziomego (Projekt P5).",
    full_definition: "Zgodnie z zasadami Mechaniki Lotu I prędkość wznoszenia w_y wynika bezpośrednio z nadmiaru mocy rozporządzalnej (P_rozp - P_potrz) podzielonego przez ciężar samolotu W = m0·g.",
    formula: "w_y = (P_rozp − P_potrz) / W = V · (T/W − 1/K)",
    effect_increase: "Wyższe wymagane wznoszenie w_y podnosi krzywą wznoszenia na Matching Chart, wymagając mocniejszego silnika lub większego wydłużenia skrzydła Λ.",
    typical_ranges: "Motoszybowce i ULM: 2.5–4.0 m/s | Samoloty szkolne i turystyczne GA: 4.0–6.5 m/s | Samoloty akrobacyjne i turbośmigłowe: 8.0–18.0 m/s | Odrzutowe: 12–30 m/s.",
    galinski_note: "Dla uzyskania wysokiego wznoszenia przy małej mocy silnika kluczowa jest niska masa konstrukcji oraz czystość aerodynamiczna szwów nitowych i owiewek."
  },

  engine_type: {
    symbol: "Typ napędu",
    title: "Rodzaj zespołu napędowego (Śmigłowy vs Odrzutowy)",
    short_desc: "Określa model charakterystyk ciągu: dla śmigłowych stała moc rozporządzalna P_rozp = η_p·P₀ (ciąg maleje z prędkością T = η_p·P₀/V), dla odrzutowych przybliżenie stałego ciągu T ≈ const.",
    full_definition: "Fundamentalne rozróżnienie w Mechanice Lotu I (`BIPOL_1_wzory.pdf`) i BIPOL I: w samolotach śmigłowych wymiarujemy obciążenie mocy P/W [W/N], natomiast w samolotach odrzutowych obciążenie ciągu T/W [-].",
    formula: "Śmigłowy: T(V) = η_p · P₀ / V   |   Odrzutowy: T(H) ≈ T₀ · σ(H)^0.8",
    effect_increase: "Napęd śmigłowy daje znacznie wyższą sprawność propulsywną przy małych i średnich prędkościach (krótki rozbieg, małe zużycie paliwa), natomiast napęd odrzutowy pozwala latać z prędkościami Ma = 0.65–0.85 na dużych pułapach.",
    typical_ranges: "Śmigłowy (tłokowy/elektryczny): V < 400 km/h | Śmigłowy (turboprop): V = 350–620 km/h | Odrzutowy (turbofan): V > 600 km/h.",
    galinski_note: "Śmigło traci sprawność, gdy końcówki łopat zbliżają się do prędkości dźwięku, a turbowentylatorowy silnik jest nieoszczędny przy małej prędkości — stąd granica ok. 600–700 km/h między napędem turbośmigłowym a odrzutowym."
  },

  engine_location: {
    symbol: "Układ silnika",
    title: "Rozmieszczenie zespołu napędowego na płatowcu",
    short_desc: "Określa położenie środka masy silnika w bilansie wyważenia P6, położenie skrzydła na kadłubie oraz ramię usterzenia L_H / L_f (wg T. Corke / Usterzenie_wymiary.pdf).",
    full_definition: "Silnik jest najcięższym skupionym elementem samolotu. Jego lokalizacja decyduje o położeniu skrzydła względem kadłuba (aby środek masy wypadł w ok. 24–28% ŚDA) oraz o ramieniu usterzenia (0.58 L_f dla silnika w nosie, 0.53 L_f na skrzydle, 0.47 L_f z tyłu).",
    formula: "x_ŚM = (∑ m_i · x_i) / (∑ m_i),   L_H / L_f ∈ [0.47 (tył), 0.53 (skrzydło), 0.58 (dziób)]",
    effect_increase: "Przeniesienie silnika z nosa na tył kadłuba (układ pchający / gondole tylne) wymaga przesunięcia skrzydła do tyłu kadłuba (ok. 46% L_f) w celu zachowania stateczności podłużnej!",
    typical_ranges: "Dziób kadłuba: klasyczne 1-silnikowe GA | Skrzydła: 2-silnikowe transportowe i komunikacyjne (odciążają skrzydło od momentu gnącego w locie!) | Tył kadłuba: odrzutowce biznesowe VLJ, UAV MALE.",
    galinski_note: "W motoszybowcach z silnikiem chowanym w kadłubie (np. AOS-71 - Rozdz. 13.3, rys. 13.37–13.39) ogromny wykrój na komorę silnika musi być wzmocniony dodatkowymi ściankami tworzącymi zamknięty przekrój pod komorą napędową!"
  },

  sfc: {
    symbol: "SFC",
    title: "Jednostkowe zużycie paliwa (Specific Fuel Consumption)",
    short_desc: "Ilość paliwa spalana w ciągu godziny na jednostkę mocy [g/(kW·h)] (dla śmigłowych) lub na jednostkę ciągu [1/h] (dla odrzutowych).",
    full_definition: "Parametr termodynamicznej sprawności silnika wchodzący wprost do wykładnika we wzorze całkowym Bregueta na zasięg i długotrwałość lotu.",
    formula: "Śmigłowy: c_p [g/(kW·h)]   |   Odrzutowy: c_j [1/h]",
    effect_increase: "Wyższe jednostkowe zużycie paliwa zwiększa wymaganą masę paliwa m_f na misję i w pętli iteracyjnej podnosi masę startową samolotu m0.",
    typical_ranges: "Tłokowe benzynowe (Rotax/Lycoming): 230–290 g/kWh | Tłokowe Diesel: 190–215 g/kWh | Małe turbośmigłowe (PT6A): 330–390 g/kWh | Regionalne turbośmigłowe (PW127): 280–300 g/kWh | Turbowentylatorowe: 0,50–0,80 1/h (małe silniki biznesowe bliżej 0,7–0,8).",
    galinski_note: "Mniejsze zużycie paliwa pozwala zmniejszyć objętość zbiorników i zrezygnować ze zbiorników kadłubowych na rzecz bezpieczniejszych zbiorników w skrzydle."
  },

  prop_efficiency: {
    symbol: "η_p [-]",
    title: "Sprawność śmigła w locie przelotowym (Propeller Efficiency)",
    short_desc: "Stosunek mocy użytecznej (ciąg × prędkość: T·V) do mocy na wale silnika P. Określa, jaka część mocy silnika zamieniana jest na użyteczną pracę ciągu.",
    full_definition: "Sprawność śmigła zależy od posuwu względnego J = V/(n·D) oraz zastosowania mechanizmu stałych obrotów (constant-speed / zmienny skok).",
    formula: "η_p = (T · V) / P_wału,   P_rozp = η_p · P_wału",
    effect_increase: "Wyższa sprawność śmigła (np. śmigło przestawialne w locie zamiast stałego) zwiększa prędkość wznoszenia wy_max, prędkość maksymalną V_max i zmniejsza zużycie paliwa na przelocie.",
    typical_ranges: "Śmigło o stałym skoku (drewniane/kompozytowe): 0.72 – 0.78 | Śmigło przestawialne Constant-Speed: 0.80 – 0.86.",
    galinski_note: "Śmigło stałego skoku ma najwyższą sprawność tylko w wąskim zakresie prędkości: skok dobrany do przelotu pogarsza start i wznoszenie, a dobrany do wznoszenia obniża prędkość przelotową. Śmigło przestawialne (constant-speed) utrzymuje η_p ≈ 0,8 od wznoszenia po przelot, kosztem masy i złożoności piasty."
  },

  flap_type: {
    symbol: "Mechanizacja spływu (Klapy)",
    title: "Typ klapy zaskrzydłowej na krawędzi spływu (Rozdz. 16.3 prof. Galińskiego)",
    short_desc: "Wybór konstrukcji klapy decyduje o przyroście maksymalnego współczynnika siły nośnej ΔCz_max, oporze przy lądowaniu ΔCx0 oraz masie i złożoności mechanizmu.",
    full_definition: "Klapy zaskrzydłowe zwiększają wysklepienie profilu (a klapy Fowlera również powierzchnię nośną S), pozwalając pogodzić dużą prędkość przelotową (małe skrzydło o dużym W/S) z niską i bezpieczną prędkością lądowania Vs0.",
    formula: "C_z,max,lnd = C_z,max,clean + ΔC_z,klapy + ΔC_z,sloty",
    effect_increase: "Przejście od klapy zwykłej (+0.55) przez jednoszczelinową (+1.15) do klapy Fowlera (+1.50) lub dwuszczelinowej (+1.85) pozwala znacząco zmniejszyć wymaganą powierzchnię skrzydła S, lecz zwiększa masę mechanizacji i ujemny moment pochylający.",
    typical_ranges: "Zwykła: ΔCz +0.55 | Krokodylowa: +0.75 | Junkersa: +1.05 | Jednoszczelinowa: +1.15 | Fowlera: +1.50 | Dwuszczelinowa: +1.85.",
    galinski_note: "Zobacz szczegółową kartę Plusów i Minusów oraz przekrój kinematyczny bezpośrednio pod selektorem klapy!"
  },

  slat_type: {
    symbol: "Mechanizacja natarcia (Sloty)",
    title: "Mechanizacja przedniej krawędzi natarcia skrzydła (Rozdz. 16.4 prof. Galińskiego)",
    short_desc: "Przedskrzydła (sloty) i klapy Kruegera opóźniają oderwanie strugi na dużych kątach natarcia, zwiększając krytyczny kąt natarcia α_kryt o 5°–9°.",
    full_definition: "Szczelina na nosku profilu kieruje wysokoenergetyczną strugę powietrza na górną powierzchnię skrzydła, zapobiegając oderwaniu warstwy przyściennej na dużych kątach natarcia (szczególnie w samolotach STOL i komunikacyjnych).",
    formula: "Δα_kryt ≈ +5° do +9°,   ΔC_z,max,slot ≈ +0.40 do +0.60",
    effect_increase: "Dodanie slotu podnosi całkowity Cz_max_lnd i zabezpiecza przed korkociągiem, ale slot stały zwiększa opór przelotowy Cx0, a slot ruchomy wymaga puszek na szyny z drenażem wody w przednim dźwigarze.",
    typical_ranges: "Czysty nos: ΔCz 0.0 | Klapa Kruegera (skrzydła laminarne): +0.40 | Slot stały (STOL): +0.45 | Slot ruchomy szynowy: +0.60.",
    galinski_note: "Rozdz. 16.4.2 (rys. 16.33): Szyny ruchomego slotu wnikają w przedni dźwigar – puszki osłonowe muszą mieć rurki drenażowe, inaczej zamarzająca woda zablokuje slot na wysokości!"
  },

  cx0: {
    symbol: "C_x0 [-]",
    title: "Współczynnik oporu szkodliwego (Zero-Lift Drag Coefficient)",
    short_desc: "Współczynnik oporu samolotu przy zerowej sile nośnej (opór tarcia pokrycia, ciśnieniowy kształtu, interferencyjny, chłodzenia i podwozia) odniesiony do powierzchni skrzydła S.",
    full_definition: "Podstawowy składnik biegunowej kwadratowej C_x = C_x0 + k·C_z² (Projekt P4, wzór 6 w BIPOL_1_wzory.pdf). Decyduje o prędkości maksymalnej samolotu V_max oraz o doskonałości maksymalnej K_max.",
    formula: "C_x(C_z) = C_x0 + C_z² / (π · Λ · e),   K_max = ½ · √(π · Λ · e / C_x0)",
    effect_increase: "Wzrost Cx0 (np. przez stałe podwozie, zastrzały, wystające nity czy pofalowane pokrycie) drastycznie obniża doskonałość K_max, zwiększa zużycie paliwa i zmniejsza prędkość maksymalną V_max!",
    typical_ranges: "Szybowce: 0,008–0,012 | Motoszybowce: 0,014–0,020 | Chowane podwozie: 0,020–0,025 | Stałe podwozie i zastrzały: 0,027–0,036 | Odrzutowe komunikacyjne: 0,015–0,020.",
    galinski_note: "Gęste nitowanie profili omegowych i brak połączeń kompensacyjnych powodują pofalowanie pokrycia (Rozdz. 12.6, rys. 12.46 Boeing B-29), które niszczy opływ laminarny i podnosi Cx0!"
  },

  oswald_e: {
    symbol: "e [-]",
    title: "Współczynnik sprawności płata Oswalda (Span Efficiency Factor)",
    short_desc: "Określa, jak bardzo rzeczywisty rozkład siły nośnej wzdłuż rozpiętości odbiega od idealnego rozkładu eliptycznego (dla którego e = 1.0).",
    full_definition: "Uwzględnia przyrost oporu indukowanego wynikający z nieeliptycznego obrysu skrzydła, zakłócenia rozkładu siły nośnej przez kadłub i gondole silnikowe oraz wzrost oporu profilowego z kątem natarcia.",
    formula: "k = 1 / (π · Λ · e),   C_xi = k · C_z²",
    effect_increase: "Wyższy współczynnik e (uzyskiwany przez zbieżność η ≈ 0.45, winglety i czyste przejście skrzydło-kadłub) obniża opór indukowany na dużych kątach natarcia (podczas wznoszenia, zakrętu i krążenia).",
    typical_ranges: "Skrzydło prostokątne z zastrzałami: 0.72 – 0.77 | Skrzydło trapezowe dolnopłata/górnopłata: 0.78 – 0.84 | Skrzydło kompozytowe z wingletami: 0.85 – 0.90.",
    galinski_note: "Współczynnik e obniżają kadłub, gondole, nieeliptyczny rozkład siły nośnej i opór lepki rosnący z Cz. Szacuj go ze wzorów statystycznych (np. Raymer dla skrzydeł prostych: e ≈ 1,78·(1 − 0,045·Λ^0,68) − 0,64); winglety dają zwykle kilka procent."
  },

  cz_max_clean: {
    symbol: "C_z,max (gładki) [-]",
    title: "Maksymalny współczynnik siły nośnej w konfiguracji gładkiej (Clean CL_max)",
    short_desc: "Maksymalna siła nośna skrzydła ze schowanymi klapami i slotami tuż przed przeciągnięciem. Wyznacza prędkość przeciągnięcia w konfiguracji czystej Vs1 oraz prędkość manewrową VA na obwiedni V-n.",
    full_definition: "Zależy od wybranego profilu lotniczego (np. NACA 2412, NACA 23015, Wortmann FX, NASA LS), liczby Reynoldsa oraz skosu skrzydła.",
    formula: "V_s1 = √[ 2·(W/S) / (ρ₀ · C_z,max,clean) ],   V_A = V_s1 · √(n_max)",
    effect_increase: "Wyższy Cz_max_clean obniża prędkość przeciągnięcia bez klap Vs1, zmniejsza prędkość manewrową VA i zacieśnia minimalny promień zakrętu r_min.",
    typical_ranges: "Profile symetryczne (akrobacyjne): 1.15 – 1.30 | Klasyczne profile NACA 4- i 5-cyfrowe: 1.35 – 1.55 | Nowoczesne profile laminarne GA/szybowcowe: 1.50 – 1.70.",
    galinski_note: "Wiercenie nitów lub szlifowanie wypływki kleju dokładnie na nosku profilu kompozytowego (Rozdz. 18.3, rys. 18.12) losowo deformuje promień noska i potrafi obniżyć Cz_max_clean o kilkanaście procent!"
  },

  cz_max_lnd: {
    symbol: "C_z,max,lnd [-]",
    title: "Maksymalny współczynnik siły nośnej do lądowania (Landing CL_max)",
    short_desc: "Maksymalna siła nośna przy pełnym wychyleniu klap (i slotów). Bezpośrednio decyduje o tym, jak małe może być skrzydło (W/S) przy zadanej prędkości lądowania Vs0!",
    full_definition: "Wynika z sumy Cz_max skrzydła gładkiego oraz przyrostu ΔCz_max od wybranej mechanizacji krawędzi spływu (klapy) i krawędzi natarcia (sloty/Kruegery).",
    formula: "C_z,max,lnd ≈ C_z,max,clean + ΔC_z,klapy + ΔC_z,sloty,   (W/S)_max = ½ · ρ₀ · V_s0² · C_z,max,lnd",
    effect_increase: "Wyższy Cz_max_lnd przesuwa granicę przeciągnięcia na wykresie Matching Chart w prawo, pozwalając zmniejszyć powierzchnię nośną S i masę skrzydła!",
    typical_ranges: "Klapa zwykła: 1.80 – 2.00 | Klapa krokodylowa: 2.00 – 2.20 | Klapa jednoszczelinowa: 2.20 – 2.55 | Klapa Fowlera: 2.55 – 2.90 | Klapa dwuszczelinowa + sloty: 2.85 – 3.45.",
    galinski_note: "Użyj selektora 'Wybór Klapy' i 'Mechanizacja natarcia' powyżej, aby automatycznie dobrać realistyczną wartość Cz_max_lnd i poznać konstrukcyjne plusy i minusy wybranego rozwiązania!"
  },

  // Dodatkowe wskaźniki wynikowe KPI (używane na kartach wyników u góry ekranu)
  kpi_m0: {
    symbol: "m₀ (MTOW) [kg]",
    title: "Maksymalna Masa Startowa Samolotu (Maximum Takeoff Weight - Projekt P2)",
    short_desc: "Całkowita masa samolotu gotowego do startu: suma masy pustej wyposażonej (OEW), paliwa całkowitego na misję z rezerwą oraz załogi i ładunku płatnego.",
    full_definition: "Wyznaczana w pętli iteracyjnej (10–25 iteracji), ponieważ udział masy pustej m_e/m_0 zależy nieliniowo od samej masy startowej m_0, a ułamek paliwa zależy od doskonałości K_max.",
    formula: "m₀ = (m_zał + m_płatna) / (1 − m̄_paliwa − A · m₀^C)",
    effect_increase: "Mniejsza masa m₀ oznacza niższe koszty zakupu i eksploatacji, mniejsze skrzydło i słabszy silnik.",
    typical_ranges: "ULM: ≤ 472.5 / 600 kg | Szkolny 2-os.: 620–850 kg | Turystyczny 4-os.: 1100–1500 kg | Regionalny: 16000–23000 kg.",
    galinski_note: "Każdy zbędny kilogram masy konstrukcji obrasta w kolejne kilogramy paliwa, skrzydła i napędu (współczynnik przyrostu masy wynosi 2.2 – 3.5)."
  },

  kpi_wing_s: {
    symbol: "S [m²]",
    title: "Powierzchnia Nośna Skrzydła (Wing Reference Area - Projekt P2/P3)",
    short_desc: "Powierzchnia rzutu płata na płaszczyznę poziomą (wraz z częścią podkadłubową). Wynika z ciężaru startowego W = m₀·g oraz wybranego na Matching Chart obciążenia powierzchni W/S.",
    full_definition: "Mniejsza powierzchnia S (większe obciążenie W/S) zmniejsza opór tarcia na przelocie i wrażliwość na podmuchy, ale zwiększa prędkość lądowania Vs0, o ile nie zastosujemy skutecznych klap.",
    formula: "S = (m₀ · g) / (W/S)_projektowe",
    effect_increase: "Większa powierzchnia S ułatwia krótki start i lądowanie (STOL), lecz zwiększa masę skrzydła i opór szkodliwy w przelocie.",
    typical_ranges: "ULM: 9,5–13 m² | Cessna 172: 16,2 m² | King Air 350: 28,8 m² | ATR 42: 54,5 m².",
    galinski_note: "Na rysunku zestawieniowym 3-rzutowym (ZPK CAD1) powierzchnia S obejmuje trapez przedłużony do płaszczyzny symetrii kadłuba."
  },

  kpi_wingspan: {
    symbol: "b [m]",
    title: "Rozpiętość Skrzydła (Wingspan - Projekt P3)",
    short_desc: "Całkowita szerokość samolotu od lewej do prawej końcówki skrzydła (podawana w milimetrach na rysunku CAD wg PN-EN ISO 129).",
    full_definition: "Wyliczana ze wzoru b = √(S · Λ) lub narzucona bezpośrednio przez projektanta (np. klasa 15 m / 18 m).",
    formula: "b = √(S · Λ),   ŚDA = (2/3)·c_r·(1 + η + η²)/(1 + η)",
    effect_increase: "Większa rozpiętość obniża opór indukowany C_xi, ale zwiększa moment gnący u nasady skrzydła.",
    typical_ranges: "GA 2–4 os.: 8.5–11.5 m | Motoszybowce: 15–18 m | Komunikacyjne regionalne: 24–28 m.",
    galinski_note: "Na rysunku wykonawczym i zestawieniowym rozpiętość b jest głównym wymiarem gabarytowym nanoszonym w rzucie z góry i z przodu."
  },

  kpi_wy_max: {
    symbol: "w_y,max [m/s]",
    title: "Maksymalna Prędkość Wznoszenia przy Ziemi (Max Rate of Climb - Projekt P5)",
    short_desc: "Największa pionowa prędkość wznoszenia na poziomie morza (H = 0 m ISA), osiągana przy prędkości ekonomicznej V_wy,max.",
    full_definition: "Wynika z maksymalnego nadmiaru mocy rozporządzalnej nad mocą niezbędną do lotu poziomego (wzory 54–58 w BIPOL_1_wzory.pdf).",
    formula: "w_y,max = max [ (P_rozp(V) − D(V)·V) / (m₀·g) ]",
    effect_increase: "Wyższe w_y,max zapewnia bezpieczne przewyższenie przeszkód po starcie oraz wysoki pułap praktyczny H_prakt.",
    typical_ranges: "Motoszybowce: 3–4.5 m/s | Tłokowe GA: 4.5–7.5 m/s | Turboprop / Jet: 10–25 m/s.",
    galinski_note: "Pułap praktyczny samolotu definiuje się jako wysokość H, na której maksymalna prędkość wznoszenia spada do w_y,max(H) = 0.5 m/s."
  },

  kpi_vs0: {
    symbol: "V_s0 [km/h]",
    title: "Prędkość Przeciągnięcia w Konfiguracji do Lądowania (Landing Stall Speed - Projekt P5)",
    short_desc: "Minimalna prędkość lotu z wypuszczonymi klapami i podwoziem. Prędkość podejścia do lądowania wynosi V_app = 1.3 · V_s0.",
    full_definition: "Bezpośrednio weryfikuje spełnienie wymagań certyfikacyjnych (np. CS-23 wymaga V_s0 ≤ 61 kt = 113 km/h dla samolotów jednosilnikowych).",
    formula: "V_s0 = √[ 2·(W/S) / (ρ₀ · C_z,max,lnd) ]",
    effect_increase: "Niższa prędkość Vs0 skraca dobieg po przyziemieniu (S_lnd ~ V_app²) i podnosi bezpieczeństwo lądowania awaryjnego.",
    typical_ranges: "STOL: 60–75 km/h | GA: 80–105 km/h | Regionalne: 135–175 km/h.",
    galinski_note: "Klapa Fowlera lub dwuszczelinowa zamiast zwykłej obniża Vs0 o ok. 10–15 % przy tym samym skrzydle, bo Vs0 ∝ 1/√Cz,max."
  },

  kpi_sm: {
    symbol: "K_n [% ŚDA]",
    title: "Zapas Stateczności Statycznej Podłużnej (Static Margin - Projekt P6)",
    short_desc: "Odległość między punktem neutralnym płatowca x_N a skrajnym tylnym położeniem środka masy x_ŚM,max wyrażona w procentach Średniej Cięciwy Aerodynamicznej (ŚDA / MAC).",
    full_definition: "Warunek konieczny naturalnej stateczności podłużnej samolotu (Mechanika Lotu I - Projekt 6): punkt neutralny x_N musi leżeć za środkiem masy (K_n ≥ 5% ŚDA).",
    formula: "K_n = (x_N − x_ŚM,tylne) / ŚDA · 100%,   gdzie  x̄_N = x̄_ac,wbn + η_H · V_H · (a_H/a_W)·(1 − dε/dα)",
    effect_increase: "Zapas K_n w przedziale 8% – 18% ŚDA gwarantuje stateczny i przyjemny pilotaż. Gdy K_n < 5%, samolot staje się niestateczny (wymaga FBW); gdy K_n > 25%, samolot jest zbyt 'ciężki na ster wysokości' przy wyrównaniu do lądowania.",
    typical_ranges: "Samoloty szkolne i turystyczne: 10% – 18% ŚDA | Samoloty komunikacyjne: 7% – 15% ŚDA | Wymóg minimalny BIPOL I: K_n ≥ 5.0% ŚDA.",
    galinski_note: "Za mały zapas stateczności: przesuń skrzydło do tyłu względem środka masy albo powiększ usterzenie poziome. Program sam zwiększa V_H do zapasu 5 % ŚDA, chyba że zablokujesz V_H."
  }
};

