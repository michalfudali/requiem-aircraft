"""Kontrola rysunku samolotu według „Przykładowego schematu postępowania przy rysowaniu kadłuba"
(Schemat_projektu.pdf, C. Galiński) i BIPOL_3, kroki 1–15. Każdy wiersz podaje krok, wielkość,
wymaganie z materiałów i wartość projektu; rysunek odręczny pozostaje pracą autora.
"""
import math

from calculations.empennage import calculate_empennage_sizing
from calculations.landing_gear import PILOT_VISION_ANGLES


def _row(step, name, required, value, passed, basis):
    return dict(step=step, name=name, required=required, value=value, passed=passed, basis=basis)


def drawing_checks(result):
    p, g, bal = result['params'], result['geometry'], result['balance']
    wing, fus, ht, vt = g['wing'], g['fuselage'], g['horizontal_tail'], g['vertical_tail']
    metrics = result['engineering_audit']['metrics']
    blueprint = result['bipol_projects']['p3']['blueprint_checks']
    rows = []
    comma = lambda v, d=2: f'{v:.{d}f}'.replace('.', ',')  # noqa: E731
    unmanned = p.get('aircraft_type') == 'uav'
    if not unmanned:
        angle = PILOT_VISION_ANGLES.get('glider' if p.get('aircraft_type') in ('glider', 'motoglider') else p.get('aircraft_type'),
                                        PILOT_VISION_ANGLES['piston_ga'])['alpha_F_deg']
        rows.append(_row('2–3', 'Kąt widoczności pilota do przodu w dół', f'≥ {comma(angle, 0)}°', 'do wykazania na rysunku', None,
                         'wykład „kadłuby”; silnik i osłona poniżej linii widoczności (kroki 5–6)'))
    if p.get('engine_type') == 'prop':
        diameter, tip = blueprint.get('propeller_diameter_m'), blueprint.get('propeller_tip_mach')
        if tip is not None:
            rows.append(_row('7', 'Liczba Macha końcówki łopaty śmigła', '≤ 0,85', comma(tip, 3), tip <= .85, 'schemat rysowania, krok 7'))
        if diameter and p.get('engine_location', 'nose') == 'nose':
            needed = .18 if p.get('landing_gear_type') == 'tailwheel' else .23
            clearance = g['gear']['axis_height_m'] - diameter / 2
            rows.append(_row('10', 'Odległość końcówki śmigła od podłoża', f'≥ {comma(needed)} m', f'{comma(clearance)} m',
                             clearance >= needed - 1e-9, 'wykłady 4 i 7'))
    cg = bal['cg_range']
    rows.append(_row('8–9', 'Skrajne położenia środka masy w locie', '25–35% ŚCA',
                     f"{comma(cg['forward_pct'], 1)}–{comma(cg['aft_pct'], 1)}% ŚCA", bal['cg_check']['passed'], 'analiza masowa, kroki 7–8'))
    ground = bal.get('ground_check')
    if ground:
        rows.append(_row('10', 'Rzut środka masy między kołami, także samolotu pustego', 'między kołami',
                         f"ŚM {comma(ground['x_cg_min_m'])}–{comma(ground['x_cg_max_m'])} m; koła {comma(ground['x_front_m'])} i {comma(ground['x_rear_m'])} m",
                         ground['passed'], 'analiza masowa, krok 7'))
    if metrics.get('tipback_angle_deg') is not None:
        rows.append(_row('10', 'Kąt między pionem przez ŚM a prostą do punktu styku koła głównego',
                         f"≥ {comma(metrics['tipback_required_deg'], 1)}° (α przy 0,9 Cz,max + 3°)", f"{comma(metrics['tipback_angle_deg'], 1)}°",
                         metrics['tipback_angle_deg'] >= metrics['tipback_required_deg'] - .05, 'wykład 7'))
    if metrics.get('tailwheel_cg_fwd_deg') is not None:
        rows.append(_row('10', 'Położenie ŚM za kołem głównym (kółko ogonowe)', '13° (przednie) do 20° (tylne)',
                         f"{comma(metrics['tailwheel_cg_fwd_deg'], 1)}–{comma(metrics['tailwheel_cg_aft_deg'], 1)}°",
                         12.5 <= metrics['tailwheel_cg_fwd_deg'] and metrics['tailwheel_cg_aft_deg'] <= 20.5, 'wykład 4'))
        rows.append(_row('11', 'Kąt postojowy na trzech punktach', f"≥ {comma(metrics['three_point_required_deg'], 1)}°",
                         f"{comma(metrics['three_point_attitude_deg'], 1)}°",
                         metrics['three_point_attitude_deg'] >= metrics['three_point_required_deg'] - .5, 'wykład 4'))
    elif metrics.get('tailstrike_angle_deg') is not None and p.get('aircraft_type') != 'glider':
        rows.append(_row('11', 'Kąt między podłożem a prostą od koła głównego do ogona', f"≥ {comma(metrics['tailstrike_required_deg'], 1)}° (α przy Cz,max)",
                         f"{comma(metrics['tailstrike_angle_deg'], 1)}°",
                         metrics['tailstrike_angle_deg'] >= metrics['tailstrike_required_deg'] - .05, 'wykład 7'))
    if metrics.get('tipover_angle_deg') is not None:
        rows.append(_row('10', 'Kąt przewrócenia na bok', '< 60°', f"{comma(metrics['tipover_angle_deg'], 1)}°",
                         metrics['tipover_angle_deg'] < 60, 'wykład 4'))
    volume_h = ht['S_h'] * ht['l_h'] / (wing['S'] * wing['mac'])
    volume_v = vt['S_v'] * vt['l_v'] / (wing['S'] * wing['b'])
    rows.append(_row('12', 'Cecha objętościowa usterzenia poziomego na rysunku', comma(float(p.get('v_h', volume_h)), 3), comma(volume_h, 3),
                     abs(volume_h - float(p.get('v_h', volume_h))) <= .02 * volume_h, 'pomoce do wymiarowania usterzeń (Corke)'))
    rows.append(_row('14', 'Cecha objętościowa usterzenia pionowego na rysunku', comma(float(p.get('v_v', volume_v)), 4), comma(volume_v, 4),
                     abs(volume_v - float(p.get('v_v', volume_v))) <= .02 * volume_v, 'pomoce do wymiarowania usterzeń (Corke)'))
    tail = calculate_empennage_sizing(dict(S=wing['S'], b=wing['b'], mac=wing['mac'], fuselage_len=fus['length'],
                                           aircraft_type=p.get('aircraft_type'), engine_location=p.get('engine_location', 'nose'),
                                           v_h=volume_h, v_v=volume_v, _tail_arm_h=ht['l_h'], _tail_arm_v=vt['l_v'],
                                           ar_h=ht['AR_h'], ar_v=vt['AR_v'],
                                           rudder_chord_ratio=vt.get('cr_over_cv', .35), tail_layout=p.get('tail_layout', 'conventional')))
    ratio = tail.get('rudder_unshielded_fraction')
    if ratio is not None and not math.isnan(ratio):
        rows.append(_row('14', 'Część steru kierunku poza cieniem usterzenia poziomego (wyjście z korkociągu)', '≥ 30%',
                         f'{comma(100 * ratio, 0)}%', ratio >= .30,
                         'pomoce do wymiarowania usterzeń (Corke): stożek 60°/30° za usterzeniem poziomym'))
    return dict(rows=rows, source='Schemat postępowania przy rysowaniu kadłuba (C. Galiński)',
                passed=sum(1 for r in rows if r['passed']), assessed=sum(1 for r in rows if r['passed'] is not None))
