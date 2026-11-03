"""Wykresy sprawozdania, z których odczytano dane lub których wymagają opisy projektów.

Krzywe odczytywane w obliczeniach (Corke, Raymer, poprawki Glauerta, posuw optymalny śmigła)
rysuje się z tych samych tablic i wielomianów, których używa program, a odczytany punkt jest
zaznaczony. Wykres zawsze odpowiada więc wartości podstawionej do wzoru.
"""
import html
import math

from markupsafe import Markup

from calculations.bipol1 import CORKE, CX0_LABELS, RAYMER, RAYMER_LABELS, WETTED_EXAMPLES
from calculations.flight_model import propulsion_lapse
from calculations.report_document import report_number
from calculations.report_figures import FONT, HALO, INK, MUTED, line_chart


def _n(value, digits=2):
    return report_number(value, digits)


def _verticals(lines, height=300):
    """Pionowe linie odniesienia [(x, opis)] dla line_chart(extra=...)."""
    def draw(px, py):
        out = []
        for x, label in lines:
            out.append(f'<path d="M{px(x):.1f} 30V{height - 54}" stroke="{INK}" stroke-width="1" stroke-dasharray="4 3"/>'
                       f'<text x="{px(x) + 4:.1f}" y="40" font-size="11" fill="{INK}" {HALO}{FONT}>{html.escape(label)}</text>')
        return ''.join(out)
    return draw


def corke_chart(corke):
    """Rzędna W/W(M=0,1) w funkcji liczby Macha (oś logarytmiczna) z odczytami dla Mp i Mk."""
    m_top = max(1.0, 2.5 * max(corke['mach_start'], corke['mach_end']))
    curve = [(math.log10(m), w, f'M = {_n(m, 2)}: {_n(w, 3)}') for m, w in CORKE if m <= m_top * 1.001]
    ticks = [m for m in (.1, .2, .3, .5, .7, 1, 1.5, 2, 3, 5, 7, 9) if m <= m_top * 1.001]
    marks = [(math.log10(corke['mach_start']), corke['ordinate_start'], f"Mp = {_n(corke['mach_start'], 3)}"),
             (math.log10(corke['mach_end']), corke['ordinate_end'], f"Mk = {_n(corke['mach_end'], 3)}")]
    if abs(marks[0][0] - marks[1][0]) < .02:
        marks[1] = (marks[1][0], marks[1][1], marks[1][2].replace('Mk', 'Mk ≈ Mp; Mk'))
        marks = marks[1:]
    return line_chart([('Wykres Corke’a', 0, curve)], 'Wykres Corke’a dla wznoszenia i rozpędzania',
                      'Liczba Macha M (skala logarytmiczna)', 'Stosunek mas W / W(M = 0,1)',
                      x_ticks=[math.log10(m) for m in ticks], x_labels=[_n(m, 1) for m in ticks],
                      extra=dict(points=marks))


def raymer_chart(family, wetted_aspect, kmax, extrapolated=False):
    """Rys. 2 BIPOL_1: krzywa K_max(Λ_wet) dla grupy samolotów z odczytem projektu. Odczyt poza
    narysowaną krzywą leży na jej przedłużeniu K ∝ √Λ_wet (linia kreskowa)."""
    points = RAYMER[family]
    curve = [(x, y, f'{_n(x, 2)}: K = {_n(y, 1)}') for x, y in points]
    extra = dict(points=[(wetted_aspect, kmax, f'K_max = {_n(kmax, 1)}' + (' (przedłużenie)' if extrapolated else ''))])
    if extrapolated:
        x_end, y_end = points[0] if wetted_aspect < points[0][0] else points[-1]

        def extension(px, py):
            xs = [x_end + (wetted_aspect - x_end) * i / 24 for i in range(25)]
            path = ''.join(f'{"M" if not i else "L"}{px(x):.1f} {py(y_end * math.sqrt(x / x_end)):.1f}' for i, x in enumerate(xs))
            return f'<path d="{path}" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        extra['svg'] = extension
    return line_chart([(RAYMER_LABELS.get(family, family), 0, curve)],
                      'Maksymalna doskonałość w funkcji wydłużenia odniesionego do powierzchni omywanej',
                      'Λ / (S_wet / S)', 'K_max', extra=extra)


SWET_SHORT = {'flying_wing': 'latające skrzydło', 'delta_fighter': 'delta F-102', 'glider': 'szybowiec',
              'light_single': 'Cessna 150', 'twin_turboprop': 'King Air', 'fighter': 'F-104',
              'jet_transport': 'Boeing 747', 'bomber': 'B-47'}


def swet_scale_chart(value, example=None):
    """Rys. 1 BIPOL_1: S_wet/S typowych układów (wg Raymera) z wartością projektu; wyróżniony układ,
    z którego przyjęto wartość."""
    width, left, right, axis_y = 680, 40, 40, 120
    lo, hi = 2.0, 8.0

    def px(x):
        return left + (min(max(x, lo), hi) - lo) / (hi - lo) * (width - left - right)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 190" role="img" class="report-chart" '
           f'aria-label="Typowe wartości S_wet/S"><title>Typowe wartości S_wet/S</title>'
           f'<rect width="{width}" height="190" fill="#fff"/>'
           f'<path d="M{left} {axis_y}H{width - right}" stroke="{INK}" stroke-width="1.5"/>']
    for tick in range(2, 9):
        svg.append(f'<path d="M{px(tick):.1f} {axis_y - 5}V{axis_y + 5}" stroke="{INK}"/>'
                   f'<text x="{px(tick):.1f}" y="{axis_y + 20}" text-anchor="middle" font-size="11" fill="{MUTED}" {FONT}>{tick}</text>')
    for i, (key, (label, x)) in enumerate(WETTED_EXAMPLES.items()):
        y = axis_y - 18 - 16 * (i % 4)
        chosen = key == example
        color, weight = (INK, ' font-weight="bold"') if chosen else (MUTED, '')
        anchor = 'end' if x > 7 else 'start' if x < 2.5 else 'middle'
        svg.append(f'<circle cx="{px(x):.1f}" cy="{axis_y}" r="{4.5 if chosen else 3.5}" fill="{color}"/>'
                   f'<path d="M{px(x):.1f} {axis_y - 4}V{y + 4}" stroke="#b5b4ae" stroke-width="1"/>'
                   f'<text x="{px(x):.1f}" y="{y}" text-anchor="{anchor}" font-size="10" fill="{color}"{weight} {HALO}{FONT}>'
                   f'{html.escape(SWET_SHORT.get(key, label))} {_n(x, 2)}</text>')
    svg.append(f'<path d="M{px(value):.1f} {axis_y - 9}L{px(value) + 7:.1f} {axis_y + 40}L{px(value) - 7:.1f} {axis_y + 40}Z" fill="#eb6834"/>'
               f'<text x="{px(value):.1f}" y="{axis_y + 56}" text-anchor="middle" font-size="12" font-weight="bold" fill="{INK}" {FONT}>'
               f'projekt: S_wet/S = {_n(value, 2)}</text>'
               f'<text x="{width / 2:.1f}" y="184" text-anchor="middle" font-size="12" fill="{INK}" {FONT}>S_wet / S</text></svg>')
    return Markup(''.join(svg))


def glauert_charts(terms):
    """Poprawki Glauerta: τ₁, δ₁ w funkcji u = Λ/a∞ oraz τ₂, δ₂ w funkcji zbieżności λ."""
    u0, lam0 = terms['u_ratio'], terms['taper']
    top = max(2.5, u0 * 1.2)
    us = [top * i / 40 for i in range(41)]
    tau1 = lambda u: .023 * u ** 3 - .103 * u ** 2 + .25 * u  # noqa: E731
    delta1 = lambda u: max(.002, .0537 * u - .005)  # noqa: E731
    tau2 = lambda x: -.18 * x ** 5 + 1.52 * x ** 4 - 3.51 * x ** 3 + 3.50 * x ** 2 - 1.33 * x + .17  # noqa: E731
    delta2 = lambda x: -.43 * x ** 5 + 1.83 * x ** 4 - 3.06 * x ** 3 + 2.56 * x ** 2 - x + .148  # noqa: E731
    left = line_chart([('τ₁(u)', 0, [(u, tau1(u), f'u = {_n(u)}: τ₁ = {_n(tau1(u), 4)}') for u in us[::4]]),
                       ('δ₁(u)', 1, [(u, delta1(u), f'u = {_n(u)}: δ₁ = {_n(delta1(u), 4)}') for u in us[::4]])],
                      'Poprawki Glauerta w funkcji u', 'u = Λ / a∞', 'τ₁, δ₁',
                      x_ticks=[x for x in (0, .5, 1, 1.5, 2, 2.5, 3) if x <= top],
                      x_labels=[_n(x, 1) for x in (0, .5, 1, 1.5, 2, 2.5, 3) if x <= top],
                      extra=dict(points=[(u0, terms['tau_1'], f'τ₁ = {_n(terms["tau_1"], 4)}'),
                                         (u0, terms['delta_1'], f'δ₁ = {_n(terms["delta_1"], 4)}')]), height=280)
    lams = [i / 10 for i in range(11)]
    right = line_chart([('τ₂(λ)', 0, [(x, tau2(x), f'λ = {_n(x, 1)}: τ₂ = {_n(tau2(x), 4)}') for x in lams]),
                        ('δ₂(λ)', 1, [(x, delta2(x), f'λ = {_n(x, 1)}: δ₂ = {_n(delta2(x), 4)}') for x in lams])],
                       'Poprawki Glauerta w funkcji zbieżności', 'zbieżność λ = c_k / c_0', 'τ₂, δ₂',
                       x_ticks=lams, x_labels=[_n(x, 1) for x in lams],
                       extra=dict(points=[(lam0, terms['tau_2'], f'τ₂ = {_n(terms["tau_2"], 4)}'),
                                          (lam0, terms['delta_2'], f'δ₂ = {_n(terms["delta_2"], 4)}')]), height=280)
    return Markup(f'<div class="figure-pair">{left}{right}</div>')


def propeller_chart(selection):
    """Posuw optymalny J w funkcji współczynnika szybkobieżności C_D (krzywa największej sprawności)."""
    j_of = lambda cd: max(.45, min(1.35, .52 * max(.2, cd) ** .78))  # noqa: E731
    cd0 = selection['cd_dimensionless']
    top = max(2.5, cd0 * 1.3)
    cds = [.4 + (top - .4) * i / 20 for i in range(21)]
    return line_chart([('J dla największej sprawności', 0, [(c, j_of(c), f'C_D = {_n(c)}: J = {_n(j_of(c), 3)}') for c in cds])],
                      'Dobór śmigła: posuw optymalny w funkcji C_D', 'C_D = V (ρ / (N n²))^(1/5)', 'J = V / (n D)',
                      x_ticks=[x for x in (.5, 1, 1.5, 2, 2.5, 3, 3.5) if x <= top],
                      x_labels=[_n(x, 1) for x in (.5, 1, 1.5, 2, 2.5, 3, 3.5) if x <= top],
                      extra=dict(points=[(cd0, selection['j_opt'], f'J = {_n(selection["j_opt"], 3)}')]), height=270)


def power_speed_chart(propulsion, engine_kw):
    """Charakterystyka prędkościowa: moc rozporządzalna śmigła stałego i przestawialnego."""
    var, fixed = propulsion['table_5_1_variable_pitch'], propulsion['table_5_2_fixed_pitch']
    series = [('śmigło przestawialne', 0, [(r['v_kmh'], r['nr_kw'], f"{_n(r['v_kmh'], 0)} km/h: {_n(r['nr_kw'], 1)} kW") for r in var]),
              ('śmigło stałe', 1, [(r['v_kmh'], r['nr_kw'], f"{_n(r['v_kmh'], 0)} km/h: {_n(r['nr_kw'], 1)} kW") for r in fixed])]
    return line_chart(series, 'Moc rozporządzalna przy ziemi w funkcji prędkości', 'V [km/h]', 'N_r [kW]',
                      x_ticks=[r['v_kmh'] for r in var], hlines=[(engine_kw, f'moc silnika {_n(engine_kw, 1)} kW')], height=280)


def altitude_chart(params, top_m, cruise_speed_ms):
    """Charakterystyka wysokościowa: względna moc (ciąg) rozporządzalna φ(H)."""
    top = max(2000.0, math.ceil(top_m / 1000) * 1000)
    hs = [top * i / 10 for i in range(11)]
    jet = params['engine_type'] == 'jet'
    series = [('V = 0' if jet else 'φ(H)', 0, [(h, propulsion_lapse(params, h, 0.0), f'H = {_n(h, 0)} m: {_n(propulsion_lapse(params, h, 0.0), 3)}') for h in hs])]
    if jet:
        series.append(('prędkość przelotowa', 1, [(h, propulsion_lapse(params, h, cruise_speed_ms),
                                                   f'H = {_n(h, 0)} m: {_n(propulsion_lapse(params, h, cruise_speed_ms), 3)}') for h in hs]))
    return line_chart(series, 'Charakterystyka wysokościowa zespołu napędowego', 'Wysokość H [m]',
                      'Ciąg względny T(H)/T₀' if jet else 'Moc względna N(H)/N₀', x_ticks=hs[::2], height=270, y_floor=0)


def offer_charts(rows, ceilings):
    """Wykres ofertowy: prędkości charakterystyczne oraz w_y,max i γ_max w funkcji wysokości."""
    ok = []
    for r in rows:
        if r['wy_max_ms'] is None or r['v_min_kmh'] is None:
            continue
        r = dict(r)
        if r['wy_max_ms'] <= 1e-9 and r.get('v_wy_kmh'):
            # Na pułapie teoretycznym lot poziomy jest możliwy tylko z jedną prędkością.
            r['v_min_kmh'] = r['v_max_kmh'] = r['v_gamma_kmh'] = r['v_wy_kmh']
        ok.append(r)
    if not ok:
        return Markup('')
    hl = [(ceilings['ht_theoretical_m'], f"pułap teoretyczny {_n(ceilings['ht_theoretical_m'], 0)} m"),
          (ceilings['hp_service_m'], f"pułap praktyczny {_n(ceilings['hp_service_m'], 0)} m", 'start')]
    def pts(key, name):
        return [(r[key], r['h_m'], f"H = {_n(r['h_m'], 0)} m: {name} = {_n(r[key], 1)} km/h") for r in ok if r.get(key) is not None]
    speeds = line_chart([('V_min', 0, pts('v_min_kmh', 'V_min')), ('V przy γ_max', 1, pts('v_gamma_kmh', 'V_γ')),
                         ('V przy w_y,max', 2, pts('v_wy_kmh', 'V_w')), ('V_max', 3, pts('v_max_kmh', 'V_max'))],
                        'Wykres ofertowy — prędkości charakterystyczne', 'V [km/h TAS]', 'H [m]', hlines=hl, height=330,
                        y_floor=0)
    climb = line_chart([('w_y,max [m/s]', 0, [(r['wy_max_ms'], r['h_m'], f"H = {_n(r['h_m'], 0)} m: {_n(r['wy_max_ms'])} m/s") for r in ok]),
                        ('γ_max [°]', 1, [(r['gamma_max_deg'], r['h_m'], f"H = {_n(r['h_m'], 0)} m: {_n(r['gamma_max_deg'], 1)}°") for r in ok
                                          if r.get('gamma_max_deg') is not None])],
                       'Wykres ofertowy — wznoszenie', 'w_y,max [m/s], γ_max [°]', 'H [m]', hlines=hl, height=330,
                       y_floor=0)
    return speeds, climb


def mission_profile_chart(params, mass):
    """Schemat profilu misji: wysokość w kolejnych fazach (skala pozioma umowna)."""
    h = float(params['cruise_altitude_m'])
    keys = [ph['key'] for ph in mass['mission_phases']]
    low = .15 * h
    seq = [('start', 0.0)]
    seq.append(('wznoszenie', h))
    seq.append((f"przelot {_n(float(params['range_km']) - float(params.get('return_range_km') or 0), 0)} km", h))
    if 'task' in keys:
        seq.append(('zadanie', h))
    if 'drop' in keys:
        seq.append(('zrzut', h))
    if 'return' in keys:
        seq.append((f"powrót {_n(float(params.get('return_range_km') or 0), 0)} km", h))
    seq.append(('zniżanie', low))
    if 'loiter' in keys:
        seq.append((f"oczekiwanie {_n(float(params.get('loiter_time_min', 45)), 0)} min", low))
    seq.append(('lądowanie', 0.0))
    pts = [(i, alt, f'{label}: H = {_n(alt, 0)} m') for i, (label, alt) in enumerate(seq)]
    return line_chart([('Wysokość lotu', 0, pts)], 'Schemat profilu misji', 'Faza lotu (skala pozioma umowna)',
                      'Wysokość H [m]', x_ticks=[p[0] for p in pts], x_labels=[s[0] for s in seq], height=270, y_floor=0)


def cg_chart(states, limits=(25.0, 35.0)):
    """Masa samolotu w funkcji położenia środka masy dla kolejnych stanów załadowania."""
    pts = [(r['xcg_mac_pct'], r['mass_kg'], f"{r['name']}: {_n(r['xcg_mac_pct'], 1)}% ŚCA, {_n(r['mass_kg'], 0)} kg") for r in states]
    lines = [(limits[0], f'{_n(limits[0], 0)}% ŚCA'), (limits[1], f'{_n(limits[1], 0)}% ŚCA')]
    xs = [p[0] for p in pts] + [limits[0], limits[1]]
    lo, hi = min(xs) - 2, max(xs) + 2
    return line_chart([('Stany załadowania', 0, pts)], 'Położenie środka masy w stanach załadowania',
                      'Położenie środka masy x̄ [% ŚCA]', 'Masa samolotu [kg]',
                      x_ticks=[round(v) for v in range(int(lo), int(hi) + 1, 2)],
                      extra=dict(svg=_verticals(lines)), height=300, x_range=(lo, hi))


def glide_masses_chart(table, masses):
    """Biegunowe prędkości lotu ślizgowego dla trzech mas (dokładne wzory równowagi sił)."""
    masses = list(masses.values()) if isinstance(masses, dict) else list(masses)
    series = []
    for i in (1, 2, 3):
        pts = [(r[f'v{i}_kmh'], -r[f'w{i}_ms'], f"m = {_n(masses[i - 1], 0)} kg: V = {_n(r[f'v{i}_kmh'], 1)} km/h, w = {_n(r[f'w{i}_ms'])} m/s")
               for r in table]
        series.append((f'm = {_n(masses[i - 1], 0)} kg', i - 1, pts))
    return line_chart(series, 'Biegunowe prędkości dla trzech mas samolotu', 'V [km/h]', '−w [m/s]', height=300)


# ---------------------------------------------------------------------------------------------
# Tablice z literatury, z których program przyjmuje wartości (zamieszczane w sprawozdaniu)
# ---------------------------------------------------------------------------------------------
FLAP_LABELS = {'plain': 'klapa zwykła', 'split': 'klapa krokodylowa', 'single_slotted': 'klapa szczelinowa',
               'flaperon': 'klapolotka', 'fowler': 'klapa Fowlera', 'double_slotted': 'klapa dwuszczelinowa',
               'junkers': 'klapa Junkersa'}


def cx0_classes():
    from calculations.bipol1 import CX0_RANGES
    return [dict(key=key, label=CX0_LABELS.get(key, key), low=low, high=high) for key, (low, high) in CX0_RANGES.items()]


def flap_increments():
    from calculations.high_lift import FLAPS
    return [dict(key=key, label=FLAP_LABELS.get(key, key), dcz_to=v[0], dcz_l=v[1], dcx_to=v[2], dcx_l=v[3],
                 e_to=v[4], e_l=v[5]) for key, v in FLAPS.items() if key != 'none']


def schrenk_chart(points):
    """Rozkład obciążenia na półrozpiętości: z obrysu, eliptyczny i Schrenka (C_z = 1)."""
    series = [(label, slot, [(p['y'], p[key], f"y = {_n(p['y'])} m: {_n(p[key], 3)} m") for p in points])
              for slot, (label, key) in enumerate((('z obrysu', 'c_geom'), ('eliptyczny', 'c_ellip'), ('Schrenka', 'c_schrenk')))]
    return line_chart(series, 'Rozkład obciążenia płata wg Schrenka', 'y [m]', 'Cięciwa zastępcza [m]', height=280, y_floor=0)


def climb_chart(rows):
    """Prędkość wznoszenia w funkcji prędkości lotu przy ziemi (bilans mocy)."""
    pts = [(r['v_kmh'], r['w_ms'], f"{_n(r['v_kmh'], 0)} km/h: {_n(r['w_ms'])} m/s") for r in rows if r.get('w_ms') is not None]
    return line_chart([('Poziom morza', 0, pts)], 'Prędkość wznoszenia w funkcji prędkości lotu', 'V [km/h]', 'w_y [m/s]',
                      height=270, hlines=[(0.0, 'w_y = 0', 'start')])


def figure_ids(sheet, keys):
    """Rysunki, do których odwołuje się pochodzenie danych wejściowych podanych wielkości (kolejność wystąpienia)."""
    import re
    from calculations.report_origin import origin_text
    seen = []
    for key in keys:
        entry = sheet.entries.get(key)
        if entry is None:
            continue
        for item in [entry] + [sheet.entries[d] for d in entry['deps'] if not d.startswith('@') and d in sheet.entries]:
            if item['kind'] == 'given':
                for fid in re.findall(r'\{fig:([A-Za-z0-9_\-]+)\}', origin_text(item)):
                    if fid not in seen:
                        seen.append(fid)
    return seen


def preliminary_polar_chart(cx0, k, cz_max):
    """Szacunkowa biegunowa analityczna C_x = C_x0 + k·C_z²: oś C_x (OX) u góry, oś C_z skierowana w dół.

    Zaznaczono opór zerowy (C_z = 0) i punkt największej doskonałości — styczną z początku układu.
    """
    width, height, left, right, top, bottom = 680, 380, 70, 40, 44, 34
    cz_end = max(float(cz_max or 0), 1.2)
    cz_opt = math.sqrt(cx0 / k)
    cx_opt, kmax = 2 * cx0, cz_opt / (2 * cx0)
    cx_end = cx0 + k * cz_end ** 2
    _, x_step = _ticks(0, cx_end)
    _, y_step = _ticks(0, cz_end)
    x_max = math.ceil(cx_end / x_step - 1e-9) * x_step
    y_max = math.ceil(cz_end / y_step - 1e-9) * y_step
    plot_w, plot_h = width - left - right, height - top - bottom

    def px(cx):
        return left + cx / x_max * plot_w

    def py(cz):
        return top + cz / y_max * plot_h  # C_z rośnie w dół, poniżej osi OX

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" class="report-chart" '
           'aria-label="Szacunkowa biegunowa analityczna"><title>Szacunkowa biegunowa analityczna</title>',
           f'<rect width="{width}" height="{height}" fill="#fff"/>']
    x = 0.0
    while x <= x_max + 1e-12:
        svg.append(f'<path d="M{px(x):.1f} {top}V{top + plot_h}" stroke="#e3e3df"/>'
                   f'<text x="{px(x):.1f}" y="{top - 8}" text-anchor="middle" font-size="11" fill="{MUTED}" {FONT}>{_n(x, _decimals(x_step))}</text>')
        x += x_step
    y = 0.0
    while y <= y_max + 1e-12:
        svg.append(f'<path d="M{left} {py(y):.1f}H{left + plot_w}" stroke="#e3e3df"/>'
                   f'<text x="{left - 8}" y="{py(y) + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}" {FONT}>{_n(y, _decimals(y_step))}</text>')
        y += y_step
    # Osie: OX (C_x) u góry, OY (C_z) w dół, ze strzałkami.
    svg.append(f'<path d="M{left} {top}H{left + plot_w + 18}M{left + plot_w + 18} {top}l-7 -4v8z" stroke="{INK}" fill="{INK}" stroke-width="1.3"/>'
               f'<path d="M{left} {top}V{top + plot_h + 18}M{left} {top + plot_h + 18}l-4 -7h8z" stroke="{INK}" fill="{INK}" stroke-width="1.3"/>'
               f'<text x="{left + plot_w + 22}" y="{top + 4}" font-size="13" font-style="italic" fill="{INK}" {FONT}>C<tspan baseline-shift="sub" font-size="9">x</tspan></text>'
               f'<text x="{left + 8}" y="{top + plot_h + 16}" font-size="13" font-style="italic" fill="{INK}" {FONT}>C<tspan baseline-shift="sub" font-size="9">z</tspan></text>')
    points = [(cx0 + k * (cz_end * i / 60) ** 2, cz_end * i / 60) for i in range(61)]
    svg.append('<path d="' + ''.join(f'{"M" if i == 0 else "L"}{px(a):.1f} {py(b):.1f}' for i, (a, b) in enumerate(points))
               + '" fill="none" stroke="#2a78d6" stroke-width="2.2"/>')
    # Styczna z początku układu wyznacza największą doskonałość.
    t = min(1.35, x_max / cx_opt, y_max / cz_opt)
    svg.append(f'<path d="M{px(0):.1f} {py(0):.1f}L{px(cx_opt * t):.1f} {py(cz_opt * t):.1f}" stroke="{INK}" stroke-width="1" stroke-dasharray="5 4"/>')
    for (a, b, text, dy) in ((cx0, 0.0, f'C_x0 = {_n(cx0, 4)}', 18),
                             (cx_opt, cz_opt, f'K_max = {_n(kmax, 1)}  (C_z = {_n(cz_opt, 2)}; C_x = {_n(cx_opt, 4)})', -8)):
        svg.append(f'<circle cx="{px(a):.1f}" cy="{py(b):.1f}" r="5" fill="{INK}" stroke="#fff" stroke-width="2"/>'
                   f'<text x="{px(a) + 10:.1f}" y="{py(b) + dy:.1f}" font-size="11.5" font-weight="bold" fill="{INK}" {HALO}{FONT}>{_svg_sub(text)}</text>')
    svg.append('</svg>')
    return Markup(''.join(svg))


def _decimals(step):
    digits = 0
    while digits < 6 and abs(step * 10 ** digits - round(step * 10 ** digits)) > 1e-9:
        digits += 1
    return digits


def _svg_sub(text):
    """Indeksy dolne w tekście SVG: C_x0 → C<tspan>x0</tspan>."""
    import re
    return re.sub(r'([A-Za-z])_([A-Za-z0-9]+)', r'\1<tspan baseline-shift="sub" font-size="8.5">\2</tspan>', html.escape(text))


def _ticks(low, high, count=6):
    from calculations.report_figures import _nice_ticks
    return _nice_ticks(low, high, count)
