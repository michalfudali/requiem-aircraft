"""Wymagania przepisów budowy stosowane w projekcie, z paragrafem i dokumentem źródłowym.

Podstawą są „Wyjątki z przepisów lotniczych JAR” udostępnione do przedmiotu WTLK przez Zakład
Samolotów i Śmigłowców Wydziału MEiL PW (polskie przekłady JAR-22, JAR-23, JAR-25 i JAR-VLA):
https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/WTLK/Wyjatki-z-przepisow

Każda wartość wynikająca z przepisów (granica stosowalności, masa osoby, prędkość przeciągnięcia,
wymaganie wznoszenia, współczynnik obciążenia, prędkość podmuchu, współczynnik bezpieczeństwa…)
jest zapisana tutaj raz, razem z paragrafem i rozdziałem, z którego pochodzi. Obliczenia, kreator
i raport biorą wartości i odwołania z tego katalogu; raport cytuje paragraf i dokument.

Kategorie spoza wyjątków (CS-LSA, Załącznik I do rozporządzenia 2018/1139, UAS) mają wskazane
własne dokumenty; ich wymagania nie pochodzą z przekładów JAR.
"""
import re

COURSE_PAGE = 'https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/WTLK/Wyjatki-z-przepisow'
PDF_BASE = 'http://itlims-zsis.meil.pw.edu.pl/pomoce/JAR/'
KT_TO_KMH = 1.852

_COURSE = ('Wyjątki z przepisów lotniczych JAR (przekład polski), materiały do przedmiotu WTLK, '
           'Zakład Samolotów i Śmigłowców, Wydział MEiL PW')

# Rozdziały wyjątków: (przepis, rozdział, plik PDF ze strony przedmiotu).
_CHAPTERS = {
    'jar22_a': ('JAR-22', 'Podczęść A – Ogólne', 'JAR-22_Ogolne.pdf'),
    'jar22_b': ('JAR-22', 'Podczęść B – Lot', 'JAR-22_Lot.pdf'),
    'jar22_c': ('JAR-22', 'Podczęść C – Struktura', 'JAR-22_Struktury.pdf'),
    'jar22_d': ('JAR-22', 'Podczęść D – Projektowanie i budowa', 'JAR-22_Projekt_i_budowa.pdf'),
    'jar22_e': ('JAR-22', 'Podczęść E – Zespół napędowy', 'JAR-22_Zespol_napedowy.pdf'),
    'jar23_a': ('JAR-23', 'Podczęść A – Ogólne', 'JAR-23_Ogolne.pdf'),
    'jar23_b': ('JAR-23', 'Podczęść B – Lot', 'JAR-23_Lot.pdf'),
    'jar23_c': ('JAR-23', 'Podczęść C – Struktura', 'JAR-23_Struktury.pdf'),
    'jar23_d': ('JAR-23', 'Podczęść D – Projekt i budowa', 'JAR-23_Projekt_i_budowa.pdf'),
    'jar23_e': ('JAR-23', 'Podczęść E – Zespół napędowy', 'JAR-23_Zespol_napedowy.pdf'),
    'jar23_anex_a': ('JAR-23', 'Załącznik A – Uproszczone kryteria obciążeń', 'JAR-23_Kryteria_uproszczone.pdf'),
    'jar25_a': ('JAR-25', 'Podczęść A – Ogólne', 'JAR-25_Ogolne.pdf'),
    'jar25_b': ('JAR-25', 'Podczęść B – Lot', 'JAR-25_Lot.pdf'),
    'jar25_c': ('JAR-25', 'Podczęść C – Struktura', 'JAR-25_Struktury.pdf'),
    'jar25_d': ('JAR-25', 'Podczęść D – Projekt i budowa', 'JAR-25_Projekt_i_budowa.pdf'),
    'jar25_e': ('JAR-25', 'Podczęść E – Zespół napędowy', 'JAR-25_Zespol_napedowy.pdf'),
    'jarvla_a': ('JAR-VLA', 'Podczęść A – Ogólne', 'JAR-VLA_Ogolne.pdf'),
    'jarvla_b': ('JAR-VLA', 'Podczęść B – Lot', 'JAR-VLA_Lot.pdf'),
    'jarvla_c': ('JAR-VLA', 'Podczęść C – Struktura', 'JAR-VLA_Struktury.pdf'),
    'jarvla_d': ('JAR-VLA', 'Podczęść D – Projekt i konstrukcja', 'JAR-VLA_Projekt_i_budowa.pdf'),
    'jarvla_f': ('JAR-VLA', 'Podczęść F – Zespół napędowy', 'JAR-VLA_Zespol_napedowy.pdf'),
}

DOCUMENTS = {key: dict(regulation=reg, chapter=chapter, url=PDF_BASE + name,
                       title=f'{reg}, {chapter}', citation=f'{_COURSE}: <em>{reg}, {chapter}</em>. {PDF_BASE + name}')
             for key, (reg, chapter, name) in _CHAPTERS.items()}
# Dokumenty spoza przekładów JAR (kategorie, których wyjątki nie obejmują).
DOCUMENTS.update({
    'easa_cs_lsa': dict(regulation='CS-LSA', chapter='Light Sport Aeroplanes', title='EASA CS-LSA',
                        url='https://www.easa.europa.eu/document-library/certification-specifications/group/cs-lsa-light-sport-aeroplanes',
                        citation='EASA: <em>Certification Specifications for Light Sport Aeroplanes CS-LSA</em> '
                                 '(odnośnik na stronie wyjątków z przepisów). https://www.easa.europa.eu/document-library/'
                                 'certification-specifications/group/cs-lsa-light-sport-aeroplanes'),
    'easa_cs22': dict(regulation='CS-22', chapter='Amendment 3', title='EASA CS-22 Amdt 3',
                      url='https://www.easa.europa.eu/document-library/certification-specifications/group/cs-22-sailplanes-and-powered-sailplanes',
                      citation='EASA: <em>Certification Specifications for Sailplanes and Powered Sailplanes CS-22</em>, '
                               'Amendment 3 (odnośnik na stronie wyjątków z przepisów). https://www.easa.europa.eu/'
                               'document-library/certification-specifications/group/cs-22-sailplanes-and-powered-sailplanes'),
    'eu_2018_1139': dict(regulation='UE 2018/1139', chapter='art. 2 ust. 8 i załącznik I', title='Rozporządzenie (UE) 2018/1139',
                         url='https://eur-lex.europa.eu/eli/reg/2018/1139/oj',
                         citation='Rozporządzenie Parlamentu Europejskiego i Rady (UE) 2018/1139, art. 2 ust. 8 i załącznik I; '
                                  'klasyfikacja krajowa t.j. Dz. U. z 2025 r. poz. 1137. https://eur-lex.europa.eu/eli/reg/2018/1139/oj'),
    'eu_2019_947': dict(regulation='UE 2019/947', chapter='art. 3–6', title='Rozporządzenie wykonawcze (UE) 2019/947',
                        url='https://eur-lex.europa.eu/eli/reg_impl/2019/947/oj',
                        citation='Rozporządzenie wykonawcze Komisji (UE) 2019/947, art. 3–6 (kategorie operacji UAS). '
                                 'https://eur-lex.europa.eu/eli/reg_impl/2019/947/oj'),
    'stanag_4671': dict(regulation='STANAG 4671', chapter='USAR, wyd. 1', title='STANAG 4671 (USAR)',
                        url=PDF_BASE + 'usar_edition_1.pdf',
                        citation='NATO: <em>STANAG 4671 — Unmanned Aerial Vehicles Systems Airworthiness Requirements '
                                 '(USAR)</em>, wyd. 1 (odnośnik na stronie wyjątków z przepisów). ' + PDF_BASE + 'usar_edition_1.pdf'),
})


def _r(doc, paragraph, title, text):
    return dict(doc=doc, paragraph=paragraph, title=title, text=text)


# Wymagania (wartości streszczone z przekładów; paragraf i rozdział jak w wyjątkach).
RULES = {
    # ---------------------------------------------------------------- JAR-23
    'jar23.1a1': _r('jar23_a', 'JAR 23.1(a)(1)', 'Stosowalność: kategorie normalna, użytkowa i akrobacyjna',
                    'do 9 miejsc dla osób na pokładzie oprócz pilotów, maksymalny ciężar startowy ≤ 5670 kg'),
    'jar23.1a2': _r('jar23_a', 'JAR 23.1(a)(2)', 'Stosowalność: kategoria transportu lokalnego (commuter)',
                    'dwusilnikowe samoloty śmigłowe, do 19 miejsc oprócz pilotów, maksymalny ciężar startowy ≤ 8618 kg'),
    'jar23.3': _r('jar23_a', 'JAR 23.3', 'Kategorie samolotów',
                  'normalna: bez akrobacji, przechylenie ≤ 60°; użytkowa: także korkociągi i przechylenie 60–90°; '
                  'akrobacyjna: bez ograniczeń; commuter: jak normalna'),
    'jar23.25a2': _r('jar23_b', 'JAR 23.25(a)(2)', 'Ograniczenia ciężaru: ciężar użytkownika miejsca',
                     '77 kg na każde miejsce (kategoria normalna i commuter), 86 kg (użytkowa i akrobacyjna)'),
    'jar23.49c': _r('jar23_b', 'JAR 23.49(c)', 'Prędkość przeciągnięcia',
                    'VS0 przy ciężarze maksymalnym ≤ 61 kt (CAS) dla samolotów jednosilnikowych oraz dwusilnikowych '
                    '≤ 2721 kg, które nie spełniają JAR 23.67(a)(1)'),
    'jar23.65a': _r('jar23_b', 'JAR 23.65(a)', 'Wznoszenie: wszystkie silniki pracujące',
                    'tłokowe do 2721 kg kategorii N, U, A: ustalony gradient wznoszenia na poziomie morza ≥ 8,3 % '
                    '(samoloty lądowe) albo ≥ 6,7 % (wodnosamoloty i amfibie), przy mocy maksymalnej trwałej, klapach do startu i V ≥ 1,2 VS1'),
    'jar23.65b': _r('jar23_b', 'JAR 23.65(b)', 'Wznoszenie: wszystkie silniki pracujące',
                    'tłokowe > 2721 kg i turbinowe kategorii N, U, A: gradient wznoszenia po starcie ≥ 4 % (moc startowa)'),
    'jar23.67a1': _r('jar23_b', 'JAR 23.67(a)(1)', 'Wznoszenie: jeden silnik niepracujący',
                     'dwusilnikowe tłokowe ≤ 2721 kg z VS0 > 61 kt: gradient ≥ 1,5 % na wysokości ciśnieniowej 5000 ft'),
    'jar23.77': _r('jar23_b', 'JAR 23.77', 'Zaniechane lądowanie',
                   'gradient ≥ 3,3 % (tłokowe ≤ 2721 kg), ≥ 2,5 % (pozostałe N, U, A), ≥ 3,2 % (commuter)'),
    'jar23.303': _r('jar23_c', 'JAR 23.303', 'Współczynnik bezpieczeństwa', 'ν = 1,5'),
    'jar23.333b': _r('jar23_c', 'JAR 23.333(b)', 'Obwiednia obciążeń sterowanych',
                     'n+ z JAR 23.337 do VD, n− przy VC, dalej liniowo do 0 przy VD (normalna, commuter) '
                     'albo do −1,0 przy VD (użytkowa, akrobacyjna)'),
    'jar23.333c': _r('jar23_c', 'JAR 23.333(c)', 'Obwiednia obciążeń od podmuchów',
                     'podmuchy ±50 ft/s (15,24 m/s) przy VC i ±25 ft/s (7,62 m/s) przy VD; dla commuter także '
                     '±66 ft/s (20,12 m/s) przy VB (do 20 000 ft)'),
    'jar23.335a': _r('jar23_c', 'JAR 23.335(a)', 'Projektowa prędkość przelotowa VC',
                     'VC [kt] ≥ 33·√(W/S) (N, U, commuter) albo 36·√(W/S) (A), W/S w lbf/ft² przy ciężarze startowym; '
                     'dla W/S > 20 mnożnik maleje liniowo do 28,6 przy W/S = 100; VC nie musi przekraczać 0,9 VH'),
    'jar23.335b': _r('jar23_c', 'JAR 23.335(b)', 'Projektowa prędkość nurkowania VD',
                     'VD ≥ 1,25 VC oraz VD ≥ 1,40 VCmin (N, commuter), 1,50 VCmin (U), 1,55 VCmin (A); '
                     'dla W/S > 20 mnożnik maleje liniowo do 1,35 przy W/S = 100'),
    'jar23.335c': _r('jar23_c', 'JAR 23.335(c)', 'Projektowa prędkość manewrowa VA', 'VA ≥ VS·√n; VA nie musi przekraczać VC'),
    'jar23.335d': _r('jar23_c', 'JAR 23.335(d)', 'Prędkość dla maksymalnej intensywności podmuchów VB',
                     'VB z przecięcia linii CN max z linią podmuchu albo VS1·√ng (mniejsza z nich); VB nie musi przekraczać VC'),
    'jar23.337a': _r('jar23_c', 'JAR 23.337(a)', 'Dodatni współczynnik obciążenia manewrowego',
                     'normalna i commuter: n ≥ 2,1 + 24000/(W + 10000), W w lb, n nie musi przekraczać 3,8; '
                     'użytkowa: 4,4; akrobacyjna: 6,0'),
    'jar23.337b': _r('jar23_c', 'JAR 23.337(b)', 'Ujemny współczynnik obciążenia manewrowego',
                     '0,4·n+ (normalna, użytkowa, commuter); 0,5·n+ (akrobacyjna)'),
    'jar23.341': _r('jar23_c', 'JAR 23.341(c)', 'Współczynniki obciążenia od podmuchu',
                    'n = 1 ± kg·ρ0·Ude·V·a / (2·W/S), kg = 0,88·µg/(5,3 + µg), µg = 2(W/S)/(ρ·C·a·g), '
                    'C – średnia cięciwa geometryczna'),
    'jar23.345': _r('jar23_c', 'JAR 23.345', 'Urządzenia do uzyskiwania wysokiej siły nośnej',
                    'klapy wypuszczone przy VF: manewr do n = 2,0 i podmuchy ±25 ft/s (7,62 m/s); VF ≥ max(1,4 VS; 1,8 VSF)'),
    'jar23.751': _r('jar23_d', 'JAR 23.751(a)', 'Wyporność głównego pływaka',
                    'wyporność o 80 % większa od potrzebnej do przejęcia ciężaru maksymalnego w słodkiej wodzie; '
                    'komory wodoszczelne chroniące przed wywróceniem przy zalaniu dwóch komór'),
    'jar23.629': _r('jar23_d', 'JAR 23.629(c)', 'Flatter',
                    'analiza racjonalna braku flatteru, rewersu sterów i dywergencji musi obejmować prędkości do 1,2 VD'),
    # ---------------------------------------------------------------- JAR-VLA
    'vla.1': _r('jarvla_a', 'JAR-VLA 1(a)', 'Stosowalność',
                'jeden silnik o zapłonie iskrowym lub samoczynnym, nie więcej niż 2 miejsca, maksymalny ciężar '
                'startowy ≤ 750 kg, VS0 ≤ 45 kt (CAS); tylko loty dzienne VFR'),
    'vla.3': _r('jarvla_a', 'JAR-VLA 3', 'Kategorie samolotów', 'tylko samoloty nieakrobacyjne (przechylenie ≤ 60°)'),
    'vla.25a2': _r('jarvla_b', 'JAR-VLA 25(a)(2)', 'Ograniczenia ciężaru: ciężar użytkownika miejsca',
                   '86 kg na każde miejsce; paliwo na co najmniej 1 h przy mocy maksymalnej trwałej'),
    'vla.65': _r('jarvla_b', 'JAR-VLA 65', 'Wznoszenie',
                 'ustalona prędkość wznoszenia ≥ 2 m/s (moc ≤ startowej, podwozie schowane, klapy startowe)'),
    'vla.77': _r('jarvla_b', 'JAR-VLA 77', 'Lądowanie zaniechane', 'ustalony kąt wznoszenia co najmniej 1:30 na poziomie morza'),
    'vla.303': _r('jarvla_c', 'JAR-VLA 303', 'Współczynnik bezpieczeństwa', 'ν = 1,5'),
    'vla.333b': _r('jarvla_c', 'JAR-VLA 333(b)', 'Obwiednia obciążeń sterowanych',
                   'n+ z JAR-VLA 337 do VD, n− przy VC, dalej liniowo do 0 przy VD'),
    'vla.333c': _r('jarvla_c', 'JAR-VLA 333(c)', 'Obwiednia obciążeń od podmuchów',
                   'podmuchy ±15,24 m/s przy VC i ±7,62 m/s przy VD'),
    'vla.335a': _r('jarvla_c', 'JAR-VLA 335(a)', 'Obliczeniowa prędkość przelotowa VC',
                   'VC [m/s] ≥ 2,4·√(Mg/S), Mg/S w N/m²; VCmin nie musi przekraczać 0,9 VH'),
    'vla.335b': _r('jarvla_c', 'JAR-VLA 335(b)', 'Obliczeniowa prędkość nurkowania VD', 'VD ≥ 1,25 VC oraz VD ≥ 1,40 VCmin'),
    'vla.335c': _r('jarvla_c', 'JAR-VLA 335(c)', 'Obliczeniowa prędkość manewrowa VA', 'VA ≥ VS·√n; VA nie musi przekraczać VC'),
    'vla.337': _r('jarvla_c', 'JAR-VLA 337', 'Dopuszczalne współczynniki obciążeń sterowanych', 'n+ ≥ 3,8; n− ≤ −1,5'),
    'vla.341': _r('jarvla_c', 'JAR-VLA 341', 'Współczynniki obciążeń od podmuchów',
                  'n = 1 + ½·ρ0·V·a·Kg·Ude/(Mg/S), Kg = 0,88·µg/(5,3 + µg), µg = 2(M/S)/(ρ·C·a)'),
    'vla.345': _r('jarvla_c', 'JAR-VLA 345', 'Urządzenia zwiększające nośność',
                  'klapy przy VF: manewr do n = 2,0 i podmuchy ±7,62 m/s; VF ≥ max(1,4 VS; 1,8 VSF)'),
    'vla.629': _r('jarvla_d', 'JAR-VLA 629(b)', 'Flatter', 'analiza racjonalna musi wykazać brak flatteru do 1,2 VD'),
    # ---------------------------------------------------------------- JAR-22
    'jar22.1a1': _r('jar22_a', 'JAR 22.1(a)(1)', 'Stosowalność: szybowce', 'ciężar maksymalny ≤ 750 kg; kategorie U i A'),
    'jar22.1a2': _r('jar22_a', 'JAR 22.1(a)(2)', 'Stosowalność: motoszybowce',
                    'jednosilnikowe (zapłon iskrowy lub samoczynny), W/b² ≤ 3 kg/m², ciężar maksymalny ≤ 850 kg'),
    'jar22.1a3': _r('jar22_a', 'JAR 22.1(a)(3)', 'Stosowalność: liczba osób', 'nie więcej niż dwie osoby na pokładzie'),
    'jar22.23b': _r('jar22_b', 'JAR 22.23(b)', 'Zakres położeń środka ciężkości',
                    'zakres ŚC dla ciężaru osoby ze spadochronem od 70 kg do 110 kg, bez balastu zdejmowalnego'),
    'jar22.25a2': _r('jar22_b', 'JAR 22.25(a)(2)', 'Ograniczenia ciężaru: osoby na pokładzie',
                     'ciężar osób ze spadochronami 110 kg (szybowiec jednomiejscowy) albo 180 kg (dwumiejscowy); '
                     'motoszybowiec: paliwo na co najmniej 0,5 h przy mocy maksymalnej ciągłej'),
    'jar22.25b': _r('jar22_b', 'JAR 22.25(b)', 'Ciężar minimalny', 'osoba ze spadochronem 55 kg plus balast zdejmowalny'),
    'jar22.49b': _r('jar22_b', 'JAR 22.49(b)', 'Prędkość przeciągnięcia',
                    'VS0 w konfiguracji do lądowania ≤ 80 km/h (hamulce schowane, bez balastu wodnego) '
                    'oraz ≤ 90 km/h z balastem wodnym'),
    'jar22.51': _r('jar22_b', 'JAR 22.51(a)', 'Start motoszybowca',
                   'długość startu do wysokości 15 m przy ciężarze maksymalnym ≤ 500 m (sucha, twarda nawierzchnia)'),
    'jar22.65': _r('jar22_b', 'JAR 22.65(a)', 'Wznoszenie motoszybowca',
                   'czas wznoszenia od oderwania do 360 m nad powierzchnią startu ≤ 4 min (średnio ≥ 1,5 m/s)'),
    'jar22.71': _r('jar22_b', 'JAR 22.71', 'Prędkość opadania motoszybowca',
                   'najmniejsza prędkość opadania z mocą zdławioną ≤ 1,0 m/s (jednomiejscowy) albo ≤ 1,2 m/s (dwumiejscowy)'),
    'jar22.303': _r('jar22_c', 'JAR 22.303', 'Współczynnik bezpieczeństwa', 'ν = 1,5'),
    'jar22.333b': _r('jar22_c', 'JAR 22.333(b)', 'Obwiednia obciążeń od manewrów',
                     'klapy w położeniu przelotowym, hamulce schowane; punkty A–G z JAR 22.337'),
    'jar22.333c': _r('jar22_c', 'JAR 22.333(c)', 'Obwiednia od podmuchów', 'podmuchy ±15 m/s przy VB i ±7,5 m/s przy VD'),
    'jar22.335a': _r('jar22_c', 'JAR 22.335(a)', 'Projektowa prędkość manewrowa VA', 'VA = VS1·√n1'),
    'jar22.335b': _r('jar22_c', 'JAR 22.335(b)', 'Projektowa prędkość z klapami VF',
                     'dla położeń do lądowania VF ≥ max(1,4 VS1; 2,0 VSF)'),
    'jar22.335c': _r('jar22_c', 'JAR 22.335(c)', 'Prędkość w burzliwej atmosferze VB', 'VB ≥ VA'),
    'jar22.335d': _r('jar22_c', 'JAR 22.335(d)', 'Projektowa prędkość holowania VT', 'VT ≥ 125 km/h'),
    'jar22.335e': _r('jar22_c', 'JAR 22.335(e)', 'Projektowa prędkość startu za wyciągarką VW', 'VW ≥ 110 km/h'),
    'jar22.335f': _r('jar22_c', 'JAR 22.335(f)', 'Projektowa prędkość maksymalna VD',
                     'VD [km/h] ≥ 18·∛((W/S)/Cd,min) (kategoria U) albo 3,5·W/S + 200 (kategoria A), W/S w daN/m²; '
                     'motoszybowiec także VD ≥ 1,35 VH'),
    'jar22.337': _r('jar22_c', 'JAR 22.337', 'Dopuszczalne współczynniki obciążenia manewrowego',
                    'kategoria U: n1 = +5,3, n2 = +4,0, n3 = −1,5, n4 = −2,65; kategoria A: n1 = n2 = +7,0, n3 = n4 = −5,0'),
    'jar22.341': _r('jar22_c', 'JAR 22.341', 'Obciążenia od podmuchów',
                    'n = 1 ± ½·k·ρ0·U·V·a/(mg/S), k = 0,88·µ/(5,3 + µ), µ = 2(m/S)/(ρ·lm·a); '
                    'n nie musi przekraczać 1,25·(V/VS1)²'),
    'jar22.345b': _r('jar22_c', 'JAR 22.345(b)(1)', 'Obciążenia z wychylonymi klapami',
                     'klapy do lądowania przy prędkości do VF: manewr do n = 4,0 i podmuchy ±7,5 m/s'),
    'jar22.629': _r('jar22_d', 'JAR 22.629', 'Flatter', 'brak flatteru do co najmniej VD; analiza racjonalna do 1,2 VD'),
    # ---------------------------------------------------------------- JAR-25
    'jar25.1': _r('jar25_a', 'JAR 25.1(a)', 'Stosowalność', 'duże samoloty z napędem turbinowym'),
    'jar25.121': _r('jar25_b', 'JAR 25.121', 'Wznoszenie: jeden silnik niepracujący',
                    'drugi odcinek startu (podwozie schowane, V2): gradient ≥ 2,4 % (2 silniki), 2,7 % (3), 3,0 % (4)'),
    'jar25.303': _r('jar25_c', 'JAR 25.303', 'Współczynnik bezpieczeństwa', 'ν = 1,5'),
    'jar25.333b': _r('jar25_c', 'JAR 25.333(b)', 'Obwiednia obciążeń sterowanych w locie', 'punkty manewrów A–I z JAR 25.337'),
    'jar25.335a': _r('jar25_c', 'JAR 25.335(a)', 'Projektowa prędkość przelotowa VC',
                     'VC istotnie większa od VB, VC ≥ VB + 1,32·Uref; VC nie musi przekraczać VH przy mocy maksymalnej trwałej'),
    'jar25.335b': _r('jar25_c', 'JAR 25.335(b)', 'Projektowa prędkość nurkowania VD', 'VC/MC nie większa niż 0,8 VD/MD'),
    'jar25.335c': _r('jar25_c', 'JAR 25.335(c)', 'Projektowa prędkość manewrowa VA', 'VA ≥ VS1·√n; VA nie musi przekraczać VC'),
    'jar25.335e': _r('jar25_c', 'JAR 25.335(e)(3)', 'Projektowa prędkość z klapami VF',
                     'VF ≥ 1,6 VS1 (klapy startowe), 1,8 VS1 (podejście), 1,8 VS0 (klapy do lądowania)'),
    'jar25.337b': _r('jar25_c', 'JAR 25.337(b)', 'Dodatni współczynnik obciążenia manewrowego',
                     'n ≥ 2,1 + 24000/(W + 10000), W w lb; n nie mniejszy niż 2,5 i nie musi przekraczać 3,8'),
    'jar25.337c': _r('jar25_c', 'JAR 25.337(c)', 'Ujemny współczynnik obciążenia manewrowego',
                     'n ≥ −1,0 do prędkości VC, dalej liniowo do 0 przy VD'),
    'jar25.341': _r('jar25_c', 'JAR 25.341(a)', 'Współczynniki obciążenia od podmuchu i turbulencji',
                    'analiza dynamiczna podmuchu 1-cos; prędkość odniesienia Uref = 17,07 m/s EAS przy VC na poziomie morza '
                    '(13,41 m/s na 15 000 ft), przy VD 0,5 Uref'),
    'jar25.345': _r('jar25_c', 'JAR 25.345(a)', 'Urządzenia do uzyskiwania wysokiej siły nośnej',
                    'klapy przy VF: manewr do n = 2,0 i podmuchy ±7,62 m/s EAS'),
    'jar25.629': _r('jar25_d', 'JAR 25.629(b)(1)', 'Flatter i dywergencja',
                    'brak niestateczności aeroelastycznej w obwiedni VD/MD powiększonej o 15 % EAS '
                    'przy stałych liczbie Macha i wysokości; przypadki bez uszkodzeń '
                    '(por. CS 25.629(b)(1), EASA CS-25 Amendment 2)'),
    # ---------------------------------------------------------------- spoza wyjątków JAR
    'lsa.1': _r('easa_cs_lsa', 'CS-LSA.1', 'Stosowalność',
                'MTOM ≤ 600 kg (650 kg wodnosamoloty), nie więcej niż 2 miejsca, VS0 ≤ 45 kt CAS, jeden silnik nieturbinowy'),
    'lsa.337': _r('easa_cs_lsa', 'CS-LSA (ASTM F2245, 4.2)', 'Współczynniki obciążeń manewrowych', 'n+ ≥ 4,0; n− ≤ −2,0'),
    'cs22.341': _r('easa_cs22', 'CS 22.341 (Amdt 3)', 'Obciążenia od podmuchu 1-cos',
                   'podmuch dyskretny 1-cos, H/c = 12,17 + 0,191·µg, Kg = 0,96·µ/(0,475 + µ), µ = µg/(H/c)'),
    'cs22.1505': _r('easa_cs22', 'CS 22.1505', 'Prędkość nieprzekraczalna VNE', 'VNE ≤ 0,9 VD'),
    'ul.optout': _r('eu_2018_1139', 'UE 2018/1139 art. 2 ust. 8', 'Samoloty ultralekkie (opt-out krajowy)',
                    'MTOM ≤ 600 kg (650 kg wodne), nie więcej niż 2 osoby, VS0 ≤ 45 kt CAS'),
    'ul.115': _r('eu_2018_1139', 'klasyfikacja krajowa UL-115 (t.j. Dz. U. z 2025 r. poz. 1137)', 'Mikrolot jednoosobowy UL-115',
                 'masa pustego ≤ 115 kg, instalacja paliwowa ≤ 20 l, Vmax ≤ 55 kt CAS, obciążenie powierzchni pustego ≤ 10 kg/m²'),
    'ltf.337': _r('eu_2018_1139', 'LTF-UL § 337', 'Współczynniki obciążeń manewrowych UL', 'n+ = 4,0; n− = −2,0'),
    'uas.ops': _r('eu_2019_947', 'UE 2019/947 art. 3–6', 'Kategorie operacji UAS',
                  'kategoria operacji (otwarta, szczególna, certyfikowana) wynika z oceny ryzyka operacji, nie z MTOM'),
    'stanag.337': _r('stanag_4671', 'STANAG 4671 USAR.337', 'Współczynniki obciążeń manewrowych UAV',
                     'n+ = 2,1 + 10900/(W + 4536), W w kg, nie musi przekraczać 3,8; n− = −0,4·n+'),
    'stanag.303': _r('stanag_4671', 'STANAG 4671 USAR.303', 'Współczynnik bezpieczeństwa', 'ν = 1,5'),
}


def rule(rule_id):
    found = RULES[rule_id]
    return {**found, 'id': rule_id, 'document': DOCUMENTS[found['doc']]}


def cite(rule_id):
    """Paragraf w brzmieniu wyjątków, np. „JAR 23.337(a)”."""
    return RULES[rule_id]['paragraph']


def lit_key(rule_id):
    """Klucz pozycji literatury (rozdziału wyjątków) dla znacznika {lit:…} raportu."""
    return 'reg_' + RULES[rule_id]['doc']


def reference(rule_id):
    """Pełne odwołanie tekstowe: paragraf, rozdział i adres dokumentu."""
    found = rule(rule_id)
    return f"{found['paragraph']} — {found['document']['title']} ({found['document']['url']})"


def report_ref(rule_id):
    """Odwołanie w raporcie: paragraf i numer pozycji literatury."""
    return f"{cite(rule_id)} {{lit:{lit_key(rule_id)}}}"


def literature():
    """Pozycje spisu literatury dla dokumentów przepisów (klucze reg_…)."""
    return {'reg_' + key: doc['citation'] for key, doc in DOCUMENTS.items()}


_PARAGRAPH = re.compile(r'(JAR-VLA \d+(?:\([a-z0-9]+\))*|JAR 2[235]\.\d+(?:\([a-z0-9]+\))*|CS[- ]22\.\d+(?: \(Amdt 3\))?|'
                        r'CS-LSA[^;,]*|STANAG 4671 USAR\.\d+|UE 20\d\d/\d+[^;,)]*|LTF-UL § \d+|'
                        r'klasyfikacja krajowa UL-115 \([^)]*\))')


def find_rules(text):
    """Identyfikatory wymagań, których paragrafy cytuje tekst (w kolejności wystąpienia)."""
    text = text or ''
    found = []
    by_paragraph = {}
    for key, value in RULES.items():
        by_paragraph.setdefault(value['paragraph'], key)
    for match in _PARAGRAPH.finditer(text):
        paragraph = match.group(1).strip()
        key = by_paragraph.get(paragraph)
        # Podpunkt (np. „JAR 23.337(b)(1)”) należy do najbliższego zapisanego punktu („JAR 23.337(b)”).
        trimmed = paragraph
        while key is None and trimmed.endswith(')') and '(' in trimmed:
            trimmed = trimmed[:trimmed.rindex('(')]
            key = by_paragraph.get(trimmed)
        if key is None:
            # Paragraf bez litery punktu (np. „JAR 23.337”) wskazuje pierwsze wymaganie tego paragrafu.
            stem = re.sub(r'\(.*$', '', paragraph)
            key = next((k for p, k in by_paragraph.items() if re.sub(r'\(.*$', '', p) == stem), None)
        if key and key not in found:
            found.append(key)
    return found


def catalog_for_frontend():
    return {'course_page': COURSE_PAGE,
            'documents': {key: {k: doc[k] for k in ('regulation', 'chapter', 'title', 'url')} for key, doc in DOCUMENTS.items()},
            'rules': {key: {**{k: value[k] for k in ('paragraph', 'title', 'text')}, 'doc': value['doc'],
                            'url': DOCUMENTS[value['doc']]['url']} for key, value in RULES.items()}}
