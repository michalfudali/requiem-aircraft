"""Small inline SVG plots for portable P1 reports; no network or JS required."""
import html
from markupsafe import Markup
from calculations.trends import predict


SCATTER_NOTE = ('Punkty o tej samej odciętej rozsunięto poziomo; '
                'opisy i regresja używają danych źródłowych.')


def _scatter_x_positions(points, project_x, left, right):
    """Spread repeated x values in SVG units only; keep source coordinates intact.

    Stable model order avoids a diagonal pattern along y. Limit each group to
    12 units either side and 40% of the distance to its closest neighbour.
    The browser uses the same layout in scatterXPositions.
    """
    positions = [project_x(p[0]) for p in points]
    groups = {}
    for i, point in enumerate(points):
        groups.setdefault(point[0], []).append(i)
    xs = sorted(groups)
    for k, value in enumerate(xs):
        indices = groups[value]
        if len(indices) < 2:
            continue
        center = project_x(value)
        spread = min(12, center - left - 4, right - center - 4)
        for neighbour in xs[max(0, k - 1):k] + xs[k + 1:k + 2]:
            spread = min(spread, abs(project_x(neighbour) - center) * .4)
        spread = max(0, spread)
        indices.sort(key=lambda i: (points[i][2], points[i][1]))
        for rank, i in enumerate(indices):
            positions[i] = center + spread * (2 * rank / (len(indices) - 1) - 1)
    return positions


def trend_chart(analysis, mode, marks=()):
    """marks: odczyty z wykresu [(x, y, opis)] zaznaczane czarnymi punktami."""
    similar = analysis.get('similar_aircraft', [])
    ac_index = {}
    for i, r in enumerate(similar, 1):
        if r.get('id'):
            ac_index[r['id']] = i
        if r.get('model'):
            ac_index[r['model']] = i

    if mode == 'mass':
        points = []
        for i, r in enumerate(similar, 1):
            if r.get('empty_fraction') is not None and .15 < r['empty_fraction'] < .95:
                num = r.get('position_num') or ac_index.get(r.get('id'), ac_index.get(r.get('model'), i))
                points.append((r['m0'], r['empty_fraction'], r['model'], num))
        fit = analysis.get('mass_fit')
        title, xlabel, ylabel = 'Korelacja masowa', 'MTOW [kg]', 'OEW / MTOW'
        forecast = None
    elif ':' in mode:
        xkey, ykey = mode.split(':', 1)
        trend = next(t for t in analysis.get('relationships', []) if t['x_key'] == xkey and t['y_key'] == ykey)
        points = []
        for i, p in enumerate(trend['points'], 1):
            num = p.get('num') or ac_index.get(p.get('id'), ac_index.get(p.get('model'), i))
            points.append((p['x'], p['y'], p['model'], num))
        fit = trend.get('fit')
        title = f"{trend['y_label']} a {trend['x_label']}"
        xlabel, ylabel = f"{trend['x_label']} [{trend['x_unit']}]", f"{trend['y_label']} [{trend['y_unit']}]"
        forecast = None
    else:
        trend = next(t for t in analysis.get('time_trends', []) if t['key'] == mode)
        points = []
        for i, p in enumerate(trend['points'], 1):
            num = p.get('num') or ac_index.get(p.get('id'), ac_index.get(p.get('model'), i))
            points.append((p['x'], p['y'], p['model'], num))
        fit = trend.get('fit')
        title, xlabel, ylabel = trend['label'], 'Rok certyfikacji', trend['unit']
        forecast = (trend['forecast_year'], trend['forecast']) if trend.get('forecast_accepted') else None
    if not points:
        return Markup('<p class="missing-chart">Brak kompletnych danych źródłowych do tej zależności. Wykres wymaga uzupełnienia próby.</p>')
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    if forecast:
        xmax = max(xmax, forecast[0]); ymin = min(ymin, forecast[1]); ymax = max(ymax, forecast[1])
    padx, pady = (xmax-xmin)*.05 or 1, (ymax-ymin)*.1 or .1
    xmin -= padx; xmax += padx; ymin -= pady; ymax += pady
    def x(value): return 65+(value-xmin)/(xmax-xmin)*555
    def y(value): return 240-(value-ymin)/(ymax-ymin)*215
    positions = _scatter_x_positions(points, x, 65, 620)
    spread = any(abs(px - x(p[0])) > 1e-6 for p, px in zip(points, positions))
    height = 310 if spread else 290
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 {height}" role="img" aria-label="{html.escape(title)}" style="width:100%;max-height:{height}px"><title>{html.escape(title)}</title>']
    for i in range(5):
        xv, yv = xmin+(xmax-xmin)*i/4, ymin+(ymax-ymin)*i/4
        xtick = f'{xv:.2f}' if abs(xv) < 10 else f'{xv:.0f}'
        svg.append(f'<path d="M{x(xv):.2f} 25V240M65 {y(yv):.2f}H620" stroke="#d6e2e6" stroke-dasharray="3 4"/><text x="{x(xv):.2f}" y="260" text-anchor="middle" font-size="11">{xtick.replace(".", ",")}</text><text x="58" y="{y(yv)+4:.2f}" text-anchor="end" font-size="11">{format(yv, ".3g").replace(".", ",")}</text>')
    if fit:
        path = []
        for i in range(51):
            xv = fit['x_min']+(fit['x_max']-fit['x_min'])*i/50
            path.append(f'{"M" if i == 0 else "L"}{x(xv):.2f} {y(predict(fit,xv)):.2f}')
        svg.append(f'<path d="{" ".join(path)}" fill="none" stroke="#168c83" stroke-width="2"/>')
        if forecast:
            svg.append(f'<path d="M{x(fit["x_max"]):.2f} {y(predict(fit,fit["x_max"])):.2f}L{x(forecast[0]):.2f} {y(forecast[1]):.2f}" stroke="#a86621" stroke-dasharray="5 3" fill="none"/>')
    for (xv, yv, model, num), px in zip(points, positions):
        py_y = y(yv)
        svg.append(f'<circle cx="{px:.2f}" cy="{py_y:.2f}" r="3.5" fill="#5478a9"><title>{html.escape(model)}: {xv:g}; {yv:g}</title></circle>')
        anchor = "end" if px > 595 else "start"
        tx = px - 5 if px > 595 else px + 5
        svg.append(f'<text x="{tx:.2f}" y="{py_y - 4:.2f}" font-size="8.5" font-weight="bold" fill="#1e3a8a" stroke="#ffffff" stroke-width="2.5" paint-order="stroke" text-anchor="{anchor}" data-point-num="{num}">{num}</text>')
    for xv, yv, label in marks:
        at_right = x(xv) > 560
        svg.append(f'<circle cx="{x(xv):.2f}" cy="{y(yv):.2f}" r="5.5" fill="#1d1d1b" stroke="#fff" stroke-width="2"/>'
                   f'<text x="{x(xv) + (-8 if at_right else 8):.2f}" y="{y(yv) - 8:.2f}" text-anchor="{"end" if at_right else "start"}" font-size="11" font-weight="bold" '
                   f'stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(label)}</text>')
    svg.append(f'<text x="340" y="284" text-anchor="middle" font-size="12">{html.escape(xlabel)}</text><text transform="translate(14 140) rotate(-90)" text-anchor="middle" font-size="12">{html.escape(ylabel)}</text>')
    if spread:
        svg.append(f'<text x="340" y="304" text-anchor="middle" font-size="9" fill="#55544f">{SCATTER_NOTE}</text>')
    svg.append('</svg>')
    return Markup(''.join(svg))
