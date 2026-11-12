"""One source of wing thickness for preliminary geometry, drag and stiffness.

An explicit NACA designation supplies its nominal t/c; pasted ordinates take
precedence and supply the maximum vertical gap of their linear interpolants.
An unspecified profile remains an assumption, even if P2 later suggests one.
This geometric link does not replace the reference aerodynamic polar.
"""
import math

from calculations.airfoils import airfoil_200mm
from calculations.validation import NUMERIC_LIMITS


def profile_thickness(profile):
    return profile.get('nominal_thickness_ratio', profile['thickness_ratio'])


def resolve_profile_geometry(params, states):
    name = ' '.join(str(params.get('airfoil') or '').split())[:80]
    coordinates = str(params.get('airfoil_coordinates') or '')
    explicit = bool(name or coordinates.strip())
    profile, error = None, None
    if explicit:
        try:
            profile = airfoil_200mm(name, coordinates)
        except ValueError as exc:
            error = str(exc)
    assumed = float(params['tc_ratio'])
    derived = params['profile_thickness_mode'] == 'auto' and profile is not None
    if derived:
        value = profile_thickness(profile)
        low, high = NUMERIC_LIMITS['tc_ratio']
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Grubość wybranego profilu t/c = {value:.6g} wykracza poza zakres '
                             f'modelu skrzydła {low:g}–{high:g}. Wybierz profil w tym zakresie '
                             'albo jawny tryb ręcznego założenia.')
        if 'tc_ratio' in params.get('locked_params', []) and not math.isclose(value, assumed, abs_tol=1e-9):
            raise ValueError('Zablokowane t/c różni się od grubości wybranego profilu. '
                             'Odblokuj t/c albo wybierz ręczne założenie grubości.')
        params['tc_ratio'] = value
    states['tc_ratio'] = dict(state='derived' if derived else
                             ('locked' if 'tc_ratio' in params.get('locked_params', []) else 'input'),
                             value=params['tc_ratio'], display_digits=6)
    if derived:
        states['tc_ratio'].update(
            formula='Nominalne t/c z oznaczenia NACA' if profile['kind'] == 'naca' else
                    'max(y_górne(x) − y_dolne(x)) / c z wklejonych rzędnych',
            sources=['airfoil', 'airfoil_coordinates'])
    context = dict(explicit=explicit, profile=profile, error=error, derived=derived)
    context['assessment'] = assess_profile_geometry(params, context)
    return context


def assess_profile_geometry(params, context):
    profile = context['profile']
    value = profile_thickness(profile) if profile is not None else None
    effective = params['tc_ratio']
    mismatch = value is not None and not math.isclose(value, effective, abs_tol=1e-4)
    source = ('Nominalna grubość z oznaczenia NACA' if profile and profile['kind'] == 'naca' else
              'Maksymalna grubość z wklejonych rzędnych') if context['derived'] else 'Ręczne założenie t/c'
    if context['derived']:
        note = 'Grubość profilu zasila geometrię skrzydła, poprawki oporu i wstępne oszacowanie sztywności.'
    elif not context['explicit']:
        note = ('Nie wybrano profilu. Obliczenia używają założonej grubości; kandydat proponowany w P2 '
                'nie jest zatwierdzonym profilem. Wybierz oznaczenie lub wklej rzędne w P3.')
    elif profile is None:
        note = ('Brak poprawnej geometrii wybranego profilu. Obliczenia używają założonego t/c. '
                + (context['error'] or 'Uzupełnij rzędne w P3.'))
    else:
        note = 'Wybrano ręczne założenie grubości niezależne od geometrii profilu.'
    if mismatch:
        note += (' Uwaga: grubość użyta w obliczeniach różni się od geometrii profilu '
                 f'({100 * effective:.4g}% zamiast {100 * value:.4g}% cięciwy).')
    note += (' Samo t/c nie wyznacza biegunowej ani Cz_max. Charakterystyki profilu wymagają '
             'danych dla właściwej liczby Reynoldsa i Macha. ')
    note += ('Obliczenia korzystają z zadeklarowanego modelu charakterystyk profilu; sprawdź jego źródło i zakres ważności. '
             if params.get('airfoil_model') else 'Tabela Paturskiego pozostaje odniesieniem NACA 23012. ')
    note += 'Model używa jednego t/c dla skrzydła; zmienność profilu wzdłuż rozpiętości wymaga osobnej analizy.'
    return dict(mode=params['profile_thickness_mode'], derived=context['derived'], source=source,
                tc_ratio=effective, profile_tc_ratio=value, mismatch=mismatch,
                profile_name=profile['name'] if profile else None,
                thickness_definition=('nominal_naca' if profile and profile['kind'] == 'naca' else
                                      'vertical_gap' if profile else None), note=note)
