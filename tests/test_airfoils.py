"""
Testy modułu profili lotniczych i generatora cięciwy 200 mm (calculations/airfoils.py).
"""
import pytest
from calculations.airfoils import (
    naca_4digit_coords,
    naca_23012_coords,
    wortmann_fx61_163_coords,
    nasa_sc2_0412_coords,
    generate_airfoil_200mm,
    generate_airfoil_svg
)


def test_naca_4digit_generation():
    coords = naca_4digit_coords(0.02, 0.4, 0.12)
    assert len(coords) == 25
    # Nose point at x=0
    assert coords[0]['x_mm'] == 0.0
    assert coords[0]['y_upper_mm'] == 0.0
    assert coords[0]['y_lower_mm'] == 0.0
    # Trailing edge at x=200
    assert coords[-1]['x_mm'] == 200.0
    # Max thickness around 30% chord (60 mm)
    mid = next(pt for pt in coords if pt['xc_pct'] == 30.0)
    assert mid['x_mm'] == 60.0
    assert mid['thick_mm'] > 20.0  # 12% of 200 mm = 24 mm approx


def test_naca_23012_generation():
    coords = naca_23012_coords()
    assert len(coords) == 25
    assert coords[0]['x_mm'] == 0.0
    assert coords[-1]['x_mm'] == 200.0
    # Thickness should peak near 21-24 mm
    max_thick = max(pt['thick_mm'] for pt in coords)
    assert 20.0 <= max_thick <= 25.0


def test_wortmann_fx61_163():
    coords = wortmann_fx61_163_coords()
    assert len(coords) == 25
    assert coords[0]['x_mm'] == 0.0
    assert coords[-1]['x_mm'] == 200.0
    # FX 61-163 has 16.3% thickness -> around 32-38 mm for c=200mm
    max_thick = max(pt['thick_mm'] for pt in coords)
    assert 30.0 <= max_thick <= 40.0


def test_nasa_sc2_0412():
    coords = nasa_sc2_0412_coords()
    assert len(coords) == 25
    assert coords[0]['x_mm'] == 0.0
    assert coords[-1]['x_mm'] == 200.0


def test_generate_airfoil_200mm_selection():
    coords_ga, note_ga = generate_airfoil_200mm("NACA 23012")
    assert "NACA 23012" in note_ga
    assert len(coords_ga) == 25

    coords_glider, note_glider = generate_airfoil_200mm("Wortmann FX 61-163")
    assert "Wortmann" in note_glider
    assert len(coords_glider) == 25

    coords_jet, note_jet = generate_airfoil_200mm("NASA SC(2)-0412")
    assert "SC(2)" in note_jet or "nadkrytycznego" in note_jet


def test_generate_airfoil_svg():
    coords = naca_23012_coords()
    svg = generate_airfoil_svg(coords)
    assert svg.startswith('<svg')
    assert svg.endswith('</svg>')
    assert 'viewBox="0 0 640 220"' in svg
    assert 'x = 200 mm' in svg

def test_api_airfoil_200mm_endpoint():
    from app import app
    client = app.test_client()
    res = client.get('/api/airfoil/200mm?airfoil=NACA 23012&tc=0.12')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['airfoil'] == 'NACA 23012'
    assert len(data['table']) == 25
    assert '<svg' in data['svg']
    assert 'NACA 23012' in data['note']
