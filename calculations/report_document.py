"""Warstwa redakcyjna sprawozdania: opis koncepcji, wnioski i zestawienia z jednego wyniku obliczeń."""
from datetime import date
import math
import re

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
CONFIGURATION = {'low': 'dolnopłat', 'high': 'górnopłat', 'braced_high': 'górnopłat zastrzałowy', 'mid': 'średniopłat'}
ENGINE_PLACE = {'nose': 'z przodu kadłuba', 'rear': 'w tylnej części kadłuba', 'wing': 'w gondolach skrzydłowych',
                'pusher': 'w układzie pchającym', 'pod': 'w gondoli'}


def report_number(value, digits=2):
    """Polish decimal punctuation and stable precision, including missing values."""
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return '—'
    return f'{value:,.{digits}f}'.replace(',', ' ').replace('.', ',')


def tex_number(value, digits=2):
    return report_number(value, digits).replace(',', '{,}').replace(' ', r'\,')


def report_metadata(params, overrides=None, today=None):
    today = today or date.today()
    year = today.year if today.month >= 10 else today.year - 1
    defaults = {'submission_date': today.strftime('%d.%m.%Y'),
                'academic_year': f'{year}/{str(year + 1)[-2:]}'}
    overrides = overrides or {}
    return [{'key': key, 'label': label,
             'value': str(overrides.get(query) or params.get(key) or defaults.get(key, '')).strip()}
            for key, label, query in METADATA]


def _row(label, value, unit='', digits=2):
    return {'label': label, 'value': value, 'unit': unit, 'digits': digits}


def assumption_rows(sheet, sections):
    """Wymagania, założenia, warunki brzegowe i przepisy użyte w wybranych częściach projektu."""
    from calculations.report_origin import ASSUMED, CATEGORY, classify
    if sheet is None:
        return []
    used = set()
    for key in sheet.order:
        entry = sheet.entries[key]
        if entry['project'] in sections:
            used.add(key)
            used.update(dep for dep in entry['deps'] if not dep.startswith('@'))
    rows = []
    for key in sheet.order:
        entry = sheet.entries[key]
        if key not in used or entry['kind'] != 'given' or entry['project'] == 'const':
            continue
        category, text = classify(entry)
        if category in ASSUMED:
            rows.append({'entry': entry, 'kind': CATEGORY[category], 'category': category, 'text': text})
    order = {c: i for i, c in enumerate(ASSUMED)}
    return sorted(rows, key=lambda r: order[r['category']])


def constant_rows(sheet):
    return [] if sheet is None else sheet.section_entries('const.const')


def _clean_check(check):
    """Kryterium w języku sprawozdania: bez znaczników roboczych, z przecinkiem dziesiętnym."""
    name = re.sub(r'^\[[^\]]+\]\s*', '', check['parameter']).replace(' (BIPOL_3)', '')
    name = re.sub(r'\s?\bP[1-6]\b', '', name).replace('biegunowej i osiągów', 'biegunowej i osiągów samolotu')
    name = name.replace('położeń ŚC', 'położeń środka masy').replace('(tylne ŚM)', '(tylne położenie środka masy)')
    decimal = lambda text: re.sub(r'(?<=\d)\.(?=\d)', ',', str(text)).replace(' pax', ' pas.')  # noqa: E731
    return {**check, 'parameter': name, 'required': decimal(check['required']).replace('ŚDA', 'ŚCA'),
            'actual': decimal(check['actual']).replace('ŚDA', 'ŚCA')}


def _relevant_checks(results, sections):
    checks = []
    for check in results['compliance_checks']:
        name = check['parameter']
        # Klasyfikacja programu i zalecenia certyfikacyjne nie są kryteriami tego opracowania.
        if '_' in str(check['required']):
            continue
        relevant = ('p1' in sections and 'stateczności' not in name)
        relevant |= ('p5' in sections and not name.startswith('[') and 'stateczności' not in name)
        relevant |= ('p3' in sections and ('stateczności' in name or 'ŚC' in name))
        relevant |= (bool({'p4', 'p5'} & set(sections)) and name.startswith('[Ściśliwość]'))
        if relevant:
            checks.append(_clean_check(check))
    return checks


def _concept(results):
    p, mass, geom = results['params'], results['mass'], results['geometry']
    number, wing = report_number, geom['wing']
    powered, jet = p['engine_type'] != 'none', p['engine_type'] == 'jet'
    controls = geom.get('control_surfaces', {})
    layout = CONFIGURATION.get(wing['wing_config'], 'jednopłat')
    noun = 'Samolot' if powered else 'Szybowiec'
    text = [f'{noun} zaprojektowano w układzie klasycznym jako {layout} z usterzeniem w tylnej części kadłuba. '
            f'Skrzydło ma obrys {wing["planform_name_pl"].lower()}, wydłużenie {number(wing["AR"])} '
            f'i zbieżność {number(wing["eta"])}.'
            + (f' Mechanizację skrzydła stanowią: {controls["flaps"]["name"].lower()}; sterowanie poprzeczne — '
               f'{controls["ailerons"]["name"].lower()}.' if controls.get('flaps') and controls.get('ailerons') else '')]
    if powered:
        engines = int(p.get('n_engines', 1) or 1)
        kind = ('odrzutowy' if jet else 'turbośmigłowy' if p.get('aircraft_type') == 'turboprop_regional'
                else 'tłokowy ze śmigłem')
        place = ENGINE_PLACE.get(p.get('engine_location'), 'w przyjętym położeniu')
        text.append(f'Napęd stanowi {"jeden silnik" if engines == 1 else f"{engines} silniki"} {kind} '
                    f'umieszczony{"" if engines == 1 else "e"} {place}.')
    else:
        text.append('Szybowiec nie ma napędu własnego; start odbywa się za holem lub z wyciągarki.')
    gear = {'fuselage': 'do kadłuba', 'wing': 'do skrzydła'}.get(p.get('gear_attachment'))
    if gear:
        text.append(f'Podwozie główne mocowane jest {gear}.')
    if mass['unmanned']:
        text.append(f'Samolot jest bezzałogowy; masa wyposażenia zadaniowego wynosi {number(mass["m_payload"], 1)} kg.')
    else:
        crew = 'członka' if mass['n_crew'] == 1 else 'członków'
        pax = (f' i {mass["n_pax"]} {"pasażera" if mass["n_pax"] == 1 else "pasażerów"}' if mass['n_pax'] else '')
        text.append(f'Kabina mieści {mass["n_crew"]} {crew} załogi{pax}; łączna masa załogi i ładunku wynosi '
                    f'{number(mass["m_crew"] + mass["m_payload"], 1)} kg.')
    pp = mass['preliminary_polar']
    text.append((f'Na tym etapie maksymalną doskonałość odczytano z wykresu jako {number(pp["kmax"], 1)}, co odpowiada oporowi zerowemu '
                 if pp['mode'] != 'input' else f'Na tym etapie maksymalną doskonałość oszacowano na {number(pp["kmax"], 1)} przy oporze zerowym ')
                + f'{number(pp["cx0"], 4)}. Najważniejsze wymagania osiągowe to prędkość przelotowa '
                f'{number(p["cruise_speed_kmh"], 0)} km/h na wysokości {number(p["cruise_altitude_m"], 0)} m'
                + (f', zasięg {number(p["range_km"], 0)} km' if powered else '')
                + f' oraz prędkość przeciągnięcia nie większa niż {number(p["v_stall_kmh"], 0)} km/h.')
    return text


def _predecessors(results):
    """Porównanie najważniejszych proporcji projektu z wartościami wynikającymi z analizy trendów."""
    p, mass, wing = results['params'], results['mass'], results['geometry']['wing']
    dp = results['sizing']['design_point']
    suggestions = results['bipol_projects']['p1']['trend_analysis'].get('suggestions', {})
    jet, m0 = p['engine_type'] == 'jet', mass['m0']
    # Projekt koncepcyjny porównuje tylko parametry wybrane na tym etapie (bez wyników bilansu i doboru).
    rows = [('ar', 'Wydłużenie skrzydła Λ', '—', mass['preliminary_polar']['aspect_ratio'], 2)]
    out = []
    for key, label, unit, value, digits in rows:
        reference = (suggestions.get(key) or {}).get('suggested_value')
        if reference and value is not None:
            out.append({'label': label, 'unit': unit, 'project': value, 'reference': reference, 'digits': digits,
                        'delta': 100 * (value / reference - 1),
                        'method': suggestions[key].get('provenance', {}).get('method', '')})
    return out


def _conclusions(results):
    p, mass = results['params'], results['mass']
    aero, perf, balance, env = results['aerodynamics'], results['performance'], results['balance'], results['envelope']
    trends = results['bipol_projects']['p1']['trend_analysis']
    number, powered, jet = report_number, p['engine_type'] != 'none', p['engine_type'] == 'jet'
    pp, dp = mass['preliminary_polar'], results['sizing']['design_point']
    out = {key: [] for key in TITLES}
    if pp['mode'] != 'input':
        low, high = pp['cx0_bounds']
        out['p1'].append(f'Do dalszych obliczeń przyjęto wydłużenie skrzydła {number(pp["aspect_ratio"])} i szacunkową '
                         f'biegunową o maksymalnej doskonałości {number(pp["kmax"], 1)} odczytanej z wykresu dla '
                         f'S_wet/S = {number(pp["swet_ratio"], 2)}, z której opór zerowy wynosi {number(pp["cx0"], 4)}; '
                         + (f'wartość mieści się w przedziale typowym {number(low, 3)}–{number(high, 3)}.' if pp['cx0_in_range'] else
                            f'wartość leży poza przedziałem typowym {number(low, 3)}–{number(high, 3)} '
                            f'o {number(abs(pp["cx0_deviation"]) * 100, 0)}%.'))
    else:
        out['p1'].append(f'Do dalszych obliczeń przyjęto wydłużenie skrzydła {number(pp["aspect_ratio"])} i szacunkową '
                         f'biegunową o oporze zerowym {number(pp["cx0"], 4)}, co daje maksymalną doskonałość '
                         f'{number(pp["kmax"], 1)}.')
    if trends['mass_fit']:
        fitted_law = mass['empty_mass_model'] in ('trend', 'bipol1_trend') and all(
            math.isclose(mass['empty_mass_law'][key], trends['mass_fit'][key], rel_tol=1e-9)
            for key in ('A', 'C'))
        out['p1'].append(f'Zależność udziału masy pustej od masy startowej wyznaczono z {trends["mass_fit"]["n"]} par '
                         f'danych (R² = {number(trends["mass_fit"]["r2"], 3)}). '
                         + ('Tę zależność wprowadzono do bilansu masy w studium wykonalności.' if fitted_law else
                            'Rozrzut danych jest duży, dlatego masy pustej nie oparto wyłącznie na tej zależności.'
                            if trends['mass_fit']['r2'] < .5 else
                            'Zależność potraktowano jako punkt odniesienia przy doborze udziałów mas.'))
    else:
        out['p1'].append('Zebrana próba nie pozwoliła wyznaczyć wiarygodnej zależności masowej; masę pustą '
                         'oszacowano z bilansu masy i korelacji dla klasy samolotu.')
    residual = mass['mission_assumptions']['mass_residual_relative'] * 100
    out['p2'].append(f'Bilans masowy daje masę startową {number(mass["m0"], 1)} kg, w tym '
                     f'{number(mass["m_empty"], 1)} kg masy własnej i {number(mass["m_fuel"], 1)} kg paliwa. '
                     f'Względna reszta równania wynosi {number(residual, 5)}%; '
                     + ('przyjęty próg 0,1% został osiągnięty.' if residual <= .1 else
                        'przyjętego progu 0,1% nie osiągnięto.'))
    if powered:
        drive = f'ciąg {number(dp["thrust_kn"])} kN' if jet else f'moc {number(dp["power_kw"], 1)} kW'
        if p.get('power_input_mode') == 'fixed' and not jet:
            out['p2'].append(f'Przyjęto moc wybranego silnika {number(dp["power_kw"], 1)} kW, wobec mocy wymaganej '
                             f'z wykresu doboru {number(dp["required_power_kw"], 1)} kW; osiągi sprawdzono dla mocy '
                             'rzeczywiście dostępnej.')
        else:
            out['p2'].append(f'Punkt projektowy wykresu doboru wyznacza obciążenie powierzchni {number(dp["ws"], 0)} N/m² '
                             f'(ograniczenie: {dp["limit_by"]}) i {drive}. Na tej podstawie należy wybrać konkretny silnik.')
    else:
        out['p2'].append('Dla szybowca pominięto dobór mocy i paliwową interpretację zasięgu. '
                         'Podstawą oceny misji pozostają prędkość i opadanie w locie ślizgowym.')
    margin = balance['stability']['static_margin_aft_pct']
    out['p3'].append(f'W rozpatrzonych stanach załadowania środek masy w locie zajmuje położenia '
                     f'{number(balance["cg_range"]["forward_pct"], 1)}–{number(balance["cg_range"]["aft_pct"], 1)}% ŚCA. '
                     f'Najmniejszy zapas stateczności statycznej wynosi {number(margin, 1)}% ŚCA. '
                     + ('Kryterium 5% ŚCA jest spełnione.' if margin >= 5 else
                        'Kryterium 5% ŚCA nie jest spełnione; konieczna jest korekta rozmieszczenia mas '
                        'lub powiększenie usterzenia poziomego.'))
    out['p4'].append(f'Prędkość przeciągnięcia wynosi {number(perf["speeds"]["vs_clean_kmh"], 1)} km/h w konfiguracji '
                     f'gładkiej i {number(perf["speeds"]["vs_lnd_kmh"], 1)} km/h w konfiguracji do lądowania. '
                     f'Współczynniki oporu zerowego wynoszą odpowiednio {number(aero["cx0_clean"], 4)} '
                     f'i {number(aero["cx0_lnd"], 4)}, a maksymalna doskonałość {number(aero["k_max"], 1)}.')
    polars = results['bipol_projects']['p4']['cg_characteristics']['speed_polars']
    out['p4'].append(f'Prędkość ekonomiczna lotu ślizgowego wynosi {number(polars["forward"]["v_ek_kmh"], 1)}–'
                     f'{number(polars["aft"]["v_ek_kmh"], 1)} km/h, a optymalna {number(polars["forward"]["v_opt_kmh"], 1)}–'
                     f'{number(polars["aft"]["v_opt_kmh"], 1)} km/h w zakresie położeń środka masy; przesunięcie środka masy '
                     'do przodu zwiększa opór wyważenia.')
    if powered:
        climb = perf['climb']['wy_max_ms']
        out['p5'].append(f'Na poziomie morza uzyskano prędkość wznoszenia {number(climb)} m/s wobec wymaganych '
                         f'{number(p["climb_rate_ms"])} m/s. '
                         + ('Warunek wznoszenia jest spełniony.' if climb >= p['climb_rate_ms'] else
                            'Warunek wznoszenia nie jest spełniony; należy zwiększyć moc (ciąg) albo zmniejszyć '
                            'obciążenie powierzchni.'))
        out['p5'].append(perf['takeoff']['note'] if p.get('operating_surface') == 'water' else
                         f'Rozbieg wynosi {number(perf["takeoff"]["ground_roll_m"], 1)} m, a start do wysokości 15 m '
                         f'wymaga {number(perf["takeoff"]["distance_to_15m"], 1)} m. Z wymaganiem porównano całkowitą '
                         'długość startu.')
    else:
        glide = perf['glide']
        out['p5'].append(f'Na wysokości {number(glide["altitude_m"], 0)} m najmniejsze opadanie wynosi '
                         f'{number(glide["minimum_sink"]["sink_ms"])} m/s, a prędkość najlepszej doskonałości '
                         f'{number(glide["best_glide"]["v_kmh"], 1)} km/h TAS. Wznoszenia z napędem i samodzielnego '
                         'startu nie rozpatrywano.')
    limits = env['limits']
    gust_governs = limits['n_gust_max'] > limits['n_max'] or limits['n_gust_min'] < limits['n_min']
    out['p6'].append(f'Obwiednia manewrowa obejmuje współczynniki obciążenia od {number(limits["n_min"])} do '
                     f'+{number(limits["n_max"])}. Po uwzględnieniu podmuchów zakres obciążeń dopuszczalnych do '
                     f'wymiarowania wynosi od {number(limits["n_dimensioning_neg"])} do '
                     f'+{number(limits["n_dimensioning_pos"])}. '
                     + ('Wymiarujące są również obciążenia podmuchowe.' if gust_governs else
                        'Podmuchy nie powiększają skrajnych obciążeń manewrowych.'))
    out['p6'].append('Obciążenia niszczące wyznaczono z obciążeń dopuszczalnych przy współczynniku bezpieczeństwa '
                     f'{number(limits["safety_factor_nu"], 1)}. Obwiednia jest podstawą obliczeń wytrzymałościowych '
                     'struktury, które stanowią kolejny etap prac.')
    return out


def _summaries(results):
    """Tabele podsumowań projektów: wyniki przekazywane do kolejnych etapów."""
    p, mass, geom = results['params'], results['mass'], results['geometry']
    aero, perf, balance, env = results['aerodynamics'], results['performance'], results['balance'], results['envelope']
    projects = results['bipol_projects']
    number, powered, jet = report_number, p['engine_type'] != 'none', p['engine_type'] == 'jet'
    wing, pp, dp = geom['wing'], mass['preliminary_polar'], results['sizing']['design_point']
    out = {}
    layout = CONFIGURATION.get(wing['wing_config'], 'jednopłat')
    drive = (f', napęd {"odrzutowy" if jet else "śmigłowy"} {ENGINE_PLACE.get(p.get("engine_location"), "")}'.rstrip()
             if powered else ', bez napędu')
    out['p1'] = [_row('Układ samolotu', f'{layout}, skrzydło {wing["planform_name_pl"].lower()}{drive}', '', None),
                 _row('Załoga / pasażerowie', f'{mass["n_crew"]} / {mass["n_pax"]}', 'os.', None),
                 _row('Masa załogi i ładunku', mass['m_crew'] + mass['m_payload'], 'kg', 1),
                 _row('Wydłużenie skrzydła Λ', pp['aspect_ratio'], '—', 2),
                 _row('Współczynnik Oswalda e', pp['oswald_e'], '—', 2),
                 _row('Opór zerowy (oszacowanie) C_x0', pp['cx0'], '—', 4),
                 _row('Maksymalna doskonałość (oszacowanie) K_max', pp['kmax'], '—', 1)]
    if pp.get('swet_ratio'):
        out['p1'].append(_row('Stosunek powierzchni omywanej do odniesienia S_wet/S', pp['swet_ratio'], '—', 2))
    two = projects['p1']['trend_analysis'].get('two_point') or {}
    if two:
        out['p1'] += [_row('Zależność mₑ/m₀ = A·m₀^C — współczynnik A', two.get('A'), '—', 4),
                      _row('Zależność mₑ/m₀ = A·m₀^C — wykładnik C', two.get('C'), '—', 4)]
    out['p2'] = [_row('Masa startowa m₀', mass['m0'], 'kg', 1), _row('Masa własna mₑ', mass['m_empty'], 'kg', 1),
                 _row('Masa paliwa m_f', mass['m_fuel'], 'kg', 1), _row('Obciążenie powierzchni W/S', dp['ws'], 'N/m²', 0),
                 _row('Powierzchnia nośna S', wing['S'], 'm²', 2)]
    if powered:
        out['p2'] += ([_row('Stosunek ciągu do ciężaru T/W', dp['tw'], '—', 3), _row('Ciąg startowy T', dp['thrust_kn'], 'kN', 2)]
                      if jet else [_row('Obciążenie mocą N/W', dp['pw'], 'W/N', 2), _row('Moc startowa N', dp['power_kw'], 'kW', 1)])
    airfoil = projects['p2']['airfoil_selection']['selected_airfoil']
    out['p2'].append(_row('Profil skrzydła', airfoil, '', None))
    cost = projects['p2'].get('cost_analysis') or {}
    if cost.get('unit_cost_usd'):
        out['p2'] += [_row(f'Koszt wytworzenia egzemplarza (rok {cost.get("cost_year")})', cost['unit_cost_usd'], 'USD', 0),
                      _row('Cena sprzedaży z zyskiem', cost.get('selling_price_usd'), 'USD', 0)]
    p2w, schrenk = projects['paturski_ml']['p2_wing_aero'], projects['p3']['schrenk_summary']
    ht, vt, fus = geom['horizontal_tail'], geom['vertical_tail'], geom['fuselage']
    out['p3'] = [_row('Rozpiętość b', wing['b'], 'm', 2), _row('Powierzchnia nośna S', wing['S'], 'm²', 2),
                 _row('Wydłużenie Λ', wing['AR'], '—', 2), _row('Zbieżność λ', wing['eta'], '—', 2),
                 _row('Cięciwa przykadłubowa / końcowa', f'{number(wing["cr"], 3)} / {number(wing["ct"], 3)}', 'm', None),
                 _row('Średnia cięciwa aerodynamiczna', wing['mac'], 'm', 3),
                 _row('Długość / średnica kadłuba', f'{number(fus["length"], 2)} / {number(fus["diameter"], 2)}', 'm', None),
                 _row('Usterzenie poziome: powierzchnia / ramię', f'{number(ht["S_h"], 2)} m² / {number(ht["l_h"], 2)} m', '', None),
                 _row('Usterzenie pionowe: powierzchnia / ramię', f'{number(vt["S_v"], 2)} m² / {number(vt["l_v"], 2)} m', '', None),
                 _row('Środek masy w locie: przednie – tylne położenie',
                      f'{number(balance["cg_range"]["forward_pct"], 1)} – {number(balance["cg_range"]["aft_pct"], 1)}', '% ŚCA', None),
                 _row('Najmniejszy zapas stateczności', balance['stability']['static_margin_aft_pct'], '% ŚCA', 1),
                 _row('Gradient siły nośnej płata a', p2w['a_wing_paturski_rad'], '1/rad', 3),
                 _row('Kąt zerowej siły nośnej płata α₀', p2w['alpha_0_deg'], '°', 2),
                 _row('Największe lokalne c_z/C_z (rozkład Schrenka)', schrenk['max_cz1'], '—', 3)]
    if schrenk.get('cz_max_wing_est'):
        out['p3'].append(_row('Maksymalny C_z płata oszacowany z rozkładu Schrenka', schrenk['cz_max_wing_est'], '—', 3))
    out['p3'].append(_row('Profil skrzydła', airfoil, '', None))
    polars = projects['p4']['cg_characteristics']['speed_polars']
    out['p4'] = [_row('Opór zerowy C_x0 (konfiguracja gładka)', aero['cx0_clean'], '—', 4),
                 _row('Współczynnik oporu indukowanego k', aero['k_clean'], '—', 5),
                 _row('Współczynnik Oswalda e', aero['oswald_e'], '—', 3),
                 _row('Maksymalna doskonałość K_max', aero['k_max'], '—', 2),
                 _row('C_z przy K_max', aero['cz_opt'], '—', 3),
                 _row('Największa funkcja energetyczna E_max', aero['e_energy_max'], '—', 1),
                 _row('C_z,max: gładka / startowa / do lądowania',
                      f'{number(aero["cz_max_clean"], 2)} / {number(aero["cz_max_to"], 2)} / {number(aero["cz_max_lnd"], 2)}', '—', None),
                 _row('V_ek / V_opt — przednie położenie środka masy',
                      f'{number(polars["forward"]["v_ek_kmh"], 1)} / {number(polars["forward"]["v_opt_kmh"], 1)}', 'km/h', None),
                 _row('V_ek / V_opt — tylne położenie środka masy',
                      f'{number(polars["aft"]["v_ek_kmh"], 1)} / {number(polars["aft"]["v_opt_kmh"], 1)}', 'km/h', None)]
    propeller = projects['p4']['paturski_propulsion'].get('propeller_selection') or {}
    if propeller:
        out['p4'] += [_row('Średnica śmigła D', propeller['diameter_m'], 'm', 2),
                      _row('Prędkość obrotowa śmigła', propeller['rpm_prop'], 'obr/min', 0),
                      _row('Liczba Macha końca łopaty', propeller['ma_tip_kl'], '—', 3)]
    if powered:
        ml6 = projects['paturski_ml']['p6_performance_paturski']
        offer, ranges, ceil = ml6['offer_chart_summary'], ml6['range_endurance_6_5'], projects['p5']['ceiling_summary']
        out['p5'] = [_row('Prędkość maksymalna przy ziemi', perf['speeds']['v_max_sl_kmh'], 'km/h', 1),
                     _row('Prędkość minimalna przy ziemi', perf['speeds']['vs_clean_kmh'], 'km/h', 1),
                     _row('Największa prędkość wznoszenia przy ziemi', offer['w_max_h0_ms'], 'm/s', 2),
                     _row('Największy kąt wznoszenia przy ziemi', offer['gamma_max_h0_deg'], '°', 1),
                     _row('Pułap teoretyczny / praktyczny', f'{number(ceil["ht_theoretical_m"], 0)} / {number(ceil["hp_service_m"], 0)}', 'm', None),
                     _row('Czas wznoszenia na pułap praktyczny', ceil['thp_min'], 'min', 1),
                     _row('Zasięg przy prędkości przelotowej', ranges.get('range_at_requested_speed_km'), 'km', 0),
                     _row('Długotrwałość przy prędkości przelotowej', ranges.get('endurance_at_requested_speed_h'), 'h', 2),
                     _row('Długość / czas startu do 15 m',
                          f'{number(perf["takeoff"]["distance_to_15m"], 0)} m / {number(perf["takeoff"].get("time_to_15m_s"), 1)} s', '', None),
                     _row('Długość lądowania znad 15 m', perf['landing']['distance_from_15m'], 'm', 0)]
        est = projects['p1'].get('t_req_est_kn' if jet else 'p_req_est_kw')
        if est is not None:
            out['p5'].insert(1, _row('Ciąg niezbędny w przelocie' if jet else 'Moc niezbędna w przelocie (na wale)',
                                     est, 'kN' if jet else 'kW', 2 if jet else 1))
    else:
        glide = perf['glide']
        out['p5'] = [_row('Prędkość przeciągnięcia', perf['speeds']['vs_clean_kmh'], 'km/h', 1),
                     _row('Najmniejsze opadanie', glide['minimum_sink']['sink_ms'], 'm/s', 2),
                     _row('Prędkość najmniejszego opadania', glide['minimum_sink']['v_kmh'], 'km/h', 1),
                     _row('Maksymalna doskonałość', glide['best_glide']['ld'], '—', 1),
                     _row('Prędkość najlepszej doskonałości', glide['best_glide']['v_kmh'], 'km/h', 1)]
    speeds, limits = env['speeds'], env['limits']
    out['p6'] = [_row(label, speeds[key], 'km/h EAS', 1) for key, label in (
        ('v_s_kmh', 'V_S1 — prędkość przeciągnięcia bez klap'), ('v_a_kmh', 'V_A — prędkość manewrowa'),
        ('v_b_kmh', 'V_B — prędkość dla podmuchu o największej intensywności'),
        ('v_c_kmh', 'V_C — prędkość przelotowa obliczeniowa'), ('v_d_kmh', 'V_D — prędkość nurkowania obliczeniowa'),
        ('v_f_kmh', 'V_F — prędkość z wychyloną mechanizacją')) if speeds.get(key) is not None]
    pair = lambda a, b: f'+{number(limits[a])} / {number(limits[b])}'  # noqa: E731
    out['p6'] += [_row('Dopuszczalny współczynnik obciążenia manewrowego: dodatni / ujemny', pair('n_max', 'n_min'), '—', None),
                  _row('Współczynnik obciążenia od podmuchów: dodatni / ujemny', pair('n_gust_max', 'n_gust_min'), '—', None),
                  _row('Obciążenie do wymiarowania: dodatnie / ujemne', pair('n_dimensioning_pos', 'n_dimensioning_neg'), '—', None),
                  _row('Obciążenie niszczące: dodatnie / ujemne', pair('n_ult_pos', 'n_ult_neg'), '—', None)]
    if env['flap'].get('applicable'):
        out['p6'].append(_row('Współczynnik obciążenia z wychyloną mechanizacją n_F', env['flap']['n_flap'], '—', 2))
    return out


def _performance_actions(results):
    """Elementy projektu do poprawy, wynikające z niespełnionych wymagań osiągowych."""
    p, perf, aero = results['params'], results['performance'], results['aerodynamics']
    ml6 = results['bipol_projects']['paturski_ml']['p6_performance_paturski']
    cruise_alt = next((row for row in ml6['range_endurance_6_5'].get('by_altitude', [])
                       if row['label'] == 'wysokość przelotowa'), None)
    number, out = report_number, []
    for row in results['bipol_projects']['p5']['critical_evaluation_table_5_1']:
        if row['comment'] != 'Niespełnione wymaganie projektu':
            continue
        name = row['param']
        got = number(row['actual_calc'], 1) if row['actual_calc'] is not None else 'brak wyniku'
        lead = f'{name}: wymagano {number(row["project_assumed"], 1)}, uzyskano {got}. '
        if name.startswith('Prędkość przelotowa'):
            check = perf['cruise_check']
            out.append(lead + f'Na wysokości {number(check["altitude_m"], 0)} m moc potrzebna do lotu '
                       f'({number(check["required_w"] / 1000, 0)} kW) przekracza moc dostępną '
                       f'({number(check["available_w"] / 1000, 0)} kW). Należy zwiększyć moc zespołu napędowego '
                       'albo zmniejszyć prędkość lub wysokość przelotu.')
        elif name.startswith('Prędkość wznoszenia'):
            out.append(lead + 'Należy zwiększyć moc (ciąg) zespołu napędowego albo zmniejszyć obciążenie powierzchni.')
        elif name.startswith('Całkowita długość startu'):
            out.append(lead + 'Należy zwiększyć współczynnik siły nośnej do startu (mechanizację), moc (ciąg) '
                       'albo powierzchnię nośną.')
        elif name.startswith('Zasięg'):
            out.append(lead + f'Bilans paliwa przyjął w przelocie doskonałość 0,94 K_max, a biegunowa samolotu '
                       f'(C_x0 = {number(aero["cx0_clean"], 4)}) przy wymaganej prędkości daje mniejszą. '
                       + (f'Największy zasięg na wysokości przelotowej odpowiada prędkości około '
                          f'{number(cruise_alt["v_l_max_kmh"], 0)} km/h. ' if cruise_alt else '')
                       + 'Należy zmniejszyć prędkość przelotową w stronę prędkości największego zasięgu albo '
                       'powtórzyć bilans masy z doskonałością wynikającą z biegunowej samolotu (większy zapas paliwa).')
        else:
            out.append(lead)
    return out


def _limitation(text):
    """Ograniczenie zakresu obliczeń opisane bez odwołań do elementów programu."""
    if 'ΔCx,wave' in text or 'M_kr' in text:
        return ('Przelot z zadaną prędkością odbywa się powyżej oszacowanej krytycznej liczby Macha. Opór falowy '
                'nie jest dodany do biegunowej samolotu, dlatego osiągi i zasięg w tym punkcie są niezweryfikowane '
                'i wymagają biegunowej zależnej od liczby Macha.')
    return text


def report_document(results, sections, overrides=None, folder_cover=False, sheet=None):
    from calculations.trend_workings import report_trend_workings
    p, mass, geom = results['params'], results['mass'], results['geometry']
    number = report_number
    powered, jet = p['engine_type'] != 'none', p['engine_type'] == 'jet'
    checks = _relevant_checks(results, sections)
    if 'p2' in sections:
        residual_pct = mass['mission_assumptions']['mass_residual_relative'] * 100
        checks.append({'parameter': 'Zbieżność bilansu masy', 'required': '≤ 0,1%',
                       'actual': f'{number(residual_pct, 5)}%', 'passed': residual_pct <= .1})
    failed = [c for c in checks if not c['passed'] and c.get('severity') != 'warning']
    pending = [c for c in checks if not c['passed'] and c.get('severity') == 'warning']
    dp = results['sizing']['design_point']
    summary = [_row('Masa startowa', mass['m0'], 'kg', 1), _row('Masa własna', mass['m_empty'], 'kg', 1),
               _row('Powierzchnia skrzydła', geom['wing']['S'], 'm²', 2), _row('Rozpiętość skrzydła', geom['wing']['b'], 'm', 2),
               _row('Maksymalna doskonałość', results['aerodynamics']['k_max'], '—', 1)]
    if powered:
        summary.append(_row('Ciąg startowy' if jet else 'Moc startowa', dp['thrust_kn'] if jet else dp['power_kw'],
                            'kN' if jet else 'kW', 2 if jet else 1))
    return {'sections': sections, 'titles': TITLES, 'metadata': report_metadata(p, overrides),
            'folder_cover': folder_cover, 'powered': powered, 'jet': jet, 'conclusions': _conclusions(results),
            'checks': checks, 'failed': failed, 'pending': pending, 'summary': summary,
            'summaries': _summaries(results), 'predecessors': _predecessors(results),
            'performance_actions': _performance_actions(results),
            'trend_workings': report_trend_workings(results['bipol_projects']['p1']['trend_analysis']),
            'concept': _concept(results),
            'assumptions': assumption_rows(sheet, sections), 'constants': constant_rows(sheet),
            'scope_limitations': [_limitation(text) for text in results.get('model_scope', {}).get('limitations', [])],
            'title': TITLES[sections[0]] if len(sections) == 1 else 'Projekt wstępny samolotu'}
