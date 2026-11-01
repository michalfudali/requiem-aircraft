"""Preliminary Korn/Lock diagnostic, separate from the low-speed drag polar.

Mason, Configuration Aerodynamics, section 7.5.2, equations (7-4)–(7-9):
https://archive.aoe.vt.edu/mason/Mason_f/ConfigAeroTransonics.pdf
The equivalent wing estimate is not a spanwise strip integration or CFD.
"""
import math
import re

from calculations.validation import NUMERIC_LIMITS

SOURCE = 'Mason, Configuration Aerodynamics, §7.5.2, (7-4)–(7-9)'
SOURCE_URL = 'https://archive.aoe.vt.edu/mason/Mason_f/ConfigAeroTransonics.pdf'
LOCK_OFFSET = (.1 / 80) ** (1 / 3)


def airfoil_technology(name):
    label = ' '.join(str(name or '').upper().split()).replace('–', '-').replace('−', '-')
    # Four/five-digit profiles may contain a 6 as camber, position or thickness.
    # Keep unseparated valid five-digit designations distinct from e.g. 63-012.
    classical = re.fullmatch(r'NACA[ -]*(?:\d{4}|[1-6][1-5][01]\d{2})(?:-\d{2})?', label)
    if re.fullmatch(r'(?:NASA\s*)?SC\s*(?:\(2\)|2)[ -]*\d{4}', label):
        return dict(kappa_a=.95, family='supercritical',
                    profile_family='Profil nadkrytyczny (supercritical)',
                    technology_source='Wartość referencyjna dla profilu nadkrytycznego; wymaga kalibracji dla projektu.')
    if not classical and re.fullmatch(r'NACA[ -]*6[1-7](?:A|\(\d\)|[, _]?\d)?[ -]*\d{3}', label):
        return dict(kappa_a=.87, family='naca6', profile_family='Profil laminarny NACA serii 6',
                    technology_source='Wartość referencyjna Masona dla NACA serii 6; samo oznaczenie nie zastępuje danych pomiarowych.')
    return dict(kappa_a=.87, family='conventional_assumption',
                profile_family='Profil klasyczny NACA / konwencjonalny',
                technology_source='Założenie κ_A = 0,87; dla tego oznaczenia nie wyznaczono współczynnika z danych profilu.')


def calculate_compressibility(mach, cz, tc=.12, sweep_deg=0., airfoil_name=''):
    """Korn/Lock at positive lift; sweep_deg refers to the half-chord line.

Rounded fields are for display only. Scope decisions and wave drag use raw
values in terms. Prandtl–Glauert is not extrapolated through Mach 1.
"""
    values = (mach, cz, tc, sweep_deg)
    if any(isinstance(x, bool) for x in values):
        raise ValueError('Model ściśliwości wymaga skończonych wartości liczbowych.')
    try:
        m, cl, thickness, sweep = map(float, values)
    except (TypeError, ValueError):
        raise ValueError('Model ściśliwości wymaga skończonych wartości liczbowych.') from None
    if not all(math.isfinite(x) for x in (m, cl, thickness, sweep)) or m < 0 or cl < 0:
        raise ValueError('Model ściśliwości wymaga skończonych wartości: M ≥ 0 i Cz ≥ 0.')
    low, high = NUMERIC_LIMITS['tc_ratio']
    if not low <= thickness <= high:
        raise ValueError(f'Grubość t/c w modelu ściśliwości musi być w zakresie {low:g}–{high:g}.')
    if not -60 < sweep < 60:
        raise ValueError('Skos linii połówek cięciw w modelu ściśliwości musi być pomiędzy −60° i 60°.')
    tech = airfoil_technology(airfoil_name)
    cosine = math.cos(math.radians(sweep))
    m_dd = tech['kappa_a'] / cosine - thickness / cosine**2 - cl / (10 * cosine**3)
    m_crit = m_dd - LOCK_OFFSET
    if not math.isfinite(m_dd - m):
        raise ValueError('Dane wykraczają poza skończony zakres modelu ściśliwości.')
    applicable = 0 < m_crit < m_dd < 1 and m < 1
    wave = 20 * max(0., m - m_crit)**4 if applicable else None
    pg = 1 / math.sqrt(1 - m*m) if m < 1 else None
    needs_wave = not applicable or m > m_crit
    note = ('Diagnostyka równoważnego skrzydła; κ_A wymaga kalibracji, a rozkład profilu '
            'i skosu wzdłuż rozpiętości osobnej analizy. Obliczony ΔCx,wave nie jest dodany '
            'do referencyjnej biegunowej Paturskiego ani bilansu osiągów.')
    if not applicable:
        note += ' Punkt jest poza zakresem tej poddźwiękowej korelacji; nie podano pozornego przyrostu oporu.'
    elif needs_wave:
        note += (' Przelot przekracza oszacowane M_kr. Osiągi i zasięg z biegunowej bez oporu '
                 'falowego są w tym punkcie niezweryfikowane; potrzebna jest biegunowa zależna od M i Cz.')
    return dict(**tech, mach=round(m, 3), m_crit=round(m_crit, 3), m_dd=round(m_dd, 3),
                delta_cx_wave=round(wave, 5) if wave is not None else None,
                prandtl_glauert_factor=round(pg, 3) if pg is not None else None,
                prandtl_glauert_applicable=applicable and m < m_crit,
                margin_to_divergence=round(m_dd - m, 3),
                drag_divergence_safe=applicable and m < m_dd,
                model_applicable=applicable, requires_wave_polar=needs_wave,
                tc_ratio=thickness, is_transonic=m >= .70, note=note,
                source=SOURCE, source_url=SOURCE_URL,
                terms=dict(mach=m, cl=cl, tc_ratio=thickness, sweep_half_chord_deg=sweep,
                           cos_sweep=cosine, m_dd=m_dd, m_crit=m_crit, lock_offset=LOCK_OFFSET,
                           delta_cx_wave=wave))


def equivalent_half_chord_sweep(wing):
    """Secant of the half-chord line from root to tip (curved/compound wings approximate)."""
    return math.degrees(math.atan(math.tan(math.radians(wing['sweep_deg'])) -
                                  (wing['cr'] - wing['ct']) / (2 * wing['b'])))
