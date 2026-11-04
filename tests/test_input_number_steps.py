"""Tests verifying that number inputs have correct stepping and precision across the UI."""
import re
from pathlib import Path
import pytest

from calculations.validation import NUMERIC_LIMITS, NUMERIC_STEPS
from calculations.design_controls import controls


def test_numeric_steps_matches_limits():
    """Every numeric limit should have a corresponding sensible step defined."""
    for key in NUMERIC_LIMITS:
        assert key in NUMERIC_STEPS, f"Key '{key}' in NUMERIC_LIMITS missing from NUMERIC_STEPS"
        step = NUMERIC_STEPS[key]
        assert isinstance(step, (int, float))
        assert step > 0


def test_taper_ratio_and_fractions_have_fractional_steps():
    """Ratios and coefficients must have fine fractional steps so arrows do not jump between 0 and 1."""
    assert NUMERIC_STEPS["taper_ratio"] == 0.01
    assert NUMERIC_STEPS["oswald_e"] == 0.01
    assert NUMERIC_STEPS["prop_efficiency"] == 0.01
    assert NUMERIC_STEPS["tc_ratio"] <= 0.01
    assert NUMERIC_STEPS["cx0"] <= 0.001
    assert NUMERIC_STEPS["cz_max_clean"] == 0.01
    assert NUMERIC_STEPS["cz_max_lnd"] == 0.01


def test_design_controls_provide_step():
    """All design controls rendered in P2 choices must provide their specific step."""
    ctrls = controls()
    assert len(ctrls) > 0
    for group in ctrls:
        for field in group["fields"]:
            assert "step" in field, f"Field {field['id']} missing step"
            assert field["step"] != "any", f"Field {field['id']} has step='any'"
            assert isinstance(field["step"], (int, float))
            assert field["step"] > 0


def test_html_templates_have_no_broken_number_steps():
    """Ensure no <input type="number"> in templates uses step='any' or leaves step unassigned."""
    root = Path(__file__).resolve().parents[1]
    templates_dir = root / "templates"
    
    broken_inputs = []
    for html_file in templates_dir.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        for m in re.finditer(r'<input\s+([^>]*type=["\']number["\'][^>]*)>', content, re.IGNORECASE):
            attrs = m.group(1)
            step_m = re.search(r'step=["\']([^"\']+)["\']', attrs)
            id_m = re.search(r'id=["\']([^"\']+)["\']', attrs)
            field_id = id_m.group(1) if id_m else "no-id"
            if not step_m or step_m.group(1) == "any":
                broken_inputs.append((html_file.name, field_id, attrs))

    assert not broken_inputs, f"Found inputs with missing or 'any' step: {broken_inputs}"


def test_index_and_inputs_panel_render_taper_ratio_with_001_step(client):
    """Verify that GET / renders taper_ratio and other parameters with step='0.01'."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Main inputs panel taper_ratio
    assert re.search(r'<input[^>]*id="taper_ratio"[^>]*step="0\.01"', html) or \
           re.search(r'<input[^>]*step="0\.01"[^>]*id="taper_ratio"', html)

    # Wizard taper_ratio
    assert re.search(r'<input[^>]*id="wiz_taper_ratio"[^>]*step="0\.01"', html) or \
           re.search(r'<input[^>]*step="0\.01"[^>]*id="wiz_taper_ratio"', html)

    # cx0
    assert re.search(r'<input[^>]*id="cx0"[^>]*step="0\.001"', html) or \
           re.search(r'<input[^>]*step="0\.001"[^>]*id="cx0"', html)
