"""Zadanie kolokwialne I (BIPOL I): skrzydło, obwiednia JAR-23 i obciążenia płata.

Treść: scraped_materials/bipol/zadanie_kolokwialne_1.pdf. Dane zależą od liczby liter
imienia (X) i nazwiska (Y). Siła nośna na czterech paskach półrozpiętości wg Schrenka,
jak w arkuszach Wing_load_taper_*.pdf do wykładu 12: L_i = (Q/S)·Δy·(c_i + c_e,i)/2,
siła tnąca i moment gnący sumowane od końcówki do wewnętrznej krawędzi paska.
Obwiednia wg JAR-23 §23.321–23.341 (te same zasady ma CS-23 Amdt 4).
"""
import math

from calculations.calc_sheet import Sheet, tex_value, KG, M, M2, MS, N_, NM2, RAD
from calculations.envelope import cs23_speed_factors

G, RHO0 = 9.81, 1.225               # wartości z arkuszy kursu
KT, LB_PER_KG, PSF = 0.514444, 2.20462262, 47.880259
VS0_MAX_KT = 61.0                   # JAR-23.49(c)
U_B, U_C, U_D = 20.12, 15.24, 7.62  # 66, 50 i 25 ft/s, JAR-23.333(c)
SAFETY = 1.5                        # JAR-23.303
SLICES = 4
FUEL_SPAN = (0.25, 0.75)
CATEGORIES = {1: ('normal', 'normalna'), 2: ('commuter', 'transportu lokalnego (commuter)'),
              3: ('utility', 'użytkowa'), 4: ('aerobatic', 'akrobacyjna')}
TASK = 'zadanie_kolokwialne_1.pdf'
NM, KTU, LB, PSFU = r'\mathrm{N\,m}', r'\mathrm{kt}', r'\mathrm{lb}', r'\mathrm{lbf/ft^2}'


def letters(text):
    """Liczba liter (bez spacji, łączników i apostrofów), jak w treści zadania."""
    return sum(ch.isalpha() for ch in str(text or ''))


def _validate(x, y):
    for name, value in (('X', x), ('Y', y)):
        if type(value) is not int or not 1 <= value <= 40:
            raise ValueError(f'{name}: podaj liczbę liter od 1 do 40.')


def _chord_area(c_r, lam, b, u, v):
    """Pole płata trapezowego między przekrojami y = u i y = v (jedna połówka)."""
    return c_r * ((v - u) - (1 - lam) * (v * v - u * u) / b) if v > u else 0.0


def schrenk_strips(S, b, lam, ws, slices=SLICES):
    """Paski półrozpiętości wg arkusza Wing_load_taper: siła nośna przy n = 1 i ciężarze ws·S."""
    c_r, dy, c_e0 = 2 * S / (b * (1 + lam)), b / 2 / slices, 4 * S / (math.pi * b)
    rows = []
    for i in range(1, slices + 1):
        y_i = (i - 0.5) * dy
        c_i = c_r * (1 - (1 - lam) * 2 * y_i / b)
        c_e = c_e0 * math.sqrt(1 - (2 * y_i / b) ** 2)
        ratio = (c_i + c_e) / (2 * c_i)
        rows.append(dict(i=i, y=y_i, y_inner=y_i - dy / 2, c=c_i, c_e=c_e, area=c_i * dy, cz_ratio=ratio,
                         lift_t=ws * c_i * dy, lift_e=ws * c_e * dy, lift=ws * c_i * dy * ratio))
    return rows


def shear_moment(rows, net):
    """Siła tnąca i moment gnący w wewnętrznej krawędzi każdego paska (obciążenia skupione w y_i)."""
    return [(sum(net[i:]), sum(p * (r['y'] - rows[i]['y_inner']) for p, r in zip(net[i:], rows[i:])))
            for i in range(len(rows))]


def _bound(s, key, sym, rule_value, base, low, ws_psf, label):
    """Współczynnik JAR-23.335 malejący liniowo dla W/S > 20 lbf/ft² (do `low` przy 100)."""
    if ws_psf <= 20:
        return s.given(key, sym, base, '', 2, label, 'JAR-23.335')
    return s.calc(key, sym, rf'{tex_value(base, 2)}-\left({tex_value(base, 2)}-{tex_value(low, 2)}\right)\frac{{(W/S)-20}}{{80}}',
                  rf'{tex_value(base, 2)}-{tex_value(base - low, 2)}\cdot\frac{{[[WS_psf]]-20}}{{80}}', rule_value, '', 3,
                  label + ' (zmniejszony liniowo powyżej 20 lbf/ft²)', 'JAR-23.335(a)(1)(iv), (b)(4)',
                  check=lambda v: base - (base - low) * (v.WS_psf - 20) / 80)


def solve_exam1(x, y):
    """Pełne rozwiązanie zadania kolokwialnego I dla danych X, Y."""
    _validate(x, y)
    s = Sheet()
    k = (x + y) % 4 + 1
    category, category_label = CATEGORIES[k]

    # -- dane ---------------------------------------------------------------------------------
    s.section('exam', 'data', 'Dane zadania', TASK)
    s.given('X', 'X', x, '', 0, 'Liczba liter imienia')
    s.given('Y', 'Y', y, '', 0, 'Liczba liter nazwiska')
    m = (x + y) * 100.0
    s.calc('m', r'm_{TO}', r'(X+Y)\cdot 100', r'([[X]]+[[Y]])\cdot 100', m, KG, 0, 'Masa startowa',
           check=lambda v: (v.X + v.Y) * 100)
    m_f, m_s = m / 8, m / 6
    s.calc('m_f', r'm_{p}', r'\frac{m_{TO}}{8}', r'\frac{[[m]]}{8}', m_f, KG, 1,
           'Masa paliwa, między 0,25 i 0,75 półrozpiętości', check=lambda v: v.m / 8)
    s.calc('m_s', r'm_{str}', r'\frac{m_{TO}}{6}', r'\frac{[[m]]}{6}', m_s, KG, 1, 'Masa struktury płata',
           check=lambda v: v.m / 6)
    s.calc('AR', r'\Lambda', 'X', '', float(x), '', 0, 'Wydłużenie geometryczne', check=lambda v: v.X, deps=['X'])
    lam = x / (x + y)
    s.calc('lam', r'\lambda', r'\frac{X}{X+Y}', r'\frac{[[X]]}{[[X]]+[[Y]]}', lam, '', 4, 'Zbieżność',
           check=lambda v: v.X / (v.X + v.Y))
    s.calc('kat', 'k', r'\left[(X+Y)\bmod 4\right]+1', r'\left[([[X]]+[[Y]])\bmod 4\right]+1', float(k), '', 0,
           f'Kategoria: {category_label}', check=lambda v: (v.X + v.Y) % 4 + 1)
    s.given('Cz_maxf', r'C_{z\,max,kl}', 2.0, '', 2, 'Maksymalny współczynnik siły nośnej z klapami')
    s.given('Cz_max', r'C_{z\,max}', 1.4, '', 2, 'Maksymalny współczynnik siły nośnej w konfiguracji gładkiej')
    s.given('Cz_min', r'C_{z\,min}', -1.1, '', 2, 'Minimalny współczynnik siły nośnej')
    s.given('Cx_min', r'C_{x\,min}', 0.04, '', 3, 'Minimalny współczynnik oporu',
            note='W metodzie JAR-23 nie wpływa na wyznaczane wielkości: VC wynika z reguły 33√(W/S), '
                 'a obwiednię wyznacza się dla C_N ≈ C_z.')
    s.given('e', 'e', 0.9, '', 2, 'Współczynnik Oswalda')
    s.given('a_inf', r'a_\infty', 2 * math.pi, RAD, 4, 'Gradient siły nośnej profilu dC_z/dα∞ = 2π')
    s.given('g', 'g', G, r'\mathrm{m/s^2}', 2, 'Przyspieszenie ziemskie')
    s.given('rho0', r'\rho_0', RHO0, r'\mathrm{kg/m^3}', 3, 'Gęstość powietrza na poziomie morza')

    # -- geometria ----------------------------------------------------------------------------
    s.section('exam', 'geometry', 'Parametry geometryczne skrzydła', 'JAR-23.49(c); płat trapezowy')
    s.given('VS0_kt', r'V_{S0}', VS0_MAX_KT, KTU, 0, 'Największa dopuszczalna prędkość przeciągnięcia z klapami',
            'JAR-23.49(c)', 'Najmniejsza powierzchnia skrzydła spełniająca wymaganie — przy prędkości granicznej.')
    vs0 = VS0_MAX_KT * KT
    s.calc('VS0', r'V_{S0}', r'61\cdot 0{,}5144', r'[[VS0_kt]]\cdot 0{,}5144', vs0, MS, 2, 'V_S0 w m/s',
           check=lambda v: v.VS0_kt * KT)
    S = 2 * m * G / (RHO0 * vs0 ** 2 * 2.0)
    s.calc('S', 'S', r'\frac{2\,m_{TO}\,g}{\rho_0\,V_{S0}^2\,C_{z\,max,kl}}',
           r'\frac{2\cdot[[m]]\cdot[[g]]}{[[rho0]]\cdot[[VS0]]^2\cdot[[Cz_maxf]]}', S, M2, 2, 'Powierzchnia skrzydła',
           check=lambda v: 2 * v.m * v.g / (v.rho0 * v.VS0 ** 2 * v.Cz_maxf))
    b = math.sqrt(x * S)
    s.calc('b', 'b', r'\sqrt{\Lambda S}', r'\sqrt{[[AR]]\cdot[[S]]}', b, M, 3, 'Rozpiętość',
           check=lambda v: math.sqrt(v.AR * v.S))
    c_r = 2 * S / (b * (1 + lam))
    s.calc('c_r', 'c_r', r'\frac{2S}{b\,(1+\lambda)}', r'\frac{2\cdot[[S]]}{[[b]]\cdot(1+[[lam]])}', c_r, M, 3,
           'Cięciwa u nasady', check=lambda v: 2 * v.S / (v.b * (1 + v.lam)))
    c_t = lam * c_r
    s.calc('c_t', 'c_k', r'\lambda\,c_r', r'[[lam]]\cdot[[c_r]]', c_t, M, 3, 'Cięciwa na końcówce',
           check=lambda v: v.lam * v.c_r)
    s.calc('c_g', 'c_g', r'\frac{S}{b}', r'\frac{[[S]]}{[[b]]}', S / b, M, 3, 'Średnia cięciwa geometryczna',
           check=lambda v: v.S / v.b)
    c_a = 2 / 3 * c_r * (1 + lam + lam ** 2) / (1 + lam)
    s.calc('c_a', 'c_a', r'\frac{2}{3}\,c_r\,\frac{1+\lambda+\lambda^2}{1+\lambda}',
           r'\frac{2}{3}\cdot[[c_r]]\cdot\frac{1+[[lam]]+[[lam]]^2}{1+[[lam]]}', c_a, M, 3,
           'Średnia cięciwa aerodynamiczna (SCA)', check=lambda v: 2 / 3 * v.c_r * (1 + v.lam + v.lam ** 2) / (1 + v.lam))
    s.calc('y_a', 'y_{SCA}', r'\frac{b}{6}\,\frac{1+2\lambda}{1+\lambda}', r'\frac{[[b]]}{6}\cdot\frac{1+2\cdot[[lam]]}{1+[[lam]]}',
           b / 6 * (1 + 2 * lam) / (1 + lam), M, 3, 'Położenie SCA od płaszczyzny symetrii',
           check=lambda v: v.b / 6 * (1 + 2 * v.lam) / (1 + v.lam))

    # -- obwiednia ----------------------------------------------------------------------------
    s.section('exam', 'envelope', f'Obwiednia obciążeń wg JAR-23 — kategoria {category_label}', 'JAR-23 §23.321–23.341')
    W = m * G
    s.calc('W', 'Q', 'm_{TO}\\,g', '[[m]]\\cdot[[g]]', W, N_, 0, 'Ciężar samolotu', check=lambda v: v.m * v.g)
    ws = W / S
    s.calc('WS', 'W/S', r'\frac{Q}{S}', r'\frac{[[W]]}{[[S]]}', ws, NM2, 1, 'Obciążenie powierzchni',
           check=lambda v: v.W / v.S)
    ws_psf = ws / PSF
    s.calc('WS_psf', 'W/S', r'\frac{W/S\,[\mathrm{N/m^2}]}{47{,}88}', r'\frac{[[WS]]}{47{,}88}', ws_psf, PSFU, 2,
           'Obciążenie powierzchni w jednostkach przepisu', check=lambda v: v.WS / PSF)
    w_lb = m * LB_PER_KG
    s.calc('W_lb', 'W', r'2{,}2046\,m_{TO}', r'2{,}2046\cdot[[m]]', w_lb, LB, 0, 'Masa startowa w funtach',
           check=lambda v: v.m * LB_PER_KG)
    if category in ('normal', 'commuter'):
        n_formula = 2.1 + 24000 / (w_lb + 10000)
        s.calc('n_wz', r'n_{wz}', r'2{,}1+\frac{24000}{W+10000}', r'2{,}1+\frac{24000}{[[W_lb]]+10000}', n_formula, '', 3,
               'Współczynnik obciążenia z wzoru przepisu', 'JAR-23.337(a)(1)', check=lambda v: 2.1 + 24000 / (v.W_lb + 10000))
        n1 = min(3.8, max(2.5, n_formula))
        s.calc('n1', 'n_1', r'\min\left(3{,}8;\;\max\left(2{,}5;\;n_{wz}\right)\right)',
               r'\min\left(3{,}8;\;\max\left(2{,}5;\;[[n_wz]]\right)\right)', n1, '', 2,
               'Dodatni manewrowy współczynnik obciążenia', 'JAR-23.337(a)(1)',
               check=lambda v: min(3.8, max(2.5, v.n_wz)))
    else:
        n1 = 4.4 if category == 'utility' else 6.0
        s.given('n1', 'n_1', n1, '', 1, 'Dodatni manewrowy współczynnik obciążenia',
                'JAR-23.337(a)(2)' if category == 'utility' else 'JAR-23.337(a)(3)')
    share = 0.5 if category == 'aerobatic' else 0.4
    n2 = -share * n1
    s.calc('n2', 'n_2', rf'-{tex_value(share, 1)}\,n_1', rf'-{tex_value(share, 1)}\cdot[[n1]]', n2, '', 2,
           'Ujemny manewrowy współczynnik obciążenia', 'JAR-23.337(b)', check=lambda v: -share * v.n1)
    vs1 = math.sqrt(2 * W / (RHO0 * S * 1.4))
    s.calc('VS1', r'V_{S1}', r'\sqrt{\frac{2Q}{\rho_0 S C_{z\,max}}}', r'\sqrt{\frac{2\cdot[[W]]}{[[rho0]]\cdot[[S]]\cdot[[Cz_max]]}}',
           vs1, MS, 2, 'Prędkość przeciągnięcia w konfiguracji gładkiej', check=lambda v: math.sqrt(2 * v.W / (v.rho0 * v.S * v.Cz_max)))
    vsm = math.sqrt(2 * W / (RHO0 * S * 1.1))
    s.calc('VSm', r'V_{S,neg}', r'\sqrt{\frac{2Q}{\rho_0 S \left|C_{z\,min}\right|}}',
           r'\sqrt{\frac{2\cdot[[W]]}{[[rho0]]\cdot[[S]]\cdot\left|[[Cz_min]]\right|}}', vsm, MS, 2,
           'Prędkość przeciągnięcia w locie odwróconym', check=lambda v: math.sqrt(2 * v.W / (v.rho0 * v.S * abs(v.Cz_min))))
    v_a = vs1 * math.sqrt(n1)
    s.calc('VA', 'V_A', r'V_{S1}\sqrt{n_1}', r'[[VS1]]\cdot\sqrt{[[n1]]}', v_a, MS, 2, 'Prędkość manewrowa',
           'JAR-23.335(c)', check=lambda v: v.VS1 * math.sqrt(v.n1))
    v_g = vsm * math.sqrt(-n2)
    s.calc('VG', 'V_G', r'V_{S,neg}\sqrt{\left|n_2\right|}', r'[[VSm]]\cdot\sqrt{\left|[[n2]]\right|}', v_g, MS, 2,
           'Prędkość manewrowa ujemna', check=lambda v: v.VSm * math.sqrt(-v.n2))
    family = 'aerobatic' if category == 'aerobatic' else 'utility' if category == 'utility' else 'normal'
    k_c, k_d = cs23_speed_factors(family, ws_psf)
    k_c0, k_d0 = (36.0 if family == 'aerobatic' else 33.0), {'aerobatic': 1.55, 'utility': 1.50}.get(family, 1.40)
    _bound(s, 'k_C', 'k_C', k_c, k_c0, 28.6, ws_psf, 'Współczynnik minimalnej prędkości przelotowej')
    vc_min_kt = k_c * math.sqrt(ws_psf)
    s.calc('VCmin_kt', r'V_{C,min}', r'k_C\sqrt{W/S}', r'[[k_C]]\cdot\sqrt{[[WS_psf]]}', vc_min_kt, KTU, 1,
           'Minimalna obliczeniowa prędkość przelotowa', 'JAR-23.335(a)(1)', check=lambda v: v.k_C * math.sqrt(v.WS_psf))
    vc_min = vc_min_kt * KT
    s.calc('VCmin', r'V_{C,min}', r'0{,}5144\,V_{C,min}\,[\mathrm{kt}]', r'0{,}5144\cdot[[VCmin_kt]]', vc_min, MS, 2,
           'V_C,min w m/s', check=lambda v: v.VCmin_kt * KT)
    v_c = max(vc_min, v_a)
    s.calc('VC', 'V_C', r'\max\left(V_{C,min};\;V_A\right)', r'\max\left([[VCmin]];\;[[VA]]\right)', v_c, MS, 2,
           'Obliczeniowa prędkość przelotowa', 'JAR-23.335(a)',
           note='Zadanie nie podaje V_H, więc przyjmuje się najmniejszą dopuszczalną V_C. '
                + ('Tu V_A > V_C,min, więc V_C podniesiono do V_A, żeby punkt A leżał przed punktem C.' if v_a > vc_min else ''),
           check=lambda v: max(v.VCmin, v.VA))
    _bound(s, 'k_D', 'k_D', k_d, k_d0, 1.35, ws_psf, 'Współczynnik minimalnej prędkości nurkowania')
    v_d = max(1.25 * v_c, k_d * vc_min)
    s.calc('VD', 'V_D', r'\max\left(1{,}25\,V_C;\;k_D\,V_{C,min}\right)', r'\max\left(1{,}25\cdot[[VC]];\;[[k_D]]\cdot[[VCmin]]\right)',
           v_d, MS, 2, 'Obliczeniowa prędkość nurkowania', 'JAR-23.335(b)', check=lambda v: max(1.25 * v.VC, v.k_D * v.VCmin))
    a = 2 * math.pi / (1 + 2 / (0.9 * x))
    s.calc('a', 'a', r'\frac{a_\infty}{1+\frac{a_\infty}{\pi e \Lambda}}', r'\frac{[[a_inf]]}{1+\frac{[[a_inf]]}{\pi\cdot[[e]]\cdot[[AR]]}}',
           a, RAD, 3, 'Gradient siły nośnej płata', check=lambda v: v.a_inf / (1 + v.a_inf / (math.pi * v.e * v.AR)))

    def gust(mass):
        ws_m = mass * G / S
        mu = 2 * ws_m / (RHO0 * c_a * a * G)
        kg = 0.88 * mu / (5.3 + mu)
        return ws_m, mu, kg
    _, mu, kg = gust(m)
    s.calc('mu', r'\mu_g', r'\frac{2\,(W/S)}{\rho_0\,c_a\,a\,g}', r'\frac{2\cdot[[WS]]}{[[rho0]]\cdot[[c_a]]\cdot[[a]]\cdot[[g]]}',
           mu, '', 2, 'Masowy parametr samolotu', 'JAR-23.341', check=lambda v: 2 * v.WS / (v.rho0 * v.c_a * v.a * v.g))
    s.calc('Kg', 'K_g', r'\frac{0{,}88\,\mu_g}{5{,}3+\mu_g}', r'\frac{0{,}88\cdot[[mu]]}{5{,}3+[[mu]]}', kg, '', 3,
           'Współczynnik złagodzenia podmuchu', 'JAR-23.341', check=lambda v: 0.88 * v.mu / (5.3 + v.mu))
    gusts = []
    commuter = category == 'commuter'
    if commuter:
        s.given('U_B', 'U_B', U_B, MS, 2, 'Prędkość podmuchu przy V_B (66 ft/s)', 'JAR-23.333(c)(1)(i)')
        c_line = RHO0 * kg * U_B * a / (2 * ws)
        s.calc('k_B', r'k_B', r'\frac{\rho_0 K_g U_B a}{2\,W/S}', r'\frac{[[rho0]]\cdot[[Kg]]\cdot[[U_B]]\cdot[[a]]}{2\cdot[[WS]]}',
               c_line, r'\mathrm{s/m}', 5, 'Nachylenie linii podmuchu 66 ft/s', check=lambda v: v.rho0 * v.Kg * v.U_B * v.a / (2 * v.WS))
        v_b1 = vs1 ** 2 / 2 * (c_line + math.sqrt(c_line ** 2 + 4 / vs1 ** 2))
        s.calc('VB1', r'V_{B,1}', r'\frac{V_{S1}^2}{2}\left(k_B+\sqrt{k_B^2+\frac{4}{V_{S1}^2}}\right)',
               r'\frac{[[VS1]]^2}{2}\cdot\left([[k_B]]+\sqrt{[[k_B]]^2+\frac{4}{[[VS1]]^2}}\right)', v_b1, MS, 2,
               'Przecięcie linii C_z,max z linią podmuchu 66 ft/s', 'JAR-23.335(d)(1)',
               check=lambda v: v.VS1 ** 2 / 2 * (v.k_B + math.sqrt(v.k_B ** 2 + 4 / v.VS1 ** 2)))
    s.given('U_C', 'U_C', U_C, MS, 2, 'Prędkość podmuchu przy V_C (50 ft/s)', 'JAR-23.333(c)(1)(i)')
    s.given('U_D', 'U_D', U_D, MS, 2, 'Prędkość podmuchu przy V_D (25 ft/s)', 'JAR-23.333(c)(1)(ii)')
    dn = lambda u, v: RHO0 * kg * u * v * a / (2 * ws)  # noqa: E731
    dn_c = dn(U_C, v_c)
    s.calc('dn_C', r'\Delta n_C', r'\frac{\rho_0 K_g U_C V_C a}{2\,W/S}',
           r'\frac{[[rho0]]\cdot[[Kg]]\cdot[[U_C]]\cdot[[VC]]\cdot[[a]]}{2\cdot[[WS]]}', dn_c, '', 3,
           'Przyrost współczynnika obciążenia od podmuchu przy V_C', 'JAR-23.341',
           check=lambda v: v.rho0 * v.Kg * v.U_C * v.VC * v.a / (2 * v.WS))
    if commuter:
        v_b = min(v_b1, vs1 * math.sqrt(1 + dn_c), v_c)
        s.calc('VB', 'V_B', r'\min\left(V_{B,1};\;V_{S1}\sqrt{1+\Delta n_C};\;V_C\right)',
               r'\min\left([[VB1]];\;[[VS1]]\cdot\sqrt{1+[[dn_C]]};\;[[VC]]\right)', v_b, MS, 2,
               'Prędkość dla największej intensywności podmuchu', 'JAR-23.335(d)',
               check=lambda v: min(v.VB1, v.VS1 * math.sqrt(1 + v.dn_C), v.VC))
        dn_b = dn(U_B, v_b)
        s.calc('dn_B', r'\Delta n_B', r'k_B\,V_B', r'[[k_B]]\cdot[[VB]]', dn_b, '', 3,
               'Przyrost współczynnika obciążenia od podmuchu przy V_B', 'JAR-23.341', check=lambda v: v.k_B * v.VB)
        n_b, n_b_neg = min(1 + dn_b, (v_b / vs1) ** 2), max(1 - dn_b, -(v_b / vsm) ** 2)
        s.calc('nB', 'n_B', r'\min\left(1+\Delta n_B;\;\left(\frac{V_B}{V_{S1}}\right)^2\right)',
               r'\min\left(1+[[dn_B]];\;\left(\frac{[[VB]]}{[[VS1]]}\right)^2\right)', n_b, '', 3,
               'Dodatni współczynnik obciążenia przy V_B, ograniczony linią C_z,max',
               note='V_B z JAR-23.335(d) może leżeć poniżej przecięcia linii podmuchu z linią C_z,max; '
                    'płat nie wytworzy wtedy większej siły nośnej niż przy C_z,max.',
               check=lambda v: min(1 + v.dn_B, (v.VB / v.VS1) ** 2))
        s.calc('nB_m', "n_B'", r'\max\left(1-\Delta n_B;\;-\left(\frac{V_B}{V_{S,neg}}\right)^2\right)',
               r'\max\left(1-[[dn_B]];\;-\left(\frac{[[VB]]}{[[VSm]]}\right)^2\right)', n_b_neg, '', 3,
               'Ujemny współczynnik obciążenia przy V_B, ograniczony linią C_z,min',
               check=lambda v: max(1 - v.dn_B, -(v.VB / v.VSm) ** 2))
        gusts.append(('B', v_b, U_B, dn_b, n_b, n_b_neg))
    gusts.append(('C', v_c, U_C, dn_c, 1 + dn_c, 1 - dn_c))
    dn_d = dn(U_D, v_d)
    s.calc('dn_D', r'\Delta n_D', r'\frac{\rho_0 K_g U_D V_D a}{2\,W/S}',
           r'\frac{[[rho0]]\cdot[[Kg]]\cdot[[U_D]]\cdot[[VD]]\cdot[[a]]}{2\cdot[[WS]]}', dn_d, '', 3,
           'Przyrost współczynnika obciążenia od podmuchu przy V_D', 'JAR-23.341',
           check=lambda v: v.rho0 * v.Kg * v.U_D * v.VD * v.a / (2 * v.WS))
    gusts.append(('D', v_d, U_D, dn_d, 1 + dn_d, 1 - dn_d))
    n_max = max([n1] + [g_[4] for g_ in gusts])
    n_min = min([n2] + [g_[5] for g_ in gusts])
    pos = [('n_1', '[[n1]]')] + ([('n_B', '[[nB]]')] if commuter else []) + [
        (r'1+\Delta n_C', '1+[[dn_C]]'), (r'1+\Delta n_D', '1+[[dn_D]]')]
    neg = [('n_2', '[[n2]]')] + ([("n_B'", '[[nB_m]]')] if commuter else []) + [
        (r'1-\Delta n_C', '1-[[dn_C]]'), (r'1-\Delta n_D', '1-[[dn_D]]')]
    join = lambda terms, i: r';\;'.join(t[i] for t in terms)  # noqa: E731
    s.calc('n_max', r'n_{max}', rf'\max\left({join(pos, 0)}\right)', rf'\max\left({join(pos, 1)}\right)', n_max, '', 2,
           'Wymiarujący dodatni współczynnik obciążeń dopuszczalnych',
           check=lambda v: max([v.n1, 1 + v.dn_C, 1 + v.dn_D] + ([v.nB] if commuter else [])))
    s.calc('n_min', r'n_{min}', rf'\min\left({join(neg, 0)}\right)', rf'\min\left({join(neg, 1)}\right)', n_min, '', 2,
           'Wymiarujący ujemny współczynnik obciążeń dopuszczalnych',
           check=lambda v: min([v.n2, 1 - v.dn_C, 1 - v.dn_D] + ([v.nB_m] if commuter else [])))
    s.given('f', 'f', SAFETY, '', 1, 'Współczynnik bezpieczeństwa', 'JAR-23.303')
    s.calc('n_ult', r'n_{obl}', r'f\,n_{max}', r'[[f]]\cdot[[n_max]]', SAFETY * n_max, '', 2,
           'Obliczeniowy (niszczący) współczynnik obciążeń', check=lambda v: v.f * v.n_max)

    # -- Schrenk ------------------------------------------------------------------------------
    s.section('exam', 'schrenk', 'Rozkład siły nośnej i C_z wzdłuż rozpiętości (Schrenk, 4 paski)',
              'Wykład 12; arkusze Wing_load_taper_*.pdf')
    s.given('N', 'N', SLICES, '', 0, 'Liczba pasków półrozpiętości')
    dy = b / 2 / SLICES
    s.calc('dy', r'\Delta y', r'\frac{b}{2N}', r'\frac{[[b]]}{2\cdot[[N]]}', dy, M, 4, 'Szerokość paska',
           check=lambda v: v.b / (2 * v.N))
    c_e0 = 4 * S / (math.pi * b)
    s.calc('c_e0', r'c_{e,0}', r'\frac{4S}{\pi b}', r'\frac{4\cdot[[S]]}{\pi\cdot[[b]]}', c_e0, M, 3,
           'Cięciwa przykadłubowa płata eliptycznego o tej samej powierzchni i rozpiętości', check=lambda v: 4 * v.S / (math.pi * v.b))
    s.table('schrenk_tab', 'Paski Schrenka (n = 1)',
            r'y_i=\left(i-\tfrac12\right)\Delta y,\quad c_i=c_r\left[1-(1-\lambda)\frac{2y_i}{b}\right],\quad'
            r'c_{e,i}=c_{e,0}\sqrt{1-\left(\frac{2y_i}{b}\right)^2},\quad \frac{c_{z,i}}{C_z}=\frac{c_i+c_{e,i}}{2c_i},\quad'
            r'L_i=\frac{Q}{S}\,c_i\,\Delta y\,\frac{c_{z,i}}{C_z}', deps=['dy', 'c_e0', 'c_r', 'lam', 'b', 'W', 'S'])
    fuel_lo, fuel_hi = (FUEL_SPAN[0] * b / 2, FUEL_SPAN[1] * b / 2)
    fuel_area = _chord_area(c_r, lam, b, fuel_lo, fuel_hi)
    rows = schrenk_strips(S, b, lam, ws)
    for r in rows:
        overlap = _chord_area(c_r, lam, b, max(r['y_inner'], fuel_lo), min(r['y_inner'] + dy, fuel_hi))
        r.update(cz_at_max=1.4 * r['cz_ratio'], m_struct=m_s * r['area'] / S, m_fuel=m_f / 2 * overlap / fuel_area)
    sum_l = sum(r['lift'] for r in rows)
    s.calc('sumL', r'\sum L_i', r'\sum_{i=1}^{N} L_i', ' + '.join(tex_value(r['lift'], 1) for r in rows), sum_l, N_, 1,
           'Siła nośna półskrzydła przy n = 1', check=lambda v: sum(r['lift'] for r in rows), deps=['schrenk_tab'])
    s.calc('chk', r'\frac{\sum L_i}{Q/2}', r'\frac{\sum L_i}{Q/2}', r'\frac{[[sumL]]}{[[W]]/2}', sum_l / (W / 2), '', 3,
           'Kontrola: powinna wynosić około 1 (błąd dyskretyzacji na 4 paskach)', check=lambda v: v.sumL / (v.W / 2))
    peak = max(rows, key=lambda r: r['cz_ratio'])
    s.given('cz_peak', r'\left(c_z/C_z\right)_{max}', peak['cz_ratio'], '', 3,
            f'Największe lokalne c_z — pasek {peak["i"]}; tam zaczyna się przeciągnięcie', 'Tabela Schrenka')
    s.calc('Mg_approx', r'M_{g,przybl}', r'0{,}44\,\frac{Q}{2}\,\frac{b}{2}', r'0{,}44\cdot\frac{[[W]]}{2}\cdot\frac{[[b]]}{2}',
           0.44 * W / 2 * b / 2, NM, 0, 'Przybliżony moment gnący u nasady przy n = 1 (bez odciążenia masami)',
           'Arkusz Wing_load_taper', check=lambda v: 0.44 * v.W / 2 * v.b / 2)

    # -- obciążenia ---------------------------------------------------------------------------
    s.section('exam', 'loads', 'Wymiarujący moment gnący i siła tnąca',
              'Wykład 12: V = Σ W·Δy, M = Σ V·Δy; odciążenie masą struktury i paliwa')
    s.table('mass_tab', 'Masy pasków (półskrzydło)',
            r'm_{str,i}=m_{str}\,\frac{c_i\,\Delta y}{S},\qquad m_{p,i}=\frac{m_p}{2}\,'
            r'\frac{S_i^{(0{,}25\div0{,}75)}}{S^{(0{,}25\div0{,}75)}_{1/2}}',
            note='Struktura proporcjonalna do pola paska; paliwo w części półrozpiętości 0,25–0,75, proporcjonalnie do pola.',
            deps=['m_s', 'm_f', 'dy', 'S'])
    s.table('load_tab', 'Obciążenie, siła tnąca i moment gnący',
            r'P_i=n\left[L_i-g\left(m_{str,i}+m_{p,i}\right)\right],\quad T_i=\sum_{j\ge i}P_j,\quad'
            r'M_i=\sum_{j\ge i}P_j\left(y_j-y_i+\tfrac{\Delta y}{2}\right)',
            note='T_i i M_i w wewnętrznej krawędzi paska i; dla i = 1 — u nasady.', deps=['schrenk_tab', 'mass_tab', 'g'])

    net = [r['lift'] - G * (r['m_struct'] + r['m_fuel']) for r in rows]
    unit = shear_moment(rows, net)
    for row, p, (t, mg) in zip(rows, net, unit):
        row.update(p_unit=p, t_unit=t, m_unit=mg, t_limit=n_max * t, m_limit=n_max * mg,
                   t_ult=SAFETY * n_max * t, m_ult=SAFETY * n_max * mg, t_neg=n_min * t, m_neg=n_min * mg)
    t0, m0 = unit[0]
    s.calc('T0_1', r'T_{0}^{(n=1)}', r'\sum_{i=1}^{N}P_i', ' + '.join(tex_value(p, 1) for p in net), t0, N_, 1,
           'Siła tnąca u nasady przy n = 1 (z odciążeniem)', check=lambda v: sum(net), deps=['load_tab'])
    s.calc('M0_1', r'M_{0}^{(n=1)}', r'\sum_{i=1}^{N}P_i\,y_i',
           ' + '.join(rf'{tex_value(p, 1)}\cdot{tex_value(r["y"], 3)}' for p, r in zip(net, rows)), m0, NM, 1,
           'Moment gnący u nasady przy n = 1 (z odciążeniem)', check=lambda v: sum(p * r['y'] for p, r in zip(net, rows)),
           deps=['load_tab'])
    s.calc('T0', 'T_0', r'n_{max}\,T_0^{(n=1)}', r'[[n_max]]\cdot[[T0_1]]', n_max * t0, N_, 0,
           'Wymiarująca siła tnąca u nasady (obciążenie dopuszczalne)', check=lambda v: v.n_max * v.T0_1)
    s.calc('M0', 'M_0', r'n_{max}\,M_0^{(n=1)}', r'[[n_max]]\cdot[[M0_1]]', n_max * m0, NM, 0,
           'Wymiarujący moment gnący u nasady (obciążenie dopuszczalne)', check=lambda v: v.n_max * v.M0_1)
    s.calc('T0_ult', r'T_{0,obl}', r'f\,T_0', r'[[f]]\cdot[[T0]]', SAFETY * n_max * t0, N_, 0,
           'Siła tnąca obliczeniowa (niszcząca)', check=lambda v: v.f * v.T0)
    s.calc('M0_ult', r'M_{0,obl}', r'f\,M_0', r'[[f]]\cdot[[M0]]', SAFETY * n_max * m0, NM, 0,
           'Moment gnący obliczeniowy (niszczący)', check=lambda v: v.f * v.M0)
    s.calc('M0_neg', r'M_{0,neg}', r'n_{min}\,M_0^{(n=1)}', r'[[n_min]]\cdot[[M0_1]]', n_min * m0, NM, 0,
           'Moment gnący u nasady przy n_min (zginanie ujemne)', check=lambda v: v.n_min * v.M0_1)

    # -- sprawdzenie bez paliwa ---------------------------------------------------------------
    s.section('exam', 'zero_fuel', 'Sprawdzenie: samolot bez paliwa',
              'Bez paliwa siła nośna jest mniejsza, ale znika odciążenie płata masą paliwa')
    m_zf = m - m_f
    s.calc('m_zf', r'm_{zf}', r'm_{TO}-m_p', r'[[m]]-[[m_f]]', m_zf, KG, 1, 'Masa bez paliwa', check=lambda v: v.m - v.m_f)
    ws_zf, mu_zf, kg_zf = gust(m_zf)
    s.calc('WS_zf', r'(W/S)_{zf}', r'\frac{m_{zf}\,g}{S}', r'\frac{[[m_zf]]\cdot[[g]]}{[[S]]}', ws_zf, NM2, 1,
           'Obciążenie powierzchni bez paliwa', check=lambda v: v.m_zf * v.g / v.S)
    s.calc('Kg_zf', r'K_{g,zf}', r'\frac{0{,}88\,\mu_{g,zf}}{5{,}3+\mu_{g,zf}},\;\mu_{g,zf}=\frac{2(W/S)_{zf}}{\rho_0 c_a a g}',
           r'\frac{0{,}88\,\mu}{5{,}3+\mu},\;\mu=\frac{2\cdot[[WS_zf]]}{[[rho0]]\cdot[[c_a]]\cdot[[a]]\cdot[[g]]}', kg_zf, '', 3,
           'Współczynnik złagodzenia podmuchu bez paliwa',
           check=lambda v: (lambda mu_: 0.88 * mu_ / (5.3 + mu_))(2 * v.WS_zf / (v.rho0 * v.c_a * v.a * v.g)))
    vs1_zf = vs1 * math.sqrt(m_zf / m)

    def gust_zf(label, v, u):
        n_ = 1 + RHO0 * kg_zf * u * v * a / (2 * ws_zf)
        return min(n_, (v / vs1_zf) ** 2) if label == 'B' else n_
    n_zf = max([n1] + [gust_zf(label, v, u) for label, v, u, *_ in gusts])
    s.calc('n_max_zf', r'n_{max,zf}', r'\max\left(n_1;\;1+\frac{\rho_0 K_{g,zf} U V a}{2\,(W/S)_{zf}}\right)',
           r'\max\left([[n1]];\;' + ';\\;'.join(rf'1+\frac{{[[rho0]]\cdot[[Kg_zf]]\cdot{tex_value(u, 2)}\cdot{tex_value(v, 2)}\cdot[[a]]}}{{2\cdot[[WS_zf]]}}'
                                               for _, v, u, *_ in gusts) + r'\right)',
           n_zf, '', 2, 'Wymiarujący współczynnik obciążeń bez paliwa (n_1 z masy startowej, JAR-23.337)',
           note='Przy V_B podmuch ograniczono linią C_z,max samolotu bez paliwa.' if commuter else '',
           check=lambda v: max([v.n1] + [gust_zf(label, w, u) for label, w, u, *_ in gusts]))
    net_zf = [ws_zf * r['area'] * r['cz_ratio'] - G * r['m_struct'] for r in rows]
    m0_zf = sum(p * r['y'] for p, r in zip(net_zf, rows))
    for row, p, (t, mg) in zip(rows, net_zf, shear_moment(rows, net_zf)):
        row.update(p_unit_zf=p, t_unit_zf=t, m_unit_zf=mg, t_limit_zf=n_zf * t, m_limit_zf=n_zf * mg)
    s.calc('M0_zf', r'M_{0,zf}', r'n_{max,zf}\sum_{i}\left[\frac{(W/S)_{zf}}{(W/S)}L_i-g\,m_{str,i}\right]y_i',
           r'[[n_max_zf]]\cdot' + tex_value(m0_zf, 1), n_zf * m0_zf, NM, 0,
           'Moment gnący u nasady bez paliwa (obciążenie dopuszczalne)', check=lambda v: v.n_max_zf * m0_zf,
           deps=['load_tab'])
    governing = 'zero_fuel' if n_zf * m0_zf > n_max * m0 else 'full'
    s.calc('M0_dim', r'M_{0,wym}', r'\max\left(M_0;\;M_{0,zf}\right)', r'\max\left([[M0]];\;[[M0_zf]]\right)',
           max(n_max * m0, n_zf * m0_zf), NM, 0, 'Moment wymiarujący u nasady (obciążenie dopuszczalne)',
           check=lambda v: max(v.M0, v.M0_zf))

    sheet = s.finalize()
    sections = [dict(key=sec['key'], title=sec['title'], source=sec['source'],
                     entries=[dict(key=e['key'], kind=e['kind'], label=e['label'], tex=e['tex'], note=e['note'],
                                   source=e['source'], value=e['value'] if e['kind'] != 'table' else None,
                                   consistent=e['consistent'])
                              for e in sheet.section_entries(sec['key'])])
                for sec in sheet.sections.values()]
    kmh = lambda v: round(v * 3.6, 1)  # noqa: E731
    stall = [dict(v_kmh=kmh(v_a * i / 18), n=round((i / 18) ** 2 * n1, 3)) for i in range(19)]
    stall_neg = [dict(v_kmh=kmh(v_g * i / 18), n=round((i / 18) ** 2 * n2, 3)) for i in range(19)]
    n_vd_neg = -1.0 if category in ('utility', 'aerobatic') else 0.0
    polygon = (stall + [dict(v_kmh=kmh(v_d), n=n1), dict(v_kmh=kmh(v_d), n=n_vd_neg), dict(v_kmh=kmh(v_c), n=n2)]
               + list(reversed(stall_neg)))
    # Linie podmuchów jako proste od (0; 1); punkty B, C, D z ograniczeniem linią C_z,max.
    gust_pos = [dict(v_kmh=0.0, n=1.0)] + [dict(v_kmh=kmh(v), n=round(1 + d, 3)) for _, v, _, d, *_ in gusts]
    gust_neg = [dict(v_kmh=0.0, n=1.0)] + [dict(v_kmh=kmh(v), n=round(1 - d, 3)) for _, v, _, d, *_ in gusts]
    points = [dict(point='A', v_kmh=kmh(v_a), n=n1), dict(point='D', v_kmh=kmh(v_d), n=n1),
              dict(point='E', v_kmh=kmh(v_d), n=n_vd_neg), dict(point='F', v_kmh=kmh(v_c), n=n2),
              dict(point='G', v_kmh=kmh(v_g), n=n2)]
    points += [dict(point=f'{label}±', v_kmh=kmh(v), n=round(n_pos, 3), n_neg=round(n_neg, 3), u_ms=u)
               for label, v, u, _, n_pos, n_neg in gusts]
    value = lambda key: sheet.entries[key]['value']  # noqa: E731
    return dict(
        x=x, y=y, category=category, category_label=category_label, category_index=k,
        sections=sections,
        consistent=all(e['consistent'] is not False for e in sheet.entries.values()),
        envelope=dict(speeds=dict(v_s_kmh=kmh(vs1), v_a_kmh=kmh(v_a), v_b_kmh=kmh(gusts[0][1]) if commuter else None,
                                  v_c_kmh=kmh(v_c), v_d_kmh=kmh(v_d), v_g_kmh=kmh(v_g)),
                      limits=dict(n_max=round(n_max, 3), n_min=round(n_min, 3), n1=round(n1, 3), n2=round(n2, 3)),
                      maneuver_polygon=polygon, gust_pos=gust_pos, gust_neg=gust_neg, points=points,
                      n_vd_neg=n_vd_neg),
        rows=[{k_: (round(v, 6) if isinstance(v, float) else v) for k_, v in r.items()} for r in rows],
        governing=governing,
        zero_fuel=dict(mass=m_zf, n_max=n_zf, M0=n_zf * m0_zf),
        answers=dict(S=value('S'), b=value('b'), c_r=value('c_r'), c_t=value('c_t'), c_g=value('c_g'), c_a=value('c_a'),
                     n_max=n_max, n_min=n_min, VA_kmh=v_a * 3.6, VC_kmh=v_c * 3.6, VD_kmh=v_d * 3.6,
                     T0=n_max * t0, M0=n_max * m0, M0_dim=value('M0_dim')),
        notes=[
            'JAR-23 zastąpiono przepisami CS-23; Amdt 4 zachowuje te same wzory (§23.321–23.341). '
            'Od Amdt 5 CS-23 opisuje wymagania celu, a obwiednię wyznacza się według norm ASTM.',
            'Prędkości obwiedni są prędkościami równoważnymi (EAS) na poziomie morza.',
            'Paliwo rozłożono na paski proporcjonalnie do pola w części 0,25–0,75 półrozpiętości, '
            'a masę struktury — proporcjonalnie do pola paska. Inny założony rozkład zmieni wynik o kilka procent.',
        ],
    )
