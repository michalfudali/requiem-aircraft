"""The reproducible study is auditable and cannot hide unresolved design checks."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from calculations import run_bipol_project
from tools.audit_topic7 import numerical_invariants, open_checks


@pytest.fixture(scope='module')
def study():
    p=json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_source_engine.json').read_text(encoding='utf-8'))
    return run_bipol_project(p)


def test_source_engine_study_closes_numbers_but_retains_real_design_issues(study):
    assert all(c['passed'] for c in numerical_invariants(study))
    issues=open_checks(study)
    assert any(v['check'].get('id')=='tailstrike_clearance' for v in issues)
    assert any(v['check'].get('id')=='main_gear_tipback' for v in issues)
    assert any(v['check'].get('id')=='empty_mass_crosscheck' for v in issues)
    assert study['acoustics']['certification_compliant'] is None


@pytest.mark.parametrize('field',['mass','geometry','acoustics'])
def test_independent_invariants_reject_corrupted_results(study,field):
    bad=deepcopy(study)
    if field=='mass':bad['mass']['m_fuel']+=10
    elif field=='geometry':bad['geometry']['wing']['S']*=1.1
    else:bad['acoustics']['propeller_tip_mach']+=.1
    assert any(not c['passed'] for c in numerical_invariants(bad))
