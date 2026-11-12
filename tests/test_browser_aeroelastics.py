"""A user can supply section data, review formulas, save and switch projects."""
import pytest
from playwright.sync_api import expect

from browser_helpers import navigate
from calculations.presets import AIRCRAFT_PRESETS

pytestmark = pytest.mark.browser


@pytest.mark.parametrize('width', [1440, 390])
def test_aeroelastic_section_is_editable_saved_reported_and_resets_between_projects(studio, width):
    page, base, out = studio
    page.set_viewport_size({'width': width, 'height': 1000})
    navigate(page, 'tab-compliance')
    expect(page.locator('#aeroelasticStatus')).to_contain_text('zgodność nie została wykazana')
    page.locator('#wing_structure_material').select_option('composite')
    page.locator('#aeroelastic_input_mode').select_option('documented')
    values = dict(wing_bending_stiffness_nm2='1020000.123456', wing_torsional_stiffness_nm2='1570000.654321',
                  wing_mass_per_length_kg_m='15', wing_elastic_axis_ratio='0.4',
                  wing_section_cg_ratio='0.45', wing_radius_gyration_ratio='0.5',
                  aeroelastic_data_source='Test UI: raport sztywności, tabela 2',
                  aeroelastic_data_conditions='Belka zastępcza; dane testowe do weryfikacji interfejsu')
    for key, value in values.items():
        page.locator('#'+key).fill(value)
    page.locator('#applyAeroelasticData').click()
    page.wait_for_function('currentResults?.aeroelastics.bending_stiffness_ei === 1020000.123456', timeout=60000)
    expect(page.locator('#aeroelasticSource')).to_contain_text(values['aeroelastic_data_source'])
    expect(page.locator('#aeroelasticResults')).to_contain_text('Nieobliczony')
    assert page.evaluate('currentResults.aeroelastics.certification_compliant') is None
    assert page.evaluate('currentResults.aeroelastics.material_key') == 'composite'
    report = page.request.post(base+'/report/project/p3', data=page.evaluate('currentResults.params'))
    assert report.ok
    assert values['aeroelastic_data_source'] in report.text()
    assert 'Nie wykazano zgodności aeroelastycznej' in report.text()
    assert 'data-given="ae_EI"' in report.text() and 'q-ae_falpha' in report.text()
    (out/'P3-aeroelastic.html').write_text(report.text(), encoding='utf8')
    context = page.context.browser.new_context(offline=True)
    try:
        rendered = context.new_page()
        errors = []
        rendered.on('pageerror', lambda error: errors.append(str(error)))
        rendered.set_content(report.text(), wait_until='load')
        rendered.evaluate('document.fonts.ready')
        assert rendered.locator('.katex-error').count() == 0
        assert rendered.locator('#q-ae_falpha .katex').count() > 0
        assert not errors, errors
        rendered.screenshot(path=str(out/'P3-aeroelastic.png'), full_page=True)
    finally:
        context.close()
    page.reload()
    page.wait_for_function('currentResults?.params.wing_bending_stiffness_nm2 === 1020000.123456', timeout=60000)
    navigate(page, 'tab-compliance')
    for key, value in values.items():
        assert page.locator('#'+key).input_value() == value
    assert page.locator('#aeroelasticDeclaredData').is_visible()
    page.evaluate('p => loadProjectIntoForm({name:"Inny projekt", params:p})', dict(AIRCRAFT_PRESETS['pzl_kos']))
    assert page.locator('#aeroelastic_input_mode').input_value() == 'estimated'
    assert page.locator('#wing_structure_material').input_value() == 'auto'
    assert page.locator('#aeroelasticDeclaredData').is_hidden()
    assert page.locator('#wing_bending_stiffness_nm2').input_value() == ''


def test_incomplete_section_cannot_be_applied_and_nonphysical_mass_matrix_is_explained(studio):
    page, _, _ = studio
    navigate(page, 'tab-compliance')
    previous = page.evaluate('currentResults.aeroelastics.bending_stiffness_ei')
    page.locator('#aeroelastic_input_mode').select_option('documented')
    page.locator('#applyAeroelasticData').click()
    assert page.locator('#wing_bending_stiffness_nm2').evaluate('el=>el.validity.valueMissing')
    assert page.evaluate('currentResults.aeroelastics.bending_stiffness_ei') == previous
    for key, value in dict(wing_bending_stiffness_nm2='1e6', wing_torsional_stiffness_nm2='1e6',
                           wing_mass_per_length_kg_m='15', wing_elastic_axis_ratio='.4',
                           wing_section_cg_ratio='.7', wing_radius_gyration_ratio='.5',
                           aeroelastic_data_source='Test', aeroelastic_data_conditions='Test').items():
        page.locator('#'+key).fill(value)
    page.locator('#applyAeroelasticData').click()
    expect(page.locator('#calculationStatus')).to_contain_text('macierz mas', timeout=60000)
    assert page.evaluate('currentResults.aeroelastics.bending_stiffness_ei') == previous
    page.locator('#wing_section_cg_ratio').fill('.4')
    page.locator('#applyAeroelasticData').click()
    page.wait_for_function('currentResults?.params.wing_section_cg_ratio===.4 && currentResults.aeroelastics.flutter_speed_kmh===null', timeout=60000)
    expect(page.locator('#aeroelasticResults')).to_contain_text('Nie wyznaczono')
    assert page.evaluate('currentResults.engineering_audit.checks.find(c=>c.id==="flutter_safety_margin").passed') is False
