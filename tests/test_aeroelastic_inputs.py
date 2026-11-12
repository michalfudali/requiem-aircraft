"""Engineering contracts for section inputs, not validation of a real aircraft."""
import copy
import math

import pytest

from calculations import run_bipol_project
from calculations.aeroelastics import estimate_aeroelastics, typical_section_flutter, comparison_basis
from calculations.calc_sheet import build_sheet
from calculations.presets import AIRCRAFT_PRESETS
from calculations.validation import validate_parameters


GEOM = dict(wing=dict(b=10., mac=1.5, tc_ratio=.12, sweep_deg=0))
MASS = dict(m0=1000., breakdown=dict(m_wing=150.))
AERO = dict(a_w_rad=5.)
ENV = dict(speeds=dict(v_d_kmh=300.))
DECLARED = dict(aeroelastic_input_mode='documented', wing_bending_stiffness_nm2=1.02e6,
                wing_torsional_stiffness_nm2=1.57e6, wing_mass_per_length_kg_m=15.,
                wing_elastic_axis_ratio=.4, wing_section_cg_ratio=.45, wing_radius_gyration_ratio=.5,
                aeroelastic_data_source='Testowy raport belki, tabela 2',
                aeroelastic_data_conditions='Stałe parametry zastępcze półskrzydła; model do sprawdzenia wzorów')


def estimate(params=None, **kwargs):
    return estimate_aeroelastics(kwargs.get('geom', GEOM), AERO, kwargs.get('mass', MASS), ENV, params)


def test_canonical_technology_changes_moduli_and_never_silently_selects_aluminium():
    metal = estimate({'technology': 'metallic'})
    composite = estimate({'technology': 'composite', 'structure_material': 'metal'})
    assert composite['material_key'] == 'composite'
    assert composite['material_source'] == 'technology'
    assert composite['bending_stiffness_ei']/metal['bending_stiffness_ei'] == pytest.approx(60/72)
    assert composite['torsional_stiffness_gj']/metal['torsional_stiffness_gj'] == pytest.approx(25/27)
    assert any('starszy parametr' in x for x in composite['limitations'])
    assert any('anizotropii' in x for x in composite['limitations'])
    assert estimate({'wing_structure_material': 'wood', 'technology': 'composite'})['material_key'] == 'wood'
    assert estimate({'structural_material': 'carbon'})['material_key'] == 'composite'
    assert any('kadłuba' in x for x in estimate({'technology': 'steel_tube'})['limitations'])


def test_declared_properties_control_independent_beam_relations():
    result = estimate(DECLARED)
    expected_q = math.pi**2*1.57e6/(4*.15*1.5**2*5*5**2)
    assert result['divergence_speed_kmh'] == pytest.approx(math.sqrt(2*expected_q/1.225)*3.6, abs=.05)
    assert result['bending_frequency_hz'] == pytest.approx(1.875**2/(2*math.pi)*math.sqrt(1.02e6/(15*5**4)), abs=.005)
    assert result['input_basis']['source'] == DECLARED['aeroelastic_data_source']
    assert result['input_basis']['skin_thickness_m'] is None
    # Changing geometric skin assumptions must not overwrite the declared stiffness.
    thicker = copy.deepcopy(GEOM); thicker['wing']['tc_ratio'] = .2
    assert estimate(DECLARED, geom=thicker)['bending_stiffness_ei'] == 1.02e6
    assert estimate({**DECLARED, 'wing_torsional_stiffness_nm2': 4*1.57e6})['divergence_speed_kmh'] == pytest.approx(2*result['divergence_speed_kmh'], abs=.1)
    assert result['certification_compliant'] is None


def test_inactive_draft_values_do_not_change_estimate_or_claim_a_source():
    result = estimate({**DECLARED, 'aeroelastic_input_mode': 'estimated'})
    assert result == estimate()


@pytest.mark.parametrize('field', [key for key in DECLARED if key != 'aeroelastic_input_mode'])
def test_declared_mode_requires_every_parameter_and_provenance(field):
    p = {**AIRCRAFT_PRESETS['pzl_kos'], **DECLARED}; del p[field]
    with pytest.raises(ValueError, match='Aeroelastyczność'):
        validate_parameters(p)


@pytest.mark.parametrize('value', [0, -1, math.nan, math.inf, True, None, 'bad', 1e308])
def test_stiffness_must_be_positive_finite_real(value):
    with pytest.raises(ValueError, match='Aeroelastyczność'):
        estimate({**DECLARED, 'wing_bending_stiffness_nm2': value})


def test_mass_matrix_requires_inertia_about_cg_to_be_positive():
    with pytest.raises(ValueError, match='macierz mas'):
        estimate({**DECLARED, 'wing_section_cg_ratio': .65})
    with pytest.raises(ValueError, match='macierz mas'):
        typical_section_flutter(15, 1.5, 1.57e6, 1.02e6, 5, 5, x_cg=.65)


def test_no_coalescence_is_inconclusive_and_does_not_omit_audit_warning():
    p = {**AIRCRAFT_PRESETS['pzl_kos'], **DECLARED, 'wing_section_cg_ratio': .4}
    result = run_bipol_project(p)
    assert result['aeroelastics']['flutter_speed_kmh'] is None
    assert result['aeroelastics']['flutter_safe'] is None
    audit = {c['id']: c for c in result['engineering_audit']['checks']}
    assert not audit['flutter_safety_margin']['passed']
    assert not audit['aeroelastic_substantiation']['passed']
    assert result['engineering_audit']['metrics']['flutter_margin'] is None


def test_very_soft_wing_is_not_artificially_clamped_to_100_pa():
    result = estimate({**DECLARED, 'wing_torsional_stiffness_nm2': .01})
    assert result['divergence_speed_kmh'] < 1
    assert result['divergence_safe'] is False


@pytest.mark.parametrize('xea', [.1, .25])
def test_axis_ahead_of_aerodynamic_centre_does_not_make_negative_divergence_speed(xea):
    result = estimate({**DECLARED, 'wing_elastic_axis_ratio': xea, 'wing_section_cg_ratio': xea})
    assert result['divergence_speed_kmh'] is None
    assert result['divergence_safe'] is None


@pytest.mark.parametrize('category,expected', [('cs22_motoglider', 1.2), ('cs_vla', 1.2),
                                             ('cs25_transport', 1.15), ('easa_optout_ul', 1.2)])
def test_comparison_scope_follows_category(category, expected):
    basis = comparison_basis({'category': category})
    assert basis['factor'] == expected
    if category == 'cs25_transport':
        assert '15%' in basis['note'] and 'EAS' in basis['note']
    if category == 'easa_optout_ul':
        assert basis['rule'] is None


def test_transport_registry_and_defense_question_do_not_repeat_universal_twenty_percent_rule():
    from calculations.regulations import RULES
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['regional_turboprop']))
    question = next(q for q in result['engineering_audit']['defense_questions'] if q['id'] == 'q_aeroelastics')
    assert '20% margines' not in question['expected_answer']
    assert 'przekraczanie ograniczeń' in question['expected_answer']
    assert '15 %' in str(RULES['jar25.629'])


@pytest.mark.parametrize('declared', [False, True])
def test_tree_formulas_reproduce_equivalent_section_calculation(declared):
    result = run_bipol_project({**AIRCRAFT_PRESETS['pzl_kos'], **(DECLARED if declared else {})})
    entries = build_sheet(result).section_entries('p3.aeroelastic')
    assert entries and all(e['consistent'] is not False for e in entries)
    assert {'ae_EI', 'ae_GJ', 'ae_xea', 'ae_xcg', 'ae_r', 'ae_Vdiv'} <= {e['key'] for e in entries}
