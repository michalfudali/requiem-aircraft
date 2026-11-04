"""Wykresy SVG schematu iteracji masy (BIPOL_1, s. 4) do sprawozdań; bez JS i sieci.

Paleta: trzy pierwsze sloty palety kategorycznej (walidowane dla wszystkich par);
każda seria ma też własny styl linii i kształt znacznika, więc wydruk czarno-biały
pozostaje czytelny. Wartości liczbowe są w tabeli iteracji obok wykresów.
"""
import html
import math

from markupsafe import Markup

from calculations.report_document import report_number

SERIES = (('#2a78d6', '', 'circle'), ('#eb6834', '6 4', 'square'), ('#1baf7a', '2 3', 'triangle'),
          ('#7b4fc9', '10 3 2 3', 'circle'), ('#8a6d1d', '1 3', 'square'))
INK, MUTED, GRID, SURFACE = '#1d1d1b', '#55544f', '#e3e3df', '#ffffff'
FONT = 'font-family="Arial, Helvetica, sans-serif"'
HALO = 'stroke="#ffffff" stroke-width="3" paint-order="stroke" '


def _num(value, digits=1):
    return report_number(value, digits)


def _nice_ticks(low, high, count=5):
    span = high - low or abs(high) or 1.0
    raw = span / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = math.floor(low / step) * step
    ticks, value = [], start
    while True:
        ticks.append(round(value, 10))
        if value >= high - step * 1e-9:
            return ticks, step
        value += step


def _marker(shape, x, y, color, title):
    tip = f'<title>{html.escape(title)}</title>'
    if shape == 'square':
        return (f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" rx="1" fill="{color}" '
                f'stroke="{SURFACE}" stroke-width="2">{tip}</rect>')
    if shape == 'triangle':
        return (f'<path d="M{x:.1f} {y - 5:.1f}L{x + 5:.1f} {y + 4:.1f}L{x - 5:.1f} {y + 4:.1f}Z" fill="{color}" '
                f'stroke="{SURFACE}" stroke-width="2">{tip}</path>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="{SURFACE}" stroke-width="2">{tip}</circle>'


def _legend(items, x, y):
    out, offset = [], 0
    for (label, slot) in items:
        color, dash, shape = SERIES[slot]
        out.append(f'<path d="M{x + offset:.1f} {y}h22" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
        out.append(_marker(shape, x + offset + 11, y, color, label))
        out.append(f'<text x="{x + offset + 28:.1f}" y="{y + 4}" font-size="11" fill="{INK}" {FONT}>{html.escape(label)}</text>')
        offset += 34 + 6.2 * len(label)
    return ''.join(out)


def line_chart(series, title, xlabel, ylabel, x_ticks=None, x_labels=None, log_y=False, hlines=(), extra=None,
               height=300, x_range=None, y_floor=None):
    """series: [(label, slot, [(x, y, tooltip), ...])]; jedna oś y, wspólne jednostki."""
    width, left, right, bottom = 680, 74, 24, 54
    top = 46 if len(series) > 1 else 28
    xs = [p[0] for _, _, pts in series for p in pts]
    ys = [p[1] for _, _, pts in series for p in pts] + [h[0] for h in hlines]
    if extra:
        xs += [p[0] for p in extra.get('points', [])]
        ys += [p[1] for p in extra.get('points', [])]
    xmin, xmax = (min(xs), max(xs)) if x_range is None else x_range
    if xmin == xmax:
        xmin, xmax = xmin - 1, xmax + 1
    if log_y:
        ys = [y for y in ys if y > 0]
        ymin, ymax = 10 ** math.floor(math.log10(min(ys))), 10 ** math.ceil(math.log10(max(ys)))
        if ymin == ymax:
            ymax *= 10
        ticks = [10 ** e for e in range(int(math.log10(ymin)), int(math.log10(ymax)) + 1)]
    else:
        ymin, ymax = min(ys), max(ys)
        pad = (ymax - ymin) * .08 or abs(ymax) * .05 or 1
        low = ymin - pad if y_floor is None else max(y_floor, ymin - pad)
        ticks, _ = _nice_ticks(low, ymax + pad)
        ymin, ymax = ticks[0], ticks[-1]
    xpad = (xmax - xmin) * .04
    x0, x1 = xmin - xpad, xmax + xpad
    plot_w, plot_h = width - left - right, height - top - bottom
    if x_ticks is None:
        x_ticks, step = _nice_ticks(xmin, xmax, 6)
        x_labels = [_num(x, 0 if step >= 1 else 1 if step >= .1 else 2) for x in x_ticks]

    def px(x):
        return left + (x - x0) / (x1 - x0) * plot_w

    def py(y):
        if log_y:
            y = max(y, ymin)
            return top + plot_h - (math.log10(y) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin)) * plot_h
        return top + plot_h - (y - ymin) / (ymax - ymin) * plot_h

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
           f'aria-label="{html.escape(title)}" class="report-chart"><title>{html.escape(title)}</title>',
           f'<rect x="0" y="0" width="{width}" height="{height}" fill="{SURFACE}"/>']
    for tick in ticks:
        label = (f'{tick * 100:g}'.replace('.', ',') + '%') if log_y else _num(tick, 0 if abs(ticks[-1] - ticks[0]) >= 20 else 2)
        svg.append(f'<path d="M{left} {py(tick):.1f}H{width - right}" stroke="{GRID}" stroke-width="1"/>'
                   f'<text x="{left - 8}" y="{py(tick) + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}" {FONT}>{label}</text>')
    for i, x in enumerate(x_ticks or []):
        if not x0 <= x <= x1:
            continue
        text = x_labels[i] if x_labels else _num(x, 0)
        svg.append(f'<text x="{px(x):.1f}" y="{top + plot_h + 18}" text-anchor="middle" font-size="11" fill="{MUTED}" {FONT}>'
                   f'{html.escape(text)}</text>')
    svg.append(f'<path d="M{left} {top + plot_h}H{width - right}" stroke="#9a9993" stroke-width="1"/>')
    for value, label, *anchor in hlines:
        at_start = anchor and anchor[0] == 'start'
        svg.append(f'<path d="M{left} {py(value):.1f}H{width - right}" stroke="{INK}" stroke-width="1" stroke-dasharray="4 3"/>'
                   f'<text x="{left + 4 if at_start else width - right - 4}" y="{py(value) - 5:.1f}" '
                   f'text-anchor="{"start" if at_start else "end"}" font-size="11" fill="{INK}" {HALO}{FONT}>'
                   f'{html.escape(label)}</text>')
    if extra:
        svg.append(extra.get('svg', lambda px, py: '')(px, py))
    for label, slot, pts in series:
        color, dash, shape = SERIES[slot]
        path = [f'{"M" if not i else "L"}{px(x):.1f} {py(y):.1f}' for i, (x, y, _) in enumerate(pts)]
        svg.append(f'<path d="{"".join(path)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
                   f'stroke-linecap="round" stroke-dasharray="{dash}"/>')
        for x, y, tip in pts:
            svg.append(_marker(shape, px(x), py(y), color, tip))
    if extra:
        for x, y, text in extra.get('points', []):
            svg.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="5.5" fill="{INK}" stroke="{SURFACE}" stroke-width="2">'
                       f'<title>{html.escape(text)}</title></circle><text x="{px(x) - 9:.1f}" y="{py(y) + 20:.1f}" text-anchor="end" '
                       f'font-size="11" font-weight="bold" fill="{INK}" {HALO}{FONT}>{html.escape(text)}</text>')
    if len(series) > 1:
        svg.append(_legend([(label, slot) for label, slot, _ in series], left, 16))
    svg.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 10}" text-anchor="middle" font-size="12" fill="{INK}" {FONT}>'
               f'{html.escape(xlabel)}</text><text transform="translate(16 {top + plot_h / 2:.1f}) rotate(-90)" '
               f'text-anchor="middle" font-size="12" fill="{INK}" {FONT}>{html.escape(ylabel)}</text></svg>')
    return Markup(''.join(svg))


def convergence_chart(trace):
    rows = trace['rows']
    ks = [row['k'] for row in rows]
    if trace['method'] == 'iterative':
        series = [('m₀⁽ᵏ⁾ zakładana', 0, [(r['k'], r['m0'], f"k={r['k']}: m₀ = {_num(r['m0'])} kg") for r in rows]),
                  ('mₑ z misji (pkt 9)', 1, [(r['k'], r['me_mission'], f"k={r['k']}: mₑ,mis = {_num(r['me_mission'])} kg") for r in rows]),
                  ('mₑ z zależności masy pustej (pkt 10)', 2, [(r['k'], r['me_trend'], f"k={r['k']}: mₑ,tr = {_num(r['me_trend'])} kg") for r in rows])]
    else:
        series = [('m₀⁽ᵏ⁾ zakładana', 0, [(r['k'], r['m0'], f"k={r['k']}: m₀⁽ᵏ⁾ = {_num(r['m0'])} kg") for r in rows]),
                  ('m₀⁽ᵏ⁺¹⁾ z równania bilansu masy', 1, [(r['k'], r['next_m0'], f"k={r['k']}: m₀⁽ᵏ⁺¹⁾ = {_num(r['next_m0'])} kg") for r in rows])]
    return line_chart(series, 'Zbieżność iteracji masy startowej', 'Numer iteracji k', 'Masa [kg]', x_ticks=ks,
                      hlines=[(trace['m0'], f"m₀ = {_num(trace['m0'])} kg")])


def error_chart(trace):
    rows = [r for r in trace['rows'] if r['relative'] > 0]
    if not rows:
        return Markup('')
    label = '|Δ| / mₑ,tr' if trace['method'] == 'iterative' else '|m₀⁽ᵏ⁺¹⁾ − m₀⁽ᵏ⁾| / m₀⁽ᵏ⁾'
    series = [(label, 0, [(r['k'], r['relative'], f"k={r['k']}: {r['relative'] * 100:.4g}%".replace('.', ',')) for r in rows])]
    return line_chart(series, 'Błąd względny kolejnych iteracji', 'Numer iteracji k', 'Błąd względny (skala logarytmiczna)',
                      x_ticks=[r['k'] for r in trace['rows']], log_y=True, hlines=[(trace['tolerance'], 'kryterium 0,1%')], height=260)


def secant_chart(trace):
    """Pkt 12 BIPOL_1: liniowa zależność m0(Δ) z dwóch iteracji wyznacza następne założenie."""
    rows = trace['rows']
    if trace['method'] != 'iterative' or len(rows) < 2:
        return Markup('')
    pts = [(r['m0'], r['delta'], f"k={r['k']}: m₀ = {_num(r['m0'])} kg, Δ = {_num(r['delta'], 2)} kg") for r in rows]

    def lines(px, py):
        out = []
        for a, b in zip(rows, rows[1:]):
            # Prosta przez (m0, Δ) dwóch iteracji, przedłużona do Δ = 0 (następne założenie).
            target = b['next_m0'] if b['rule'] == 'secant' else None
            end = target if target is not None else b['m0']
            out.append(f'<path d="M{px(a["m0"]):.1f} {py(a["delta"]):.1f}L{px(end):.1f} {py(0 if target is not None else b["delta"]):.1f}" '
                       f'stroke="#9a9993" stroke-width="1" stroke-dasharray="3 3" fill="none"/>')
        placed = []
        for r in rows:
            x, y = px(r['m0']), py(r['delta']) + (16 if r['delta'] >= 0 else -10)
            if any(abs(x - a) < 26 and abs(y - b) < 12 for a, b in placed):
                continue
            placed.append((x, y))
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="11" fill="{MUTED}" {HALO}{FONT}>k={r["k"]}</text>')
        return ''.join(out)
    return line_chart([('Δ = mₑ,mis − mₑ,tr', 0, pts)], 'Różnica mas pustego w funkcji zakładanej masy startowej',
                      'Zakładana masa startowa m₀ [kg]', 'Δ [kg]', x_ticks=_nice_ticks(min(r['m0'] for r in rows), max(r['m0'] for r in rows))[0],
                      hlines=[(0.0, 'Δ = 0', 'start')], extra=dict(svg=lines, points=[(trace['m0'], 0.0, f"m₀ = {_num(trace['m0'])} kg")]))


SHORT = {'takeoff': 'start', 'climb': 'wznosz.', 'cruise': 'przelot', 'task': 'zadanie', 'drop': 'zrzut',
         'return': 'powrót', 'loiter': 'oczekiw.', 'landing': 'lądow.'}


def mission_chart(phases, m0):
    """Masa samolotu po kolejnych fazach misji (ostatnia iteracja)."""
    pts = [(0, m0, f'start misji: {_num(m0)} kg')]
    labels = ['m₀']
    for i, ph in enumerate(phases, start=1):
        pts.append((i, ph['m_end'], f"{ph['label']}: {_num(ph['m_end'])} kg (Δm = {_num(ph['m_start'] - ph['m_end'])} kg)"))
        labels.append(SHORT.get(ph['key'], ph['key']))
    return line_chart([('Masa samolotu', 0, pts)], 'Masa samolotu po kolejnych fazach misji', 'Faza lotu (koniec fazy)',
                      'Masa [kg]', x_ticks=[p[0] for p in pts], x_labels=labels, height=270)


# ---------------------------------------------------------------------------------------
# Schemat blokowy
# ---------------------------------------------------------------------------------------
def _box(x, y, w, h, title, body, tone='#f4f6f8', border='#6d7a86'):
    lines = [body] if isinstance(body, str) else body
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{tone}" stroke="{border}" stroke-width="1"/>',
           f'<text x="{x + 8}" y="{y + 15}" font-size="11" font-weight="bold" fill="{INK}" {FONT}>{html.escape(title)}</text>']
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + 8}" y="{y + 30 + 13 * i}" font-size="10.5" fill="{INK}" {FONT}>{html.escape(line)}</text>')
    return ''.join(out)


def _arrow(points, label=None, label_at=None):
    d = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in points)
    out = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.2" marker-end="url(#arrowhead)"/>'
    if label:
        lx, ly = label_at
        out += f'<text x="{lx}" y="{ly}" font-size="10.5" fill="{INK}" {FONT}>{html.escape(label)}</text>'
    return out


def flow_diagram(trace):
    final = trace['final']
    law = trace['law']
    defs = (f'<defs><marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0L10 5L0 10z" fill="{INK}"/></marker></defs>')
    if trace['method'] == 'iterative':
        return _flow_iterative(trace, final, law, defs)
    return _flow_proportion(trace, final, law, defs)


def _diamond(cx, cy, half_w, text):
    return (f'<path d="M{cx} {cy - 38}L{cx + half_w} {cy}L{cx} {cy + 38}L{cx - half_w} {cy}Z" fill="#fff8ec" stroke="#a86621" stroke-width="1"/>'
            f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" font-size="11" font-weight="bold" fill="{INK}" {FONT}>{html.escape(text)}</text>'
            f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="10" fill="{MUTED}" {FONT}>(kryterium zbieżności)</text>')


def _svg_open(height, label, title, defs):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {height}" role="img" class="report-chart flow" '
            f'aria-label="{html.escape(label)}"><title>{html.escape(title)}</title>{defs}',
            f'<rect width="680" height="{height}" fill="{SURFACE}"/>']


def _flow_iterative(trace, final, law, defs):
    """Kolumna lewa: pkt 12 i 1–8 w dół; prawa: pkt 9–11 i warunek w górę."""
    m, n = final['masses'], final
    ph = {q['key']: q for q in final['phases']}
    ratio = lambda key: _num(ph[key]['ratio'], 5)  # noqa: E731
    task = ('task' in ph) or ('drop' in ph)
    steps = [
        ('1) Założenie masy startowej', f"m₀⁽ᵏ⁾ = {_num(n['m0'])} kg  (k = {n['k']})"),
        ('2) Masa po starcie', f"m₁ = m₀·{ratio('takeoff')} = {_num(m['m1'])} kg"),
        ('3) Masa po wznoszeniu i rozpędzaniu', f"m₂ = m₁·{ratio('climb')} = {_num(m['m2'])} kg"),
        ('4) Masa po dolocie do celu', f"m₃ = m₂·{ratio('cruise')} = {_num(m['m3'])} kg"),
        ('5) Masa po wykonaniu zadania', f"m₄ = m₃ − m_f,zad − m_zrzut = {_num(m['m4'])} kg" if task else 'bez zadania i zrzutu: m₄ = m₃'),
        ('6) Masa po powrocie', f"m₅ = m₄·{ratio('return')} = {_num(m['m5'])} kg" if 'return' in ph else 'bez odcinka powrotnego: m₅ = m₄'),
        ('7) Masa po oczekiwaniu', f"m₆ = m₅·{ratio('loiter')} = {_num(m['m6'])} kg"),
        ('8) Masa po lądowaniu i kołowaniu', f"m₇ = m₆·{ratio('landing')} = {_num(m['m7'])} kg"),
    ]
    bw, x1, x2 = 300, 20, 360
    svg = _svg_open(580, 'Schemat iteracji masy startowej, metoda iteracyjna', 'Schemat iteracyjnego wyznaczania masy startowej', defs)
    svg.append(_box(x1, 20, bw, 62, '12) Korekta masy startowej', ['k = 1:  m₀⁽²⁾ = m₀⁽¹⁾ − Δ⁽¹⁾',
                                                                    'k ≥ 2: m₀⁽ᵏ⁺¹⁾ = m₀⁽ᵏ⁾ − Δ⁽ᵏ⁾·(m₀⁽ᵏ⁾ − m₀⁽ᵏ⁻¹⁾)/(Δ⁽ᵏ⁾ − Δ⁽ᵏ⁻¹⁾)'],
                    tone='#fff8ec', border='#a86621'))
    tops = []
    for i, (title, body) in enumerate(steps):
        y = 104 + i * 58
        tops.append(y)
        svg.append(_box(x1, y, bw, 44, title, body, tone='#eef4fb' if i == 0 else '#f4f6f8'))
        svg.append(_arrow([(x1 + bw / 2, y - (22 if i == 0 else 14)), (x1 + bw / 2, y)]))
    cx = x2 + bw / 2
    y9 = tops[-1] + 22 - 31
    blocks = [
        (y9, '9) Masa pustego z misji', ['mₑ,mis = m₇ − m_ład,poz − m_zał − m_f,rez',
                                         f"= {_num(n['m_landing'])} − {_num(trace['payload'] - trace['drop'])} − {_num(trace['crew'])} − {_num(n['reserve'], 2)} = {_num(n['me_mission'])} kg"]),
        (y9 - 80, '10) Masa pustego z zależności statystycznej', [f"mₑ,tr = m₀·A·m₀^C·K_vs = m₀·{_num(n['empty_fraction'], 4)}", f"= {_num(n['me_trend'])} kg"]),
        (y9 - 160, '11) Różnica mas', [f"Δ = mₑ,mis − mₑ,tr = {_num(n['delta'], 3)} kg", f"|Δ|/mₑ,tr = {n['relative'] * 100:.4f}%".replace('.', ',')]),
    ]
    for y, title, body in blocks:
        svg.append(_box(x2, y, bw, 62, title, body))
    svg.append(_arrow([(x1 + bw, tops[-1] + 22), (x2, tops[-1] + 22)]))
    svg.append(_arrow([(cx, y9), (cx, y9 - 18)]))
    svg.append(_arrow([(cx, y9 - 80), (cx, y9 - 98)]))
    cy = y9 - 160 - 56
    svg.append(_arrow([(cx, y9 - 160), (cx, cy + 38)]))
    svg.append(_diamond(cx, cy, 120, '|Δ|/mₑ,tr ≤ 0,1% ?'))
    svg.append(_arrow([(cx - 120, cy), (340, cy), (340, 51), (x1 + bw, 51)], 'nie', (cx - 150, cy - 6)))
    svg.append(_arrow([(cx, cy - 38), (cx, 120 + 62)], 'tak', (cx + 6, cy - 44)))
    svg.append(_box(x2, 120, bw, 62, 'Wynik', [f"m₀ = {_num(trace['m0'])} kg po {trace['final_k']} iteracjach",
                                                f"kryterium 0,1% spełnione w iteracji {trace.get('converged_at') or '—'}"],
                    tone='#edf7f2', border='#2f8a5f'))
    svg.append(_box(x2, 20, bw, 82, 'Dane do iteracji', [f"m_zał = {_num(trace['crew'])} kg, m_ład = {_num(trace['payload'])} kg",
                                                         f"A = {_num(law['A'], 5)}, C = {_num(law['C'], 5)}, K_vs = {_num(law['k_vs'], 2)}",
                                                         f"k_rez = {_num(trace['reserve_factor'], 2)} (rezerwa i paliwo niezużywalne)",
                                                         f"m_zrzut = {_num(trace['drop'])} kg"], tone='#ffffff'))
    svg.append('</svg>')
    return Markup(''.join(svg))


def _flow_proportion(trace, final, law, defs):
    """Kolumna lewa: pkt 1–4 w dół; prawa: równanie (1), wzór (5) i warunek w górę."""
    first, n = trace['rows'][0], final
    bw, x1, x2 = 300, 20, 360
    svg = _svg_open(490, 'Schemat iteracji masy startowej, metoda proporcji', 'Schemat wyznaczania masy startowej metodą proporcji', defs)
    powered = trace.get('powered', True)
    load = 'm_zał + m_ład' if trace.get('payload') else 'm_zał'
    # Szybowiec nie ma paliwa: bez stosunków mas faz lotu i udziału paliwa.
    left = ([
        ('1) Stosunki mas w fazach lotu', ['mᵢ₊₁/mᵢ: start, wznoszenie, przelot,', 'oczekiwanie, lądowanie (tabela faz)']),
        ('2) Iloczyn stosunków', [f"M_ff = Π mᵢ₊₁/mᵢ = {_num(first['mff'], 5)}"]),
        ('3) Udział masy paliwa', [f"m_f/m₀ = {_num(trace['reserve_factor'], 2)}·(1 − M_ff) = {_num(first['fuel_fraction'], 5)}"]),
    ] if powered else [('1) Masa załogi' + (' i masa płatna' if trace.get('payload') else ''),
                        [f"{load} = {_num(trace['useful'])} kg", 'szybowiec bez paliwa'])]) + [
        ('4) Założenie masy startowej' if powered else '2) Założenie masy startowej',
         [f"m₀⁽¹⁾ = {_num(trace['start'])} kg", f"({trace['start_rule']})"]),
    ]
    offset = 4 - len(left)
    for i, (title, body) in enumerate(left):
        y = 20 + (i + offset) * 100
        svg.append(_box(x1, y, bw, 62, title, body, tone='#eef4fb' if i == len(left) - 1 else '#f4f6f8'))
        if i:
            svg.append(_arrow([(x1 + bw / 2, y - 38), (x1 + bw / 2, y)]))
    cx = x2 + bw / 2
    svg.append(_box(x2, 320, bw, 62, ('5)' if powered else '3)') + ' Udział masy pustego z zależności statystycznej', [f"mₑ/m₀ = A·(m₀⁽ᵏ⁾)^C·K_vs = {_num(n['empty_fraction'], 4)}",
                                                                               f"A = {_num(law['A'], 5)}, C = {_num(law['C'], 5)}, K_vs = {_num(law['k_vs'], 2)}"]))
    svg.append(_box(x2, 220, bw, 62, ('6)' if powered else '4)') + ' Nowa masa startowa z równania bilansu',
                    [f'm₀⁽ᵏ⁺¹⁾ = ({load})/(1 − m_f/m₀ − mₑ/m₀)' if powered else f'm₀⁽ᵏ⁺¹⁾ = ({load})/(1 − mₑ/m₀)',
                                                                         f"= {_num(trace['useful'])}/{_num(n['denominator'], 5)} = {_num(n['next_m0'])} kg"]))
    svg.append(_arrow([(x1 + bw, 351), (x2, 351)]))
    svg.append(_arrow([(cx, 320), (cx, 282)]))
    cy = 150
    svg.append(_arrow([(cx, 220), (cx, cy + 38)]))
    svg.append(_diamond(cx, cy, 136, '|m₀⁽ᵏ⁺¹⁾ − m₀⁽ᵏ⁾|/m₀⁽ᵏ⁾ ≤ 0,1% ?'))
    svg.append(_box(x2, 420, bw, 44, 'Następna iteracja', 'm₀⁽ᵏ⁾ := m₀⁽ᵏ⁺¹⁾,  k := k + 1', tone='#fff8ec', border='#a86621'))
    svg.append(_arrow([(cx + 136, cy), (672, cy), (672, 442), (x2 + bw, 442)], 'nie', (cx + 140, cy - 6)))
    svg.append(_arrow([(cx, 420), (cx, 382)]))
    svg.append(_arrow([(cx, cy - 38), (cx, 82)], 'tak', (cx + 6, cy - 44)))
    svg.append(_box(x2, 20, bw, 62, 'Wynik', [f"m₀ = {_num(trace['m0'])} kg po {trace['final_k']} iteracjach",
                                               f"kryterium 0,1% spełnione w iteracji {trace.get('converged_at') or '—'}"],
                    tone='#edf7f2', border='#2f8a5f'))
    svg.append('</svg>')
    return Markup(''.join(svg))


def mission_chart_for(trace, mass):
    """Fazy ostatniej iteracji (metoda iteracyjna) lub bilansu projektu (metoda proporcji)."""
    if trace['method'] == 'iterative':
        return mission_chart(trace['final']['phases'], trace['final']['m0'])
    phases = [dict(key=p['key'], label=p['phase'], m_start=p['mass_start_kg'], m_end=p['mass_end_kg'])
              for p in mass['mission_phases'] if p['key'] not in ('warmup', 'descent')]
    return mission_chart(phases, mass['m0'])
