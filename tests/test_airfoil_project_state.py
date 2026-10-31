"""The calculated project, independent profile API and P3 report share geometry."""
import pytest
import xml.etree.ElementTree as ET

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.airfoils import profile_from_text

SELIG='CUSTOM TEST\n'+'\n'.join(f'{x} {y}' for x,y in (
    (1,.001),(.5,.06),(.3,.075),(.1,.05),(.025,.025),(0,0),
    (.025,-.015),(.1,-.025),(.3,-.03),(.5,-.02),(1,0)))


@pytest.mark.parametrize('name,coordinates',[
    ('NACA 0012',''),('NACA 2412',''),('NACA 23012',''),
    ('Wortmann FX 61-163',SELIG),('NACA 0012',SELIG),('',SELIG),('',SELIG.partition('\n')[2]),
    ('naca0012',''),('Custom   profile',SELIG)])
def test_project_and_profile_api_have_identical_data_and_provenance(name,coordinates):
    params=dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil=name,airfoil_coordinates=coordinates)
    result=run_bipol_project(params)
    p3=result['bipol_projects']['p3']
    client=app.test_client()
    response=client.post('/api/airfoil/200mm',json=dict(airfoil=name,coordinates=coordinates))
    assert response.status_code==200
    standalone=response.json
    info=p3['airfoil_200mm_info']
    assert info['name']==standalone['airfoil']
    assert result['bipol_projects']['p2']['airfoil_selection']['selected_airfoil']==info['name']
    assert info['kind']==standalone['kind']
    assert info['chord_mm']==standalone['chord_mm']==200.
    assert info['thickness_pct']==standalone['thickness_pct']
    assert info['thickness_x_pct']==standalone['thickness_x_pct']
    assert p3['airfoil_200mm_svg']==standalone['svg']
    assert p3['airfoil_200mm_table']==standalone['table']
    assert p3['airfoil_coordinates_note']==standalone['note']
    if coordinates:assert info['kind']=='pasted'
    report=client.post('/report/project/p3',json=params)
    assert report.status_code==200
    assert p3['airfoil_200mm_svg'] in report.get_data(as_text=True)


@pytest.mark.parametrize('name,coordinates',[
    ('Wortmann FX 61-163',''),('NACA 0012','INVALID COORDINATES'),('UNKNOWN PROFILE','')])
def test_unavailable_or_invalid_coordinates_cannot_fall_back_to_another_profile(name,coordinates):
    params=dict(AIRCRAFT_PRESETS['ga_trainer'],airfoil=name,airfoil_coordinates=coordinates)
    p3=run_bipol_project(params)['bipol_projects']['p3']
    assert p3['airfoil_200mm_info'] is None
    assert p3['airfoil_200mm_table']==[] and p3['airfoil_200mm_svg']==''
    report=app.test_client().post('/report/project/p3',json=params)
    assert report.status_code==200
    assert '<figure class="airfoil-1to1">' not in report.get_data(as_text=True)


def test_supplied_profile_name_remains_text_in_svg_attributes():
    name='Custom " data-probe="injected <test> & geometry'
    profile=profile_from_text(SELIG,name)
    svg=ET.fromstring(profile['svg'])
    assert svg.get('aria-label')==f'Profil {name}, cięciwa 200 mm'
    assert svg.get('data-probe') is None
    assert name in ''.join(svg.itertext())
