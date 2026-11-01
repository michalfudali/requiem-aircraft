"""Pochodzenie danych w sprawozdaniu, odwołania do rysunków, tabel i wzorów oraz spis literatury.

Każda dana wejściowa arkusza (``kind == 'given'``) ma w sprawozdaniu jednoznaczne pochodzenie:
wymaganie tematu, założenie początkowe, warunek brzegowy, przepisy budowy, odczyt z wykresu
zamieszczonego w sprawozdaniu, dane z literatury albo wynik wcześniejszego obliczenia.

Teksty mogą zawierać znaczniki:
    {fig:id}  — „(rys. N)” dla <figure id="fig-id">,
    {tab:id}  — „(tab. N)” dla tabeli z id="tab-id",
    {eq:klucz} — „, wzór (N)” dla pozycji arkusza id="q-klucz",
    {lit:id}  — „[N]” — pozycja spisu literatury numerowana w kolejności pierwszego cytowania.
Numery nadaje ``number_references`` po złożeniu całego dokumentu, w tej samej kolejności co
liczniki CSS (caption, figure, .equation) i pola SEQ eksportu DOCX. Odwołanie do elementu, którego
nie ma w dokumencie (np. raport jednej części), znika razem z nawiasem.
"""
import html as _html
import re

from markupsafe import Markup, escape

# ---------------------------------------------------------------------------------------------
# Literatura (kolejność numerów wynika z kolejności cytowania w dokumencie)
# ---------------------------------------------------------------------------------------------
LITERATURE = {
    'galinski_aw': 'Galiński C.: <em>Analizy wstępne</em>. Materiały pomocnicze do projektowania samolotów, '
                   'Politechnika Warszawska, Wydział MEiL, Zakład Samolotów i Śmigłowców, Warszawa.',
    'galinski_wz': 'Galiński C., Goetzendorf-Grabowski T.: <em>Wyprowadzenie wzorów do analiz wstępnych</em>. '
                   'Materiały pomocnicze, Politechnika Warszawska, Wydział MEiL, Warszawa.',
    'galinski_sw': 'Galiński C.: <em>Studium wykonalności</em>. Materiały pomocnicze do projektowania samolotów, '
                   'Politechnika Warszawska, Wydział MEiL, Warszawa.',
    'grabowski_am': 'Goetzendorf-Grabowski T., Galiński C.: <em>Analiza masowa</em>. Materiały pomocnicze do '
                    'projektowania samolotów, Politechnika Warszawska, Wydział MEiL, Warszawa 2010.',
    'paturski': 'Paturski Z.: <em>Przewodnik po projektach z Mechaniki Lotu</em>, wyd. 4.2. Politechnika '
                'Warszawska, Wydział MEiL, Zakład Mechaniki, Warszawa.',
    'raymer': 'Raymer D. P.: <em>Aircraft Design: A Conceptual Approach</em>. AIAA Education Series, Reston.',
    'corke': 'Corke T. C.: <em>Design of Aircraft</em>. Prentice Hall, Upper Saddle River 2003.',
    'danilecki': 'Danilecki S.: <em>Konstruowanie samolotów. Wybrane zagadnienia</em>. Oficyna Wydawnicza '
                 'Politechniki Wrocławskiej, Wrocław.',
    'abbott': 'Abbott I. H., von Doenhoff A. E.: <em>Theory of Wing Sections</em>. Dover Publications, New York 1959.',
    'mason': 'Mason W. H.: <em>Configuration Aerodynamics</em>, rozdz. 7. Virginia Tech, Blacksburg.',
    'cs23': 'EASA: <em>Certification Specifications for Normal, Utility, Aerobatic and Commuter Category '
            'Aeroplanes CS-23</em>, Amendment 4, 2015.',
    'cs22': 'EASA: <em>Certification Specifications for Sailplanes and Powered Sailplanes CS-22</em>, Amendment 3.',
    'cs25': 'EASA: <em>Certification Specifications for Large Aeroplanes CS-25</em>.',
    'stanag': 'NATO: <em>STANAG 4671 — Unmanned Aerial Vehicles Systems Airworthiness Requirements (USAR)</em>.',
    'isa': 'ISO 2533:1975 <em>Standard Atmosphere</em> (atmosfera wzorcowa ISA).',
}

CATEGORY = {'req': 'Wymaganie tematu', 'ass': 'Założenie początkowe', 'bc': 'Warunek brzegowy',
            'reg': 'Przepisy budowy', 'chart': 'Odczyt z wykresu', 'lit': 'Dane z literatury',
            'calc': 'Wynik obliczeń', 'const': 'Stała fizyczna'}
# Kategorie zestawiane w tabeli wymagań i założeń na początku sprawozdania.
ASSUMED = ('req', 'ass', 'bc', 'reg')

_ISA = ('const', 'atmosfera wzorcowa ISA {lit:isa}')
_MISSION = ('ass', 'przyjęto w profilu misji {fig:mission}')
_PHASES = ('calc', 'z bilansu mas w fazach misji {tab:mission-phases}')
_MASS_TABLE = ('calc', 'z zestawienia mas i ramion zespołów {tab:mass-components}')
_COST = ('calc', 'z zależności kosztowych Corke’a {lit:corke} dla współczynników z podanego roku{eq:cer}')
_RATE = ('calc', 'stawka z 1986 r. przeliczona liniowo na rok kosztów {lit:galinski_sw}')
_AIRCRAFT_AERO = ('calc', 'z tabeli charakterystyk aerodynamicznych samolotu {tab:aircraft-aero}')
_HIGH_LIFT = ('lit', 'przyrost dla przyjętego rodzaju klapy {tab:high-lift-data}')


def _gust(e):
    return ('reg', 'prędkość podmuchu obliczeniowego wg przepisów ' + _regulation(e['source']))


def _empty_law(e):
    source = e.get('source') or ''
    if 'Korelacja' in source:
        return ('lit', 'korelacja statystyczna dla klasy samolotu {lit:raymer}')
    if 'Dwa punkty' in source:
        return ('chart', 'z dwóch punktów odczytanych z wykresu udziału masy pustej {fig:mass-trend}')
    if 'Regresja' in source or 'analizy trendów' in source:
        return ('calc', 'z linii trendu udziału masy pustej w analizie trendów {fig:mass-trend}')
    if 'autora' in source and 'Współczynniki' in source:
        return ('ass', 'współczynniki zależności przyjęte w koncepcji')
    return ('ass', 'stały udział masy pustej przyjęty w koncepcji')


def _extra_requirement(e):
    if e.get('value'):
        return ('req', 'dodatkowe wymaganie misji (prędkość maksymalna lub holowanie szybowca)')
    return ('calc', 'temat nie stawia dodatkowego wymagania prędkości maksymalnej ani holowania — przyjęto zero')


def _load_factor(e):
    return ('reg', 'wartość graniczna dla przyjętej kategorii samolotu wg ' + _regulation(e['source']))


ORIGIN = {
    # --- stałe ---
    'g': ('const', 'normalne przyspieszenie ziemskie'), 'rho0': _ISA, 'T0': _ISA, 'p0': _ISA, 'R_air': _ISA,
    'kappa': ('const', 'dla powietrza jako gazu dwuatomowego'), 'beta': _ISA, 'nu0': _ISA, 'p11': _ISA,
    'T_cr': _ISA, 'a_0': _ISA, 'sigma_4500': _ISA, 'rho_gl': _ISA, 'rho_mis': _ISA,
    # --- Projekt 1 ---
    'n_pas': ('req', ''), 'm_cargo': ('req', ''), 'n_zal': ('req', ''),
    'm_pas': ('ass', 'masa obliczeniowa pasażera wraz z bagażem'),
    'm_bag': ('ass', 'bagaż ponad masę obliczeniową pasażera'),
    'm_os': ('ass', 'masa obliczeniowa członka załogi z wyposażeniem osobistym'),
    'H_cr': ('req', ''), 'V_cr_kmh': ('req', 'prędkość rzeczywista (TAS)'),
    'AR': ('ass', 'wydłużenie przyjęte w koncepcji; porównanie z analizą trendów {tab:predecessors}'),
    'AR_1': ('ass', 'wynika z zadanej rozpiętości i powierzchni skrzydła'),
    'e_1': ('ass', 'typowa wartość dla płata o umiarkowanym wydłużeniu, e ≈ 0,8 {lit:galinski_aw}'),
    'Cx0_1': ('ass', 'wartość z przedziału typowego dla klasy samolotu {tab:cx0-classes}'),
    'Cx0_baz': ('ass', 'wartość z przedziału typowego dla klasy samolotu {tab:cx0-classes}'),
    'dCx0_konf': ('ass', 'dodatek oporu od elementów konfiguracji wymienionych w opisie koncepcji'),
    'Swet_S_szk': ('calc', 'zmierzono na szkicu koncepcyjnym samolotu {fig:sketch}'),
    'Kmax_1': ('chart', 'odczyt z wykresu maksymalnej doskonałości w funkcji Λ/(S_wet/S) {fig:raymer}'),
    'tr_x1': ('chart', 'odczyt z linii trendu udziału masy pustej {fig:mass-trend}'),
    'tr_y1': ('chart', 'odczyt z linii trendu udziału masy pustej {fig:mass-trend}'),
    'tr_x2': ('chart', 'odczyt z linii trendu udziału masy pustej {fig:mass-trend}'),
    'tr_y2': ('chart', 'odczyt z linii trendu udziału masy pustej {fig:mass-trend}'),
    # --- Projekt 2: misja i masa ---
    'R_km': ('req', ''), 'R_pow': _MISSION, 'H_0': _MISSION, 'V_0_kmh': _MISSION, 't_ocz': _MISSION,
    'V_ocz_kmh': _MISSION, 't_zad': _MISSION, 'm_zrzut': _MISSION,
    'SFC': ('ass', 'jednostkowe zużycie paliwa silnika przyjętego w koncepcji (zakres przelotowy)'),
    'TSFC': ('ass', 'jednostkowe zużycie paliwa silnika przyjętego w koncepcji (zakres przelotowy)'),
    'SFC_max': ('ass', 'jednostkowe zużycie paliwa przy mocy (ciągu) maksymalnej — dane silnika'),
    'T_max_zad': ('ass', 'ciąg maksymalny silnika przyjętego w koncepcji'),
    'P_max_zad': ('ass', 'moc maksymalna silnika przyjętego w koncepcji'),
    'eta_p': ('ass', 'sprawność śmigła w przelocie, typowo η ≈ 0,8 {lit:galinski_aw}'),
    'k_K': ('ass', 'średnia doskonałość w przelocie 0,94 K_max, bo przelot nie odbywa się dokładnie przy K_max'),
    'K_przel': ('calc', 'z biegunowej samolotu (Projekt 4) przy wymaganej prędkości i wysokości przelotu'),
    'r_TO': ('ass', 'wartość statystyczna dla rozruchu, kołowania i startu (0,970–0,975) {lit:galinski_aw}'),
    'r_LND': ('ass', 'wartość statystyczna dla lądowania i kołowania (0,970–0,975) {lit:galinski_aw}'),
    'r_CL': ('ass', 'oszacowanie — liczba Macha poza zakresem wykresu Corke’a {fig:corke}'),
    'W_p': ('chart', 'odczyt z wykresu Corke’a dla liczby Macha M_p {fig:corke}'),
    'W_k': ('chart', 'odczyt z wykresu Corke’a dla liczby Macha M_k {fig:corke}'),
    'k_rez': ('ass', 'zapas 6% paliwa na rezerwę i paliwo niezużywalne {lit:galinski_aw}'),
    'S_mis': ('calc', 'powierzchnia nośna z ostatniej iteracji bilansu uzgodnionego z biegunową samolotu (Projekt 4)'),
    'CD0_mis': ('calc', 'opór zerowy biegunowej analitycznej samolotu (Projekt 4) {tab:polar-coefficients}'),
    'k_mis': ('calc', 'współczynnik oporu indukowanego biegunowej analitycznej samolotu (Projekt 4) {tab:polar-coefficients}'),
    'c_mis': ('calc', 'przeliczenie jednostkowego zużycia paliwa na zużycie na jednostkę drogi'),
    'margin_R': ('ass', 'zapas obliczeniowy 0,1% długości trasy'),
    'r_CR_start': _PHASES, 'r_RET_start': _PHASES,
    'K_vs': ('ass', 'skrzydło o stałym skosie (dla skosu zmiennego 1,04) {lit:galinski_aw}'),
    'K_kor': ('lit', 'poprawka konstrukcyjna do korelacji statystycznej klasy samolotu {lit:raymer}'),
    'mp_x1': ('chart', 'odczyt z wykresu udziału masy pustej {fig:mass-trend}'),
    'mp_y1': ('chart', 'odczyt z wykresu udziału masy pustej {fig:mass-trend}'),
    'mp_x2': ('chart', 'odczyt z wykresu udziału masy pustej {fig:mass-trend}'),
    'mp_y2': ('chart', 'odczyt z wykresu udziału masy pustej {fig:mass-trend}'),
    # --- Projekt 2: wykres doboru i napęd ---
    'V_min_kmh': ('req', 'największa dopuszczalna prędkość przeciągnięcia'), 's_L': ('req', ''),
    'w_y_wym': ('req', ''), 's_TO': ('req', 'całkowita długość startu do wysokości 15 m'),
    's_roz': ('req', 'długość rozbiegu (temat nie podaje długości startu do 15 m)'),
    'sigma_lot': ('bc', 'lotnisko na poziomie morza w atmosferze wzorcowej'),
    'm_lnd': _PHASES, 'm_sr_cr': _PHASES,
    'eta_TO': ('ass', 'sprawność śmigła na rozbiegu, typowo 0,5–0,6'),
    'S': ('ass', 'powierzchnia skrzydła narzucona w koncepcji'),
    'P': ('ass', 'moc silnika wybranego w koncepcji'),
    'TW_TO': ('calc', 'start nie wymiaruje napędu w tym wariancie'),
    'PW_extra': _extra_requirement, 'TW_extra': _extra_requirement,
    'A_e': _empty_law, 'C_e': _empty_law, 'e_m0': _empty_law,
    'P_P4': ('calc', 'moc potrzebna w przelocie i wznoszeniu obliczona z biegunowej samolotu (Projekt 4)'),
    'TW_P4': ('calc', 'ciąg potrzebny w przelocie i wznoszeniu obliczony z biegunowej samolotu (Projekt 4)'),
    'PW_TO_check': ('calc', 'moc potrzebna do startu na 15 m obliczona modelem rozbiegu i wznoszenia (Projekt 5)'),
    'TW_TO_check': ('calc', 'ciąg potrzebny do startu na 15 m obliczony modelem rozbiegu i wznoszenia (Projekt 5)'),
    'PW_mod': ('calc', 'moc potrzebna do startu na 15 m obliczona modelem rozbiegu i wznoszenia (Projekt 5)'),
    'TW_mod': ('calc', 'ciąg potrzebny do startu na 15 m obliczony modelem rozbiegu i wznoszenia (Projekt 5)'),
    'k_p': ('lit', 'spadek ciągu silnika dwuprzepływowego z liczbą Macha {lit:paturski}'),
    'dCx0_dob': ('ass', 'dodatek oporu od elementów konfiguracji wymienionych w opisie koncepcji'),
    # --- Projekt 2: koszty ---
    'V_max_c': ('calc', 'prędkość maksymalna lotu poziomego z obliczeń osiągów (Projekt 5)'),
    'N_P': ('ass', 'przewidywana wielkość serii produkcyjnej'),
    'N_am': ('ass', 'liczba egzemplarzy, na które rozkłada się koszty fazy rozwoju'),
    'rok': ('ass', 'rok, na który przeliczono koszty'),
    'H_E_70': _COST, 'H_E_86': _COST, 'H_ML_70': _COST, 'H_ML_86': _COST, 'H_T_70': _COST, 'H_T_86': _COST,
    'C_MM_70': _COST, 'C_MM_86': _COST,
    'R_E': _RATE, 'R_ML': _RATE, 'R_T': _RATE, 'R_QC': _RATE,
    'k_QC': ('lit', 'koszt kontroli jakości równy 13% kosztu robocizny produkcji {lit:galinski_sw}'),
    'n_sil': ('ass', 'liczba silników przyjęta w koncepcji'),
    'C_sil': ('ass', 'cena silnika wg ceny jednostkowej podobnych silników'),
    'C_av': ('ass', 'cena wyposażenia awionicznego jednego egzemplarza'),
    'C_RDTE': ('calc', 'suma składników kosztów fazy rozwoju {tab:costs}'),
    'z_zysk': ('ass', 'marża producenta'),
    # --- Projekt 3: geometria ---
    'lambda_w': ('ass', 'zbieżność obrysu skrzydła przyjęta w koncepcji'),
    'chi25': ('ass', 'skos skrzydła przyjęty w koncepcji'),
    'b': ('req', 'rozpiętość narzucona w temacie lub koncepcji'),
    'c_t': ('calc', 'obrys eliptyczny kończy się zerową cięciwą'),
    'xi_b': ('ass', 'położenie załamania obrysu przyjęte w koncepcji'),
    'y_mac': ('calc', 'z całkowania obrysu skrzydła (moment statyczny półskrzydła)'),
    'd_k': ('ass', 'średnica kadłuba dobrana do układu kabiny (do 4 osób 1,25 m, powyżej 1,50 m)'),
    'n_ab': ('ass', 'liczba foteli w rzędzie przyjęta w koncepcji kabiny'),
    'l_layout': ('ass', 'długość kabiny z przyjętego układu foteli'),
    'd_layout': ('ass', 'średnica kabiny z przyjętego układu foteli'),
    'l_bay': ('req', 'wymiar użytkowy ładowni'), 'w_bay': ('req', 'wymiar użytkowy ładowni'),
    'h_bay': ('req', 'wymiar użytkowy ładowni'),
    'shell_bay': ('ass', 'naddatek średnicy na pokrycie i wręgi'),
    'l_H': ('calc', 'ramię wynikające z położenia skrzydła ustalonego w analizie wyważenia {tab:loading-states}'),
    'l_V': ('calc', 'ramię wynikające z położenia skrzydła ustalonego w analizie wyważenia {tab:loading-states}'),
    'V_H': ('ass', 'przyjęto z uwzględnieniem średniej z analizy trendów {tab:trend-means}'),
    'V_V': ('ass', 'przyjęto z uwzględnieniem średniej z analizy trendów {tab:trend-means}'),
    'AR_H': ('ass', 'typowe wydłużenie usterzenia poziomego samolotów tej klasy'),
    'lambda_H': ('ass', 'typowa zbieżność usterzenia poziomego'),
    'AR_V': ('ass', 'typowe wydłużenie usterzenia pionowego samolotów tej klasy'),
    'lambda_V': ('ass', 'typowa zbieżność usterzenia pionowego'),
    'bf_b_zal': ('ass', 'udział rozpiętości zajęty przez klapy'),
    'ba_b_zal': ('ass', 'udział rozpiętości zajęty przez lotki'),
    'ca_c': ('ass', 'przyjęto z uwzględnieniem średniej z analizy trendów {tab:trend-means}'),
    'cf_c': ('ass', 'względna cięciwa klapy przyjęta w koncepcji'),
    'eta_f_in': ('ass', 'klapolotki na całej rozpiętości krawędzi spływu poza kadłubem'),
    'eta_f_out': ('ass', 'klapolotki na całej rozpiętości krawędzi spływu poza kadłubem'),
    'eta_a_in': ('ass', 'położenie lotki na krawędzi spływu'),
    'eta_a_out': ('ass', 'położenie lotki na krawędzi spływu'),
    # --- Projekt 3: masy i wyważenie ---
    'M_kgr': _MASS_TABLE, 'M_sgr': _MASS_TABLE, 'm_sgr': _MASS_TABLE, 'x_zal': _MASS_TABLE,
    'x_lad': _MASS_TABLE, 'x_f': _MASS_TABLE,
    'xcel': ('ass', 'środek masy samolotu pustego przy 25% ŚCA, z myślą o zakresie położeń w locie {lit:grabowski_am}'),
    'x_LEc': ('calc', 'położenie skrzydła dobrane tak, aby środek masy w locie mieścił się w zakresie 25–35% ŚCA'),
    'xcg_fwd': ('calc', 'z zestawienia stanów załadowania {tab:loading-states}'),
    'xcg_aft': ('calc', 'z zestawienia stanów załadowania {tab:loading-states}'),
    'dx_n': ('ass', 'przesunięcie punktu neutralnego od śmigła i gondol, wg położenia napędu'),
    'eta_H': ('ass', 'hamowanie strug i interferencja na usterzeniu poziomym'),
    # --- Projekt 3: płat ---
    'cz1_max': ('chart', 'największa wartość lokalnego c_z/C_z z rozkładu Schrenka {fig:schrenk}'),
    'Cz_max': ('ass', 'maksymalny współczynnik siły nośnej samolotu w konfiguracji gładkiej'),
    'cz_prof': ('lit', 'charakterystyka wybranego profilu dla liczby Reynoldsa lotu {tab:airfoil-candidates}'),
    'Cx_min1': ('lit', 'wynik badań tunelowych profilu {lit:paturski} {tab:airfoil-data}'),
    'a_inf': ('lit', 'wynik badań tunelowych profilu {lit:paturski} {tab:airfoil-data}'),
    'delta_3': ('calc', 'poprawka na skos; dla skrzydła bez skosu równa 1 {fig:glauert}'),
    'tau_G': ('calc', 'płat eliptyczny bez skosu ma rozkład eliptyczny — poprawka zerowa'),
    'delta_G': ('calc', 'płat eliptyczny bez skosu ma rozkład eliptyczny — poprawka zerowa'),
    # --- Projekt 4 ---
    'Cx_k_eff': ('lit', 'dolna granica oporu kadłuba z kabiną i okuciami wg statystyki samolotów podobnych {lit:paturski}'),
    'sum_CxS': ('calc', 'suma z zestawienia oporów zespołów nienośnych {tab:parasite}'),
    'x_sc_trim': ('ass', 'położenie środka masy, dla którego obliczono biegunową samolotu wyważonego'),
    'k_int': ('lit', 'opór interferencyjny równy 4% oporu szkodliwego {lit:paturski}'),
    'zeta': ('lit', 'przyrost oporu szkodliwego ze wzrostem C_z {lit:paturski}'),
    'Cx_H0': ('calc', 'opór minimalny profilu usterzenia powiększony o opór szczelin steru'),
    'n_fit': _AIRCRAFT_AERO, 'Sx': _AIRCRAFT_AERO, 'Sy': _AIRCRAFT_AERO, 'Sxx': _AIRCRAFT_AERO, 'Sxy': _AIRCRAFT_AERO,
    'dCz_TO_p': _HIGH_LIFT, 'dCz_L_p': _HIGH_LIFT, 'dCx_TO_p': _HIGH_LIFT, 'dCx_L_p': _HIGH_LIFT,
    'e_fTO': _HIGH_LIFT, 'e_fL': _HIGH_LIFT, 'dCz_sl_p': _HIGH_LIFT, 'dCx_sl_p': _HIGH_LIFT,
    'Ssl_S': ('calc', 'z geometrii skrzydła (Projekt 3)'),
    'dCx_podw': ('ass', 'przyrost oporu od wypuszczonego podwozia chowanego'),
    'delta_a': ('ass', 'największe wychylenie lotek'),
    'pb2V_min': ('ass', 'wstępne kryterium skuteczności lotek dla klasy samolotu {lit:raymer}'),
    'wave_chi25': ('ass', 'skos skrzydła przyjęty w koncepcji'),
    'wave_kappa': ('lit', 'współczynnik technologiczny profilu klasycznego {lit:mason}'),
    # --- Projekt 5 ---
    'm_L': _PHASES, 'm_p_cr': _PHASES, 'm_k_cr': _PHASES,
    'V_wy': ('calc', 'prędkość największego nadmiaru mocy z bilansu mocy przy ziemi {fig:climb}'),
    'mu_r': ('bc', 'współczynnik tarcia tocznego dla nawierzchni pasa startowego'),
    'gamma_app': ('ass', 'kąt ścieżki podejścia do lądowania'),
    'mu_h': ('bc', 'współczynnik tarcia kół hamowanych na suchej nawierzchni'),
    'Cz_gopt': ('calc', 'z tabeli biegunowej prędkości {tab:speed-polar}'),
    'Cz_gek': ('calc', 'z tabeli biegunowej prędkości {tab:speed-polar}'),
    # --- Projekt 6 ---
    'nu': ('reg', 'współczynnik bezpieczeństwa 1,5 wymagany przepisami budowy'),
    'Cz_min': ('ass', 'najmniejszy (ujemny) współczynnik siły nośnej w locie odwróconym'),
    'k_VC': ('reg', 'współczynnik minimalnej prędkości przelotowej wg przepisów {lit:cs23}'),
    'k_VD': ('reg', 'stosunek V_D/V_C,min wg przepisów {lit:cs23}'),
    'V_B': ('reg', 'prędkość dla podmuchu o największej intensywności wg przepisów {lit:cs23}'),
    'U_B': _gust, 'U_C': _gust, 'U_D': _gust, 'U_F': _gust,
    'n_f': ('reg', 'przeciążenie manewrowe z wychyloną mechanizacją wg przepisów'),
    'n_plus': _load_factor, 'n_minus': _load_factor,
    'Cd_min': ('calc', 'najmniejszy współczynnik oporu z biegunowej samolotu (Projekt 4) {tab:polar-coefficients}'),
}

_PATTERNS = (
    (re.compile(r'^Wymagania tematu', re.I), ('req', '')),
    (re.compile(r'^(Założenia projektu|Założenie autora|Założenie)\b', re.I), ('ass', '')),
    (re.compile(r'^(Dane silnika)', re.I), ('ass', 'dane silnika przyjętego w koncepcji')),
    (re.compile(r'^Profil misji', re.I), _MISSION),
    (re.compile(r'^ISA$'), _ISA),
    (re.compile(r'CS-?2[235]|STANAG|FAR', re.I), None),
)


def _regulation(text):
    """Nazwa przepisu z odnośnikiem do literatury, bez dopisków roboczych."""
    text = text or ''
    for key, needle in (('cs22', '22'), ('cs25', '25'), ('stanag', 'STANAG'), ('cs23', '23')):
        if needle in text:
            name = {'cs22': 'CS-22', 'cs25': 'CS-25', 'stanag': 'STANAG 4671', 'cs23': 'CS-23'}[key]
            paragraph = re.search(r'§\s?(\d+[.]\d+(?:\([a-z0-9]+\))*)', text)
            if not paragraph and key in ('cs22', 'cs25'):
                paragraph = re.search(r'\b(2[25][.]\d{3}(?:\([a-z0-9]+\))*)', text)
            return name + (f' § {paragraph.group(1)}' if paragraph else '') + ' {lit:' + key + '}'
    return 'przyjętych przepisów budowy'


def classify(entry):
    """(kategoria, tekst) danej wejściowej arkusza."""
    key = entry['key']
    found = ORIGIN.get(key)
    if found is None and key.endswith('_kmh'):
        found = ORIGIN.get(key[:-4] + '_kmh') or ORIGIN.get(key[:-4])
    if callable(found):
        found = found(entry)
    if found is not None:
        return found
    source = entry.get('source') or ''
    if key == 'tc':
        return ('ass' if not re.search(r'NACA|profil', source, re.I) else 'calc',
                'grubość względna wybranego profilu' if re.search(r'NACA|profil', source, re.I)
                else 'grubość względna profilu skrzydła')
    for pattern, result in _PATTERNS:
        if pattern.search(source):
            return result if result is not None else ('reg', 'wg ' + _regulation(source))
    return ('ass', '')


def origin_text(entry):
    """Opis pochodzenia danej wejściowej (ze znacznikami odwołań)."""
    category, text = classify(entry)
    if category in ASSUMED and category != 'reg':
        return CATEGORY[category] + (f' — {text}' if text else '')
    if category == 'reg':
        return 'Przepisy budowy — ' + text if text and not text.startswith('wg') else 'Przepisy budowy ' + text
    return text[:1].upper() + text[1:] if text else CATEGORY[category]


def ref_text(sheet, key, here_project=None):
    """Pochodzenie wielkości zdefiniowanej w innym miejscu arkusza."""
    entry = sheet.entries[key]
    if entry['project'] == 'const':
        return 'Stała fizyczna {tab:constants}'
    if entry['kind'] == 'given':
        return origin_text(entry)
    section = sheet.sections[entry['section']]
    project = '' if entry['project'] == here_project else f' (Projekt {entry["project"][1:]})'
    return f'Obliczono w części „{section["title"]}”{project}' + '{eq:' + key + '}'


# ---------------------------------------------------------------------------------------------
# Odwołania
# ---------------------------------------------------------------------------------------------
_TOKEN = re.compile(r'\{(fig|tab|eq|lit):([A-Za-z0-9_\-]+)\}')


def xref(target, pre=' (', post=')', upper=False):
    """Odwołanie do rysunku, tabeli lub wzoru; tekst uzupełnia ``number_references``."""
    return Markup(f'<span class="xref" data-ref="{escape(target)}" data-pre="{escape(pre)}" '
                  f'data-post="{escape(post)}"{" data-upper" if upper else ""}></span>')


def cite(key, note=''):
    """Cytowanie pozycji literatury: [N] lub [N, s. 5]."""
    return Markup(f'<span class="cite" data-cite="{escape(key)}"'
                  + (f' data-note="{escape(note)}"' if note else '') + '></span>')


_SUB = re.compile(r'(?<![\w\\])([A-Za-zΑ-Ωα-ω])_((?:[^\s/(),.;:<&\]|]|[,.](?=[^\s<]))+)')


_TEX = re.compile(r'(\\\(.*?\\\)|\\\[.*?\\\]|<[^>]*>)', re.S)


def _sub_html(html):
    """Indeksy dolne poza wzorami TeX i znacznikami HTML."""
    return ''.join(part if i % 2 else _SUB.sub(r'\1<sub>\2</sub>', part)
                   for i, part in enumerate(_TEX.split(html)))


def subscripts(text):
    """Indeksy dolne w zwykłym tekście: K_max → K<sub>max</sub> (tekst jest escapowany)."""
    return Markup(_sub_html(str(escape(text or ''))))


def render_tokens(text):
    """Tekst ze znacznikami → HTML z odwołaniami (tekst jest escapowany)."""
    out, last = [], 0
    for match in _TOKEN.finditer(text or ''):
        out.append(str(escape(text[last:match.start()].rstrip() if match.group(1) != 'lit' else text[last:match.start()])))
        kind, target = match.groups()
        if kind == 'fig':
            out.append(xref('fig-' + target))
        elif kind == 'tab':
            out.append(xref('tab-' + target))
        elif kind == 'eq':
            out.append(xref('q-' + target, ', ', ''))
        else:
            out.append(cite(target))
        last = match.end()
    out.append(str(escape(text[last:] if text else '')))
    html = re.sub(r'\s+</span>', '</span>', ''.join(out))
    return Markup(_sub_html(html))


def origin(entry):
    return render_tokens(origin_text(entry))


def origin_ref(sheet, key, here_project=None):
    return render_tokens(ref_text(sheet, key, here_project))


_TAG = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>')
_ATTR_ID = re.compile(r'\bid="([^"]+)"')
_ATTR_CLASS = re.compile(r'\bclass="([^"]*)"')
_XREF = re.compile(r'<span class="xref" data-ref="([^"]+)" data-pre="([^"]*)" data-post="([^"]*)"( data-upper)?></span>')
_CITE = re.compile(r'<span class="cite" data-cite="([^"]+)"(?: data-note="([^"]*)")?></span>')
_BIBLIOGRAPHY = re.compile(r'(<ol class="bibliography" data-bibliography>)(</ol>)')


def number_references(document, literature=None):
    """Numeruje odwołania i literaturę w złożonym dokumencie HTML (część <main class="document">)."""
    start = document.find('<main class="document')
    end = document.rfind('</main>')
    if start < 0 or end < 0:
        return document
    head, body, tail = document[:start], document[start:end], document[end:]
    labels, counts = {}, {'tab': 0, 'fig': 0, 'eq': 0}
    pending_table = pending_eq = None
    for match in _TAG.finditer(body):
        name, attrs = match.group(1).lower(), match.group(2)
        ident = _ATTR_ID.search(attrs)
        ident = ident.group(1) if ident else None
        classes = (_ATTR_CLASS.search(attrs).group(1).split() if _ATTR_CLASS.search(attrs) else [])
        if name == 'table':
            pending_table = ident
        elif name == 'caption':
            counts['tab'] += 1
            for target in (pending_table, ident):
                if target:
                    labels[target] = f'tab. {counts["tab"]}'
            pending_table = None
        elif name == 'figure':
            counts['fig'] += 1
            if ident:
                labels[ident] = f'rys. {counts["fig"]}'
        elif 'equation' in classes:
            counts['eq'] += 1
            for target in (pending_eq, ident):
                if target:
                    labels.setdefault(target, f'wzór ({counts["eq"]})')
            pending_eq = None
        if ident and ident.startswith('q-'):
            pending_eq = ident

    def fill(match):
        label = labels.get(match.group(1))
        if not label:
            return ''
        if match.group(4):
            label = label[:1].upper() + label[1:]
        return _html.unescape(match.group(2)) + label + _html.unescape(match.group(3))

    body = _XREF.sub(fill, body)
    literature = {**LITERATURE, **(literature or {})}
    order = []

    def number(match):
        key = match.group(1)
        if key not in literature:
            return ''
        if key not in order:
            order.append(key)
        note = f', {match.group(2)}' if match.group(2) else ''
        return f'<span class="cite">[{order.index(key) + 1}{note}]</span>'

    body = _CITE.sub(number, body)
    items = ''.join(f'<li id="lit-{key}">{literature[key]}</li>' for key in order)
    body = _BIBLIOGRAPHY.sub(lambda m: m.group(1) + items + m.group(2), body)
    return head + body + tail


def component_source(text):
    """Podstawa oszacowania oporu zespołu w języku sprawozdania (dane tunelowe i statystyka z literatury)."""
    text = re.sub(r',?\s*(\[\d+\]\s*)?rys\. Z\.\d+', '', text or '')
    text = re.sub(r'Wzór \(3\.1\),?', 'opór tarcia z poprawką kształtu,', text)
    text = re.sub(r'Wzór \(3\.6\),?', 'obliczono:', text)
    text = text.replace('Tabela C', 'statystyka samolotów podobnych').replace('Dane tunelowe', 'badania tunelowe')
    text = text.replace(' + statystyka', '; statystyka').strip(' ,')
    if 'badania tunelowe' in text or 'statystyka' in text or 'danych tunelowych' in text:
        text += ' {lit:paturski}'
    return render_tokens(text)
