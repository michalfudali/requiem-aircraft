"""Minimum trim ballast for all loading cases of a fixed aircraft.

FAA-H-8083-1B, ch. 7: w = M*(x_target-x_CG)/(x_ballast-x_target).
We retain both CG limits, the existing static margin and design mass. Writing
z = w*x_ballast makes every condition affine in (w,z). Their feasible polygon
gives a global minimum, including a single feasible point, without a grid scan.
"""
from math import isfinite, ulp


def ballast_model(study, geometry, balance):
    """Serialize the physical coefficients once; Python and the UI use these."""
    le, mac = balance['x_lemac_m'], geometry['wing']['mac']
    limits = study['limits']
    bounds = [('forward', 'Przednie ŚC P3', limits['forward_pct'], 1),
              ('aft', 'Tylne ŚC P3', limits['aft_pct'], -1),
              ('stability', 'Zapas stateczności 5% ŚDA', limits['stability_aft_pct'], -1)]
    constraints = []
    for case in study['cases']:
        common = dict(state_key=case['key'], state_name=case['name'])
        mb, qb, n, arm = case['base_mass_kg'], case['base_moment_kg_m'], study['n_crew'], study['crew_arm_m']
        constraints.append(dict(**common, kind='mass', label='Masa projektowa', unit='kg',
                                a=-1., b=0., c0=limits['maximum_mass_kg']-mb, cp=-n))
        for kind, label, pct, sign in bounds:
            if pct is None:
                continue
            x = le + mac*pct/100
            constraints.append(dict(**common, kind=kind, label=label, unit='kg m',
                                    a=-sign*x, b=float(sign), c0=sign*(qb-x*mb), cp=sign*n*(arm-x)))
    return dict(version=1, station_domain_m=[0., geometry['fuselage']['length']],
                lemac_m=le, mac_m=mac, neutral_point_pct=balance['neutral_point']['x_n_mac_pct'],
                n_crew=study['n_crew'], crew_arm_m=study['crew_arm_m'],
                maximum_mass_kg=limits['maximum_mass_kg'], constraints=constraints,
                cases=[{k: c[k] for k in ('key', 'name', 'base_mass_kg', 'base_moment_kg_m')} for c in study['cases']],
                source_url=study['source_url'],
                note='Balast korekcyjny pozostaje na miejscu we wszystkich stanach. '
                     'Przeszukiwany zakres obejmuje długość kadłuba; wykonalność zabudowy i mocowania wymaga osobnej oceny. '
                     'To pomoc projektowa według kryteriów P3, bez dodawania masy do istniejącego bilansu.')


def _residual(c, point):
    return c['a']*point[0]+c['b']*point[1]+c['c']


def _tolerance(c, point):
    return 64*ulp(max(1., abs(c['a']*point[0])+abs(c['b']*point[1])+abs(c['c'])))


def _clip(polygon, constraint):
    out = []
    previous = polygon[-1]
    vp = _residual(constraint, previous)
    ip = vp >= -_tolerance(constraint, previous)
    for current in polygon:
        vc = _residual(constraint, current)
        ic = vc >= -_tolerance(constraint, current)
        if ip != ic:
            t = max(0., min(1., vp/(vp-vc)))
            out.append([previous[0]+t*(current[0]-previous[0]), previous[1]+t*(current[1]-previous[1])])
        if ic:
            out.append(current)
        previous, vp, ip = current, vc, ic
    return out


def solve_ballast(model, person_kg, station_m=None):
    """Use a specified station, or minimize ballast over the whole fuselage.

    A zero solution has no preferred station. Positive ballast never repairs
    overweight, and a station at a violated CG limit cannot bring CG onto it.
    """
    if not isfinite(person_kg) or person_kg < 0:
        raise ValueError('Masa osoby musi być skończona i nieujemna.')
    xmin, xmax = model['station_domain_m']
    if station_m is not None and (not isfinite(station_m) or not xmin <= station_m <= xmax):
        raise ValueError('Położenie balastu musi leżeć w badanym zakresie kadłuba.')
    constraints = [dict(c, c=c['c0']+c['cp']*person_kg) for c in model['constraints']]

    def states(w, z):
        rows = []
        for case in model['cases']:
            m = case['base_mass_kg']+model['n_crew']*person_kg+w
            q = case['base_moment_kg_m']+model['n_crew']*person_kg*model['crew_arm_m']+z
            pct = 100*(q/m-model['lemac_m'])/model['mac_m']
            failed = [c['label'] for c in constraints if c['state_key']==case['key']
                      and _residual(c, [w,z]) < -_tolerance(c, [w,z])]
            rows.append(dict(key=case['key'], name=case['name'], mass_kg=m, moment_kg_m=q,
                             xcg_m=q/m, xcg_mac_pct=pct, static_margin_pct=model['neutral_point_pct']-pct,
                             failed=failed, passed=not failed))
        return rows

    before = states(0., 0.)
    cap = min(c['c'] for c in constraints if c['kind']=='mass')
    common = dict(person_kg=person_kg, station_m=station_m, before=before,
                  mass_headroom_kg=max(0., cap), constraints=constraints)
    if all(c['passed'] for c in before):
        return dict(**common, status='unnecessary', feasible=True, mass_kg=0., moment_kg_m=0.,
                    after=before, vertices=[], active_constraints=[],
                    message='Balast nie jest potrzebny: wszystkie stany spełniają kryteria modelu.')
    if cap < 0:
        return dict(**common, status='infeasible', feasible=False, mass_kg=None, moment_kg_m=None,
                    after=[], vertices=[], active_constraints=[], reason='mass',
                    message='Przekroczona masa projektowa. Dodatni balast nie usunie przekroczenia.')
    polygon = [[0.,0.], [cap,xmin*cap], [cap,xmax*cap]]
    if station_m is not None:
        polygon = [[0.,0.], [cap, station_m*cap]]
    for c in constraints:
        polygon = _clip(polygon, c)
        if not polygon:
            return dict(**common, status='infeasible', feasible=False, mass_kg=None, moment_kg_m=None,
                        after=[], vertices=[], active_constraints=[], reason='balance',
                        message='Brak wspólnego rozwiązania dla ŚC, zapasu stateczności i masy projektowej '
                                +('w wybranym miejscu balastu.' if station_m is not None else 'w badanym zakresie kadłuba.'))
    w, z = min(polygon, key=lambda p: (p[0], p[1]))
    station = z/w if w > 0 else station_m
    # A plane through an existing polygon vertex can leave a few ulps outside.
    # Snap the recovered station to its physical bounds, not the ballast mass.
    if station is not None:
        station = max(xmin, min(xmax, station))
        z = w*station
    common['station_m'] = station
    return dict(**common, status='feasible', feasible=True, mass_kg=w, moment_kg_m=z,
                after=states(w,z), vertices=polygon,
                active_constraints=[c for c in constraints if abs(_residual(c,[w,z])) <= _tolerance(c,[w,z])],
                message='Najmniejszy wspólny balast spełniający kryteria modelu dla wszystkich stanów.')
