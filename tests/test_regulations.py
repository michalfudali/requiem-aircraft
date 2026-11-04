"""Regulation basis (course JAR excerpts), class-dependent design elements and report references."""
import json
import math
import re

import pytest

from app import app
from calculations import regulations as R
from calculations import run_bipol_project
from calculations.atmosphere import G0
from calculations.polish_law import (SUBCATEGORIES, catalog_for_frontend, check_compliance, features,
                                     limit_load_factors, normalize_occupants, resolve_category)
from calculations.presets import AIRCRAFT_PRESETS


def text(html):
    html = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


def test_every_requirement_has_paragraph_document_and_link():
    for key, rule in R.RULES.items():
        assert rule['paragraph'] and rule['text'] and rule['title'], key
        document = R.DOCUMENTS[rule['doc']]
        assert document['url'].startswith('http') and document['citation'], key
    # Course excerpts are the chapters linked from the ZSiS page.
    assert R.DOCUMENTS['jar23_c']['url'] == 'http://itlims-zsis.meil.pw.edu.pl/pomoce/JAR/JAR-23_Struktury.pdf'


def test_every_category_rule_exists_and_is_found_back_from_its_paragraph():
    for key, sub in SUBCATEGORIES.items():
        for role, rule_id in sub.get('rules', {}).items():
            assert rule_id in R.RULES, (key, role)
            assert rule_id in R.find_rules(R.cite(rule_id)), (key, role)


@pytest.mark.parametrize('category,mass,expected', [
    ('jar23_normal', 1000, 3.8), ('jar23_utility', 1000, 4.4), ('jar23_aerobatic', 1000, 6.0),
    ('cs_vla', 700, 3.8), ('cs22_glider', 300, 5.3), ('cs22_aerobatic', 300, 7.0)])
def test_load_factors_and_their_paragraphs(category, mass, expected):
    n_pos, n_neg, ref = limit_load_factors(category, mass)
    assert n_pos == expected
    assert R.find_rules(ref), ref


def test_sailplane_has_no_cargo_baggage_cargo_bay_or_water_operations():
    f = features('cs22_glider', 'glider', 'none')
    assert not (f['cargo'] or f['cargo_bay'] or f['baggage'] or f['powered'] or f['water'])
    f = features('cs22_motoglider', 'motoglider', 'prop')
    assert not (f['cargo'] or f['cargo_bay']) and f['powered']
    assert features('cs25_transport', 'turboprop_regional', 'prop')['cargo_bay']
    assert not features('jar23_normal', 'piston_ga', 'prop')['cargo_bay']
    assert features('easa_uas_specific', 'uav', 'prop')['cargo_label'] == 'wyposażenie zadaniowe'


def test_cargo_entered_for_a_sailplane_is_removed_with_a_note():
    params = dict(AIRCRAFT_PRESETS['motoglider_aos'], m_cargo=60, cargo_bay_length_m=1, cargo_bay_width_m=1,
                  cargo_bay_height_m=1, payload_input_mode='total', operating_surface='water')
    p, notes = normalize_occupants(params)
    assert p['m_cargo'] == 0 and p['cargo_bay_length_m'] == 0 and p['payload_input_mode'] == 'seats'
    assert p['operating_surface'] == 'land'
    assert any('ładunku handlowego' in note for note in notes) and any('ładowni' in note for note in notes)


def test_glider_report_has_no_cargo_baggage_fuel_or_engine_rows():
    with app.test_client() as client:
        body = text(client.get('/report?preset=glider_pw5').get_data(as_text=True))
    for word in ('Ładunek handlowy', 'ładowni', 'bagaż', 'Paliwo w poszczególnych', 'Rozbieg', 'Liczba silników',
                 'Silnik ze śmigłem', 'Instalacja paliwowa', 'Ramię paliwa', 'Udział masy paliwa', 'CS-22 [', 'Amdt'):
        assert word not in body, word
    assert 'Wartości wynikające z przepisów budowy' in body
    assert 'JAR 22.25(a)(2)' in body and 'JAR 22.337' in body


def test_regulation_corrections_follow_the_selected_regulations():
    glider = run_bipol_project(AIRCRAFT_PRESETS['glider_pw5'])
    assert glider['params']['m_crew_person'] == 110 and glider['params']['m_cargo'] == 0
    assert any('JAR 22.25(a)(2)' in note for note in glider['easa_compliance']['corrections'])
    # JAR 23.49(c): a single-engine aeroplane may not exceed 61 kt in landing configuration.
    fighter = run_bipol_project(AIRCRAFT_PRESETS['f6f_hellcat'])
    assert fighter['params']['v_stall_kmh'] == pytest.approx(61 * 1.852, abs=.06)
    check = next(c for c in fighter['easa_compliance']['checks'] if 'VS0' in c['name'])
    assert check['paragraph'] == 'JAR 23.49(c)'


def test_vla_design_speeds_follow_jar_vla_335():
    r = run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos'], category='cs_vla'))
    env, t = r['envelope'], r['envelope']['terms']
    assert env['limits']['basis'] == 'JAR-VLA' and 'JAR-VLA 335(a)' in env['limits']['speed_rule']
    assert t['v_c_min_ms'] == pytest.approx(2.4 * math.sqrt(t['ws']), rel=1e-9)
    assert t['v_d_ms'] >= 1.40 * t['v_c_min_ms'] - 1e-9


def test_jar25_flap_speed_is_1_8_vs0():
    env = run_bipol_project(AIRCRAFT_PRESETS['regional_turboprop'])['envelope']
    assert env['terms']['v_f_ms'] == pytest.approx(1.8 * env['terms']['vs_lnd_ms'], rel=1e-9)
    assert 'JAR 25.335(e)(3)' in env['flap']['basis']


def test_regulation_values_in_report_cite_paragraph_and_chapter():
    with app.test_client() as client:
        html = client.get('/report?preset=ga_trainer').get_data(as_text=True)
    table = html[html.index('id="tab-regulation-values"'):]
    table = table[:table.index('</table>')]
    rows = re.findall(r'<tr><td>.*?</tr>', table, flags=re.S)
    assert len(rows) >= 8
    for row in rows:
        assert re.search(r'JAR[ -]', row) and 'class="cite"' in row, row
    body = text(html)
    # Negative load factor quotes JAR 23.337(b), not (a); every regulation chapter is listed in the literature.
    assert 'Wymaganie przepisów: JAR 23.337(b)' in body
    assert 'JAR-23_Struktury.pdf' in body and 'JAR-23_Ogolne.pdf' in body


def test_every_regulation_assumption_in_the_report_names_a_paragraph():
    from calculations.calc_sheet import build_sheet
    from calculations.report_origin import classify
    for preset in ('ga_trainer', 'glider_pw5', 'regional_turboprop'):
        sheet = build_sheet(run_bipol_project(AIRCRAFT_PRESETS[preset]))
        for entry in sheet.entries.values():
            if entry['kind'] == 'given' and classify(entry)[0] == 'reg':
                assert R.find_rules(entry['source']) or 'STANAG' in entry['source'], (preset, entry['key'], entry['source'])


def test_index_offers_regulations_from_the_catalogue_with_field_limits():
    with app.test_client() as client:
        html = client.get('/').get_data(as_text=True)
    assert html.count('data-regulation-select') == 2 and 'cs23_level' not in html.split('window.BIPOL_REGULATIONS')[0]
    catalog = catalog_for_frontend()
    normal = catalog['subcategories']['jar23_normal']['limits']
    assert normal['n_pax']['max'] == 9 and normal['n_pax']['paragraph'] == 'JAR 23.1(a)(1)'
    assert normal['v_stall_kmh']['max'] == pytest.approx(113.0, abs=.1) and normal['v_stall_kmh']['single_engine_only']
    assert catalog['subcategories']['cs22_glider']['limits']['engine_type']['allowed'] == ['none']
    assert catalog['subcategories']['cs22_motoglider']['features']['motoglider']['cargo'] is False
    assert json.dumps(catalog, ensure_ascii=False).count('JAR 2') > 50


def test_official_topic_outside_jar23_scope_is_redesigned_in_the_category_that_covers_it():
    from calculations.official_topics import ALL_TOPICS
    topic = next(t for t in ALL_TOPICS if t['num'] == 61)
    r = run_bipol_project(dict(topic['parameters']))
    assert r['mass']['m0'] > 5670 and r['params']['category'] == 'cs25_transport'
    law = check_compliance(r['params'], r['mass'], r['geometry'], r['performance'], r['envelope'])
    assert next(c for c in law['checks'] if c['name'] == 'Rodzaj napędu: turbinowy')['ok']
    assert resolve_category(topic['parameters']['category']) == 'jar23_normal'


@pytest.mark.parametrize('category',['cs22_glider','cs22_motoglider'])
def test_ui_crew_mass_depends_on_actual_number_of_occupants(category):
    from calculations.polish_law import ui_limits, occupant_mass_minimum
    limits=ui_limits(category)
    for field in ['m_crew_person','m_pax']:
        assert limits[field]['min_by_occupants']=={
            str(n):occupant_mass_minimum(category,n)[0] for n in (1,2)}
    assert limits['m_crew_person']['min_by_occupants']=={'1':110.0,'2':90.0}
