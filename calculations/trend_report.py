"""Small inline SVG plots for portable P1 reports; no network or JS required."""
import html
from markupsafe import Markup
from calculations.trends import predict


def trend_chart(analysis, mode, marks=()):
    """marks: odczyty z wykresu [(x, y, opis)] zaznaczane czarnymi punktami."""
    if mode == 'mass':
        points = [(r['m0'], r['empty_fraction'], r['model']) for r in analysis['similar_aircraft']
                  if r['empty_fraction'] is not None and .15 < r['empty_fraction'] < .95]
        fit = analysis['mass_fit']
        title, xlabel, ylabel = 'Korelacja masowa', 'MTOW [kg]', 'OEW / MTOW'
        forecast = None
    elif ':' in mode:
        xkey, ykey = mode.split(':', 1)
        trend = next(t for t in analysis['relationships'] if t['x_key'] == xkey and t['y_key'] == ykey)
        points = [(p['x'], p['y'], p['model']) for p in trend['points']]
        fit = trend['fit']
        title = f"{trend['y_label']} a {trend['x_label']}"
        xlabel, ylabel = f"{trend['x_label']} [{trend['x_unit']}]", f"{trend['y_label']} [{trend['y_unit']}]"
        forecast = None
    else:
        trend = next(t for t in analysis['time_trends'] if t['key'] == mode)
        points = [(p['x'], p['y'], p['model']) for p in trend['points']]
        fit = trend['fit']
        title, xlabel, ylabel = trend['label'], 'Rok certyfikacji', trend['unit']
        forecast = (trend['forecast_year'], trend['forecast']) if trend['forecast_accepted'] else None
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
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 290" role="img" aria-label="{html.escape(title)}" style="width:100%;max-height:290px"><title>{html.escape(title)}</title>']
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
    for xv, yv, model in points:
        svg.append(f'<circle cx="{x(xv):.2f}" cy="{y(yv):.2f}" r="3.5" fill="#5478a9"><title>{html.escape(model)}: {xv:g}; {yv:g}</title></circle>')
    for xv, yv, label in marks:
        svg.append(f'<circle cx="{x(xv):.2f}" cy="{y(yv):.2f}" r="5.5" fill="#1d1d1b" stroke="#fff" stroke-width="2"/>'
                   f'<text x="{x(xv) + 8:.2f}" y="{y(yv) - 8:.2f}" font-size="11" font-weight="bold" '
                   f'stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(label)}</text>')
    svg.append(f'<text x="340" y="284" text-anchor="middle" font-size="12">{html.escape(xlabel)}</text><text transform="translate(14 140) rotate(-90)" text-anchor="middle" font-size="12">{html.escape(ylabel)}</text></svg>')
    return Markup(''.join(svg))
