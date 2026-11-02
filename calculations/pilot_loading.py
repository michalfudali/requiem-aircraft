"""Fixed-airframe crew loading study: mass moments and exact affine limits.

FAA-H-8083-1B, chapter 2: xCG = sum(m*x)/sum(m). The 25–35% MAC
criterion and 5% margin are the existing BIPOL model's design criteria,
not certified operating limits. All crew stations vary together, as in P3.
"""
from math import isclose
from calculations.ballast import ballast_model, solve_ballast

FAA_SOURCE = 'https://www.faa.gov/sites/faa.gov/files/2023-09/Weight_Balance_Handbook.pdf'
CS22_SOURCE = 'https://www.easa.europa.eu/sites/default/files/dfu/CS-22%20Amendment%203.pdf'


def intersect_limits(constraints, domain):
    """Solve a*m+b >= 0 without sampling, division by zero or infinite JSON."""
    low, high = domain
    for c in constraints:
        a, b = c['a'], c['b']
        if a == 0:
            if b < 0:
                return None
        elif a > 0:
            low = max(low, -b / a)
        else:
            high = min(high, -b / a)
    if low > high:
        if not isclose(low, high, rel_tol=0, abs_tol=1e-9):
            return None
        low = high = (low + high) / 2
    return dict(min_kg=low, max_kg=high)


def calculate_pilot_loading(mass, geometry, balance):
    n = int(mass.get('n_crew') or 0)
    if mass.get('unmanned') or n == 0 or mass['m_crew'] <= 0:
        return dict(available=False, reason='Brak załogi na pokładzie.')
    nominal = mass['m_crew'] / n
    domain = [min(55., nominal), max(110., nominal)]
    mac = geometry['wing']['mac']
    le = balance['x_lemac_m']
    arm = balance['arms']['crew']
    np_pct = balance['neutral_point']['x_n_mac_pct']
    fwd = 25. if balance['cg_range']['delta_pct'] <= 10. else None
    limits = dict(forward_pct=fwd, aft_pct=35., minimum_margin_pct=5.,
                  stability_aft_pct=np_pct - 5., maximum_mass_kg=mass['m0'])
    sample_masses = sorted(set([domain[0], domain[1], nominal, 55., 70., 110.] +
                               [domain[0] + (domain[1]-domain[0])*i/44 for i in range(45)]))
    cases, all_constraints = [], []
    for state in balance['loading_states']:
        if state['key'] == 'oew':
            continue
        base_mass = state['mass_kg'] - mass['m_crew']
        base_moment = state['moment_kg_m'] - mass['m_crew'] * arm
        constraints = [dict(kind='mass', label='Masa projektowa', a=-n, b=mass['m0']-base_mass)]
        for kind, label, pct, lower in [('forward', 'Przednie ŚC (P3)', fwd, True),
                ('aft', 'Tylne ŚC (P3)', 35., False),
                ('stability', 'Zapas stateczności 5% ŚDA', np_pct-5., False)]:
            if pct is None:
                continue
            x_limit = le + mac*pct/100
            sign = 1 if lower else -1
            constraints.append(dict(kind=kind, label=label, a=sign*n*(arm-x_limit),
                                    b=sign*(base_moment-x_limit*base_mass)))
        for c in constraints:
            c['state_key'] = state['key']
            c['state_name'] = state['name']

        def point(person):
            total = base_mass + n*person
            moment = base_moment + n*person*arm
            xcg = moment/total
            pct = 100*(xcg-le)/mac
            checks = {c['kind']: c['a']*person+c['b'] >= -1e-9 for c in constraints}
            return dict(person_kg=person, mass_kg=total, moment_kg_m=moment, xcg_m=xcg,
                        xcg_mac_pct=pct, static_margin_pct=np_pct-pct,
                        mass_excess_kg=max(0., total-mass['m0']),
                        sensitivity_pct_per_kg=100*n*(arm*base_mass-base_moment)/(mac*total**2),
                        checks=checks, passed=all(checks.values()))

        cases.append(dict(key=state['key'], name=state['name'], base_mass_kg=base_mass,
                          base_moment_kg_m=base_moment, constraints=constraints,
                          interval=intersect_limits(constraints, domain),
                          samples=[point(p) for p in sample_masses],
                          light=point(55.), heavy=point(110.), nominal=point(nominal)))
        all_constraints.extend(constraints)
    result = dict(available=True, n_crew=n, nominal_person_kg=nominal, crew_arm_m=arm,
                domain_kg=domain, limits=limits, cases=cases,
                common_interval=intersect_limits(all_constraints, domain),
                source_url=FAA_SOURCE, regulation_url=CS22_SOURCE,
                note='Stała geometria i położenia mas; zmienia się masa każdej osoby załogi jednocześnie. '
                     'Pasażerowie, ładunek i paliwo danego stanu pozostają stałe. '
                     'Masa osoby obejmuje jej wyposażenie. Przedział dotyczy kryteriów modelu P3, '
                     'bez oceny sterowności i bez balastu; nie jest ograniczeniem z instrukcji użytkowania.',
                cs22_note='CS 22.23(b): 70–110 kg na osobę ze spadochronem bez balastu; '
                          'CS 22.25(b): przypadek 55 kg, z dopuszczonym balastem. '
                          'Zakres 55–110 kg w P3 jest analizą projektową, a nie deklaracją zgodności CS-22.')
    model = ballast_model(result, geometry, balance)
    result['ballast'] = dict(model=model, references=[solve_ballast(model,p) for p in (55.,110.)])
    return result
