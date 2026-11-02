"""Tryb sterowania ręcznego: każdą wartość domyślną w obliczeniach użytkownik wpisuje sam.

W tym trybie dane wejściowe arkusza obliczeń — wymagania tematu, założenia początkowe, warunki
brzegowe i dane z literatury — nie są przyjmowane bez udziału użytkownika. Program pokazuje
sugerowaną wartość i jej uzasadnienie, ale wartość musi wpisać użytkownik. Kolejne projekty
(P1 → P6) odblokowują się dopiero po wpisaniu wszystkich danych poprzednich.

Stan trybu przychodzi w parametrach projektu:
    manual_control = {"enabled": true,
                      "typed": ["range_km", ...],     # parametry wpisane przez użytkownika w formularzu lub kreatorze
                      "accepted": {"k_rez": 1.06}}    # wartości wpisane w oknie akceptacji (klucze arkusza)
Wartość danej, która odpowiada parametrowi projektu, trafia do obliczeń. Pozostałe dane są stałymi
przyjętej metody: użytkownik akceptuje je, wpisując ich wartość, a zmienia — zmieniając metodę
(np. rodzaj klapy).
"""
import math
import re

from calculations.report_document import TITLES
from calculations.report_origin import CATEGORY, classify, origin_text

GATED = ('req', 'ass', 'bc', 'lit')

# Dane arkusza, które są parametrami projektu: wpisana wartość trafia do obliczeń.
PARAM = {
    'n_pas': 'n_pax', 'm_pas': 'm_pax', 'm_bag': 'm_bag', 'm_cargo': 'm_cargo', 'n_zal': 'n_crew',
    'm_os': 'm_crew_person', 'H_cr': 'cruise_altitude_m', 'V_cr_kmh': 'cruise_speed_kmh', 'R_km': 'range_km',
    'V_min_kmh': 'v_stall_kmh', 's_L': 'landing_distance_m', 's_TO': 'takeoff_distance_m', 's_roz': 'takeoff_run_m',
    'w_y_wym': 'climb_rate_ms', 'R_pow': 'return_range_km', 'AR': 'aspect_ratio', 'e_1': 'oswald_e',
    'Cx0_1': 'cx0', 'Cx0_baz': 'cx0', 'tc': 'tc_ratio', 'SFC': 'sfc', 'TSFC': 'sfc', 'eta_p': 'prop_efficiency',
    'k_K': 'mission_ld_factor', 'r_TO': 'takeoff_mass_fraction', 'r_LND': 'landing_mass_fraction',
    'k_rez': 'fuel_reserve_factor', 'H_0': 'climb_start_altitude_m', 'V_0_kmh': 'climb_start_speed_kmh',
    't_ocz': 'loiter_time_min', 'V_ocz_kmh': 'loiter_speed_kmh', 't_zad': 'max_power_time_min',
    'SFC_max': 'max_power_sfc', 'T_max_zad': 'max_thrust_kn', 'P_max_zad': 'max_power_kw', 'm_zrzut': 'payload_drop_kg',
    'eta_TO': 'prop_eff_to', 'N_P': 'cost_n_production', 'N_am': 'cost_n_amortization', 'rok': 'cost_year',
    'C_av': 'avionics_price_usd', 'k_QC': 'cost_qc_factor', 'lambda_w': 'taper_ratio', 'lambda_2': 'taper_ratio',
    'chi25': 'sweep_quarter_deg', 'wave_chi25': 'sweep_quarter_deg', 'xi_b': 'break_span_ratio', 'V_H': 'v_h',
    'V_V': 'v_v', 'AR_H': 'ar_h', 'bf_b_zal': 'flap_span_ratio', 'ba_b_zal': 'aileron_span_ratio',
    'ca_c': 'aileron_chord_ratio', 'cf_c': 'flap_chord_ratio', 'Cz_max': 'cz_max_clean', 'mu_r': 'mu_ground',
    'cz_prof': 'airfoil_cz_max',
}
# Dane podawane w innej skali niż parametr (wartość arkusza × współczynnik = parametr).
SCALED = {'z_zysk': ('cost_profit_pct', 100.0)}
INTEGER = {'n_pax', 'n_crew', 'cost_n_production', 'cost_n_amortization', 'cost_year'}
# Wskazówka, jak zmienić stałą metody, której nie wpisuje się jako parametru.
METHOD_HINT = {
    'dCz_TO_p': 'rodzaj klapy', 'dCz_L_p': 'rodzaj klapy', 'dCx_TO_p': 'rodzaj klapy', 'dCx_L_p': 'rodzaj klapy',
    'e_fTO': 'rodzaj klapy', 'e_fL': 'rodzaj klapy', 'Cz_TO_2': 'rodzaj i zasięg klap', 'Cz_L_2': 'rodzaj i zasięg klap',
    'd_k': 'liczbę osób w rzędzie', 'Cx_min1': 'profil skrzydła', 'a_inf': 'profil skrzydła',
}


def settings(params):
    state = params.get('manual_control') if isinstance(params, dict) else None
    return state if isinstance(state, dict) and state.get('enabled') else None


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Sterowanie ręczne: wpisane wartości muszą być liczbami.')
    return float(value)


def parameter_of(key):
    if key in PARAM:
        return PARAM[key]
    if key in SCALED:
        return SCALED[key][0]
    return 'engine_power_kw' if key == 'P' else None


def apply(params):
    """Parametry z wartościami wpisanymi w oknie akceptacji (tylko w trybie sterowania ręcznego)."""
    state = settings(params)
    if not state:
        return params
    accepted = state.get('accepted') or {}
    if not isinstance(accepted, dict) or not isinstance(state.get('typed', []), list):
        raise ValueError('Sterowanie ręczne: nieprawidłowy zapis zaakceptowanych danych.')
    result = dict(params)
    for key, value in accepted.items():
        value = _number(value)
        if key in PARAM:
            result[PARAM[key]] = int(round(value)) if PARAM[key] in INTEGER else value
        elif key in SCALED:
            result[SCALED[key][0]] = value * SCALED[key][1]
        elif key == 'P':
            result.update(power_input_mode='fixed', engine_power_kw=value)
    return result


def _plain_unit(tex):
    text = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', tex or '')
    text = text.replace('^2', '²').replace('^3', '³').replace('^{-1}', '⁻¹').replace(r'\,', ' ').replace(r'\;', ' ')
    text = text.replace('{}^{\\circ}', '°').replace(r'\%', '%').replace(r'\text{', '').replace('}', '').replace('{', '')
    return text.strip()


def _plain_origin(entry):
    return re.sub(r'\s*\{(?:fig|tab|eq|lit):[^}]+\}', '', origin_text(entry))


def _close(a, b, digits):
    return abs(a - b) <= max(0.5 * 10 ** -digits, 1e-6 * abs(a)) + 1e-12


def review(params, sheet):
    """Dane do wpisania przez użytkownika: bieżący etap (projekt), konflikty i postęp."""
    state = settings(params)
    if not state:
        return None
    accepted = state.get('accepted') or {}
    typed = set(state.get('typed') or [])
    points, pending, conflicts = [], [], []
    for key in sheet.order:
        entry = sheet.entries[key]
        if entry['kind'] != 'given' or entry['project'] == 'const':
            continue
        category, _ = classify(entry)
        if category not in GATED:
            continue
        param = parameter_of(key)
        point = dict(key=key, project=entry['project'], section=sheet.sections[entry['section']]['title'],
                     label=entry['label'], unit=_plain_unit(entry['unit']), digits=entry['digits'],
                     suggested=entry['value'], origin=_plain_origin(entry), category=CATEGORY[category],
                     param=param, editable=param is not None, scale=SCALED[key][1] if key in SCALED else 1.0)
        points.append(point)
        if key in accepted:
            value = _number(accepted[key])
            if not _close(value, entry['value'], entry['digits']):
                hint = METHOD_HINT.get(key)
                point['message'] = (f'Wartości nie zastosowano w obliczeniach (otrzymano {entry["value"]:.{entry["digits"]}f}). '
                                    if param else
                                    'Ta wartość wynika z przyjętej metody obliczeń; wpisz wartość sugerowaną'
                                    + (f' albo zmień {hint}.' if hint else '.'))
                point['entered'] = value
                conflicts.append(point)
        elif not (param and param in typed):
            pending.append(point)
    open_points = pending + conflicts
    stage = min((p['project'] for p in open_points), default=None, key=lambda key: int(key[1:]))
    return dict(enabled=True, stage=stage, stage_title=f'Projekt {stage[1:]}. {TITLES[stage]}' if stage else None,
                pending=[p for p in pending if p['project'] == stage],
                conflicts=[p for p in conflicts if p['project'] == stage],
                remaining=len(open_points), total=len(points), accepted=len(points) - len(open_points),
                remaining_by_project={key: sum(1 for p in open_points if p['project'] == key) for key in TITLES})


def blocked_message(state):
    if not state or not state['remaining']:
        return None
    return (f'Tryb sterowania ręcznego: przed przygotowaniem raportu wpisz wszystkie dane domyślne '
            f'(pozostało {state["remaining"]}, bieżący etap: {state["stage_title"]}).')
