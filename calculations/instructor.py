"""Course requirements transcribed from the five lecture-note photographs.

See docs/WYTYCZNE_PROWADZACEGO.md for the source and ambiguous annotations.
These requirements assess coursework, not airworthiness certification.
"""
MIN_AIRCRAFT = 8
CRUISE_LD_FACTOR = 0.94
PASSENGER_WITH_BAG_KG = 115.0
TAKEOFF_MASS_FRACTION = 0.975
MIN_MASS_ITERATIONS = 5
FLAP_TAKEOFF_DEFLECTION_DEG = 20.0
FLAP_LANDING_DEFLECTION_DEG = 40.0
# Largest accepted gap between the P2 assumed and the P4 computed Kmax before iterating.
POLAR_CONSISTENCY_TOLERANCE = 0.20


def review_coursework(result):
    p, mass = result['params'], result['mass']
    trends = result['bipol_projects']['p1']['trend_analysis']
    fit = trends['mass_fit']
    charts = trends['report_charts']
    checks = []

    def check(key, label, passed, detail):
        checks.append(dict(key=key, label=label, passed=bool(passed), detail=detail))

    check('sample', 'Co najmniej 8 podobnych konstrukcji', trends['families_n'] >= MIN_AIRCRAFT,
          f"{trends['families_n']} rodzin; {trends['selected_n']} wariantów tej samej klasy i napędu.")
    check('charts', '6 wykresów: 1 masowy i 5 parametrów',
          len(charts) == 6 and len({c['parameter'] for c in charts if c['kind'] != 'mass'}) == 5
          and all(c['n'] >= MIN_AIRCRAFT and c['fit'] for c in charts),
          f"Kompletne wykresy (minimum 8 par): {sum(c['n'] >= MIN_AIRCRAFT and bool(c['fit']) for c in charts)}/6. Braki wymagają danych źródłowych.")
    check('mass_trend', 'Malejący udział masy pustej w funkcji MTOW', fit and fit['C'] < 0,
          f"C = {fit['C']:.4f}." if fit else 'Brak regresji masowej.')
    check('iteration', 'Bilans masy: minimum 5 iteracji i zbieżność',
          len(mass['iterations']) >= MIN_MASS_ITERATIONS and mass['mission_assumptions']['mass_residual_relative'] <= .001,
          f"{len(mass['iterations'])} iteracji; kryterium reszty równania ≤0,1%.")
    flap_states = result['aerodynamics']['flap_configurations']
    check('flaps', 'Wychylenia klap: start 20°, lądowanie 40°',
          flap_states['takeoff']['deflection_deg'] == FLAP_TAKEOFF_DEFLECTION_DEG and
          flap_states['landing']['deflection_deg'] == FLAP_LANDING_DEFLECTION_DEG,
          'Wychylenia w stopniach, potwierdzone przez autora notatek. Przyrosty nośności i oporu są oszacowaniami dla tych konfiguracji.')
    k_p2 = mass['mission_assumptions'].get('k_max_preliminary')
    if k_p2:
        aero = result['aerodynamics']
        k_p4, cx0_p4 = aero['k_max'], aero['cx0_clean']
        if mass['mission_assumptions'].get('cruise_model') == 'constant_tas_altitude':
            check('polar_consistency', 'Domknięcie bilansu misji z biegunową P4',
                  result['design_iteration']['converged'],
                  f"{result['design_iteration']['iterations']} iteracji masy, geometrii i oporu przy zadanej TAS i wysokości.")
        else:
            check('polar_consistency', f'Spójność biegunowej P2 i P4 (Kmax ±{POLAR_CONSISTENCY_TOLERANCE:.0%})',
              abs(k_p2 - k_p4) <= POLAR_CONSISTENCY_TOLERANCE * k_p4,
              f"P2: Kmax = {k_p2:.1f} (Cx0 = {p['cx0']:.4f}, e = {p['oswald_e']:.2f}); "
              f"P4: Kmax = {k_p4:.1f} (Cx0 = {cx0_p4:.4f}, e = {aero['oswald_e']:.2f}). "
                  'Przy większej różnicy przyjmij w założeniach P2 wartości z P4 i powtórz bilans masy.')
    if p['engine_type'] != 'none':
        drive_key = 'thrust_to_weight' if p['engine_type'] == 'jet' else 'power_loading_kg_kw'
        climb = next(c for c in trends['relationships'] if c['x_key'] == drive_key and c['y_key'] == 'climb_rate_ms')
        check('climb_data', 'Dane do zależności wznoszenia od obciążenia napędu',
              len(climb['points']) >= MIN_AIRCRAFT,
              f"{len(climb['points'])} par. Brakujące wartości można wczytać z CSV wraz ze źródłem.")
        refined = mass['mission_assumptions'].get('ld_source') == 'p4_cruise'
        check('cruise', 'Doskonałość przelotowa 0,94 Kmax',
              abs(mass['mission_assumptions']['ld_factor'] - CRUISE_LD_FACTOR) < 1e-9,
              'Bilans uściślony: pierwsze oszacowanie 0,94 Kmax zastąpiono doskonałością z biegunowej P4 '
              f"przy wymaganej prędkości (K = {mass['ld_cruise_used']:.2f})." if refined else
              'Założenie do równania Bregueta, odrębne od doskonałości przy zadanej prędkości.')
        check('start_fraction', 'Ułamek masy po starcie 0,970–0,975',
              .970 <= mass['fuel_fractions_detail']['takeoff'] <= .975,
              'Rozruch i start liczone łącznie, bez podwójnego zużycia paliwa.')
        check('takeoff', 'Wymagana całkowita długość startu', p.get('takeoff_distance_m', 0) > 0,
              'Od postoju do wysokości 15 m; rozbieg jest tylko składową.')
    check('landing', 'Wymagana całkowita długość lądowania', p.get('landing_distance_m', 0) > 0,
          'Od wysokości 15 m do zatrzymania; dobieg jest tylko składową.')
    if p['n_pax']:
        check('passenger', '115 kg na pasażera z bagażem',
              abs(p['m_pax'] + p.get('m_bag', 0) - PASSENGER_WITH_BAG_KG) < 1e-6,
              'Inna wartość wymaga uzasadnienia w założeniach tematu; załogę liczono oddzielnie.')
    return {'checks': checks, 'passed': sum(c['passed'] for c in checks), 'total': len(checks),
            'manual': ['P1: odręczny szkic w trzech rzutach na gładkim A4.',
                       'P3: rysunek na papierze milimetrowym; wskazać mocowanie podwozia.',
                       'Dane katalogowe sprawdzić w źródłach (np. Jane’s/AFM); arkusz CSV otwiera się w Excelu.']}
