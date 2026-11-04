"""Tests for WTLK motogliders dataset and numbered chart points."""
import xml.etree.ElementTree as ET
import pytest

from calculations import aircraft_store, run_bipol_project
from calculations.aircraft_store import connect
from calculations.presets import AIRCRAFT_PRESETS
from calculations.trends import load_aircraft, analyze_trends
from calculations.trend_report import trend_chart


WTLK_MODELS = [
    ('Nimbus 3DT', 1993, 22.9, 16.3, 480.0, 392.0, 270.0, 55.0, 0.44),
    ('Duo Discus X', 1993, 20.0, 16.4, 700.0, 410.0, 263.0, 46.0, 0.58),
    ('Ventus 2cM', 1994, 15.0, 9.7, 525.0, 290.0, 285.0, 46.0, 0.51),
    ('Banjo MH', 1995, 13.3, 10.5, 260.0, 157.0, 100.0, 28.0, None),
    ('Pipistrel Sinus', 2001, 15.0, 12.3, 472.5, 285.0, 225.0, 27.0, None),
    ('Pipistrel Taurus M', 2004, 15.0, 12.33, 472.5, 285.0, 130.0, 41.0, 0.7),
    ('ASH 31Mi', 2009, 21.0, 13.2, 700.0, 430.0, 280.0, 56.0, None),
    ('Antares 20E', 2009, 20.0, 12.6, 660.0, 460.0, 280.0, 56.0, 0.49),
    ('Alisport Silent 2', 2011, 13.0, 8.9, 300.0, 130.0, 220.0, 40.0, 0.6),
    ('Alatus ME', 2012, 13.1, 13.2, 200.0, 80.0, 140.0, 27.0, 0.6),
    ('GP 11 PULSE', 2021, 13.5, 7.4, 230.0, 120.0, 190.0, 43.0, 0.53),
    ('PW-X10', 2023, 16.0, 15.25, 590.0, 390.0, 265.0, 34.0, None),
]


def test_wtlk_motogliders_in_database():
    """Verify all 12 motogliders from the user table are in the database with exact values."""
    with connect() as con:
        for model, year, b, s, m0, me, vmax, ld, wz in WTLK_MODELS:
            row = con.execute('SELECT * FROM aircraft WHERE model = ?', (model,)).fetchone()
            assert row is not None, f"Model '{model}' not found in database"
            assert row['aircraft_type'] == 'motoglider'
            assert row['year'] == year
            assert row['b'] == pytest.approx(b, rel=1e-3)
            assert row['s'] == pytest.approx(s, rel=1e-3)
            assert row['m0'] == pytest.approx(m0, rel=1e-3)
            assert row['me'] == pytest.approx(me, rel=1e-3)
            assert row['v_max'] == pytest.approx(vmax, rel=1e-3)
            assert row['ld_max'] == pytest.approx(ld, rel=1e-3)
            if wz is not None:
                assert row['w_z_min_ms'] == pytest.approx(wz, rel=1e-3)
            # Aspect ratio b^2 / s
            ar = row['b'] ** 2 / row['s']
            assert ar > 10.0


def test_points_labeled_with_position_numbers_on_charts():
    """Verify generated trend charts label every point with its number in the sample."""
    res = run_bipol_project(dict(AIRCRAFT_PRESETS['motoglider_aos']))
    analysis = res['bipol_projects']['p1']['trend_analysis']
    similar = analysis['similar_aircraft']
    assert len(similar) >= 12
    # Verify each aircraft has a position number
    assert all(r.get('position_num') == i + 1 for i, r in enumerate(similar))

    # Test mass chart
    svg_mass = str(trend_chart(analysis, 'mass'))
    assert 'data-point-num="1"' in svg_mass
    assert 'data-point-num="2"' in svg_mass

    # Test XML structure of labels
    xml_mass = ET.fromstring(svg_mass)
    ns = {'s': 'http://www.w3.org/2000/svg'}
    text_labels = [t.text for t in xml_mass.findall('.//s:text[@data-point-num]', ns)]
    assert len(text_labels) > 0
    # The first point label must be "1"
    assert text_labels[0] == '1'
    # All text labels should be integers corresponding to positions
    for lbl in text_labels:
        assert lbl.isdigit()
        val = int(lbl)
        assert 1 <= val <= len(similar)


def test_report_includes_lp_column_and_numbered_points(client):
    """Verify /report generates table with Lp. and charts with numbered points."""
    resp = client.get('/report?sections=p1&preset=motoglider_aos')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check Lp. column in sample table
    assert 'id="tab-sample"' in html
    assert 'Lp.' in html
    # Check data-point-num on SVG charts
    assert 'data-point-num=' in html

