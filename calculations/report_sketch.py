"""An honest, portable configuration sketch, without drawing-office placeholders."""
import html
import math
from markupsafe import Markup


def report_sketch(result, view='three', dimensions=True):
    """dimensions=False: szkic układu bez wymiarów (projekt koncepcyjny, przed wymiarowaniem)."""
    g, p = result['geometry'], result['params']
    w, f = g['wing'], g['fuselage']
    ht, vt = g['horizontal_tail'], g['vertical_tail']
    length, span, diameter = f['length'], w['b'], f['diameter']
    xwing = result['balance']['x_le_wing_m']
    sweep = math.tan(math.radians(w['sweep_deg']))
    height = 335 if view == 'top' else 510
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 {height}" role="img" '
           'aria-label="Schemat konfiguracji płatowca"><title>Konfiguracja płatowca</title>',
           f'<rect width="660" height="{height}" fill="white"/>']

    def path(points, fill='#f2f3f2', close=True):
        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.2f},{y:.2f}' for i, (x, y) in enumerate(points))
        out.append(f'<path d="{d}{"Z" if close else ""}" fill="{fill}" stroke="#333" stroke-width="1.1"/>')

    def label(x, y, text, size=12):
        out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial, sans-serif" '
                   f'font-size="{size}" fill="#333">{html.escape(text)}</text>')

    scale = min(570 / span, 265 / (length + .3))
    top = lambda x, y: (330 + y * scale, 30 + x * scale)
    # Chords are sampled from the actual selected planform, including elliptical/compound wings.
    points = g['schrenk']
    for sign in (-1, 1):
        leading, trailing = [], []
        for station in points:
            y, chord = station['y'], station['c_geom']
            x = xwing + y * sweep + .25 * (w['cr'] - chord)
            leading.append(top(x, sign * y))
            trailing.append(top(x + chord, sign * y))
        path(leading + trailing[::-1])
        tailac = ht['x_ac_m']
        path([top(tailac-.25*ht['cr_h'], 0), top(tailac-.25*ht['ct_h'], sign*ht['b_h']/2),
              top(tailac+.75*ht['ct_h'], sign*ht['b_h']/2), top(tailac+.75*ht['cr_h'], 0)])
    stations = [(0, 0), (.12, .33), (.3, .5), (.5, .46), (.75, .22), (1, .02)]
    path([top(x * length, sign * width * diameter) for sign in (-1, 1)
          for x, width in (stations if sign == -1 else stations[::-1])], '#fff')
    path([top(length - vt['cr_v'], 0), top(length, 0)], 'none', False)
    if p['engine_type'] == 'prop':
        xprop = -.08 if p.get('engine_location', 'nose') == 'nose' else length * .85
        propd = result['bipol_projects']['p3']['blueprint_checks']['propeller_diameter_m']
        path([top(xprop, -propd / 2), top(xprop, propd / 2)], 'none', False)
    label(330, 319, f'Rzut z góry · b = {round(span * 1000)} mm' if dimensions else 'Rzut z góry')
    if view == 'top':
        return Markup(''.join(out) + '</svg>')

    s = min(270 / length, 105 / (diameter + vt['h_v']))
    side = lambda x, z: (28 + x * s, 430 - z * s)
    path([side(x * length, sign * width * diameter) for sign in (-1, 1)
          for x, width in (stations if sign == -1 else stations[::-1])], '#fff')
    tailac = vt['x_ac_m']
    path([side(tailac-.25*vt['cr_v'], .1*diameter), side(tailac-.25*vt['ct_v'], vt['h_v']),
          side(tailac+.75*vt['ct_v'], vt['h_v']), side(tailac+.75*vt['cr_v'], 0)])
    path([side(xwing, 0), side(xwing + w['cr'], 0)], 'none', False)
    label(167, 485, f'Rzut z boku · L = {round(length * 1000)} mm' if dimensions else 'Rzut z boku')

    s = min(270 / span, 90 / (diameter + vt['h_v']))
    front = lambda y, z: (490 + y * s, 430 - z * s)
    zroot = diameter * (.3 if p.get('wing_config') in ('high', 'braced_high') else -.3)
    ztip = zroot + span / 2 * math.tan(math.radians(w['dihedral_deg']))
    path([front(-span / 2, ztip), front(0, zroot), front(span / 2, ztip)], 'none', False)
    out.append(f'<ellipse cx="490" cy="430" rx="{diameter*s/2:.2f}" ry="{diameter*s/2:.2f}" '
               'fill="white" stroke="#333"/>')
    path([front(0, diameter / 2), front(0, vt['h_v'])], 'none', False)
    label(490, 485, 'Rzut z przodu')
    out.append('</svg>')
    return Markup(''.join(out))
