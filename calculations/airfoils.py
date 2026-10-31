"""Rzędne profilu skrzydła do rysunku P3 o cięciwie c = 200 mm (BIPOL I, opis projektu 3).

Profile NACA 4- i 5-cyfrowe wyznacza się analitycznie (Abbott, von Doenhoff, „Theory of Wing
Sections”, rozdz. 6): rozkład grubości z zamkniętą krawędzią spływu (−0,1036 zamiast −0,1015)
i linia szkieletowa nałożona prostopadle. Pozostałe profile (Wortmann, NASA SC(2), Clark Y…)
nie mają wzoru — ich rzędne trzeba przepisać z katalogu; moduł je wtedy skaluje i rysuje.
Program nie podstawia innego profilu w miejsce nieznanego.
"""
import math
import re

CHORD_MM = 200.0
STATIONS_PCT = (0.0, 0.5, 1.25, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0,
                55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0)
# Linie szkieletowe serii 5-cyfrowej (C_z,proj = 0,3): położenie maks. ugięcia → (r, k₁).
MEAN_LINES_5 = {1: (0.0580, 361.4), 2: (0.1260, 51.640), 3: (0.2025, 15.957), 4: (0.2900, 6.643), 5: (0.3910, 3.230)}
CATALOGUES = ('Abbott, von Doenhoff „Theory of Wing Sections” / NACA Report 824 (profile NACA), '
              'F. X. Wortmann „Stuttgarter Profilkatalog” (profile FX), NASA TP 2969 (SC(2)), '
              'UIUC Airfoil Coordinates Database (pliki .dat)')


def _thickness(x, t):
    return 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)


def _camber_4(m, p):
    def line(x):
        if m == 0:
            return 0.0, 0.0
        if x < p:
            return m / p ** 2 * (2 * p * x - x ** 2), 2 * m / p ** 2 * (p - x)
        return m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x ** 2), 2 * m / (1 - p) ** 2 * (p - x)
    return line


def _camber_5(design_digit, position_digit):
    r, k1 = MEAN_LINES_5[position_digit]
    scale = design_digit / 2  # stałe dotyczą C_z,proj = 0,3, czyli pierwszej cyfry 2

    def line(x):
        if x < r:
            return (scale * k1 / 6 * (x ** 3 - 3 * r * x ** 2 + r ** 2 * (3 - r) * x),
                    scale * k1 / 6 * (3 * x ** 2 - 6 * r * x + r ** 2 * (3 - r)))
        return scale * k1 * r ** 3 / 6 * (1 - x), -scale * k1 * r ** 3 / 6
    return line


def parse_naca(name):
    """Opis profilu NACA z oznaczenia albo None, jeśli nie jest analitycznym profilem 4/5-cyfrowym."""
    match = re.fullmatch(r'\s*NACA[\s-]*(\d{4,5})\s*', str(name or ''), re.I)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 4:
        m, p, t = int(digits[0]) / 100, int(digits[1]) / 10, int(digits[2:]) / 100
        if not 0.01 <= t <= 0.40 or (m > 0) != (p > 0):
            raise ValueError(f'NACA {digits}: nieprawidłowe oznaczenie profilu 4-cyfrowego.')
        return dict(name=f'NACA {digits}', thickness=t, camber=_camber_4(m, p),
                    description=f'm = {m:.0%}, p = {p:.0%}, t/c = {t:.0%}')
    design, position, reflex, t = int(digits[0]), int(digits[1]), int(digits[2]), int(digits[3:]) / 100
    if reflex:
        raise ValueError(f'NACA {digits}: linia szkieletowa z odgięciem (trzecia cyfra 1) nie ma tu wzoru — '
                         'przepisz rzędne z katalogu.')
    if position not in MEAN_LINES_5 or not 1 <= design <= 6 or not 0.01 <= t <= 0.40:
        raise ValueError(f'NACA {digits}: nieprawidłowe oznaczenie profilu 5-cyfrowego.')
    return dict(name=f'NACA {digits}', thickness=t, camber=_camber_5(design, position),
                description=f'linia szkieletowa {digits[:3]}, C_z,proj = {0.15 * design:.2f}'.replace('.', ',')
                            + f', t/c = {t:.0%}')


def _surface_point(spec, x):
    yt = _thickness(x, spec['thickness'])
    yc, slope = spec['camber'](x)
    theta = math.atan(slope)
    return (x - yt * math.sin(theta), yc + yt * math.cos(theta)), (x + yt * math.sin(theta), yc - yt * math.cos(theta)), yt


def _pl(value, digits):
    return f'{value:.{digits}f}'.replace('.', ',').replace('-', '−')


def thin_airfoil(name, n=2000):
    """Teoria cienkiego profilu dla linii szkieletowej NACA: α₀ i c_m względem 1/4 cięciwy.

    α₀ = −(1/π)∫(dy_c/dx)(cos θ − 1)dθ,  c_m,c/4 = (π/4)(A₂ − A₁),  A_k = (2/π)∫(dy_c/dx)cos kθ dθ,
    x = (1 − cos θ)/2 (Anderson, „Fundamentals of Aerodynamics”, rozdz. 4); a∞ = 2π.
    """
    line = parse_naca(name)['camber']
    i0 = i1 = i2 = 0.0
    for k in range(n):
        theta = math.pi * (k + 0.5) / n
        slope = line((1 - math.cos(theta)) / 2)[1]
        i0 += slope * (math.cos(theta) - 1)
        i1 += slope * math.cos(theta)
        i2 += slope * math.cos(2 * theta)
    step = math.pi / n
    a1, a2 = 2 / math.pi * i1 * step, 2 / math.pi * i2 * step
    return dict(alpha0_deg=round(math.degrees(-i0 * step / math.pi), 3), cm_c4=round(math.pi / 4 * (a2 - a1), 4))


def naca_profile(name, chord_mm=CHORD_MM, dense=80):
    """Rzędne analitycznego profilu NACA w mm: tabela stacji i gęste punkty do rysunku."""
    spec = parse_naca(name)
    if spec is None:
        raise ValueError(f'„{name}” nie jest profilem NACA 4- ani 5-cyfrowym.')
    table = []
    for pct in STATIONS_PCT:
        (xu, yu), (xl, yl), yt = _surface_point(spec, pct / 100)
        table.append(dict(xc_pct=pct, xu_mm=round(xu * chord_mm, 2), yu_mm=round(yu * chord_mm, 2),
                          xl_mm=round(xl * chord_mm, 2), yl_mm=round(yl * chord_mm, 2),
                          thick_mm=round(2 * yt * chord_mm, 2)))
    xs = [(1 - math.cos(math.pi * i / dense)) / 2 for i in range(dense + 1)]  # zagęszczenie przy krawędziach
    points = [_surface_point(spec, x) for x in xs]
    upper = [(round(u[0] * chord_mm, 3), round(u[1] * chord_mm, 3)) for u, _, _ in points]
    lower = [(round(l[0] * chord_mm, 3), round(l[1] * chord_mm, 3)) for _, l, _ in points]
    thin = thin_airfoil(name)
    result = _result(spec['name'], upper, lower, table, chord_mm, kind='naca',
                     note=f"Profil {spec['name']} ({spec['description']}) wyznaczony analitycznie wg Abbotta i von Doenhoffa; "
                          "krawędź spływu domknięta. Współrzędne x górnej i dolnej powierzchni różnią się, "
                          "bo grubość odkłada się prostopadle do linii szkieletowej. "
                          f"Teoria cienkiego profilu: α₀ = {_pl(thin['alpha0_deg'], 2)}°, c_m,c/4 = {_pl(thin['cm_c4'], 4)} — "
                          "porównaj z danymi katalogowymi dla Twojej liczby Reynoldsa.")
    result['thin_airfoil'] = thin
    return result


def parse_coordinates(text):
    """Rzędne z pliku .dat (format Seliga lub Lednicera) → (nazwa, górna, dolna) od krawędzi natarcia, w częściach cięciwy."""
    if not isinstance(text, str) or len(text) > 60000:
        raise ValueError('Wklej rzędne profilu jako tekst (najwyżej 60 000 znaków).')
    name, rows = '', []
    for line in text.splitlines():
        parts = line.replace(';', ' ').replace('\t', ' ').split()
        try:
            values = [float(p.replace(',', '.')) for p in parts]
        except ValueError:
            values = None
        if values is not None and len(values) == 2:
            rows.append(tuple(values))
        elif values is None and not rows and line.strip():
            name = line.strip()[:80]
        elif line.strip() and rows:
            raise ValueError(f'Nie rozpoznano wiersza rzędnych: „{line.strip()[:40]}”.')
    if not rows:
        raise ValueError('Nie znaleziono par liczb x, y.')
    first = rows[0]
    if first[0] > 1.5 and first[1] > 1.5 and first[0].is_integer() and first[1].is_integer():
        n_upper, n_lower = int(first[0]), int(first[1])  # Lednicer: liczby punktów, potem obie powierzchnie od LE
        body = rows[1:]
        if len(body) != n_upper + n_lower:
            raise ValueError('Format Lednicera: liczba wierszy nie zgadza się z nagłówkiem.')
        upper, lower = body[:n_upper], body[n_upper:]
    else:
        if len(rows) < 10:
            raise ValueError('Za mało punktów: potrzeba co najmniej 10 par x, y.')
        nose = min(range(len(rows)), key=lambda i: rows[i][0])
        upper, lower = list(reversed(rows[:nose + 1])), rows[nose:]
    if len(upper) < 5 or len(lower) < 5 or len(upper) + len(lower) > 1200:
        raise ValueError('Każda powierzchnia musi mieć od 5 do 600 punktów.')
    x_le = min(p[0] for p in upper + lower)
    chord = max(p[0] for p in upper + lower) - x_le
    if chord <= 0:
        raise ValueError('Rzędne nie wyznaczają cięciwy.')
    norm = lambda pts: [((x - x_le) / chord, y / chord) for x, y in pts]  # noqa: E731 — także rzędne w % lub mm
    upper, lower = norm(upper), norm(lower)
    if sum(y for _, y in upper) / len(upper) < sum(y for _, y in lower) / len(lower):
        upper, lower = lower, upper
    return name, upper, lower


def profile_from_text(text, name='', chord_mm=CHORD_MM):
    """Profil z wklejonych rzędnych, przeskalowany do cięciwy 200 mm."""
    title, upper, lower = parse_coordinates(text)
    label = (name or title or 'Profil z wklejonych rzędnych').strip()[:80]
    scale = lambda pts: [(round(x * chord_mm, 3), round(y * chord_mm, 3)) for x, y in pts]  # noqa: E731
    up, lo = scale(upper), scale(lower)
    table = [dict(xc_pct=None, xu_mm=u[0], yu_mm=u[1], xl_mm=None, yl_mm=None, thick_mm=None) for u in up] + \
            [dict(xc_pct=None, xu_mm=None, yu_mm=None, xl_mm=l[0], yl_mm=l[1], thick_mm=None) for l in lo]
    return _result(label, up, lo, table, chord_mm, kind='pasted',
                   note=f'{label}: rzędne wklejone przez autora i przeskalowane do c = {chord_mm:.0f} mm. '
                        'Sprawdź ich źródło (katalog, strona) i podaj je w opracowaniu.')


def _interp(points, x):
    pts = sorted(points)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def _result(name, upper, lower, table, chord_mm, kind, note):
    xs = [chord_mm * i / 200 for i in range(201)]
    gaps = [(x, _interp(upper, x), _interp(lower, x)) for x in xs]
    gaps = [(x, u - l) for x, u, l in gaps if u is not None and l is not None]
    x_t, t_mm = max(gaps, key=lambda g: g[1]) if gaps else (None, None)
    return dict(name=name, kind=kind, chord_mm=chord_mm, upper=upper, lower=lower, table=table, note=note,
                thickness_pct=round(100 * t_mm / chord_mm, 2) if t_mm else None,
                thickness_x_pct=round(100 * x_t / chord_mm, 1) if t_mm else None,
                svg=airfoil_svg(name, upper, lower, chord_mm))


def airfoil_svg(name, upper, lower, chord_mm=CHORD_MM):
    """Rysunek profilu w milimetrach: wydrukowany w skali 100% ma cięciwę dokładnie chord_mm."""
    ys = [y for _, y in upper + lower]
    pad, top, bottom = 10.0, max(ys) + 14.0, min(ys) - 24.0
    width, height = chord_mm + 2 * pad, top - bottom
    pt = lambda x, y: f'{x:.2f},{-y:.2f}'  # noqa: E731 — oś y w górę
    outline = 'M ' + ' L '.join([pt(x, y) for x, y in reversed(upper)] + [pt(x, y) for x, y in lower[1:]]) + ' Z'
    bar_y = bottom + 12.0
    ticks = ''.join(f'<line x1="{10 * i}" y1="{-bar_y:.2f}" x2="{10 * i}" y2="{-bar_y + (2.5 if i % 5 else 4):.2f}"/>'
                    for i in range(11))
    safe = str(name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = 'font-family="sans-serif" fill="#334155"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="airfoil-200mm-svg" width="{width:.1f}mm" height="{height:.1f}mm" '
            f'viewBox="{-pad} {-top:.2f} {width:.2f} {height:.2f}" role="img" aria-label="Profil {safe}, cięciwa {chord_mm:.0f} mm">'
            f'<rect x="{-pad}" y="{-top:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#fff"/>'
            f'<line x1="-4" y1="0" x2="{chord_mm + 4}" y2="0" stroke="#94a3b8" stroke-width="0.2" stroke-dasharray="2 1.5"/>'
            f'<path d="{outline}" fill="none" stroke="#0f3d55" stroke-width="0.35" stroke-linejoin="round"/>'
            f'<g stroke="#334155" stroke-width="0.25"><line x1="0" y1="{-bar_y:.2f}" x2="100" y2="{-bar_y:.2f}"/>{ticks}</g>'
            f'<text x="0" y="{-bar_y + 7:.2f}" font-size="3.2" {text}>0</text>'
            f'<text x="100" y="{-bar_y + 7:.2f}" font-size="3.2" {text} text-anchor="middle">100 mm</text>'
            f'<text x="104" y="{-bar_y + 1.2:.2f}" font-size="3.2" {text}>sprawdź linijką po wydruku w skali 100%</text>'
            f'<text x="0" y="{-top + 6:.2f}" font-size="4" font-weight="bold" font-family="sans-serif" fill="#0f172a">'
            f'{safe} · c = {chord_mm:.0f} mm</text></svg>')


def airfoil_200mm(name='', coordinates=''):
    """Wejście API: wklejone rzędne mają pierwszeństwo, w przeciwnym razie profil NACA z oznaczenia."""
    if coordinates and coordinates.strip():
        return profile_from_text(coordinates, name)
    if parse_naca(name) is None:
        raise ValueError(f'Dla profilu „{name or "—"}” nie ma wzoru analitycznego. Wklej jego rzędne (plik .dat w formacie '
                         f'Seliga lub Lednicera) z katalogu: {CATALOGUES}.')
    return naca_profile(name)
