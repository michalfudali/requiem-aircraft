"""Traceable analytical checks from Galiński & Grabowski, BIPOL_1_wzory.

Idealized, steady, subsonic results conforming to BIPOL_1.pdf (pp. 2–6) and BIPOL_1_wzory.pdf (pp. 1–9).
Includes Raymer wetted aspect ratio and maximum lift-to-drag ratio estimate,
analytical Cx0 check from equation (3), and verification against the 7-class BIPOL table.
"""
import math
from calculations.atmosphere import G0, isa_atmosphere

# BIPOL_1.pdf, s. 3: Tabela dopuszczalnych/oczekiwanych wartości Cx0 dla siedmiu klas samolotów
BIPOL_1_CX0_TABLE = {
    'combat': {
        'name': 'Bojowe',
        'cx0_range': (0.014, 0.020),
        'cfe_typical': 0.0035,
        'description': 'Samoloty myśliwskie / szturmowe naddźwiękowe i poddźwiękowe'
    },
    'large_transport': {
        'name': 'Duże samoloty transportowe',
        'cx0_range': (0.018, 0.024),
        'cfe_typical': 0.0030,
        'description': 'Pasażerskie i transportowe odrzutowce komunikacyjne (CS-25)'
    },
    'small_twin': {
        'name': 'Małe dwusilnikowe',
        'cx0_range': (0.022, 0.028),
        'cfe_typical': 0.0045,
        'description': 'Lekkie samoloty dyspozycyjne i regionalne dwusilnikowe'
    },
    'single_retractable': {
        'name': 'Jednosilnikowe z podwoziem chowanym',
        'cx0_range': (0.020, 0.030),
        'cfe_typical': 0.0050,
        'description': 'Szybkie samoloty turystyczne i szkolne z chowanym podwoziem'
    },
    'single_fixed': {
        'name': 'Jednosilnikowe z podwoziem stałym',
        'cx0_range': (0.025, 0.040),
        'cfe_typical': 0.0065,
        'description': 'Klasyczne samoloty szkolne i turystyczne ze stałym podwoziem'
    },
    'agricultural': {
        'name': 'Rolnicze',
        'cx0_range': (0.060, 0.080),
        'cfe_typical': 0.0090,
        'description': 'Samoloty agrolotnicze o dużej powierzchni i wyposażeniu opryskowym'
    },
    'motoglider': {
        'name': 'Motoszybowce',
        'cx0_range': (0.014, 0.020),
        'cfe_typical': 0.0025,
        'description': 'Szybowce z napędem i motoszybowce turystyczne (CS-22)'
    },
}


def classify_bipol_cx0(params):
    """Przyporządkowanie projektu do jednej z siedmiu klas z BIPOL_1.pdf s. 3."""
    ac_type = params.get('aircraft_type', 'piston_ga')
    from calculations.paturski_ml import default_retractable_gear
    explicit = params.get('landing_gear_type', params.get('gear_type'))
    if explicit in ('fixed', 'retractable') and 'retractable_gear' not in params and params.get('gear_retraction', 'auto') == 'auto':
        gear = explicit
    else:
        gear = 'retractable' if default_retractable_gear(params) else 'fixed'
    n_eng = int(params.get('n_engines', 1))

    if ac_type in ('glider', 'motoglider'):
        return 'motoglider'
    if ac_type == 'jet_transport':
        return 'large_transport'
    if ac_type == 'jet_business':
        return 'large_transport' if int(params.get('n_pax', 4)) > 8 else 'small_twin'
    if ac_type == 'turboprop_regional':
        return 'small_twin' if n_eng <= 2 else 'large_transport'
    if ac_type == 'piston_ga':
        if n_eng >= 2:
            return 'small_twin'
        return 'single_retractable' if gear == 'retractable' else 'single_fixed'
    if ac_type == 'agricultural':
        return 'agricultural'
    return 'single_fixed'


def preliminary_insights(params, mass, geometry, aero):
    rho = isa_atmosphere(params['cruise_altitude_m'])['rho']
    weight = mass['m0'] * G0
    area = geometry['wing']['S']
    ar = geometry['wing']['AR']
    swet_over_s = geometry['wetted_area']['swet_over_s']
    cd0, k = aero['cx0_clean'], aero['k_clean']
    cl_ld = math.sqrt(cd0 / k)
    ld_max = 1 / (2 * math.sqrt(cd0 * k))
    operating_points = []
    for key, label, cl, formula in (
        ('max_ld', 'Największa doskonałość / zasięg śmigłowy', cl_ld, 'Cz = √(Cx₀/k), Kmax = 1/(2√(Cx₀·k))'),
        ('jet_range', 'Największy zasięg odrzutowy', cl_ld / math.sqrt(3), 'Cz = √(Cx₀/(3k))'),
        ('prop_endurance', 'Najdłuższy lot śmigłowy / minimum mocy', cl_ld * math.sqrt(3), 'Cz = √(3Cx₀/k)'),
    ):
        cd = cd0 + k * cl * cl
        operating_points.append({'key': key, 'label': label, 'cl': cl, 'cd': cd, 'ld': cl/cd,
            'v_tas_kmh': math.sqrt(2*weight/(rho*area*cl))*3.6,
            'below_stall_limit': cl <= aero['cz_max_clean'], 'formula': formula})
    v = params['cruise_speed_kmh']/3.6
    ws = weight/area
    q = .5*rho*v*v
    n45 = math.sqrt(2)

    # Fig. 2 is read directly: a Cfe assumption is not a Raymer graph reading.
    ar_wet = ar / max(0.1, swet_over_s)
    bipol_class_key = classify_bipol_cx0(params)
    bipol_class = BIPOL_1_CX0_TABLE[bipol_class_key]
    e_oswald = float(params.get('oswald_e', 0.80))
    from calculations.bipol1 import preliminary_polar
    reading = mass['preliminary_polar']

    if reading['mode'] == 'input':
        reading = preliminary_polar(dict(params, preliminary_polar_mode='raymer', wetted_example='sketch',
                                         sketch_swet_ratio=swet_over_s, aspect_ratio=ar))
    k_max_raymer = reading['kmax'] if reading else None
    cx0_raymer_est = reading['cx0'] if reading else None
    cx0_from_kmax_formula3 = cx0_raymer_est

    # Kontrola Cx0 względem 7 klas z tabeli BIPOL_1 s. 3
    in_range = bipol_class['cx0_range'][0] <= cd0 <= bipol_class['cx0_range'][1]
    if in_range:
        status_pl = 'Zgodny z przedziałem typowym dla klasy w BIPOL_1'
    elif cd0 < bipol_class['cx0_range'][0]:
        status_pl = f'Poniżej przedziału typowego ({cd0:.4f} < {bipol_class["cx0_range"][0]:.3f})'
    else:
        status_pl = f'Powyżej przedziału typowego ({cd0:.4f} > {bipol_class["cx0_range"][1]:.3f})'

    cx0_table_check = {
        'class_key': bipol_class_key,
        'class_name': bipol_class['name'],
        'cx0_range': bipol_class['cx0_range'],
        'cx0_range_str': f"{bipol_class['cx0_range'][0]:.3f} – {bipol_class['cx0_range'][1]:.3f}",
        'cx0_actual': round(cd0, 4),
        'in_range': in_range,
        'status': status_pl,
        'description': bipol_class['description'],
        'source_table': 'BIPOL_1.pdf, s. 3 (tabela siedmiu klas samolotów)'
    }

    raymer_estimate = {
        'wetted_aspect_ratio': round(reading['wetted_aspect_ratio'], 2),
        'swet_over_s': round(reading['swet_ratio'], 2),
        'k_max_raymer': round(k_max_raymer, 2) if k_max_raymer is not None else None,
        'cx0_from_raymer': round(cx0_raymer_est, 4) if cx0_raymer_est is not None else None,
        'cx0_from_formula3': round(cx0_from_kmax_formula3, 4) if cx0_from_kmax_formula3 is not None else None,
        'used_in_mass': params.get('preliminary_polar_mode','input')!='input',
        'limitation': reading['reading_note'] if reading.get('extrapolated') else None,
        'source': 'BIPOL_1, rys. 1–2: przybliżony odczyt graficzny; wzór (3).'
    }

    return {
        'source': 'BIPOL_1_wzory.pdf, s. 1–9; BIPOL_1.pdf, s. 2–6',
        'altitude_m': params['cruise_altitude_m'], 'rho': rho, 'operating_points': operating_points,
        'k_max': ld_max, 'cx0_from_kmax': 1/(4*k*ld_max*ld_max),
        'wetted_aspect_ratio': ar_wet,
        'raymer': raymer_estimate,
        'cx0_table_check': cx0_table_check,
        'bipol_7_classes_table': BIPOL_1_CX0_TABLE,
        'climb': {'gradient_required': params.get('climb_rate_ms', 0)/v,
            'tw_lower_bound': params.get('climb_rate_ms', 0)/v + 1/ld_max,
            'formula': 'T/W ≥ G + 1/Kmax; G = w/V (przy stałej TAS)'},
        'turn_45': {'load_factor': n45, 'radius_m': v*v/G0, 'rate_deg_s': math.degrees(G0/v),
            'cl_required': n45*ws/q, 'stall_limited_n': q*aero['cz_max_clean']/ws,
            'tw_required': q*cd0/ws + k*n45*n45*ws/q,
            'tw_lower_bound': n45/ld_max,
            'formula': 'n = 1/cosφ; r = V²/[g√(n²−1)]; T/W = q·Cx₀/(W/S) + k·n²·(W/S)/q'},
        'limitations': 'Biegunowa paraboliczna, stałe zużycie jednostkowe i sprawność napędu, lot ustalony. Prędkości TAS dla masy startowej i wysokości przelotowej. Cz powyżej Czmax oznacza nieosiągalny punkt. Warunek ciągu w zakręcie nie uwzględnia ograniczeń konstrukcji ani dostępnej mocy.'
    }
