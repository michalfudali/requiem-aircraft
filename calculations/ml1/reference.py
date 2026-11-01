"""ML1 P1: known aircraft data, provenance and measured three-view scale."""
from .validation import finite

SOURCE_URL='https://www.meil.pw.edu.pl/zm/content/download/25508/134259/file/Projekt_1.pdf'


def drawing_scale(reference_length_m,measured_length_mm,*,target_denominator=75):
    actual=finite(reference_length_m,'Rzeczywisty wymiar samolotu [m]',positive=True)
    measured=finite(measured_length_mm,'Wymiar na rysunku [mm]',positive=True)
    target=finite(target_denominator,'Mianownik docelowej podziałki',positive=True)
    if not 50<=target<=100:raise ValueError('Projekt 1 wymaga podziałki od 1:50 do 1:100.')
    current=1000*actual/measured
    return dict(method='ml1.p1.drawing_scale',source_url=SOURCE_URL,
                current_denominator=current,target_denominator=target,
                print_size_percent=100*current/target,
                target_length_mm=1000*actual/target,scale_bar_one_metre_mm=1000/target)


def known_aircraft(data):
    """Fixed measured masses bypass BIPOL's unrelated preliminary sizing loop."""
    if not isinstance(data,dict):raise ValueError('Dane samolotu muszą być obiektem.')
    name=str(data.get('name','')).strip()
    if not name:raise ValueError('Podaj nazwę i wariant samolotu.')
    sources=data.get('sources')
    if not isinstance(sources,list) or not sources or not all(isinstance(s,str) and s.strip() for s in sources):
        raise ValueError('Wpisz co najmniej jedno źródło danych, autora i stronę lub adres.')
    positive=['span_m','length_m','height_m','area_m2','empty_mass_kg','mtow_kg','flight_mass_kg']
    result={key:finite(data.get(key),key,positive=True) for key in positive}
    for key in ['fuel_mass_kg','payload_mass_kg']:
        result[key]=finite(data.get(key),key,nonnegative=True)
    if result['empty_mass_kg']>result['flight_mass_kg'] or result['flight_mass_kg']>result['mtow_kg']:
        raise ValueError('Masy muszą spełniać: pusta ≤ w locie ≤ maksymalna startowa.')
    if result['empty_mass_kg']+result['payload_mass_kg']>result['flight_mass_kg']:
        raise ValueError('Masa w locie nie pokrywa pustego samolotu i deklarowanego ładunku.')
    if result['fuel_mass_kg']>result['mtow_kg']-result['empty_mass_kg']:
        raise ValueError('Masa paliwa przekracza różnicę MTOW i masy pustej.')
    propulsion=data.get('propulsion')
    if propulsion not in ('propeller','jet','glider'):raise ValueError('Wybierz napęd propeller, jet lub glider.')
    reported=data.get('reported_performance',{})
    if not isinstance(reported,dict):raise ValueError('Osiągi źródłowe muszą być tabelą danych.')
    performance={key:finite(value,'Osiągi źródłowe '+key,nonnegative=True) for key,value in reported.items() if value is not None}
    return dict(method='ml1.p1.known_aircraft',source_url=SOURCE_URL,name=name[:200],**result,
                propulsion=propulsion,sources=sources,reported_performance=performance,
                aspect_ratio=result['span_m']**2/result['area_m2'],
                full_fuel_and_payload_fit=(result['empty_mass_kg']+result['payload_mass_kg']+result['fuel_mass_kg']<=result['mtow_kg']),
                notes=str(data.get('notes',''))[:10000],
                engine_data=data.get('engine_data',{}),profile_data=data.get('profile_data',{}),
                drawing=data.get('drawing',{}),mass_basis='known_aircraft_fixed_measurements')
