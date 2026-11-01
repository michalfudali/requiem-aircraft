"""ML1 P2 (2.1)/(2.2): exact integrals of piecewise-linear wing boundaries."""
import math

from .validation import finite, finite_result

SOURCE_URL = 'https://www.meil.pw.edu.pl/zm/content/download/23965/126684/file/Projekt%202.pdf'


def integrate_planform(stations):
    """Symmetric wing from half-span stations {y_m, x_le_m, chord_m}.

The leading edge and chord interpolate linearly on each segment. Integrals
are exact for that geometry, including multiple changes of taper and sweep.
"""
    if not isinstance(stations, list) or not 2 <= len(stations) <= 501:
        raise ValueError('Obrys skrzydła: podaj od 2 do 501 stacji półrozpiętości.')
    points = []
    for i, row in enumerate(stations, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Stacja {i}: wymagane y_m, x_le_m i chord_m.')
        points.append(dict(y_m=finite(row.get('y_m'), f'Stacja {i}, y', nonnegative=True),
                           x_le_m=finite(row.get('x_le_m'), f'Stacja {i}, x krawędzi natarcia'),
                           chord_m=finite(row.get('chord_m'), f'Stacja {i}, cięciwa', nonnegative=True)))
    if points[0]['y_m'] != 0:
        raise ValueError('Pierwsza stacja obrysu musi leżeć na osi symetrii y = 0.')
    integrals = dict(chord=0., chord_squared=0., chord_x_le=0., y_chord=0.)
    segments = []
    for index, (start, end) in enumerate(zip(points, points[1:]), 1):
        length = end['y_m'] - start['y_m']
        if length <= 0:
            raise ValueError('Stacje obrysu muszą mieć ściśle rosnące współrzędne y.')
        c0, c1 = start['chord_m'], end['chord_m']
        x0, x1 = start['x_le_m'], end['x_le_m']
        part = dict(chord=length*(c0+c1)/2,
                    chord_squared=length*(c0*c0+c0*c1+c1*c1)/3,
                    chord_x_le=length*(2*c0*x0+c0*x1+c1*x0+2*c1*x1)/6,
                    y_chord=start['y_m']*length*(c0+c1)/2 + length*length*(c0+2*c1)/6)
        finite_result(*part.values())
        for key in integrals:
            integrals[key] += part[key]
        segments.append(dict(index=index, y_start_m=start['y_m'], y_end_m=end['y_m'], integrals=part))
    finite(integrals['chord'], 'Pole półskrzydła', positive=True)
    area = 2*integrals['chord']
    span = 2*points[-1]['y_m']
    mac = integrals['chord_squared']/integrals['chord']
    x_le_mac = integrals['chord_x_le']/integrals['chord']
    y_mac = integrals['y_chord']/integrals['chord']
    aspect = span*span/area
    finite_result(area, span, mac, x_le_mac, y_mac, aspect)
    return dict(method='ml1.p2.planform_integrals', source='ML1 Projekt 2, (2.1), (2.2)', source_url=SOURCE_URL,
                stations=points, segments=segments, half_wing_integrals=integrals,
                area_m2=area, span_m=span, aspect_ratio=aspect,
                geometric_mean_chord_m=area/span, mac_m=mac,
                x_le_mac_m=x_le_mac, x_n_mac_m=x_le_mac-points[0]['x_le_m'], y_mac_m=y_mac)


def elliptical_planform(span_m, root_chord_m, half_chord_sweep_deg=0.):
    """Exact ellipse with a straight half-chord line; ML1 P2 note 2 / (2.5a)."""
    span = finite(span_m, 'Rozpiętość', positive=True)
    chord = finite(root_chord_m, 'Cięciwa nasadowa', positive=True)
    sweep = finite(half_chord_sweep_deg, 'Skos linii połówek cięciw')
    if not -90 < sweep < 90:
        raise ValueError('Skos linii połówek cięciw musi być pomiędzy −90° i 90°.')
    area = math.pi*span*chord/4
    mac = 8*chord/(3*math.pi)
    y_mac = 2*span/(3*math.pi)
    x_le = (chord-mac)/2 + y_mac*math.tan(math.radians(sweep))
    finite_result(area, mac, y_mac, x_le, span*span/area)
    return dict(method='ml1.p2.ellipse', source='ML1 Projekt 2, uwaga 2, (2.5a)', source_url=SOURCE_URL,
                span_m=span, root_chord_m=chord, half_chord_sweep_deg=sweep,
                area_m2=area, aspect_ratio=span*span/area,
                geometric_mean_chord_m=area/span, mac_m=mac,
                x_le_mac_m=x_le, x_n_mac_m=x_le, y_mac_m=y_mac)
