"""Porównanie profili kandydackich (BIPOL_3, dobór profilu, kroki 7–9) i jego związek z C_z,max płata ze Schrenka."""
import pytest

from app import app
from calculations import run_bipol_project
from calculations.airfoil_comparison import parse_comparison, rank_comparison, resolve_criterion
from calculations.presets import AIRCRAFT_PRESETS
from calculations.validation import validate_parameters

TEXT = ('# dane z katalogu dla Re = 5,8 mln\n'
        'NACA 23012; 0,0062; 0,0071; 1,55; umiarkowane\n'
        'NACA 2415\t0.0070\t0.0075\t1.50\tłagodne\n'
        'NACA 4412; 0.0065; 0.0068; 1.60')


def test_comparison_accepts_semicolons_tabs_and_decimal_commas():
    rows = parse_comparison(TEXT)
    assert [r['name'] for r in rows] == ['NACA 23012', 'NACA 2415', 'NACA 4412']
    assert rows[0]['cx_cz_proj'] == 0.0071 and rows[1]['cz_max'] == 1.5 and rows[2]['stall'] == 'nie opisano'
    with pytest.raises(ValueError, match='wiersz 2'):
        parse_comparison('NACA 0012; 0,006; 0,007; 1,4\nNACA 2412; abc; 0,007; 1,5')
    with pytest.raises(ValueError, match='różne'):
        parse_comparison('NACA 0012; 0,006; 0,007; 1,4\nnaca  0012; 0,006; 0,007; 1,4')


def test_ranking_follows_the_bipol3_criterion():
    cruise = rank_comparison(parse_comparison(TEXT), 'cruise', 0.411, 'NACA 2415')
    assert [r['name'] for r in cruise] == ['NACA 4412', 'NACA 23012', 'NACA 2415']
    lift = rank_comparison(parse_comparison(TEXT), 'lift', 0.411, 'NACA 2415')
    assert [r['name'] for r in lift] == ['NACA 4412', 'NACA 23012', 'NACA 2415']
    by_lift = rank_comparison(parse_comparison('A; 0,006; 0,0060; 1,3\nB; 0,007; 0,0080; 1,7'), 'lift', .4, 'A')
    assert [r['name'] for r in by_lift] == ['B', 'A'] and by_lift[1]['recommended'] and by_lift[0]['best']
    assert by_lift[1]['k_proj'] == pytest.approx(.4 / .006, abs=.05)
    assert resolve_criterion({'name': 'Temat 66: Samolot transportowy, STOL'}) == 'lift'
    assert resolve_criterion({'name': 'Samolot dyspozycyjny'}) == 'cruise'
    assert resolve_criterion({'name': 'STOL', 'airfoil_criterion': 'cruise'}) == 'cruise'


def test_project_uses_the_comparison_and_feeds_schrenk():
    params = validate_parameters({**AIRCRAFT_PRESETS['ga_trainer'], 'airfoil_comparison': TEXT,
                                  'airfoil': 'NACA 2415', 'airfoil_criterion': 'cruise'})
    r = run_bipol_project(params)
    af = r['bipol_projects']['p2']['airfoil_selection']
    assert af['comparison_by_author'] and af['best_airfoil'] == 'NACA 4412' and af['selected_airfoil'] == 'NACA 2415'
    assert [c['recommended'] for c in af['candidates']] == [False, False, True]
    schrenk = r['bipol_projects']['p3']['schrenk_summary']
    assert schrenk['airfoil_cz_max'] == 1.5 and schrenk['airfoil_cz_max_source'] == 'porównanie profili P2'
    assert schrenk['cz_max_wing_est'] == pytest.approx(1.5 / schrenk['max_cz1'], abs=1e-3)
    # Wartość wpisana w karcie 3.4 ma pierwszeństwo.
    own = run_bipol_project({**params, 'airfoil_cz_max': 1.7})['bipol_projects']['p3']['schrenk_summary']
    assert own['airfoil_cz_max'] == 1.7 and own['airfoil_cz_max_source'] == 'karta 3.4'
    html = app.test_client().post('/report/project/p2', json=params).get_data(as_text=True)
    assert 'Najlepszy według kryterium jest profil NACA 4412; przyjęto NACA 2415' in html and 'NACA 2415 (przyjęty)' in html


def test_invalid_comparison_is_reported_before_calculation():
    with pytest.raises(ValueError, match='Porównanie profili, wiersz 1'):
        validate_parameters({'airfoil_comparison': 'NACA 0012; 0,006'})
    with pytest.raises(ValueError, match='airfoil_criterion'):
        validate_parameters({'airfoil_criterion': 'najlepszy'})
