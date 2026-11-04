"""Human-readable arithmetic for the very observations and weights used by P1.

No second catalogue, rounding of inputs, or independent regression is introduced.
"""
import math

from calculations.report_document import tex_number
from calculations.trends import BIPOL_1_AVERAGES, METRICS, SUGGESTION_SPECS, sample_weights, valid_value


def regression_working(points, weights, fit, forecast_year=None):
    if not fit:
        return None
    power = fit['kind'] == 'power'
    xy = [(math.log(x), math.log(y)) if power else (x, y) for x, y in points]
    total = sum(weights)
    sx = sum(w * x for (x, y), w in zip(xy, weights))
    sy = sum(w * y for (x, y), w in zip(xy, weights))
    xm, ym = sx / total, sy / total
    sxx = sum(w * (x - xm) ** 2 for (x, y), w in zip(xy, weights))
    sxy = sum(w * (x - xm) * (y - ym) for (x, y), w in zip(xy, weights))
    syy = sum(w * (y - ym) ** 2 for (x, y), w in zip(xy, weights))
    residual = sum(w * (y - fit['intercept'] - fit['slope'] * x) ** 2 for (x, y), w in zip(xy, weights))
    f = tex_number
    constrained = bool(fit.get('physically_constrained'))
    slope_line = (rf'a_{{MNK}}=\frac{{S_{{xy}}}}{{S_{{xx}}}}={f(sxy/sxx, 8)},\qquad '
                  rf'a=C_{{przyj}}={f(fit["slope"], 8)}') if constrained else (
                  rf'a=\frac{{S_{{xy}}}}{{S_{{xx}}}}=\frac{{{f(sxy, 6)}}}{{{f(sxx, 6)}}}={f(fit["slope"], 8)}')
    lines = [
        rf'\bar x=\frac{{\sum w_i x_i}}{{\sum w_i}}=\frac{{{f(sx, 5)}}}{{{f(total, 5)}}}={f(xm, 6)}',
        rf'\bar y=\frac{{\sum w_i y_i}}{{\sum w_i}}=\frac{{{f(sy, 5)}}}{{{f(total, 5)}}}={f(ym, 6)}',
        rf'S_{{xx}}=\sum w_i(x_i-\bar x)^2={f(sxx, 6)}',
        rf'S_{{xy}}=\sum w_i(x_i-\bar x)(y_i-\bar y)={f(sxy, 6)}',
        slope_line,
        rf'b=\bar y-a\bar x={f(ym, 6)}-({f(fit["slope"], 8)})\cdot {f(xm, 6)}={f(fit["intercept"], 8)}',
    ]
    if fit['r2'] is not None:
        lines += [rf'R^2=1-\frac{{\sum w_i(y_i-b-a x_i)^2}}{{\sum w_i(y_i-\bar y)^2}}'
                  rf'=1-\frac{{{f(residual, 8)}}}{{{f(syy, 8)}}}={f(fit["r2"], 4)}']
    if power:
        lines += [rf'C=a={f(fit["C"], 6)},\qquad A=\exp(b)=\exp({f(fit["intercept"], 8)})={f(fit["A"], 6)}']
    elif forecast_year is not None:
        value = fit['intercept'] + fit['slope'] * forecast_year
        lines += [rf'\hat y({forecast_year})=\bar y+a({forecast_year}-\bar x)'
                  rf'={f(ym, 6)}+({f(fit["slope"], 8)})\cdot({forecast_year}-{f(xm, 6)})={f(value, 4)}']
    return {'lines': lines, 'slope': fit['slope'], 'intercept': fit['intercept'],
            'unconstrained_slope': sxy/sxx, 'constrained': constrained,
            'sum_weights': total, 'n': len(points), 'power': power}


def report_trend_workings(analysis):
    rows = analysis['similar_aircraft']
    weights = sample_weights(analysis['weighting'])
    averages = []
    for key in BIPOL_1_AVERAGES:
        subset = [r for r in rows if valid_value(key, r)]
        sw = weights(subset)
        label, unit = METRICS[key]
        total = sum(sw)
        value = sum(r[key] * w for r, w in zip(subset, sw)) / total if total else None
        digits = 4 if key == 'v_v' else 3
        formula = (rf'\bar x=\frac{{\sum w_i x_i}}{{\sum w_i}}='
                   rf'\frac{{{tex_number(sum(r[key] * w for r, w in zip(subset, sw)), 5)}}}{{{tex_number(total, 5)}}}'
                   rf'={tex_number(value, digits)}') if total else None
        averages.append(dict(key=key, label=label, unit=unit, n=len(subset), value=value, formula=formula))
    charts = {}
    for chart in analysis['report_charts']:
        mode = chart['mode']
        if chart['kind'] == 'mass':
            subset = [r for r in rows if valid_value('empty_fraction', r)]
            points = [(r['m0'], r['empty_fraction']) for r in subset]
        elif chart['kind'] == 'time':
            key = mode
            basis = 'production' if analysis['year_basis'] == 'Rok produkcji' else 'certification'
            subset = [r for r in rows if r.get('year') is not None and
                      (r.get('year_basis') or 'certification') == basis and valid_value(key, r)]
            points = [(r['year'], r[key]) for r in subset]
        else:
            x, y = mode.split(':')
            subset = [r for r in rows if r.get(x) is not None and r.get(y) is not None
                      and not (x == 'ar' and not 2 <= r['ar'] <= 60)]
            points = [(r[x], r[y]) for r in subset]
        charts[mode] = regression_working(points, weights(subset), chart['fit'],
                                         analysis['forecast_year'] if chart['kind'] == 'time' else None)
    adopted = []
    for key in ('ws', 'ar', 'me_m0', 'pw', 'tw'):
        item = analysis['suggestions'][key]
        if item['provenance']:
            extra = None
            if item['model_type'] == 'time_trend':
                metric = next(spec[1] for spec in SUGGESTION_SPECS if spec[0] == key)
                if metric not in charts:
                    obs = item['provenance']['observations']
                    extra = regression_working([(o['x'], o['value']) for o in obs], [o['weight'] for o in obs],
                                               item['provenance']['fit'], analysis['forecast_year'])
            # The handout already requires the mean empty fraction in the averages table.
            if key != 'me_m0' or item['model_type'] != 'mean':
                adopted.append(dict(item, report_key=key, working=extra))
    # Include the actual source values of every plotted relation, without exporting
    # the catalogue's unrelated fields. The primary sample table already gives m0/ar.
    keys = []
    for chart in analysis['report_charts']:
        selected = ([chart['mode']] if chart['kind'] == 'time' else
                    chart['mode'].split(':') if chart['kind'] == 'relation' else [])
        for key in selected:
            if key not in ('ar', 'empty_fraction', 'm0') and key not in keys:
                keys.append(key)
    for spec in SUGGESTION_SPECS:
        if spec[0] in ('ws', 'ar', 'pw', 'tw') and analysis['suggestions'][spec[0]]['provenance'] and spec[1] not in keys:
            keys.append(spec[1])
    columns = [dict(key=k, label=METRICS[k][0], unit=METRICS[k][1]) for k in keys]
    return {'averages': averages, 'charts': charts, 'adopted': adopted,
            'reference_groups': [columns[i:i + 3] for i in range(0, len(columns), 3)]}
