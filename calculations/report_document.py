"""Editorial layer for the submission reports; all findings come from one result."""
from datetime import date
import math

TITLES = {
    'p1': 'Projekt koncepcyjny',
    'p2': 'Studium wykonalności',
    'p3': 'Projekt wstępny i analiza masowa',
    'p4': 'Charakterystyki aerodynamiczne samolotu',
    'p5': 'Osiągi samolotu',
    'p6': 'Obwiednia obciążeń dopuszczalnych',
}
METADATA = (
    ('student_name', 'Imię i nazwisko', 'student'),
    ('album_no', 'Numer albumu', 'album'),
    ('group_no', 'Grupa', 'group'),
    ('supervisor', 'Prowadzący', 'supervisor'),
    ('submission_date', 'Data oddania', 'date'),
    ('academic_year', 'Rok akademicki', 'academic_year'),
)


def report_number(value, digits=2):
    """Polish decimal punctuation and stable precision, including missing values."""
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return '—'
    return f'{value:,.{digits}f}'.replace(',', '\u202f').replace('.', ',')


def tex_number(value, digits=2):
    return report_number(value, digits).replace(',', '{,}').replace('\u202f', r'\,')


def report_metadata(params, overrides=None, today=None):
    today = today or date.today()
    year = today.year if today.month >= 10 else today.year - 1
    defaults = {'submission_date': today.strftime('%d.%m.%Y'),
                'academic_year': f'{year}/{str(year + 1)[-2:]}'}
    overrides = overrides or {}
    return [{'key': key, 'label': label,
             'value': str(overrides.get(query) or params.get(key) or defaults.get(key, '')).strip()}
            for key, label, query in METADATA]


def report_document(results, sections, overrides=None, folder_cover=False):
    p = results['params']
    mass, geom = results['mass'], results['geometry']
    aero, perf = results['aerodynamics'], results['performance']
    balance, env = results['balance'], results['envelope']
    trends = results['bipol_projects']['p1']['trend_analysis']
    number = report_number
    powered = p['engine_type'] != 'none'
    # Keep the assessment relevant when exporting just one part of the project.
    all_checks = results['compliance_checks']
    checks = []
    for check in all_checks:
        name = check['parameter']
        relevant = ('p1' in sections and 'stateczności' not in name)
        relevant |= ('p5' in sections and not name.startswith('[') and 'stateczności' not in name)
        relevant |= ('p3' in sections and 'stateczności' in name)
        if relevant:
            checks.append(check)
    if 'p2' in sections:
        residual_pct = mass['mission_assumptions']['mass_residual_relative'] * 100
        checks.append({'parameter': 'Zbieżność równania bilansu masy', 'required': '≤ 0,1%',
                       'actual': f'{number(residual_pct, 5)}%', 'passed': residual_pct <= .1})
    if 'p4' in sections:
        aileron = geom['control_surfaces']['ailerons']
        checks.append({'parameter': 'Wskaźnik skuteczności lotek pb/(2V)',
                       'required': f'≥ {number(aileron["min_pb_2v_req"], 3)}',
                       'actual': number(aileron['roll_helix_pb_2v'], 3),
                       'passed': aileron['roll_authority_ok']})
    if 'p1' in sections:
        for c in results['instructor_review']['checks']:
            if c['key'] in ('sample','charts','mass_trend','climb_data'):
                checks.append(dict(parameter=c['label'], required='Wytyczne prowadzącego',
                                   actual=c['detail'], passed=c['passed']))
    failed = [c for c in checks if not c['passed'] and c.get('severity') != 'warning']
    pending = [c for c in checks if not c['passed'] and c.get('severity') == 'warning']
    conclusions = {key: [] for key in TITLES}
    conclusions['p1'].append(
        f'Do dalszych obliczeń przyjęto powierzchnię skrzydła {number(geom["wing"]["S"])} m² '
        f'i wydłużenie {number(geom["wing"]["AR"])}. Dla przyjętej biegunowej '
        f'maksymalna doskonałość wynosi {number(aero["k_max"], 1)}.')
    if trends['mass_fit']:
        conclusions['p1'].append(
            f'Porównanie masowe obejmuje {trends["mass_fit"]["n"]} par danych. '
            f'Współczynnik R² = {number(trends["mass_fit"]["r2"], 3)} opisuje dopasowanie '
            'do tej próby. ' + ('Ze względu na słabe dopasowanie nie oparto wymiarowania '
                                'wyłącznie na regresji.' if trends['mass_fit']['r2'] < .5 else
                                'Zależność traktowano jako punkt odniesienia przy doborze proporcji masowych.'))
    else:
        conclusions['p1'].append('Próba nie pozwala wyznaczyć wiarygodnej regresji masowej. '
                                 'Wymiarowanie oparto na bilansie masy i założeniach aerodynamicznych.')
    residual = mass['mission_assumptions']['mass_residual_relative'] * 100
    conclusions['p2'].append(
        f'Bilans masowy daje masę startową {number(mass["m0"], 1)} kg, w tym '
        f'{number(mass["m_empty"], 1)} kg masy własnej i {number(mass["m_fuel"], 1)} kg paliwa. '
        f'Względna reszta równania wynosi {number(residual, 5)}%; '
        + ('osiągnięto przyjęty próg 0,1%.' if residual <= .1 else 'nie osiągnięto przyjętego progu 0,1%.'))
    if powered:
        dp = results['sizing']['design_point']
        drive = (f'ciąg {number(dp["thrust_kn"])} kN' if p['engine_type'] == 'jet'
                 else f'moc {number(dp["power_kw"], 1)} kW')
        if p.get('power_input_mode') == 'fixed' and p['engine_type'] == 'prop':
            conclusions['p2'].append(
                f'Do obliczeń osiągów przyjęto narzuconą moc {number(dp["power_kw"], 1)} kW. '
                f'Diagram doboru wskazuje wymaganą moc {number(dp["required_power_kw"], 1)} kW. '
                'Różnicę uwzględniono przez sprawdzenie rzeczywistych osiągów dla dostępnej mocy.')
        else:
            conclusions['p2'].append(f'Z diagramu doboru uzyskano {drive}. Jest to wartość '
                                     'do doboru zespołu napędowego; wybór konkretnego silnika wymaga jego charakterystyk.')
    else:
        conclusions['p2'].append('Dla szybowca pominięto dobór mocy i paliwową interpretację zasięgu. '
                                 'Podstawą oceny misji pozostają prędkość i opadanie w locie ślizgowym.')
    margin = balance['stability']['static_margin_aft_pct']
    conclusions['p3'].append(
        f'W rozpatrzonych stanach załadowania środek masy zajmuje położenia '
        f'{number(balance["cg_range"]["forward_pct"], 1)}–{number(balance["cg_range"]["aft_pct"], 1)}% ŚDA. '
        f'Najmniejszy zapas stateczności statycznej wynosi {number(margin, 1)}% ŚDA. '
        + ('Przyjęte kryterium 5% ŚDA jest spełnione.' if margin >= 5 else
           'Kryterium 5% ŚDA nie jest spełnione; konieczna jest korekta rozmieszczenia mas lub usterzenia.'))
    controls = geom['control_surfaces']
    conclusions['p4'].append(
        f'Dla konfiguracji gładkiej obliczono prędkość przeciągnięcia '
        f'{number(perf["speeds"]["vs_clean_kmh"], 1)} km/h, a dla konfiguracji do lądowania '
        f'{number(perf["speeds"]["vs_lnd_kmh"], 1)} km/h. '
        f'Współczynniki oporu zerowego wynoszą odpowiednio {number(aero["cx0_clean"], 4)} '
        f'oraz {number(aero["cx0_lnd"], 4)}.')
    if not controls['ailerons']['roll_authority_ok']:
        conclusions['p4'].append('Oszacowana skuteczność lotek jest mniejsza od przyjętego kryterium. '
                                 'Należy zwiększyć ich wymiary lub wychylenie i ponownie sprawdzić sterowność poprzeczną.')
    else:
        conclusions['p4'].append('Oszacowanie skuteczności lotek spełnia przyjęte kryterium modelu; '
                                 'wynik wymaga sprawdzenia z uwzględnieniem rzeczywistej kinematyki sterowania.')
    if powered:
        climb = perf['climb']['wy_max_ms']
        conclusions['p5'].append(
            f'Na poziomie morza uzyskano prędkość wznoszenia {number(climb)} m/s '
            f'wobec wymaganych {number(p["climb_rate_ms"])} m/s. '
            + ('Warunek wznoszenia jest spełniony.' if climb >= p['climb_rate_ms'] else
               'Warunek wznoszenia nie jest spełniony; należy zmienić moc lub obciążenie powierzchni.'))
        conclusions['p5'].append(
            f'Obliczony rozbieg wynosi {number(perf["takeoff"]["ground_roll_m"], 1)} m, '
            f'a start nad przeszkodę 15 m wymaga {number(perf["takeoff"]["distance_to_15m"], 1)} m. '
            'Z wymaganiem porównano całkowitą długość startu, łącznie z odcinkiem powietrznym.')
        if p.get('operating_surface') == 'water':
            conclusions['p5'][-1] = perf['takeoff']['note']
    else:
        glide = perf['glide']
        conclusions['p5'].append(
            f'Przy wysokości {number(glide["altitude_m"], 0)} m najmniejsze opadanie wynosi '
            f'{number(glide["minimum_sink"]["sink_ms"])} m/s. Prędkość najlepszej doskonałości '
            f'wynosi {number(glide["best_glide"]["v_kmh"], 1)} km/h TAS. '
            'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano.')
    limits = env['limits']
    gust_governs = (limits['n_gust_max'] > limits['n_max'] or limits['n_gust_min'] < limits['n_min'])
    conclusions['p6'].append(
        f'Obwiednia manewrowa obejmuje przeciążenia od {number(limits["n_min"])} '
        f'do +{number(limits["n_max"])}. Po uwzględnieniu podmuchów zakres obciążeń '
        f'dopuszczalnych do wymiarowania wynosi {number(limits["n_dimensioning_neg"])} '
        f'do +{number(limits["n_dimensioning_pos"])}. '
        + ('Wymiarujące są również obciążenia podmuchowe.' if gust_governs else
           'W rozpatrzonym modelu podmuchy nie powiększają skrajnych przeciążeń manewrowych.'))
    conclusions['p6'].append('Obciążenia niszczące wyznaczono z obciążeń dopuszczalnych '
                             f'przy współczynniku bezpieczeństwa {number(limits["safety_factor_nu"], 1)}. '
                             'Sama obwiednia nie określa wytrzymałości zaprojektowanej struktury.')
    summary = [('Masa startowa', mass['m0'], 'kg', 1),
               ('Masa własna', mass['m_empty'], 'kg', 1),
               ('Powierzchnia skrzydła', geom['wing']['S'], 'm²', 2),
               ('Rozpiętość skrzydła', geom['wing']['b'], 'm', 2),
               ('Maksymalna doskonałość', aero['k_max'], '—', 1)]
    if len(sections) == 1:
        key = sections[0]
        if key == 'p2':
            summary = summary[:2] + [('Masa paliwa', mass['m_fuel'], 'kg', 1), summary[2]]
            if powered:
                summary.append(('Ciąg startowy', results['sizing']['design_point']['thrust_kn'], 'kN', 2)
                               if p['engine_type'] == 'jet' else
                               ('Moc startowa', results['sizing']['design_point']['power_kw'], 'kW', 1))
        elif key == 'p3':
            summary = summary[2:4] + [('Średnia cięciwa aerodynamiczna', geom['wing']['mac'], 'm', 3),
                ('Przednie położenie środka masy', balance['cg_range']['forward_pct'], '% ŚDA', 1),
                ('Tylne położenie środka masy', balance['cg_range']['aft_pct'], '% ŚDA', 1),
                ('Najmniejszy zapas stateczności', margin, '% ŚDA', 1)]
        elif key == 'p4':
            summary = [('Opór zerowy — konfiguracja gładka', aero['cx0_clean'], '—', 4),
                       ('Współczynnik oporu indukowanego', aero['k_clean'], '—', 5), summary[-1],
                       ('Maksymalny Cz — konfiguracja gładka', aero['cz_max_clean'], '—', 2),
                       ('Maksymalny Cz — do lądowania', aero['cz_max_lnd'], '—', 2)]
        elif key == 'p5':
            summary = [('Przeciągnięcie — do lądowania', perf['speeds']['vs_lnd_kmh'], 'km/h', 1),
                       ('Prędkość najlepszej doskonałości', perf['glide']['best_glide']['v_kmh'], 'km/h TAS', 1),
                       ('Minimalne opadanie', perf['glide']['minimum_sink']['sink_ms'], 'm/s', 2)]
            if powered:
                summary += [('Maksymalna prędkość wznoszenia', perf['climb']['wy_max_ms'], 'm/s', 2),
                            ('Całkowita droga startu do 15 m', perf['takeoff']['distance_to_15m'], 'm', 1),
                            ('Pułap praktyczny', perf['ceiling']['service_ceiling_m'], 'm', 0)]
        elif key == 'p6':
            summary = [('Prędkość manewrowa VA', env['speeds']['v_a_kmh'], 'km/h', 1),
                       ('Prędkość obliczeniowa VC', env['speeds']['v_c_kmh'], 'km/h', 1),
                       ('Prędkość nurkowania VD', env['speeds']['v_d_kmh'], 'km/h', 1),
                       ('Dodatnie obciążenie do wymiarowania', limits['n_dimensioning_pos'], '—', 2),
                       ('Ujemne obciążenie do wymiarowania', limits['n_dimensioning_neg'], '—', 2)]
    configuration = {'low': 'dolnopłata', 'high': 'górnopłata',
                     'braced_high': 'górnopłata zastrzałowego', 'mid': 'średniopłata'}
    concept = f'Przyjęto układ {configuration.get(geom["wing"]["wing_config"], "jednopłata")}'
    concept += f'. Wybrany obrys skrzydła: {geom["wing"]["planform_name_pl"].lower()}. '
    if powered:
        drive = 'odrzutowy' if p['engine_type'] == 'jet' else 'śmigłowy'
        location = {'nose': 'z przodu kadłuba', 'rear': 'w tylnej części kadłuba',
                    'wing': 'w gondolach skrzydłowych', 'pusher': 'w układzie pchającym',
                    'pod': 'w gondoli'}.get(p.get('engine_location'), 'w przyjętym położeniu')
        concept += f'Napęd {drive} rozmieszczono {location}. '
    else:
        concept += 'Rozpatrywany wariant nie ma napędu własnego. '
    concept += (f'Załoga: {mass["n_crew"]} os.; pasażerowie: {mass["n_pax"]} os. '
                if not mass['unmanned'] else 'Statek powietrzny jest bezzałogowy. ')
    concept += f'Łączna masa załogi i ładunku wynosi {number(mass["m_crew"] + mass["m_payload"], 1)} kg.'
    geometry_sample = {}
    geometry = trends.get('geometry_trends_analysis')
    if geometry:
        for metric in geometry['metrics']:
            for sample in metric['samples']:
                row = geometry_sample.setdefault(sample['model'], {'model': sample['model'], 'values': {}, 'sources': []})
                row['values'][metric['key']] = sample['val']
                if sample['source'] not in row['sources']:
                    row['sources'].append(sample['source'])
    return {'sections': sections, 'titles': TITLES, 'metadata': report_metadata(p, overrides),
            'folder_cover': folder_cover, 'powered': powered, 'conclusions': conclusions,
            'checks': checks, 'failed': failed, 'pending': pending, 'summary': summary,
            'geometry_sample': list(geometry_sample.values()),
            'concept': concept, 'scope_limitations': results.get('model_scope', {}).get('limitations', []),
            'title': TITLES[sections[0]] if len(sections) == 1 else 'Projekt wstępny statku powietrznego'}
