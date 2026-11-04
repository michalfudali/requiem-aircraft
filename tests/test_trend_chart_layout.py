"""Repeated catalogue masses stay visible without changing scientific data."""
from copy import deepcopy
import xml.etree.ElementTree as ET

import pytest

from calculations.trend_report import _scatter_x_positions, SCATTER_NOTE, trend_chart
from calculations.trends import fit_regression, predict


NS = {'s': 'http://www.w3.org/2000/svg'}
POINTS = [(575, .58, 'Left'), (780, .69, 'Right'),
          *[(600, .45 + i * .02, f'Aircraft {i:02}') for i in range(14)]]


def test_repeated_x_spreads_stably_inside_neighbouring_values_without_mutation():
    points = [(10, .6, 'Left'), (20, .7, 'B'), (20, .5, 'A'),
              (20, .6, 'C'), (21, .6, 'Right')]
    original = deepcopy(points)
    positions = _scatter_x_positions(points, lambda v: v, 0, 100)
    assert points == original
    assert positions[0] == 10 and positions[-1] == 21
    assert len(set(positions[1:4])) == 3
    assert sum(positions[1:4]) / 3 == pytest.approx(20)
    assert all(10 < px < 21 and abs(px - 20) <= 12 for px in positions[1:4])
    reversed_positions = _scatter_x_positions(points[::-1], lambda v: v, 0, 100)
    assert reversed_positions[::-1] == positions
    assert _scatter_x_positions([], lambda v: v, 0, 100) == []


@pytest.mark.parametrize('mode', ['mass', 'ar:range_km', 'ar'])
def test_report_spreads_all_scatter_modes_but_keeps_true_y_tooltips_and_marks(mode):
    fit = fit_regression([(x, y) for x, y, _ in POINTS])
    trend = dict(points=[dict(x=x, y=y, model=model) for x, y, model in POINTS], fit=fit,
                 x_key='ar', y_key='range_km', x_label='AR', y_label='Range',
                 x_unit='−', y_unit='km', key='ar', label='AR', unit='−', forecast_accepted=False)
    analysis = dict(similar_aircraft=[dict(m0=x, empty_fraction=y, model=model) for x, y, model in POINTS],
                    mass_fit=fit, relationships=[trend], time_trends=[trend])
    original = deepcopy(analysis)
    mark = (780, predict(fit, 780), 'punkt 2')
    svg = ET.fromstring(str(trend_chart(analysis, mode, [mark])))
    assert analysis == original
    circles = svg.findall('s:circle', NS)
    assert len(circles) == len(POINTS) + 1
    repeated = circles[2:-1]
    assert len({c.attrib['cx'] for c in repeated}) == 14
    for (xv, yv, model), circle in zip(POINTS, circles):
        assert circle.find('s:title', NS).text == f'{model}: {xv:g}; {yv:g}'
        # Vertical coordinates must retain the exact linear data projection.
        low, high = min(p[1] for p in POINTS), max(p[1] for p in POINTS)
        pad = (high - low) * .1
        expected_y = 240 - (yv - low + pad) / (high - low + 2 * pad) * 215
        assert float(circle.attrib['cy']) == pytest.approx(expected_y, abs=.005)
    # The trend reading remains at the unshifted x position of the unique endpoint.
    assert circles[-1].attrib['cx'] == circles[1].attrib['cx']
    label = next(t for t in svg.findall('s:text', NS) if t.text == 'punkt 2')
    assert label.attrib['text-anchor'] == 'end'
    assert SCATTER_NOTE in ''.join(svg.itertext())


def test_unique_abscissae_keep_original_chart_height_and_no_spread_notice():
    analysis = dict(similar_aircraft=[dict(m0=x, empty_fraction=y, model=m) for x, y, m in POINTS[:2]], mass_fit=None)
    svg = ET.fromstring(str(trend_chart(analysis, 'mass')))
    assert svg.attrib['viewBox'] == '0 0 650 290'
    assert SCATTER_NOTE not in ''.join(svg.itertext())

