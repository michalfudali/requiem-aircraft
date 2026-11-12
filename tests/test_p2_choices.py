"""Guide P2 decisions checked against independent physical optima and UI contracts."""
from html.parser import HTMLParser
import math

import pytest

from calculations import run_bipol_project
from calculations.atmosphere import G0, RHO0
from calculations.calc_sheet import build_sheet
from calculations.design_controls import controls
from calculations.presets import AIRCRAFT_PRESETS
from calculations.sizing import calculate_matching_chart
from calculations.validation import ENUM_CHOICES, NUMERIC_LIMITS


def params(**extra):
    return dict(AIRCRAFT_PRESETS['ga_trainer'], wing_input_mode='loading', **extra)


def test_minimum_thrust_point_matches_analytic_cruise_optimum():
    # At sea level, other requirements negligible: min(Cx0*q/ws+k*ws/q).
    p = dict(engine_type='jet', aircraft_type='jet_business', v_stall_kmh=200,
             cruise_speed_kmh=250, cruise_altitude_m=0, climb_rate_ms=0,
             aspect_ratio=8, oswald_e=.8, cx0=.025, cz_max_to=2, cz_max_lnd=2.2,
             takeoff_distance_m=10000, matching_design_mode='minimum_power')
    chart = calculate_matching_chart(p, 1000)
    q = .5 * RHO0 * (250 / 3.6) ** 2
    k = 1 / (math.pi * 8 * .8)
    # Jet lapse at the chosen speed scales this cruise curve by a constant;
    # the root below is an independent derivative of the parabolic polar.
    expected = q * math.sqrt(.025 / k)
    assert chart['design_point']['ws'] == pytest.approx(expected, rel=2e-5)


@pytest.mark.parametrize('engine,preset', [('prop','ga_trainer'),('jet','vlj_jet')])
def test_minimum_envelope_is_no_worse_than_dense_chart_sweep(engine, preset):
    p = dict(AIRCRAFT_PRESETS[preset], wing_input_mode='loading', matching_design_mode='minimum_power')
    chart = calculate_matching_chart(p, 2000)
    required = chart['design_point']['pw' if engine == 'prop' else 'tw']
    margin = 1.08 if engine == 'prop' else 1.06
    curve_keys = ['curve_takeoff','curve_climb','curve_cruise','curve_ceiling','curve_vmax','curve_tow']
    samples = [max(c[i] for key in curve_keys if (c := chart[key]) is not None and c[i] is not None)
               for i, ws in enumerate(chart['ws_values']) if ws <= chart['ws_limit'] and chart['curve_takeoff'][i] is not None]
    assert required / margin <= min(samples) + (.02 if engine == 'prop' else .001)


def test_range_choice_respects_landing_and_stall_limits():
    p = params(cruise_speed_kmh=150, matching_design_mode='range')
    result = run_bipol_project(p)
    sz = result['sizing']
    assert sz['design_point']['ws'] == pytest.approx(min(sz['ws_max_range'], sz['ws_limit']), abs=.1)
    assert result['geometry']['wing']['S'] == pytest.approx(result['mass']['m0'] * G0 / sz['design_point']['ws'])


def test_known_geometry_takes_precedence_over_a_or_b_choice():
    p = dict(AIRCRAFT_PRESETS['ga_trainer'], wing_input_mode='area_aspect', wing_area_m2=30,
             matching_design_mode='minimum_power')
    r = run_bipol_project(p)
    assert r['geometry']['wing']['S'] == 30
    assert r['sizing']['design_point']['ws'] == pytest.approx(r['mass']['m0'] * G0 / 30)
    assert 'zadanej geometrii' in r['sizing']['design_point']['selection_note']


@pytest.mark.parametrize('mode', ['wing_limit','minimum_power','range'])
@pytest.mark.parametrize('airfield', [{}, {'airfield_elevation_m':1200,'airfield_delta_t_k':15},
                                     {'airfield_elevation_m':-300}])
def test_matching_decision_and_airfield_are_consistent_in_worked_formulas(mode, airfield):
    result = run_bipol_project(params(matching_design_mode=mode, **airfield))
    sheet = build_sheet(result)
    wrong = {key:(e['value'],e['computed']) for key,e in sheet.entries.items() if e['consistent'] is False}
    assert not wrong
    assert sheet.entries['WS']['kind'] == ('solve' if mode == 'minimum_power' else 'calc')
    assert sheet.entries['sigma_lot']['value'] == result['sizing']['terms']['sigma_airfield']


@pytest.mark.parametrize('change', [dict(airfield_elevation_m=float('nan')),dict(cost_rate_production_per_month=0),
    dict(airfield_delta_t_k=200),dict(matching_design_mode='unknown'),dict(design_iteration_mode='unknown'),
    dict(airfoil_source=[]),dict(airfoil_source='x'*4001)])
def test_new_choices_reject_invalid_api_inputs(client, change):
    response = client.post('/api/calculate', json={**params(), **change})
    assert response.status_code == 400


class FormControls(HTMLParser):
    def __init__(self):
        super().__init__(); self.fields = {}; self.labels = set(); self.options = {}; self.select = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('input','select','textarea') and attrs.get('id'):
            assert attrs['id'] not in self.fields, f'Duplicate input: {attrs["id"]}'
            self.fields[attrs['id']] = attrs
        if tag == 'label' and attrs.get('for'):
            self.labels.add(attrs['for'])
        if tag == 'select':
            self.select = attrs.get('id'); self.options[self.select] = set()
        if tag == 'option' and self.select:
            self.options[self.select].add(attrs.get('value'))

    def handle_endtag(self, tag):
        if tag == 'select': self.select = None


# Each missing input must have an explicit scientific/UI reason. This list is
# deliberately exhaustive so newly added validated parameters cannot hide in API.
NON_EDITABLE = {
    'ce_ch': 'alias of elevator_chord_ratio', 'cr_cv': 'alias of rudder_chord_ratio',
    'cruise_ld_p4': 'computed P4 polar in coupled sizing',
    'cruise_ld_p4_altitude_m': 'calculated P4 reference altitude',
    'cruise_ld_p4_speed_kmh': 'calculated P4 reference speed',
    'cz_max_to': 'configuration model, flap/slat choice',
    'delta_cx0_flaps_lnd': 'configuration model, flap choice',
    'delta_cx0_flaps_to': 'configuration model, flap choice',
    'delta_cx0_gear': 'configuration model, gear choice',
    'empty_mass_a': 'legacy mass law excluded by course methodology',
    'empty_mass_c': 'legacy mass law excluded by course methodology',
    'empty_mass_fraction': 'legacy mass law excluded by course methodology',
    'empty_mass_trend_A': 'computed from the selected comparison sample',
    'empty_mass_trend_C': 'computed from the selected comparison sample',
    'engine_static_thrust_kn': 'actual engine proposal, catalog/custom engine panel',
    'm_bag': 'combined passenger and baggage mass m_pax in UI',
    'mass_initial_guess': 'obsolete sample mode, removed during validation',
    'outbound_range_km': 'derived as total route minus return route',
    'span_limit': 'legacy alias resolved by explicit wing geometry mode',
    'trend_count': 'obsolete count alias; use trend_nearest_count',
}


def test_every_validated_numeric_parameter_has_ui_control_or_explicit_derived_role(client):
    form = FormControls(); form.feed(client.get('/').get_data(as_text=True))
    assert set(NUMERIC_LIMITS) - form.fields.keys() == set(NON_EDITABLE)
    for group in controls():
        for field in group['fields']:
            html = form.fields[field['id']]
            assert field['id'] in form.labels
            assert 'data-analysis-param' in html and 'data-optional-param' in html
            assert (float(html['min']), float(html['max'])) == NUMERIC_LIMITS[field['id']]


def test_every_validated_enum_has_all_supported_course_choices_in_ui(client):
    form = FormControls(); form.feed(client.get('/').get_data(as_text=True))
    for key, values in ENUM_CHOICES.items():
        # Validation accepts old documents, then canonicalizes this legacy mode.
        expected = set(values) - ({'standard'} if key == 'mission_phase_model' else set())
        assert form.options.get(key) == expected, key


def test_engine_cost_model_rejects_nonphysical_negative_price_but_accepts_quote():
    from calculations.costs import engine_price
    p = dict(engine_type='jet', turbine_inlet_temp_k=300)
    with pytest.raises(ValueError, match='oferty producenta'):
        engine_price(p,2026,1,None,.3)
    assert engine_price({**p,'engine_price_usd':40000},2026,1,None,.3)[0] == 40000


def test_optional_native_integration_does_not_block_application(client, monkeypatch):
    from calculations import openvsp_bridge
    monkeypatch.setattr(openvsp_bridge,'vsp',None)
    assert client.get('/').status_code == 200
    assert client.get('/healthz').status_code == 200
    assert client.get('/api/openvsp/status').json['available'] is False
    response = client.post('/api/openvsp/build-from-bipol',json={})
    assert response.status_code == 503 and response.json['available'] is False


def test_profile_source_and_decision_are_present_in_real_report(client):
    p = params(matching_design_mode='minimum_power', airfoil='NACA 2415',
               airfoil_source='Źródło autora: geometria analityczna NACA, przykład testowy')
    response = client.post('/report/project/p2', json=p)
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'Źródło autora: geometria analityczna NACA' in text
    assert 'Punkt A minimalizuje' in text
    assert 'NACA 2415' in text
