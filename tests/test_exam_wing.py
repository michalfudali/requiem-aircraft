"""Zadanie kolokwialne I: zgodność z arkuszami kursu, przepisami JAR-23 i API."""
import math

import pytest

from app import app
from calculations.exam_wing import SLICES, letters, schrenk_strips, shear_moment, solve_exam1

# Wing_load_taper_{1,05,025}.pdf: B = 12 m, c_r = 2 m, m = 1500 kg, g = 9,81 m/s², 4 paski.
COURSE_SHEETS = {
    1.0: (24.0, [2081.49, 2005.22, 1833.79, 1486.59], [7407.08, 5325.59, 3320.37, 1486.59],
          [20754.13, 11204.63, 4720.16, 1114.94], [1.132, 1.090, 0.997, 0.808]),
    0.5: (18.0, [2311.41, 2081.86, 1757.14, 1256.67], [7407.08, 5095.67, 3013.81, 1256.67],
          [19604.52, 10227.46, 4145.36, 942.50], [1.005, 1.045, 1.042, 0.911]),
    0.25: (15.0, [2495.35, 2143.17, 1695.83, 1072.73], [7407.08, 4911.73, 2768.56, 1072.73],
           [18684.83, 9445.73, 3685.51, 804.55], [0.936, 1.013, 1.085, 1.060]),
}


def entries(result):
    return {e['key']: e for s in result['sections'] for e in s['entries']}


@pytest.mark.parametrize('lam', sorted(COURSE_SHEETS))
def test_schrenk_strips_reproduce_course_sheets(lam):
    S, lift, shear, moment, cz = COURSE_SHEETS[lam]
    rows = schrenk_strips(S, 12.0, lam, 1500 * 9.81 / S)
    loads = shear_moment(rows, [r['lift'] for r in rows])
    assert [round(r['lift'], 2) for r in rows] == pytest.approx(lift, abs=0.02)
    assert [round(t, 2) for t, _ in loads] == pytest.approx(shear, abs=0.02)
    assert [round(m, 2) for _, m in loads] == pytest.approx(moment, abs=0.02)
    assert [round(r['cz_ratio'], 3) for r in rows] == pytest.approx(cz, abs=0.001)


def test_example_solution_values():
    r = solve_exam1(6, 7)
    e = entries(r)
    assert r['consistent'] and r['category'] == 'commuter'
    assert e['m']['value'] == 1300 and e['m_f']['value'] == pytest.approx(162.5) and e['m_s']['value'] == pytest.approx(216.667, abs=1e-3)
    assert e['lam']['value'] == pytest.approx(6 / 13)
    # S z V_S0 = 61 kt i C_z,max = 2,0; geometria trapezu.
    vs0 = 61 * 0.514444
    S = 2 * 1300 * 9.81 / (1.225 * vs0 ** 2 * 2.0)
    assert r['answers']['S'] == pytest.approx(S)
    assert r['answers']['b'] == pytest.approx(math.sqrt(6 * S))
    assert r['answers']['c_r'] * (1 + 6 / 13) * r['answers']['b'] / 2 == pytest.approx(S)
    assert r['answers']['c_g'] == pytest.approx(S / r['answers']['b'])
    # Commuter: n1 = 2,1 + 24000/(W+10000) ograniczone do 3,8; podmuch 66 ft/s przy VB.
    assert e['n_wz']['value'] == pytest.approx(2.1 + 24000 / (1300 * 2.20462262 + 10000))
    assert e['n1']['value'] == 3.8 and e['n2']['value'] == pytest.approx(-1.52)
    assert 'VB' in e and e['VB']['value'] <= e['VC']['value']
    assert r['envelope']['speeds']['v_b_kmh'] == pytest.approx(e['VB']['value'] * 3.6, abs=0.06)
    # V_B leży poniżej przecięcia z linią C_z,max, więc podmuch 66 ft/s ogranicza przeciągnięcie.
    assert e['VB']['value'] < e['VB1']['value']
    assert e['nB']['value'] == pytest.approx((e['VB']['value'] / e['VS1']['value']) ** 2)
    assert e['nB']['value'] < 1 + e['dn_B']['value']
    # Zawsze to samo W/S, bo S wynika z V_S0 i C_z,max z klapami: 0,5·ρ·V²·2,0.
    assert e['WS']['value'] == pytest.approx(0.5 * 1.225 * vs0 ** 2 * 2.0)


@pytest.mark.parametrize('x,y,category,n1,n2', [
    (3, 2, 'commuter', 3.8, -1.52),     # (5 mod 4) + 1 = 2
    (4, 4, 'normal', 3.8, -1.52),       # 1
    (5, 5, 'utility', 4.4, -1.76),      # 3
    (5, 6, 'aerobatic', 6.0, -3.0),     # 4
])
def test_category_from_letters_and_load_factors(x, y, category, n1, n2):
    r = solve_exam1(x, y)
    e = entries(r)
    assert r['category'] == category and r['category_index'] == (x + y) % 4 + 1
    assert e['n1']['value'] == pytest.approx(n1) and e['n2']['value'] == pytest.approx(n2)
    assert ('VB' in e) == (category == 'commuter')
    # JAR-23.333(b)(3): przy VD ujemna gałąź kończy się na 0 (normal, commuter) lub −1 (utility, aerobatic).
    assert r['envelope']['n_vd_neg'] == (-1.0 if category in ('utility', 'aerobatic') else 0.0)
    assert r['envelope']['limits']['n_max'] >= n1 and r['envelope']['limits']['n_min'] <= n2


def test_masses_and_equilibrium_of_half_wing():
    r = solve_exam1(7, 9)
    e, rows = entries(r), r['rows']
    assert len(rows) == SLICES
    assert sum(row['m_struct'] for row in rows) == pytest.approx(e['m_s']['value'] / 2)
    assert sum(row['m_fuel'] for row in rows) == pytest.approx(e['m_f']['value'] / 2)
    # Paliwo między 0,25 i 0,75 półrozpiętości: przy 4 paskach dokładnie paski 2 i 3.
    assert rows[0]['m_fuel'] == 0 and rows[3]['m_fuel'] == 0 and rows[1]['m_fuel'] > rows[2]['m_fuel'] > 0
    half_lift = sum(row['lift'] for row in rows)
    relief = 9.81 * (e['m_s']['value'] + e['m_f']['value']) / 2
    assert rows[0]['t_unit'] == pytest.approx(half_lift - relief)
    assert e['T0']['value'] == pytest.approx(e['n_max']['value'] * (half_lift - relief))
    assert e['M0_ult']['value'] == pytest.approx(1.5 * e['M0']['value'])
    # Siła tnąca i moment maleją do końcówki.
    assert all(a['t_limit'] > b['t_limit'] > 0 for a, b in zip(rows, rows[1:]))
    assert all(a['m_limit'] > b['m_limit'] > 0 for a, b in zip(rows, rows[1:]))


def test_every_letter_count_gives_consistent_sheet():
    for x in range(1, 41, 3):
        for y in range(1, 41, 4):
            r = solve_exam1(x, y)
            bad = [k for k, e in entries(r).items() if e['consistent'] is False]
            assert not bad, (x, y, bad)
            assert r['answers']['VD_kmh'] > r['answers']['VC_kmh'] >= r['answers']['VA_kmh'] - 1e-9
            assert r['answers']['M0_dim'] >= r['answers']['M0']


@pytest.mark.parametrize('x,y', [(0, 5), (41, 5), (True, 5), (5.0, 5), ('6', 7), (None, 7)])
def test_invalid_letter_counts(x, y):
    with pytest.raises(ValueError):
        solve_exam1(x, y)


def test_letters_counts_only_letters():
    assert letters('Michał') == 6
    assert letters('Kowalska-Nowak') == 13
    assert letters("O'Neill") == 6
    assert letters('  ') == 0


def test_api_returns_solution_and_rejects_bad_input():
    client = app.test_client()
    ok = client.post('/api/exam/wing-loads', json={'x': 6, 'y': 7})
    assert ok.status_code == 200 and ok.get_json()['answers']['S'] > 0
    for body in ({'x': 0, 'y': 7}, {'x': 6}, [6, 7], {'x': 'Michał', 'y': 7}):
        bad = client.post('/api/exam/wing-loads', json=body)
        assert bad.status_code == 400 and bad.get_json()['message']


def test_panel_is_reachable_from_navigation():
    html = app.test_client().get('/').get_data(as_text=True)
    assert 'id="tab-exam"' in html and 'data-studio-nav="tab-exam"' in html and 'data-target="tab-exam"' in html
    assert '/static/js/exam.js' in html
