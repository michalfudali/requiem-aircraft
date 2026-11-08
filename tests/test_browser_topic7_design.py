"""Temat 7: plik projektu wczytany na stronie daje ten sam wynik co obliczenie bez interfejsu."""
import json
from pathlib import Path

import pytest

from calculations import run_bipol_project

pytestmark = pytest.mark.browser
CASE = Path(__file__).parents[1] / 'data/design_cases/topic7_motoszybowiec_21m.json'


def test_design_case_imports_with_its_gear_structure_and_mass_closure(studio):
    page, _, _ = studio
    page.locator('#projectImportFileInput').set_input_files(str(CASE))
    page.wait_for_function('currentResults?.params?.landing_gear_type === "tailwheel"', timeout=60000)
    expected = run_bipol_project(json.loads(CASE.read_text(encoding='utf-8')))
    assert page.evaluate('currentResults.mass.m0') == pytest.approx(expected['mass']['m0'], rel=1e-6)
    assert page.locator('#landing_gear_type').input_value() == 'tailwheel'
    assert page.locator('#technology').input_value() == 'composite'
    assert page.locator('#empty_mass_closure').input_value() == 'components'
