"""Arkusz obliczeń sprawozdania, zapisany jak w Mathcadzie.

Każda obliczona wielkość ma wzór ogólny, podstawienie liczb i wynik z jednostką:
    S = m0·g/(W/S) = 1619,9·9,807/767,8 = 20,69 m².
Dane wejściowe mają źródło (założenie, wymaganie, odczyt z wykresu). Dla danych
tabelarycznych (np. kolejne punkty biegunowej) podaje się jeden wzór i tabelę.

Wzory odpowiadają funkcjom modułów obliczeniowych, a wyniki pochodzą z tego samego
przebiegu run_bipol_project(). Funkcja ``check`` pozycji liczy wzór niezależnie;
testy porównują ją z wynikiem programu, więc podstawienie daje podany wynik.
Zależności wynikają z podstawień ``[[klucz]]``; pozwalają złożyć raport dla dowolnego
parametru razem z tokiem obliczeń, który do niego prowadzi.
"""
import math
import re

from calculations.atmosphere import G0, RHO0, T0, P0, R_AIR, KAPPA, BETA_T, H_TROPO, isa_atmosphere
from calculations.report_document import tex_number

REF = re.compile(r'\[\[([A-Za-z_][A-Za-z0-9_]*)\]\]')
KEY = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

KG, M, M2, MS, KMH = r'\mathrm{kg}', r'\mathrm{m}', r'\mathrm{m^2}', r'\mathrm{m/s}', r'\mathrm{km/h}'
N_, KN, KW, NM2, PA = r'\mathrm{N}', r'\mathrm{kN}', r'\mathrm{kW}', r'\mathrm{N/m^2}', r'\mathrm{Pa}'
DEG, RAD, S_, H_, KM = r'{}^{\circ}', r'\mathrm{rad^{-1}}', r'\mathrm{s}', r'\mathrm{h}', r'\mathrm{km}'
PCT, USD, KGM2 = r'\%', r'\mathrm{USD}', r'\mathrm{kg\,m^2}'

SOURCES = {
    'B1': 'BIPOL_1 (C. Galiński, Analizy wstępne)',
    'B1W': 'BIPOL_1 — wyprowadzenie wzorów (C. Galiński, T. Grabowski)',
    'B2': 'BIPOL_2 (C. Galiński, Studium wykonalności)',
    'B3': 'BIPOL_3 (T. Grabowski, C. Galiński, Analiza masowa)',
    'ML': 'Z. Paturski, Przewodnik po projektach z Mechaniki Lotu',
    'R': 'D. P. Raymer, Aircraft Design: A Conceptual Approach',
    'D': 'J. Danilecki, Konstruowanie samolotów',
    'CS23': 'CS-23 Amdt 4 (metoda)', 'CS22': 'CS-22 Amdt 2', 'CS25': 'CS-25',
}


def tex_value(value, digits=3):
    """Liczba w zapisie TeX z przecinkiem dziesiętnym; bardzo małe i duże — notacja wykładnicza."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return r'\text{—}'
    magnitude = abs(value)
    if magnitude and (magnitude < 1e-4 or magnitude >= 1e8):
        exponent = math.floor(math.log10(magnitude))
        mantissa = value / 10 ** exponent
        if round(abs(mantissa), 3) >= 10:
            mantissa, exponent = mantissa / 10, exponent + 1
        return rf'{tex_number(mantissa, 3)}\cdot 10^{{{exponent}}}'
    return tex_number(value, digits)


def _visual_length(tex):
    """Przybliżona liczba znaków wiersza wzoru po złożeniu (do wyboru układu w dwóch wierszach)."""
    text = re.sub(r'\\(left|right|,|;|quad|qquad|mathrm|text)', '', tex)
    text = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', lambda m: 'x' * max(len(m.group(1)), len(m.group(2))), text)
    text = re.sub(r'\\[A-Za-z]+', 'x', text)
    return len(re.sub(r'[{}]', '', text))


class _Values:
    def __init__(self, values):
        self.__dict__.update(values)


def _close(computed, value, digits, tolerance=None):
    if not isinstance(computed, (int, float)) or not isinstance(value, (int, float)):
        return False
    limit = tolerance if tolerance is not None else max(3e-3 * abs(value), 10 ** -digits, 1e-12)
    return abs(computed - value) <= limit


class Sheet:
    """Rejestr wielkości: dane, obliczenia (wzór, podstawienie, wynik) i wzory tabelaryczne."""

    def __init__(self):
        self.entries, self.order, self.sections, self.blocks = {}, [], {}, {}
        self.dropped = set()
        self._section = None

    # -- definicje -------------------------------------------------------------------------
    def section(self, project, key, title, source=''):
        skey = f'{project}.{key}'
        self.sections.setdefault(skey, dict(key=skey, project=project, title=title, source=source, keys=[]))
        self._section = skey

    def _add(self, key, kind, **entry):
        if not KEY.match(key):
            raise ValueError(f'Nieprawidłowy klucz arkusza: {key}')
        if key in self.entries:
            raise ValueError(f'Powtórzony klucz arkusza: {key}')
        section = self.sections[self._section]
        entry.update(key=key, kind=kind, project=section['project'], section=section['key'])
        entry.setdefault('deps', [])
        self.entries[key] = entry
        self.order.append(key)
        section['keys'].append(key)
        return entry.get('value')

    def given(self, key, sym, value, unit='', digits=2, label='', source='', note=''):
        """Dana wejściowa: założenie, wymaganie, odczyt z wykresu lub wynik procedury numerycznej."""
        return self._add(key, 'given', sym=sym, value=value, unit=unit, digits=digits,
                         label=label, source=source, note=note)

    def calc(self, key, sym, formula, subst, value, unit='', digits=2, label='', source='', note='',
             check=None, deps=(), tolerance=None):
        """Wielkość obliczona: wzór ogólny, podstawienie liczb ([[klucz]]) i wynik programu."""
        refs = REF.findall(subst or '')
        return self._add(key, 'calc', sym=sym, formula=formula, subst=subst, value=value, unit=unit,
                         digits=digits, label=label, source=source, note=note, check=check,
                         tolerance=tolerance, deps=list(dict.fromkeys(refs + list(deps))))

    def solve(self, key, sym, condition, value, unit='', digits=2, label='', source='', note='',
              deps=(), check=None, tolerance=None):
        """Wynik procedury numerycznej (pierwiastek, ekstremum) z zapisanym warunkiem."""
        return self._add(key, 'solve', sym=sym, formula=condition, subst='', value=value, unit=unit,
                         digits=digits, label=label, source=source, note=note, check=check,
                         tolerance=tolerance, deps=list(deps))

    def table(self, key, label, formula, note='', deps=(), source=''):
        """Jeden wzór dla powtarzalnych wierszy tabeli (wyjątek od podstawień)."""
        return self._add(key, 'table', sym='', formula=formula, subst='', value=True, unit='',
                         digits=0, label=label, source=source, note=note, deps=list(deps))

    def block(self, key, project, title, deps=(), note=''):
        self.blocks[key] = dict(key=key, project=project, title=title, deps=list(deps), note=note)

    # -- zamknięcie arkusza ----------------------------------------------------------------
    def finalize(self):
        usable = lambda e: e['kind'] == 'table' or (isinstance(e['value'], (int, float))  # noqa: E731
                                                     and not isinstance(e['value'], bool)
                                                     and math.isfinite(e['value']))
        dropped = {k for k, e in self.entries.items() if not usable(e)}
        changed = True
        while changed:
            changed = False
            for key, entry in self.entries.items():
                if key in dropped:
                    continue
                for dep in entry['deps']:
                    if dep.startswith('@'):
                        if dep[1:] not in self.blocks:
                            raise KeyError(f'{key}: nieznany blok {dep}')
                        continue
                    if dep not in self.entries:
                        raise KeyError(f'{key}: nieznany symbol [[{dep}]]')
                    if dep in dropped:
                        dropped.add(key)
                        changed = True
                        break
        self.dropped = dropped
        for key in dropped:
            del self.entries[key]
        self.order = [k for k in self.order if k in self.entries]
        for section in self.sections.values():
            section['keys'] = [k for k in section['keys'] if k in self.entries]
        values = _Values({k: e['value'] for k, e in self.entries.items() if e['kind'] != 'table'})
        for entry in self.entries.values():
            entry['tex'] = self._tex(entry)
            entry['value_tex'] = (self.num(entry['key']) + (r'\;' + entry['unit'] if entry['unit'] else '')
                                  if entry['kind'] != 'table' else '')
            check = entry.pop('check', None)
            entry['computed'] = check(values) if check else None
            entry['consistent'] = (None if check is None else
                                   _close(entry['computed'], entry['value'], entry['digits'], entry.get('tolerance')))
        return self

    # -- prezentacja -----------------------------------------------------------------------
    def num(self, key, wrap=False):
        entry = self.entries[key]
        text = tex_value(entry['value'], entry['digits'])
        return rf'\left({text}\right)' if wrap and entry['value'] < 0 else text

    def _tex(self, e):
        if e['kind'] == 'table':
            return e['formula']
        result = self.num(e['key']) + (rf'\;{e["unit"]}' if e['unit'] else '')
        if e['kind'] == 'given':
            return f'{e["sym"]} = {result}'
        if e['kind'] == 'solve':
            return rf'{e["formula"]}\quad\Rightarrow\quad {e["sym"]} = {result}'
        subst = REF.sub(lambda m: self.num(m.group(1), wrap=True), e['subst']) if e['subst'] else ''
        # Długi zapis: wzór i podstawienie w dwóch wierszach, o ile podstawienie mieści się w szerokości
        # strony; dłuższe pozostają w jednym ciągu, który KaTeX łamie przy znakach działań.
        if len(e['formula']) + len(subst) > 150 and _visual_length(subst + result) <= 66:
            return (r'\begin{aligned}' + f'{e["sym"]} &= {e["formula"]}' + r'\\'
                    + (f'&= {subst} = {result}' if subst else f'&= {result}') + r'\end{aligned}')
        return ' = '.join(part for part in (e['sym'], e['formula'], subst, result) if part)

    def section_entries(self, skey):
        section = self.sections.get(skey)
        return [self.entries[k] for k in section['keys']] if section else []

    def view(self, skey, only=None, chain=False):
        """Sekcja do wydruku: dane wejściowe, wielkości przyjęte z innych części i obliczenia.

        Raport projektu (only=None) pokazuje wielkości z innych etapów; raport wybranych
        parametrów bez toku obliczeń — wszystkie wielkości użyte, a niewybrane.
        """
        section = self.sections.get(skey)
        if not section:
            return dict(givens=[], items=[], refs=[], title='', source='')
        entries = [self.entries[k] for k in section['keys'] if only is None or k in only]
        keys = {e['key'] for e in entries}
        refs = []
        if not chain:
            for entry in entries:
                for dep in entry['deps']:
                    if dep.startswith('@') or dep in keys or dep in refs:
                        continue
                    other = self.entries[dep]
                    if only is None and other['project'] == section['project']:
                        continue
                    refs.append(dep)
        return dict(givens=[e for e in entries if e['kind'] == 'given'], items=[e for e in entries if e['kind'] != 'given'],
                    refs=[self.entries[k] for k in refs], title=section['title'], source=section['source'],
                    project=section['project'])

    def where(self, key):
        """Opis miejsca definicji wielkości (do tabel danych)."""
        entry = self.entries[key]
        section = self.sections[entry['section']]
        part = 'Stałe' if section['project'] == 'const' else section['project'].upper()
        return f"{part} · {section['title']}"

    def external(self, skey):
        """Wielkości użyte w sekcji, a zdefiniowane w innej części projektu."""
        section = self.sections.get(skey)
        if not section:
            return []
        own = set(section['keys'])
        found = []
        for key in section['keys']:
            for dep in self.entries[key]['deps']:
                if dep.startswith('@') or dep in own or dep in found:
                    continue
                found.append(dep)
        return [self.entries[k] for k in found]

    def chain(self, keys, follow=True):
        """Wybrane wielkości z wszystkimi poprzednikami, w kolejności obliczeń."""
        seen, out, blocks = set(), [], []

        def visit(key):
            if key.startswith('@'):
                if key[1:] in self.blocks and key[1:] not in blocks:
                    blocks.append(key[1:])
                    for dep in self.blocks[key[1:]]['deps']:
                        visit(dep)
                return
            if key in seen or key not in self.entries:
                return
            seen.add(key)
            if follow:
                for dep in self.entries[key]['deps']:
                    visit(dep)
            out.append(key)
        for key in keys:
            visit(key)
        return out, blocks

    def catalog(self):
        """Lista wielkości dla interfejsu: sekcje, etykiety i wartości."""
        sections = []
        for section in self.sections.values():
            items = [dict(key=k, label=self.entries[k]['label'] or k, sym=self.entries[k]['sym'],
                          kind=self.entries[k]['kind'], value=self.entries[k]['value']
                          if self.entries[k]['kind'] != 'table' else None,
                          unit=self.entries[k]['unit'], digits=self.entries[k]['digits'],
                          value_tex=self.entries[k]['value_tex'])
                     for k in section['keys']]
            if items:
                sections.append(dict(key=section['key'], project=section['project'],
                                     title=section['title'], items=items))
        blocks = [dict(key='@' + b['key'], project=b['project'], title=b['title'], note=b['note'])
                  for b in self.blocks.values()]
        return dict(sections=sections, blocks=blocks)


def build_sheet(results):
    """Pełny arkusz obliczeń dla wyniku run_bipol_project()."""
    sheet = Sheet()
    for builder in (_constants, _p1, _p2, _p3, _p4, _p5, _p6):
        builder(sheet, results)
    return sheet.finalize()


# =============================================================================================
# Pomocnicze
# =============================================================================================
def _kmh(s, key, sym, kmh, label, source='', digits=2):
    """Prędkość zadana w km/h i jej wartość w m/s."""
    s.given(key + '_kmh', sym, kmh, KMH, 1, label, source)
    s.calc(key, sym, rf'\frac{{{sym}\,[\mathrm{{km/h}}]}}{{3{{,}}6}}', rf'\frac{{[[{key}_kmh]]}}{{3{{,}}6}}',
           kmh / 3.6, MS, digits, label + ' w m/s', check=lambda v: getattr(v, key + '_kmh') / 3.6)


def _to_kmh(s, key, sym, ms_key, value_kmh, label):
    s.calc(key, sym, rf'3{{,}}6\,{s.entries[ms_key]["sym"]}', rf'3{{,}}6\cdot[[{ms_key}]]', value_kmh, KMH, 1,
           label, check=lambda v: 3.6 * getattr(v, ms_key))


def _span_fixed(r):
    """Rozpiętość zadana w obliczeniach geometrii (params zawierają później wyliczone b)."""
    return r['geometry']['wing']['span_fixed']


def _ar_key(r):
    """Wydłużenie z założeń (P1) — przy zadanej rozpiętości oznaczone osobno od Λ = b²/S z P3."""
    return 'AR_1' if _span_fixed(r) else 'AR'


def _powered(r):
    return r['params']['engine_type'] != 'none' and r['params'].get('aircraft_type') != 'glider'


# =============================================================================================
# Stałe
# =============================================================================================
def _constants(s, r):
    s.section('const', 'const', 'Stałe fizyczne i atmosfera wzorcowa ISA')
    s.given('g', 'g', G0, r'\mathrm{m/s^2}', 5, 'Przyspieszenie ziemskie', 'ISA')
    s.given('rho0', r'\rho_0', RHO0, r'\mathrm{kg/m^3}', 3, 'Gęstość powietrza na poziomie morza', 'ISA')
    s.given('T0', 'T_0', T0, r'\mathrm{K}', 2, 'Temperatura na poziomie morza', 'ISA')
    s.given('p0', 'p_0', P0, PA, 0, 'Ciśnienie na poziomie morza', 'ISA')
    s.given('R_air', 'R', R_AIR, r'\mathrm{J/(kg\,K)}', 3, 'Stała gazowa powietrza', 'ISA')
    s.given('kappa', r'\kappa', KAPPA, '', 1, 'Wykładnik adiabaty powietrza', 'ISA')
    s.given('beta', r'\beta', BETA_T, r'\mathrm{K/m}', 4, 'Gradient temperatury w troposferze', 'ISA')


# =============================================================================================
# P1 — projekt koncepcyjny
# =============================================================================================
def _p1(s, r):
    p, mass, geom = r['params'], r['mass'], r['geometry']
    s.section('p1', 'load', 'Masa załogi i masa płatna', SOURCES['B1'])
    s.given('n_pas', r'n_{pas}', mass['n_pax'], r'\text{os.}', 0, 'Liczba pasażerów', 'Wymagania tematu')
    s.given('m_pas', r'm_{pas}', p.get('m_pax', 80), KG, 1, 'Masa pasażera z bagażem', 'Wytyczne z zajęć: 115 kg')
    s.given('m_bag', r'm_{bag}', p.get('m_bag', 0), KG, 1, 'Dodatkowy bagaż pasażera', 'Założenie')
    s.given('m_cargo', r'm_{cargo}', p.get('m_cargo', 0), KG, 1, 'Ładunek (cargo, wyposażenie zadaniowe)', 'Wymagania tematu')
    s.calc('m_lad', r'm_{ład}', r'n_{pas}\,(m_{pas}+m_{bag})+m_{cargo}',
           r'[[n_pas]]\cdot([[m_pas]]+[[m_bag]])+[[m_cargo]]', mass['m_payload'], KG, 1, 'Masa płatna',
           check=lambda v: v.n_pas * (v.m_pas + v.m_bag) + v.m_cargo)
    s.given('n_zal', r'n_{zał}', mass['n_crew'], r'\text{os.}', 0, 'Liczba członków załogi', 'Wymagania tematu')
    s.given('m_os', r'm_{os}', p.get('m_crew_person', 90), KG, 1, 'Masa członka załogi', 'Założenie')
    s.calc('m_zal', r'm_{zał}', r'n_{zał}\,m_{os}', r'[[n_zal]]\cdot[[m_os]]', mass['m_crew'], KG, 1,
           'Masa załogi', check=lambda v: v.n_zal * v.m_os)

    s.section('p1', 'atm', 'Atmosfera wzorcowa na wysokości przelotu', 'ISA')
    h = float(p['cruise_altitude_m'])
    isa = isa_atmosphere(h)
    s.given('H_cr', 'H', h, M, 0, 'Wysokość przelotu', 'Wymagania tematu')
    if h <= H_TROPO:
        s.calc('T_cr', 'T_H', r'T_0+\beta H', r'[[T0]]+[[beta]]\cdot[[H_cr]]', isa['T'], r'\mathrm{K}', 2,
               'Temperatura na wysokości przelotu', check=lambda v: v.T0 + v.beta * v.H_cr)
        s.calc('p_cr', 'p_H', r'p_0\left(\frac{T_H}{T_0}\right)^{-\frac{g}{\beta R}}',
               r'[[p0]]\cdot\left(\frac{[[T_cr]]}{[[T0]]}\right)^{-\frac{[[g]]}{[[beta]]\cdot[[R_air]]}}',
               isa['p'], PA, 0, 'Ciśnienie na wysokości przelotu',
               check=lambda v: v.p0 * (v.T_cr / v.T0) ** (-v.g / (v.beta * v.R_air)))
    else:
        t11 = T0 + BETA_T * H_TROPO
        p11 = P0 * (t11 / T0) ** (-G0 / (BETA_T * R_AIR))
        s.given('T_cr', 'T_H', isa['T'], r'\mathrm{K}', 2, 'Temperatura w stratosferze (stała)', 'ISA')
        s.given('p11', 'p_{11}', p11, PA, 0, 'Ciśnienie na wysokości 11 km', 'ISA')
        s.calc('p_cr', 'p_H', r'p_{11}\exp\left(-\frac{g\,(H-11000)}{R\,T_H}\right)',
               r'[[p11]]\cdot\exp\left(-\frac{[[g]]\cdot([[H_cr]]-11000)}{[[R_air]]\cdot[[T_cr]]}\right)',
               isa['p'], PA, 0, 'Ciśnienie na wysokości przelotu',
               check=lambda v: v.p11 * math.exp(-v.g * (v.H_cr - 11000) / (v.R_air * v.T_cr)))
    s.calc('rho_cr', r'\rho_H', r'\frac{p_H}{R\,T_H}', r'\frac{[[p_cr]]}{[[R_air]]\cdot[[T_cr]]}', isa['rho'],
           r'\mathrm{kg/m^3}', 4, 'Gęstość powietrza na wysokości przelotu', check=lambda v: v.p_cr / (v.R_air * v.T_cr))
    s.calc('sigma_cr', r'\sigma_H', r'\frac{\rho_H}{\rho_0}', r'\frac{[[rho_cr]]}{[[rho0]]}', isa['sigma'], '', 4,
           'Gęstość względna', check=lambda v: v.rho_cr / v.rho0)
    s.calc('a_cr', 'a_H', r'\sqrt{\kappa R T_H}', r'\sqrt{[[kappa]]\cdot[[R_air]]\cdot[[T_cr]]}', isa['a'], MS, 2,
           'Prędkość dźwięku', check=lambda v: math.sqrt(v.kappa * v.R_air * v.T_cr))
    mu = 1.789e-5 * (isa['T'] / 288.15) ** 1.5 * (288.15 + 110.4) / (isa['T'] + 110.4)
    s.calc('mu_cr', r'\mu_H', r'1{,}789\cdot10^{-5}\left(\frac{T_H}{288{,}15}\right)^{1{,}5}\frac{288{,}15+110{,}4}{T_H+110{,}4}',
           r'1{,}789\cdot10^{-5}\cdot\left(\frac{[[T_cr]]}{288{,}15}\right)^{1{,}5}\cdot\frac{398{,}55}{[[T_cr]]+110{,}4}',
           mu, r'\mathrm{Pa\,s}', 4, 'Lepkość dynamiczna (wzór Sutherlanda)',
           check=lambda v: 1.789e-5 * (v.T_cr / 288.15) ** 1.5 * 398.55 / (v.T_cr + 110.4))
    _kmh(s, 'V_cr', r'V_{cr}', float(p['cruise_speed_kmh']), 'Prędkość przelotowa (TAS)', 'Wymagania tematu')
    s.calc('M_cr', r'M_{cr}', r'\frac{V_{cr}}{a_H}', r'\frac{[[V_cr]]}{[[a_cr]]}', float(p['cruise_speed_kmh']) / 3.6 / isa['a'],
           '', 3, 'Liczba Macha w przelocie', check=lambda v: v.V_cr / v.a_cr)

    _p1_polar(s, r)
    _p1_trend(s, r)

    s.section('p1', 'wetted', 'Powierzchnia omywana i stosunek Swet/S', SOURCES['R'] + ', rozdz. 12; ' + SOURCES['B1'] + ', rys. 1')
    w, fus = geom['wing'], geom['fuselage']
    ht, vt = geom['horizontal_tail'], geom['vertical_tail']
    s.calc('S_exp', r'S_{exp}', r'\max\left(0{,}75\,S;\;S-c_r d_k\right)', r'\max\left(0{,}75\cdot[[S]];\;[[S]]-[[c_r]]\cdot[[d_k]]\right)',
           w['S_exposed'], M2, 2, 'Powierzchnia skrzydła poza kadłubem', check=lambda v: max(.75 * v.S, v.S - v.c_r * v.d_k))
    s.given('tc', r'(t/c)', w['tc_ratio'], '', 3, 'Względna grubość profilu skrzydła', 'Założenie')
    s.calc('Swet_w', r'S_{wet,p}', r'2S_{exp}\left(1+0{,}25\,(t/c)\right)', r'2\cdot[[S_exp]]\cdot(1+0{,}25\cdot[[tc]])',
           w['S_wet'], M2, 2, 'Powierzchnia omywana skrzydła', check=lambda v: 2 * v.S_exp * (1 + .25 * v.tc))
    clamp = 1 - 2 / fus['fineness'] < .5
    s.calc('Swet_k', r'S_{wet,k}', (r'\pi d_k l_k\cdot0{,}5^{2/3}\left(1+\frac{1}{\lambda_k^2}\right)' if clamp else
                                   r'\pi d_k l_k\left(1-\frac{2}{\lambda_k}\right)^{2/3}\left(1+\frac{1}{\lambda_k^2}\right)'),
           (r'\pi\cdot[[d_k]]\cdot[[l_k]]\cdot0{,}5^{2/3}\cdot\left(1+\frac{1}{[[lambda_k]]^2}\right)' if clamp else
            r'\pi\cdot[[d_k]]\cdot[[l_k]]\cdot\left(1-\frac{2}{[[lambda_k]]}\right)^{2/3}\cdot\left(1+\frac{1}{[[lambda_k]]^2}\right)'),
           fus['S_wet'], M2, 2, 'Powierzchnia omywana kadłuba',
           check=lambda v: math.pi * v.d_k * v.l_k * max(.5, 1 - 2 / v.lambda_k) ** (2 / 3) * (1 + 1 / v.lambda_k ** 2),
           tolerance=.006 * fus['S_wet'] + .01)
    s.calc('Swet_H', r'S_{wet,H}', r'2S_H\left(1+0{,}25\cdot0{,}09\right)', r'2\cdot[[S_H]]\cdot1{,}0225', ht['S_wet'], M2, 2,
           'Powierzchnia omywana usterzenia poziomego (t/c = 0,09)', check=lambda v: 2 * v.S_H * 1.0225, tolerance=.006 * ht['S_wet'] + .01)
    s.calc('Swet_V', r'S_{wet,V}', r'2S_V\left(1+0{,}25\cdot0{,}09\right)', r'2\cdot[[S_V]]\cdot1{,}0225', vt['S_wet'], M2, 2,
           'Powierzchnia omywana usterzenia pionowego', check=lambda v: 2 * v.S_V * 1.0225, tolerance=.006 * vt['S_wet'] + .01)
    s.calc('Swet', r'S_{wet}', r'S_{wet,p}+S_{wet,k}+S_{wet,H}+S_{wet,V}', r'[[Swet_w]]+[[Swet_k]]+[[Swet_H]]+[[Swet_V]]',
           geom['wetted_area']['total_m2'], M2, 2, 'Całkowita powierzchnia omywana',
           check=lambda v: v.Swet_w + v.Swet_k + v.Swet_H + v.Swet_V)
    s.calc('Swet_S', r'S_{wet}/S', r'\frac{S_{wet}}{S}', r'\frac{[[Swet]]}{[[S]]}', geom['wetted_area']['swet_over_s'], '', 2,
           'Stosunek powierzchni omywanej do powierzchni nośnej', check=lambda v: v.Swet / v.S)

    if _powered(r):
        p1 = r['bipol_projects']['p1']
        s.section('p1', 'power', 'Wstępne zapotrzebowanie mocy (ciągu) w przelocie', SOURCES['B1W'])
        s.calc('q_cr', r'q_{cr}', r'\frac{\rho_H V_{cr}^2}{2}', r'\frac{[[rho_cr]]\cdot[[V_cr]]^2}{2}',
               .5 * isa['rho'] * (float(p['cruise_speed_kmh']) / 3.6) ** 2, PA, 1, 'Ciśnienie dynamiczne w przelocie',
               check=lambda v: .5 * v.rho_cr * v.V_cr ** 2)
        s.calc('Cz_cr', r'C_{z,cr}', r'\frac{m_0 g}{q_{cr} S}', r'\frac{[[m0]]\cdot[[g]]}{[[q_cr]]\cdot[[S]]}',
               r['mass']['m0'] * G0 / (.5 * isa['rho'] * (float(p['cruise_speed_kmh']) / 3.6) ** 2 * geom['wing']['S']),
               '', 4, 'Współczynnik siły nośnej w przelocie', check=lambda v: v.m0 * v.g / (v.q_cr * v.S))
        aero = r['aerodynamics']
        cx = aero['cx0_clean'] + aero['k_clean'] * s.entries['Cz_cr']['value'] ** 2
        s.calc('Cx_cr', r'C_{x,cr}', r'C_{x0}+k\,C_{z,cr}^2', r'[[Cx0]]+[[k]]\cdot[[Cz_cr]]^2', cx, '', 5,
               'Współczynnik oporu w przelocie (biegunowa P4)', check=lambda v: v.Cx0 + v.k * v.Cz_cr ** 2)
        drag = s.entries['q_cr']['value'] * geom['wing']['S'] * cx
        s.calc('D_cr', r'D_{cr}', r'q_{cr}\,S\,C_{x,cr}', r'[[q_cr]]\cdot[[S]]\cdot[[Cx_cr]]', drag, N_, 0,
               'Opór w przelocie', check=lambda v: v.q_cr * v.S * v.Cx_cr)
        if p['engine_type'] == 'jet':
            s.calc('T_n_cr', r'T_{n}', r'\frac{D_{cr}}{1000}', r'\frac{[[D_cr]]}{1000}', p1['t_req_est_kn'], KN, 2,
                   'Ciąg niezbędny w przelocie', check=lambda v: v.D_cr / 1000)
        else:
            s.calc('N_n_cr', r'N_{n}', r'\frac{D_{cr}V_{cr}}{1000\,\eta_p}', r'\frac{[[D_cr]]\cdot[[V_cr]]}{1000\cdot[[eta_p]]}',
                   p1['p_req_est_kw'], KW, 1, 'Moc niezbędna w przelocie (na wale)',
                   check=lambda v: v.D_cr * v.V_cr / (1000 * v.eta_p))


def _p1_polar(s, r):
    p, mass = r['params'], r['mass']
    pp = mass['preliminary_polar']
    s.section('p1', 'polar', 'Szacunkowa biegunowa analityczna', SOURCES['B1'] + ', wzory (2)–(3)')
    span_fixed = _span_fixed(r)
    ar_key = _ar_key(r)
    s.given(ar_key, r'\Lambda', pp['aspect_ratio'], '', 2,
            'Wydłużenie przyjęte z analizy trendów' if not span_fixed else 'Wydłużenie do biegunowej szacunkowej',
            SOURCES['B1'] + ', s. 2')
    s.given('e_1', 'e', pp['oswald_e'], '', 3, 'Współczynnik Oswalda', SOURCES['B1'] + ': e ≈ 0,8')
    ar = '[[' + ar_key + ']]'
    if pp['mode'] == 'input':
        base = float(p['cx0'])
        extra = pp['cx0'] - base
        if extra > 1e-12:
            s.given('Cx0_baz', r'C_{x0,baz}', base, '', 4, 'Opór zerowy przyjęty z tabeli BIPOL_1', SOURCES['B1'] + ', tabela Cx0')
            names = [n for n, on in (('zastrzały', p.get('wing_config') == 'braced_high'),
                                     ('klapa Junkersa', p.get('flap_type') == 'junkers'),
                                     ('slot stały', p.get('slat_type') == 'fixed_slot')) if on]
            s.given('dCx0_konf', r'\Delta C_{x0,konf}', extra, '', 4, 'Dodatek konfiguracji: ' + ', '.join(names), 'Założenie')
            s.calc('Cx0_1', r'C_{x0}', r'C_{x0,baz}+\Delta C_{x0,konf}', r'[[Cx0_baz]]+[[dCx0_konf]]', pp['cx0'], '', 4,
                   'Opór zerowy biegunowej szacunkowej', check=lambda v: v.Cx0_baz + v.dCx0_konf)
        else:
            s.given('Cx0_1', r'C_{x0}', pp['cx0'], '', 4, 'Opór zerowy przyjęty z tabeli BIPOL_1', SOURCES['B1'] + ', tabela Cx0')
        s.calc('Kmax_1', r'K_{max}', r'\frac{1}{2}\sqrt{\frac{\pi\Lambda e}{C_{x0}}}',
               r'\frac{1}{2}\sqrt{\frac{\pi\cdot' + ar + r'\cdot[[e_1]]}{[[Cx0_1]]}}', pp['kmax'], '', 3,
               'Maksymalna doskonałość szacunkowa', SOURCES['B1'] + ', wzór (3)',
               check=lambda v: .5 * math.sqrt(math.pi * getattr(v, ar_key) * v.e_1 / v.Cx0_1))
    else:
        s.given('Swet_S_szk', r'(S_{wet}/S)_{szk}', pp['swet_ratio'], '', 3, 'Stosunek odczytany ze szkicu odręcznego',
                SOURCES['B1'] + ', rys. 1')
        if pp['mode'] == 'raymer':
            s.calc('AR_wet', r'\Lambda_{wet}', r'\frac{\Lambda}{(S_{wet}/S)_{szk}}', r'\frac{' + ar + r'}{[[Swet_S_szk]]}', pp['wetted_aspect_ratio'], '', 3,
                   'Wydłużenie odniesione do powierzchni omywanej',
                   check=lambda v: getattr(v, ar_key) / v.Swet_S_szk)
            s.given('Kmax_1', r'K_{max}', pp['kmax'], '', 2, 'Odczyt z rys. 2 dla Λwet (interpolacja odcinkowa)',
                    SOURCES['B1'] + ', rys. 2 (Raymer)')
        else:
            s.given('Kmax_1', r'K_{max}', pp['kmax'], '', 2, 'Odczyt autora z rys. 2', SOURCES['B1'] + ', rys. 2')
        s.calc('Cx0_1', r'C_{x0}', r'\frac{\pi\Lambda e}{4K_{max}^2}', r'\frac{\pi\cdot' + ar + r'\cdot[[e_1]]}{4\cdot[[Kmax_1]]^2}',
               pp['cx0'], '', 5, 'Opór zerowy z maksymalnej doskonałości', SOURCES['B1'] + ', wzór (3)',
               check=lambda v: math.pi * getattr(v, ar_key) * v.e_1 / (4 * v.Kmax_1 ** 2))
    ar_value = pp['aspect_ratio']
    s.calc('k_1', 'k', r'\frac{1}{\pi\Lambda e}', r'\frac{1}{\pi\cdot' + ar + r'\cdot[[e_1]]}',
           1 / (math.pi * ar_value * pp['oswald_e']), '', 5, 'Współczynnik oporu indukowanego',
           SOURCES['B1'] + ', wzór (2)', check=lambda v: 1 / (math.pi * getattr(v, ar_key) * v.e_1))
    s.table('polar_1', 'Biegunowa analityczna', r'C_x=C_{x0}+\frac{C_z^2}{\pi\Lambda e}=C_{x0}+k\,C_z^2',
            source=SOURCES['B1'] + ', wzór (2)')


def _p1_trend(s, r):
    ta = r['bipol_projects']['p1']['trend_analysis']
    tp = ta.get('two_point')
    if not (ta.get('mass_fit') and tp):
        return
    s.section('p1', 'trend', 'Współczynniki równania (1) z analizy trendów', SOURCES['B1'] + ', wzór (1)')
    s.given('tr_x1', 'x_1', tp['x1'], KG, 0, 'Punkt 1 linii trendu — masa startowa', 'Linia regresji próby P1')
    s.given('tr_y1', 'y_1', tp['y1'], '', 4, 'Punkt 1 linii trendu — mₑ/m₀', 'Linia regresji próby P1')
    s.given('tr_x2', 'x_2', tp['x2'], KG, 0, 'Punkt 2 linii trendu — masa startowa', 'Linia regresji próby P1')
    s.given('tr_y2', 'y_2', tp['y2'], '', 4, 'Punkt 2 linii trendu — mₑ/m₀', 'Linia regresji próby P1')
    s.calc('tr_C', 'C', r'\frac{\log\left(y_1/y_2\right)}{\log\left(x_1/x_2\right)}',
           r'\frac{\log\left([[tr_y1]]/[[tr_y2]]\right)}{\log\left([[tr_x1]]/[[tr_x2]]\right)}', tp['C'], '', 5,
           'Wykładnik równania (1) z próby', SOURCES['B1'] + ', s. 1',
           check=lambda v: math.log(v.tr_y1 / v.tr_y2) / math.log(v.tr_x1 / v.tr_x2))
    s.calc('tr_A', 'A', r'\frac{y_1}{x_1^{C}}', r'\frac{[[tr_y1]]}{[[tr_x1]]^{[[tr_C]]}}', tp['A'], '', 5,
           'Współczynnik równania (1) z próby', SOURCES['B1'] + ', s. 1', check=lambda v: v.tr_y1 / v.tr_x1 ** v.tr_C)


# =============================================================================================
# P2 — studium wykonalności
# =============================================================================================
def _p2(s, r):
    p, mass = r['params'], r['mass']
    powered = _powered(r)
    trace = mass['guideline_traces'].get(mass['primary_method'])
    ma = mass['mission_assumptions']
    m0 = mass['m0']
    phases = {ph['key']: ph for ph in mass['mission_phases']}
    s.block('mass_iteration_' + mass['primary_method'], 'p2',
            'Schemat iteracji masy startowej — ' + ('metoda proporcji' if mass['primary_method'] == 'proportion'
                                                   else 'metoda iteracyjna') + ' (BIPOL_1, s. 4)',
            deps=['m_zal', 'm_lad', 'e_m0'], note='Metoda użyta w bilansie projektu.')
    for method, other in mass['guideline_traces'].items():
        if method != mass['primary_method']:
            s.block('mass_iteration_' + method, 'p2',
                    'Schemat iteracji masy startowej — ' + ('metoda proporcji' if method == 'proportion'
                                                           else 'metoda iteracyjna') + ' (BIPOL_1, s. 4)',
                    deps=['m_zal', 'm_lad', 'e_m0'], note='Metoda porównawcza; daje tę samą masę bez zrzutu ładunku.')

    s.section('p2', 'mission', 'Profil misji i stosunki mas w fazach lotu', SOURCES['B1'] + ', s. 4–6')
    if powered:
        jet = p['engine_type'] == 'jet'
        back = float(p.get('return_range_km') or 0)
        total = float(p['range_km'])
        s.given('R_km', 'R', total, KM, 0, 'Zasięg obliczeniowy misji', 'Wymagania tematu')
        if jet:
            s.given('TSFC', r'c_T g', float(p['sfc']), r'\mathrm{1/h}', 3, 'Jednostkowe zużycie paliwa (ciągowe)', 'Dane silnika / założenie')
            s.calc('c_T', 'c_T', r'\frac{c_T g\,[\mathrm{1/h}]}{3600}', r'\frac{[[TSFC]]}{3600}', float(p['sfc']) / 3600,
                   r'\mathrm{1/s}', 6, 'Jednostkowe zużycie paliwa w jednostkach SI', check=lambda v: v.TSFC / 3600)
        else:
            s.given('SFC', r'SFC', float(p['sfc']), r'\mathrm{g/(kW\,h)}', 1, 'Jednostkowe zużycie paliwa (mocowe)', 'Dane silnika / założenie')
            s.calc('c_P', 'c_P', r'\frac{SFC}{3{,}6\cdot10^{9}}', r'\frac{[[SFC]]}{3{,}6\cdot10^{9}}', float(p['sfc']) / 3.6e9,
                   r'\mathrm{kg/(W\,s)}', 4, 'Jednostkowe zużycie paliwa w jednostkach SI', check=lambda v: v.SFC / 3.6e9)
            s.given('eta_p', r'\eta_p', float(p.get('prop_efficiency', .82)), '', 2, 'Sprawność śmigła w przelocie',
                    SOURCES['B1'] + ': η ≈ 0,8')
        if ma.get('ld_source') == 'p4_cruise':
            s.given('K_przel', r'K_{przel}', trace['cruise_ld'] if trace else mass['ld_cruise_used'], '', 3,
                    'Doskonałość w przelocie', 'Bilans uściślony: biegunowa P4 przy wymaganej prędkości i wysokości',
                    'Średnia doskonałość przelotu ze stałą prędkością (zasięg P5); zastępuje pierwsze oszacowanie 0,94 Kmax.')
        else:
            s.given('k_K', 'k_K', ma['ld_factor'], '', 2, 'Udział maksymalnej doskonałości w przelocie',
                    'Wytyczne z zajęć: K = 0,94 Kmax')
            s.calc('K_przel', r'K_{przel}', r'k_K K_{max}', r'[[k_K]]\cdot[[Kmax_1]]', trace['cruise_ld'] if trace else mass['ld_cruise_used'],
                   '', 3, 'Porównawcza doskonałość studium wstępnego; przelot liczony osobno z całki P4' if ma.get('cruise_model') == 'constant_tas_altitude' else 'Doskonałość w przelocie',
                   check=lambda v: v.k_K * v.Kmax_1)
        s.given('r_TO', r'\frac{m_1}{m_0}', mass['fuel_fractions_detail']['takeoff'], '', 3, 'Start i kołowanie',
                SOURCES['B1'] + ', s. 4: 0,970–0,975')
        corke = ma['corke']
        if corke.get('provisional'):
            s.given('r_CL', r'\frac{m_2}{m_1}', corke['fraction'], '', 5,
                    'Wznoszenie — przybliżenie robocze (Mach poniżej zakresu rys. 3)', 'Wymaga odczytu źródłowego')
        else:
            if corke['mode'] != 'reading':
                h0 = float(p.get('climb_start_altitude_m', 0))
                isa0 = isa_atmosphere(h0)
                s.given('H_0', 'H_0', h0, M, 0, 'Wysokość początku wznoszenia', 'Profil misji')
                v0 = float(p.get('climb_start_speed_kmh', p['cruise_speed_kmh']))
                _kmh(s, 'V_0', 'V_0', v0, 'Prędkość na początku wznoszenia', 'Profil misji')
                if h0 <= H_TROPO:
                    s.calc('a_0', 'a_0', r'\sqrt{\kappa R\,(T_0+\beta H_0)}', r'\sqrt{[[kappa]]\cdot[[R_air]]\cdot([[T0]]+[[beta]]\cdot[[H_0]])}',
                           isa0['a'], MS, 2, 'Prędkość dźwięku na początku wznoszenia',
                           check=lambda v: math.sqrt(v.kappa * v.R_air * (v.T0 + v.beta * v.H_0)))
                else:
                    s.given('a_0', 'a_0', isa0['a'], MS, 2, 'Prędkość dźwięku na początku wznoszenia', 'ISA')
                s.calc('M_p', 'M_p', r'\frac{V_0}{a_0}', r'\frac{[[V_0]]}{[[a_0]]}', corke['mach_start'], '', 4,
                       'Liczba Macha na początku wznoszenia', check=lambda v: v.V_0 / v.a_0)
                s.calc('M_k', 'M_k', r'\frac{V_{cr}}{a_H}', r'\frac{[[V_cr]]}{[[a_cr]]}', corke['mach_end'], '', 4,
                       'Liczba Macha na końcu wznoszenia', check=lambda v: v.V_cr / v.a_cr)
                source = SOURCES['B1'] + ', rys. 3 (Corke, oś M logarytmiczna)'
                s.given('W_p', r'\bar W(M_p)', corke['ordinate_start'], '', 5, 'Rzędna wykresu Corke’a dla Mp', source)
                s.given('W_k', r'\bar W(M_k)', corke['ordinate_end'], '', 5, 'Rzędna wykresu Corke’a dla Mk', source)
            else:
                s.given('W_p', r'\bar W(M_p)', corke['ordinate_start'], '', 5, 'Odczyt autora z rys. 3', SOURCES['B1'] + ', rys. 3')
                s.given('W_k', r'\bar W(M_k)', corke['ordinate_end'], '', 5, 'Odczyt autora z rys. 3', SOURCES['B1'] + ', rys. 3')
            s.calc('r_CL', r'\frac{m_2}{m_1}', r'\frac{\bar W(M_k)}{\bar W(M_p)}', r'\frac{[[W_k]]}{[[W_p]]}', corke['fraction'],
                   '', 5, 'Wznoszenie i rozpędzanie', SOURCES['B1'] + ', s. 4–5', check=lambda v: v.W_k / v.W_p)
        legs = [('r_CR', r'\frac{m_3}{m_2}', 'R_1' if back else 'R_km', phases['cruise']['fraction'],
                 'Przelot do celu' if back else 'Przelot')]
        if back:
            s.given('R_pow', r'R_{pow}', back, KM, 0, 'Długość odcinka powrotnego', 'Profil misji')
            s.calc('R_1', 'R_1', r'R-R_{pow}', r'[[R_km]]-[[R_pow]]', total - back, KM, 0, 'Długość lotu do celu',
                   check=lambda v: v.R_km - v.R_pow)
            legs.append(('r_RET', r'\frac{m_5}{m_4}', 'R_pow', phases['return']['fraction'], 'Lot powrotny'))
        for key, sym, dist, value, label in legs:
            if ma.get('cruise_model') == 'constant_tas_altitude':
                if key == 'r_CR':
                    from calculations.mission_cruise import coefficients
                    polar = ma['cruise_polar']
                    a, b, consumption = coefficients(p, polar)
                    s.given('S_mis', r'S_{mis}', polar['S'], M2, 4, 'Powierzchnia ostatniej iteracji misji', 'Domknięcie P2–P4')
                    s.given('CD0_mis', r'C_{x0,mis}', polar['cx0'], '', 7, 'Opór zerowy ostatniej iteracji misji', 'Biegunowa P4')
                    s.given('k_mis', r'k_{mis}', polar['k'], '', 7, 'Opór indukowany ostatniej iteracji misji', 'Biegunowa P4')
                    s.given('rho_mis', r'\rho_{mis}', isa_atmosphere(p['cruise_altitude_m'])['rho'], r'\mathrm{kg/m^3}', 5, 'Gęstość w przelocie', 'ISA')
                    s.calc('a_mis', 'a', r'\tfrac12\rho V^2 S C_{x0}', r'0{,}5[[rho_mis]][[V_cr]]^2[[S_mis]][[CD0_mis]]',
                           a, r'\mathrm{N}', 4, 'Stała składowa oporu D=a+b m²', check=lambda v: .5*v.rho_mis*v.V_cr**2*v.S_mis*v.CD0_mis)
                    s.calc('b_mis', 'b', r'\frac{k g^2}{\tfrac12\rho V^2 S}', r'\frac{[[k_mis]][[g]]^2}{0{,}5[[rho_mis]][[V_cr]]^2[[S_mis]]}',
                           b, r'\mathrm{N/kg^2}', 8, 'Składowa oporu zależna od masy', check=lambda v: v.k_mis*v.g**2/(.5*v.rho_mis*v.V_cr**2*v.S_mis))
                    s.given('c_mis', r'c_x', consumption, r'\mathrm{kg/(N\,m)}', 10, 'Przelicznik paliwa na drogę: cT/(gV) dla odrzutowego, cP/η dla śmigłowego', 'Jednostki SFC')
                    s.given('margin_R', r'k_R', 1.001, '', 3, 'Jawny margines długości trasy', 'Założenie obliczeniowe')
                phase = phases['cruise' if key == 'r_CR' else 'return']
                s.given(key+'_start', r'm_{p,'+key+'}', phase['mass_start_kg'], KG, 3, 'Masa na początku odcinka', 'Poprzednia faza misji')
                s.calc(key+'_end', r'm_{k,'+key+'}', r'\sqrt{a/b}\tan\left(\arctan(m_p\sqrt{b/a})-1000R k_R c_x\sqrt{ab}\right)',
                       rf'\sqrt{{[[a_mis]]/[[b_mis]]}}\tan\left(\arctan([[{key}_start]]\sqrt{{[[b_mis]]/[[a_mis]]}})-1000[[{dist}]][[margin_R]][[c_mis]]\sqrt{{[[a_mis]][[b_mis]]}}\right)',
                       phase['mass_end_kg'], KG, 3, label + ' — całka bilansu paliwa przy stałej TAS i wysokości',
                       check=lambda v, q=key, d=dist: math.sqrt(v.a_mis/v.b_mis)*math.tan(math.atan(getattr(v,q+'_start')*math.sqrt(v.b_mis/v.a_mis))-1000*getattr(v,d)*v.margin_R*v.c_mis*math.sqrt(v.a_mis*v.b_mis)))
                s.calc(key, sym, r'm_k/m_p', rf'[[{key}_end]]/[[{key}_start]]', value, '', 6,
                       label + ' — stosunek mas', check=lambda v, q=key: getattr(v,q+'_end')/getattr(v,q+'_start'))
            elif jet:
                s.calc(key, sym, r'\exp\left(-\frac{1000\,R\,c_T}{V_{cr}K_{przel}}\right)',
                       rf'\exp\left(-\frac{{1000\cdot[[{dist}]]\cdot[[c_T]]}}{{[[V_cr]]\cdot[[K_przel]]}}\right)', value, '', 5,
                       label + ' (równanie Bregueta dla napędu odrzutowego)', SOURCES['B1'] + ', s. 5',
                       check=lambda v, d=dist: math.exp(-1000 * getattr(v, d) * v.c_T / (v.V_cr * v.K_przel)))
            else:
                s.calc(key, sym, r'\exp\left(-\frac{1000\,R\,c_P\,g}{\eta_p K_{przel}}\right)',
                       rf'\exp\left(-\frac{{1000\cdot[[{dist}]]\cdot[[c_P]]\cdot[[g]]}}{{[[eta_p]]\cdot[[K_przel]]}}\right)', value, '', 5,
                       label + ' (równanie Bregueta dla napędu śmigłowego)', SOURCES['B1'] + ', s. 5',
                       check=lambda v, d=dist: math.exp(-1000 * getattr(v, d) * v.c_P * v.g / (v.eta_p * v.K_przel)))
        if 'task' in phases:
            task_h = float(p['max_power_time_min'])
            s.given('t_zad', r't_{zad}', task_h, r'\mathrm{min}', 0, 'Czas pracy na maksymalnym ciągu (mocy)', 'Profil misji')
            s.given('SFC_max', r'SFC_{max}', float(p['max_power_sfc']), r'\mathrm{1/h}' if jet else r'\mathrm{g/(kW\,h)}', 3,
                    'Zużycie jednostkowe przy maksymalnym ciągu (mocy)', 'Dane silnika')
            if jet:
                s.given('T_max_zad', r'T_{max}', float(p['max_thrust_kn']), KN, 2, 'Maksymalny ciąg', 'Dane silnika')
                s.calc('m_f_zad', r'm_{f,zad}', r'\frac{SFC_{max}}{g}\,1000\,T_{max}\frac{t_{zad}}{60}',
                       r'\frac{[[SFC_max]]}{[[g]]}\cdot1000\cdot[[T_max_zad]]\cdot\frac{[[t_zad]]}{60}', phases['task']['fuel_burn_kg'],
                       KG, 2, 'Paliwo zużyte w zadaniu', SOURCES['B1'] + ', s. 5',
                       check=lambda v: v.SFC_max / v.g * 1000 * v.T_max_zad * v.t_zad / 60)
            else:
                s.given('P_max_zad', r'N_{max}', float(p['max_power_kw']), KW, 1, 'Maksymalna moc', 'Dane silnika')
                s.calc('m_f_zad', r'm_{f,zad}', r'\frac{SFC_{max}}{1000}\,N_{max}\frac{t_{zad}}{60}',
                       r'\frac{[[SFC_max]]}{1000}\cdot[[P_max_zad]]\cdot\frac{[[t_zad]]}{60}', phases['task']['fuel_burn_kg'],
                       KG, 2, 'Paliwo zużyte w zadaniu', SOURCES['B1'] + ', s. 5',
                       check=lambda v: v.SFC_max / 1000 * v.P_max_zad * v.t_zad / 60)
        if 'drop' in phases:
            s.given('m_zrzut', r'm_{zrzut}', phases['drop']['payload_drop_kg'], KG, 1, 'Masa zrzucanego ładunku', 'Profil misji')
        s.given('t_ocz', r't_{ocz}', float(p.get('loiter_time_min', 45)), r'\mathrm{min}', 0, 'Czas oczekiwania (krążenia)', 'Profil misji')
        kmax_label = SOURCES['B1'] + ', s. 6 (oczekiwanie: 0,8 Kmax)'
        if jet:
            s.calc('r_LT', r'\frac{m_6}{m_5}', r'\exp\left(-\frac{60\,t_{ocz}\,c_T}{0{,}8\,K_{max}}\right)',
                   r'\exp\left(-\frac{60\cdot[[t_ocz]]\cdot[[c_T]]}{0{,}8\cdot[[Kmax_1]]}\right)', phases['loiter']['fraction'], '', 5,
                   'Oczekiwanie w kolejce do lądowania', kmax_label,
                   check=lambda v: math.exp(-60 * v.t_ocz * v.c_T / (.8 * v.Kmax_1)))
        else:
            _kmh(s, 'V_ocz', r'V_{ocz}', ma['loiter_speed_kmh'], 'Prędkość oczekiwania', 'Profil misji')
            s.calc('r_LT', r'\frac{m_6}{m_5}', r'\exp\left(-\frac{60\,t_{ocz}V_{ocz}c_P\,g}{0{,}8\,\eta_p K_{max}}\right)',
                   r'\exp\left(-\frac{60\cdot[[t_ocz]]\cdot[[V_ocz]]\cdot[[c_P]]\cdot[[g]]}{0{,}8\cdot[[eta_p]]\cdot[[Kmax_1]]}\right)',
                   phases['loiter']['fraction'], '', 5, 'Oczekiwanie w kolejce do lądowania', kmax_label,
                   check=lambda v: math.exp(-60 * v.t_ocz * v.V_ocz * v.c_P * v.g / (.8 * v.eta_p * v.Kmax_1)))
        s.given('r_LND', r'\frac{m_7}{m_6}', mass['fuel_fractions_detail']['landing'], '', 3, 'Lądowanie i kołowanie',
                SOURCES['B1'] + ', s. 6: 0,970–0,975')
        s.given('k_rez', r'k_{rez}', ma['reserve_factor'], '', 2, 'Rezerwa i paliwo niezużywalne', SOURCES['B1'] + ', wzór (4)')
        if 'task' not in phases and 'drop' not in phases:
            ratios = ['r_TO', 'r_CL', 'r_CR'] + (['r_RET'] if back else []) + ['r_LT', 'r_LND']
            s.calc('Mff', r'M_{ff}', r'\prod_i\frac{m_{i+1}}{m_i}', r'\cdot'.join(f'[[{k}]]' for k in ratios),
                   mass['fuel_fractions_detail']['total_mff'], '', 5, 'Iloczyn stosunków mas faz lotu',
                   SOURCES['B1'] + ', s. 4', check=lambda v: math.prod(getattr(v, k) for k in ratios))
            s.calc('mf_m0', r'\frac{m_f}{m_0}', r'k_{rez}\left(1-M_{ff}\right)', r'[[k_rez]]\cdot\left(1-[[Mff]]\right)',
                   mass['m_fuel'] / m0, '', 5, 'Udział masy paliwa', SOURCES['B1'] + ', wzór (4)',
                   check=lambda v: v.k_rez * (1 - v.Mff))

    _p2_empty_law(s, r)

    s.section('p2', 'mass', 'Masa startowa, masa własna i masa paliwa', SOURCES['B1'] + ', wzory (1), (4), (5)')
    block = '@mass_iteration_' + mass['primary_method']
    if powered and 'mf_m0' in s.entries:
        s.calc('m0', 'm_0', r'\frac{m_{zał}+m_{ład}}{1-\dfrac{m_f}{m_0}-\dfrac{m_e}{m_0}}',
               r'\frac{[[m_zal]]+[[m_lad]]}{1-[[mf_m0]]-[[e_m0]]}', m0, KG, 1,
               'Masa startowa — rozwiązanie wzoru (5) z równaniem (1)', SOURCES['B1'] + ', wzór (5)',
               note='Równanie rozwiązano iteracyjnie; kolejne przybliżenia pokazuje schemat iteracji masy.',
               check=lambda v: (v.m_zal + v.m_lad) / (1 - v.mf_m0 - v.e_m0), deps=[block])
    elif not powered:
        s.calc('m0', 'm_0', r'\frac{m_{zał}+m_{ład}}{1-\dfrac{m_e}{m_0}}', r'\frac{[[m_zal]]+[[m_lad]]}{1-[[e_m0]]}', m0, KG, 1,
               'Masa startowa bez paliwa — wzór (5) z równaniem (1)', SOURCES['B1'] + ', wzór (5)',
               note='Równanie rozwiązano iteracyjnie; kolejne przybliżenia pokazuje schemat iteracji masy.',
               check=lambda v: (v.m_zal + v.m_lad) / (1 - v.e_m0), deps=[block])
    else:
        s.solve('m0', 'm_0', r'\Delta(m_0)=m_{e,mis}(m_0)-m_0\frac{m_e}{m_0}=0', m0, KG, 1,
                'Masa startowa — zgodność masy pustego z misji i z równania (1)', SOURCES['B1'] + ', s. 4, pkt 9–12',
                note='Kolejne przybliżenia pokazuje schemat iteracji masy.', deps=[block, 'e_m0', 'm_zal', 'm_lad'])
    s.calc('m_e', 'm_e', r'm_0\,\frac{m_e}{m_0}', r'[[m0]]\cdot[[e_m0]]', mass['m_empty'], KG, 1, 'Masa własna (pustego samolotu)',
           SOURCES['B1'] + ', pkt 10', check=lambda v: v.m0 * v.e_m0)
    if powered:
        burns = [ph for ph in mass['mission_phases'] if ph['fuel_burn_kg'] > 1e-9]
        s.calc('m_f_spal', r'm_{f,spal}', r'\sum_i \Delta m_{f,i}', '+'.join(tex_value(ph['fuel_burn_kg'], 2) for ph in burns),
               mass['fuel_burn_kg'], KG, 2, 'Paliwo spalone w fazach misji (tabela faz)', deps=['m0'],
               check=lambda v, b=[ph['fuel_burn_kg'] for ph in burns]: sum(b))
        s.calc('m_f', 'm_f', r'k_{rez}\,m_{f,spal}', r'[[k_rez]]\cdot[[m_f_spal]]', mass['m_fuel'], KG, 1,
               'Masa paliwa z rezerwą i paliwem niezużywalnym', SOURCES['B1'] + ', wzór (4)', check=lambda v: v.k_rez * v.m_f_spal)
        s.calc('m0_sum', r'm_0', r'm_e+m_f+m_{zał}+m_{ład}', r'[[m_e]]+[[m_f]]+[[m_zal]]+[[m_lad]]',
               mass['m_empty'] + mass['m_fuel'] + mass['m_crew'] + mass['m_payload'], KG, 1, 'Sprawdzenie bilansu mas',
               check=lambda v: v.m_e + v.m_f + v.m_zal + v.m_lad)
    s.calc('m_zfw', r'm_{ZFW}', r'm_e+m_{zał}+m_{ład}', r'[[m_e]]+[[m_zal]]+[[m_lad]]', mass['m_zfw'], KG, 1,
           'Masa bez paliwa', check=lambda v: v.m_e + v.m_zal + v.m_lad)

    _p2_matching(s, r)
    _p2_airfoil(s, r)
    _p2_cost(s, r)


def _p2_empty_law(s, r):
    p, mass = r['params'], r['mass']
    law = mass['empty_mass_law']
    mode = law['mode']
    s.section('p2', 'empty', 'Udział masy własnej — równanie (1)', SOURCES['B1'] + ', wzór (1)')
    source = {'class_correlation': 'Korelacja klasy (robocza; do zastąpienia analizą własnej próby)',
              'trend': f"Regresja próby P1 ({law.get('n', '—')} konstrukcji)",
              'bipol1_trend': 'Współczynniki z analizy trendów P1', 'coefficients': 'Współczynniki podane przez autora',
              'two_point': 'Dwa punkty odczytane z wykresu mₑ/m₀ = f(m₀)', 'fixed_fraction': 'Założenie autora'}[mode]
    if mode == 'fixed_fraction':
        s.given('e_m0', r'\frac{m_e}{m_0}', law['A'], '', 4, 'Stały udział masy własnej', source)
        return
    if mode == 'two_point':
        s.given('mp_x1', 'x_1', float(p['mass_point_x1']), KG, 0, 'Punkt 1 wykresu — masa startowa', source)
        s.given('mp_y1', 'y_1', float(p['mass_point_y1']), '', 4, 'Punkt 1 wykresu — mₑ/m₀', source)
        s.given('mp_x2', 'x_2', float(p['mass_point_x2']), KG, 0, 'Punkt 2 wykresu — masa startowa', source)
        s.given('mp_y2', 'y_2', float(p['mass_point_y2']), '', 4, 'Punkt 2 wykresu — mₑ/m₀', source)
        s.calc('C_e', 'C', r'\frac{\log\left(y_1/y_2\right)}{\log\left(x_1/x_2\right)}',
               r'\frac{\log\left([[mp_y1]]/[[mp_y2]]\right)}{\log\left([[mp_x1]]/[[mp_x2]]\right)}', law['C'], '', 5,
               'Wykładnik równania (1)', SOURCES['B1'] + ', s. 1',
               check=lambda v: math.log(v.mp_y1 / v.mp_y2) / math.log(v.mp_x1 / v.mp_x2))
        s.calc('A_e', 'A', r'\frac{y_1}{x_1^{C}}', r'\frac{[[mp_y1]]}{[[mp_x1]]^{[[C_e]]}}', law['A'], '', 5,
               'Współczynnik równania (1)', SOURCES['B1'] + ', s. 1', check=lambda v: v.mp_y1 / v.mp_x1 ** v.C_e)
    else:
        s.given('A_e', 'A', law['A'], '', 5, 'Współczynnik równania (1)', source)
        s.given('C_e', 'C', law['C'], '', 5, 'Wykładnik równania (1)', source)
    s.given('K_vs', 'K_{vs}', law['k_vs'], '', 2, 'Współczynnik stałości skosu (1,0 — stały; 1,04 — zmienny)', SOURCES['B1'] + ', s. 1')
    m0, value = mass['m0'], mass['m_empty'] / mass['m0']
    if mode == 'class_correlation':
        s.given('K_kor', 'K_{kor}', law['structural_modifier'], '', 4, 'Poprawka konstrukcyjna korelacji klasy', 'Korelacja klasy')
        raw = law['A'] * m0 ** law['C'] * law['k_vs'] * law['structural_modifier']
        bounded = not .38 <= raw <= .74
        formula, subst = r'A\,m_0^{C}K_{vs}K_{kor}', r'[[A_e]]\cdot[[m0]]^{[[C_e]]}\cdot[[K_vs]]\cdot[[K_kor]]'
        if bounded:  # Korelacja klasy jest ograniczona do 0,38–0,74; zapis jawny, by podstawienie dawało wynik.
            formula = r'\min\left(0{,}74;\;\max\left(0{,}38;\;' + formula + r'\right)\right)'
            subst = r'\min\left(0{,}74;\;\max\left(0{,}38;\;' + subst + r'\right)\right)'
        s.calc('e_m0', r'\frac{m_e}{m_0}', formula, subst,
               value, '', 4, 'Udział masy własnej dla masy startowej projektu', SOURCES['B1'] + ', wzór (1)',
               check=lambda v: min(.74, max(.38, v.A_e * v.m0 ** v.C_e * v.K_vs * v.K_kor)))
    else:
        s.calc('e_m0', r'\frac{m_e}{m_0}', r'A\,m_0^{C}K_{vs}', r'[[A_e]]\cdot[[m0]]^{[[C_e]]}\cdot[[K_vs]]', value, '', 4,
               'Udział masy własnej dla masy startowej projektu', SOURCES['B1'] + ', wzór (1)',
               check=lambda v: v.A_e * v.m0 ** v.C_e * v.K_vs)


def _p2_matching(s, r):
    p, mass, sz = r['params'], r['mass'], r['sizing']
    dp, t, geom = sz['design_point'], sz['terms'], r['geometry']
    s.section('p2', 'matching', 'Obciążenie powierzchni i powierzchnia nośna', SOURCES['B2'] + ', wzory (1)–(5), (10)')
    _kmh(s, 'V_min', r'V_{min}', float(p['v_stall_kmh']), 'Wymagana prędkość minimalna', 'Wymagania tematu')
    s.calc('WS_Vmin', r'\left(\tfrac{W}{S}\right)_{V_{min}}', r'\frac{\rho_0 V_{min}^2}{2}\,\frac{C_{z\,max,L}}{1{,}1}',
           r'\frac{[[rho0]]\cdot[[V_min]]^2}{2}\cdot\frac{[[Cz_L]]}{1{,}1}', t['ws_min_speed'], NM2, 1,
           'Ograniczenie z prędkości minimalnej', SOURCES['B2'] + ', wzór (10)',
           check=lambda v: .5 * v.rho0 * v.V_min ** 2 * v.Cz_L / 1.1)
    candidates = [r'[[WS_Vmin]]']
    if t['ws_landing'] is not None:
        s.given('s_L', 's_L', t['s_l'], M, 0, 'Długość lądowania znad przeszkody 15 m', 'Wymagania tematu')
        s.given('sigma_lot', r'\sigma', 1.0, '', 1, 'Gęstość względna na lotnisku', SOURCES['B2'])
        s.calc('WS_L_lnd', r'\left(\tfrac{W}{S}\right)_{L,ląd}', r'\frac{\sigma C_{z\,max,L}\,(s_L-122)}{0{,}75}',
               r'\frac{[[sigma_lot]]\cdot[[Cz_L]]\cdot([[s_L]]-122)}{0{,}75}', t['ws_landing_l'], NM2, 1,
               'Ograniczenie z długości lądowania (dla masy do lądowania)', SOURCES['B2'] + ', wzór (3)',
               check=lambda v: v.sigma_lot * v.Cz_L * (v.s_L - 122) / .75)
        s.given('m_lnd', r'm_{ląd}', t['m_landing'], KG, 1, 'Masa na początku lądowania (bilans misji)', 'P2, tabela faz')
        s.calc('WS_L', r'\left(\tfrac{W}{S}\right)_{L}', r'\left(\tfrac{W}{S}\right)_{L,ląd}\frac{m_0}{m_{ląd}}',
               r'[[WS_L_lnd]]\cdot\frac{[[m0]]}{[[m_lnd]]}', t['ws_landing'], NM2, 1,
               'Ograniczenie z lądowania przeliczone na masę startową', SOURCES['B2'] + ', uwaga do wzoru (3)',
               check=lambda v: v.WS_L_lnd * v.m0 / v.m_lnd)
        candidates.append(r'[[WS_L]]')
    fixed_area = geom['wing']['area_fixed']
    state = r['constraints']['parameter_states'].get('wing_area_m2') or {}
    if fixed_area and state.get('state') == 'derived' and geom['wing']['span_fixed']:
        # Tryb „rozpiętość i wydłużenie”: powierzchnię wyznacza się z założeń geometrii, a nie z W/S.
        s.calc('S', 'S', r'\frac{b^2}{\Lambda}', r'\frac{[[b]]^2}{[[AR_1]]}', geom['wing']['S'], M2, 2,
               'Powierzchnia skrzydła z zadanej rozpiętości i wydłużenia', check=lambda v: v.b ** 2 / v.AR_1)
    elif fixed_area:
        s.given('S', 'S', geom['wing']['S'], M2, 2, 'Powierzchnia skrzydła zadana przez autora', 'Założenia projektu')
    if fixed_area:
        s.calc('WS', r'\frac{W}{S}', r'\frac{m_0 g}{S}', r'\frac{[[m0]]\cdot[[g]]}{[[S]]}', dp['ws'], NM2, 1,
               'Obciążenie powierzchni dla zadanej powierzchni', check=lambda v: v.m0 * v.g / v.S)
    else:
        if len(candidates) > 1:
            s.calc('WS', r'\frac{W}{S}', r'\min\left\{\left(\tfrac{W}{S}\right)_{V_{min}};\left(\tfrac{W}{S}\right)_{L}\right\}',
                   r'\min\left\{' + ';\\;'.join(candidates) + r'\right\}', dp['ws'], NM2, 1,
                   'Obciążenie powierzchni w punkcie projektowym', SOURCES['B2'],
                   check=lambda v: round(min(v.WS_Vmin, v.WS_L), 1))
        else:
            s.calc('WS', r'\frac{W}{S}', r'\left(\tfrac{W}{S}\right)_{V_{min}}', r'[[WS_Vmin]]', dp['ws'], NM2, 1,
                   'Obciążenie powierzchni w punkcie projektowym', SOURCES['B2'], check=lambda v: round(v.WS_Vmin, 1))
        s.calc('S', 'S', r'\frac{m_0 g}{W/S}', r'\frac{[[m0]]\cdot[[g]]}{[[WS]]}', geom['wing']['S'], M2, 2,
               'Powierzchnia nośna', SOURCES['B2'] + ', wzór (1)', check=lambda v: v.m0 * v.g / v.WS)

    if not _powered(r):
        return
    jet = p['engine_type'] == 'jet'
    s.section('p2', 'drive', 'Wymagania napędu w punkcie projektowym', SOURCES['B2'] + ', wzory (2), (6)–(9), (11)–(12)')
    ar = _ar_key(r)
    cx0_key = 'Cx0_1'
    if abs(t['cx0'] - s.entries['Cx0_1']['value']) > 1e-12:
        s.given('dCx0_dob', r'\Delta C_{x0,konf}', t['cx0'] - t['cx0_base'], '', 4, 'Dodatek konfiguracji do oporu zerowego', 'Założenie')
        s.calc('Cx0_2', r'C_{x0}', r'C_{x0,1}+\Delta C_{x0,konf}', r'[[Cx0_1]]+[[dCx0_dob]]', t['cx0'], '', 4,
               'Opór zerowy do wykresu doboru', check=lambda v: v.Cx0_1 + v.dCx0_dob)
        cx0_key = 'Cx0_2'
    cx0 = f'[[{cx0_key}]]'
    s.given('w_y_wym', r'w_{y,wym}', t['climb_rate_ms'], MS, 2, 'Wymagana prędkość wznoszenia przy ziemi', 'Wymagania tematu')
    s.calc('V_wzn', r'V_{wzn}', r'V_{min}+0{,}25\,(V_{max}-V_{min}),\;V_{max}=V_{cr}', r'[[V_min]]+0{,}25\cdot([[V_cr]]-[[V_min]])',
           t['v_climb_ms'], MS, 2, 'Prędkość wznoszenia (Vmax przyjęto równą prędkości przelotowej)', SOURCES['B2'] + ', s. 3',
           check=lambda v: v.V_min + .25 * max(0, v.V_cr - v.V_min))
    s.calc('q_wzn', r'q_{wzn}', r'\frac{\rho_0V_{wzn}^2}{2}', r'\frac{[[rho0]]\cdot[[V_wzn]]^2}{2}', t['q_climb'], PA, 1,
           'Ciśnienie dynamiczne przy wznoszeniu', check=lambda v: .5 * v.rho0 * v.V_wzn ** 2)
    s.calc('G_wzn', 'G', r'\frac{w_{y,wym}}{V_{wzn}}', r'\frac{[[w_y_wym]]}{[[V_wzn]]}', t['gradient'], '', 4,
           'Gradient wznoszenia', SOURCES['B1W'] + ', wzór (11)', check=lambda v: v.w_y_wym / v.V_wzn)
    s.calc('TW_wzn_min', r'\left(\tfrac{T}{W}\right)_{min}', r'G+2\sqrt{C_{x0}k}', rf'[[G_wzn]]+2\sqrt{{{cx0}\cdot[[k_1]]}}',
           t['tw_climb_min'], '', 4, 'Najmniejszy stosunek ciągu do ciężaru dla wznoszenia', SOURCES['B1W'] + ', wzór (18)',
           check=lambda v: v.G_wzn + 2 * math.sqrt(getattr(v, cx0_key) * v.k_1))
    at = t['at_design']
    # Start
    if p.get('operating_surface') == 'water':
        tw_to = 0.0
        s.given('TW_TO', r'(T/W)_{TO}', 0.0, '', 1,
                'Ograniczenie startu lądowego wyłączone; operacji wodnych nie wyznaczono', 'Zakres modelu')
    elif t['s_to']:
        s.given('s_TO', r's_{TO}', t['s_to'], M, 0, 'Długość startu do wysokości 15 m', 'Wymagania tematu')
        s.calc('TOP', 'TOP', r'\frac{W/S}{C_{z\,max,TO}\,\sigma}', r'\frac{[[WS]]}{[[Cz_TO]]\cdot1}', dp['ws'] / t['cz_max_to'], NM2, 1,
               'Parametr startu', SOURCES['B2'] + ', wzór (2)', check=lambda v: v.WS / v.Cz_TO)
        tw_to = 0.133 * s.entries['TOP']['value'] / (t['s_to'] - 3.834 * math.sqrt(s.entries['TOP']['value']))
        s.calc('TW_TO', r'\left(\tfrac{T}{W}\right)_{TO}', r'\frac{0{,}133\,TOP}{s_{TO}-3{,}834\sqrt{TOP}}',
               r'\frac{0{,}133\cdot[[TOP]]}{[[s_TO]]-3{,}834\sqrt{[[TOP]]}}', tw_to, '', 4,
               'Ciąg względny wymagany do startu', SOURCES['B2'] + ', wzór (2)',
               check=lambda v: .133 * v.TOP / (v.s_TO - 3.834 * math.sqrt(v.TOP)))
    else:
        s.given('s_roz', r's_{roz}', max(30.0, t['s_run']), M, 0, 'Długość rozbiegu', 'Wymagania tematu')
        tw_to = 1.21 * dp['ws'] / (G0 * RHO0 * t['cz_max_to'] * max(30.0, t['s_run'])) + .04
        s.calc('TW_TO', r'\left(\tfrac{T}{W}\right)_{TO}', r'\frac{1{,}21\,W/S}{g\rho_0C_{z\,max,TO}s_{roz}}+\mu',
               r'\frac{1{,}21\cdot[[WS]]}{[[g]]\cdot[[rho0]]\cdot[[Cz_TO]]\cdot[[s_roz]]}+0{,}04', tw_to, '', 4,
               'Ciąg względny do rozbiegu (wzór zastępczy, μ = 0,04)',
               check=lambda v: 1.21 * v.WS / (v.g * v.rho0 * v.Cz_TO * v.s_roz) + .04)
    tw_cl = t['q_climb'] * t['cx0'] / dp['ws'] + dp['ws'] * t['k_ind'] / t['q_climb'] + t['gradient']
    s.calc('TW_wzn', r'\left(\tfrac{T}{W}\right)_{wzn}', r'\frac{q_{wzn}C_{x0}}{W/S}+\frac{W/S}{q_{wzn}\pi\Lambda e}+G',
           rf'\frac{{[[q_wzn]]\cdot{cx0}}}{{[[WS]]}}+[[WS]]\cdot\frac{{[[k_1]]}}{{[[q_wzn]]}}+[[G_wzn]]', tw_cl, '', 4,
           'Ciąg względny do wznoszenia', SOURCES['B2'] + ', wzór (9)',
           check=lambda v: v.q_wzn * getattr(v, cx0_key) / v.WS + v.WS * v.k_1 / v.q_wzn + v.G_wzn)
    tw_cr = t['q_cr'] * t['cx0'] / dp['ws'] + dp['ws'] * t['k_ind'] / t['q_cr']
    s.calc('TW_cr', r'\left(\tfrac{T}{W}\right)_{cr}', r'\frac{q_{cr}C_{x0}}{W/S}+\frac{W/S}{q_{cr}\pi\Lambda e}',
           rf'\frac{{[[q_cr]]\cdot{cx0}}}{{[[WS]]}}+[[WS]]\cdot\frac{{[[k_1]]}}{{[[q_cr]]}}', tw_cr, '', 4,
           'Ciąg względny do lotu poziomego z prędkością przelotową', SOURCES['B1W'] + ', wzór (61)',
           check=lambda v: v.q_cr * getattr(v, cx0_key) / v.WS + v.WS * v.k_1 / v.q_cr)
    _lapse(s, r, 'phi_cr', 'cr', t['lapse_cr'])
    if jet:
        s.calc('TW_cr_inst', r'\left(\tfrac{T}{W}\right)_{cr,0}', r'\frac{(T/W)_{cr}}{\varphi_H}', r'\frac{[[TW_cr]]}{[[phi_cr]]}',
               at['przelot'], '', 4, 'Przeliczenie na ciąg startowy (spadek ciągu z wysokością)',
               check=lambda v: v.TW_cr / v.phi_cr)
        req = [('TW_TO', 'start'), ('TW_wzn', 'wznoszenie'), ('TW_cr_inst', 'przelot')]
        s.given('TW_extra', r'(T/W)_{zad}', max((v for k,v in at.items() if k not in ('start','wznoszenie','przelot')), default=0), '', 5,
                'Dodatkowe ograniczenie misji: prędkość maksymalna lub holowanie; zero przy braku wymagania', 'Dodatkowe krzywe wykresu doboru P2')
        tw0 = round(max(at.values()) * 1.06, 3)
        s.calc('TW_dob', r'\left(\tfrac{T}{W}\right)_{dob}', r'1{,}06\,\max\{(T/W)_{TO};(T/W)_{wzn};(T/W)_{cr,0};(T/W)_{zad}\}',
               r'1{,}06\cdot\max\left\{[[TW_TO]];\;[[TW_wzn]];\;[[TW_cr_inst]];\;[[TW_extra]]\right\}', tw0, '', 3,
               'Stosunek ciągu do ciężaru z wykresu doboru (6% zapasu)', SOURCES['B2'],
               check=lambda v: round(1.06 * max(v.TW_TO, v.TW_wzn, v.TW_cr_inst, v.TW_extra), 3))
        if sz.get('flight_model_requirement') is not None:
            s.given('TW_P4', r'(T/W)_{P4}', sz['flight_model_requirement']['required_rating']/(mass['m0']*G0), '', 5,
                    'Wymaganie przelotu i wznoszenia z końcowej biegunowej P4', 'Równowaga sił i mocy')
            s.given('TW_TO_check', r'(T/W)_{TO,mod}', sz.get('takeoff_model_requirement', 0), '', 5,
                    'Wymaganie modelu startu; zero oznacza wyłączenie ograniczenia, gdy model nie ma zastosowania', 'P5')
            s.calc('TW', r'T/W', r'\max\{(T/W)_{dob};1{,}06(T/W)_{P4};1{,}06(T/W)_{TO,mod}\}',
                   r'\max\{[[TW_dob]];1{,}06[[TW_P4]];1{,}06[[TW_TO_check]]\}', dp['tw'], '', 5,
                   'Przyjęty ciąg względny po sprawdzeniu P4 i P5',
                   check=lambda v: max(v.TW_dob, 1.06*v.TW_P4, 1.06*v.TW_TO_check))
        elif sz.get('takeoff_model_requirement') is not None:
            s.given('TW_mod', r'\left(\tfrac{T}{W}\right)_{TO,mod}', sz['takeoff_model_requirement'], '', 4,
                    'Ciąg względny z modelu startu P5 dla wymaganej drogi (rozwiązanie numeryczne)', SOURCES['ML'] + ', P6')
            s.calc('TW', r'\frac{T}{W}', r'\max\left\{\left(\tfrac{T}{W}\right)_{dob};\;1{,}06\left(\tfrac{T}{W}\right)_{TO,mod}\right\}',
                   r'\max\left\{[[TW_dob]];\;1{,}06\cdot[[TW_mod]]\right\}', dp['tw'], '', 4, 'Stosunek ciągu do ciężaru przyjęty',
                   check=lambda v: max(v.TW_dob, 1.06 * v.TW_mod))
        else:
            s.calc('TW', r'\frac{T}{W}', r'\left(\tfrac{T}{W}\right)_{dob}', r'[[TW_dob]]', dp['tw'], '', 4,
                   'Stosunek ciągu do ciężaru przyjęty', check=lambda v: v.TW_dob)
        s.calc('T_0', 'T', r'\frac{(T/W)\,m_0 g}{1000}', r'\frac{[[TW]]\cdot[[m0]]\cdot[[g]]}{1000}', dp['thrust_kn'], KN, 2,
               'Ciąg startowy zespołu napędowego', check=lambda v: v.TW * v.m0 * v.g / 1000)
    else:
        s.given('eta_TO', r'\eta_{TO}', t['eta_to'], '', 2, 'Sprawność śmigła na rozbiegu', 'Założenie')
        s.calc('V_sr', r'V_{śr}', r'\frac{1{,}12}{\sqrt2}\sqrt{\frac{2\,W/S}{\rho_0C_{z\,max,TO}}}',
               r'\frac{1{,}12}{\sqrt2}\cdot\sqrt{\frac{2\cdot[[WS]]}{[[rho0]]\cdot[[Cz_TO]]}}', t['v_mean_to'], MS, 2,
               'Średnia prędkość rozbiegu (VLOF/√2, VLOF = 1,12 VS,TO)', check=lambda v: 1.12 * math.sqrt(2 * v.WS / (v.rho0 * v.Cz_TO)) / math.sqrt(2))
        s.calc('PW_TO', r'\left(\tfrac{N}{W}\right)_{TO}', r'\left(\tfrac{T}{W}\right)_{TO}\frac{V_{śr}}{\eta_{TO}}', r'[[TW_TO]]\cdot\frac{[[V_sr]]}{[[eta_TO]]}',
               at.get('start'), r'\mathrm{W/N}', 3, 'Moc względna do startu', SOURCES['B2'] + ': T = ηN/V',
               check=lambda v: v.TW_TO * v.V_sr / v.eta_TO)
        s.calc('PW_wzn', r'\left(\tfrac{N}{W}\right)_{wzn}', r'\left(\tfrac{T}{W}\right)_{wzn}\frac{V_{wzn}}{\eta_p}', r'[[TW_wzn]]\cdot\frac{[[V_wzn]]}{[[eta_p]]}',
               at['wznoszenie'], r'\mathrm{W/N}', 3, 'Moc względna do wznoszenia', check=lambda v: v.TW_wzn * v.V_wzn / v.eta_p)
        s.calc('PW_cr', r'\left(\tfrac{N}{W}\right)_{cr}', r'\left(\tfrac{T}{W}\right)_{cr}\frac{V_{cr}}{\eta_p\varphi_H}',
               r'[[TW_cr]]\cdot\frac{[[V_cr]]}{[[eta_p]]\cdot[[phi_cr]]}', at['przelot'], r'\mathrm{W/N}', 3,
               'Moc względna do przelotu (przeliczona na moc startową)', check=lambda v: v.TW_cr * v.V_cr / (v.eta_p * v.phi_cr))
        pw0 = round(max(at.values()) * 1.08, 2)
        s.given('PW_extra', r'(N/W)_{zad}', max((v for k,v in at.items() if k not in ('start','wznoszenie','przelot')), default=0), r'\mathrm{W/N}', 5,
                'Dodatkowe ograniczenie misji: prędkość maksymalna lub holowanie; zero przy braku wymagania', 'Dodatkowe krzywe wykresu doboru P2')
        s.calc('PW_dob', r'\left(\tfrac{N}{W}\right)_{dob}', r'1{,}08\,\max\{(N/W)_{TO};(N/W)_{wzn};(N/W)_{cr};(N/W)_{zad}\}',
               r'1{,}08\cdot\max\left\{[[PW_TO]];\;[[PW_wzn]];\;[[PW_cr]];\;[[PW_extra]]\right\}', pw0, r'\mathrm{W/N}', 2,
               'Moc względna z wykresu doboru (8% zapasu)', SOURCES['B2'],
               check=lambda v: round(1.08 * max(v.PW_TO, v.PW_wzn, v.PW_cr, v.PW_extra), 2))
        p_dob = round(pw0 * mass['m0'] * G0 / 1000, 1)
        s.calc('P_dob', r'N_{dob}', r'\frac{(N/W)_{dob}\,m_0 g}{1000}', r'\frac{[[PW_dob]]\cdot[[m0]]\cdot[[g]]}{1000}', p_dob, KW, 1,
               'Moc z wykresu doboru', check=lambda v: v.PW_dob * v.m0 * v.g / 1000)
        required = dp['required_power_kw']
        if sz.get('flight_model_requirement') is not None:
            s.given('P_P4', r'N_{P4}', sz['flight_model_requirement']['required_rating']/1000, KW, 3,
                    'Wymaganie mocy na wale z końcowej biegunowej P4 (przelot i wznoszenie)', 'Równowaga sił i mocy')
            s.given('PW_TO_check', r'(N/W)_{TO,mod}', sz.get('takeoff_model_requirement', 0), r'\mathrm{W/N}', 5,
                    'Wymaganie modelu startu; zero oznacza wyłączenie ograniczenia, gdy model nie ma zastosowania', 'P5')
            s.calc('P_wym', r'N_{wym}', r'\max\{N_{dob};1{,}08N_{P4};1{,}08(N/W)_{TO,mod}m_0g/1000\}',
                   r'\max\{[[P_dob]];1{,}08[[P_P4]];1{,}08[[PW_TO_check]][[m0]][[g]]/1000\}', required, KW, 2,
                   'Moc wymagana po sprawdzeniu P4 i P5',
                   check=lambda v: max(v.P_dob, 1.08*v.P_P4, 1.08*v.PW_TO_check*v.m0*v.g/1000))
        elif sz.get('takeoff_model_requirement') is not None:
            s.given('PW_mod', r'\left(\tfrac{N}{W}\right)_{TO,mod}', sz['takeoff_model_requirement'], r'\mathrm{W/N}', 3,
                    'Moc względna z modelu startu P5 dla wymaganej drogi (rozwiązanie numeryczne)', SOURCES['ML'] + ', P6')
            s.calc('P_wym', r'N_{wym}', r'\max\left\{N_{dob};\;\frac{1{,}08\,(N/W)_{TO,mod}\,m_0g}{1000}\right\}',
                   r'\max\left\{[[P_dob]];\;\frac{1{,}08\cdot[[PW_mod]]\cdot[[m0]]\cdot[[g]]}{1000}\right\}', required, KW, 1,
                   'Moc wymagana', check=lambda v: max(v.P_dob, 1.08 * v.PW_mod * v.m0 * v.g / 1000))
        else:
            s.calc('P_wym', r'N_{wym}', r'N_{dob}', r'[[P_dob]]', required, KW, 1, 'Moc wymagana', check=lambda v: v.P_dob)
        if p.get('power_input_mode') == 'fixed' or 'engine_power_kw' in p.get('locked_params', []):
            s.given('P', 'N', dp['power_kw'], KW, 1, 'Moc dostępna zadana przez autora (silnik wybrany)', 'Założenia projektu')
        else:
            s.calc('P', 'N', r'N_{wym}', r'[[P_wym]]', dp['power_kw'], KW, 1, 'Moc startowa zespołu napędowego',
                   check=lambda v: v.P_wym)
        s.calc('PW', r'\frac{N}{W}', r'\frac{1000\,N}{m_0 g}', r'\frac{1000\cdot[[P]]}{[[m0]]\cdot[[g]]}', dp['pw'], r'\mathrm{W/N}', 3,
               'Moc względna przyjęta do obliczeń osiągów', check=lambda v: 1000 * v.P / (v.m0 * v.g))
    if t.get('ws_max_range_cruise') is not None:
        if jet:
            s.calc('WS_R_cr', r'\left(\tfrac{W}{S}\right)_{R,cr}', r'q_{cr}\sqrt{\frac{\pi\Lambda e\,C_{x0}}{3}}',
                   r'[[q_cr]]\cdot\sqrt{\frac{\pi\cdot[[' + ar + r']]\cdot[[e_1]]\cdot' + cx0 + r'}{3}}', t['ws_max_range_cruise'], NM2, 1,
                   'Obciążenie największego zasięgu w połowie przelotu', SOURCES['B1W'] + ', wzór (29)',
                   check=lambda v: v.q_cr * math.sqrt(math.pi * getattr(v, ar) * v.e_1 * getattr(v, cx0_key) / 3))
        else:
            s.calc('WS_R_cr', r'\left(\tfrac{W}{S}\right)_{R,cr}', r'q_{cr}\sqrt{\pi\Lambda e\,C_{x0}}',
                   r'[[q_cr]]\cdot\sqrt{\pi\cdot[[' + ar + r']]\cdot[[e_1]]\cdot' + cx0 + r'}', t['ws_max_range_cruise'], NM2, 1,
                   'Obciążenie największego zasięgu w połowie przelotu', SOURCES['B1W'] + ', wzór (22)',
                   check=lambda v: v.q_cr * math.sqrt(math.pi * getattr(v, ar) * v.e_1 * getattr(v, cx0_key)))
        s.given('m_sr_cr', r'm_{śr}', t['m_mid_cruise'], KG, 1, 'Masa w połowie przelotu', 'P2, tabela faz')
        s.calc('WS_R', r'\left(\tfrac{W}{S}\right)_{R}', r'\left(\tfrac{W}{S}\right)_{R,cr}\frac{m_0}{m_{śr}}', r'[[WS_R_cr]]\cdot\frac{[[m0]]}{[[m_sr_cr]]}',
               sz['ws_max_range'], NM2, 1, 'Linia największego zasięgu na wykresie doboru (punkt B)', SOURCES['B2'] + ', wzory (11)–(12)',
               check=lambda v: v.WS_R_cr * v.m0 / v.m_sr_cr)


def _lapse(s, r, key, where, value):
    """Spadek mocy (ciągu) z wysokością — ten sam model co flight_model.propulsion_lapse()."""
    p = r['params']
    sigma = f'[[sigma_{where}]]'
    if p['engine_type'] == 'jet':
        kp = .45 if p.get('aircraft_type') == 'jet_business' else .55
        s.given('k_p', 'k_p', kp, '', 2, 'Współczynnik spadku ciągu z prędkością', SOURCES['ML'] + ', P5')
        s.calc(key, r'\varphi_H', r'\sigma_H^{0{,}85}\max\left(0{,}35;\;1-k_pM\right)',
               sigma + r'^{0{,}85}\cdot\max\left(0{,}35;\;1-[[k_p]]\cdot[[M_cr]]\right)', value, '', 4,
               'Względny ciąg rozporządzalny (silnik dwuprzepływowy)', SOURCES['ML'] + ', P5',
               check=lambda v: getattr(v, 'sigma_' + where) ** .85 * max(.35, 1 - v.k_p * v.M_cr))
    elif p.get('aircraft_type') == 'turboprop_regional':
        s.calc(key, r'\varphi_H', r'\sigma_H^{0{,}85}', sigma + r'^{0{,}85}', value, '', 4, 'Względna moc silnika turbośmigłowego',
               SOURCES['ML'] + ', P5', check=lambda v: getattr(v, 'sigma_' + where) ** .85)
    elif p.get('turbocharged'):
        s.given('sigma_4500', r'\sigma_{4500}', isa_atmosphere(4500)['sigma'], '', 4, 'Gęstość względna wysokości nominalnej', 'ISA')
        s.calc(key, r'\varphi_H', r'\min\left(1;\;\left(\frac{\sigma_H}{\sigma_{4500}}\right)^{0{,}9}\right)',
               r'\min\left(1;\;\left(\frac{' + sigma + r'}{[[sigma_4500]]}\right)^{0{,}9}\right)', value, '', 4,
               'Względna moc silnika doładowanego', SOURCES['ML'] + ', P5',
               check=lambda v: min(1, (getattr(v, 'sigma_' + where) / v.sigma_4500) ** .9))
    else:
        s.calc(key, r'\varphi_H', r'\sigma_H-\frac{1-\sigma_H}{7{,}55}', sigma + r'-\frac{1-' + sigma + r'}{7{,}55}', value, '', 4,
               'Względna moc silnika tłokowego (wzór Gagga–Farrara)', SOURCES['ML'] + ', P5',
               check=lambda v: getattr(v, 'sigma_' + where) - (1 - getattr(v, 'sigma_' + where)) / 7.55)


def _p2_airfoil(s, r):
    af = r['bipol_projects']['p2']['airfoil_selection']
    s.section('p2', 'airfoil', 'Warunki pracy profilu w przelocie', SOURCES['B3'])
    s.calc('Re_cr', r'Re', r'\frac{\rho_H V_{cr}\,\bar c}{\mu_H}', r'\frac{[[rho_cr]]\cdot[[V_cr]]\cdot[[mac]]}{[[mu_cr]]}',
           af['reynolds_cruise'], '', 0, 'Liczba Reynoldsa dla średniej cięciwy aerodynamicznej',
           check=lambda v: v.rho_cr * v.V_cr * v.mac / v.mu_cr, tolerance=.002 * af['reynolds_cruise'] + 1)
    s.calc('Cz_proj', r'C_{z,proj}', r'\frac{2m_0 g}{\rho_H S V_{cr}^2}', r'\frac{2\cdot[[m0]]\cdot[[g]]}{[[rho_cr]]\cdot[[S]]\cdot[[V_cr]]^2}',
           af['cz_proj'], '', 3, 'Obliczeniowy współczynnik siły nośnej profilu', check=lambda v: 2 * v.m0 * v.g / (v.rho_cr * v.S * v.V_cr ** 2))


def _p2_cost(s, r):
    ca = r['bipol_projects']['p2']['cost_analysis']
    t, prod, rdte = ca['terms'], ca['production'], ca['rdte']
    year = ca['cost_year']
    s.section('p2', 'cost', 'Koszt produkcji i cena samolotu', SOURCES['B2'] + ', wzory (13)–(21), tab. 5.9, wzór (5.10)')
    s.calc('W_lb', 'W_s', r'2{,}20462\,m_e', r'2{,}20462\cdot[[m_e]]', t['w_lb'], r'\mathrm{lb}', 1, 'Masa własna w funtach',
           check=lambda v: 2.20462 * v.m_e)
    s.given('V_max_c', r'V_{max}', ca['vmax_knots'] / .539957, KMH, 1, 'Prędkość maksymalna do zależności kosztowych', 'P5 (szybowiec: 0,9 VD)')
    s.calc('V_kt', r'V_{max}', r'0{,}539957\,V_{max}\,[\mathrm{km/h}]', r'0{,}539957\cdot[[V_max_c]]', t['v_kt'], r'\mathrm{kt}', 1,
           'Prędkość maksymalna w węzłach', check=lambda v: .539957 * v.V_max_c)
    s.given('N_P', 'N_P', ca['series_count'], r'\text{szt.}', 0, 'Liczba egzemplarzy serii', 'Założenie')
    s.given('N_am', r'N_{am}', ca['amortization_count'], r'\text{szt.}', 0, 'Liczba egzemplarzy, na które rozkłada się koszty rozwoju', 'Założenie')
    s.given('rok', r'r', year, '', 0, 'Rok kosztów', 'Założenie')
    s.table('cer', 'Zależności kosztowe (Corke)', r'H,\,C=C_1\,W_s^{C_2}\,V_{max}^{C_3}\,N^{C_4}\left(Q^{C_5}\right)',
            note='Współczynniki C₁–C₅ dla 1970 i 1986 r. — BIPOL_2, wzory (13)–(21).', deps=['W_lb', 'V_kt', 'N_P'])
    s.table('extrap', 'Ekstrapolacja do roku kosztów', r'X_{r}=X_{1986}+\left(X_{1986}-X_{1970}\right)\frac{r-1986}{1986-1970}',
            note='Roboczogodziny i stawki ekstrapoluje się osobno; koszt robocizny jest ich iloczynem.', deps=['rok'])
    by = prod['by_year']
    hours = prod['hours_raw']
    for key, name, label in (('H_E', 'H_E', 'Roboczogodziny prac inżynierskich'), ('H_ML', 'H_ML', 'Roboczogodziny produkcji'),
                             ('H_T', 'H_T', 'Roboczogodziny oprzyrządowania')):
        sub = name.split('_')[1]
        h70, h86 = f'H_{{{sub},1970}}', f'H_{{{sub},1986}}'
        s.given(key + '_70', h70, by[name][0], r'\mathrm{h}', 0, label + ' — współczynniki 1970', SOURCES['B2'])
        s.given(key + '_86', h86, by[name][1], r'\mathrm{h}', 0, label + ' — współczynniki 1986', SOURCES['B2'])
        s.calc(key, f'H_{{{sub}}}', rf'{h86}+\left({h86}-{h70}\right)\frac{{r-1986}}{{16}}',
               rf'[[{key}_86]]+\left([[{key}_86]]-[[{key}_70]]\right)\cdot\frac{{[[rok]]-1986}}{{16}}', hours[key[2:]], r'\mathrm{h}', 0,
               label + f' dla serii, rok {year}', check=lambda v, k=key: max(0, getattr(v, k + '_86') + (getattr(v, k + '_86') - getattr(v, k + '_70')) * (v.rok - 1986) / 16),
               tolerance=max(1.0, 1e-6 * hours[key[2:]]))
    rates = t['rates_raw']
    for key, sym, label in (('E', 'R_E', 'Stawka godzinowa — inżynieria'), ('ML', 'R_{ML}', 'Stawka godzinowa — produkcja'),
                            ('T', 'R_T', 'Stawka godzinowa — oprzyrządowanie'), ('QC', 'R_{QC}', 'Stawka godzinowa — kontrola jakości')):
        s.given('R_' + key, sym, rates[key], r'\mathrm{USD/h}', 2, label + f' w roku {year}', SOURCES['B2'] + ', tab. 5.9 (ekstrapolacja)')
    items = prod['items_raw']
    s.calc('C_E', 'C_E', r'H_E R_E', r'[[H_E]]\cdot[[R_E]]', items['C_E'], USD, 0, 'Koszt prac inżynierskich', SOURCES['B2'] + ', wzór (13)',
           check=lambda v: v.H_E * v.R_E)
    s.calc('C_ML', 'C_{ML}', r'H_{ML} R_{ML}', r'[[H_ML]]\cdot[[R_ML]]', items['C_ML'], USD, 0, 'Koszt robocizny', SOURCES['B2'] + ', wzór (16)',
           check=lambda v: v.H_ML * v.R_ML)
    s.calc('C_T', 'C_T', r'H_T R_T', r'[[H_T]]\cdot[[R_T]]', items['C_T'], USD, 0, 'Koszt oprzyrządowania', SOURCES['B2'] + ', wzór (19)',
           check=lambda v: v.H_T * v.R_T)
    s.calc('C_QC', 'C_{QC}', r'0{,}13\,H_{ML}R_{QC}', r'0{,}13\cdot[[H_ML]]\cdot[[R_QC]]', items['C_QC'], USD, 0, 'Koszt kontroli jakości',
           SOURCES['B2'] + ', wzór (20)', check=lambda v: .13 * v.H_ML * v.R_QC)
    s.given('C_MM_70', r'C_{MM,1970}', by['C_MM'][0], USD, 0, 'Koszt materiałów — współczynniki 1970', SOURCES['B2'])
    s.given('C_MM_86', r'C_{MM,1986}', by['C_MM'][1], USD, 0, 'Koszt materiałów — współczynniki 1986', SOURCES['B2'])
    s.calc('C_MM', 'C_{MM}', r'C_{MM,1986}+\left(C_{MM,1986}-C_{MM,1970}\right)\frac{r-1986}{16}',
           r'[[C_MM_86]]+\left([[C_MM_86]]-[[C_MM_70]]\right)\cdot\frac{[[rok]]-1986}{16}', items['C_MM'], USD, 0,
           'Koszt materiałów i półfabrykatów', SOURCES['B2'] + ', wzór (17)',
           check=lambda v: max(0, v.C_MM_86 + (v.C_MM_86 - v.C_MM_70) * (v.rok - 1986) / 16), tolerance=max(1.0, 1e-6 * items['C_MM']))
    s.given('n_sil', 'n_s', t['n_engines'], '', 0, 'Liczba silników', 'Założenia projektu')
    s.given('C_sil', 'C_s', t['engine_price_raw'], USD, 0, 'Cena jednego silnika — ' + ca['engine_basis'], SOURCES['B2'] + ', wzór (15)')
    s.given('C_av', r'C_{av}', t['avionics_raw'], USD, 0, 'Cena awioniki na egzemplarz', 'Założenie')
    s.calc('C_EN', 'C_{EN}', r'N_P\left(n_sC_s+C_{av}\right)', r'[[N_P]]\cdot\left([[n_sil]]\cdot[[C_sil]]+[[C_av]]\right)', items['C_EN'], USD, 0,
           'Koszt silników i awioniki serii', SOURCES['B2'] + ', wzór (15)', check=lambda v: v.N_P * (v.n_sil * v.C_sil + v.C_av))
    s.calc('C_prod', r'C_{prod}', r'C_E+C_{ML}+C_{MM}+C_T+C_{QC}+C_{EN}', r'[[C_E]]+[[C_ML]]+[[C_MM]]+[[C_T]]+[[C_QC]]+[[C_EN]]',
           prod['total_raw'], USD, 0, 'Koszt produkcji serii', check=lambda v: v.C_E + v.C_ML + v.C_MM + v.C_T + v.C_QC + v.C_EN)
    s.given('C_RDTE', r'C_{RDT\&E}', rdte['total_raw'], USD, 0, f'Koszt fazy rozwoju ({rdte["n"]} prototypy) — tabela kosztów', SOURCES['B2'])
    s.given('z_zysk', 'z', t['profit'], '', 3, 'Zysk producenta', 'Założenie')
    s.calc('C_min', r'C_{min}', r'\frac{C_{prod}}{N_P}+\frac{C_{RDT\&E}}{N_{am}}', r'\frac{[[C_prod]]}{[[N_P]]}+\frac{[[C_RDTE]]}{[[N_am]]}',
           t['min_price_raw'], USD, 0, 'Minimalna opłacalna cena egzemplarza', SOURCES['B2'] + ', wzór (5.10)',
           check=lambda v: v.C_prod / v.N_P + v.C_RDTE / v.N_am)
    s.calc('C_cena', r'C', r'(1+z)\,C_{min}', r'(1+[[z_zysk]])\cdot[[C_min]]', t['price_raw'], USD, 0, 'Cena sprzedaży z zyskiem',
           SOURCES['B2'] + ', wzór (5.10)', check=lambda v: (1 + v.z_zysk) * v.C_min)


# =============================================================================================
# P3 — projekt wstępny i analiza masowa
# =============================================================================================
def _p3(s, r):
    p, geom, mass = r['params'], r['geometry'], r['mass']
    w, fus = geom['wing'], geom['fuselage']
    ht, vt = geom['horizontal_tail'], geom['vertical_tail']
    s.section('p3', 'wing', 'Geometria skrzydła', SOURCES['ML'] + ', P2, wzory (2.3)–(2.5)')
    if _span_fixed(r):
        s.given('b', 'b', w['b'], M, 2, 'Rozpiętość zadana', 'Założenia projektu / temat')
        s.calc('AR', r'\Lambda', r'\frac{b^2}{S}', r'\frac{[[b]]^2}{[[S]]}', w['AR'], '', 2, 'Wydłużenie skrzydła',
               check=lambda v: v.b ** 2 / v.S)
    else:
        s.calc('b', 'b', r'\sqrt{S\Lambda}', r'\sqrt{[[S]]\cdot[[AR]]}', w['b'], M, 2, 'Rozpiętość skrzydła',
               check=lambda v: math.sqrt(v.S * v.AR))
    planform = w['wing_planform']
    s.given('lambda_w', r'\lambda', w['eta'], '', 3, 'Zbieżność obrysu c_k/c_0', 'Założenia projektu')
    if planform == 'rectangular':
        s.calc('c_r', 'c', r'\frac{S}{b}', r'\frac{[[S]]}{[[b]]}', w['cr'], M, 3, 'Cięciwa płata prostokątnego', check=lambda v: v.S / v.b)
        s.calc('mac', r'\bar c', 'c', r'[[c_r]]', w['mac'], M, 3, 'Średnia cięciwa aerodynamiczna', check=lambda v: v.c_r)
        s.calc('y_mac', r'y_{\bar c}', r'\frac{b}{4}', r'\frac{[[b]]}{4}', w['y_mac'], M, 2, 'Położenie ŚCA wzdłuż rozpiętości',
               check=lambda v: v.b / 4)
    elif planform == 'elliptical':
        s.calc('c_r', 'c_0', r'\frac{4S}{\pi b}', r'\frac{4\cdot[[S]]}{\pi\cdot[[b]]}', w['cr'], M, 3, 'Cięciwa przykadłubowa płata eliptycznego',
               check=lambda v: 4 * v.S / (math.pi * v.b))
        s.calc('mac', r'\bar c', r'\frac{8}{3\pi}c_0', r'\frac{8}{3\pi}\cdot[[c_r]]', w['mac'], M, 3, 'Średnia cięciwa aerodynamiczna',
               check=lambda v: 8 / (3 * math.pi) * v.c_r)
        s.calc('y_mac', r'y_{\bar c}', r'\frac{2b}{3\pi}', r'\frac{2\cdot[[b]]}{3\pi}', w['y_mac'], M, 2, 'Położenie ŚCA wzdłuż rozpiętości',
               check=lambda v: 2 * v.b / (3 * math.pi))
    elif planform == 'compound_trapezoid':
        s.given('xi_b', r'\xi', float(p.get('break_span_ratio', .4)), '', 2, 'Względne położenie załamania obrysu', 'Założenia projektu')
        s.calc('y_b', 'y_b', r'\xi\frac{b}{2}', r'[[xi_b]]\cdot\frac{[[b]]}{2}', w['break_station_m'], M, 2, 'Położenie załamania',
               check=lambda v: v.xi_b * v.b / 2)
        s.calc('w_k', 'w', r'\frac{b}{2}-y_b', r'\frac{[[b]]}{2}-[[y_b]]', w['b'] / 2 - w['break_station_m'], M, 2, 'Rozpiętość końcówki',
               check=lambda v: v.b / 2 - v.y_b)
        s.calc('c_r', 'c_0', r'\frac{S}{2\left(y_b+\frac{1+\lambda}{2}w\right)}', r'\frac{[[S]]}{2\left([[y_b]]+\frac{1+[[lambda_w]]}{2}\cdot[[w_k]]\right)}',
               w['cr'], M, 3, 'Cięciwa centropłata', check=lambda v: v.S / (2 * (v.y_b + (1 + v.lambda_w) / 2 * v.w_k)))
        s.calc('c_t', 'c_k', r'\lambda c_0', r'[[lambda_w]]\cdot[[c_r]]', w['ct'], M, 3, 'Cięciwa końcowa', check=lambda v: v.lambda_w * v.c_r)
        s.calc('mac', r'\bar c', r'\frac{2}{S}\left[c_0^2y_b+\frac{w}{3}\left(c_0^2+c_0c_k+c_k^2\right)\right]',
               r'\frac{2}{[[S]]}\left[[[c_r]]^2\cdot[[y_b]]+\frac{[[w_k]]}{3}\left([[c_r]]^2+[[c_r]]\cdot[[c_t]]+[[c_t]]^2\right)\right]', w['mac'], M, 3,
               'Średnia cięciwa aerodynamiczna', check=lambda v: 2 / v.S * (v.c_r ** 2 * v.y_b + v.w_k / 3 * (v.c_r ** 2 + v.c_r * v.c_t + v.c_t ** 2)))
        s.given('y_mac', r'y_{\bar c}', w['y_mac'], M, 2, 'Położenie ŚCA (moment statyczny obrysu)', 'Całkowanie obrysu')
    else:
        s.calc('c_r', 'c_0', r'\frac{2S}{b\,(1+\lambda)}', r'\frac{2\cdot[[S]]}{[[b]]\cdot(1+[[lambda_w]])}', w['cr'], M, 3,
               'Cięciwa przykadłubowa', check=lambda v: 2 * v.S / (v.b * (1 + v.lambda_w)))
        s.calc('c_t', 'c_k', r'\lambda c_0', r'[[lambda_w]]\cdot[[c_r]]', w['ct'], M, 3, 'Cięciwa końcowa', check=lambda v: v.lambda_w * v.c_r)
        s.calc('mac', r'\bar c', r'\frac{2}{3}c_0\frac{1+\lambda+\lambda^2}{1+\lambda}',
               r'\frac{2}{3}\cdot[[c_r]]\cdot\frac{1+[[lambda_w]]+[[lambda_w]]^2}{1+[[lambda_w]]}', w['mac'], M, 3,
               'Średnia cięciwa aerodynamiczna', SOURCES['ML'] + ', wzór (2.4)',
               check=lambda v: 2 / 3 * v.c_r * (1 + v.lambda_w + v.lambda_w ** 2) / (1 + v.lambda_w))
        s.calc('y_mac', r'y_{\bar c}', r'\frac{b}{6}\,\frac{1+2\lambda}{1+\lambda}', r'\frac{[[b]]}{6}\cdot\frac{1+2\cdot[[lambda_w]]}{1+[[lambda_w]]}',
               w['y_mac'], M, 2, 'Położenie ŚCA wzdłuż rozpiętości', check=lambda v: v.b / 6 * (1 + 2 * v.lambda_w) / (1 + v.lambda_w))
        s.given('chi25', r'\chi_{25}', w['sweep_deg'], DEG, 1, 'Skos linii 25% cięciw', 'Założenia projektu')
        s.calc('x_le_mac', r'x_{N,\bar c}', r'y_{\bar c}\left(\tan\chi_{25}+\frac{c_0(1-\lambda)}{2b}\right)',
               r'[[y_mac]]\cdot\left(\tan[[chi25]]^{\circ}+\frac{[[c_r]]\cdot(1-[[lambda_w]])}{2\cdot[[b]]}\right)', w['x_le_mac'], M, 2,
               'Odsunięcie noska ŚCA od noska cięciwy przykadłubowej',
               check=lambda v: v.y_mac * (math.tan(math.radians(v.chi25)) + v.c_r * (1 - v.lambda_w) / (2 * v.b)), tolerance=.011)

    s.section('p3', 'fuselage', 'Wymiary kadłuba', 'Proporcje wstępne programu (do sprawdzenia rysunkiem zabudowy)')
    ac = p.get('aircraft_type', 'piston_ga')
    if fus.get('cargo_bay'):
        bay = fus['cargo_bay']
        for key, symbol, value, label in [
            ('l_layout', 'l_{kab}', bay['layout_length_m'], 'Długość z bazowego układu kabiny'),
            ('d_layout', 'd_{kab}', bay['layout_diameter_m'], 'Średnica z bazowego układu kabiny'),
            ('l_bay', 'l_{lad}', bay['length_m'], 'Długość użytkowa ładowni'),
            ('w_bay', 'w_{lad}', bay['width_m'], 'Szerokość użytkowa ładowni'),
            ('h_bay', 'h_{lad}', bay['height_m'], 'Wysokość użytkowa ładowni'),
            ('shell_bay', r'\Delta d', bay['shell_diametral_allowance_m'], 'Wstępny naddatek średnicy na konstrukcję')]:
            s.given(key, symbol, value, M, 2, label, 'Jawne założenia zabudowy, do sprawdzenia rysunkiem')
        s.calc('d_k', 'd_k', r'\max\{d_{kab};\sqrt{w_{lad}^2+h_{lad}^2}+\Delta d\}',
               r'\max\{[[d_layout]];\sqrt{[[w_bay]]^2+[[h_bay]]^2}+[[shell_bay]]\}', fus['diameter'], M, 3,
               'Obwiednia kołowa przekroju użytkowego ładowni',
               check=lambda v: max(v.d_layout, math.hypot(v.w_bay, v.h_bay)+v.shell_bay))
        s.calc('l_k', 'l_k', r'\max\{l_{kab};l_{lad}+4d_k\}', r'\max\{[[l_layout]];[[l_bay]]+4[[d_k]]\}',
               fus['length'], M, 3, 'Długość kadłuba z ładownią, nosem i ogonem',
               check=lambda v: max(v.l_layout, v.l_bay+4*v.d_k))
    elif ac in ('glider', 'motoglider'):
        s.calc('l_k', 'l_k', r'\max\left(5{,}5;\;0{,}45\,b\right)', r'\max\left(5{,}5;\;0{,}45\cdot[[b]]\right)', fus['length'], M, 2,
               'Długość kadłuba', check=lambda v: max(5.5, .45 * v.b), tolerance=.011)
        s.given('d_k', 'd_k', fus['diameter'], M, 2, 'Średnica zastępcza przekroju kabiny (układ i liczba miejsc)', 'Wymiary kabin szybowcowych')
    elif ac == 'uav':
        s.calc('l_k', 'l_k', r'\max\left(1{,}5;\;0{,}55\,b\right)', r'\max\left(1{,}5;\;0{,}55\cdot[[b]]\right)', fus['length'], M, 2,
               'Długość kadłuba', check=lambda v: max(1.5, .55 * v.b), tolerance=.011)
        s.calc('d_k', 'd_k', r'\min\left(1{,}4;\;\max\left(0{,}25;\;0{,}08\,m_0^{1/3}\right)\right)',
               r'\min\left(1{,}4;\;\max\left(0{,}25;\;0{,}08\cdot[[m0]]^{1/3}\right)\right)', fus['diameter'], M, 2,
               'Średnica kadłuba (przekrój ładunku i paliwa)', check=lambda v: min(1.4, max(.25, .08 * v.m0 ** (1 / 3))), tolerance=.006)
    elif ac == 'piston_ga':
        s.calc('l_k', 'l_k', r'\max\left(5{,}5;\;0{,}72\,b\right)', r'\max\left(5{,}5;\;0{,}72\cdot[[b]]\right)', fus['length'], M, 2,
               'Długość kadłuba', check=lambda v: max(5.5, .72 * v.b), tolerance=.011)
        s.given('d_k', 'd_k', fus['diameter'], M, 2, 'Średnica kadłuba (1,25 m do 4 pasażerów, dalej 1,50 m)', 'Wymiary kabin GA')
    else:
        n_ab = fus['seats_abreast']
        shell = (.45, .30) if ac in ('turboprop_regional', 'jet_business') else (.50, .35)
        s.given('n_ab', r'n_{rz}', n_ab, '', 0, 'Liczba foteli w rzędzie', 'Układ kabiny')
        s.calc('d_k', 'd_k', rf'0{{,}}48\,n_{{rz}}+{tex_value(shell[0], 2)}+{tex_value(shell[1], 2)}',
               rf'0{{,}}48\cdot[[n_ab]]+{tex_value(shell[0], 2)}+{tex_value(shell[1], 2)}', fus['diameter'], M, 2,
               'Średnica kadłuba (fotele, przejście i poszycie)', check=lambda v: .48 * v.n_ab + sum(shell), tolerance=.006)
        s.calc('l_k', 'l_k', r'0{,}80\max\left(2;\;\left\lceil\frac{n_{pas}}{n_{rz}}\right\rceil\right)+4d_k',
               r'0{,}80\cdot\max\left(2;\;\left\lceil\frac{[[n_pas]]}{[[n_ab]]}\right\rceil\right)+4\cdot[[d_k]]', fus['length'], M, 2,
               'Długość kadłuba (rzędy foteli co 0,80 m oraz nos i ogon)', check=lambda v: .8 * max(2, math.ceil(v.n_pas / v.n_ab)) + 4 * v.d_k,
               tolerance=.03)
    s.calc('lambda_k', r'\lambda_k', r'\frac{l_k}{d_k}', r'\frac{[[l_k]]}{[[d_k]]}', fus['fineness'], '', 2, 'Wydłużenie kadłuba',
           check=lambda v: v.l_k / v.d_k)

    s.section('p3', 'tail', 'Usterzenia — metoda cech objętościowych', SOURCES['B1'] + ', s. 1; Usterzenie_wymiary')
    s.given('l_H', 'l_H', ht['l_h'], M, 2, 'Ramię usterzenia poziomego: x_H − (x_N,ŚCA + 0,25 c̄), z pętli położenia skrzydła',
            'P3, wyważenie (dokładność pętli 0,015 m)')
    s.given('V_H', 'V_H', ht['vh_coeff'], '', 3, 'Cecha objętościowa usterzenia poziomego', 'Średnia z analizy trendów / założenie')
    s.calc('S_H', 'S_H', r'\frac{V_H\,S\,\bar c}{l_H}', r'\frac{[[V_H]]\cdot[[S]]\cdot[[mac]]}{[[l_H]]}', ht['S_h'], M2, 2,
           'Powierzchnia usterzenia poziomego', check=lambda v: v.V_H * v.S * v.mac / v.l_H)
    s.given('AR_H', r'\Lambda_H', ht['AR_h'], '', 2, 'Wydłużenie usterzenia poziomego', 'Założenie')
    s.calc('b_H', 'b_H', r'\sqrt{S_H\Lambda_H}', r'\sqrt{[[S_H]]\cdot[[AR_H]]}', ht['b_h'], M, 2, 'Rozpiętość usterzenia poziomego',
           check=lambda v: math.sqrt(v.S_H * v.AR_H))
    s.given('lambda_H', r'\lambda_H', .6, '', 2, 'Zbieżność usterzenia poziomego', 'Założenie')
    s.calc('c_rH', 'c_{0H}', r'\frac{2S_H}{b_H(1+\lambda_H)}', r'\frac{2\cdot[[S_H]]}{[[b_H]]\cdot(1+[[lambda_H]])}', ht['cr_h'], M, 3,
           'Cięciwa przykadłubowa usterzenia poziomego', check=lambda v: 2 * v.S_H / (v.b_H * (1 + v.lambda_H)), tolerance=.006 * ht['cr_h'] + .001)
    s.calc('mac_H', r'\bar c_H', r'\frac{2}{3}c_{0H}\frac{1+\lambda_H+\lambda_H^2}{1+\lambda_H}',
           r'\frac{2}{3}\cdot[[c_rH]]\cdot\frac{1+[[lambda_H]]+[[lambda_H]]^2}{1+[[lambda_H]]}', ht['mac_h'], M, 3,
           'Średnia cięciwa usterzenia poziomego', check=lambda v: 2 / 3 * v.c_rH * (1 + v.lambda_H + v.lambda_H ** 2) / (1 + v.lambda_H))
    s.given('l_V', 'l_V', vt['l_v'], M, 2, 'Ramię usterzenia pionowego z pętli położenia skrzydła', 'P3, wyważenie')
    s.given('V_V', 'V_V', vt['vv_coeff'], '', 4, 'Cecha objętościowa usterzenia pionowego', 'Średnia z analizy trendów / założenie')
    s.calc('S_V', 'S_V', r'\frac{V_V\,S\,b}{l_V}', r'\frac{[[V_V]]\cdot[[S]]\cdot[[b]]}{[[l_V]]}', vt['S_v'], M2, 2,
           'Powierzchnia usterzenia pionowego', check=lambda v: v.V_V * v.S * v.b / v.l_V)
    s.given('AR_V', r'\Lambda_V', vt['AR_v'], '', 2, 'Wydłużenie usterzenia pionowego', 'Założenie')
    s.calc('h_V', 'h_V', r'\sqrt{S_V\Lambda_V}', r'\sqrt{[[S_V]]\cdot[[AR_V]]}', vt['h_v'], M, 2, 'Wysokość usterzenia pionowego',
           check=lambda v: math.sqrt(v.S_V * v.AR_V))
    s.given('lambda_V', r'\lambda_V', .65, '', 2, 'Zbieżność usterzenia pionowego', 'Założenie')
    s.calc('c_rV', 'c_{0V}', r'\frac{2S_V}{h_V(1+\lambda_V)}', r'\frac{2\cdot[[S_V]]}{[[h_V]]\cdot(1+[[lambda_V]])}', vt['cr_v'], M, 3,
           'Cięciwa nasady usterzenia pionowego', check=lambda v: 2 * v.S_V / (v.h_V * (1 + v.lambda_V)), tolerance=.006 * vt['cr_v'] + .001)

    _p3_controls(s, r)
    _p3_balance(s, r)
    _p3_schrenk(s, r)
    _p3_wing_aero(s, r)


def _p3_controls(s, r):
    cs, geom = r['geometry']['control_surfaces'], r['geometry']
    flaps, ail = cs['flaps'], cs['ailerons']
    s.section('p3', 'controls', 'Podział krawędzi spływu: klapy i lotki', SOURCES['B2'] + ', s. 4; ' + SOURCES['D'] + ', rozdz. 8')
    s.calc('eta_k', r'\eta_k', r'\frac{d_k/2}{b/2}', r'\frac{[[d_k]]}{[[b]]}', cs['trailing_edge_partition']['fuselage_gap_pct'] / 100, '', 3,
           'Względna półszerokość kadłuba', check=lambda v: v.d_k / v.b, tolerance=.0006)
    if cs['is_flaperon']:
        s.given('eta_f_in', r'\eta_{f,1}', flaps['eta_in'], '', 3, 'Początek klapolotki', 'Układ klapolotek')
        s.given('eta_f_out', r'\eta_{f,2}', flaps['eta_out'], '', 3, 'Koniec klapolotki', 'Układ klapolotek')
    else:
        s.calc('eta_f_in', r'\eta_{f,1}', r'\max\left(\eta_k;\;0{,}05\right)', r'\max\left([[eta_k]];\;0{,}05\right)', flaps['eta_in'], '', 3,
               'Początek klapy (przy kadłubie)', check=lambda v: max(v.eta_k, .05), tolerance=.0006)
        s.given('bf_b_zal', r'(b_f/b)_{zał}', float(r['params'].get('flap_span_ratio', .6)), '', 2, 'Założona względna rozpiętość klap', 'Założenia projektu')
        s.calc('eta_f_out', r'\eta_{f,2}', r'\min\left(0{,}74;\;\max\left(\eta_{f,1}+0{,}15;\;\eta_{f,1}+(b_f/b)_{zał}\right)\right)',
               r'\min\left(0{,}74;\;\max\left([[eta_f_in]]+0{,}15;\;[[eta_f_in]]+[[bf_b_zal]]\right)\right)', flaps['eta_out'], '', 3,
               'Koniec klapy', check=lambda v: min(.74, max(v.eta_f_in + .15, v.eta_f_in + v.bf_b_zal)), tolerance=.0006)
    s.calc('bf_b', r'b_f/b', r'\eta_{f,2}-\eta_{f,1}', r'[[eta_f_out]]-[[eta_f_in]]', flaps['bf_over_b'], '', 3,
           'Względna rozpiętość klap (na półrozpiętości)', check=lambda v: v.eta_f_out - v.eta_f_in, tolerance=.0011)
    s.solve('S_f', 'S_f', r'S_f=2\int_{\eta_{f,1}b/2}^{\eta_{f,2}b/2}c(y)\,\mathrm{d}y', flaps['S_flapped_m2'], M2, 2,
            'Powierzchnia płata objęta klapami (całkowanie obrysu metodą Simpsona)', deps=['eta_f_in', 'eta_f_out', 'b', 'c_r'])
    s.calc('Sf_S', r'S_f/S', r'\frac{S_f}{S}', r'\frac{[[S_f]]}{[[S]]}', flaps['s_flapped_over_s'], '', 4, 'Udział powierzchni z klapami',
           check=lambda v: v.S_f / v.S, tolerance=.0015)
    if not cs['is_flaperon']:
        s.calc('eta_a_in', r'\eta_{a,1}', r'\min\left(0{,}85;\;\eta_{f,2}+0{,}015\right)', r'\min\left(0{,}85;\;[[eta_f_out]]+0{,}015\right)',
               ail['eta_in'], '', 3, 'Początek lotki (szczelina 1,5% za klapą)', check=lambda v: min(.85, v.eta_f_out + .015), tolerance=.0006)
        s.given('ba_b_zal', r'(b_a/b)_{zał}', float(r['params'].get('aileron_span_ratio', .28)), '', 2, 'Założona względna rozpiętość lotek', 'Założenia projektu')
        s.calc('eta_a_out', r'\eta_{a,2}', r'\min\left(0{,}97;\;\max\left(\eta_{a,1}+0{,}10;\;\eta_{a,1}+(b_a/b)_{zał}\right)\right)',
               r'\min\left(0{,}97;\;\max\left([[eta_a_in]]+0{,}10;\;[[eta_a_in]]+[[ba_b_zal]]\right)\right)', ail['eta_out'], '', 3,
               'Koniec lotki', check=lambda v: min(.97, max(v.eta_a_in + .1, v.eta_a_in + v.ba_b_zal)), tolerance=.0006)
    else:
        s.given('eta_a_in', r'\eta_{a,1}', ail['eta_in'], '', 3, 'Początek lotki (klapolotka)', 'Układ klapolotek')
        s.given('eta_a_out', r'\eta_{a,2}', ail['eta_out'], '', 3, 'Koniec lotki (klapolotka)', 'Układ klapolotek')
    s.calc('ba_b', r'b_a/b', r'\eta_{a,2}-\eta_{a,1}', r'[[eta_a_out]]-[[eta_a_in]]', ail['ba_over_b'], '', 3,
           'Względna rozpiętość lotek (na półrozpiętości)', check=lambda v: v.eta_a_out - v.eta_a_in, tolerance=.0011)
    s.given('ca_c', r'c_a/c', ail['ca_over_c'], '', 3, 'Względna cięciwa lotki', 'Średnia z analizy trendów / założenie')
    s.given('cf_c', r'c_f/c', flaps['cf_over_c'], '', 3, 'Względna cięciwa klapy', 'Założenia projektu')


def _p3_balance(s, r):
    p, mass, geom, bal = r['params'], r['mass'], r['geometry'], r['balance']
    bd, arms, wp = mass['breakdown'], bal['arms'], bal['wing_placement']
    s.section('p3', 'balance', 'Położenie skrzydła i środka masy', SOURCES['B3'] + ', wzór (3.1), pkt 7–8')
    s.table('comp_mass', 'Masy zespołów', r'm_i=u_i\,m_e', note='Udziały uᵢ zespołów w masie własnej — tabela mas.', deps=['m_e'])
    s.table('comp_arm', 'Ramiona mas', r'x_i=x_{N,\bar c}+k_i\,\bar c\quad\text{lub}\quad x_i=k_i\,l_k',
            note='Współczynniki kᵢ położeń zespołów — tabela mas.', deps=['mac', 'l_k'])
    s.given('M_kgr', r'M_{kadł}', wp['moment_fuselage_group'], r'\mathrm{kg\,m}', 1, 'Moment statyczny zespołów kadłubowych względem nosa', 'Tabela mas')
    s.given('M_sgr', r'M_{skrz}', wp['moment_wing_offset'], r'\mathrm{kg\,m}', 1, 'Moment zespołów skrzydłowych względem noska ŚCA', 'Tabela mas')
    s.given('m_sgr', r'm_{skrz}', wp['m_wing_group'], KG, 1, 'Masa zespołów związanych ze skrzydłem', 'Tabela mas')
    s.given('xcel', r'\bar x_{cel}', wp['target_oew_mac'], '', 2, 'Docelowe położenie ŚM samolotu pustego w ŚCA', SOURCES['B3'])
    s.calc('x_lemac0', r'x_{N,\bar c}^{(0)}', r'\frac{M_{kadł}+M_{skrz}-\bar x_{cel}\,\bar c\,m_e}{m_e-m_{skrz}}',
           r'\frac{[[M_kgr]]+[[M_sgr]]-[[xcel]]\cdot[[mac]]\cdot[[m_e]]}{[[m_e]]-[[m_sgr]]}', wp['x_lemac_raw'], M, 3,
           'Wstępne położenie noska ŚCA (wyważenie samolotu pustego)',
           check=lambda v: (v.M_kgr + v.M_sgr - v.xcel * v.mac * v.m_e) / max(1, v.m_e - v.m_sgr))
    if abs(bal['x_lemac_m'] - wp['x_lemac_raw']) > 1e-3:
        s.given('x_LEc', r'x_{N,\bar c}', bal['x_lemac_m'], M, 3,
                'Położenie noska ŚCA po korekcie (granice 0,25–0,56 lₖ i kryterium BIPOL_3 pkt 8)', SOURCES['B3'] + ', pkt 8')
    else:
        s.calc('x_LEc', r'x_{N,\bar c}', r'x_{N,\bar c}^{(0)}', r'[[x_lemac0]]', bal['x_lemac_m'], M, 3, 'Położenie noska ŚCA',
               check=lambda v: v.x_lemac0)
    mtow = next(st for st in bal['loading_states'] if st['key'] == 'mtow')
    parts = [('m_fuselage', 'fuselage'), ('m_wing', 'wing'), ('m_tail', 'tail'), ('m_propulsion', 'propulsion'),
             ('m_gear', 'gear'), ('m_systems', 'systems')]
    moment = sum(bd[m] * arms[a] for m, a in parts)
    s.calc('M_e', r'M_e', r'\sum_i m_i x_i', '+'.join(rf'{tex_value(bd[m], 1)}\cdot{tex_value(arms[a], 2)}' for m, a in parts if bd[m]),
           moment, r'\mathrm{kg\,m}', 1, 'Moment statyczny masy własnej względem nosa kadłuba', deps=['x_LEc', 'm_e'],
           check=lambda v, m=moment: m)
    s.given('x_zal', r'x_{zał}', arms['crew'], M, 2, 'Ramię załogi', 'Tabela mas')
    s.given('x_lad', r'x_{ład}', arms['payload_equivalent'], M, 2, 'Ramię zastępcze ładunku (pasażerowie i bagaż)', 'Tabela mas')
    s.given('x_f', r'x_f', arms['fuel'], M, 2, 'Ramię paliwa', 'Tabela mas')
    s.calc('x_cg', r'x_{SM}', r'\frac{M_e+m_{zał}x_{zał}+m_{ład}x_{ład}+m_fx_f}{m_e+m_{zał}+m_{ład}+m_f}',
           r'\frac{[[M_e]]+[[m_zal]]\cdot[[x_zal]]+[[m_lad]]\cdot[[x_lad]]+[[m_f]]\cdot[[x_f]]}{[[m_e]]+[[m_zal]]+[[m_lad]]+[[m_f]]}'
           if 'm_f' in s.entries else
           r'\frac{[[M_e]]+[[m_zal]]\cdot[[x_zal]]+[[m_lad]]\cdot[[x_lad]]}{[[m_e]]+[[m_zal]]+[[m_lad]]}',
           mtow['xcg_m'], M, 3, 'Położenie środka masy przy masie startowej (MTOW)', SOURCES['B3'] + ', wzór (3.1)',
           check=lambda v: (v.M_e + v.m_zal * v.x_zal + v.m_lad * v.x_lad + getattr(v, 'm_f', 0) * v.x_f)
           / (v.m_e + v.m_zal + v.m_lad + getattr(v, 'm_f', 0)), tolerance=.002)
    s.calc('xcg_pct', r'\bar x_{SM}', r'100\,\frac{x_{SM}-x_{N,\bar c}}{\bar c}', r'100\cdot\frac{[[x_cg]]-[[x_LEc]]}{[[mac]]}',
           mtow['xcg_mac_pct'], PCT, 1, 'Położenie środka masy w % ŚCA (MTOW)', check=lambda v: 100 * (v.x_cg - v.x_LEc) / v.mac, tolerance=.11)
    s.table('cg_states', 'Stany załadowania', r'x_{SM}=\frac{\sum_i m_ix_i}{\sum_i m_i},\qquad \bar x_{SM}=\frac{x_{SM}-x_{N,\bar c}}{\bar c}',
            note='Pozostałe stany załadowania — tabela stanów.', source=SOURCES['B3'], deps=['x_LEc', 'mac'])
    s.given('xcg_fwd', r'\bar x_{SM,p}', bal['cg_range']['forward_pct'], PCT, 1, 'Przednie położenie ŚM w locie', 'Tabela stanów załadowania')
    s.given('xcg_aft', r'\bar x_{SM,t}', bal['cg_range']['aft_pct'], PCT, 1, 'Tylne położenie ŚM w locie', 'Tabela stanów załadowania')

    np_ = bal['neutral_point']
    t = np_['terms']
    s.section('p3', 'neutral', 'Punkt neutralny i zapas stateczności', SOURCES['ML'] + ', P6; Munk–Multhopp')
    s.calc('a_wNP', r'a_w', r'\frac{2\pi\Lambda}{\Lambda+2}', r'\frac{2\pi\cdot[[AR]]}{[[AR]]+2}', t['a_w'], RAD, 3,
           'Gradient siły nośnej płata (do punktu neutralnego)', check=lambda v: 2 * math.pi * v.AR / (v.AR + 2))
    s.calc('a_HNP', r'a_H', r'\frac{2\pi\Lambda_H}{\Lambda_H+2}', r'\frac{2\pi\cdot[[AR_H]]}{[[AR_H]]+2}', t['a_h'], RAD, 3,
           'Gradient siły nośnej usterzenia poziomego', check=lambda v: 2 * math.pi * v.AR_H / (v.AR_H + 2))
    s.calc('de_da', r'\frac{\mathrm d\varepsilon}{\mathrm d\alpha}', r'\min\left(0{,}55;\;\frac{2a_w}{\pi\Lambda}\right)',
           r'\min\left(0{,}55;\;\frac{2\cdot[[a_wNP]]}{\pi\cdot[[AR]]}\right)', t['de_da'], '', 4, 'Gradient odchylenia strug za płatem',
           check=lambda v: min(.55, 2 * v.a_wNP / (math.pi * v.AR)))
    s.calc('dx_k', r'\Delta\bar x_k', r'\min\left(0{,}11;\;\max\left(0{,}055;\;0{,}35\,\frac{d_k^2 l_k}{S\,\bar c\,a_w}\right)\right)',
           r'\min\left(0{,}11;\;\max\left(0{,}055;\;0{,}35\cdot\frac{[[d_k]]^2\cdot[[l_k]]}{[[S]]\cdot[[mac]]\cdot[[a_wNP]]}\right)\right)', t['delta_xac_fus'], '', 4,
           'Przesunięcie środka aerodynamicznego przez kadłub', check=lambda v: min(.11, max(.055, .35 * v.d_k ** 2 * v.l_k / (v.S * v.mac * v.a_wNP))))
    s.given('dx_n', r'\Delta\bar x_n', t['delta_xac_prop'], '', 3, 'Przesunięcie od zespołu napędowego (śmigło, gondole)', 'Założenie wg położenia napędu')
    s.calc('x_ac', r'\bar x_{SA}', r'0{,}25-\Delta\bar x_k-\Delta\bar x_n', r'0{,}25-[[dx_k]]-[[dx_n]]', t['x_ac_wbn_pct'] / 100, '', 4,
           'Środek aerodynamiczny układu płat–kadłub–gondole', check=lambda v: .25 - v.dx_k - v.dx_n)
    s.calc('x_H', 'x_H', r'0{,}90\,l_k', r'0{,}90\cdot[[l_k]]', t['x_ac_h'], M, 3, 'Położenie środka aerodynamicznego usterzenia poziomego',
           check=lambda v: .9 * v.l_k, tolerance=.006)
    s.calc('l_H_rz', r'l_{H,rz}', r'x_H-\left(x_{N,\bar c}+0{,}25\,\bar c\right)', r'[[x_H]]-\left([[x_LEc]]+0{,}25\cdot[[mac]]\right)', t['l_h'], M, 3,
           'Rzeczywiste ramię usterzenia poziomego', check=lambda v: max(.1, v.x_H - (v.x_LEc + .25 * v.mac)), tolerance=.002)
    s.calc('V_H_rz', r'V_{H,rz}', r'\frac{S_H\,l_{H,rz}}{S\,\bar c}', r'\frac{[[S_H]]\cdot[[l_H_rz]]}{[[S]]\cdot[[mac]]}', t['v_h'], '', 4,
           'Rzeczywista cecha objętościowa usterzenia poziomego', check=lambda v: v.S_H * v.l_H_rz / (v.S * v.mac))
    s.given('eta_H', r'\eta_H', t['eta_h'], '', 2, 'Współczynnik spiętrzenia i interferencji na usterzeniu', 'Założenie')
    s.calc('dx_NH', r'\Delta\bar x_{N,H}', r'\eta_H V_{H,rz}\frac{a_H}{a_w}\left(1-\frac{\mathrm d\varepsilon}{\mathrm d\alpha}\right)',
           r'[[eta_H]]\cdot[[V_H_rz]]\cdot\frac{[[a_HNP]]}{[[a_wNP]]}\cdot\left(1-[[de_da]]\right)', t['delta_xn_tail_pct'] / 100, '', 4,
           'Udział usterzenia poziomego w położeniu punktu neutralnego', check=lambda v: v.eta_H * v.V_H_rz * v.a_HNP / v.a_wNP * (1 - v.de_da))
    s.calc('x_N', r'\bar x_N', r'100\left(\bar x_{SA}+\Delta\bar x_{N,H}\right)', r'100\cdot\left([[x_ac]]+[[dx_NH]]\right)', np_['x_n_mac_pct'], PCT, 1,
           'Punkt neutralny w % ŚCA', check=lambda v: 100 * (v.x_ac + v.dx_NH), tolerance=.051)
    s.calc('Kn_aft', r'K_{n,t}', r'\bar x_N-\bar x_{SM,t}', r'[[x_N]]-[[xcg_aft]]', bal['stability']['static_margin_aft_pct'], PCT, 1,
           'Zapas stateczności statycznej przy tylnym położeniu ŚM (kryterium ≥ 5%)', check=lambda v: v.x_N - v.xcg_aft, tolerance=.051)
    s.calc('Kn_fwd', r'K_{n,p}', r'\bar x_N-\bar x_{SM,p}', r'[[x_N]]-[[xcg_fwd]]', bal['stability']['static_margin_forward_pct'], PCT, 1,
           'Zapas stateczności przy przednim położeniu ŚM', check=lambda v: v.x_N - v.xcg_fwd, tolerance=.051)

    inertia = r['bipol_projects']['p3']['inertia_moments']
    rows = r['bipol_projects']['p3']['table_3_1_components']
    s.section('p3', 'inertia', 'Momenty bezwładności (masy skupione zespołów)', SOURCES['B3'] + ', wzory (2.3)–(2.4)')
    zcg = inertia['zcg_m']
    s.calc('z_cg', r'z_{SM}', r'\frac{\sum_i m_iz_i}{\sum_i m_i}', '', zcg, M, 3, 'Wysokość środka masy (suma po wierszach tabeli mas)',
           deps=['x_cg'], check=lambda v: sum(q['mass_kg'] * q['z_m'] for q in rows) / sum(q['mass_kg'] for q in rows))
    xcg = next(st for st in r['balance']['loading_states'] if st['key'] == 'mtow')['xcg_m']
    sums = dict(jx=sum(q['mass_kg'] * (q['y_rms_m'] ** 2 + (q['z_m'] - zcg) ** 2) for q in rows),
                jy=sum(q['mass_kg'] * ((q['x_m'] - xcg) ** 2 + (q['z_m'] - zcg) ** 2) for q in rows),
                jz=sum(q['mass_kg'] * ((q['x_m'] - xcg) ** 2 + q['y_rms_m'] ** 2) for q in rows),
                jxz=sum(q['mass_kg'] * (q['x_m'] - xcg) * (q['z_m'] - zcg) for q in rows))
    for key, sym, formula, value, label in (
            ('J_x', 'J_x', r'\sum_i m_i\left(y_i^2+(z_i-z_{SM})^2\right)', inertia['jx_cg_kgm2'], 'Moment bezwładności względem osi podłużnej'),
            ('J_y', 'J_y', r'\sum_i m_i\left((x_i-x_{SM})^2+(z_i-z_{SM})^2\right)', inertia['jy_cg_kgm2'], 'Moment bezwładności względem osi poprzecznej'),
            ('J_z', 'J_z', r'\sum_i m_i\left((x_i-x_{SM})^2+y_i^2\right)', inertia['jz_cg_kgm2'], 'Moment bezwładności względem osi pionowej'),
            ('J_xz', 'J_{xz}', r'\sum_i m_i\,(x_i-x_{SM})(z_i-z_{SM})', inertia['jxz_cg_kgm2'], 'Moment dewiacji')):
        s.calc(key, sym, formula, '', value, KGM2, 1, label + ' (suma po wierszach tabeli mas)', deps=['z_cg', 'x_cg'],
               check=lambda v, val=sums[key.lower().replace('_', '')]: val, tolerance=.06)


def _p3_schrenk(s, r):
    geom, aero = r['geometry'], r['aerodynamics']
    pin = geom['schrenk_Pinpoint']
    summary = r['bipol_projects']['p3']['schrenk_summary']
    s.section('p3', 'schrenk', 'Rozkład obciążenia wg Schrenka (Cz = 1)', SOURCES['D'] + ', rozdz. 7')
    s.calc('c_e0', r'c_{e,0}', r'\frac{4S}{\pi b}', r'\frac{4\cdot[[S]]}{\pi\cdot[[b]]}', 4 * geom['wing']['S'] / (math.pi * geom['wing']['b']), M, 3,
           'Cięciwa eliptyczna w płaszczyźnie symetrii', check=lambda v: 4 * v.S / (math.pi * v.b))
    s.table('schrenk_rows', 'Rozkład Schrenka', r'c_e(y)=c_{e,0}\sqrt{1-\left(\frac{2y}{b}\right)^2},\qquad c_S(y)=\frac{c(y)+c_e(y)}{2},'
            r'\qquad \frac{c_z(y)}{C_z}=\frac{1}{2}\left(1+\frac{c_e(y)}{c(y)}\right)', note='Wartości w 26 przekrojach półrozpiętości — tabela Schrenka.',
            deps=['c_e0'])
    s.given('cz1_max', r'\left(c_z/C_z\right)_{max}', pin['max_cz1'], '', 3, f"Największe lokalne c_z przy y = {pin['stall_y_m']:.2f} m".replace('.', ','),
            'Tabela Schrenka')
    s.given('Cz_max', r'C_{z\,max}', float(aero['cz_max_clean']), '', 2, 'Maksymalny współczynnik siły nośnej w konfiguracji gładkiej', 'Założenia projektu')
    s.calc('Cz_max_wing', r'C_{z\,max,p}', r'\frac{1{,}06\,C_{z\,max}}{\max\left(1;\;(c_z/C_z)_{max}\right)}',
           r'\frac{1{,}06\cdot[[Cz_max]]}{\max\left(1;\;[[cz1_max]]\right)}', summary['cz_max_wing_est'], '', 3,
           'Szacunkowy maksymalny współczynnik siły nośnej płata', check=lambda v: 1.06 * v.Cz_max / max(1, v.cz1_max), tolerance=.0011)


def _p3_wing_aero(s, r):
    p2 = r['aerodynamics']['paturski_p2']
    t = p2['terms']
    s.section('p3', 'wing_aero', 'Charakterystyki aerodynamiczne płata', SOURCES['ML'] + ', P2, wzory (2.6)–(2.27)')
    s.calc('V_S1w', r'V_{S1}', r'\sqrt{\frac{2m_0g}{\rho_0SC_{z\,max}}}', r'\sqrt{\frac{2\cdot[[m0]]\cdot[[g]]}{[[rho0]]\cdot[[S]]\cdot[[Cz_max]]}}',
           t['v_s1_ms'], MS, 2, 'Prędkość przeciągnięcia płata', SOURCES['ML'] + ', wzór (2.6)',
           check=lambda v: math.sqrt(2 * v.m0 * v.g / (v.rho0 * v.S * v.Cz_max)))
    s.given('nu0', r'\nu_0', t['nu0'], r'\mathrm{m^2/s}', 4, 'Lepkość kinematyczna powietrza przy ziemi', 'ISA')
    s.calc('Re_1', 'Re_1', r'\frac{V_{S1}\,\bar c}{\nu_0}', r'\frac{[[V_S1w]]\cdot[[mac]]}{[[nu0]]}', t['re_1'], '', 0,
           'Liczba Reynoldsa przy przeciągnięciu', SOURCES['ML'] + ', wzór (2.6a)', check=lambda v: v.V_S1w * v.mac / v.nu0,
           tolerance=.003 * t['re_1'])
    s.given('Cx_min1', r"C'_{x\,min,1}", p2['cx_min_1_tunnel'], '', 5, 'Minimalny opór profilu w tunelu (Re = 10⁷)', SOURCES['ML'] + ', tab. 2.1')
    s.calc('Cx_min2', r"C'_{x\,min,2}", r"C'_{x\,min,1}\left(\frac{Re_1}{10^{7}}\right)^{0{,}11}", r'[[Cx_min1]]\cdot\left(\frac{[[Re_1]]}{10^{7}}\right)^{0{,}11}',
           p2['cx_min_2_corrected'], '', 5, 'Opór profilu przeliczony na liczbę Reynoldsa płata', SOURCES['ML'] + ', wzory (2.7)–(2.9)',
           check=lambda v: v.Cx_min1 * (v.Re_1 / 1e7) ** .11)
    s.given('a_inf', r'a_\infty', p2['a_inf_rad'], RAD, 3, 'Gradient siły nośnej profilu', SOURCES['ML'] + ', tab. 2.1')
    if r['geometry']['wing']['wing_planform'] == 'elliptical' and abs(t['sweep_deg']) < 1e-9:
        s.given('tau_G', r'\tau', 0.0, '', 4, 'Poprawka Glauerta (płat eliptyczny bez skosu)', SOURCES['ML'])
        s.given('delta_G', r'\delta', 0.0, '', 4, 'Poprawka Glauerta (płat eliptyczny bez skosu)', SOURCES['ML'])
    else:
        s.calc('u_G', 'u', r'\frac{\Lambda}{a_\infty}', r'\frac{[[AR]]}{[[a_inf]]}', t['u_ratio'], '', 4, 'Parametr wykresów Glauerta',
               check=lambda v: v.AR / v.a_inf)
        s.calc('tau_1', r'\tau_1', r'0{,}023u^3-0{,}103u^2+0{,}25u', r'0{,}023\cdot[[u_G]]^3-0{,}103\cdot[[u_G]]^2+0{,}25\cdot[[u_G]]', t['tau_1'], '', 5,
               'Aproksymacja wykresu τ₁(u)', SOURCES['ML'] + ', wzory (2.14)–(2.16)',
               check=lambda v: .023 * v.u_G ** 3 - .103 * v.u_G ** 2 + .25 * v.u_G)
        s.calc('tau_2', r'\tau_2', r'-0{,}18\lambda^5+1{,}52\lambda^4-3{,}51\lambda^3+3{,}50\lambda^2-1{,}33\lambda+0{,}17',
               r'-0{,}18\cdot[[lambda_w]]^5+1{,}52\cdot[[lambda_w]]^4-3{,}51\cdot[[lambda_w]]^3+3{,}50\cdot[[lambda_w]]^2-1{,}33\cdot[[lambda_w]]+0{,}17',
               t['tau_2'], '', 5, 'Aproksymacja wykresu τ₂(λ)', SOURCES['ML'] + ', wzór (2.17)',
               check=lambda v: -.18 * v.lambda_w ** 5 + 1.52 * v.lambda_w ** 4 - 3.51 * v.lambda_w ** 3 + 3.5 * v.lambda_w ** 2 - 1.33 * v.lambda_w + .17,
               tolerance=2e-4)
        s.calc('tau_G', r'\tau', r'\frac{\tau_1\tau_2}{0{,}17}', r'\frac{[[tau_1]]\cdot[[tau_2]]}{0{,}17}', p2['tau_glauert'], '', 4,
               'Poprawka Glauerta do kąta indukowanego', SOURCES['ML'] + ', wzór (2.18)', check=lambda v: max(0, v.tau_1 * v.tau_2 / .17), tolerance=2e-4)
        s.calc('delta_1', r'\delta_1', r'\max\left(0{,}002;\;0{,}0537u-0{,}005\right)', r'\max\left(0{,}002;\;0{,}0537\cdot[[u_G]]-0{,}005\right)',
               t['delta_1'], '', 5, 'Aproksymacja wykresu δ₁(u)', check=lambda v: max(.002, .0537 * v.u_G - .005))
        s.calc('delta_2', r'\delta_2', r'-0{,}43\lambda^5+1{,}83\lambda^4-3{,}06\lambda^3+2{,}56\lambda^2-\lambda+0{,}148',
               r'-0{,}43\cdot[[lambda_w]]^5+1{,}83\cdot[[lambda_w]]^4-3{,}06\cdot[[lambda_w]]^3+2{,}56\cdot[[lambda_w]]^2-[[lambda_w]]+0{,}148',
               t['delta_2'], '', 5, 'Aproksymacja wykresu δ₂(λ)',
               check=lambda v: -.43 * v.lambda_w ** 5 + 1.83 * v.lambda_w ** 4 - 3.06 * v.lambda_w ** 3 + 2.56 * v.lambda_w ** 2 - v.lambda_w + .148,
               tolerance=2e-4)
        s.given('delta_3', r'\delta_3', t['delta_3'], '', 5, 'Poprawka na skos δ₃(Λ, χ) — dla χ = 0 równa 1', SOURCES['ML'] + ', wzór (2.19)')
        s.calc('delta_G', r'\delta', r'\frac{\delta_1\delta_2\delta_3}{0{,}048}', r'\frac{[[delta_1]]\cdot[[delta_2]]\cdot[[delta_3]]}{0{,}048}',
               p2['delta_glauert'], '', 4, 'Poprawka Glauerta do oporu indukowanego', SOURCES['ML'] + ', wzór (2.20)',
               check=lambda v: max(0, v.delta_1 * v.delta_2 * v.delta_3 / .048), tolerance=2e-4)
    s.calc('dCx_tech', r'\Delta C_{x,tech}', r"0{,}15\,C'_{x\,min,2}", r'0{,}15\cdot[[Cx_min2]]', p2['delta_cx_tech'], '', 5,
           'Opór techniczny (nierówności, szczeliny)', SOURCES['ML'] + ', s. II-6', check=lambda v: .15 * v.Cx_min2, tolerance=6e-6)
    s.calc('a_w', 'a', r'\frac{a_\infty}{1+\frac{a_\infty}{\pi\Lambda}(1+\tau)}', r'\frac{[[a_inf]]}{1+\frac{[[a_inf]]}{\pi\cdot[[AR]]}\cdot(1+[[tau_G]])}',
           p2['a_wing_paturski_rad'], RAD, 3, 'Gradient siły nośnej płata', SOURCES['ML'] + ', wzór (2.27)',
           check=lambda v: v.a_inf / (1 + v.a_inf / (math.pi * v.AR) * (1 + v.tau_G)))
    s.calc('a_w_deg', 'a', r'a\,\frac{\pi}{180}', r'[[a_w]]\cdot\frac{\pi}{180}', p2['a_wing_paturski_deg'], r'\mathrm{1/^{\circ}}', 4,
           'Gradient siły nośnej płata na stopień', check=lambda v: v.a_w * math.pi / 180, tolerance=6e-5)
    s.table('wing_rows', 'Charakterystyki płata', r'\alpha=\alpha_\infty+\frac{C_z}{\pi\Lambda}(1+\tau),\quad'
            r"C_x=C'_{x\infty}+\Delta C_{x,tech}+\frac{C_z^2}{\pi\Lambda}(1+\delta),\quad C_m=C_{m,SA}-\bar x_{SA}C_z",
            note='Wartości dla kolejnych Cz — tabela charakterystyk płata.', source=SOURCES['ML'] + ', tab. 2.2',
            deps=['tau_G', 'delta_G', 'dCx_tech', 'AR'])


# =============================================================================================
# P4 — charakterystyki aerodynamiczne samolotu
# =============================================================================================
def _p4(s, r):
    aero, geom = r['aerodynamics'], r['geometry']
    p3 = aero['paturski_p3']
    t = p3['fuselage']['terms']
    s.section('p4', 'parasite', 'Opór szkodliwy zespołów nienośnych', SOURCES['ML'] + ', P3, wzory (3.1)–(3.6), tab. 3.1')
    s.calc('S_kc', 'S_k', r'\frac{\pi d_k^2}{4}', r'\frac{\pi\cdot[[d_k]]^2}{4}', t['s_k'], M2, 3, 'Pole przekroju czołowego kadłuba',
           check=lambda v: math.pi * v.d_k ** 2 / 4)
    s.calc('S_ck', 'S_{ck}', r'2{,}85\,l_k\sqrt{S_k}', r'2{,}85\cdot[[l_k]]\cdot\sqrt{[[S_kc]]}', t['s_ck'], M2, 2, 'Powierzchnia omywana kadłuba',
           SOURCES['ML'] + ', wzór (3.1)', check=lambda v: 2.85 * v.l_k * math.sqrt(v.S_kc))
    s.calc('Re_k', 'Re_k', r'\frac{\rho_H V_{cr} l_k}{\mu_H}', r'\frac{[[rho_cr]]\cdot[[V_cr]]\cdot[[l_k]]}{[[mu_cr]]}', t['re_k'], '', 0,
           'Liczba Reynoldsa kadłuba', check=lambda v: v.rho_cr * max(25, v.V_cr) * v.l_k / v.mu_cr, tolerance=.002 * t['re_k'])
    s.calc('Cf_k', 'C_f', r'\frac{0{,}455}{\left(\log Re_k\right)^{2{,}58}\left(1+0{,}144M^2\right)^{0{,}65}}',
           r'\frac{0{,}455}{\left(\log[[Re_k]]\right)^{2{,}58}\cdot\left(1+0{,}144\cdot[[M_cr]]^2\right)^{0{,}65}}', t['cf_k'], '', 5,
           'Współczynnik tarcia płyty turbulentnej', check=lambda v: .455 / (math.log10(v.Re_k) ** 2.58 * (1 + .144 * v.M_cr ** 2) ** .65))
    s.calc('eta_kf', r'\eta_k', r'1+\frac{2{,}2}{\lambda_k^{1{,}5}}+\frac{3{,}8}{\lambda_k^{3}}', r'1+\frac{2{,}2}{[[lambda_k]]^{1{,}5}}+\frac{3{,}8}{[[lambda_k]]^{3}}',
           t['eta_k'], '', 4, 'Współczynnik kształtu kadłuba', check=lambda v: 1 + 2.2 / max(3, v.lambda_k) ** 1.5 + 3.8 / max(3, v.lambda_k) ** 3,
           tolerance=2e-3)
    s.calc('eta_M', r'\eta_M', r'1+0{,}18M^2', r'1+0{,}18\cdot[[M_cr]]^2', t['eta_ma'], '', 4, 'Poprawka ściśliwości', check=lambda v: 1 + .18 * v.M_cr ** 2)
    s.calc('Cx_k', r'C_{x,k}', r'\min\left(0{,}15;\;\max\left(0{,}08;\;C_f\,\eta_k\,\eta_M\,\frac{S_{ck}}{S_k}\right)\right)',
           r'\min\left(0{,}15;\;\max\left(0{,}08;\;[[Cf_k]]\cdot[[eta_kf]]\cdot[[eta_M]]\cdot\frac{[[S_ck]]}{[[S_kc]]}\right)\right)', t['cx_k_frontal'], '', 4,
           'Współczynnik oporu kadłuba odniesiony do przekroju czołowego', SOURCES['ML'] + ', wzór (3.1)',
           check=lambda v: max(.08, min(.15, v.Cf_k * v.eta_kf * v.eta_M * v.S_ck / v.S_kc)), tolerance=2e-3)
    if abs(t['cx_k_eff'] - t['cx_k_frontal']) > 1e-9:
        s.given('Cx_k_eff', r'C_{x,k,ef}', t['cx_k_eff'], '', 4, 'Opór kadłuba z dolnym progiem statystyki Tabeli C (kabina, okucia)', SOURCES['ML'] + ', tab. C')
    s.calc('kappa_H', r"\kappa'_H", r'\frac{S_H\,l_H}{S\,\bar c}\left(\frac{V_H}{V}\right)^2', r'\frac{[[S_H]]\cdot[[l_H]]}{[[S]]\cdot[[mac]]}\cdot' + tex_value(t['vh_vinf_sq'], 2),
           t['kappa_h_prime'], '', 4, 'Względna cecha objętościowa usterzenia z hamowaniem strug', SOURCES['ML'] + ', wzory (3.2)–(3.5)',
           check=lambda v: v.S_H * v.l_H / (v.S * v.mac) * t['vh_vinf_sq'])
    s.calc('Lambda_eH', r'\Lambda_{eH}', r'\Lambda_H e_H', r'[[AR_H]]\cdot' + tex_value(t['e_h'], 2), t['lambda_eh'], '', 2,
           'Wydłużenie efektywne usterzenia poziomego', check=lambda v: v.AR_H * t['e_h'])
    s.table('parasite_rows', 'Opory szkodliwe zespołów (tab. 3.1)', r'C_{x,szk,min}=\frac{\sum_j C_{x,j}S_j}{S}',
            note='Iloczyny Cₓⱼ·Sⱼ — tabela oporu zespołów.', deps=['S'])
    sailplane = r['params'].get('aircraft_type') in ('glider', 'motoglider')
    s.given('sum_CxS', r'\sum_j C_{x,j}S_j', t['sum_cxj_sj'], M2, 4, 'Suma iloczynów z tabeli oporów zespołów', 'Tabela 3.1')
    low = '0{,}002' if sailplane else '0{,}008'
    s.calc('Cx_szk', r'C_{x,szk,min}', r'\min\left(0{,}042;\;\max\left(' + low + r';\;\frac{\sum_j C_{x,j}S_j}{S}\right)\right)',
           r'\min\left(0{,}042;\;\max\left(' + low + r';\;\frac{[[sum_CxS]]}{[[S]]}\right)\right)', p3['cx_szk_min'], '', 5, 'Minimalny opór szkodliwy zespołów',
           check=lambda v: max(.002 if sailplane else .008, min(.042, v.sum_CxS / v.S)), tolerance=2e-5)

    s.section('p4', 'trim', 'Biegunowa samolotu wyważonego (tabela 2.2)', SOURCES['ML'] + ', tab. 2.2')
    tm = p3['trim_model']
    s.given('x_sc_trim', r'\bar x', .28, '', 2, 'Położenie ŚM przyjęte do tabeli biegunowej', SOURCES['ML'])
    s.given('k_int', r'k_{int}', tm['k_interf'], '', 2, 'Poprawka interferencji', SOURCES['ML'])
    s.given('zeta', r'\zeta', tm['zeta_szk'], '', 1, 'Parametr przyrostu oporu szkodliwego z Cz', SOURCES['ML'])
    s.given('Cx_H0', r'C_{x,H0}', tm['cx_h0'], '', 4, 'Opór minimalny usterzenia poziomego (profil + szczeliny)', SOURCES['ML'] + ', wzór (3.6)')
    s.table('trim_rows', 'Kolejne wiersze tabeli 2.2',
            r"\alpha=\alpha_0+\frac{C_{z\infty}}{a_\infty}+\frac{C_{z\infty}(1+\tau)}{\pi\Lambda},\quad "
            r"C'_{x,p}=C'_{x\infty}+\Delta C_{x,tech}+\frac{C_{z\infty}^2(1+\delta)}{\pi\Lambda},\quad "
            r"C_{z,H}=\frac{C_{m,SA}+(\bar x-\bar x_{SA})C_{z\infty}}{\kappa'_H},\quad "
            r"C_{x,H}=C_{x,H0}+\frac{C_{z,H}^2}{\pi\Lambda_{eH}},\quad "
            r"C_x=\left(C'_{x,p}+C_{x,szk,min}\left(1+\frac{|C_{z\infty}|}{\zeta}\right)+\frac{S_H}{S}C_{x,H}\right)(1+k_{int}),\quad "
            r"C_z=C_{z\infty}+\frac{S_H}{S}C_{z,H}",
            note='Wiersze tabeli — tabela biegunowej samolotu.', deps=['tau_G', 'delta_G', 'dCx_tech', 'kappa_H', 'Lambda_eH', 'Cx_szk', 'k_int', 'zeta', 'Cx_H0', 'x_sc_trim'])

    fit = p3['analytical_polar_fit']
    s.section('p4', 'fit', 'Biegunowa analityczna z tabeli 2.2 (metoda najmniejszych kwadratów)', SOURCES['ML'] + ', wzór (3.11)')
    s.given('n_fit', 'n', fit['n_fit'], '', 0, f"Liczba punktów 0 ≤ Cz∞ ≤ 0,85 Cz,max", 'Tabela 2.2')
    s.given('Sx', r'\sum x', fit['sum_x'], '', 5, 'Suma x = Cz²', 'Tabela 2.2')
    s.given('Sy', r'\sum y', fit['sum_y'], '', 5, 'Suma y = Cx', 'Tabela 2.2')
    s.given('Sxx', r'\sum x^2', fit['sum_xx'], '', 5, 'Suma x²', 'Tabela 2.2')
    s.given('Sxy', r'\sum xy', fit['sum_xy'], '', 6, 'Suma x·y', 'Tabela 2.2')
    s.calc('k', 'k', r'\frac{n\sum xy-\sum x\sum y}{n\sum x^2-\left(\sum x\right)^2}',
           r'\frac{[[n_fit]]\cdot[[Sxy]]-[[Sx]]\cdot[[Sy]]}{[[n_fit]]\cdot[[Sxx]]-[[Sx]]^2}', aero['k_clean'], '', 5,
           'Współczynnik oporu indukowanego samolotu', check=lambda v: (v.n_fit * v.Sxy - v.Sx * v.Sy) / (v.n_fit * v.Sxx - v.Sx ** 2), tolerance=2e-5)
    s.calc('Cx0', 'C_{x0}', r'\frac{\sum y-k\sum x}{n}', r'\frac{[[Sy]]-[[k]]\cdot[[Sx]]}{[[n_fit]]}', aero['cx0_clean'], '', 4,
           'Opór zerowy samolotu', check=lambda v: (v.Sy - fit['slope_raw'] * v.Sx) / v.n_fit, tolerance=6e-5)
    s.calc('Lambda_e', r'\Lambda_e', r'\frac{1}{\pi k}', r'\frac{1}{\pi\cdot[[k]]}', aero['lambda_e'], '', 2, 'Wydłużenie efektywne',
           check=lambda v: 1 / (math.pi * v.k), tolerance=.03)
    s.calc('e', 'e', r'\frac{\Lambda_e}{\Lambda}', r'\frac{[[Lambda_e]]}{[[AR]]}', aero['oswald_e'], '', 3, 'Współczynnik Oswalda samolotu',
           check=lambda v: v.Lambda_e / v.AR, tolerance=.002)
    s.table('polar', 'Biegunowa analityczna samolotu', r'C_x=C_{x0}+k\,C_z^2,\qquad K=\frac{C_z}{C_x}', deps=['Cx0', 'k'])

    s.section('p4', 'optimum', 'Punkty charakterystyczne biegunowej', SOURCES['B1W'] + ', wzory (6)–(8), (28)')
    s.calc('Cz_opt', r'C_{z,opt}', r'\sqrt{\frac{C_{x0}}{k}}', r'\sqrt{\frac{[[Cx0]]}{[[k]]}}', aero['cz_opt'], '', 3, 'Cz największej doskonałości',
           check=lambda v: math.sqrt(v.Cx0 / v.k))
    s.calc('Cx_opt', r'C_{x,opt}', r'2C_{x0}', r'2\cdot[[Cx0]]', aero['cx_opt'], '', 4, 'Cx największej doskonałości', check=lambda v: 2 * v.Cx0)
    s.calc('Kmax', r'K_{max}', r'\frac{C_{z,opt}}{C_{x,opt}}=\frac{1}{2\sqrt{C_{x0}k}}', r'\frac{[[Cz_opt]]}{[[Cx_opt]]}', aero['k_max'], '', 2,
           'Maksymalna doskonałość aerodynamiczna', check=lambda v: 1 / (2 * math.sqrt(v.Cx0 * v.k)))
    s.calc('Cz_ek', r'C_{z,ek}', r'\sqrt{\frac{3C_{x0}}{k}}', r'\sqrt{\frac{3\cdot[[Cx0]]}{[[k]]}}', aero['cz_econ'], '', 3,
           'Cz najmniejszego opadania (ekonomiczne)', check=lambda v: math.sqrt(3 * v.Cx0 / v.k))
    s.calc('Cx_ek', r'C_{x,ek}', r'4C_{x0}', r'4\cdot[[Cx0]]', aero['cx_econ'], '', 4, 'Cx najmniejszego opadania', check=lambda v: 4 * v.Cx0)
    s.calc('K_ek', r'K_{ek}', r'\frac{C_{z,ek}}{C_{x,ek}}', r'\frac{[[Cz_ek]]}{[[Cx_ek]]}', aero['k_econ'], '', 2, 'Doskonałość przy najmniejszym opadaniu',
           check=lambda v: v.Cz_ek / v.Cx_ek)
    s.calc('E_max', r'E_{max}', r'\frac{C_{z,ek}^3}{C_{x,ek}^2}', r'\frac{[[Cz_ek]]^3}{[[Cx_ek]]^2}', aero['e_energy_max'], '', 1,
           'Największa wartość funkcji energetycznej', check=lambda v: v.Cz_ek ** 3 / v.Cx_ek ** 2)
    if r['params']['engine_type'] == 'jet':
        s.calc('Cz_R', r'C_{z,R}', r'\sqrt{\frac{C_{x0}}{3k}}', r'\sqrt{\frac{[[Cx0]]}{3\cdot[[k]]}}', aero['cz_jet_range'], '', 3,
               'Cz największego zasięgu samolotu odrzutowego', SOURCES['B1W'] + ', wzór (28)', check=lambda v: math.sqrt(v.Cx0 / (3 * v.k)))

    _p4_highlift(s, r)
    _p4_cm(s, r)
    _p4_roll(s, r)


def _p4_highlift(s, r):
    from calculations.high_lift import FLAPS, high_lift
    from calculations.paturski_ml import default_retractable_gear
    p, aero, geom = r['params'], r['aerodynamics'], r['geometry']
    fd = high_lift(p, aero['oswald_e'], geometry=geom)
    base = FLAPS[p.get('flap_type', 'single_slotted')]
    slat = {'none': (0, 0), 'slats_auto': (.35, .008), 'fixed_slot': (.30, .012), 'krueger': (.25, .010)}[p.get('slat_type', 'none')]
    s.section('p4', 'highlift', 'Mechanizacja płata: klapy 20° i 40°', SOURCES['B2'] + ', s. 4')
    s.given('dCz_TO_p', r'\Delta c_{z,TO}', base[0], '', 3, 'Przyrost profilowy przy klapach 20°', 'Tabela mechanizacji (wartości wstępne)')
    s.given('dCz_L_p', r'\Delta c_{z,L}', base[1], '', 3, 'Przyrost profilowy przy klapach 40°', 'Tabela mechanizacji (wartości wstępne)')
    s.calc('dCz_TO', r'\Delta C_{z,TO}', r'\Delta c_{z,TO}\frac{S_f}{S}', r'[[dCz_TO_p]]\cdot[[Sf_S]]', fd['delta_cz_to'], '', 4,
           'Przyrost Cz max płata przy starcie', check=lambda v: v.dCz_TO_p * v.Sf_S, tolerance=1e-4)
    s.calc('dCz_L', r'\Delta C_{z,L}', r'\Delta c_{z,L}\frac{S_f}{S}', r'[[dCz_L_p]]\cdot[[Sf_S]]', fd['delta_cz_lnd'], '', 4,
           'Przyrost Cz max płata przy lądowaniu', check=lambda v: v.dCz_L_p * v.Sf_S, tolerance=1e-4)
    sl_terms = ''
    if slat[0]:
        s.given('dCz_sl_p', r'\Delta c_{z,sl}', slat[0], '', 3, 'Przyrost profilowy od slotów / skrzeli', 'Tabela mechanizacji')
        s.given('Ssl_S', r'S_{sl}/S', fd['slat_area_fraction'], '', 4, 'Udział powierzchni ze slotami', 'Geometria P3')
        s.calc('dCz_sl', r'\Delta C_{z,sl}', r'\Delta c_{z,sl}\frac{S_{sl}}{S}', r'[[dCz_sl_p]]\cdot[[Ssl_S]]', fd['slat_lift'], '', 4,
               'Przyrost Cz max od slotów', check=lambda v: v.dCz_sl_p * v.Ssl_S, tolerance=1e-4)
        sl_terms = 'sl'
    s.calc('Cz_TO', r'C_{z\,max,TO}', r'C_{z\,max}+\Delta C_{z,TO}' + (r'+0{,}5\,\Delta C_{z,sl}' if sl_terms else ''),
           r'[[Cz_max]]+[[dCz_TO]]' + (r'+0{,}5\cdot[[dCz_sl]]' if sl_terms else ''), aero['cz_max_to'], '', 2,
           'Cz max w konfiguracji startowej', check=lambda v: v.Cz_max + v.dCz_TO + .5 * getattr(v, 'dCz_sl', 0), tolerance=.0051)
    s.calc('Cz_L', r'C_{z\,max,L}', r'C_{z\,max}+\Delta C_{z,L}' + (r'+\Delta C_{z,sl}' if sl_terms else ''),
           r'[[Cz_max]]+[[dCz_L]]' + (r'+[[dCz_sl]]' if sl_terms else ''), aero['cz_max_lnd'], '', 2,
           'Cz max w konfiguracji do lądowania', check=lambda v: v.Cz_max + v.dCz_L + getattr(v, 'dCz_sl', 0), tolerance=.0051)
    s.given('dCx_TO_p', r'\Delta c_{x,TO}', base[2], '', 4, 'Przyrost profilowy oporu przy klapach 20°', 'Tabela mechanizacji')
    s.given('dCx_L_p', r'\Delta c_{x,L}', base[3], '', 4, 'Przyrost profilowy oporu przy klapach 40°', 'Tabela mechanizacji')
    gear = .018 if default_retractable_gear(p) and p.get('aircraft_type') != 'glider' else 0.0
    s.given('dCx_podw', r'\Delta C_{x0,podw}', gear, '', 3, 'Opór wypuszczonego podwozia chowanego', 'Założenie')
    if slat[0]:
        s.given('dCx_sl_p', r'\Delta c_{x,sl}', slat[1], '', 4, 'Przyrost oporu od slotów', 'Tabela mechanizacji')
    sl = slat[1] * fd['slat_area_fraction']
    s.calc('Cx0_TO', r'C_{x0,TO}', r'C_{x0}+\Delta c_{x,TO}\frac{S_f}{S}' + (r'+0{,}5\,\Delta c_{x,sl}\frac{S_{sl}}{S}' if slat[0] else ''),
           r'[[Cx0]]+[[dCx_TO_p]]\cdot[[Sf_S]]' + (r'+0{,}5\cdot[[dCx_sl_p]]\cdot[[Ssl_S]]' if slat[0] else ''), aero['cx0_to'], '', 4,
           'Opór zerowy w konfiguracji startowej', check=lambda v: v.Cx0 + v.dCx_TO_p * v.Sf_S + .5 * sl, tolerance=6e-5)
    s.calc('Cx0_L', r'C_{x0,L}', r'C_{x0}+\Delta c_{x,L}\frac{S_f}{S}' + (r'+\Delta c_{x,sl}\frac{S_{sl}}{S}' if slat[0] else '') + r'+\Delta C_{x0,podw}',
           r'[[Cx0]]+[[dCx_L_p]]\cdot[[Sf_S]]' + (r'+[[dCx_sl_p]]\cdot[[Ssl_S]]' if slat[0] else '') + r'+[[dCx_podw]]', aero['cx0_lnd'], '', 4,
           'Opór zerowy w konfiguracji do lądowania', check=lambda v: v.Cx0 + v.dCx_L_p * v.Sf_S + sl + v.dCx_podw, tolerance=6e-5)
    for key, cfg, e_flap, value in (('k_TO', 'TO', fd['e_to'], aero['k_to']), ('k_L', 'L', fd['e_lnd'], aero['k_lnd'])):
        s.given('e_f' + cfg, rf'e_{{f,{cfg}}}', e_flap, '', 3, f'Współczynnik Oswalda z wychylonymi klapami ({cfg})', 'Tabela mechanizacji')
        s.calc('e_' + cfg, rf'e_{{{cfg}}}', rf'\min\left(e;\;e_{{f,{cfg}}}\right)', rf'\min\left([[e]];\;[[e_f{cfg}]]\right)', min(aero['oswald_e'], e_flap), '', 3,
               f'Współczynnik Oswalda w konfiguracji {cfg}', check=lambda v, c=cfg: min(v.e, getattr(v, 'e_f' + c)), tolerance=.0011)
        s.calc(key, rf'k_{{{cfg}}}', rf'\frac{{1}}{{\pi\Lambda e_{{{cfg}}}}}', rf'\frac{{1}}{{\pi\cdot[[AR]]\cdot[[e_{cfg}]]}}', value, '', 5,
               f'Współczynnik oporu indukowanego w konfiguracji {cfg}', check=lambda v, c=cfg: 1 / (math.pi * v.AR * getattr(v, 'e_' + c)),
               tolerance=4e-4)


def _p4_cm(s, r):
    cc = r['bipol_projects']['p4']['cg_characteristics']
    cm = cc['cm_model']
    s.section('p4', 'cm', 'Moment pochylający i wyważenie', SOURCES['ML'] + ', P3–P4')
    s.calc('x_sr', r'\bar x_{śr}', r'\frac{\bar x_{SM,p}+\bar x_{SM,t}}{2}', r'\frac{[[xcg_fwd]]+[[xcg_aft]]}{2}', (cm['x_fwd_pct'] + cm['x_aft_pct']) / 2, PCT, 2,
           'Średnie położenie ŚM', check=lambda v: (v.xcg_fwd + v.xcg_aft) / 2)
    if 'Cz_cr' in s.entries:
        s.calc('Cz_ref', r'C_{z,ref}', r'\min\left(C_{z,cr};\;0{,}9\,C_{z\,max}\right)', r'\min\left([[Cz_cr]];\;0{,}9\cdot[[Cz_max]]\right)', cm['cz_ref'], '', 3,
               'Cz przelotu, przy którym ster ustawiono do równowagi', check=lambda v: min(v.Cz_cr, .9 * v.Cz_max), tolerance=6e-4)
    else:
        s.calc('Cz_ref', r'C_{z,ref}', r'\min\left(\frac{2m_0g}{\rho_HSV_{cr}^2};\;0{,}9\,C_{z\,max}\right)',
               r'\min\left(\frac{2\cdot[[m0]]\cdot[[g]]}{[[rho_cr]]\cdot[[S]]\cdot[[V_cr]]^2};\;0{,}9\cdot[[Cz_max]]\right)', cm['cz_ref'], '', 3,
               'Cz przelotu, przy którym ster ustawiono do równowagi',
               check=lambda v: min(2 * v.m0 * v.g / (v.rho_cr * v.S * v.V_cr ** 2), .9 * v.Cz_max), tolerance=6e-4)
    s.calc('Cm0', r'C_{m0}', r'\frac{\bar x_N-\bar x_{śr}}{100}\,C_{z,ref}', r'\frac{[[x_N]]-[[x_sr]]}{100}\cdot[[Cz_ref]]', cm['cm0'], '', 4,
           'Moment przy zerowej sile nośnej (ster ustalony)', check=lambda v: (v.x_N - v.x_sr) / 100 * v.Cz_ref, tolerance=2e-4)
    s.calc('dCm_fwd', r'\left.\frac{\mathrm dC_m}{\mathrm dC_z}\right|_p', r'\frac{\bar x_{SM,p}-\bar x_N}{100}', r'\frac{[[xcg_fwd]]-[[x_N]]}{100}',
           cm['dcm_dcz_fwd'], '', 3, 'Stateczność statyczna przy przednim ŚM', check=lambda v: (v.xcg_fwd - v.x_N) / 100, tolerance=6e-4)
    s.calc('dCm_aft', r'\left.\frac{\mathrm dC_m}{\mathrm dC_z}\right|_t', r'\frac{\bar x_{SM,t}-\bar x_N}{100}', r'\frac{[[xcg_aft]]-[[x_N]]}{100}',
           cm['dcm_dcz_aft'], '', 3, 'Stateczność statyczna przy tylnym ŚM', check=lambda v: (v.xcg_aft - v.x_N) / 100, tolerance=6e-4)
    if cm['cz_trim_fwd'] is not None:
        s.calc('Cz_trim_fwd', r'C_{z,r,p}', r'\frac{-C_{m0}}{\mathrm dC_m/\mathrm dC_z|_p}', r'\frac{-[[Cm0]]}{[[dCm_fwd]]}', cm['cz_trim_fwd'], '', 3,
               'Cz równowagi przy przednim ŚM', check=lambda v: -v.Cm0 / v.dCm_fwd, tolerance=.004)
    if cm['cz_trim_aft'] is not None:
        s.calc('Cz_trim_aft', r'C_{z,r,t}', r'\frac{-C_{m0}}{\mathrm dC_m/\mathrm dC_z|_t}', r'\frac{-[[Cm0]]}{[[dCm_aft]]}', cm['cz_trim_aft'], '', 3,
               'Cz równowagi przy tylnym ŚM', check=lambda v: -v.Cm0 / v.dCm_aft, tolerance=.004)
    s.table('cm_rows', 'Moment pochylający samolotu', r'C_m=C_{m0}+\frac{\bar x-\bar x_N}{100}\,C_z', deps=['Cm0', 'x_N'])
    s.table('speed_polar_rows', 'Biegunowa prędkości dla skrajnych położeń ŚM',
            r'V=\sqrt{\frac{2mg}{\rho S\sqrt{C_z^2+C_x^2}}},\qquad w=V\frac{C_x}{\sqrt{C_z^2+C_x^2}}',
            note='Punkty biegunowej prędkości — tabela prędkości charakterystycznych.', source=SOURCES['ML'] + ', P4, wzory (4.3)–(4.5)',
            deps=['m0', 'S'])


def _p4_roll(s, r):
    ail = r['geometry']['control_surfaces']['ailerons']
    w = r['geometry']['wing']
    s.section('p4', 'roll', 'Skuteczność lotek', SOURCES['R'] + ', wzór (12.18)')
    s.calc('tau_a', r'\tau_a', r'1{,}2\sqrt{c_a/c}', r'1{,}2\cdot\sqrt{[[ca_c]]}', ail['tau_a'], '', 4, 'Skuteczność względna lotki',
           check=lambda v: 1.2 * math.sqrt(v.ca_c))
    s.calc('a_est', 'a', r'\frac{2\pi\Lambda}{2+\sqrt{4+\left(\Lambda/\cos\chi\right)^2}}', r'\frac{2\pi\cdot[[AR]]}{2+\sqrt{4+[[AR]]^2}}'
           if not w['sweep_deg'] else r'\frac{2\pi\cdot[[AR]]}{2+\sqrt{4+\left([[AR]]/\cos[[chi25]]^{\circ}\right)^2}}', ail['a_w_est'], RAD, 3,
           'Gradient siły nośnej płata (wzór Helmbolda)', check=lambda v: 2 * math.pi * v.AR / (2 + math.sqrt(4 + (v.AR / max(.2, math.cos(math.radians(w['sweep_deg'])))) ** 2)),
           tolerance=.002)
    s.solve('I_1', 'I_1', r'I_1=\int_{\eta_{a,1}b/2}^{\eta_{a,2}b/2}c(y)\,y\,\mathrm{d}y', ail['int_y_c'], r'\mathrm{m^3}', 3,
            'Moment statyczny obrysu objętego lotkami (całka analityczna obrysu)', deps=['eta_a_in', 'eta_a_out', 'c_r', 'b'])
    s.calc('Cl_da', r'C_{l\delta_a}', r'\frac{2a\tau_a}{S\,b}\,I_1', r'\frac{2\cdot[[a_est]]\cdot[[tau_a]]}{[[S]]\cdot[[b]]}\cdot[[I_1]]', ail['cl_delta_a'], RAD, 5,
           'Skuteczność lotek (pochodna momentu przechylającego)', check=lambda v: 2 * v.a_est * v.tau_a / (v.S * v.b) * v.I_1)
    s.solve('I_2', 'I_2', r'I_2=\int_0^{b/2}c(y)\,y^2\,\mathrm{d}y', ail['int_y2_c'], r'\mathrm{m^4}', 3,
            'Moment bezwładności obrysu połówki płata (całkowanie metodą Simpsona)', deps=['c_r', 'b'])
    s.calc('Cl_p', r'C_{lp}', r'-\frac{4a}{S\,b^2}\,I_2', r'-\frac{4\cdot[[a_est]]}{[[S]]\cdot[[b]]^2}\cdot[[I_2]]', ail['cl_p'], '', 5,
           'Tłumienie przechylania', check=lambda v: -4 * v.a_est * v.I_2 / (v.S * v.b ** 2))
    s.given('delta_a', r'\delta_{a,max}', ail['delta_a_max_deg'], DEG, 0, 'Największe wychylenie lotek', 'Założenie')
    s.calc('pb2V', r'\frac{pb}{2V}', r'\left|\frac{C_{l\delta_a}}{C_{lp}}\right|\delta_{a,max}', r'\left|\frac{[[Cl_da]]}{[[Cl_p]]}\right|\cdot[[delta_a]]\cdot\frac{\pi}{180}',
           ail['roll_helix_pb_2v'], '', 3, 'Wskaźnik skuteczności przechylania', check=lambda v: abs(v.Cl_da / min(-.01, v.Cl_p)) * math.radians(v.delta_a), tolerance=.0011)
    s.given('pb2V_min', r'\left(\frac{pb}{2V}\right)_{min}', ail['min_pb_2v_req'], '', 3, 'Kryterium wstępne dla klasy samolotu', 'Założenie')


# =============================================================================================
# P5 — osiągi
# =============================================================================================
def _p5(s, r):
    p, perf, aero, mass = r['params'], r['performance'], r['aerodynamics'], r['mass']
    t = perf['terms']
    powered = _powered(r)
    s.section('p5', 'speeds', 'Prędkości charakterystyczne', SOURCES['ML'] + ', P6')
    s.calc('WS_0', r'\frac{W}{S}', r'\frac{m_0 g}{S}', r'\frac{[[m0]]\cdot[[g]]}{[[S]]}', t['ws'], NM2, 1, 'Obciążenie powierzchni przy masie startowej',
           check=lambda v: v.m0 * v.g / v.S)
    for key, cz, label, ms in (('V_S', 'Cz_max', 'konfiguracja gładka', t['vs_clean']), ('V_STO', 'Cz_TO', 'konfiguracja startowa', t['vs_to']),
                               ('V_S0', 'Cz_L', 'konfiguracja do lądowania', t['vs_lnd'])):
        sym = {'V_S': 'V_{S1}', 'V_STO': 'V_{S,TO}', 'V_S0': 'V_{S0}'}[key]
        czsym = s.entries[cz]['sym']
        s.calc(key, sym, rf'\sqrt{{\frac{{2\,W/S}}{{\rho_0 {czsym}}}}}', rf'\sqrt{{\frac{{2\cdot[[WS_0]]}}{{[[rho0]]\cdot[[{cz}]]}}}}', ms, MS, 2,
               f'Prędkość przeciągnięcia — {label}', check=lambda v, c=cz: math.sqrt(2 * v.WS_0 / (v.rho0 * getattr(v, c))))
        _to_kmh(s, key + '_kmh', sym, key, ms * 3.6, f'Prędkość przeciągnięcia — {label}')
    s.calc('V_LOF', 'V_{LOF}', r'1{,}15\,V_{S,TO}', r'1{,}15\cdot[[V_STO]]', perf['speeds']['v_lof_kmh'] / 3.6, MS, 2, 'Prędkość oderwania',
           check=lambda v: 1.15 * v.V_STO, tolerance=.02)
    s.calc('V_2', 'V_2', r'1{,}20\,V_{S,TO}', r'1{,}20\cdot[[V_STO]]', perf['speeds']['v_2_kmh'] / 3.6, MS, 2, 'Prędkość bezpieczna wznoszenia',
           check=lambda v: 1.2 * v.V_STO, tolerance=.02)
    lt = perf['landing']['terms']
    s.given('m_L', 'm_L', perf['landing']['mass_kg'], KG, 1, 'Masa na początku lądowania', 'Bilans misji P2')
    s.calc('WS_Lp', r'\left(\frac{W}{S}\right)_L', r'\frac{m_L g}{S}', r'\frac{[[m_L]]\cdot[[g]]}{[[S]]}', lt['ws_lnd'], NM2, 1,
           'Obciążenie powierzchni przy lądowaniu', check=lambda v: v.m_L * v.g / v.S)
    s.calc('V_SL', r'V_{S,L}', r'\sqrt{\frac{2\,(W/S)_L}{\rho_0 C_{z\,max,L}}}', r'\sqrt{\frac{2\cdot[[WS_Lp]]}{[[rho0]]\cdot[[Cz_L]]}}', lt['vs'], MS, 2,
           'Prędkość przeciągnięcia przy masie do lądowania', check=lambda v: math.sqrt(2 * v.WS_Lp / (v.rho0 * v.Cz_L)))
    s.calc('V_app', 'V_{app}', r'1{,}3\,V_{S,L}', r'1{,}3\cdot[[V_SL]]', lt['v_app'], MS, 2, 'Prędkość podejścia do lądowania', check=lambda v: 1.3 * v.V_SL)
    s.calc('V_TD', 'V_{TD}', r'1{,}15\,V_{S,L}', r'1{,}15\cdot[[V_SL]]', lt['v_td'], MS, 2, 'Prędkość przyziemienia', check=lambda v: 1.15 * v.V_SL)
    if powered:
        if p['engine_type'] == 'jet':
            cond = r'T\,\varphi_0(V)\,V=\tfrac12\rho_0V^3SC_{x0}+\frac{2k(m_0g)^2}{\rho_0VS}'
            deps = ['T_0', 'Cx0', 'k', 'm0', 'S']
        else:
            cond = r'1000\,\eta_pN=\tfrac12\rho_0V^3SC_{x0}+\frac{2k(m_0g)^2}{\rho_0VS}'
            deps = ['P', 'eta_p', 'Cx0', 'k', 'm0', 'S']
        s.solve('V_max', r'V_{max}', cond, t['v_max_sl'], MS, 2, 'Prędkość maksymalna lotu poziomego przy ziemi (większy pierwiastek)', deps=deps)
        _to_kmh(s, 'V_max_kmh', r'V_{max}', 'V_max', perf['speeds']['v_max_sl_kmh'], 'Prędkość maksymalna lotu poziomego przy ziemi')

    if powered:
        _p5_climb(s, r)
        _p5_takeoff(s, r)
    _p5_landing(s, r)
    if powered:
        _p5_range(s, r)
    _p5_glide(s, r)
    if powered:
        _p5_turn(s, r)


def _p5_climb(s, r):
    p, perf = r['params'], r['performance']
    p6 = perf['paturski_p6']
    offer = p6['offer_chart_summary']
    s.section('p5', 'climb', 'Wznoszenie i pułap (metoda mocy)', SOURCES['ML'] + ', P6, tab. 6.1–6.2')
    jet = p['engine_type'] == 'jet'
    s.table('climb_rows', 'Bilans mocy (tab. 6.1)', r'N_n=\tfrac12\rho V^3SC_{x0}+\frac{2k(mg)^2}{\rho VS},\qquad '
            + (r'N_r=1000\,T\varphi_H V,' if jet else r'N_r=1000\,\eta_p N\varphi_H,') + r'\qquad w=\frac{N_r-N_n}{mg}',
            note='Punkty bilansu mocy — tabela 6.1.', deps=['Cx0', 'k', 'm0', 'S'])
    v = offer['v_w_h0_kmh'] / 3.6
    s.given('V_wy', r'V_{w}', v, MS, 2, 'Prędkość największego wznoszenia przy ziemi (maksimum w(V))', 'Tabela 6.1')
    nn = .5 * RHO0 * v ** 3 * r['geometry']['wing']['S'] * r['aerodynamics']['paturski_p3']['analytical_polar_fit']['cx0_approx'] \
        + 2 * r['aerodynamics']['paturski_p3']['analytical_polar_fit']['slope_d_cx_d_cz2'] * (r['mass']['m0'] * G0) ** 2 / (RHO0 * v * r['geometry']['wing']['S'])
    s.calc('N_n_wy', r'N_n', r'\tfrac12\rho_0V_w^3SC_{x0}+\frac{2k(m_0g)^2}{\rho_0V_wS}',
           r'\tfrac12\cdot[[rho0]]\cdot[[V_wy]]^3\cdot[[S]]\cdot[[Cx0]]+\frac{2\cdot[[k]]\cdot([[m0]]\cdot[[g]])^2}{[[rho0]]\cdot[[V_wy]]\cdot[[S]]}', nn, r'\mathrm{W}', 0,
           'Moc niezbędna przy prędkości największego wznoszenia', check=lambda q: .5 * q.rho0 * q.V_wy ** 3 * q.S * q.Cx0 + 2 * q.k * (q.m0 * q.g) ** 2 / (q.rho0 * q.V_wy * q.S),
           tolerance=.004 * nn)
    if jet:
        avail = (r['sizing']['design_point']['thrust_kn'] or 0) * 1000 * _lapse_value(r, 0, v) * v
        s.calc('N_r_wy', r'N_r', r'1000\,T\,\varphi_0\,V_w', r'1000\cdot[[T_0]]\cdot' + tex_value(_lapse_value(r, 0, v), 4) + r'\cdot[[V_wy]]', avail, r'\mathrm{W}', 0,
               'Moc rozporządzalna przy ziemi', check=lambda q: 1000 * q.T_0 * _lapse_value(r, 0, v) * q.V_wy, tolerance=.002 * avail)
    else:
        avail = (r['sizing']['design_point']['power_kw'] or 0) * 1000 * _lapse_value(r, 0, v) * float(p.get('prop_efficiency', .82))
        s.calc('N_r_wy', r'N_r', r'1000\,\eta_pN\varphi_0', r'1000\cdot[[eta_p]]\cdot[[P]]\cdot' + tex_value(_lapse_value(r, 0, v), 4), avail, r'\mathrm{W}', 0,
               'Moc rozporządzalna przy ziemi', check=lambda q: 1000 * q.eta_p * q.P * _lapse_value(r, 0, v), tolerance=.002 * avail)
    s.calc('w_max', r'w_{max}', r'\frac{N_r-N_n}{m_0g}', r'\frac{[[N_r_wy]]-[[N_n_wy]]}{[[m0]]\cdot[[g]]}', perf['climb']['wy_max_ms'], MS, 2,
           'Największa prędkość wznoszenia przy ziemi', check=lambda q: (q.N_r_wy - q.N_n_wy) / (q.m0 * q.g), tolerance=.011)
    ceil = p6['table_6_2_climb_and_ceilings']['ceilings']
    s.solve('H_t', 'H_t', r'w_{max}(H_t)=0', perf['ceiling']['absolute_ceiling_m'], M, 0, 'Pułap teoretyczny (bisekcja w modelu ISA)',
            deps=['w_max'])
    s.solve('H_p', 'H_p', rf'w_{{max}}(H_p)={tex_value(ceil["w_crit_ceiling_ms"], 1)}\;\mathrm{{m/s}}', perf['ceiling']['service_ceiling_m'], M, 0,
            'Pułap praktyczny', deps=['w_max'])
    if ceil.get('t_hp_climb_to_practical_ceiling_min'):
        s.solve('t_Hp', 't_{H_p}', r't=\int_0^{H_p}\frac{\mathrm dh}{w_{max}(h)}', ceil['t_hp_climb_to_practical_ceiling_min'], r'\mathrm{min}', 1,
                'Czas wznoszenia na pułap praktyczny (całkowanie metodą Simpsona)', deps=['H_p'])


def _lapse_value(r, altitude, speed):
    from calculations.flight_model import propulsion_lapse
    return propulsion_lapse(r['params'], altitude, speed)


def _p5_takeoff(s, r):
    to = r['performance']['takeoff']
    if not to.get('available') or 'terms' not in to:
        return
    t = to['terms']
    jet = r['params']['engine_type'] == 'jet'
    s.section('p5', 'takeoff', 'Start do wysokości 15 m', SOURCES['ML'] + ', P6; model jednakowego przyspieszenia średniego')
    s.calc('V_LOFt', r'V_{LOF}', r'1{,}15\,V_{S,TO}', r'1{,}15\cdot[[V_STO]]', t['vlof'], MS, 2, 'Prędkość oderwania', check=lambda v: 1.15 * v.V_STO)
    s.calc('V_rms', r'V_{śr}', r'\frac{V_{LOF}}{\sqrt2}', r'\frac{[[V_LOFt]]}{\sqrt2}', t['vrms'], MS, 2, 'Prędkość średnia (kwadratowa) rozbiegu',
           check=lambda v: v.V_LOFt / math.sqrt(2))
    s.calc('q_roz', r'q_{śr}', r'\frac{\rho_0V_{śr}^2}{2}', r'\frac{[[rho0]]\cdot[[V_rms]]^2}{2}', t['q'], PA, 1, 'Ciśnienie dynamiczne średnie',
           check=lambda v: .5 * v.rho0 * v.V_rms ** 2)
    s.calc('phi_ge', r'\phi_{ge}', r'\frac{1{,}6^2}{1+1{,}6^2}', r'\frac{2{,}56}{3{,}56}', t['phi'], '', 4, 'Wpływ ziemi na opór indukowany',
           check=lambda v: 1.6 ** 2 / (1 + 1.6 ** 2))
    s.given('mu_r', r'\mu', t['mu_ground'], '', 3, 'Współczynnik tarcia tocznego', 'Nawierzchnia pasa')
    if jet:
        s.calc('TW_roz', r'\left(\frac{T}{W}\right)_{roz}', r'\frac{T}{W}', r'[[TW]]', t['thrust_roll'], '', 4, 'Ciąg względny na rozbiegu',
               check=lambda v: v.TW)
    else:
        s.calc('TW_roz', r'\left(\frac{T}{W}\right)_{roz}', r'\frac{N}{W}\,\frac{\eta_{TO}}{V_{śr}}', r'[[PW]]\cdot\frac{[[eta_TO]]}{[[V_rms]]}', t['thrust_roll'], '', 4,
               'Ciąg względny śmigła na rozbiegu', check=lambda v: v.PW * v.eta_TO / v.V_rms, tolerance=2e-4)
    s.calc('a_roz', r'\frac{\bar a}{g}', r'\left(\frac{T}{W}\right)_{roz}-\frac{q_{śr}}{W/S}\left(C_{x0,TO}+\phi_{ge}k_{TO}\cdot0{,}25^2\right)-\mu\left(1-\frac{q_{śr}}{W/S}\cdot0{,}25\right)',
           r'[[TW_roz]]-\frac{[[q_roz]]}{[[WS_0]]}\cdot\left([[Cx0_TO]]+[[phi_ge]]\cdot[[k_TO]]\cdot0{,}0625\right)-[[mu_r]]\cdot\left(1-\frac{[[q_roz]]}{[[WS_0]]}\cdot0{,}25\right)',
           t['net'], '', 4, 'Względne przyspieszenie średnie na rozbiegu (Cz rozbiegu = 0,25)',
           check=lambda v: v.TW_roz - v.q_roz / v.WS_0 * (v.Cx0_TO + v.phi_ge * v.k_TO * .0625) - v.mu_r * (1 - v.q_roz / v.WS_0 * .25), tolerance=3e-4)
    s.calc('s_roll', r's_{roz}', r'\frac{V_{LOF}^2}{2g\,(\bar a/g)}', r'\frac{[[V_LOFt]]^2}{2\cdot[[g]]\cdot[[a_roz]]}', to['ground_roll_m'], M, 1, 'Długość rozbiegu',
           check=lambda v: v.V_LOFt ** 2 / (2 * v.g * v.a_roz), tolerance=.15)
    s.calc('t_roll', r't_{roz}', r'\frac{V_{LOF}}{g\,(\bar a/g)}', r'\frac{[[V_LOFt]]}{[[g]]\cdot[[a_roz]]}', to['ground_roll_time_s'], S_, 1, 'Czas rozbiegu',
           check=lambda v: v.V_LOFt / (v.g * v.a_roz), tolerance=.06)
    s.calc('V_2t', 'V_2', r'1{,}20\,V_{S,TO}', r'1{,}20\cdot[[V_STO]]', t['v2'], MS, 2, 'Prędkość wznoszenia nad przeszkodą', check=lambda v: 1.2 * v.V_STO)
    s.calc('q_2', 'q_2', r'\frac{\rho_0V_2^2}{2}', r'\frac{[[rho0]]\cdot[[V_2t]]^2}{2}', t['q2'], PA, 1, 'Ciśnienie dynamiczne przy V₂',
           check=lambda v: .5 * v.rho0 * v.V_2t ** 2)
    if jet:
        s.calc('TW_2', r'\left(\frac{T}{W}\right)_2', r'\frac{T}{W}', r'[[TW]]', t['thrust_climb'], '', 4, 'Ciąg względny przy V₂', check=lambda v: v.TW)
    else:
        s.calc('TW_2', r'\left(\frac{T}{W}\right)_2', r'\frac{N}{W}\,\frac{\eta_p}{V_2}', r'[[PW]]\cdot\frac{[[eta_p]]}{[[V_2t]]}', t['thrust_climb'], '', 4,
               'Ciąg względny śmigła przy V₂', check=lambda v: v.PW * v.eta_p / v.V_2t, tolerance=2e-4)
    s.calc('G_2', r'\sin\gamma', r'\left(\frac{T}{W}\right)_2-\frac{q_2}{W/S}\left(C_{x0,TO}+k_{TO}\left(\frac{W/S}{q_2}\right)^2\right)',
           r'[[TW_2]]-\frac{[[q_2]]}{[[WS_0]]}\cdot\left([[Cx0_TO]]+[[k_TO]]\cdot\left(\frac{[[WS_0]]}{[[q_2]]}\right)^2\right)', t['gradient'], '', 4,
           'Gradient wznoszenia po oderwaniu', check=lambda v: v.TW_2 - v.q_2 / v.WS_0 * (v.Cx0_TO + v.k_TO * (v.WS_0 / v.q_2) ** 2), tolerance=3e-4)
    s.calc('V_tr', r'V_{tr}', r'1{,}175\,V_{S,TO}', r'1{,}175\cdot[[V_STO]]', t['vtr'], MS, 2, 'Prędkość na łuku przejściowym', check=lambda v: 1.175 * v.V_STO)
    s.calc('R_tr', r'R_{tr}', r'\frac{V_{tr}^2}{0{,}15\,g}', r'\frac{[[V_tr]]^2}{0{,}15\cdot[[g]]}', t['radius'], M, 1, 'Promień łuku przejściowego (n = 1,15)',
           check=lambda v: v.V_tr ** 2 / (.15 * v.g))
    if t['height'] < 15:
        s.calc('gamma_TO', r'\gamma', r'\arcsin\left(\min\left(0{,}35;\;\sin\gamma\right)\right)', r'\arcsin\left(\min\left(0{,}35;\;[[G_2]]\right)\right)', t['gamma'],
               r'\mathrm{rad}', 4, 'Kąt toru wznoszenia', check=lambda v: math.asin(min(.35, v.G_2)), tolerance=6e-4)
        s.calc('h_tr', r'h_{tr}', r'R_{tr}\left(1-\cos\gamma\right)', r'[[R_tr]]\cdot\left(1-\cos[[gamma_TO]]\right)', t['height'], M, 2, 'Wysokość na końcu łuku',
               check=lambda v: v.R_tr * (1 - math.cos(v.gamma_TO)), tolerance=.02)
    else:
        s.calc('gamma_TO', r'\gamma', r'\arccos\left(1-\frac{15}{R_{tr}}\right)', r'\arccos\left(1-\frac{15}{[[R_tr]]}\right)', t['gamma'], r'\mathrm{rad}', 4,
               'Kąt toru: łuk przejściowy osiąga 15 m przed końcem wyrównania', check=lambda v: math.acos(max(0, 1 - 15 / v.R_tr)), tolerance=6e-4)
    if t['height'] < 15:
        s.calc('s_tr', r's_{tr}', r'R_{tr}\sin\gamma', r'[[R_tr]]\cdot\sin[[gamma_TO]]', to['transition_m'], M, 1, 'Długość łuku przejściowego',
               check=lambda v: v.R_tr * math.sin(v.gamma_TO), tolerance=.15)
        s.calc('s_cl', r's_{wzn}', r'\frac{15-h_{tr}}{\tan\gamma}', r'\frac{15-[[h_tr]]}{\tan[[gamma_TO]]}', to['climb_to_15m_m'], M, 1, 'Wznoszenie do 15 m',
               check=lambda v: (15 - v.h_tr) / math.tan(v.gamma_TO), tolerance=.2)
        s.calc('s_TO15', r's_{TO}', r's_{roz}+s_{tr}+s_{wzn}', r'[[s_roll]]+[[s_tr]]+[[s_cl]]', to['distance_to_15m'], M, 1, 'Całkowita długość startu do 15 m',
               check=lambda v: v.s_roll + v.s_tr + v.s_cl, tolerance=.2)
    else:
        s.calc('s_tr', r's_{tr}', r'R_{tr}\sin\gamma', r'[[R_tr]]\cdot\sin[[gamma_TO]]', to['transition_m'], M, 1, 'Długość łuku do wysokości 15 m',
               check=lambda v: v.R_tr * math.sin(v.gamma_TO), tolerance=.15)
        s.calc('s_TO15', r's_{TO}', r's_{roz}+s_{tr}', r'[[s_roll]]+[[s_tr]]', to['distance_to_15m'], M, 1, 'Całkowita długość startu do 15 m',
               check=lambda v: v.s_roll + v.s_tr, tolerance=.2)


def _p5_landing(s, r):
    if r['params'].get('operating_surface') == 'water':
        return
    perf = r['performance']
    ld, t = perf['landing'], perf['landing']['terms']
    s.section('p5', 'landing', 'Lądowanie znad przeszkody 15 m', SOURCES['ML'] + ', P6')
    s.given('gamma_app', r'\gamma_{pod}', t['gamma_app_deg'], DEG, 1, 'Kąt ścieżki podejścia', 'Założenie')
    s.calc('R_fl', r'R_{wyr}', r'\frac{V_{app}^2}{0{,}15\,g}', r'\frac{[[V_app]]^2}{0{,}15\cdot[[g]]}', t['r_flare'], M, 1, 'Promień wyrównania (n = 1,15)',
           check=lambda v: v.V_app ** 2 / (.15 * v.g))
    s.calc('h_fl', r'h_{wyr}', r'R_{wyr}\left(1-\cos\gamma_{pod}\right)', r'[[R_fl]]\cdot\left(1-\cos[[gamma_app]]^{\circ}\right)', t['h_flare'], M, 2,
           'Wysokość rozpoczęcia wyrównania', check=lambda v: v.R_fl * (1 - math.cos(math.radians(v.gamma_app))))
    if t['h_flare'] > 15:
        s.calc('gamma_fl', r'\theta_{wyr}', r'2\arcsin\sqrt{\frac{15}{2R_{wyr}}}',
               r'2\arcsin\sqrt{\frac{15}{2\cdot[[R_fl]]}}', t['effective_flare_angle_rad'], r'\mathrm{rad}', 5,
               'Kąt łuku od przeszkody 15 m do przyziemienia (przeszkoda wewnątrz wyrównania)',
               check=lambda v: 2 * math.asin(math.sqrt(15 / (2 * v.R_fl))))
        s.calc('s_air', r's_{pow}', r'R_{wyr}\sin\theta_{wyr}', r'[[R_fl]]\cdot\sin[[gamma_fl]]', ld['air_approach_m'], M, 1,
               'Odcinek powietrzny lądowania — część łuku wyrównania',
               check=lambda v: v.R_fl * math.sin(v.gamma_fl), tolerance=.15)
    else:
        s.calc('s_air', r's_{pow}', r'\frac{15-h_{wyr}}{\tan\gamma_{pod}}+R_{wyr}\sin\gamma_{pod}',
               r'\frac{15-[[h_fl]]}{\tan[[gamma_app]]^{\circ}}+[[R_fl]]\cdot\sin[[gamma_app]]^{\circ}', ld['air_approach_m'], M, 1,
               'Odcinek powietrzny lądowania — prosta ścieżka i łuk wyrównania',
               check=lambda v: (15 - v.h_fl) / math.tan(math.radians(v.gamma_app)) + v.R_fl * math.sin(math.radians(v.gamma_app)),
               tolerance=.15)
    s.calc('s_free', r's_{sw}', r'1{,}5\,V_{TD}', r'1{,}5\cdot[[V_TD]]', ld['free_roll_m'], M, 1, 'Dobieg swobodny (1,5 s)', check=lambda v: 1.5 * v.V_TD, tolerance=.06)
    s.given('mu_h', r'\mu_h', t['mu_brake'], '', 2, 'Współczynnik tarcia przy hamowaniu', 'Założenie')
    s.calc('q_dob', r'q_{śr}', r'\frac{\rho_0}{2}\left(\frac{V_{TD}}{\sqrt2}\right)^2', r'\frac{[[rho0]]}{2}\cdot\left(\frac{[[V_TD]]}{\sqrt2}\right)^2', t['q_rms'], PA, 1,
           'Średnie ciśnienie dynamiczne dobiegu', check=lambda v: .5 * v.rho0 * (v.V_TD / math.sqrt(2)) ** 2)
    s.calc('Cx_dob', r'C_{x,dob}', r'C_{x0,L}+\phi_{ge}k_L\cdot0{,}2^2', r'[[Cx0_L]]+\frac{2{,}56}{3{,}56}\cdot[[k_L]]\cdot0{,}04', t['cx_roll'], '', 4,
           'Współczynnik oporu na dobiegu (Cz = 0,2)', check=lambda v: v.Cx0_L + 2.56 / 3.56 * v.k_L * .04, tolerance=6e-5)
    s.calc('a_h', r'\bar a_h', r'g\left(\mu_h+\frac{q_{śr}}{(W/S)_L}\left(C_{x,dob}-\mu_h\cdot0{,}2\right)\right)',
           r'[[g]]\cdot\left([[mu_h]]+\frac{[[q_dob]]}{[[WS_Lp]]}\cdot\left([[Cx_dob]]-[[mu_h]]\cdot0{,}2\right)\right)', t['a_mean'], r'\mathrm{m/s^2}', 3,
           'Średnie opóźnienie hamowania', check=lambda v: v.g * (v.mu_h + v.q_dob / v.WS_Lp * (v.Cx_dob - v.mu_h * .2)), tolerance=2e-3)
    s.calc('s_brake', r's_h', r'\frac{V_{TD}^2}{2\bar a_h}', r'\frac{[[V_TD]]^2}{2\cdot[[a_h]]}', ld['braking_roll_m'], M, 1, 'Droga hamowania',
           check=lambda v: v.V_TD ** 2 / (2 * v.a_h), tolerance=.15)
    s.calc('s_L15', 's_L', r's_{pow}+s_{sw}+s_h', r'[[s_air]]+[[s_free]]+[[s_brake]]', ld['distance_from_15m'], M, 1, 'Całkowita długość lądowania znad 15 m',
           check=lambda v: v.s_air + v.s_free + v.s_brake, tolerance=.2)


def _p5_range(s, r):
    p, perf, mass = r['params'], r['performance'], r['mass']
    ra = perf['paturski_p6']['range_endurance_6_5']
    rows = ra.get('table_6_3') or []
    row = next((q for q in rows if abs(q['v_kmh'] - float(p['cruise_speed_kmh'])) < .06), None)
    s.section('p5', 'range', 'Zasięg i długotrwałość przy wymaganej prędkości', SOURCES['ML'] + ', P6, wzory (6.13)–(6.38)')
    fit = r['aerodynamics']['paturski_p3']['analytical_polar_fit']
    jet = p['engine_type'] == 'jet'
    s.table('range_rows', 'Zasięg i długotrwałość (tab. 6.3)',
            (r'L=3{,}6\,V\,t,\qquad t=\frac{10}{g\,q_e}\sqrt{\frac{\pi\Lambda_e}{C_{x0}}}\left[\arctan\frac{2gm_p}{A}-\arctan\frac{2gm_k}{A}\right]' if jet else
             r'L=3{,}6\,V\,t,\qquad t=\frac{1000\,\eta_p}{g\,V\,q_e}\sqrt{\frac{\pi\Lambda_e}{C_{x0}}}\left[\arctan\frac{2gm_p}{A}-\arctan\frac{2gm_k}{A}\right]')
            + r',\qquad A=\rho SV^2\sqrt{C_{x0}\pi\Lambda_e}', note='Wartości dla kolejnych prędkości — tabela zasięgu.', deps=['Cx0', 'Lambda_e'])
    if not row:
        return
    phases = {ph['key']: ph for ph in mass['mission_phases']}
    s.given('m_p_cr', 'm_p', phases['cruise']['mass_start_kg'], KG, 1, 'Masa na początku przelotu', 'Bilans misji P2')
    s.given('m_k_cr', 'm_k', phases['cruise']['mass_end_kg'], KG, 1, 'Masa na końcu przelotu', 'Bilans misji P2')
    raw = float(p.get('sfc', .62 if jet else 265))
    qe = raw * 10 / G0 if jet else (raw / 1000 if raw > 10 else raw)
    if jet:
        s.calc('q_e', 'q_e', r'\frac{10\,c_Tg}{g}', r'\frac{10\cdot[[TSFC]]}{[[g]]}', qe, r'\mathrm{kg/(daN\,h)}', 4, 'Jednostkowe zużycie paliwa w jednostkach tabeli 6.3',
               check=lambda v: 10 * v.TSFC / v.g)
    else:
        s.calc('q_e', 'q_e', r'\frac{SFC}{1000}', r'\frac{[[SFC]]}{1000}', qe, r'\mathrm{kg/(kW\,h)}', 4, 'Jednostkowe zużycie paliwa w jednostkach tabeli 6.3',
               check=lambda v: v.SFC / 1000)
    rho = s.entries['rho_cr']['value']
    v = float(p['cruise_speed_kmh']) / 3.6
    a_param = rho * r['geometry']['wing']['S'] * v ** 2 * math.sqrt(fit['cx0_approx'] * math.pi * fit['lambda_e_approx'])
    s.calc('A_R', 'A', r'\rho_HSV^2\sqrt{C_{x0}\pi\Lambda_e}', r'[[rho_cr]]\cdot[[S]]\cdot[[V_cr]]^2\cdot\sqrt{[[Cx0]]\cdot\pi\cdot[[Lambda_e]]}', a_param, N_, 0,
           'Parametr całki zasięgu', check=lambda q: q.rho_cr * q.S * q.V_cr ** 2 * math.sqrt(q.Cx0 * math.pi * q.Lambda_e), tolerance=.004 * a_param)
    atan_term = math.atan(2 * G0 * phases['cruise']['mass_start_kg'] / a_param) - math.atan(2 * G0 * phases['cruise']['mass_end_kg'] / a_param)
    s.calc('atan_R', r'\Delta\Phi', r'\arctan\frac{2gm_p}{A}-\arctan\frac{2gm_k}{A}', r'\arctan\frac{2\cdot[[g]]\cdot[[m_p_cr]]}{[[A_R]]}-\arctan\frac{2\cdot[[g]]\cdot[[m_k_cr]]}{[[A_R]]}',
           atan_term, r'\mathrm{rad}', 5, 'Różnica funkcji arctan', check=lambda q: math.atan(2 * q.g * q.m_p_cr / q.A_R) - math.atan(2 * q.g * q.m_k_cr / q.A_R))
    if jet:
        s.calc('t_R', 't', r'\frac{10}{g\,q_e}\sqrt{\frac{\pi\Lambda_e}{C_{x0}}}\,\Delta\Phi', r'\frac{10}{[[g]]\cdot[[q_e]]}\cdot\sqrt{\frac{\pi\cdot[[Lambda_e]]}{[[Cx0]]}}\cdot[[atan_R]]',
               row.get('t_const_v_h_unrounded', row['t_const_v_h']), H_, 5, 'Długotrwałość przelotu', check=lambda q: 10 / (q.g * q.q_e) * math.sqrt(math.pi * q.Lambda_e / q.Cx0) * q.atan_R, tolerance=.011)
    else:
        s.calc('t_R', 't', r'\frac{1000\,\eta_p}{g\,V\,q_e}\sqrt{\frac{\pi\Lambda_e}{C_{x0}}}\,\Delta\Phi',
               r'\frac{1000\cdot[[eta_p]]}{[[g]]\cdot[[V_cr]]\cdot[[q_e]]}\cdot\sqrt{\frac{\pi\cdot[[Lambda_e]]}{[[Cx0]]}}\cdot[[atan_R]]', row.get('t_const_v_h_unrounded', row['t_const_v_h']), H_, 5,
               'Długotrwałość przelotu', check=lambda q: 1000 * q.eta_p / (q.g * q.V_cr * q.q_e) * math.sqrt(math.pi * q.Lambda_e / q.Cx0) * q.atan_R, tolerance=.011)
    s.calc('L_R', 'L', r'3{,}6\,V\,t', r'3{,}6\cdot[[V_cr]]\cdot[[t_R]]', row.get('l_const_v_km_unrounded', row['l_const_v_km']), KM, 1, 'Zasięg przy wymaganej prędkości i wysokości',
           check=lambda q: 3.6 * q.V_cr * q.t_R, tolerance=max(1.0, .004 * row['l_const_v_km']))


def _p5_glide(s, r):
    glide = r['performance']['glide']
    best, sink = glide['best_glide'], glide['minimum_sink']
    s.section('p5', 'glide', 'Lot ślizgowy — równowaga sił', SOURCES['ML'] + ', P4, wzory (4.3)–(4.5)')
    s.given('rho_gl', r'\rho_H', glide['rho'], r'\mathrm{kg/m^3}', 4, 'Gęstość powietrza na wysokości lotu ślizgowego', 'ISA')
    for key, label, pt in (('opt', 'największej doskonałości', best), ('ek', 'najmniejszego opadania', sink)):
        s.given('Cz_g' + key, rf'C_{{z,{key}}}', pt['cz'], '', 4, f'Cz punktu {label} (tabela biegunowej prędkości)', 'Biegunowa P4')
        s.calc('Cx_g' + key, rf'C_{{x,{key}}}', r'C_{x0}+k\,C_z^2', rf'[[Cx0]]+[[k]]\cdot[[Cz_g{key}]]^2', pt['cx'], '', 5, f'Cx punktu {label}',
               check=lambda v, k=key: v.Cx0 + v.k * getattr(v, 'Cz_g' + k) ** 2)
        s.calc('V_g' + key, rf'V_{{{key}}}', r'\sqrt{\frac{2m_0g}{\rho_HS\sqrt{C_z^2+C_x^2}}}',
               rf'\sqrt{{\frac{{2\cdot[[m0]]\cdot[[g]]}}{{[[rho_gl]]\cdot[[S]]\cdot\sqrt{{[[Cz_g{key}]]^2+[[Cx_g{key}]]^2}}}}}}', pt['v_ms'], MS, 2,
               f'Prędkość {label} (TAS)', check=lambda v, k=key: math.sqrt(2 * v.m0 * v.g / (v.rho_gl * v.S * math.hypot(getattr(v, 'Cz_g' + k), getattr(v, 'Cx_g' + k)))))
        s.calc('w_g' + key, rf'w_{{{key}}}', r'V\frac{C_x}{\sqrt{C_z^2+C_x^2}}', rf'[[V_g{key}]]\cdot\frac{{[[Cx_g{key}]]}}{{\sqrt{{[[Cz_g{key}]]^2+[[Cx_g{key}]]^2}}}}',
               pt['sink_ms'], MS, 3, f'Prędkość opadania — punkt {label}',
               check=lambda v, k=key: getattr(v, 'V_g' + k) * getattr(v, 'Cx_g' + k) / math.hypot(getattr(v, 'Cz_g' + k), getattr(v, 'Cx_g' + k)))
    s.calc('K_gopt', r'K', r'\frac{C_{z,opt}}{C_{x,opt}}', r'\frac{[[Cz_gopt]]}{[[Cx_gopt]]}', best['ld'], '', 2, 'Doskonałość w locie ślizgowym',
           check=lambda v: v.Cz_gopt / v.Cx_gopt)


def _p5_turn(s, r):
    turn = r['performance']['turn']
    t = turn['terms']
    if turn['mode'] != 'level':
        return
    s.section('p5', 'turn', 'Zakręt ustalony', SOURCES['B1W'] + ', wzory (30)–(52)')
    s.calc('V_z', 'V_z', r'\max\left(1{,}45\,V_{S1};\;\min\left(V_{cr};\;0{,}85\,V_{max}\right)\right)',
           r'\max\left(1{,}45\cdot[[V_S]];\;\min\left([[V_cr]];\;0{,}85\cdot[[V_max]]\right)\right)', t['v'], MS, 2, 'Prędkość zakrętu',
           check=lambda v: max(1.45 * v.V_S, min(v.V_cr, .85 * v.V_max)))
    s.calc('q_z', 'q_z', r'\frac{\rho_0V_z^2}{2}', r'\frac{[[rho0]]\cdot[[V_z]]^2}{2}', t['q'], PA, 1, 'Ciśnienie dynamiczne zakrętu', check=lambda v: .5 * v.rho0 * v.V_z ** 2)
    s.calc('n_aero', r'n_{aero}', r'\frac{q_zC_{z\,max}}{W/S}', r'\frac{[[q_z]]\cdot[[Cz_max]]}{[[WS_0]]}', t['n_aero_max'], '', 3, 'Przeciążenie graniczne aerodynamicznie',
           SOURCES['B1W'] + ', wzór (38)', check=lambda v: v.q_z * v.Cz_max / v.WS_0)
    jet = r['params']['engine_type'] == 'jet'
    if jet:
        s.calc('T_z', 'T_r', r'1000\,T', r'1000\cdot[[T_0]]', t['t_avail'], N_, 0, 'Ciąg rozporządzalny', check=lambda v: 1000 * v.T_0, tolerance=.002 * t['t_avail'])
    else:
        s.calc('T_z', 'T_r', r'\frac{1000\,\eta_pN}{V_z}', r'\frac{1000\cdot[[eta_p]]\cdot[[P]]}{[[V_z]]}', t['t_avail'], N_, 0, 'Ciąg rozporządzalny śmigła',
               check=lambda v: 1000 * v.eta_p * v.P / v.V_z, tolerance=.002 * t['t_avail'])
    s.calc('n_T2', r'n_T^2', r'\frac{\frac{T_r}{W}q_z-\frac{q_z^2C_{x0}}{W/S}}{k\,W/S}', r'\frac{\frac{[[T_z]]}{[[m0]]\cdot[[g]]}\cdot[[q_z]]-\frac{[[q_z]]^2\cdot[[Cx0]]}{[[WS_0]]}}{[[k]]\cdot[[WS_0]]}',
           t['n_thrust_sq'], '', 3, 'Kwadrat przeciążenia zakrętu prawidłowego (T = D)', SOURCES['B1W'] + ', wzór (50)',
           check=lambda v: (v.T_z / (v.m0 * v.g) * v.q_z - v.q_z ** 2 * v.Cx0 / v.WS_0) / (v.k * v.WS_0), tolerance=.01 * abs(t['n_thrust_sq']) + 1e-3)
    s.calc('n_z', 'n', r'\min\left(n_{aero};\;\sqrt{n_T^2}\right)', r'\min\left([[n_aero]];\;\sqrt{[[n_T2]]}\right)', turn['n_sustained'], '', 2, 'Przeciążenie w zakręcie ustalonym',
           check=lambda v: min(v.n_aero, math.sqrt(max(0, v.n_T2))), tolerance=.006)
    s.calc('phi_z', r'\varphi', r'\arccos\frac{1}{n}', r'\arccos\frac{1}{[[n_z]]}', turn['bank_angle_deg'], DEG, 1, 'Kąt przechylenia', SOURCES['B1W'] + ', wzór (31)',
           check=lambda v: math.degrees(math.acos(1 / v.n_z)), tolerance=.2)
    if turn['r_min_m'] is not None:
        s.calc('R_z', 'r', r'\frac{V_z^2}{g\sqrt{n^2-1}}', r'\frac{[[V_z]]^2}{[[g]]\cdot\sqrt{[[n_z]]^2-1}}', turn['r_min_m'], M, 1, 'Promień zakrętu', SOURCES['B1W'] + ', wzór (34)',
               check=lambda v: v.V_z ** 2 / (v.g * math.sqrt(v.n_z ** 2 - 1)), tolerance=.01 * turn['r_min_m'] + .2)


# =============================================================================================
# P6 — obwiednia obciążeń
# =============================================================================================
def _p6(s, r):
    env = r['envelope']
    t, lim, sp, gf = env['terms'], env['limits'], env['speeds'], env['gust_factors']
    basis = t['load_basis']
    s.section('p6', 'loads', 'Współczynniki obciążeń dopuszczalnych', {'CS-22': SOURCES['CS22'], 'CS-25': SOURCES['CS25']}.get(lim['basis'], SOURCES['CS23']) + ' §.337')
    if basis in ('cs23_normal', 'cs23_commuter', 'cs25'):
        key = 'W_lb6'
        s.calc('W_lb6', 'W', r'2{,}20462\,m_0', r'2{,}20462\cdot[[m0]]', t['w_lb'], r'\mathrm{lb}', 0, 'Masa startowa w funtach',
               check=lambda v: 2.20462 * max(1, v.m0))
        s.calc('n_plus', r'n_+', r'\min\left(3{,}8;\;\max\left(2{,}5;\;2{,}1+\frac{24000}{W+10000}\right)\right)',
               rf'\min\left(3{{,}}8;\;\max\left(2{{,}}5;\;2{{,}}1+\frac{{24000}}{{[[{key}]]+10000}}\right)\right)', lim['n_max'], '', 2,
               'Dodatnie przeciążenie manewrowe', check=lambda v: min(3.8, max(2.5, 2.1 + 24000 / (v.W_lb6 + 10000))))
        if basis == 'cs25':
            s.given('n_minus', r'n_-', lim['n_min'], '', 2, 'Ujemne przeciążenie manewrowe', SOURCES['CS25'] + ' §25.337')
        else:
            s.calc('n_minus', r'n_-', r'-0{,}4\,n_+', r'-0{,}4\cdot[[n_plus]]', lim['n_min'], '', 2, 'Ujemne przeciążenie manewrowe',
                   check=lambda v: -.4 * v.n_plus)
    else:
        s.given('n_plus', r'n_+', lim['n_max'], '', 2, 'Dodatnie przeciążenie manewrowe', lim['load_factor_reference'])
        s.given('n_minus', r'n_-', lim['n_min'], '', 2, 'Ujemne przeciążenie manewrowe', lim['load_factor_reference'])
    s.given('nu', r'\nu', lim['safety_factor_nu'], '', 1, 'Współczynnik bezpieczeństwa', SOURCES['CS23'] + ' §23.303 / CS 22.303')

    s.section('p6', 'speeds', 'Prędkości obliczeniowe obwiedni (EAS)', lim['speed_rule'])
    s.calc('V_A', 'V_A', r'V_{S1}\sqrt{n_+}', r'[[V_S]]\cdot\sqrt{[[n_plus]]}', t['v_a_ms'], MS, 2, 'Prędkość manewrowa', check=lambda v: v.V_S * math.sqrt(v.n_plus), tolerance=.03)
    s.given('Cz_min', r'C_{z\,min}', t['cz_min'], '', 2, 'Najmniejszy (ujemny) współczynnik siły nośnej', 'Założenie')
    s.calc('V_G', 'V_G', r'V_{S1}\sqrt{|n_-|\frac{C_{z\,max}}{|C_{z\,min}|}}', r'[[V_S]]\cdot\sqrt{\left|[[n_minus]]\right|\cdot\frac{[[Cz_max]]}{\left|[[Cz_min]]\right|}}',
           t['v_g_ms'], MS, 2, 'Prędkość manewrowa ujemna', check=lambda v: v.V_S * math.sqrt(abs(v.n_minus) * v.Cz_max / abs(v.Cz_min)), tolerance=.03)
    if lim['basis'] == 'CS-22':
        s.calc('WS_daN', r'\left(\frac{W}{S}\right)_{daN}', r'\frac{W/S}{10}', r'\frac{[[WS_0]]}{10}', t['ws_dan'], r'\mathrm{daN/m^2}', 2, 'Obciążenie powierzchni w daN/m²',
               check=lambda v: v.WS_0 / 10)
        s.given('Cd_min', r'C_{d\,min}', t['cd_min'], '', 4, 'Najmniejszy współczynnik oporu', 'Biegunowa P4')
        if basis == 'cs22_utility':
            s.calc('V_D_rule', r'V_{D,min}', r'18\sqrt[3]{\frac{(W/S)_{daN}}{C_{d\,min}}}', r'18\cdot\sqrt[3]{\frac{[[WS_daN]]}{[[Cd_min]]}}', t['vd_rule_kmh'], KMH, 1,
                   'Najmniejsza prędkość nurkowania (kat. U)', 'CS 22.335(f)', check=lambda v: 18 * (v.WS_daN / v.Cd_min) ** (1 / 3))
        else:
            s.calc('V_D_rule', r'V_{D,min}', r'3{,}5\,(W/S)_{daN}+200', r'3{,}5\cdot[[WS_daN]]+200', t['vd_rule_kmh'], KMH, 1,
                   'Najmniejsza prędkość nurkowania (kat. A)', 'CS 22.335(f)', check=lambda v: 3.5 * v.WS_daN + 200)
        if 'V_max' in s.entries:
            s.calc('V_D', 'V_D', r'\max\left(\frac{V_{D,min}}{3{,}6};\;1{,}35\,V_H;\;V_A\right)', r'\max\left(\frac{[[V_D_rule]]}{3{,}6};\;1{,}35\cdot[[V_max]];\;[[V_A]]\right)',
                   t['v_d_ms'], MS, 2, 'Prędkość obliczeniowa nurkowania', check=lambda v: max(v.V_D_rule / 3.6, 1.35 * v.V_max, v.V_A), tolerance=.03)
        else:
            s.calc('V_D', 'V_D', r'\max\left(\frac{V_{D,min}}{3{,}6};\;V_A\right)', r'\max\left(\frac{[[V_D_rule]]}{3{,}6};\;[[V_A]]\right)', t['v_d_ms'], MS, 2,
                   'Prędkość obliczeniowa nurkowania', check=lambda v: max(v.V_D_rule / 3.6, v.V_A), tolerance=.03)
        s.calc('V_F', 'V_F', r'\max\left(1{,}4\,V_{S1};\;2{,}0\,V_{S0}\right)', r'\max\left(1{,}4\cdot[[V_S]];\;2{,}0\cdot[[V_S0]]\right)', t['v_f_ms'], MS, 2,
               'Prędkość obliczeniowa z wychyloną mechanizacją', 'CS 22.335(b)', check=lambda v: max(1.4 * v.V_S, 2 * v.V_S0), tolerance=.03)
        s.calc('V_B', 'V_B', 'V_A', '[[V_A]]', t['v_b_ms'], MS, 2, 'Prędkość podmuchu intensywnego (nie mniejsza niż VA)', 'CS 22.335(c)', check=lambda v: v.V_A)
    else:
        s.calc('WS_psf', r'\left(\frac{W}{S}\right)_{psf}', r'\frac{W/S}{47{,}88}', r'\frac{[[WS_0]]}{47{,}88026}', t['ws_psf'], r'\mathrm{lbf/ft^2}', 2,
               'Obciążenie powierzchni w lbf/ft²', check=lambda v: v.WS_0 / 47.88026)
        s.given('k_VC', r'k_{VC}', t['vc_factor_kts'], r'\mathrm{kt/\sqrt{psf}}', 2, 'Współczynnik prędkości przelotowej (33/36, malejący powyżej 20 psf)', SOURCES['CS23'] + ' §23.335(a)')
        s.calc('V_Cmin', r'V_{C,min}', r'0{,}514444\,k_{VC}\sqrt{(W/S)_{psf}}', r'0{,}514444\cdot[[k_VC]]\cdot\sqrt{[[WS_psf]]}', t['v_c_min_ms'], MS, 2,
               'Najmniejsza obliczeniowa prędkość przelotowa', check=lambda v: .514444 * v.k_VC * math.sqrt(max(1, v.WS_psf)))
        s.calc('V_cr_eas', r'V_{cr,EAS}', r'V_{cr}\sqrt{\sigma_H}', r'[[V_cr]]\cdot\sqrt{[[sigma_cr]]}', t['v_cr_eas_ms'], MS, 2, 'Prędkość przelotowa równoważna',
               check=lambda v: v.V_cr * math.sqrt(v.sigma_cr))
        if lim['basis'] == 'CS-25':
            s.calc('V_C', 'V_C', r'\max\left(V_{cr,EAS};\;1{,}02\,V_A\right)', r'\max\left([[V_cr_eas]];\;1{,}02\cdot[[V_A]]\right)', t['v_c_ms'], MS, 2,
                   'Obliczeniowa prędkość przelotowa', check=lambda v: max(v.V_cr_eas, 1.02 * v.V_A), tolerance=.03)
            s.calc('V_D', 'V_D', r'1{,}25\,V_C', r'1{,}25\cdot[[V_C]]', t['v_d_ms'], MS, 2, 'Obliczeniowa prędkość nurkowania (VD ≥ VC/0,8)', check=lambda v: 1.25 * v.V_C, tolerance=.03)
        else:
            if 'V_max' in s.entries:
                s.calc('V_C', 'V_C', r'\max\left(V_{cr,EAS};\;1{,}02\,V_A;\;\min\left(V_{C,min};\;0{,}9\,V_H\right)\right)',
                       r'\max\left([[V_cr_eas]];\;1{,}02\cdot[[V_A]];\;\min\left([[V_Cmin]];\;0{,}9\cdot[[V_max]]\right)\right)', t['v_c_ms'], MS, 2,
                       'Obliczeniowa prędkość przelotowa', check=lambda v: max(v.V_cr_eas, 1.02 * v.V_A, min(v.V_Cmin, .9 * v.V_max)), tolerance=.03)
            else:
                s.calc('V_C', 'V_C', r'\max\left(V_{cr,EAS};\;1{,}02\,V_A;\;V_{C,min}\right)', r'\max\left([[V_cr_eas]];\;1{,}02\cdot[[V_A]];\;[[V_Cmin]]\right)',
                       t['v_c_ms'], MS, 2, 'Obliczeniowa prędkość przelotowa', check=lambda v: max(v.V_cr_eas, 1.02 * v.V_A, v.V_Cmin), tolerance=.03)
            s.given('k_VD', r'k_{VD}', t['vd_factor'], '', 3, 'Współczynnik VD/VC,min (1,40 / 1,50 / 1,55, malejący powyżej 20 psf)', SOURCES['CS23'] + ' §23.335(b)')
            s.calc('V_D', 'V_D', r'\max\left(1{,}25\,V_C;\;k_{VD}V_{C,min}\right)', r'\max\left(1{,}25\cdot[[V_C]];\;[[k_VD]]\cdot[[V_Cmin]]\right)', t['v_d_ms'], MS, 2,
                   'Obliczeniowa prędkość nurkowania', check=lambda v: max(1.25 * v.V_C, v.k_VD * v.V_Cmin), tolerance=.03)
        if gf['vb_gust']:
            s.given('V_B', 'V_B', t['v_b_ms'], MS, 2, 'Prędkość VB: przecięcie linii przeciągnięcia z linią podmuchu 66 ft/s, ograniczone do VC',
                    SOURCES['CS23'] + ' §23.335(c)')
        s.calc('V_F', 'V_F', r'\max\left(1{,}4\,V_{S1};\;1{,}8\,V_{S0}\right)', r'\max\left(1{,}4\cdot[[V_S]];\;1{,}8\cdot[[V_S0]]\right)', t['v_f_ms'], MS, 2,
               'Prędkość obliczeniowa z wychyloną mechanizacją', SOURCES['CS23'] + ' §23.345', check=lambda v: max(1.4 * v.V_S, 1.8 * v.V_S0), tolerance=.03)
    for key in ('V_A', 'V_C', 'V_D', 'V_F', 'V_G'):
        if key in s.entries:
            _to_kmh(s, key + '_kmh', s.entries[key]['sym'], key, sp[{'V_A': 'v_a_kmh', 'V_C': 'v_c_kmh', 'V_D': 'v_d_kmh', 'V_F': 'v_f_kmh', 'V_G': 'v_g_kmh'}[key]],
                    s.entries[key]['label'])

    s.section('p6', 'gust', 'Obciążenia od podmuchów', gf['gust_basis'])
    chord_key = 'mac'
    if lim['basis'] == 'CS-22':
        s.calc('c_g', r'\bar c_g', r'\frac{S}{b}', r'\frac{[[S]]}{[[b]]}', gf['chord_m'], M, 3, 'Średnia cięciwa geometryczna', 'CS 22.341', check=lambda v: v.S / v.b, tolerance=.0011)
        chord_key = 'c_g'
    s.calc('mu_g', r'\mu_g', r'\frac{2\,m_0/S}{\rho_0\,\bar c\,a}', rf'\frac{{2\cdot[[m0]]/[[S]]}}{{[[rho0]]\cdot[[{chord_key}]]\cdot[[a_w]]}}', gf['mu_g'], '', 2,
           'Cecha masowa samolotu', SOURCES['D'] + ', wzór (2.14)', check=lambda v: 2 * v.m0 / v.S / (v.rho0 * getattr(v, chord_key) * v.a_w), tolerance=.03)
    s.calc('K_g', 'K_g', r'\frac{0{,}88\,\mu_g}{5{,}3+\mu_g}', r'\frac{0{,}88\cdot[[mu_g]]}{5{,}3+[[mu_g]]}', gf['k_g'], '', 3, 'Współczynnik łagodzenia podmuchu',
           SOURCES['D'] + ', wzór (2.13)', check=lambda v: .88 * v.mu_g / (5.3 + v.mu_g), tolerance=.0011)
    sailplane = lim['basis'] == 'CS-22'
    for gust in gf['gusts']:
        label = gust['speed']
        vkey = {'VB': 'V_B', 'VC': 'V_C', 'VD': 'V_D'}[label]
        u = 'U_' + label[1]
        s.given(u, f'U_{label[1]}', gust['u_ms'], MS, 2, f'Prędkość podmuchu przy {label}', gf['gust_basis'].split(':')[0])
        dn = gust['delta_n']
        if sailplane:
            s.calc('dn_' + label[1], rf'\Delta n_{label[1]}', r'\min\left(\frac{K_g\rho_0Va\,U}{2\,W/S};\;1{,}25\left(\frac{V}{V_{S1}}\right)^2-1\right)',
                   rf'\min\left(\frac{{[[K_g]]\cdot[[rho0]]\cdot[[{vkey}]]\cdot[[a_w]]\cdot[[{u}]]}}{{2\cdot[[WS_0]]}};\;1{{,}}25\cdot\left(\frac{{[[{vkey}]]}}{{[[V_S]]}}\right)^2-1\right)',
                   dn, '', 3, f'Przyrost przeciążenia od podmuchu przy {label}', 'CS 22.341',
                   check=lambda v, vk=vkey, uk=u: min(v.K_g * v.rho0 * getattr(v, vk) * v.a_w * getattr(v, uk) / (2 * v.WS_0), 1.25 * (getattr(v, vk) / v.V_S) ** 2 - 1),
                   tolerance=.004 + .01 * abs(dn))
        else:
            s.calc('dn_' + label[1], rf'\Delta n_{label[1]}', r'\frac{K_g\rho_0Va\,U}{2\,W/S}',
                   rf'\frac{{[[K_g]]\cdot[[rho0]]\cdot[[{vkey}]]\cdot[[a_w]]\cdot[[{u}]]}}{{2\cdot[[WS_0]]}}', dn, '', 3,
                   f'Przyrost przeciążenia od podmuchu przy {label}', SOURCES['D'] + ', wzory (2.10)–(2.13)',
                   check=lambda v, vk=vkey, uk=u: v.K_g * v.rho0 * getattr(v, vk) * v.a_w * getattr(v, uk) / (2 * v.WS_0), tolerance=.004 + .01 * abs(dn))
    keys = ['dn_' + g['speed'][1] for g in gf['gusts']]
    s.calc('n_g_max', r'n_{g,max}', r'1+\max_i\Delta n_i', r'1+\max\left\{' + ';\\;'.join(f'[[{k}]]' for k in keys) + r'\right\}', lim['n_gust_max'], '', 2,
           'Największe przeciążenie od podmuchu', check=lambda v: 1 + max(getattr(v, k) for k in keys), tolerance=.006)
    s.calc('n_g_min', r'n_{g,min}', r'1-\max_i\Delta n_i', r'1-\max\left\{' + ';\\;'.join(f'[[{k}]]' for k in keys) + r'\right\}', lim['n_gust_min'], '', 2,
           'Najmniejsze przeciążenie od podmuchu', check=lambda v: 1 - max(getattr(v, k) for k in keys), tolerance=.006)

    s.section('p6', 'design', 'Obciążenia do wymiarowania', SOURCES['D'] + ', rozdz. 2')
    s.calc('n_dim_p', r'n_{wym,+}', r'\max\left(n_+;\;n_{g,max}\right)', r'\max\left([[n_plus]];\;[[n_g_max]]\right)', lim['n_dimensioning_pos'], '', 2,
           'Dodatnie przeciążenie dopuszczalne do wymiarowania', check=lambda v: max(v.n_plus, v.n_g_max), tolerance=.006)
    s.calc('n_dim_m', r'n_{wym,-}', r'\min\left(n_-;\;n_{g,min}\right)', r'\min\left([[n_minus]];\;[[n_g_min]]\right)', lim['n_dimensioning_neg'], '', 2,
           'Ujemne przeciążenie dopuszczalne do wymiarowania', check=lambda v: min(v.n_minus, v.n_g_min), tolerance=.006)
    s.calc('n_ult_p', r'n_{niszcz,+}', r'\nu\,n_{wym,+}', r'[[nu]]\cdot[[n_dim_p]]', lim['n_ult_pos'], '', 2, 'Dodatnie przeciążenie niszczące',
           check=lambda v: v.nu * v.n_dim_p, tolerance=.006)
    s.calc('n_ult_m', r'n_{niszcz,-}', r'\nu\,n_{wym,-}', r'[[nu]]\cdot[[n_dim_m]]', lim['n_ult_neg'], '', 2, 'Ujemne przeciążenie niszczące',
           check=lambda v: v.nu * v.n_dim_m, tolerance=.006)

    flap = env['flap']
    s.section('p6', 'flaps', 'Obwiednia z wychyloną mechanizacją', SOURCES['CS23'] + ' §23.345 / CS 22.345')
    s.given('n_f', r'n_f', flap['n_flap'], '', 1, 'Przeciążenie z wychylonymi klapami', SOURCES['CS23'] + ' §23.345 / CS 22.345')
    v_af = next(pt['v_kmh'] for pt in flap['loop'] if pt['point'].startswith('Af'))
    s.calc('V_Af', r'V_{A,f}', r'3{,}6\,V_{S0}\sqrt{n_f}', r'3{,}6\cdot[[V_S0]]\cdot\sqrt{[[n_f]]}', v_af, KMH, 1, 'Wejście na przeciążenie nf z klapami',
           check=lambda v: 3.6 * v.V_S0 * math.sqrt(v.n_f), tolerance=.11)


# =============================================================================================
# Zapis kolejnych iteracji masy (BIPOL_1, s. 4) — punkt po punkcie
# =============================================================================================
def _t(value, digits=2):
    return tex_value(value, digits)


def _tw(value, digits):
    text = _t(value, digits)
    return rf'\left({text}\right)' if value < 0 else text


def _law_tex(trace, m0, fraction):
    """Udział masy pustego z równania (1): (wzór, podstawienie) dla masy m0."""
    law = trace['law']
    if law['mode'] == 'fixed_fraction':
        return r'\left(\frac{m_e}{m_0}\right)_{zał}', _t(fraction, 4)
    formula = r'A\left(m_0^{(k)}\right)^{C}K_{vs}'
    numbers = rf"{_t(law['A'], 5)}\cdot{_t(m0, 2)}^{{{_t(law['C'], 5)}}}\cdot{_t(law['k_vs'], 2)}"
    if law['mode'] == 'class_correlation':
        formula += 'K_{kor}'
        numbers += rf"\cdot{_t(law['modifier'], 4)}"
    return formula, numbers


def worked_iteration(trace, index):
    """Równania jednej iteracji (numeracja punktów jak w BIPOL_1) z podstawionymi liczbami."""
    rows = trace['rows']
    row = rows[index]
    k = row['k']
    steps = []

    def add(point, label, tex):
        steps.append(dict(point=point, label=label, tex=tex))

    unit = r'\;\mathrm{kg}'
    if index == 0:
        add('1' if trace['method'] == 'iterative' else '4', 'Założenie masy startowej: ' + trace['start_rule'],
            f"m_0^{{(1)}} = {_t(row['m0'], 1)}{unit}")
    else:
        prev = rows[index - 1]
        point = '1' if trace['method'] == 'iterative' else '4'
        if trace['method'] == 'iterative' and prev['rule'] == 'correction':
            add(point, 'Masa startowa skorygowana o różnicę mas poprzedniej iteracji (pkt 12)',
                f"m_0^{{({k})}} = m_0^{{({k - 1})}}-\\Delta^{{({k - 1})}} = {_t(prev['m0'], 2)}-{_tw(prev['delta'], 3)} = {_t(row['m0'], 2)}{unit}")
        elif trace['method'] == 'iterative':
            before = rows[index - 2]
            add(point, 'Masa startowa z prostej przez dwa ostatnie punkty (m₀, Δ), dla której Δ = 0 (pkt 12)',
                r'\begin{aligned}'
                + f"m_0^{{({k})}} &= m_0^{{({k - 1})}}-\\Delta^{{({k - 1})}}\\,\\frac{{m_0^{{({k - 1})}}-m_0^{{({k - 2})}}}}{{\\Delta^{{({k - 1})}}-\\Delta^{{({k - 2})}}}}"
                + r'\\'
                + f"&= {_t(prev['m0'], 2)}-{_tw(prev['delta'], 3)}\\cdot\\frac{{{_t(prev['m0'], 2)}-{_t(before['m0'], 2)}}}"
                  f"{{{_tw(prev['delta'], 3)}-{_tw(before['delta'], 3)}}} = {_t(row['m0'], 2)}{unit}"
                + r'\end{aligned}')
        elif prev['rule'] == 'secant':
            add(point, 'Przyspieszenie zbieżności: prosta przez dwa ostatnie przybliżenia', f"m_0^{{({k})}} = {_t(row['m0'], 2)}{unit}")
        else:
            add(point, f'Masa startowa: wynik wzoru (5) z iteracji {k - 1}', f"m_0^{{({k})}} = {_t(row['m0'], 2)}{unit}")
    if trace['method'] == 'iterative':
        _worked_mission(trace, row, add)
    else:
        _worked_proportion(trace, row, add)
        steps.sort(key=lambda step: int(step['point']))  # pkt 3 (udział paliwa) przed założeniem masy (pkt 4)
    return steps


def _worked_mission(trace, row, add):
    phases = {ph['key']: ph for ph in row['phases']}
    masses = row['masses']
    unit = r'\;\mathrm{kg}'
    names = {1: ('takeoff', 'po starcie'), 2: ('climb', 'po wznoszeniu i rozpędzaniu'), 3: ('cruise', 'po dolocie do celu'),
             5: ('return', 'po powrocie'), 6: ('loiter', 'po oczekiwaniu w kolejce do lądowania'), 7: ('landing', 'po lądowaniu i kołowaniu')}
    previous = row['m0']
    for i in range(1, 8):
        point = str(i + 1)
        if i == 4:
            task, drop = phases.get('task'), phases.get('drop')
            if task or drop:
                symbols, numbers = ['m_3'], [_t(masses['m3'], 2)]
                if task:
                    symbols.append('m_{f,zad}')
                    numbers.append(_t(task['fuel'], 2))
                if drop:
                    symbols.append('m_{zrzut}')
                    numbers.append(_t(drop['release'], 2))
                add(point, 'Masa po wykonaniu zadania (paliwo zadania i zrzut ładunku)',
                    'm_4 = ' + '-'.join(symbols) + ' = ' + '-'.join(numbers) + f" = {_t(masses['m4'], 2)}{unit}")
            else:
                add(point, 'Masa po wykonaniu zadania — misja bez zadania i zrzutu', f"m_4 = m_3 = {_t(masses['m4'], 2)}{unit}")
            previous = masses['m4']
            continue
        key, label = names[i]
        if key in phases:
            add(point, 'Masa ' + label,
                f"m_{i} = m_{i - 1}\\,\\frac{{m_{i}}}{{m_{i - 1}}} = {_t(previous, 2)}\\cdot{_t(phases[key]['ratio'], 5)} = {_t(masses[f'm{i}'], 2)}{unit}")
        else:
            add(point, 'Masa ' + label + ' — faza nie występuje', f"m_{i} = m_{i - 1} = {_t(masses[f'm{i}'], 2)}{unit}")
        previous = masses[f'm{i}']
    burn = row['m0'] - row['m_landing'] - trace['drop']
    add('9a', 'Paliwo spalone w misji',
        f"m_{{f,spal}} = m_0-m_7-m_{{zrzut}} = {_t(row['m0'], 2)}-{_t(row['m_landing'], 2)}-{_t(trace['drop'], 2)} = {_t(burn, 2)}{unit}")
    add('9b', 'Rezerwa paliwa i paliwo niezużywalne (k_rez − 1 = 0,06)',
        f"m_{{f,rez}} = (k_{{rez}}-1)\\,m_{{f,spal}} = {_t(trace['reserve_factor'] - 1, 2)}\\cdot{_t(burn, 2)} = {_t(row['reserve'], 3)}{unit}")
    add('9c', 'Masa samolotu pustego z misji: masa po lądowaniu bez ładunku, załogi i rezerwy paliwa',
        f"m_{{e,mis}} = m_7-(m_{{ład}}-m_{{zrzut}})-m_{{zał}}-m_{{f,rez}} = {_t(row['m_landing'], 2)}-{_t(trace['payload'] - trace['drop'], 2)}"
        f"-{_t(trace['crew'], 2)}-{_t(row['reserve'], 3)} = {_t(row['me_mission'], 2)}{unit}")
    formula, numbers = _law_tex(trace, row['m0'], row['empty_fraction'])
    add('10', 'Realistyczna masa pustego: zakładana masa startowa razy udział z równania (1)',
        f"m_{{e,tr}} = m_0^{{(k)}}\\,{formula} = {_t(row['m0'], 2)}\\cdot{numbers} = {_t(row['me_trend'], 2)}{unit}")
    criterion = r'\le 0{,}1\,\%' if row['relative'] <= trace['tolerance'] else r'> 0{,}1\,\%'
    add('11', 'Różnica mas pustego z punktów 9 i 10',
        f"\\Delta^{{({row['k']})}} = m_{{e,mis}}-m_{{e,tr}} = {_t(row['me_mission'], 2)}-{_t(row['me_trend'], 2)} = {_t(row['delta'], 3)}{unit}")
    add('11', 'Kryterium zgodności mas 0,1%',
        f"\\frac{{|\\Delta^{{({row['k']})}}|}}{{m_{{e,tr}}}} = \\frac{{{_t(abs(row['delta']), 3)}}}{{{_t(row['me_trend'], 2)}}} = {_t(100 * row['relative'], 4)}\\,\\%{criterion}")


def _worked_proportion(trace, row, add):
    k = row['k']
    unit = r'\;\mathrm{kg}'
    if trace['task_fuel']:
        fuel = f"\\frac{{m_f}}{{m_0}} = \\frac{{{_t(row['fuel'], 2)}}}{{{_t(row['m0'], 2)}}} = {_t(row['fuel_fraction'], 5)}"
    else:
        fuel = (f"\\frac{{m_f}}{{m_0}} = k_{{rez}}\\left(1-M_{{ff}}\\right) = {_t(trace['reserve_factor'], 2)}\\cdot\\left(1-{_t(row['mff'], 5)}\\right)"
                f" = {_t(row['fuel_fraction'], 5)}")
    add('3', 'Udział paliwa (wzór (4))', fuel)
    formula, numbers = _law_tex(trace, row['m0'], row['empty_fraction'])
    add('5', 'Udział masy pustego z równania (1)', f"\\frac{{m_e}}{{m_0}} = {formula} = {numbers} = {_t(row['empty_fraction'], 5)}")
    add('6', 'Nowa masa startowa ze wzoru (5)',
        f"m_0^{{({k + 1})}} = \\frac{{m_{{zał}}+m_{{ład}}}}{{1-\\dfrac{{m_f}}{{m_0}}-\\dfrac{{m_e}}{{m_0}}}}"
        f" = \\frac{{{_t(trace['useful'], 1)}}}{{1-{_t(row['fuel_fraction'], 5)}-{_t(row['empty_fraction'], 5)}}} = {_t(row['next_m0'], 2)}{unit}")
    criterion = r'\le 0{,}1\,\%' if row['relative'] <= trace['tolerance'] else r'> 0{,}1\,\%'
    add('7', 'Kryterium zgodności 0,1%',
        f"\\frac{{\\left|m_0^{{({k + 1})}}-m_0^{{({k})}}\\right|}}{{m_0^{{({k})}}}} = \\frac{{\\left|{_t(row['next_m0'], 2)}-{_t(row['m0'], 2)}\\right|}}"
        f"{{{_t(row['m0'], 2)}}} = {_t(100 * row['relative'], 4)}\\,\\%{criterion}")
