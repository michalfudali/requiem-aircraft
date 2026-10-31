"""Profil skrzydła o cięciwie 200 mm do rysunku P3 (calculations/airfoils.py)."""
import re

import pytest

from calculations.airfoils import _interp, airfoil_200mm, naca_profile, parse_coordinates, parse_naca


def camber_pct(name):
    """Największa rzędna linii szkieletowej (średnia z powierzchni przy tym samym x zawyża ją przy krawędzi natarcia)."""
    line = parse_naca(name)['camber']
    return max(line(i / 4000)[0] for i in range(1, 4000)) * 100


@pytest.mark.parametrize('name,camber,thickness', [
    ('NACA 0012', 0.0, 12.0), ('NACA 2412', 2.0, 12.0), ('NACA 4415', 4.0, 15.0),
    ('NACA 23012', 1.84, 12.0), ('NACA 23015', 1.84, 15.0), ('NACA 21012', 1.11, 12.0), ('NACA 44012', 4.16, 12.0),  # max w x = r(1 - sqrt(r/3))
])
def test_naca_camber_and_thickness_match_definition(name, camber, thickness):
    """Ugięcie linii 230 = 1,84% przy 15% (Abbott, von Doenhoff); dawniej program dawał 41,6%."""
    profile = naca_profile(name)
    assert camber_pct(name) == pytest.approx(camber, abs=0.01)
    assert profile['thickness_pct'] == pytest.approx(thickness, abs=0.1)


def test_naca_23012_matches_published_ordinates():
    """Rzędne NACA 23012 w % cięciwy (Abbott, von Doenhoff, dodatek I) — zgodność do 0,15% cięciwy."""
    p = naca_profile('NACA 23012', chord_mm=100)
    upper = {5: 4.91, 15: 7.19, 30: 7.55, 50: 6.41, 80: 3.08}
    lower = {5: -2.26, 15: -3.50, 30: -4.46, 50: -4.17, 80: -2.16}
    assert all(abs(_interp(p['upper'], x) - y) < 0.15 for x, y in upper.items())
    assert all(abs(_interp(p['lower'], x) - y) < 0.15 for x, y in lower.items())


def test_station_table_has_separate_upper_and_lower_x():
    table = naca_profile('NACA 4412')['table']
    row = next(r for r in table if r['xc_pct'] == 10.0)
    assert row['xu_mm'] < 20.0 < row['xl_mm']  # grubość odłożona prostopadle do pochylonej szkieletowej
    assert table[0]['xu_mm'] == table[0]['yu_mm'] == 0 and table[-1]['xu_mm'] == pytest.approx(200, abs=0.01)


@pytest.mark.parametrize('name', ['Wortmann FX 61-163', 'NASA SC(2)-0412', 'Clark Y', 'NACA 23112', 'NACA 64A212', ''])
def test_profiles_without_formula_are_not_replaced_by_another(name):
    with pytest.raises(ValueError):
        airfoil_200mm(name)
    assert parse_naca('Clark Y') is None


SELIG = """NACA 0012 (fragment)
1.0000 0.0013
0.5000 0.0529
0.3000 0.0600
0.1000 0.0468
0.0250 0.0262
0.0000 0.0000
0.0250 -0.0262
0.1000 -0.0468
0.3000 -0.0600
0.5000 -0.0529
1.0000 -0.0013
"""
LEDNICER = """TEST PROFIL
6. 6.

0.0 0.0
0.1 0.05
0.3 0.07
0.5 0.06
0.8 0.03
1.0 0.0

0.0 0.0
0.1 -0.03
0.3 -0.04
0.5 -0.03
0.8 -0.01
1.0 0.0
"""


def test_pasted_coordinates_in_selig_and_lednicer_formats():
    name, upper, lower = parse_coordinates(SELIG)
    assert name == 'NACA 0012 (fragment)' and upper[0] == (0.0, 0.0) and upper[-1][0] == 1.0
    assert all(y >= 0 for _, y in upper) and all(y <= 0 for _, y in lower)
    profile = airfoil_200mm('', SELIG)
    assert profile['kind'] == 'pasted' and profile['thickness_pct'] == pytest.approx(12.0, abs=0.05)
    lednicer = airfoil_200mm('', LEDNICER)
    assert lednicer['name'] == 'TEST PROFIL' and lednicer['thickness_pct'] == pytest.approx(11.0, abs=0.05)
    # Rzędne w procentach cięciwy skalują się tak samo.
    percent = '\n'.join(f'{float(x) * 100} {float(y) * 100}' for x, y in (line.split() for line in SELIG.splitlines()[1:]))
    assert airfoil_200mm('', percent)['thickness_pct'] == pytest.approx(12.0, abs=0.05)


@pytest.mark.parametrize('text', ['abc', '0 0\n1 0', 'NAZWA\n7 7\n0 0\n1 0', '1 2 3\n' * 20])
def test_bad_pasted_coordinates_are_rejected(text):
    with pytest.raises(ValueError):
        parse_coordinates(text)


def test_svg_is_drawn_in_millimetres_at_full_scale():
    svg = naca_profile('NACA 23012')['svg']
    width = float(re.search(r'width="([\d.]+)mm"', svg).group(1))
    view = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    assert width == pytest.approx(view[2]) and width == pytest.approx(220.0)  # 1 jednostka = 1 mm, cięciwa 200 mm
    assert '100 mm' in svg and 'NACA 23012 · c = 200 mm' in svg


def test_api_airfoil_200mm_endpoint():
    from app import app
    client = app.test_client()
    res = client.get('/api/airfoil/200mm?airfoil=NACA 23012')
    data = res.get_json()
    assert res.status_code == 200 and data['airfoil'] == 'NACA 23012' and len(data['table']) == 25
    assert data['thickness_pct'] == pytest.approx(12.0, abs=0.1) and '<svg' in data['svg']
    pasted = client.post('/api/airfoil/200mm', json={'airfoil': 'Mój profil', 'coordinates': SELIG})
    assert pasted.status_code == 200 and pasted.get_json()['airfoil'] == 'Mój profil'
    missing = client.get('/api/airfoil/200mm?airfoil=Wortmann FX 61-163')
    assert missing.status_code == 400 and 'Wklej' in missing.get_json()['message']


def test_p3_report_contains_full_scale_airfoil_page():
    from app import app
    html = app.test_client().get('/report?preset=ga_trainer&sections=p3').get_data(as_text=True)
    assert 'figure class="airfoil-1to1"' in html and 'width="220.0mm"' in html
    assert 'Rzędne profilu [mm] dla cięciwy 200 mm' in html
    jet = app.test_client().get('/report?preset=vlj_jet&sections=p3').get_data(as_text=True)
    assert 'figure class="airfoil-1to1"' not in jet and 'Wklej' in jet  # SC(2): bez wzoru, rzędne z katalogu


@pytest.mark.parametrize('name,alpha0,cm', [('NACA 2412', -2.077, -0.0531), ('NACA 4412', -4.154, -0.1062),
                                            ('NACA 23012', -1.094, -0.0128), ('NACA 0012', 0.0, 0.0)])
def test_thin_airfoil_theory_for_naca_camber_lines(name, alpha0, cm):
    """NACA 2412: α₀ = −2,077°, c_m,c/4 = −0,053 (Anderson, przykład teorii cienkiego profilu)."""
    from calculations.airfoils import thin_airfoil
    thin = thin_airfoil(name)
    assert thin['alpha0_deg'] == pytest.approx(alpha0, abs=0.01) and thin['cm_c4'] == pytest.approx(cm, abs=0.0005)
    assert naca_profile(name)['thin_airfoil'] == thin
