"""ML1 project 6 supplement: whole-aircraft polar correction at M < 1."""
import math

from calculations.atmosphere import isa_atmosphere, G0
from .validation import finite, finite_result

SOURCE_URL = 'https://www.meil.pw.edu.pl/zm/content/download/23997/126812/file/proj-06-supl.pdf'


def prandtl_corrected_cd(cd_incompressible, mach):
    """The course method corrects the entire CD, not only induced drag."""
    cd = finite(cd_incompressible, 'Cx nieściśliwy', nonnegative=True)
    m = finite(mach, 'Liczba Macha', nonnegative=True)
    if m >= 1:
        raise ValueError('Korekta Prandtla ML1 wymaga M < 1; dla M ≥ 1 jest niedostępna.')
    corrected = cd/math.sqrt(1-m*m)
    finite_result(corrected)
    return corrected


def altitude_polars(mass_kg, area_m2, polar, altitudes_m):
    """Return each positive-CL flight point and the supplement's corrected CD.

Unavailable points retain their input data and explicit reason. A negative
CL cannot balance positive weight in the level-flight construction used here.
"""
    mass = finite(mass_kg, 'Masa obliczeniowa', positive=True)
    area = finite(area_m2, 'Powierzchnia odniesienia', positive=True)
    if not isinstance(polar, list) or not 2 <= len(polar) <= 500:
        raise ValueError('Biegunowa ML1: podaj od 2 do 500 par cl, cd.')
    points = []
    for i, row in enumerate(polar, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Wiersz biegunowej {i}: wymagane cl i cd.')
        points.append(dict(cl=finite(row.get('cl'), f'Cz, wiersz {i}'),
                           cd=finite(row.get('cd'), f'Cx, wiersz {i}', nonnegative=True)))
    if not isinstance(altitudes_m, list) or not 1 <= len(altitudes_m) <= 51:
        raise ValueError('Biegunowe wysokościowe: podaj od 1 do 51 wysokości.')
    heights = [finite(h, 'Wysokość ISA', nonnegative=True) for h in altitudes_m]
    if len(set(heights)) != len(heights) or any(h > 20000 for h in heights):
        raise ValueError('Wysokości muszą być różne i mieścić się w zakresie 0–20000 m ISA.')
    tables = []
    for height in heights:
        atmosphere = isa_atmosphere(height)
        rows = []
        for point in points:
            cl = point['cl']
            base = dict(cl=cl, cd_incompressible=point['cd'])
            if cl <= 0:
                rows.append(dict(**base, available=False, speed_ms=None, mach=None, cd_corrected=None,
                                 reason='Lot poziomy przy dodatnim ciężarze wymaga Cz > 0.'))
                continue
            speed = math.sqrt(2*mass*G0/(atmosphere['rho']*area*cl))
            mach = speed/atmosphere['a']
            finite_result(speed, mach)
            available = mach < 1
            corrected = prandtl_corrected_cd(point['cd'], mach) if available else None
            rows.append(dict(**base, speed_ms=speed, mach=mach, cd_corrected=corrected,
                             available=available, reason='' if available else 'Korekta Prandtla wymaga M < 1.'))
        tables.append(dict(altitude_m=height, rho_kg_m3=atmosphere['rho'], sound_speed_ms=atmosphere['a'], rows=rows))
    return dict(method='ml1.p6.prandtl_supplement', source='ML1 Projekt 6, suplement', source_url=SOURCE_URL,
                mass_kg=mass, area_m2=area, tables=tables,
                note='Metoda dydaktyczna dla poddźwiękowego samolotu odrzutowego. Korekta nie jest modelem oporu falowego ani pełną analizą transoniczną.')
