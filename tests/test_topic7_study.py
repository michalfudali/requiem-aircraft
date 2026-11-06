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
    assert any(v['check'].get('id')=='empty_mass_crosscheck' for v in issues)
    assert study['acoustics']['certification_compliant'] is None


@pytest.mark.parametrize('field',['mass','geometry','acoustics','component_geometry',
    'component_loads','component_total','allocated_mass'])
def test_independent_invariants_reject_corrupted_results(study,field):
    bad=deepcopy(study)
    if field=='mass':bad['mass']['m_fuel']+=10
    elif field=='geometry':bad['geometry']['wing']['S']*=1.1
    elif field=='acoustics':bad['acoustics']['propeller_tip_mach']+=.1
    elif field=='component_geometry':bad['mass']['component_masses']['inputs']['tc_ratio']*=2
    elif field=='component_loads':bad['mass']['component_masses']['inputs']['ultimate_load_factor']*=1.5
    elif field=='component_total':bad['mass']['component_masses']['m_empty']+=10
    else:bad['bipol_projects']['p3']['component_mass_estimation']['rows'][0]['assigned_mass_kg']+=10
    assert any(not c['passed'] for c in numerical_invariants(bad))
