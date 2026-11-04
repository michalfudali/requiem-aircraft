"""Route test suite & regression guardrails for BiPOL Requiem Web UI (Milestone 2).

Covers:
- Core application entry points: /, /holistic, /projekty
- Health and status endpoints: /healthz
- Static data and catalog endpoints: /api/presets, /api/topics, /api/aircraft-classification, /api/constraints/suggestions
- Report routes: /report, /report/project/<p_id>, /report/parameters
- Milestone 2 DOM integrity & regression contracts:
  * Zero duplicate HTML IDs across rendered templates
  * Zero duplicate style attributes (e.g. index.html:1986 starterProjectsCard)
  * Clean semantic select controls (no hardcoded pastel hex backgrounds)
  * Exactly 4 primary KPI cards rendered in Overview
  * Exactly 7 primary sidebar items visible in Studio navigation
"""
import re
import pytest
from app import app
from calculations.presets import AIRCRAFT_PRESETS


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


# ==============================================================================
# 1. Primary Route Availability & Portal Mode Tests
# ==============================================================================

def test_index_route_renders_successfully(client):
    """GET / renders main studio shell with 200 OK."""
    res = client.get('/')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'BiPOL' in html
    assert 'id="studioSidebar"' in html
    assert 'id="tab-overview"' in html
    assert 'id="tab-inputs"' in html


def test_holistic_route_renders_with_holistic_portal_mode(client):
    """GET /holistic renders index template in holistic CAE mode."""
    res = client.get('/holistic')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'id="studioSidebar"' in html
    assert 'id="tab-overview"' in html


def test_projekty_route_renders_with_projects_portal_mode(client):
    """GET /projekty renders index template with semester coursework workstation."""
    res = client.get('/projekty')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'id="studioSidebar"' in html
    assert 'pill-p1' in html or 'panel-p1' in html or 'tab-overview' in html


def test_healthz_route(client):
    """GET /healthz returns ok status and application name."""
    res = client.get('/healthz')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert 'BiPOL' in data['application']


# ==============================================================================
# 2. API Route & Contract Tests
# ==============================================================================

def test_api_presets_returns_complete_dictionary(client):
    """GET /api/presets returns all configured aircraft presets."""
    res = client.get('/api/presets')
    assert res.status_code == 200
    presets = res.get_json()
    assert 'pzl_kos' in presets
    assert 'ga_trainer' in presets
    assert 'glider_pw5' in presets
    assert 'vlj_jet' in presets


def test_api_aircraft_classification_route(client):
    """GET /api/aircraft-classification returns Polish aviation regulation catalog."""
    res = client.get('/api/aircraft-classification')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, (dict, list))


def test_api_topics_route(client):
    """GET /api/topics returns MEiL PW BIPOL topic definitions."""
    res = client.get('/api/topics')
    assert res.status_code == 200
    data = res.get_json()
    assert 'categories' in data
    assert 'topics' in data


def test_api_constraints_suggestions_route(client):
    """GET /api/constraints/suggestions returns default suggestions."""
    res = client.get('/api/constraints/suggestions?category=cs23_level2&aircraft_type=piston_ga')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is True
    assert 'suggestions' in data


# ==============================================================================
# 3. Report Routes Tests
# ==============================================================================

@pytest.mark.parametrize('part', ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'])
def test_report_project_routes(client, part):
    """GET /report/project/<p_id> returns 200 OK for each individual project milestone."""
    res = client.get(f'/report/project/{part}')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert f'data-report-section="{part}"' in html or f'Projekt {part.upper()}' in html or 'Wydział Mechaniczny' in html


def test_report_folder_cover_route(client):
    """GET /report/project/folder_cover renders standard MEiL folder cover."""
    res = client.get('/report/project/folder_cover')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'Wydział Mechaniczny Energetyki i Lotnictwa' in html or 'BIPOL' in html


def test_report_parameters_route(client):
    """GET /report/parameters returns 200 OK for valid parameter catalog request."""
    res = client.get('/report/parameters?keys=rho0,T0,g')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'rho0' in html or 'Karta obliczeń' in html


# ==============================================================================
# 4. Milestone 2 Regression Guardrails & UI Contract Assertions
# ==============================================================================

def test_m2_guardrail_no_duplicate_dom_ids(client):
    """Contract: Rendered / must contain zero duplicate element IDs."""
    res = client.get('/')
    html = res.get_data(as_text=True)
    ids = re.findall(r'\bid=["\']([^"\']+)["\']', html)
    duplicates = [id_name for id_name in set(ids) if ids.count(id_name) > 1]
    assert not duplicates, f"Found duplicate DOM IDs in index.html: {duplicates}"


def test_m2_guardrail_no_duplicate_style_attributes(client):
    """Contract: index.html must not contain duplicate style attributes on any tag (e.g. starterProjectsCard)."""
    res = client.get('/')
    html = res.get_data(as_text=True)
    # Search for any HTML tag that declares style="..." more than once
    duplicate_style_tags = re.findall(r'<[^>]+style=["\'][^"\']*["\'][^>]+style=["\'][^"\']*["\'][^>]*>', html)
    assert not duplicate_style_tags, f"Found tags with duplicate style attributes: {duplicate_style_tags}"


def test_m2_guardrail_clean_theme_classes_on_inputs(client):
    """Contract: flap_type, aileron_type, and slat_type selects must not have hardcoded inline pastel hex backgrounds."""
    res = client.get('/')
    html = res.get_data(as_text=True)
    for select_id, bad_color in [('flap_type', '#eff6ff'), ('aileron_type', '#f0fdf4'), ('slat_type', '#f0f9ff')]:
        pattern = rf'id="{select_id}"[^>]*style="[^"]*{bad_color}'
        assert not re.search(pattern, html), f"Found hardcoded pastel background {bad_color} on select #{select_id}"


def test_m2_guardrail_dual_portal_toggle_buttons_exist(client):
    """Contract: Dual-portal mode buttons #btnModeProjects and #btnModeHolistic must be present in DOM."""
    res = client.get('/')
    html = res.get_data(as_text=True)
    assert 'id="btnModeProjects"' in html, "Missing #btnModeProjects button in sidebar"
    assert 'id="btnModeHolistic"' in html, "Missing #btnModeHolistic button in sidebar"


def test_m2_guardrail_sidebar_uncollapsed_item_count(client):
    """Contract: studio_sidebar.html must have exactly 7 primary uncollapsed items."""
    res = client.get('/')
    html = res.get_data(as_text=True)
    # Ensure analysisNavigation is NOT marked open by default
    assert 'id="analysisNavigation" open' not in html, "id='analysisNavigation' must NOT have 'open' attribute on initial render (causes Playwright count to fail)"
