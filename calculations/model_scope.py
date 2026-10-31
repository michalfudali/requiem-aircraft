"""Explicit applicability and unverified analyses for special aircraft missions."""

WATER_NOTE = ('Nie wyznaczono operacji na wodzie: potrzebne są charakterystyki oporu hydrodynamicznego, '
              'stateczność na wodzie i obciążenia kadłuba lub pływaków. Model tarcia kół nie ma zastosowania.')


def is_water(params):
    return params.get('operating_surface', 'land') == 'water'


def assessment(params, mass):
    checks, limitations = [], []
    water = None
    if is_water(params):
        # CS 23.2310(a): 80% excess over the buoyancy supporting MTOW in fresh water.
        required = 1.8 * mass['m0'] / 1000.0
        volume = params.get('water_displacement_volume_m3') or None
        cs23 = str(params.get('category', '')).startswith('cs23_') and mass['m0'] <= 8618
        basis_note = ('EASA CS 23.2310(a); obliczenie wyporności nie dowodzi stateczności ani certyfikacji.'
                      if cs23 else
                      'Wstępne kryterium 1,8·MTOW zaczerpnięte z CS 23.2310(a). Projekt poza zakresem CS-23: '
                      'wymagania wyporności i podziału kadłuba/pływaków właściwej podstawy certyfikacji pozostają niezweryfikowane.')
        water = dict(required_buoyant_volume_m3=required, supplied_buoyant_volume_m3=volume,
                     fresh_water_density_kg_m3=1000.0, excess_buoyancy_factor=1.8,
                     hydrodynamic_performance_available=False,
                     cs23_criterion_applicable=cs23, source=basis_note)
        checks.append(dict(parameter='[Woda] Wyporność kadłuba lub pływaków przy MTOW',
                           required=f'≥ {required:.3f} m³ (woda słodka, ρ=1000 kg/m³)',
                           actual=f'{volume:g} m³' if volume is not None else 'Brak danych kadłuba lub pływaków',
                           passed=volume is not None and volume >= required,
                           note=water['source']))
        checks.append(dict(parameter='[Woda] Operacje i stateczność na wodzie',
                           required='Analiza hydrodynamiczna i stateczność, także przy zalaniu',
                           actual='Niezweryfikowane', passed=False, severity='warning', note=WATER_NOTE))
        limitations.append(WATER_NOTE)
        if not cs23:
            limitations.append(basis_note)
    try:
        number = int(params.get('topic_id', 0)) if params.get('topic_origin') == 'official' else 0
    except (ValueError, TypeError):
        number = 0
    special = ('Zabudowa noszy, dostęp do chorego i wyjście awaryjne wymagają sprawdzenia wymiarów kabiny.'
               if number in (43, 44) else
               'Wymiary ładowni, nośność podłogi, mocowania i rampa wymagają odrębnego projektu.'
               if 66 <= number <= 74 else
               'Zbiorniki, zrzut i zmiana wyważenia przy opróżnianiu wymagają odrębnej analizy.'
               if 86 <= number <= 94 or number in (109, 110) else
               'Zabudowa wyposażenia zadaniowego, opór zewnętrzny i obciążenia wymagają odrębnej analizy.'
               if 99 <= number <= 102 else None)
    if special:
        limitations.append(special)
        checks.append(dict(parameter='[Zakres] Zabudowa i misja specjalna', required='Opracowanie szczegółowe',
                           actual='Niezweryfikowane', passed=False, severity='warning', note=special))
    if params.get('m_cargo', 0) and not all(params.get(key, 0) for key in
            ('cargo_bay_length_m', 'cargo_bay_width_m', 'cargo_bay_height_m')):
        note = 'Nie podano wymiarów ładowni. Masa ładunku nie wyznacza jego gabarytów; geometria kadłuba jest oszacowaniem wymagającym sprawdzenia.'
        limitations.append(note)
        checks.append(dict(parameter='[Zakres] Gabaryty ładowni', required='Długość, szerokość i wysokość użytkowa',
                           actual='Brak danych', passed=False, severity='warning', note=note))
    return dict(operating_surface=params.get('operating_surface', 'land'), water=water,
                limitations=limitations, checks=checks)


def suppress_water_distances(performance):
    """Retain airborne speeds and mass; never expose wheel braking as water performance."""
    takeoff = performance['takeoff']
    for key in ('ground_roll_m', 'transition_m', 'climb_to_15m_m', 'air_distance_m', 'climb_angle_deg',
                'distance_to_15m', 'ground_roll_time_s', 'time_to_15m_s'):
        takeoff[key] = None
    takeoff.update(available=False, model_available=False, surface='water', note=WATER_NOTE)
    takeoff.pop('terms', None)
    landing = performance['landing']
    for key in ('air_approach_m', 'free_roll_m', 'braking_roll_m', 'ground_roll_m', 'distance_from_15m',
                'approach_straight_m', 'flare_horizontal_m'):
        landing[key] = None
    for key in ('mu_brake', 'v_rms', 'q_rms', 'phi_ge', 'cz_roll', 'cx_roll', 'a_mean', 'effective_flare_angle_rad'):
        landing['terms'].pop(key, None)
    landing.update(available=False, model_available=False, surface='water', note=WATER_NOTE)
