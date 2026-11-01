"""Porównanie profili kandydackich wg BIPOL_3 (dobór profilu, kroki 7–9).

Autor wpisuje dane z katalogu (dla Re i Macha z P2), po jednym profilu w wierszu:
    nazwa; C_x,min; C_x(C_z,proj); C_z,max; opis przeciągnięcia
Separatorem jest średnik lub tabulator (wklejenie z arkusza); przecinek dziesiętny jest dozwolony.
Ranking: dla osiągów przelotowych najmniejsze C_x(C_z,proj), dla samolotów STOL, szkolnych
i rolniczych największe C_z,max (BIPOL_3, krok 9). Charakterystykę przeciągnięcia ocenia autor.
"""
import re

MAX_ROWS = 8
CRITERIA = ('auto', 'cruise', 'lift')
CRITERION_LABELS = {'cruise': 'najmniejszy C_x(C_z,proj) — osiągi przelotowe',
                    'lift': 'największy C_z,max — STOL, samolot szkolny lub rolniczy'}
_LIFT_TOPICS = re.compile(r'stol|szkol|rolnicz|pożar|pozar|akrobac', re.IGNORECASE)


def _number(text, line, label, low, high):
    try:
        value = float(text.strip().replace(',', '.'))
    except ValueError:
        raise ValueError(f'Porównanie profili, wiersz {line}: {label} musi być liczbą.') from None
    if not low <= value <= high:
        raise ValueError(f'Porównanie profili, wiersz {line}: {label} poza zakresem {low:g}–{high:g}.')
    return value


def parse_comparison(text):
    """Wiersze porównania jako lista słowników; puste wiersze i komentarze (#) pomija."""
    rows = []
    for line, raw in enumerate(str(text or '').splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        fields = [f.strip() for f in re.split(r'[;\t]', raw)]
        if len(fields) < 4 or not fields[0]:
            raise ValueError(f'Porównanie profili, wiersz {line}: podaj nazwę; C_x,min; C_x(C_z,proj); C_z,max[; przeciągnięcie].')
        rows.append({'name': ' '.join(fields[0].split())[:60],
                     'cx_min': _number(fields[1], line, 'C_x,min', 0.001, 0.2),
                     'cx_cz_proj': _number(fields[2], line, 'C_x(C_z,proj)', 0.001, 0.2),
                     'cz_max': _number(fields[3], line, 'C_z,max', 0.3, 4.0),
                     'stall': '; '.join(f for f in fields[4:] if f)[:120] or 'nie opisano'})
    if len(rows) > MAX_ROWS:
        raise ValueError(f'Porównanie profili: najwyżej {MAX_ROWS} profili.')
    if len({r['name'].upper() for r in rows}) != len(rows):
        raise ValueError('Porównanie profili: nazwy profili muszą być różne.')
    return rows


def resolve_criterion(params):
    criterion = params.get('airfoil_criterion') or 'auto'
    if criterion != 'auto':
        return criterion
    return 'lift' if _LIFT_TOPICS.search(str(params.get('name') or '')) else 'cruise'


def same_profile(a, b):
    return ''.join(str(a or '').upper().split()) == ''.join(str(b or '').upper().split())


def rank_comparison(rows, criterion, cz_proj, selected):
    """Ranking (1 = najlepszy wg kryterium), doskonałość profilu w punkcie projektowym i status."""
    key = (lambda r: (r['cx_cz_proj'], -r['cz_max'])) if criterion == 'cruise' else (lambda r: (-r['cz_max'], r['cx_cz_proj']))
    ordered = sorted(rows, key=key)
    for rank, row in enumerate(ordered, 1):
        row.update(rank=rank, k_proj=round(cz_proj / row['cx_cz_proj'], 1), k_max=None,
                   recommended=same_profile(row['name'], selected), best=rank == 1)
    return ordered
