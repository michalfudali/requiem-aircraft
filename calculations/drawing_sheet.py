"""A4 reference sheet for the required hand drawing, in one physical scale."""
import html
import math
from markupsafe import Markup


def drawing_sheet(result):
    g, p = result['geometry'], result['params']
    w, f, ht, vt = g['wing'], g['fuselage'], g['horizontal_tail'], g['vertical_tail']
    length, span, diameter = f['length'], w['b'], f['diameter']
    minimum = max(span * 1000 / 166, length * 1000 / 113, (vt['h_v'] + diameter) * 1000 / 42)
    denominator = next((d for d in (20, 25, 50, 75, 100, 150, 200, 250, 500, 1000) if d >= minimum), math.ceil(minimum / 100) * 100)
    s = 1000 / denominator
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 190 270" role="img" aria-label="Arkusz A4: trzy rzuty w jednej skali">',
           '<defs><pattern id="millimeter" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M1 0H0V1" fill="none" stroke="#ddd" stroke-width=".08"/></pattern><pattern id="centimeter" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="#bbb" stroke-width=".15"/></pattern></defs>',
           '<rect width="190" height="270" fill="white"/><g class="drawing-grid"><rect width="190" height="248" fill="url(#millimeter)"/><rect width="190" height="248" fill="url(#centimeter)"/></g>']
    def path(points, close=False, dash=False):
        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.3f},{y:.3f}' for i, (x, y) in enumerate(points))
        out.append(f'<path d="{d}{"Z" if close else ""}" fill="none" stroke="#222" stroke-width=".35"' + (' stroke-dasharray="2 1"' if dash else '') + '/>')
    def label(x, y, text, size=3):
        out.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}">{html.escape(text)}</text>')
    top = lambda x, y: (95 + y * s, 20 + x * s)
    side = lambda x, z: (18 + x * s, 187 - z * s)
    front = lambda y, z: (95 + y * s, 231 - z * s)
    xwing = result['balance']['x_le_wing_m']
    sweep = math.tan(math.radians(w['sweep_deg']))
    stations = [(0, 0), (.12, .33), (.3, .5), (.5, .46), (.75, .22), (1, .02)]
    fuselage = [(x * length, sign * width * diameter) for sign in (-1, 1)
                for x, width in (stations if sign == -1 else stations[::-1])]
    for sign in (-1, 1):
        leading, trailing = [], []
        for station in g['schrenk']:
            y, chord = station['y'], station['c_geom']
            x = xwing + y * sweep + .25 * (w['cr'] - chord)
            leading.append(top(x, sign * y)); trailing.append(top(x + chord, sign * y))
        path(leading + trailing[::-1], True)
        tailac = ht['x_ac_m']
        path([top(tailac-.25*ht['cr_h'], 0), top(tailac-.25*ht['ct_h'], sign*ht['b_h']/2),
              top(tailac+.75*ht['ct_h'], sign*ht['b_h']/2), top(tailac+.75*ht['cr_h'], 0)], True)
    path([top(*v) for v in fuselage], True)
    path([side(*v) for v in fuselage], True)
    tailac = vt['x_ac_m']
    path([side(tailac-.25*vt['cr_v'], 0), side(tailac-.25*vt['ct_v'], vt['h_v']),
          side(tailac+.75*vt['ct_v'], vt['h_v']), side(tailac+.75*vt['cr_v'], 0)], True)
    path([side(xwing, 0), side(xwing + w['cr'], 0)])
    zroot = diameter * (.3 if p.get('wing_config') in ('high', 'braced_high') else -.3)
    ztip = zroot + span / 2 * math.tan(math.radians(w['dihedral_deg']))
    path([front(-span/2, ztip), front(0, zroot), front(span/2, ztip)])
    cx, cy = front(0, 0)
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{diameter*s/2}" fill="none" stroke="#222" stroke-width=".35"/>')
    path([front(0, diameter/2), front(0, vt['h_v'])])
    # Main gear position comes from the mass model, track from geometry.
    xgear = result['balance']['arms']['gear']
    track = g['gear']['track']
    zground = -.8 * diameter
    mount_y = track / 2 if p.get('gear_attachment', 'fuselage') == 'wing' else diameter / 2
    for sign in (-1, 1):
        path([top(xgear, sign * mount_y), top(xgear, sign * track/2)], dash=True)
        path([front(sign * mount_y, zroot), front(sign * track/2, zground)])
        for point in (top(xgear, sign * mount_y), front(sign * mount_y, zroot)):
            out.append(f'<circle cx="{point[0]:.3f}" cy="{point[1]:.3f}" r=".8" fill="white" stroke="#222" stroke-width=".25"/>')
    path([side(xgear, zroot), side(xgear, zground)])
    path([side(.12 * length, -.3 * diameter), side(.12 * length, zground)])
    for x in (xgear, .12 * length):
        px, py = side(x, zground)
        out.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="1.2" fill="none" stroke="#222" stroke-width=".35"/>')
    # Linie wymiarowe wg PN-EN ISO 129
    y_left = 95 - (span / 2) * s
    y_right = 95 + (span / 2) * s
    dim_y = 14
    out.append(f'<line x1="{y_left:.3f}" y1="{dim_y}" x2="{y_right:.3f}" y2="{dim_y}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{y_left:.3f}" y1="{dim_y-2}" x2="{y_left:.3f}" y2="{dim_y+2}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{y_right:.3f}" y1="{dim_y-2}" x2="{y_right:.3f}" y2="{dim_y+2}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<text x="95" y="{dim_y-1}" font-family="Arial,sans-serif" font-size="2.6" fill="#005691" text-anchor="middle">b = {span*1000:.0f} mm</text>')

    x_nose = 18
    x_tail = 18 + length * s
    dim_x_side = 193
    out.append(f'<line x1="{x_nose:.3f}" y1="{dim_x_side}" x2="{x_tail:.3f}" y2="{dim_x_side}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{x_nose:.3f}" y1="{dim_x_side-2}" x2="{x_nose:.3f}" y2="{dim_x_side+2}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{x_tail:.3f}" y1="{dim_x_side-2}" x2="{x_tail:.3f}" y2="{dim_x_side+2}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<text x="{(x_nose+x_tail)/2:.3f}" y="{dim_x_side-1}" font-family="Arial,sans-serif" font-size="2.6" fill="#005691" text-anchor="middle">L = {length*1000:.0f} mm</text>')

    y_g_left = 95 - (track / 2) * s
    y_g_right = 95 + (track / 2) * s
    dim_track = 241
    out.append(f'<line x1="{y_g_left:.3f}" y1="{dim_track}" x2="{y_g_right:.3f}" y2="{dim_track}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{y_g_left:.3f}" y1="{dim_track-1.5}" x2="{y_g_left:.3f}" y2="{dim_track+1.5}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<line x1="{y_g_right:.3f}" y1="{dim_track-1.5}" x2="{y_g_right:.3f}" y2="{dim_track+1.5}" stroke="#005691" stroke-width=".25"/>')
    out.append(f'<text x="95" y="{dim_track+3.2}" font-family="Arial,sans-serif" font-size="2.2" fill="#005691" text-anchor="middle">rozstaw = {track*1000:.0f} mm</text>')

    label(8, 8, 'Rzut z góry — dziób do góry')
    label(8, 139, f'b = {span*1000:.0f} mm; S = {w["S"]:.2f} m²; Λ = {w["AR"]:.2f}')
    label(8, 151, 'Rzut z boku — dziób w lewo')
    label(8, 198, f'L = {length*1000:.0f} mm')
    label(8, 207, 'Rzut z przodu — wznios i położenie podwozia')
    label(8, 246, '○ Mocowanie podwozia: ' + ('skrzydło' if p.get('gear_attachment') == 'wing' else 'kadłub'))
    path([(0, 250), (190, 250), (190, 270), (0, 270)], True)
    label(3, 256, str(p.get('name', 'Projekt BIPOL I'))[:75])
    label(3, 262, f'A4 • skala 1:{denominator} przy wydruku 100% • wymiary w mm')
    label(3, 267, 'Wzór do rysunku odręcznego; mocowania pokazano koncepcyjnie.', 2.6)
    out.append('</svg>')
    return Markup(''.join(out))
