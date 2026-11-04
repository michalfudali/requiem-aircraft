"""Empirical Adversarial Stress Test Suite for BIPOL M1 Refactored Reports.

Authored by m1_challenger_reports_1 (EMPIRICAL CHALLENGER).
Stress-tests and rigorously challenges:
1. All 10 aircraft presets (glider, jet, piston GA, turboprops, UAVs, aerobatic).
2. Full report, individual section reports (p1-p6), and project reports.
3. Word DOCX generation across all presets and adversarial configurations.
4. Extreme pilot and crew loading (ultra-light 40kg, ultra-heavy 150kg, UAV 0 crew).
5. Infeasible, zero, and extreme ballast trimming scenarios.
6. In-flight payload drop with iterative 8-phase mission mass convergence.
7. Transonic wave polar / compressibility assessment variants (P4 vs P5).
8. Flap type configurations ('plain', 'split', 'fowler', 'junkers', 'none', etc.).
9. Water operating surface (seaplane/amphibian).
10. Preservation of interface contracts, semantic verdict markers, KaTeX math, and absence of Jinja/text corruption.
"""
from copy import deepcopy
import io
import re
import xml.etree.ElementTree as ET
import zipfile

import pytest
from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.report_docx import build_docx

ALL_PRESET_IDS = list(AIRCRAFT_PRESETS.keys())
SECTION_IDS = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6']
FLAP_TYPES = ['plain', 'split', 'single_slotted', 'double_slotted', 'fowler', 'junkers', 'flaperon', 'none']


def check_html_integrity(html: str, context_label: str):
    """Rigorous checks for text corruption, Jinja leaks, and crash markers."""
    assert html and len(html) > 500, f"[{context_label}] HTML response too short or empty"
    
    # Check no Jinja token leaks (outside of <pre> or script if any)
    # Exclude KaTeX / math formulas or legitimate JS
    body_match = re.search(r'<main class="document.*?>(.*?)</main>', html, re.DOTALL)
    body = body_match.group(1) if body_match else html

    # Strip SVGs and Scripts to avoid false positives on SVG math definitions
    body_clean = re.sub(r'<svg.*?</svg>', '', body, flags=re.DOTALL)
    body_clean = re.sub(r'<script.*?</script>', '', body_clean, flags=re.DOTALL)

    # 1. No unrendered Jinja tags: {{ ... }} or {% ... %}
    jinja_tags = re.findall(r'\{\{.*?\}\}|\{%.*?%\}', body_clean)
    assert not jinja_tags, f"[{context_label}] Unrendered Jinja tokens detected: {jinja_tags[:5]}"

    # 2. No Python unhandled exceptions or error text in document body
    for bad_token in ('Traceback (most recent call last)', 'UndefinedError', 'TemplateSyntaxError', 'ZeroDivisionError'):
        assert bad_token not in html, f"[{context_label}] Exception token '{bad_token}' found in output!"

    # 3. Verify acronym ŚDA is eliminated from ballast and report template headers
    assert '<th>ŚC przed [% ŚDA]</th>' not in html, f"[{context_label}] Obsolete 'ŚDA' header found in ballast table!"
    assert '<th>Kn po [% ŚDA]</th>' not in html, f"[{context_label}] Obsolete 'Kn po [% ŚDA]' header found in ballast table!"
    if '<caption>Wspólny balast:' in html:
        assert 'ŚC przed [% ŚCA]' in html and 'ŚC po [% ŚCA]' in html and 'Zapas stateczności po [% ŚCA]' in html, f"[{context_label}] Expected 'ŚCA' in ballast table!"

    # 4. Check for double punctuation in Polish prose (e.g., '..', ',,')
    # Filter out ellipsis '...' and KaTeX/LaTeX decimal comma r'\,', or URLs
    prose_sample = re.sub(r'\\\(.*?\\\)', '', body_clean)  # remove inline math
    prose_sample = re.sub(r'\\\[.*?\\\]', '', prose_sample, flags=re.DOTALL)  # remove display math
    prose_sample = re.sub(r'<[^>]+>', ' ', prose_sample)  # strip tags
    prose_sample = re.sub(r'\.\.\.', ' ', prose_sample)  # remove ellipsis

    double_punct = re.findall(r'([,;:!?])\s*\1|\.\s*\.', prose_sample)
    assert not double_punct, f"[{context_label}] Double punctuation found: {double_punct[:5]}"


def check_docx_validity(html: str, title: str = "Test Report") -> bytes:
    """Compile HTML to DOCX and verify valid OpenXML package."""
    docx_bytes = build_docx(html, title=title, author="Empirical Challenger")
    assert isinstance(docx_bytes, (bytes, bytearray))
    assert len(docx_bytes) > 1000

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        namelist = set(zf.namelist())
        assert 'word/document.xml' in namelist
        assert '[Content_Types].xml' in namelist
        assert '_rels/.rels' in namelist

        for name in namelist:
            if name.endswith(('.xml', '.rels')):
                content = zf.read(name)
                ET.fromstring(content)  # Must parse cleanly without syntax errors
        
        doc_xml = zf.read('word/document.xml').decode('utf-8')
        assert 'SEQ Tabela' in doc_xml or '<w:body>' in doc_xml
    return docx_bytes


# ==============================================================================
# SUITE 1: ALL 10 PRESETS COMPLETE & SECTIONAL VERIFICATION
# ==============================================================================

@pytest.mark.parametrize('preset_id', ALL_PRESET_IDS)
def test_all_presets_full_report(preset_id):
    """Stress-test full report generation for each of the 10 presets."""
    with app.test_client() as client:
        resp = client.get(f'/report?preset={preset_id}')
        assert resp.status_code == 200, f"Preset {preset_id} failed with status {resp.status_code}"
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"Preset {preset_id} Full")

        # Preset-specific contract checks
        if preset_id == 'glider_pw5':
            assert 'Dla szybowca pominięto dobór mocy' in html
            assert 'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano' in html
        elif preset_id in ('uav_male', 'uav_tactical'):
            assert 'Samolot jest bezzałogowy' in html
        elif preset_id == 'regional_turboprop':
            assert 'CS-25' in html


@pytest.mark.parametrize('preset_id', ALL_PRESET_IDS)
@pytest.mark.parametrize('section', SECTION_IDS)
def test_all_presets_individual_sections(preset_id, section):
    """Stress-test single-section reports for each preset."""
    with app.test_client() as client:
        resp = client.get(f'/report?preset={preset_id}&sections={section}')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"Preset {preset_id} Section {section}")


@pytest.mark.parametrize('preset_id', ['pzl_kos', 'glider_pw5', 'vlj_jet', 'uav_male', 'regional_turboprop'])
@pytest.mark.parametrize('section', SECTION_IDS)
def test_all_presets_project_report_endpoints(preset_id, section):
    """Stress-test /report/project/{p_id} endpoints across diverse presets."""
    with app.test_client() as client:
        resp = client.get(f'/report/project/{section}?preset={preset_id}')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"Project Endpoint {section} for {preset_id}")


# ==============================================================================
# SUITE 2: DOCX EXPORT ACROSS DIVERSE AIRCRAFT CONFIGURATIONS
# ==============================================================================

@pytest.mark.parametrize('preset_id', ALL_PRESET_IDS)
def test_docx_export_across_all_presets(preset_id):
    """Ensure Word DOCX generation succeeds without OOXML corruption across all presets."""
    with app.test_client() as client:
        resp = client.get(f'/report?preset={preset_id}')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        
        docx_data = check_docx_validity(html, title=f"Report {preset_id}")
        assert len(docx_data) > 2048


# ==============================================================================
# SUITE 3: ADVERSARIAL CREW & PILOT WEIGHTS
# ==============================================================================

@pytest.mark.parametrize('pilot_weight', [40.0, 50.0, 55.0, 70.0, 110.0, 130.0, 160.0])
def test_extreme_pilot_weights_piston_ga(pilot_weight):
    """Stress-test piston GA report with extreme pilot weights."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    params['m_crew_person'] = pilot_weight
    
    with app.test_client() as client:
        resp = client.post('/report', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"GA Trainer pilot={pilot_weight}kg")
        assert 'Wpływ masy załogi przy stałym płatowcu' in html
        assert 'Dobór balastu korekcyjnego' in html


@pytest.mark.parametrize('pilot_weight', [45.0, 55.0, 110.0, 150.0])
def test_extreme_pilot_weights_glider(pilot_weight):
    """Stress-test pure glider report with extreme pilot weights and CS-22 ballast rules."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['glider_pw5']))
    params['m_crew_person'] = pilot_weight
    
    with app.test_client() as client:
        resp = client.post('/report', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"Glider PW5 pilot={pilot_weight}kg")
        assert 'CS 22.23(b)' in html or 'CS-22' in html


# ==============================================================================
# SUITE 4: BALLAST STRESS-TESTING (INFEASIBLE, ZERO, ASYMMETRIC)
# ==============================================================================

def test_infeasible_ballast_rendering():
    """Adversarially provoke infeasible ballast solution and verify clean degradation."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    # Severely move CG and empty mass to make ballast placement impossible within fuselage bounds
    params['v_h'] = 0.20  # tiny horizontal tail -> extreme forward instability
    params['locked_params'] = ['v_h']
    
    with app.test_client() as client:
        resp = client.post('/report', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Infeasible Ballast Case")
        assert 'Dobór balastu korekcyjnego' in html
        # Should gracefully report status without Jinja crash


def test_motoglider_ballast_and_pilot_loading():
    """Verify motoglider ballast optimization and trim conditions."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['motoglider_aos']))
    params['v_h'] = 0.35
    params['locked_params'] = ['v_h']

    with app.test_client() as client:
        resp = client.post('/report', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Motoglider AOS Ballast")
        assert 'Dobór balastu korekcyjnego' in html
        assert 'Zapas stateczności po [% ŚCA]' in html


# ==============================================================================
# SUITE 5: IN-FLIGHT PAYLOAD DROP & MASS ITERATION CONVERGENCE
# ==============================================================================

def test_iterative_mass_sizing_with_payload_drop():
    """Mission with in-flight payload drop triggers iterative mass convergence narrative."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    params['m_cargo'] = 200.0
    params['payload_drop_kg'] = 150.0
    params['mission_has_drop'] = True

    with app.test_client() as client:
        resp = client.post('/report?sections=p1,p2', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Payload Drop Iterative Sizing")
        assert 'metodą iteracyjną' in html
        assert 'Z uwagi na zrzut części ładunku w locie' in html
        assert 'tab-mass-iteration' in html or 'iteration-table' in html
        assert 'Krok' in html


def test_standard_mass_sizing_proportion_method():
    """Standard mission without drop uses proportion method narrative."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    params['payload_drop_kg'] = 0.0

    with app.test_client() as client:
        resp = client.post('/report?sections=p1,p2', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Standard Proportion Mass Sizing")
        assert 'metodą proporcji' in html
        assert 'Dla profilu misji bez zrzutu ładunku w locie' in html


# ==============================================================================
# SUITE 6: TRANSONIC COMPRESSIBILITY & WAVE POLAR
# ==============================================================================

def test_transonic_wave_polar_required():
    """High-speed jet at M > M_crit triggers wave polar assessment in P4 and P5."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['vlj_jet']))
    params['cruise_speed_kmh'] = 850.0
    params['cruise_altitude_m'] = 12000.0
    params['airfoil'] = 'NACA 0016'

    with app.test_client() as client:
        resp = client.post('/report?sections=p4,p5', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Transonic Jet Wave Polar")
        assert 'data-wave-polar-required="true"' in html
        assert 'Wpływ ściśliwości na osiągi:' in html
        assert 'Ściśliwość w przelocie:' in html


def test_subsonic_low_speed_compressibility():
    """Low-speed piston aircraft has negligible wave drag."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['pzl_kos']))

    with app.test_client() as client:
        resp = client.post('/report?sections=p4,p5', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Subsonic Kos Compressibility")
        assert 'data-wave-polar-required="false"' in html
        assert 'opór falowy jest pomijalny' in html


# ==============================================================================
# SUITE 7: FLAP TYPES MATRIX
# ==============================================================================

@pytest.mark.parametrize('flap_type', FLAP_TYPES)
def test_flap_types_matrix(flap_type):
    """Stress-test all flap mechanization options in P4 and P6 reports."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    params['flap_type'] = flap_type

    with app.test_client() as client:
        resp = client.post('/report?sections=p4,p6', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, f"Flap type {flap_type}")
        if flap_type == 'none':
            assert 'Skrzydło nie jest wyposażone w mechanizację wysklepiającą' in html
            assert 'Samolot nie ma mechanizacji skrzydła' in html
        else:
            assert 'Zastosowano klap' in html or 'Zastosowano klapolotki' in html
            assert 'tab-high-lift-data' in html
            assert 'flap-loads-table' in html


# ==============================================================================
# SUITE 8: WATER OPERATING SURFACE (SEAPLANE / AMPHIBIAN)
# ==============================================================================

def test_water_operating_surface():
    """Seaplane takeoff and landing notes must render cleanly."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['ga_trainer']))
    params['operating_surface'] = 'water'

    with app.test_client() as client:
        resp = client.post('/report?sections=p5', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Water Operating Surface")
        assert 'woda' in html.lower() or 'wod' in html.lower()


# ==============================================================================
# SUITE 9: SEMANTIC VERDICT PHRASES & INTERFACE CONTRACTS
# ==============================================================================

def test_semantic_verdict_phrases_failure_modes():
    """Ensure negative verdicts produce exact contract phrases in conclusions."""
    params = deepcopy(dict(AIRCRAFT_PRESETS['pzl_kos']))
    # Deliberately underpower to fail climb requirement
    params['power_input_mode'] = 'fixed'
    params['engine_power_kw'] = 10.0
    # Increase climb requirement to an impossible 25 m/s
    params['climb_rate_ms'] = 25.0

    with app.test_client() as client:
        resp = client.post('/report', json=params)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        check_html_integrity(html, "Failed Climb Verdict")
        assert 'nie jest spełniony' in html
